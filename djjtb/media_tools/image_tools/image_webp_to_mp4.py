import os
import sys
import pathlib
import tempfile
import shutil
import subprocess
import djjtb.utils as djj
from PIL import Image

os.system('clear')

def extract_webp_frames(webp_path, output_folder):
    """
    Extract all frames from an animated WebP to PNG files.

    FPS is computed from the average of every frame's duration (not just
    the first frame) — some WebPs vary per-frame timing. If every frame
    reports exactly the 100ms PIL default, that's treated as "no real
    metadata" rather than trusted as an actual 10fps — many WebPs re-saved
    by browsers lose their real timing and PIL silently falls back to that
    placeholder, which previously produced wrong-speed output.

    Returns (frame_paths, fps_or_None, status) where status is one of
    'ok', 'not_animated', 'error'.
    """
    try:
        img = Image.open(webp_path)

        if not getattr(img, 'is_animated', False):
            return None, None, 'not_animated'

        frame_count = getattr(img, 'n_frames', 1)
        durations = []
        try:
            for i in range(frame_count):
                img.seek(i)
                duration = img.info.get('duration', None)
                if duration:
                    durations.append(duration)
        except Exception:
            pass

        if durations and any(d != 100 for d in durations):
            avg_duration = sum(durations) / len(durations)
            fps = 1000.0 / avg_duration
        else:
            fps = None  # No real metadata — caller falls back to manual/default

        img.seek(0)

        # Determine if frames are full-canvas or partial-region updates,
        # so partial-update frames get composited onto the previous frame
        # instead of leaving the untouched region blank.
        mode = 'full'
        try:
            while True:
                if img.tile:
                    tile = img.tile[0]
                    update_region = tile[1]
                    update_region_dimensions = update_region[2:]
                    if update_region_dimensions != img.size:
                        mode = 'partial'
                        break
                img.seek(img.tell() + 1)
        except EOFError:
            pass

        img.seek(0)

        frame_paths = []
        i = 0
        last_frame = img.convert('RGBA')

        try:
            while True:
                new_frame = Image.new('RGBA', img.size)

                if mode == 'partial':
                    new_frame.paste(last_frame)

                new_frame.paste(img, (0, 0), img.convert('RGBA'))

                frame_path = os.path.join(output_folder, f'frame_{i:05d}.png')
                new_frame.save(frame_path, 'PNG')
                frame_paths.append(frame_path)

                i += 1
                last_frame = new_frame
                img.seek(img.tell() + 1)
        except EOFError:
            pass

        img.close()
        return frame_paths, fps, 'ok'

    except Exception as e:
        print(f"\033[93m⚠️  Error extracting frames from {os.path.basename(webp_path)}: {e}\033[0m")
        return None, None, 'error'

def convert_webp_to_mp4(webp_path, output_path, quality_preset='high', use_detected_fps=True, manual_fps=None):
    """
    Convert an animated WebP to MP4 using frame extraction and FFmpeg.

    Args:
        webp_path: Path to input WebP file
        output_path: Path for output MP4 file
        quality_preset: 'high', 'medium', or 'low'
        use_detected_fps: Whether to use detected FPS (True) or manual FPS (False)
        manual_fps: Manual FPS value if use_detected_fps is False

    Returns:
        tuple: (success, fps_used, metadata_found, status)
        status is one of 'ok', 'not_animated', 'error'
    """
    temp_dir = tempfile.mkdtemp(prefix='webp2mp4_')

    try:
        print(f"   Extracting frames from {os.path.basename(webp_path)}...")
        frame_paths, detected_fps, status = extract_webp_frames(webp_path, temp_dir)

        if status == 'not_animated':
            print(f"   \033[93m⏭️  Not animated — skipping\033[0m")
            return False, None, False, 'not_animated'

        if not frame_paths:
            return False, None, False, 'error'

        metadata_found = detected_fps is not None

        if use_detected_fps and detected_fps:
            fps = detected_fps
            print(f"   \033[92m✓ Detected FPS: {detected_fps:.2f}\033[0m")
        elif use_detected_fps and not detected_fps:
            fps = manual_fps if manual_fps else 30
            print(f"   \033[93m⚠️  No FPS metadata - using {fps:.2f} FPS\033[0m")
        else:
            fps = manual_fps if manual_fps else 30

        print(f"   Creating MP4 with {len(frame_paths)} frames at {fps:.2f} FPS...")

        quality_settings = {
            'high': {'crf': '18', 'preset': 'slow'},
            'medium': {'crf': '23', 'preset': 'medium'},
            'low': {'crf': '28', 'preset': 'fast'}
        }
        settings = quality_settings.get(quality_preset, quality_settings['high'])

        frame_pattern = os.path.join(temp_dir, 'frame_%05d.png')

        # libx264 + yuv420p requires even width/height — pad odd-dimension
        # sources instead of letting ffmpeg hard-fail on them.
        with Image.open(frame_paths[0]) as first_frame:
            pad_filter = djj.get_pad_filter(*first_frame.size)

        cmd = [
            'ffmpeg',
            '-y',
            '-framerate', str(fps),
            '-i', frame_pattern,
            '-c:v', 'libx264',
            '-crf', settings['crf'],
            '-preset', settings['preset'],
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
        ]
        if pad_filter != 'null':
            cmd += ['-vf', pad_filter]
        cmd.append(output_path)

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode == 0:
            return True, fps, metadata_found, 'ok'
        else:
            print(f"\033[93m⚠️  FFmpeg error: {result.stderr[-200:]}\033[0m")
            return False, None, metadata_found, 'error'

    except Exception as e:
        print(f"\033[93m⚠️  Conversion error: {e}\033[0m")
        return False, None, False, 'error'

    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

def collect_webp_files(input_path, include_subfolders=False):
    """Collect WebP files from a directory."""
    input_path_obj = pathlib.Path(input_path)

    webp_files = []
    if input_path_obj.is_dir():
        if include_subfolders:
            webp_files = list(input_path_obj.rglob('*.webp'))
        else:
            webp_files = list(input_path_obj.glob('*.webp'))

    return sorted([str(f) for f in webp_files], key=str.lower)

def collect_webp_from_txt():
    """Collect WebP files from txt file."""
    txt_path = djj.get_path_input("Enter txt file path")

    if not os.path.exists(txt_path):
        return []

    webp_files = []
    try:
        with open(txt_path, 'r') as f:
            paths = [line.strip() for line in f if line.strip()]

        for path in paths:
            path_obj = pathlib.Path(path)
            if path_obj.is_file() and path_obj.suffix.lower() == '.webp':
                webp_files.append(str(path_obj))
            elif path_obj.is_dir():
                webp_files.extend(collect_webp_files(str(path_obj), include_subfolders=False))
    except Exception as e:
        print(f"\033[93m⚠️  Error reading txt file: {e}\033[0m")

    return sorted(set(webp_files), key=str.lower)

def batch_convert_webps(webp_files, output_folder, source_folder, quality_preset, use_detected_fps, manual_fps=None):
    """
    Convert multiple WebP files to MP4. Mirrors each file's subfolder
    (relative to source_folder) under output_folder, so same-named files
    from different subfolders don't collide/overwrite each other.

    Returns:
        tuple: (success_count, skipped_count, failed_count, fps_info)
    """
    os.makedirs(output_folder, exist_ok=True)

    success_count = 0
    skipped_count = 0
    failed_count = 0
    fps_info = []

    print()
    print("\033[1;33m🔄 Converting WebPs to MP4...\033[0m")
    print("=" * 60)

    for i, webp_path in enumerate(webp_files):
        filename = os.path.basename(webp_path)
        output_filename = os.path.splitext(filename)[0] + '.mp4'

        rel_dir = os.path.relpath(os.path.dirname(webp_path), source_folder)
        dest_dir = output_folder if rel_dir == '.' else os.path.join(output_folder, rel_dir)
        os.makedirs(dest_dir, exist_ok=True)
        output_path = os.path.join(dest_dir, output_filename)

        print(f"\033[93m[{i+1}/{len(webp_files)}]\033[0m {filename}")

        success, fps_used, metadata_found, status = convert_webp_to_mp4(
            webp_path,
            output_path,
            quality_preset,
            use_detected_fps,
            manual_fps
        )

        if success:
            print(f"\033[92m   ✅ Success - {output_filename}\033[0m")
            success_count += 1
            fps_info.append((filename, fps_used, metadata_found))
        elif status == 'not_animated':
            skipped_count += 1
        else:
            print(f"\033[91m   ❌ Failed - {filename}\033[0m")
            failed_count += 1

        print()

    print("=" * 60)
    print(f"\033[1;33m🏁 Conversion Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {success_count}")
    if skipped_count:
        print(f"⏭️  \033[93mSkipped (not animated):\033[0m {skipped_count}")
    print(f"❌ \033[91mFailed:\033[0m {failed_count}")

    return success_count, skipped_count, failed_count, fps_info

def main():
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mAnimated WebP to MP4 Converter\033[0m")
        print("Convert animated WebPs with automatic FPS detection")
        print("\033[92m==================================================\033[0m")
        print()

        # Input mode selection
        input_mode = djj.prompt_choice(
            "\033[93mInput mode:\033[0m\n"
            "1. Folder path\n"
            "2. Space-separated file paths\n"
            "3. Path list from txt file\n",
            ['1', '2', '3'],
            default='1'
        )
        print()

        webp_files = []
        source_folder = None

        if input_mode == '1':
            source_folder = djj.get_path_input("Enter folder path")
            print()

            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'],
                default='2'
            ) == '1'
            print()

            webp_files = collect_webp_files(source_folder, include_sub)

        elif input_mode == '2':
            file_paths = input("📁 \033[93mEnter WebP paths (space-separated):\n\033[0m -> ").strip()

            if not file_paths:
                print("❌ \033[93mNo file paths provided.\033[0m")
                continue

            webp_files = djj.parse_multipath_input(file_paths, extensions=('.webp',))
            if webp_files:
                source_folder = str(pathlib.Path(webp_files[0]).parent)
            print()

        else:  # input_mode == '3'
            webp_files = collect_webp_from_txt()

            if not webp_files:
                print("❌ \033[93mNo valid WebP files found.\033[0m")
                continue

            if webp_files:
                source_folder = str(pathlib.Path(webp_files[0]).parent)
            print()

        if not webp_files:
            print("❌ \033[93mNo WebP files found. Try again.\033[0m\n")
            continue

        print(f"✅ \033[93mFound {len(webp_files)} WebP file(s)\033[0m")

        for i, webp in enumerate(webp_files[:5]):
            print(f"   {i+1}. {os.path.basename(webp)}")
        if len(webp_files) > 5:
            print(f"   ... and {len(webp_files) - 5} more")
        print()

        # FPS handling
        fps_mode = djj.prompt_choice(
            "\033[93mFrame rate handling:\033[0m\n"
            "1. Auto-detect from WebP (recommended)\n"
            "2. Use manual FPS for all\n",
            ['1', '2'],
            default='1'
        )
        print()

        use_detected_fps = (fps_mode == '1')
        manual_fps = None

        if not use_detected_fps:
            manual_fps = djj.get_float_input(
                "Enter FPS [1-120, default: 30]", min_val=1, max_val=120, default=30.0
            )
            print(f"\033[92m✓ Using manual FPS: {manual_fps}\033[0m")
            print()

        # Quality preset
        quality_choice = djj.prompt_choice(
            "\033[93mQuality preset:\033[0m\n"
            "1. High (CRF 18, slower encode)\n"
            "2. Medium (CRF 23, balanced)\n"
            "3. Low (CRF 28, faster encode)\n",
            ['1', '2', '3'],
            default='2'
        )
        print()

        quality_map = {'1': 'high', '2': 'medium', '3': 'low'}
        quality_preset = quality_map[quality_choice]

        output_folder = os.path.join(source_folder, "Output", "webp_to_mp4")
        print(f"\033[92m✓ Output folder: {output_folder}\033[0m")

        print("\n" * 2)
        print("\033[1;93mStarting conversion...\033[0m")

        success, skipped, failed, fps_info = batch_convert_webps(
            webp_files,
            output_folder,
            source_folder,
            quality_preset,
            use_detected_fps,
            manual_fps
        )

        # FPS summary, split by whether real metadata was found
        if fps_info:
            print()
            print("\033[93m📊 FPS Summary:\033[0m")
            print("-" * 50)

            with_metadata = [f for f in fps_info if f[2]]
            without_metadata = [f for f in fps_info if not f[2]]

            if with_metadata:
                print(f"   \033[92m✓ {len(with_metadata)} file(s) with FPS metadata:\033[0m")
                for filename, fps, _ in with_metadata[:5]:
                    print(f"      {filename}: {fps:.2f} FPS")
                if len(with_metadata) > 5:
                    print(f"      ... and {len(with_metadata) - 5} more")

            if without_metadata:
                print(f"\n   \033[93m⚠️  {len(without_metadata)} file(s) WITHOUT FPS metadata:\033[0m")
                print(f"      Used fallback: {manual_fps if manual_fps else 30} FPS")
                for filename, fps, _ in without_metadata[:5]:
                    print(f"      {filename}")
                if len(without_metadata) > 5:
                    print(f"      ... and {len(without_metadata) - 5} more")
                print()
                print("   \033[93mℹ️  These WebPs may have been saved from browsers\033[0m")
                print("   \033[93m   without preserving original timing metadata.\033[0m")
                print("   \033[93m   Try the 'Manual FPS' option if playback seems wrong.\033[0m")

        print()
        print(f"\033[92m✓ Output folder:\033[0m {output_folder}")
        print()

        djj.prompt_open_folder(output_folder)

        print("\n" * 2)

        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == '__main__':
    main()
