import os
import sys
import subprocess
import pathlib
import json
import logging
import shlex
from pathlib import Path
from datetime import datetime
import djjtb.utils as djj

os.system('clear')

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
LOG_DIR = Path("~/Documents/Scripts/DJJTB/djjtb/logs").expanduser()
LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_op_logger(op_name):
    log_file = LOG_DIR / f"video_frame_bridge_{op_name}_log.txt"
    logger = logging.getLogger(f'djjtb.video_frame_bridge.{op_name}')
    logger.setLevel(logging.INFO)
    logger.handlers = []
    logger.propagate = False
    handler = logging.FileHandler(log_file, mode='a')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)
    logger.info(f"===== RUN START: {op_name} =====")
    return logger


# ══════════════════════════════════════════════════════════════════════════
# Mode 1: Video → Frames
# ══════════════════════════════════════════════════════════════════════════

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
    """Folder walking delegates to djj.collect_videos_from_folder; wrapped
    back into Path objects since the rest of this file relies on
    .stem/.parent/.name on every collected video throughout."""
    return sorted(
        (Path(p) for p in djj.collect_videos_from_folder(str(folder_path), include_subfolders=include_sub)),
        key=lambda p: str(p).lower()
    )


def collect_videos_from_paths(raw_input, include_sub=False):
    paths = parse_finder_paths(raw_input)
    videos = []
    for p in paths:
        if not p.exists():
            print(f"\033[93m⚠️  Path not found, skipping: {p}\033[0m")
            continue
        if p.is_file() and p.suffix.lower() in djj.VIDEO_EXTENSIONS:
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
        if p.is_file() and p.suffix.lower() in djj.VIDEO_EXTENSIONS:
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


# ── Extraction: interval-based ────────────────────────────────────────────────

def extract_frames_interval_one(video_path, nb_frames, frame_interval, session_dir, allow_large=False, logger=None):
    """Pure single-video interval extraction, extracted 2026-07-28 from
    extract_frames_interval()'s inline loop body so djjtb-suite's backend can call the same
    code the CLI does (see djjtb-suite's CLAUDE.md 'Source of truth' section) -- same reasoning
    as video_processor.py's reencode_one()/speed_change_one()/crop_one().

    Does NOT prompt. If the estimated output would exceed 3000 images and `allow_large` is
    False, returns status "skipped_large" *without* running ffmpeg -- the CLI wrapper below
    prompts interactively on that status and retries with allow_large=True if the user says
    yes; djjtb-suite's backend treats it as a per-item skip (its "hard-skip with an optional
    force checkbox" default, chosen deliberately over exposing the CLI's interactive prompt).

    Returns a dict: {status: "success"|"skipped_large"|"error", output_dir, ...}.
    """
    video_name = video_path.stem
    output_dir = make_video_output_dir(session_dir, video_name)

    total_images = None
    try:
        total_images = max(1, int(nb_frames / frame_interval))
    except Exception as e:
        if logger:
            logger.error(f"Error estimating frames for {video_path}: {e}")

    if total_images and total_images > 3000 and not allow_large:
        return {"status": "skipped_large", "output_dir": output_dir, "estimated_count": total_images}

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
        if logger:
            logger.info(f"Extracted {extracted} frames for {video_name} to {output_dir}")
        return {"status": "success", "output_dir": output_dir, "extracted_count": extracted}
    except subprocess.CalledProcessError as e:
        if logger:
            logger.error(f"Error processing {video_name}: {e.stderr}")
        return {"status": "error", "output_dir": output_dir, "error": e.stderr}


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

        result = extract_frames_interval_one(video_path, nb_frames, frame_interval, session_dir, allow_large=False, logger=logger)

        if result["status"] == "skipped_large":
            sys.stdout.write(f"\r{' ' * 60}\r")
            sys.stdout.flush()
            print(f"\n\033[93mWarning: ~{result['estimated_count']} images from {video_name}.\033[0m")
            proceed = djj.prompt_choice("\033[93mProceed?\033[0m\n1. Yes\n2. Skip", ['1', '2'], default='2')
            if proceed == '1':
                result = extract_frames_interval_one(video_path, nb_frames, frame_interval, session_dir, allow_large=True, logger=logger)
            else:
                logger.info(f"Skipped {video_name} (user choice)")
                output_session_dirs.append(session_dir)
                continue

        if result["status"] == "error":
            sys.stdout.write(f"\r{' ' * 60}\r")
            sys.stdout.flush()
            print(f"\033[93mError processing {video_name}: {result['error']}\033[0m")

        output_session_dirs.append(session_dir)

    return output_session_dirs


# ── Extraction: target count — evenly spread ─────────────────────────────────

def extract_frames_count_one(video_path, nb_frames, target_count, session_dir, logger=None):
    """Pure single-video target-count extraction, extracted 2026-07-28 -- same reasoning as
    extract_frames_interval_one() above. No interactive branch in this mode (unlike interval
    mode), so this one's a straight extraction, no allow_large equivalent needed.

    Returns a dict: {status: "success"|"no_frame_count"|"error", output_dir, ...}.
    """
    video_name = video_path.stem
    output_dir = make_video_output_dir(session_dir, video_name)

    if nb_frames == 0:
        if logger:
            logger.error(f"Could not get frame count for {video_name}")
        return {"status": "no_frame_count", "output_dir": output_dir}

    actual_count = min(target_count, nb_frames)
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
        if logger:
            logger.info(f"Extracted {extracted}/{actual_count} frames for {video_name} to {output_dir}")
        return {"status": "success", "output_dir": output_dir, "extracted_count": extracted, "actual_count": actual_count}
    except subprocess.CalledProcessError as e:
        if logger:
            logger.error(f"Error processing {video_name}: {e.stderr}")
        return {"status": "error", "output_dir": output_dir, "error": e.stderr, "actual_count": actual_count}


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

        result = extract_frames_count_one(video_path, nb_frames, target_count, session_dir, logger=logger)

        if result["status"] == "error":
            sys.stdout.write(f"\r{' ' * 60}\r")
            sys.stdout.flush()
            print(f"\033[93mError processing {video_name}: {result['error']}\033[0m")

        output_session_dirs.append(session_dir)

    return output_session_dirs


def _print_extraction_summary(total_videos, mode_label, output_session_dirs):
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


def run_video_to_frames():
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
            return
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
        print("\033[93m⚠️  No video files found.\033[0m\n")
        return

    videos = [v for v in videos if not v.name.startswith('.')]

    probe_results = probe_all_videos(videos)
    display_probe_table(probe_results)

    mode = djj.prompt_choice(
        "🎬 Extraction mode?\n1. Interval  (every Nth frame)\n2. Target count  (N frames evenly spread)",
        ['1', '2'], default='1'
    )
    print()

    logger = get_op_logger("extract")

    if mode == '1':
        frame_interval = prompt_integer(
            "🔢 Frame interval (e.g. 10 = every 10th frame)", min_value=1
        )
        print()
        output_session_dirs = extract_frames_interval(probe_results, frame_interval, logger)
        _print_extraction_summary(len(videos), f"interval every {frame_interval} frames", output_session_dirs)
    else:
        target_count = prompt_integer(
            "🔢 How many frames to extract per video", min_value=1
        )
        print()
        output_session_dirs = extract_frames_count(probe_results, target_count, logger)
        _print_extraction_summary(len(videos), f"target {target_count} frames evenly spread", output_session_dirs)


# ══════════════════════════════════════════════════════════════════════════
# Mode 2: Frames → Video
# ══════════════════════════════════════════════════════════════════════════

def collect_images_from_txt():
    """Collect images from a txt file of paths."""
    paths = djj.get_paths_from_txt("📄 Enter txt file path")
    if not paths:
        return []
    images = []
    for path in paths:
        path_obj = pathlib.Path(path)
        if path_obj.is_file() and path_obj.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(str(path))
        elif path_obj.is_dir():
            images.extend(djj.collect_images_from_folder(str(path), extensions=IMAGE_EXTENSIONS))
    return sorted(set(images), key=lambda x: x.lower())


def collect_subfolders_with_images(parent_path):
    """
    Scan immediate subfolders of parent_path.
    Returns dict: {subfolder_path: [sorted image paths]}
    Only includes subfolders that actually contain images.
    """
    parent = pathlib.Path(parent_path)
    grouped = {}

    for subfolder in sorted(parent.iterdir()):
        if subfolder.is_dir():
            images = sorted(
                [str(f) for f in subfolder.glob('*') if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS],
                key=lambda x: x.lower()
            )
            if images:
                grouped[str(subfolder)] = images

    return grouped


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


def compile_images_to_video(images, fps, audio_mode, audio_ref_path, output_file):
    """
    Compile a sorted list of images into a video using ffmpeg.

    Audio modes:
        'none'      - no audio stream
        'silent'    - silent AAC audio track
        'reference' - audio extracted from reference video, looped if short, trimmed to video length
    """
    list_file = output_file.replace('.mp4', '_input_list.txt')
    duration_per_frame = 1.0 / fps

    with open(list_file, 'w') as f:
        for img in images:
            f.write(f"file '{img}'\n")
            f.write(f"duration {duration_per_frame}\n")
        f.write(f"file '{images[-1]}'\n")

    video_duration = len(images) * duration_per_frame

    cmd = ["ffmpeg", "-y"]

    if audio_mode == 'reference':
        cmd += [
            "-f", "concat", "-safe", "0", "-i", list_file,
            "-stream_loop", "-1", "-i", audio_ref_path,
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

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        success = True
        error = None
    except subprocess.CalledProcessError as e:
        success = False
        error = e.stderr
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)

    return success, error, video_duration


def run_frames_to_video():
    logger = get_op_logger("compile")

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
                return
            total_images = sum(len(v) for v in subfolder_groups.values())
            print(f"✅ \033[93m{len(subfolder_groups)} subfolder(s) found — {total_images} images total\033[0m")
            for sf, imgs in subfolder_groups.items():
                print(f"   📁 {os.path.basename(sf)}  ({len(imgs)} images)")
            print()
        else:
            images = djj.collect_images_from_folder(folder_path, extensions=IMAGE_EXTENSIONS)

    elif input_mode == '2':
        raw = input("📁 \033[93mEnter image paths (space-separated):\033[0m\n -> ").strip()
        if not raw:
            print("❌ \033[93mNo paths provided.\033[0m")
            return
        images = djj.collect_images_from_paths(raw, extensions=IMAGE_EXTENSIONS)

    else:
        images = collect_images_from_txt()

    if not subfolder_mode:
        if not images:
            print("\033[1;5;93m❌ No valid image files found.\033[0m\n")
            return

        if not folder_path:
            folder_path = str(pathlib.Path(images[0]).parent)

        print(f"\n✅ \033[93m{len(images)} image(s) found\033[0m")

        dims = get_image_dimensions(images[0])
        if dims:
            print(f"📐 \033[93mDetected resolution:\033[0m {dims[0]}x{dims[1]} (from first image)")
        else:
            print("\033[93m⚠️  Could not detect resolution — ffmpeg will use source dimensions\033[0m")
        print()
    else:
        first_images = list(subfolder_groups.values())[0]
        dims = get_image_dimensions(first_images[0])
        if dims:
            print(f"📐 \033[93mDetected resolution:\033[0m {dims[0]}x{dims[1]} (from first image of first subfolder)")
        print()

    fps = djj.get_int_input(
        "🎬 \033[93mFrame rate (1–120 fps):\033[0m\n"
        "   Examples: 1 = 1 image/sec  |  24/30/60 = smooth video\n"
        "   Enter fps",
        min_val=1,
        max_val=120
    )
    print()

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
        ref_duration = get_audio_duration(audio_ref_path)
        if ref_duration:
            if ref_duration < video_duration_preview:
                print(f"\033[93m⚠️  Reference audio ({ref_duration:.1f}s) is shorter than video ({video_duration_preview:.1f}s) — will loop\033[0m")
            elif ref_duration > video_duration_preview:
                print(f"\033[93m✂️  Reference audio ({ref_duration:.1f}s) is longer than video ({video_duration_preview:.1f}s) — will trim\033[0m")
            else:
                print(f"\033[92m✅ Audio and video durations match\033[0m")
        print()

    audio_label = {'none': 'No audio', 'silent': 'Silent track', 'reference': 'From reference video'}[audio_mode]

    if subfolder_mode:
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
                logger.info(f"Compiled {sf_name} ({len(sf_images)} frames) to {output_file}")
            else:
                print(f"   \033[91m❌ Failed\033[0m")
                if error:
                    error_lines = [l for l in error.strip().split('\n') if l.strip()]
                    for line in error_lines[-2:]:
                        print(f"      \033[93m{line}\033[0m")
                all_errors.append(sf_name)
                logger.error(f"Failed to compile {sf_name}: {error}")

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

        logger.info(f"Compiled {len(all_outputs)} of {len(subfolder_groups)} subfolder videos successfully")

        if all_outputs:
            top_output_dir = os.path.join(parent_resolved, "Output", "VideoCompiler")
            print(f"\n\033[92m✅ Done! Output folder: {top_output_dir}\033[0m")
            djj.prompt_open_folder(top_output_dir)

    else:
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
            logger.info(f"Compiled {len(images)} images to {output_file}")
            djj.prompt_open_folder(output_dir)
        else:
            print(f"\n\033[91m❌ Compile failed.\033[0m")
            logger.error(f"Compile failed for {folder_path_resolved}: {error}")
            if error:
                error_lines = [l for l in error.strip().split('\n') if l.strip()]
                for line in error_lines[-4:]:
                    print(f"   \033[93m{line}\033[0m")


# ══════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════

def main():
    while True:
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mVideo ⟷ Frame Bridge\033[0m")
        print("Extract frames from video, or compile frames into video")
        print("\033[92m==================================================\033[0m")
        print()

        mode = djj.prompt_choice(
            "\033[93mMode:\033[0m\n1. Video → Frames\n2. Frames → Video\n",
            ['1', '2'], default='1'
        )
        print()

        if mode == '1':
            run_video_to_frames()
        else:
            run_frames_to_video()

        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()
