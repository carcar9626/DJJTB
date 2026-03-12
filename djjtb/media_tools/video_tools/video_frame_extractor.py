import os
import sys
import pathlib
import subprocess
import json
import logging
from pathlib import Path
import djjtb.utils as djj

os.system('clear')


def prompt_integer(prompt, min_value=1):
    while True:
        try:
            value = int(input(f"{prompt}: ").strip())
            if value >= min_value:
                return value
            else:
                print(f"\033[93mPlease enter a number >\033[0m= {min_value}.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def get_video_info(video_path):
    """Returns (nb_frames, duration, frame_rate) for a video."""
    try:
        probe_cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=nb_frames,duration,r_frame_rate", "-of", "json", str(video_path)
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        data = json.loads(probe_result.stdout)["streams"][0]
        nb_frames = int(data["nb_frames"]) if "nb_frames" in data else None
        duration = float(data["duration"]) if "duration" in data else None
        frame_rate = eval(data["r_frame_rate"]) if '/' in data["r_frame_rate"] else float(data["r_frame_rate"])

        if duration and frame_rate:
            expected_frames = int(duration * frame_rate)
            if not nb_frames or abs(nb_frames - expected_frames) > 0.1 * expected_frames:
                nb_frames = expected_frames

        return nb_frames or 0, duration or 0, frame_rate or 0
    except Exception:
        return 0, 0, 0


def collect_videos(input_path, subfolders=False):
    input_path_obj = pathlib.Path(input_path)
    video_extensions = ('.mp4', '.mkv', '.webm', '.mov')
    videos = []
    if input_path_obj.is_file() and input_path_obj.suffix.lower() in video_extensions:
        videos = [input_path_obj]
    elif input_path_obj.is_dir():
        if subfolders:
            for root, _, files in os.walk(input_path):
                videos.extend(pathlib.Path(root) / f for f in files if pathlib.Path(f).suffix.lower() in video_extensions)
        else:
            videos = [f for f in input_path_obj.glob('*') if f.suffix.lower() in video_extensions and f.is_file()]
    return videos


# ── Mode 1: interval-based (original) ────────────────────────────────────────

def extract_frames_interval(videos, frame_interval, logger):
    output_base_dirs = []
    total_videos = len(videos)

    for i, video_path in enumerate(videos, 1):
        video_name = Path(video_path).stem
        video_dir = os.path.dirname(video_path)
        output_base_dir = os.path.join(video_dir, "Output", "Frames", video_name)
        Path(output_base_dir).mkdir(parents=True, exist_ok=True)

        progress = (i / total_videos) * 100
        sys.stdout.write(f"\rProcessing {i}/{total_videos} ({progress:.1f}%)...")
        sys.stdout.flush()

        nb_frames, duration, frame_rate = get_video_info(video_path)

        try:
            total_images = max(1, int(nb_frames / frame_interval))
            if total_images > 3000:
                sys.stdout.write(f"\r{' ' * 60}\r")
                sys.stdout.flush()
                print(f"\n\033[93mWarning: \033[0m{total_images} \033[93mimages will be extracted from \033[0m{video_name}\033[93m.\033[0m")
                proceed = djj.prompt_choice("\033[93mThis is a large number of frames. Proceed?\033[0m\n1. Yes, 2. No ", ['1', '2'], default='2')
                if proceed != '1':
                    print(f"\033[93mSkipped \033[0m{video_name}\033[93m.\033[0m")
                    logger.info(f"Frame extraction cancelled for {video_name} (user choice)")
                    output_base_dirs.append(output_base_dir)
                    continue
        except Exception as e:
            logger.error(f"Error estimating frames for {video_path}: {e}")

        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-vf', f'select=not(mod(n\\,{frame_interval}))',
            '-vsync', '0', '-q:v', '2',
            f'{output_base_dir}/{video_name}_F%03d.jpg'
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            extracted = len([f for f in os.listdir(output_base_dir) if f.endswith('.jpg')])
            logger.info(f"Extracted {extracted} frames for {video_name} to {output_base_dir}")
        except subprocess.CalledProcessError as e:
            sys.stdout.write(f"\r{' ' * 60}\r")
            sys.stdout.flush()
            print(f"\033[93mError processing\033[0m {video_name}: {e.stderr}")
            logger.error(f"Error processing {video_name}: {e.stderr}")

        output_base_dirs.append(output_base_dir)

    return output_base_dirs


# ── Mode 2: target count — evenly spread ─────────────────────────────────────

def extract_frames_count(videos, target_count, logger):
    """
    For each video, compute total frames, pick `target_count` evenly-spaced
    frame indices, and extract exactly those frames using ffmpeg's select filter.
    """
    output_base_dirs = []
    total_videos = len(videos)

    for i, video_path in enumerate(videos, 1):
        video_name = Path(video_path).stem
        video_dir = os.path.dirname(video_path)
        output_base_dir = os.path.join(video_dir, "Output", "Frames", video_name)
        Path(output_base_dir).mkdir(parents=True, exist_ok=True)

        progress = (i / total_videos) * 100
        sys.stdout.write(f"\rProcessing {i}/{total_videos} ({progress:.1f}%)...")
        sys.stdout.flush()

        nb_frames, duration, frame_rate = get_video_info(video_path)

        if nb_frames == 0:
            sys.stdout.write(f"\r{' ' * 60}\r")
            print(f"\033[93m❌ Could not get frame count for \033[0m{video_name}\033[93m, skipping.\033[0m")
            logger.error(f"Could not get frame count for {video_name}")
            continue

        # Clamp target to available frames
        actual_count = min(target_count, nb_frames)
        if actual_count < target_count:
            sys.stdout.write(f"\r{' ' * 60}\r")
            print(f"\033[93m⚠️  {video_name} only has {nb_frames} frames — extracting {actual_count} instead of {target_count}.\033[0m")
            sys.stdout.flush()

        # Build evenly-spaced frame indices (0-based)
        if actual_count == 1:
            indices = [nb_frames // 2]
        else:
            step = (nb_frames - 1) / (actual_count - 1)
            indices = [round(step * j) for j in range(actual_count)]

        # Build ffmpeg select expression: eq(n,5)+eq(n,42)+...
        select_expr = "+".join(f"eq(n\\,{idx})" for idx in indices)

        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-vf', f'select={select_expr}',
            '-vsync', '0', '-q:v', '2',
            f'{output_base_dir}/{video_name}_F%03d.jpg'
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            extracted = len([f for f in os.listdir(output_base_dir) if f.endswith('.jpg')])
            logger.info(f"Extracted {extracted}/{actual_count} frames for {video_name} to {output_base_dir}")
        except subprocess.CalledProcessError as e:
            sys.stdout.write(f"\r{' ' * 60}\r")
            sys.stdout.flush()
            print(f"\033[93mError processing\033[0m {video_name}: {e.stderr}")
            logger.error(f"Error processing {video_name}: {e.stderr}")

        output_base_dirs.append(output_base_dir)

    return output_base_dirs


# ── Shared entry point ────────────────────────────────────────────────────────

def extract_frames(input_path, subfolders=False, frame_interval=None):
    """Legacy entry point — defaults to interval mode."""
    videos = collect_videos(input_path, subfolders)
    if not videos:
        print("\033[93mError: No video files found.\033[0m", file=sys.stderr)
        return

    first_video_dir = os.path.dirname(videos[0])
    first_output_dir = os.path.join(first_video_dir, "Output", "Frames")
    os.makedirs(first_output_dir, exist_ok=True)
    logger = djj.setup_logging(first_output_dir, "video_frame_extractor")

    if frame_interval is None:
        frame_interval = prompt_integer("Enter the frame interval (e.g. 10 for every 10th frame)", min_value=1)

    output_base_dirs = extract_frames_interval(videos, frame_interval, logger)
    _print_summary(len(videos), f"interval: every {frame_interval} frames", output_base_dirs)
    return output_base_dirs


def _print_summary(total_videos, mode_label, output_base_dirs):
    sys.stdout.write(f"\r{' ' * 60}\r")
    sys.stdout.flush()
    print()
    print("\n\033[93mFrame Extraction Summary\033[0m")
    print("------------------------")
    print(f"\033[93mVideos processed:\033[0m {total_videos}")
    print(f"\033[93mMode:\033[0m {mode_label}")
    print(f"\033[93mOutput folder(s):\033[0m {len(output_base_dirs)} \033[93mcreated.\033[0m")
    print()
    if output_base_dirs:
        djj.prompt_open_folder(output_base_dirs[-1])


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def main():
    while True:
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mFrame Extractor\033[0m")
        print("Extract frames from videos")
        print("\033[92m==================================================\033[0m")
        print()

        folder = djj.get_path_input("📁 Enter path")
        print()

        include_sub = djj.prompt_choice(
            "📂 Include subfolders?\n1. Yes, 2. No ",
            ['1', '2'], default='2'
        ) == '1'
        print()

        mode = djj.prompt_choice(
            "🎬 Extraction mode?\n1. Interval  (every Nth frame)\n2. Target count  (N frames evenly spread)",
            ['1', '2'], default='1'
        )
        print()

        videos = collect_videos(folder, include_sub)
        if not videos:
            print("\033[93mNo video files found.\033[0m")
            action = djj.what_next()
            if action == 'exit':
                break
            continue

        first_output_dir = os.path.join(os.path.dirname(videos[0]), "Output", "Frames")
        os.makedirs(first_output_dir, exist_ok=True)
        logger = djj.setup_logging(first_output_dir, "video_frame_extractor")

        # ── Mode 1: interval ──────────────────────────────────────────────────
        if mode == '1':
            frame_interval = prompt_integer(
                "🔢 Frame interval (e.g. 10 = every 10th frame)", min_value=1
            )
            print()
            output_base_dirs = extract_frames_interval(videos, frame_interval, logger)
            _print_summary(len(videos), f"interval every {frame_interval} frames", output_base_dirs)

        # ── Mode 2: target count ──────────────────────────────────────────────
        else:
            target_count = prompt_integer(
                "🔢 How many frames to extract per video", min_value=1
            )
            print()
            output_base_dirs = extract_frames_count(videos, target_count, logger)
            _print_summary(len(videos), f"target {target_count} frames evenly spread", output_base_dirs)

        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()