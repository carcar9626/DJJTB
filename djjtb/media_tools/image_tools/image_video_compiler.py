import os
import subprocess
import sys
import pathlib
import logging
from datetime import datetime
import djjtb.utils as djj

os.system('clear')

# --- Image Collection (same pattern as slideshow maker) ---

def collect_images_from_folder(input_path):
    """Collect images from a folder (no subfolders)."""
    input_path_obj = pathlib.Path(input_path)
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
    images = [f for f in input_path_obj.glob('*') if f.suffix.lower() in image_extensions and f.is_file()]
    return sorted([str(v) for v in images], key=lambda x: x.lower())

def collect_images_from_paths(raw_input):
    """Collect images from space-separated file/folder paths."""
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
    images = []
    for path_str in raw_input.strip().split():
        path_obj = pathlib.Path(path_str.strip('\'"'))
        if path_obj.is_file() and path_obj.suffix.lower() in image_extensions:
            images.append(str(path_obj))
        elif path_obj.is_dir():
            images.extend(collect_images_from_folder(str(path_obj)))
    return sorted(images, key=lambda x: x.lower())

def collect_images_from_txt():
    """Collect images from a txt file of paths."""
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
    paths = djj.get_paths_from_txt("📄 Enter txt file path")
    if not paths:
        return []
    images = []
    for path in paths:
        path_obj = pathlib.Path(path)
        if path_obj.is_file() and path_obj.suffix.lower() in image_extensions:
            images.append(str(path))
        elif path_obj.is_dir():
            images.extend(collect_images_from_folder(str(path)))
    return sorted(set(images), key=lambda x: x.lower())


# --- Subfolder Grouping ---

def collect_subfolders_with_images(parent_path):
    """
    Scan immediate subfolders of parent_path.
    Returns dict: {subfolder_path: [sorted image paths]}
    Only includes subfolders that actually contain images.
    """
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
    parent = pathlib.Path(parent_path)
    grouped = {}

    for subfolder in sorted(parent.iterdir()):
        if subfolder.is_dir():
            images = sorted(
                [str(f) for f in subfolder.glob('*') if f.is_file() and f.suffix.lower() in image_extensions],
                key=lambda x: x.lower()
            )
            if images:
                grouped[str(subfolder)] = images

    return grouped


# --- Resolution Detection ---

def get_image_dimensions(image_path):
    """Get width x height from first valid image using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0",
            image_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        w, h = map(int, result.stdout.strip().split('x'))
        return w, h
    except Exception:
        return None


# --- Audio Helpers ---

def get_audio_duration(path):
    """Get duration of an audio/video file in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return None


# --- Core Compiler ---

def compile_images_to_video(images, fps, audio_mode, audio_ref_path, output_file):
    """
    Compile a sorted list of images into a video using ffmpeg.

    Audio modes:
        'none'      - no audio stream
        'silent'    - silent AAC audio track
        'reference' - audio extracted from reference video, looped if short, trimmed to video length
    """

    # --- Step 1: Create image list file for ffmpeg concat ---
    list_file = output_file.replace('.mp4', '_input_list.txt')
    duration_per_frame = 1.0 / fps  # how long each image shows

    with open(list_file, 'w') as f:
        for img in images:
            f.write(f"file '{img}'\n")
            f.write(f"duration {duration_per_frame}\n")
        # ffmpeg concat needs last entry repeated without duration
        f.write(f"file '{images[-1]}'\n")

    video_duration = len(images) * duration_per_frame

    # --- Step 2: Build ffmpeg command ---
    cmd = ["ffmpeg", "-y"]

    if audio_mode == 'reference':
        # Input 0: image concat, Input 1: reference audio
        cmd += [
            "-f", "concat", "-safe", "0", "-i", list_file,
            "-stream_loop", "-1", "-i", audio_ref_path,  # loop audio input
        ]
        cmd += [
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "veryfast",
            "-c:a", "aac",
            "-t", str(video_duration),  # trim both video and audio to video length
            output_file
        ]

    elif audio_mode == 'silent':
        cmd += [
            "-f", "concat", "-safe", "0", "-i", list_file,
            "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000",
        ]
        cmd += [
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "veryfast",
            "-c:a", "aac",
            "-t", str(video_duration),
            "-shortest",
            output_file
        ]

    else:  # no audio
        cmd += [
            "-f", "concat", "-safe", "0", "-i", list_file,
            "-map", "0:v:0",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "veryfast",
            "-t", str(video_duration),
            "-an",
            output_file
        ]

    # --- Step 3: Run ---
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        success = True
        error = None
    except subprocess.CalledProcessError as e:
        success = False
        error = e.stderr
    finally:
        # Clean up list file
        if os.path.exists(list_file):
            os.remove(list_file)

    return success, error, video_duration


# --- Main ---

if __name__ == '__main__':
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93m🎞️  IMAGE → VIDEO COMPILER\033[0m")
        print("Compiles image frames into a video file")
        print("\033[92m==================================================\033[0m")
        print()

        # --- Input Mode ---
        input_mode = djj.prompt_choice(
            "\033[93mInput mode:\033[0m\n"
            "1. Folder path\n"
            "2. Space-separated file paths\n"
            "3. Path list from txt file\n",
            ['1', '2', '3'],
            default='1'
        )
        print()

        images = []
        folder_path = None
        subfolder_mode = False
        subfolder_groups = {}

        if input_mode == '1':
            folder_path = djj.get_path_input("📁 Enter folder path")
            print()

            include_sub = djj.prompt_choice(
                "\033[93mSubfolders?\033[0m\n"
                "1. This folder only\n"
                "2. Each subfolder → separate video\n",
                ['1', '2'],
                default='1'
            )
            print()

            if include_sub == '2':
                subfolder_mode = True
                subfolder_groups = collect_subfolders_with_images(folder_path)
                if not subfolder_groups:
                    print("\033[1;5;93m❌ No subfolders with images found.\033[0m\n")
                    continue
                total_images = sum(len(v) for v in subfolder_groups.values())
                print(f"✅ \033[93m{len(subfolder_groups)} subfolder(s) found — {total_images} images total\033[0m")
                for sf, imgs in subfolder_groups.items():
                    print(f"   📁 {os.path.basename(sf)}  ({len(imgs)} images)")
                print()
            else:
                images = collect_images_from_folder(folder_path)

        elif input_mode == '2':
            raw = input("📁 \033[93mEnter image paths (space-separated):\033[0m\n -> ").strip()
            if not raw:
                print("❌ \033[93mNo paths provided.\033[0m")
                continue
            images = collect_images_from_paths(raw)

        else:
            images = collect_images_from_txt()

        if not subfolder_mode:
            if not images:
                print("\033[1;5;93m❌ No valid image files found. Try again.\033[0m\n")
                continue

            # Set folder_path for output if not already set
            if not folder_path:
                folder_path = str(pathlib.Path(images[0]).parent)

            print(f"\n✅ \033[93m{len(images)} image(s) found\033[0m")

            # --- Detect Resolution ---
            dims = get_image_dimensions(images[0])
            if dims:
                print(f"📐 \033[93mDetected resolution:\033[0m {dims[0]}x{dims[1]} (from first image)")
            else:
                print("\033[93m⚠️  Could not detect resolution — ffmpeg will use source dimensions\033[0m")
            print()
        else:
            # In subfolder mode resolution shown per-batch, just confirm here
            first_images = list(subfolder_groups.values())[0]
            dims = get_image_dimensions(first_images[0])
            if dims:
                print(f"📐 \033[93mDetected resolution:\033[0m {dims[0]}x{dims[1]} (from first image of first subfolder)")
            print()

        # --- Frame Rate ---
        fps = djj.get_int_input(
            "🎬 \033[93mFrame rate (1–120 fps):\033[0m\n"
            "   Examples: 1 = 1 image/sec  |  24/30/60 = smooth video\n"
            "   Enter fps",
            min_val=1,
            max_val=120
        )
        print()

        # Quick summary so user knows what they're getting
        sample_count = len(images) if not subfolder_mode else sum(len(v) for v in subfolder_groups.values())
        video_duration_preview = sample_count / fps if not subfolder_mode else len(list(subfolder_groups.values())[0]) / fps
        mins = int(video_duration_preview // 60)
        secs = video_duration_preview % 60
        if mins > 0:
            duration_str = f"{mins}m {secs:.1f}s"
        else:
            duration_str = f"{secs:.1f}s"
        if not subfolder_mode:
            print(f"⏱️  \033[93mEstimated duration:\033[0m {duration_str} ({len(images)} frames @ {fps}fps)")
        else:
            print(f"⏱️  \033[93mEstimated duration per video:\033[0m ~{duration_str} (varies by subfolder @ {fps}fps)")
        print()

        # --- Audio ---
        audio_choice = djj.prompt_choice(
            "\033[93mAudio:\033[0m\n"
            "1. No audio\n"
            "2. Silent audio track\n"
            "3. Audio from reference video\n",
            ['1', '2', '3'],
            default='1'
        )
        print()

        audio_mode = {'1': 'none', '2': 'silent', '3': 'reference'}[audio_choice]
        audio_ref_path = None

        if audio_mode == 'reference':
            audio_ref_path = djj.get_path_input("🎵 Enter reference video path (audio will be extracted)")
            print()
            # Give user a heads up on length mismatch
            ref_duration = get_audio_duration(audio_ref_path)
            if ref_duration:
                if ref_duration < video_duration_preview:
                    print(f"\033[93m⚠️  Reference audio ({ref_duration:.1f}s) is shorter than video ({video_duration_preview:.1f}s) — will loop\033[0m")
                elif ref_duration > video_duration_preview:
                    print(f"\033[93m✂️  Reference audio ({ref_duration:.1f}s) is longer than video ({video_duration_preview:.1f}s) — will trim\033[0m")
                else:
                    print(f"\033[92m✅ Audio and video durations match\033[0m")
            print()

        # --- Compile ---
        audio_label = {'none': 'No audio', 'silent': 'Silent track', 'reference': 'From reference video'}[audio_mode]

        if subfolder_mode:
            # --- Multi-subfolder compile ---
            parent_resolved = str(pathlib.Path(folder_path).resolve())
            all_outputs = []
            all_errors = []

            print(f"\033[1;93mCompiling {len(subfolder_groups)} video(s)...\033[0m")
            print("-------------")

            for idx, (subfolder_path, sf_images) in enumerate(subfolder_groups.items(), 1):
                sf_name = os.path.basename(subfolder_path)
                sf_duration = len(sf_images) / fps
                sf_mins = int(sf_duration // 60)
                sf_secs = sf_duration % 60
                sf_dur_str = f"{sf_mins}m {sf_secs:.1f}s" if sf_mins > 0 else f"{sf_secs:.1f}s"

                print(f"\033[93m[{idx}/{len(subfolder_groups)}] {sf_name}\033[0m  ({len(sf_images)} frames → {sf_dur_str})")

                # Output: parent/Output/VideoCompiler/subfoldername_fps_timestamp.mp4
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = os.path.join(parent_resolved, "Output", "VideoCompiler")
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir, f"{sf_name}_{fps}fps_{timestamp}.mp4")

                success, error, _ = compile_images_to_video(
                    images=sf_images,
                    fps=fps,
                    audio_mode=audio_mode,
                    audio_ref_path=audio_ref_path,
                    output_file=output_file
                )

                if success:
                    print(f"   \033[92m✅ {output_file}\033[0m")
                    all_outputs.append(output_file)
                else:
                    print(f"   \033[91m❌ Failed\033[0m")
                    if error:
                        error_lines = [l for l in error.strip().split('\n') if l.strip()]
                        for line in error_lines[-2:]:
                            print(f"      \033[93m{line}\033[0m")
                    all_errors.append(sf_name)

            print()
            print("\033[93mImage → Video Compiler Summary\033[0m")
            print("-------------")
            print(f"Subfolders processed: {len(subfolder_groups)}")
            print(f"Videos created:       {len(all_outputs)}")
            print(f"Failed:               {len(all_errors)}")
            print(f"Frame rate:           {fps} fps")
            print(f"Audio:                {audio_label}")
            if all_errors:
                print(f"Failed folders:       {', '.join(all_errors)}")

            if all_outputs:
                top_output_dir = os.path.join(parent_resolved, "Output", "VideoCompiler")
                print(f"\n\033[92m✅ Done! Output folder: {top_output_dir}\033[0m")
                djj.prompt_open_folder(top_output_dir)

        else:
            # --- Single compile ---
            folder_path_resolved = str(pathlib.Path(folder_path).resolve())
            output_dir = os.path.join(folder_path_resolved, "Output", "VideoCompiler")
            os.makedirs(output_dir, exist_ok=True)

            folder_name = os.path.basename(folder_path_resolved)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(output_dir, f"{folder_name}_{fps}fps_{timestamp}.mp4")

            print("\033[1;93mCompiling...\033[0m")
            print("-------------")

            success, error, actual_duration = compile_images_to_video(
                images=images,
                fps=fps,
                audio_mode=audio_mode,
                audio_ref_path=audio_ref_path,
                output_file=output_file
            )

            print()
            print("\033[93mImage → Video Compiler Summary\033[0m")
            print("-------------")
            print(f"Images compiled: {len(images)}")
            print(f"Frame rate:      {fps} fps")
            print(f"Duration:        {duration_str}")
            print(f"Audio:           {audio_label}")

            if success:
                print(f"Output:          {output_file}")
                print(f"\n\033[92m✅ Done!\033[0m")
                djj.prompt_open_folder(output_dir)
            else:
                print(f"\n\033[91m❌ Compile failed.\033[0m")
                if error:
                    error_lines = [l for l in error.strip().split('\n') if l.strip()]
                    for line in error_lines[-4:]:
                        print(f"   \033[93m{line}\033[0m")

        # --- What Next ---
        action = djj.what_next()
        if action == 'exit':
            break

    os.system('clear')
