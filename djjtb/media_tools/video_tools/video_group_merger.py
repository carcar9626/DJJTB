import os
import sys
import subprocess
import pathlib
import tempfile
import djjtb.utils as djj

os.system('clear')

VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.webm', '.mov')

# ─── Helpers ─────────────────────────────────────────────────────────────────

def clean_path(path_str):
    return path_str.strip().strip('\'"')

def is_valid_video(filename):
    return filename.lower().endswith(VIDEO_EXTENSIONS)

def collect_videos_from_folder(input_path):
    """Collect videos from a single folder (no recursion)."""
    input_path_obj = pathlib.Path(input_path)
    videos = [f for f in input_path_obj.glob('*') if f.suffix.lower() in VIDEO_EXTENSIONS and f.is_file()]
    return sorted([str(v) for v in videos], key=str.lower)

def collect_subfolders_with_videos(parent_path):
    """
    Scan immediate subfolders of parent_path.
    Returns dict: {subfolder_path: [sorted video paths]}
    Only includes subfolders that actually contain videos.
    """
    parent = pathlib.Path(parent_path)
    grouped = {}
    for subfolder in sorted(parent.iterdir()):
        if subfolder.is_dir():
            videos = collect_videos_from_folder(str(subfolder))
            if videos:
                grouped[str(subfolder)] = videos
    return grouped

def collect_videos_from_paths(file_paths):
    """Collect videos from space-separated file/folder paths."""
    videos = []
    for path_str in file_paths.strip().split():
        path_obj = pathlib.Path(clean_path(path_str))
        if path_obj.is_file() and is_valid_video(path_obj.name):
            videos.append(str(path_obj))
        elif path_obj.is_dir():
            videos.extend(collect_videos_from_folder(str(path_obj)))
    return sorted(videos, key=str.lower)

def get_user_group_size():
    try:
        group_size = int(input("\033[93mHow many files to merge per group?\033[0m\n [default 2]: ").strip() or 2)
        if group_size < 2:
            raise ValueError
        return group_size
    except ValueError:
        print("❌ Invalid input. Using default of 2.")
        return 2

# ─── Video Info ───────────────────────────────────────────────────────────────

def get_video_info(video_path):
    cmd = [
        "ffprobe", "-v", "quiet", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,r_frame_rate",
        "-of", "csv=p=0", video_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        parts = result.stdout.strip().split(',')
        codec = parts[0] if len(parts) > 0 else "unknown"
        width = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        height = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
        fps = parts[3] if len(parts) > 3 else "30/1"
        return codec, width, height, fps
    except Exception:
        return "unknown", 0, 0, "30/1"

# ─── Sizing ───────────────────────────────────────────────────────────────────

def get_sizing_method(videos):
    print(f"\n📹 \033[93mChoose sizing method:\033[0m")
    print("\nSample video dimensions:")
    for i, video in enumerate(videos[:3]):
        _, width, height, _ = get_video_info(video)
        print(f"  {i+1}. {os.path.basename(video)}: {width}x{height}")
    if len(videos) > 3:
        print(f"  ... and {len(videos) - 3} more")
    print()

    sizing_choice = djj.prompt_choice(
        "\033[93mSizing method:\033[0m\n"
        "1. Use first video's dimensions\n"
        "2. Fixed target size (1920x1080)\n"
        "3. Crop all to fit (16:9 or 9:16)\n",
        ['1', '2', '3'],
        default='1'
    )

    if sizing_choice == '3':
        print()
        crop_aspect = djj.prompt_choice(
            "\033[93mCrop aspect ratio:\033[0m\n1. 16:9 (horizontal)\n2. 9:16 (vertical)\n",
            ['1', '2'],
            default='1'
        )
        return 'crop', crop_aspect

    print()
    use_background = djj.prompt_choice(
        "\033[93mBackground method:\033[0m\n1. Blurred background (no black bars)\n2. Black padding (simple/fast)\n",
        ['1', '2'],
        default='1'
    ) == '1'

    method_map = {'1': 'first_video', '2': 'fixed_1920x1080'}
    base_method = method_map[sizing_choice]
    return (f"{base_method}_blur" if use_background else f"{base_method}_pad"), None

def build_crop_filter(crop_aspect, width, height):
    if crop_aspect == '1':  # 16:9
        target_w = int((16 / 9) * height)
        if target_w <= width:
            offset_x = (width - target_w) // 2
            return f"crop={target_w}:{height}:{offset_x}:0", target_w, height
        else:
            target_h = int((9 / 16) * width)
            offset_y = (height - target_h) // 2
            return f"crop={width}:{target_h}:0:{offset_y}", width, target_h
    else:  # 9:16
        target_w = int((9 / 16) * height)
        if target_w <= width:
            offset_x = (width - target_w) // 2
            return f"crop={target_w}:{height}:{offset_x}:0", target_w, height
        else:
            target_h = int((16 / 9) * width)
            offset_y = (height - target_h) // 2
            return f"crop={width}:{target_h}:0:{offset_y}", width, target_h

def will_need_padding_after_crop(crop_aspect, width, height, target_width, target_height):
    _, cropped_w, cropped_h = build_crop_filter(crop_aspect, width, height)
    crop_ratio = cropped_w / cropped_h
    target_ratio = target_width / target_height
    return abs(crop_ratio - target_ratio) > 0.05

def create_background_video(video_path, output_path, target_width, target_height, opacity=0.7, blur_radius=8):
    temp_bg_video = os.path.join(os.path.dirname(output_path), f"temp_bg_{os.path.basename(output_path)}")
    bg_cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
               f"crop={target_width}:{target_height},"
               f"gblur=sigma={blur_radius},"
               f"eq=brightness=-{1-opacity}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-an", temp_bg_video
    ]
    result = subprocess.run(bg_cmd, capture_output=True, text=True)
    return temp_bg_video if result.returncode == 0 else None

def _bg_overlay_cmd(bg_video, video, target_width, target_height, temp_output):
    """Composite the (scaled) source video over its blurred background."""
    return [
        "ffmpeg", "-y", "-i", bg_video, "-i", video,
        "-filter_complex",
        f"[1:v]scale='if(gt(iw/ih,{target_width}/{target_height}),{target_width},-2)':'if(gt(iw/ih,{target_width}/{target_height}),-2,{target_height})'[scaled];"
        f"[0:v][scaled]overlay=(W-w)/2:(H-h)/2[outv]",
        "-map", "[outv]", "-map", "1:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-r", "30", "-pix_fmt", "yuv420p",
        temp_output
    ]

def _crop_scale_cmd(video, crop_filter, target_width, target_height, temp_output):
    return [
        "ffmpeg", "-y", "-i", video,
        "-vf", f"{crop_filter},scale={target_width}:{target_height}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-r", "30", "-pix_fmt", "yuv420p",
        temp_output
    ]

def _scale_pad_cmd(video, target_width, target_height, temp_output):
    return [
        "ffmpeg", "-y", "-i", video,
        "-vf", f"scale='if(gt(iw/ih,{target_width}/{target_height}),{target_width},-2)':'if(gt(iw/ih,{target_width}/{target_height}),-2,{target_height})',"
               f"pad={target_width}:{target_height}:({target_width}-iw)/2:({target_height}-ih)/2:color=black",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-r", "30", "-pix_fmt", "yuv420p",
        temp_output
    ]

def process_video_for_sizing(video, sizing_method, crop_aspect, target_width, target_height, temp_output, output_dir):
    """Re-encode a single video to match target dimensions/method."""
    _, curr_width, curr_height, _ = get_video_info(video)
    bg_video = None

    if sizing_method == 'crop':
        needs_padding = will_need_padding_after_crop(crop_aspect, curr_width, curr_height, target_width, target_height)
        if needs_padding:
            bg_video = create_background_video(video, temp_output, target_width, target_height)
        if bg_video:
            cmd = _bg_overlay_cmd(bg_video, video, target_width, target_height, temp_output)
        else:
            crop_filter, _, _ = build_crop_filter(crop_aspect, curr_width, curr_height)
            cmd = _crop_scale_cmd(video, crop_filter, target_width, target_height, temp_output)

    elif sizing_method.endswith('_blur'):
        bg_video = create_background_video(video, temp_output, target_width, target_height)
        if bg_video:
            cmd = _bg_overlay_cmd(bg_video, video, target_width, target_height, temp_output)
        else:
            cmd = _scale_pad_cmd(video, target_width, target_height, temp_output)
    else:  # _pad
        cmd = _scale_pad_cmd(video, target_width, target_height, temp_output)

    result = subprocess.run(cmd, capture_output=True, text=True)

    if bg_video and os.path.exists(bg_video):
        os.remove(bg_video)

    return result.returncode == 0, result.stderr


# ─── Core Merge ───────────────────────────────────────────────────────────────

def merge_videos_to_file(videos, output_file, sizing_method, crop_aspect, target_width, target_height, use_reencode=True, label=""):
    """
    Merge a list of videos into a single output file.
    Returns (success: bool, error: str)
    """
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)
    temp_videos = []
    concat_file = None

    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            concat_file = f.name
            needs_processing = sizing_method != 'simple'

            if needs_processing:
                for i, video in enumerate(videos):
                    sys.stdout.write(f"\r\033[93m  {label}Processing {i+1}/{len(videos)}: {os.path.basename(video)}\033[0m  ")
                    sys.stdout.flush()
                    temp_out = os.path.join(output_dir, f"_temp_{i}_{os.path.basename(output_file)}")
                    temp_videos.append(temp_out)
                    ok, err = process_video_for_sizing(
                        video, sizing_method, crop_aspect,
                        target_width, target_height, temp_out, output_dir
                    )
                    if not ok:
                        print(f"\n\033[91m❌ Failed to process: {os.path.basename(video)}\033[0m")
                        return False, err
                    f.write(f"file '{temp_out}'\n")
                print()
            else:
                for video in videos:
                    escaped = video.replace("'", "'\\''")
                    f.write(f"file '{escaped}'\n")

        if use_reencode:
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", "-r", "30", "-pix_fmt", "yuv420p",
                output_file
            ]
        else:
            # Safe to stream-copy here: when needs_processing is True, every
            # entry in concat_file is one of our own temp segments, already
            # normalized to identical codec/dims/fps/pix_fmt by
            # process_video_for_sizing — exactly what -c copy concat requires.
            cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", output_file]

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stderr if result.returncode != 0 else ""

    finally:
        for t in temp_videos:
            if os.path.exists(t):
                os.remove(t)
        if concat_file and os.path.exists(concat_file):
            os.remove(concat_file)


# ─── Simple Merge Modes ───────────────────────────────────────────────────────

def simple_merge_single(videos, output_dir, sizing_method, crop_aspect, target_width, target_height):
    """Merge all videos into one file."""
    base_name = os.path.splitext(os.path.basename(videos[0]))[0]
    output_file = os.path.join(output_dir, f"{base_name}_merged_all.mp4")

    print(f"\n\033[1;93mMerging {len(videos)} videos into one...\033[0m")
    print("-------------")

    ok, err = merge_videos_to_file(videos, output_file, sizing_method, crop_aspect, target_width, target_height)
    if ok:
        print(f"\033[92m✅ Created: {os.path.basename(output_file)}\033[0m")
        return 1, 0
    else:
        print(f"\033[91m❌ Merge failed\033[0m")
        if err:
            for line in [l for l in err.strip().split('\n') if l.strip()][-3:]:
                print(f"   \033[93m{line}\033[0m")
        return 0, 1


def simple_merge_per_folder(subfolder_groups, output_dir, sizing_method, crop_aspect, target_width, target_height):
    """One merged video per subfolder, all outputs flat in output_dir."""
    success_count = 0
    error_count = 0

    print(f"\n\033[1;93mMerging {len(subfolder_groups)} folder(s) → one video each...\033[0m")
    print("-------------")

    for idx, (subfolder_path, videos) in enumerate(subfolder_groups.items(), 1):
        sf_name = os.path.basename(subfolder_path)
        print(f"\n\033[93m[{idx}/{len(subfolder_groups)}] {sf_name}\033[0m  ({len(videos)} videos)")

        output_file = os.path.join(output_dir, f"{sf_name}_merged.mp4")

        ok, err = merge_videos_to_file(
            videos, output_file, sizing_method, crop_aspect,
            target_width, target_height, label=f"{sf_name} "
        )
        if ok:
            print(f"   \033[92m✅ {os.path.basename(output_file)}\033[0m")
            success_count += 1
        else:
            print(f"   \033[91m❌ Failed\033[0m")
            if err:
                for line in [l for l in err.strip().split('\n') if l.strip()][-2:]:
                    print(f"      \033[93m{line}\033[0m")
            error_count += 1

    return success_count, error_count


# ─── Group Merge Modes ────────────────────────────────────────────────────────

def group_merge_videos(videos, output_dir, group_size, use_reencode, sizing_method, crop_aspect, target_width, target_height, label_prefix=""):
    """Split videos into groups of N and merge each group. Returns (success, error) counts."""
    total_groups = len(videos) // group_size
    remaining = len(videos) % group_size
    success_count = 0
    error_count = 0

    if remaining != 0:
        print(f"   \033[93m⚠️  {remaining} file(s) skipped (not enough for a full group of {group_size})\033[0m")

    for g in range(total_groups):
        group_videos = videos[g * group_size: (g + 1) * group_size]
        base_name = os.path.splitext(os.path.basename(group_videos[0]))[0]
        output_file = os.path.join(output_dir, f"{label_prefix}{base_name}_group_{g+1:03d}.mp4")

        preview = ' + '.join(os.path.basename(v) for v in group_videos[:2])
        if len(group_videos) > 2:
            preview += '...'
        print(f"\033[93m  Group {g+1}/{total_groups}:\033[0m {preview}")

        ok, err = merge_videos_to_file(
            group_videos, output_file, sizing_method, crop_aspect,
            target_width, target_height, use_reencode=use_reencode
        )
        if ok:
            print(f"   \033[92m✅ {os.path.basename(output_file)}\033[0m")
            success_count += 1
        else:
            print(f"   \033[91m❌ Failed\033[0m")
            if err:
                for line in [l for l in err.strip().split('\n') if l.strip()][-2:]:
                    print(f"      \033[93m{line}\033[0m")
            error_count += 1

    return success_count, error_count


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mVideo Group Merger\033[0m")
        print("Simple merge or group merge videos")
        print("\033[92m==================================================\033[0m")
        print()

        # --- Merge type ---
        merge_type = djj.prompt_choice(
            "\033[93mMerge type:\033[0m\n"
            "1. Simple merge (all videos → one file)\n"
            "2. Group merge (every N videos → groups)\n",
            ['1', '2'],
            default='1'
        )
        print()

        # --- Input mode ---
        input_mode = djj.prompt_choice(
            "\033[93mInput mode:\033[0m\n"
            "1. Folder path\n"
            "2. Space-separated file paths\n",
            ['1', '2'],
            default='1'
        )
        print()

        videos = []
        output_dir = None
        subfolder_groups = {}
        subfolder_mode = False
        subfolder_scope = None  # 'per_folder' or 'collective'

        # --- Collect input ---
        if input_mode == '1':
            src_dir = djj.get_path_input("📁 Enter folder path")
            src_dir_resolved = str(pathlib.Path(src_dir).resolve())
            print()

            include_sub = djj.prompt_choice(
                "\033[93mSubfolders?\033[0m\n"
                "1. This folder only\n"
                "2. Include subfolders\n",
                ['1', '2'],
                default='1'
            )
            print()

            if include_sub == '2':
                subfolder_groups = collect_subfolders_with_videos(src_dir_resolved)

                if not subfolder_groups:
                    print("\033[93m⚠️  No subfolders with videos found. Falling back to this folder only.\033[0m\n")
                    videos = collect_videos_from_folder(src_dir_resolved)
                else:
                    subfolder_mode = True
                    total_vids = sum(len(v) for v in subfolder_groups.values())
                    print(f"✅ \033[93m{len(subfolder_groups)} subfolder(s) — {total_vids} videos total\033[0m")
                    for sf, vids in subfolder_groups.items():
                        print(f"   📁 {os.path.basename(sf)}  ({len(vids)} videos)")
                    print()

                    if merge_type == '1':
                        scope_choice = djj.prompt_choice(
                            "\033[93mHow to merge?\033[0m\n"
                            "1. One merged video per subfolder\n"
                            "2. Merge all videos recursively into one file\n",
                            ['1', '2'],
                            default='1'
                        )
                    else:
                        scope_choice = djj.prompt_choice(
                            "\033[93mHow to group?\033[0m\n"
                            "1. Groups within each subfolder independently\n"
                            "2. Pool all videos together then group\n",
                            ['1', '2'],
                            default='1'
                        )

                    subfolder_scope = 'per_folder' if scope_choice == '1' else 'collective'
                    print()

                    if subfolder_scope == 'collective':
                        for vids in subfolder_groups.values():
                            videos.extend(vids)
                        videos = sorted(videos, key=str.lower)
            else:
                videos = collect_videos_from_folder(src_dir_resolved)

            output_dir = os.path.join(src_dir_resolved, "Output", "VideoMerger")

        else:
            raw = input("📁 \033[93mEnter file/folder paths (space-separated):\033[0m\n -> ").strip()
            if not raw:
                print("❌ No paths provided.")
                continue
            videos = collect_videos_from_paths(raw)
            if videos:
                output_dir = os.path.join(str(pathlib.Path(videos[0]).parent), "Output", "VideoMerger")
            print()

        # --- Validate ---
        if not subfolder_mode and not videos:
            print("\033[1;5;93m❌ No valid video files found. Try again.\033[0m\n")
            continue
        if subfolder_mode and subfolder_scope == 'per_folder' and not subfolder_groups:
            print("\033[1;5;93m❌ No subfolders with videos found. Try again.\033[0m\n")
            continue

        # Show video summary for non-per-folder modes
        if not subfolder_mode or subfolder_scope == 'collective':
            print(f"✅ \033[93m{len(videos)} video(s) found\033[0m")
            for i, v in enumerate(videos[:3]):
                print(f"  {i+1}. {os.path.basename(v)}")
            if len(videos) > 3:
                print(f"  ... and {len(videos) - 3} more")
            print()

        os.makedirs(output_dir, exist_ok=True)

        # --- Sizing options ---
        sample_videos = videos if videos else list(subfolder_groups.values())[0]
        sizing_method, crop_aspect = get_sizing_method(sample_videos)
        print()

        if sizing_method.startswith('first_video'):
            _, target_width, target_height, _ = get_video_info(sample_videos[0])
            print(f"🎯 \033[93mTarget:\033[0m {target_width}x{target_height} (from first video)")
        elif sizing_method.startswith('fixed_1920x1080'):
            target_width, target_height = 1920, 1080
            print(f"🎯 \033[93mTarget:\033[0m 1920x1080 (fixed)")
        elif sizing_method == 'crop':
            target_width, target_height = (1920, 1080) if crop_aspect == '1' else (1080, 1920)
            aspect_name = "16:9" if crop_aspect == '1' else "9:16"
            print(f"✂️  \033[93mCropping to:\033[0m {aspect_name} ({target_width}x{target_height})")
        print()

        # Group merge extras
        use_reencode = True
        group_size = 2
        if merge_type == '2':
            use_reencode = djj.prompt_choice(
                "\033[93mMerge method:\033[0m\n"
                "1. Re-encode (safer, fixes freezing issues)\n"
                "2. Copy streams (faster, may freeze)\n",
                ['1', '2'],
                default='1'
            ) == '1'
            print()
            group_size = get_user_group_size()
            print()

        # ─── Execute ─────────────────────────────────────────────────────────

        success_count = 0
        error_count = 0

        if merge_type == '1':
            if subfolder_mode and subfolder_scope == 'per_folder':
                success_count, error_count = simple_merge_per_folder(
                    subfolder_groups, output_dir,
                    sizing_method, crop_aspect, target_width, target_height
                )
            else:
                success_count, error_count = simple_merge_single(
                    videos, output_dir,
                    sizing_method, crop_aspect, target_width, target_height
                )

        else:
            print(f"\033[1;93mGrouping into sets of {group_size}...\033[0m")
            print("-------------")

            if subfolder_mode and subfolder_scope == 'per_folder':
                for sf_path, sf_videos in subfolder_groups.items():
                    sf_name = os.path.basename(sf_path)
                    sf_total = len(sf_videos) // group_size
                    print(f"\n\033[93m📁 {sf_name}\033[0m  ({len(sf_videos)} videos → {sf_total} group(s))")
                    s, e = group_merge_videos(
                        sf_videos, output_dir, group_size, use_reencode,
                        sizing_method, crop_aspect, target_width, target_height,
                        label_prefix=f"{sf_name}_"
                    )
                    success_count += s
                    error_count += e
            else:
                success_count, error_count = group_merge_videos(
                    videos, output_dir, group_size, use_reencode,
                    sizing_method, crop_aspect, target_width, target_height
                )

        # ─── Summary ─────────────────────────────────────────────────────────
        print()
        print("\033[93mVideo Merger Summary\033[0m")
        print("-------------")
        print(f"Videos created:  {success_count}")
        if error_count:
            print(f"Errors:          \033[91m{error_count}\033[0m")
        print(f"Output folder:   {output_dir}")
        print()

        djj.prompt_open_folder(output_dir)

        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()