import os
import sys
import pathlib
import subprocess
import json
import logging
from pathlib import Path
import shlex
import djjtb.utils as djj

os.system('clear')

VIDEO_EXTS = ('.mp4', '.mkv', '.webm', '.mov')


def prompt_integer(prompt, min_value=1):
    while True:
        try:
            value = int(input(f"{prompt}: ").strip())
            if value >= min_value:
                return value
            else:
                print(f"\033[93mPlease enter a number >= {min_value}.\033[0m")
        except ValueError:
            print("\033[93mInvalid input. Please enter a number.\033[0m")


# ── Video info ────────────────────────────────────────────────────────────────

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


def probe_all_videos(videos):
    """
    Probe all videos and return a list of dicts with info.
    Shows a progress indicator while probing.
    """
    print("\033[93m🔍 Probing videos...\033[0m")
    results = []
    for i, v in enumerate(videos, 1):
        sys.stdout.write(f"\r  {i}/{len(videos)}...")
        sys.stdout.flush()
        nb_frames, duration, fps = get_video_info(v)
        results.append({
            'path': v,
            'name': v.name,
            'nb_frames': nb_frames,
            'duration': duration,
            'fps': fps,
        })
    sys.stdout.write(f"\r{' ' * 30}\r")
    sys.stdout.flush()
    return results


def format_duration(seconds):
    """Format seconds as Xm Ys or Xs."""
    if seconds >= 60:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}m {s:02d}s"
    return f"{seconds:.1f}s"


def display_probe_table(probe_results):
    """Display a formatted table of video info."""
    print()
    print(f"  {'#':>3}  {'Filename':<40}  {'Frames':>8}  {'Duration':>8}  {'FPS':>6}")
    print(f"  {'─'*3}  {'─'*40}  {'─'*8}  {'─'*8}  {'─'*6}")
    for i, r in enumerate(probe_results, 1):
        name = r['name']
        if len(name) > 40:
            name = name[:37] + '...'
        frames = f"{r['nb_frames']:,}" if r['nb_frames'] else '?'
        dur = format_duration(r['duration']) if r['duration'] else '?'
        fps = f"{r['fps']:.2f}" if r['fps'] else '?'
        print(f"  {i:>3}. {name:<40}  {frames:>8}  {dur:>8}  {fps:>6}")
    print()


# ── Input collection helpers ──────────────────────────────────────────────────

def parse_finder_paths(raw_input):
    raw_input = raw_input.strip()
    try:
        parts = shlex.split(raw_input)
    except ValueError:
        parts = [p.strip('\'"') for p in raw_input.split()]
    return [pathlib.Path(part).expanduser().resolve() for part in parts]


def collect_videos_from_folder(folder_path, include_sub=False):
    folder = pathlib.Path(folder_path)
    videos = []
    if include_sub:
        for root, _, files in os.walk(folder):
            for f in files:
                if pathlib.Path(f).suffix.lower() in VIDEO_EXTS:
                    videos.append(pathlib.Path(root) / f)
    else:
        videos = [f for f in folder.glob('*')
                  if f.suffix.lower() in VIDEO_EXTS and f.is_file()]
    return sorted(videos, key=lambda p: str(p).lower())


def collect_videos_from_paths(raw_input, include_sub=False):
    paths = parse_finder_paths(raw_input)
    videos = []
    for p in paths:
        if not p.exists():
            print(f"\033[93m⚠️  Path not found, skipping: {p}\033[0m")
            continue
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS:
            videos.append(p)
        elif p.is_dir():
            videos.extend(collect_videos_from_folder(p, include_sub))
    return sorted(videos, key=lambda p: str(p).lower())


def collect_videos_from_txt(include_sub=False):
    paths = djj.get_paths_from_txt("Enter txt file path")
    if not paths:
        return []
    videos = []
    for path in paths:
        p = pathlib.Path(path)
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS:
            videos.append(p)
        elif p.is_dir():
            videos.extend(collect_videos_from_folder(p, include_sub))
    return sorted(set(videos), key=lambda p: str(p).lower())


# ── Output folder helpers ─────────────────────────────────────────────────────

def resolve_session_dirs(videos, session_name):
    """
    Pre-compute ONE session folder per unique parent folder.
    Auto-renames (_2, _3) only if folder already has content from a previous run.
    Returns dict: { parent_path: session_dir }
    """
    session_map = {}
    for video_path in videos:
        parent = Path(video_path).parent
        if parent in session_map:
            continue
        base = parent / "Output" / session_name
        candidate = base
        counter = 2
        while candidate.exists() and any(candidate.iterdir()):
            candidate = base.parent / f"{base.name}_{counter}"
            counter += 1
        candidate.mkdir(parents=True, exist_ok=True)
        session_map[parent] = candidate
    return session_map


def make_video_output_dir(session_dir, video_stem):
    out = session_dir / video_stem
    out.mkdir(parents=True, exist_ok=True)
    return out


# ── Frame-accurate renaming ───────────────────────────────────────────────────

def rename_frames_interval(output_dir, video_stem, frame_interval, nb_frames):
    """
    Rename sequentially-numbered ffmpeg output to actual frame numbers.
    ffmpeg outputs F0001, F0002, F0003...
    We rename to F0001, F0005, F0009... (for interval 4, 1-indexed actual frames)
    """
    files = sorted([f for f in os.listdir(output_dir) if f.endswith('.jpg')])
    # Actual frame indices (0-based): 0, interval, 2*interval...
    # Display as 1-based: 1, interval+1, 2*interval+1...
    for seq_idx, filename in enumerate(files):
        actual_frame_1based = seq_idx * frame_interval + 1
        new_name = f"{video_stem}_F{actual_frame_1based:04d}.jpg"
        old_path = os.path.join(output_dir, filename)
        new_path = os.path.join(output_dir, new_name)
        if old_path != new_path:
            os.rename(old_path, new_path)


def rename_frames_count(output_dir, video_stem, indices):
    """
    Rename sequentially-numbered ffmpeg output to actual frame numbers.
    indices: list of 0-based frame indices that were extracted.
    Display as 1-based.
    """
    files = sorted([f for f in os.listdir(output_dir) if f.endswith('.jpg')])
    for seq_idx, filename in enumerate(files):
        if seq_idx >= len(indices):
            break
        actual_frame_1based = indices[seq_idx] + 1
        new_name = f"{video_stem}_F{actual_frame_1based:04d}.jpg"
        old_path = os.path.join(output_dir, filename)
        new_path = os.path.join(output_dir, new_name)
        if old_path != new_path:
            os.rename(old_path, new_path)


# ── Mode 1: interval-based ────────────────────────────────────────────────────

def extract_frames_interval(probe_results, frame_interval, logger):
    """
    Extract every Nth frame.
    Output: <video_parent>/Output/Frames_<interval>/<video_stem>/
    Files named by actual frame number: video_F0001.jpg, video_F0005.jpg...
    """
    videos = [r['path'] for r in probe_results]
    session_name = f"Frames_{frame_interval}"
    session_map = resolve_session_dirs(videos, session_name)
    output_session_dirs = []
    total = len(probe_results)

    for i, r in enumerate(probe_results, 1):
        video_path = r['path']
        video_name = video_path.stem
        nb_frames = r['nb_frames']
        progress = (i / total) * 100
        sys.stdout.write(f"\r\033[93mExtracting \033[0m{i}/{total} ({progress:.0f}%)...")
        sys.stdout.flush()

        session_dir = session_map[video_path.parent]
        output_dir = make_video_output_dir(session_dir, video_name)

        try:
            total_images = max(1, int(nb_frames / frame_interval))
            if total_images > 3000:
                sys.stdout.write(f"\r{' ' * 60}\r")
                sys.stdout.flush()
                print(f"\n\033[93mWarning: ~{total_images} images from {video_name}.\033[0m")
                proceed = djj.prompt_choice("\033[93mProceed?\033[0m\n1. Yes\n2. Skip", ['1', '2'], default='2')
                if proceed != '1':
                    logger.info(f"Skipped {video_name} (user choice)")
                    output_session_dirs.append(session_dir)
                    continue
        except Exception as e:
            logger.error(f"Error estimating frames for {video_path}: {e}")

        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-vf', f'select=not(mod(n\\,{frame_interval}))',
            '-vsync', '0', '-q:v', '2',
            f'{output_dir}/{video_name}_tmp%04d.jpg'
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            rename_frames_interval(output_dir, video_name, frame_interval, nb_frames)
            extracted = len([f for f in os.listdir(output_dir) if f.endswith('.jpg')])
            logger.info(f"Extracted {extracted} frames for {video_name} to {output_dir}")
        except subprocess.CalledProcessError as e:
            sys.stdout.write(f"\r{' ' * 60}\r")
            sys.stdout.flush()
            print(f"\033[93mError processing {video_name}: {e.stderr}\033[0m")
            logger.error(f"Error processing {video_name}: {e.stderr}")

        output_session_dirs.append(session_dir)

    return output_session_dirs


# ── Mode 2: target count — evenly spread ─────────────────────────────────────

def extract_frames_count(probe_results, target_count, logger):
    """
    Extract exactly N evenly-spaced frames per video.
    Output: <video_parent>/Output/Frames_<count>x/<video_stem>/
    Files named by actual frame number: video_F0001.jpg, video_F0247.jpg...
    """
    videos = [r['path'] for r in probe_results]
    session_name = f"Frames_{target_count}x"
    session_map = resolve_session_dirs(videos, session_name)
    output_session_dirs = []
    total = len(probe_results)

    for i, r in enumerate(probe_results, 1):
        video_path = r['path']
        video_name = video_path.stem
        nb_frames = r['nb_frames']
        progress = (i / total) * 100
        sys.stdout.write(f"\r\033[93mExtracting \033[0m{i}/{total} ({progress:.0f}%)...")
        sys.stdout.flush()

        session_dir = session_map[video_path.parent]
        output_dir = make_video_output_dir(session_dir, video_name)

        if nb_frames == 0:
            sys.stdout.write(f"\r{' ' * 60}\r")
            print(f"\033[93m❌ Could not get frame count for {video_name}, skipping.\033[0m")
            logger.error(f"Could not get frame count for {video_name}")
            continue

        actual_count = min(target_count, nb_frames)
        if actual_count < target_count:
            sys.stdout.write(f"\r{' ' * 60}\r")
            print(f"\033[93m⚠️  {video_name}: only {nb_frames} frames, extracting {actual_count}.\033[0m")
            sys.stdout.flush()

        if actual_count == 1:
            indices = [nb_frames // 2]
        else:
            step = (nb_frames - 1) / (actual_count - 1)
            indices = [round(step * j) for j in range(actual_count)]

        select_expr = "+".join(f"eq(n\\,{idx})" for idx in indices)

        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-vf', f'select={select_expr}',
            '-vsync', '0', '-q:v', '2',
            f'{output_dir}/{video_name}_tmp%04d.jpg'
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            rename_frames_count(output_dir, video_name, indices)
            extracted = len([f for f in os.listdir(output_dir) if f.endswith('.jpg')])
            logger.info(f"Extracted {extracted}/{actual_count} frames for {video_name} to {output_dir}")
        except subprocess.CalledProcessError as e:
            sys.stdout.write(f"\r{' ' * 60}\r")
            sys.stdout.flush()
            print(f"\033[93mError processing {video_name}: {e.stderr}\033[0m")
            logger.error(f"Error processing {video_name}: {e.stderr}")

        output_session_dirs.append(session_dir)

    return output_session_dirs


# ── Summary ───────────────────────────────────────────────────────────────────

def _print_summary(total_videos, mode_label, output_session_dirs):
    sys.stdout.write(f"\r{' ' * 60}\r")
    sys.stdout.flush()
    unique_sessions = list(dict.fromkeys(str(d) for d in output_session_dirs))
    print()
    print("\033[93mFrame Extraction Summary\033[0m")
    print("------------------------")
    print(f"\033[93mVideos processed:\033[0m {total_videos}")
    print(f"\033[93mMode:\033[0m {mode_label}")
    print(f"\033[93mOutput session(s):\033[0m {len(unique_sessions)}")
    print()
    if output_session_dirs:
        djj.prompt_open_folder(str(output_session_dirs[-1]))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    while True:
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mFrame Extractor\033[0m")
        print("Extract frames from videos")
        print("\033[92m==================================================\033[0m")
        print()

        # ── Input mode ───────────────────────────────────────────────────────
        input_mode = djj.prompt_choice(
            "\033[93mInput mode:\033[0m\n"
            "1. Folder path\n"
            "2. Multiple files / folders (space-separated or Finder drag)\n"
            "3. Path list from txt file\n",
            ['1', '2', '3'],
            default='1'
        )
        print()

        videos = []

        if input_mode == '1':
            parent_folder = djj.get_path_input("📁 Enter folder path")
            print()
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'], default='2'
            ) == '1'
            print()
            videos = collect_videos_from_folder(parent_folder, include_sub)

        elif input_mode == '2':
            raw = input("📁 \033[93mEnter or drag paths here:\n\033[0m -> ").strip()
            if not raw:
                print("❌ \033[93mNo paths provided.\033[0m")
                continue
            print()
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders (for any folder paths)?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'], default='2'
            ) == '1'
            print()
            videos = collect_videos_from_paths(raw, include_sub)

        else:
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders (for any folder paths)?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'], default='2'
            ) == '1'
            print()
            videos = collect_videos_from_txt(include_sub)

        if not videos:
            print("\033[93m⚠️  No video files found. Try again.\033[0m\n")
            action = djj.what_next()
            if action == 'exit':
                break
            continue

        videos = [v for v in videos if not v.name.startswith('.')]

        # ── Probe all videos and show table ──────────────────────────────────
        probe_results = probe_all_videos(videos)
        display_probe_table(probe_results)

        # ── Extraction mode ──────────────────────────────────────────────────
        mode = djj.prompt_choice(
            "🎬 Extraction mode?\n1. Interval  (every Nth frame)\n2. Target count  (N frames evenly spread)",
            ['1', '2'], default='1'
        )
        print()

        # Logger sits in Output beside the first video
        first_output_dir = videos[0].parent / "Output"
        first_output_dir.mkdir(parents=True, exist_ok=True)
        logger = djj.setup_logging(str(first_output_dir), "video_frame_extractor")

        if mode == '1':
            frame_interval = prompt_integer(
                "🔢 Frame interval (e.g. 10 = every 10th frame)", min_value=1
            )
            print()
            output_session_dirs = extract_frames_interval(probe_results, frame_interval, logger)
            _print_summary(len(videos), f"interval every {frame_interval} frames", output_session_dirs)

        else:
            target_count = prompt_integer(
                "🔢 How many frames to extract per video", min_value=1
            )
            print()
            output_session_dirs = extract_frames_count(probe_results, target_count, logger)
            _print_summary(len(videos), f"target {target_count} frames evenly spread", output_session_dirs)

        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()
