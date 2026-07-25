import os
import sys
import csv
import subprocess
import logging
from pathlib import Path
from datetime import datetime
import djjtb.utils as djj

os.system('clear')

LOG_DIR = Path("~/Documents/Scripts/DJJTB/djjtb/logs").expanduser()
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ─── Shared: logging ───────────────────────────────────────────────────────

def get_op_logger(op_name):
    log_file = LOG_DIR / f"video_processor_{op_name}_log.txt"
    logger = logging.getLogger(f'djjtb.video_processor.{op_name}')
    logger.setLevel(logging.INFO)
    logger.handlers = []
    logger.propagate = False
    handler = logging.FileHandler(log_file, mode='a')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)
    logger.info(f"===== RUN START: {op_name} =====")
    return logger


# ─── Shared: video collection ──────────────────────────────────────────────

def collect_videos_from_folder(input_path, subfolders=False):
    """
    Folder walking delegates to djj.collect_videos_from_folder (dedup target).
    Kept local: accepting a bare file path as input_path (safety net for
    when djj.get_path_input's "Enter folder path" prompt gets a file path
    instead), and returning Path objects — the rest of this file relies on
    .stem/.parent/.name throughout run_reencode/run_speed_change/run_crop.
    """
    input_path_obj = Path(input_path).expanduser().resolve()
    if input_path_obj.is_file() and input_path_obj.suffix.lower() in djj.VIDEO_EXTENSIONS:
        videos = [input_path_obj]
    elif input_path_obj.is_dir():
        videos = [Path(p) for p in djj.collect_videos_from_folder(str(input_path_obj), include_subfolders=subfolders)]
    else:
        print("\033[91mError: Input must be a video file or directory.\033[0m", file=sys.stderr)
        return []

    if not videos:
        print("\033[93mError: No video files found.\033[0m", file=sys.stderr)
    return sorted(videos, key=lambda x: str(x).lower())


def collect_videos_from_paths(raw_input):
    """
    Not delegated to djj.collect_videos_from_paths: that function expands
    directories found in the input, but this mode is explicitly file-paths-
    only (its prompt says so) and warns + skips any directory it's handed
    instead — a deliberate behavior difference, not something to dedup away.
    Only the extension list comes from djj now.
    """
    videos = []
    for path_str in raw_input.strip().split():
        path_obj = Path(path_str.strip('\'"')).expanduser().resolve()
        if path_obj.is_file() and path_obj.suffix.lower() in djj.VIDEO_EXTENSIONS:
            videos.append(path_obj)
        elif path_obj.is_dir():
            print(f"\033[93m⚠️ Skipping directory in file list:\033[0m {path_str}")
        else:
            print(f"\033[93m⚠️ Skipping invalid video file:\033[0m {path_str}")

    if not videos:
        print("\033[93mError: No video files found.\033[0m", file=sys.stderr)
    return sorted(videos, key=lambda x: str(x).lower())


def get_videos_input():
    """Shared folder/paths input picker used by all three modes."""
    input_mode = djj.prompt_choice(
        "\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
        ['1', '2'], default='1'
    )
    print()
    if input_mode == '1':
        input_path = djj.get_path_input("📁 Enter folder path")
        print()
        include_sub = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes, 2. No", ['1', '2'], default='2'
        ) == '1'
        print()
        return collect_videos_from_folder(input_path, include_sub)
    else:
        file_paths = input("📁 \033[93mEnter space-separated file paths: \n ->\033[0m ").strip()
        print()
        if not file_paths:
            print("\033[93mNo file paths provided.\033[0m")
            return []
        return collect_videos_from_paths(file_paths)


def get_audio_choice():
    print("\033[93mAudio options:\033[0m")
    print("1. Keep original audio")
    print("2. Strip audio")
    print("3. Add silent track")
    choice = djj.prompt_choice("Choose audio option: \n ", ['1', '2', '3'], default='1')
    print()
    return choice


# ─── Mode 1: Re-encode ──────────────────────────────────────────────────────

def run_reencode(videos):
    print("\033[93mChoose codec:\033[0m\n1. H.264\n2. H.265\n3. Copy container only (no re-encoding)")
    codec_choice = djj.prompt_choice("", ['1', '2', '3'], default='1')
    print()

    if codec_choice == '1':
        codec, crf, suffix, tag = "libx264", "23", "_reencoded", ""
        print("\033[93mRe-encoding with H.264...\033[0m")
    elif codec_choice == '2':
        codec, crf, suffix, tag = "libx265", "28", "_hevc", "-tag:v hvc1"
        print("\033[93mRe-encoding with H.265...\033[0m")
    else:
        codec, crf, suffix, tag = "copy", None, "_copy", ""
        print("\033[93mCopying container without re-encoding...\033[0m")

    audio_choice = get_audio_choice()

    output_base_dirs = []
    total = len(videos)
    successful = 0
    logger = get_op_logger("reencode")

    for i, video_path in enumerate(videos, 1):
        out_dir = video_path.parent / "Output" / "Reencoded"
        out_dir.mkdir(parents=True, exist_ok=True)
        output = out_dir / f"{video_path.stem}{suffix}.mp4"

        default_stream = "0"
        if audio_choice != '3':
            try:
                default_stream = subprocess.run([
                    "ffprobe", "-v", "error", "-show_entries", "stream=index:disposition=default",
                    "-of", "csv=p=0", "-select_streams", "v", str(video_path)
                ], capture_output=True, text=True).stdout.strip().split(',')[0]
                if not default_stream:
                    default_stream = subprocess.run([
                        "ffprobe", "-v", "error", "-show_entries", "stream=index",
                        "-of", "csv=p=0", "-select_streams", "v", str(video_path)
                    ], capture_output=True, text=True).stdout.strip().split('\n')[0]
            except Exception as e:
                logger.error(f"Error getting stream info for {video_path.name}: {e}")

        progress = (i / total) * 100
        sys.stdout.write(f"\033[93m\rProcessing \033[0m{i}/{total} ({progress:.1f}%)...")
        sys.stdout.flush()

        if codec == "copy":
            cmd = ["ffmpeg", "-i", str(video_path), "-c", "copy", "-y", str(output)]
        else:
            cmd = ["ffmpeg", "-i", str(video_path)]
            if audio_choice != '3':
                cmd.extend(["-map", f"0:v:{default_stream}"])
            cmd.extend(djj.get_audio_options(audio_choice))
            cmd.extend(["-c:v", codec, "-preset", "medium", "-crf", crf])
            if tag:
                cmd.extend(tag.split())
            cmd.extend(["-y", str(output)])

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Re-encoded {video_path.name} to {output}")
            successful += 1
        except subprocess.CalledProcessError as e:
            logger.error(f"Error re-encoding {video_path.name}: {e.stderr}")
            print(f"\n\033[93mError re-encoding {video_path.name}: {e.stderr}\033[0m")

        if out_dir not in output_base_dirs:
            output_base_dirs.append(out_dir)

        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()

    summary = f"Re-encoded {successful} of {total} videos successfully"
    logger.info(summary)
    print("\n\033[93mRe-encoding Summary\033[0m")
    print("-------------------")
    print(f"\033[93mVideos processed:\033[0m {total}")
    print(f"\033[93mVideos successfully re-encoded:\033[0m {successful}")
    print(f"\033[93mOutput folder(s):\033[0m {', '.join(str(d) for d in output_base_dirs)}")
    print()
    djj.prompt_open_folder(str(output_base_dirs[0]))


# ─── Mode 2: Speed Change ───────────────────────────────────────────────────

def get_atempo_chain(speed):
    if speed == 1.0:
        return ""
    filters = []
    remaining_speed = speed
    while remaining_speed > 2.0:
        filters.append("atempo=2.0")
        remaining_speed /= 2.0
    while remaining_speed < 0.5:
        filters.append("atempo=0.5")
        remaining_speed /= 0.5
    if remaining_speed != 1.0:
        filters.append(f"atempo={remaining_speed}")
    return ",".join(filters)


def run_speed_change(videos):
    while True:
        try:
            speed = float(input("Enter the playback speed multiplier\n(e.g., 0.5, 2.0): ").strip())
            print()
            if speed <= 0:
                print("Speed must be a positive number.")
                continue
            break
        except ValueError:
            print("Please enter a valid number.")

    overwrite = djj.prompt_choice("Overwrite existing output files?\n 1. Yes, 2. No ", ['1', '2'], default='2')
    print()

    single_output = len(videos) == 1 or all(v.parent == videos[0].parent for v in videos)
    base_dir = videos[0].parent / "Output" / "Speed_Adjusted"
    base_dir.mkdir(parents=True, exist_ok=True)
    logger = get_op_logger("speed")

    output_base_dirs = []
    total = len(videos)

    for i, video_path in enumerate(videos, 1):
        if single_output:
            current_output_dir = base_dir
        else:
            current_output_dir = video_path.parent / "Output" / "Speed_Adjusted"
            current_output_dir.mkdir(parents=True, exist_ok=True)

        output = current_output_dir / f"{video_path.stem}_{speed}x{video_path.suffix}"

        if output.exists() and overwrite != '1':
            logger.info(f"Skipped {video_path.stem} (file exists)")
            continue

        try:
            audio_stream = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                "-of", "csv=p=0", "-select_streams", "a", str(video_path)
            ], capture_output=True, text=True).stdout.strip()
            audio_exists = "audio" in audio_stream
        except subprocess.CalledProcessError:
            audio_exists = False

        pts = 1 / speed
        progress = (i / total) * 100
        sys.stdout.write(f"\rProcessing {i}/{total} ({progress:.1f}%)...")
        sys.stdout.flush()

        try:
            if audio_exists:
                atempo = get_atempo_chain(speed)
                cmd = [
                    "ffmpeg", "-i", str(video_path),
                    "-filter_complex", f"[0:v]setpts={pts}*PTS[v];[0:a]{atempo}[a]",
                    "-map", "[v]", "-map", "[a]", "-loglevel", "quiet", "-y", str(output)
                ]
            else:
                cmd = [
                    "ffmpeg", "-i", str(video_path),
                    "-filter:v", f"setpts={pts}*PTS",
                    "-an", "-loglevel", "quiet", "-y", str(output)
                ]
            subprocess.run(cmd, check=True)
            logger.info(f"Speed adjusted {video_path.stem} to {speed}x -> {output}")
        except subprocess.CalledProcessError:
            logger.error(f"Error processing {video_path.stem}: FFmpeg failed to adjust speed")
            sys.stdout.write(f"\r{' ' * 60}\r")
            sys.stdout.flush()
            print(f"Error processing {video_path.stem}: FFmpeg failed to adjust speed.")

        if current_output_dir not in output_base_dirs:
            output_base_dirs.append(current_output_dir)

    sys.stdout.write(f"\r{' ' * 60}\r")
    sys.stdout.flush()

    summary = f"Speed adjustment complete for {total} videos at {speed}x"
    logger.info(summary)
    print()
    print("\nSpeed Adjustment Summary")
    print("------------------------")
    print(f"Videos processed: {total}")
    print(f"Speed multiplier: {speed}x")
    print(f"Output folder(s): {', '.join(str(d) for d in output_base_dirs)}")
    print()
    djj.prompt_open_folder(str(output_base_dirs[0]))


# ─── Mode 3: Crop / Trim Padding ────────────────────────────────────────────

CROP_LOG_FILE = LOG_DIR / "video_processor_crop_log.csv"


def get_cropdetect_crop(video_path):
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-t", "5",
        "-vf", "cropdetect=24:16:0",
        "-f", "null", "-"
    ]
    try:
        result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        crops = [line for line in result.stderr.splitlines() if "crop=" in line]
        if crops:
            return crops[-1].split("crop=")[-1].strip()
    except Exception:
        return None
    return None


def get_video_resolution(video_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        w, h = map(int, result.stdout.strip().split(","))
        return w, h
    except Exception:
        return None, None


def build_crop_filter(mode, width, height):
    if mode == "2.1":
        target_w = int((16 / 9) * height)
        offset_x = (width - target_w) // 2
        return f"crop={target_w}:{height}:{offset_x}:0"
    elif mode == "2.2":
        target_w = int((9 / 16) * height)
        offset_x = (width - target_w) // 2
        return f"crop={target_w}:{height}:{offset_x}:0"
    return None


def log_crop_to_csv(entry):
    file_exists = CROP_LOG_FILE.exists()
    with open(CROP_LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=entry.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(entry)


def run_crop(videos):
    print("\033[93mCropping Mode:\033[0m")
    print("1. Trim Paddings")
    print("2. Crop to Fit")
    crop_mode = djj.prompt_choice("Choose cropping mode: \n ", ['1', '2'], default='1')

    if crop_mode == '2':
        print()
        print("\033[93mCrop to Fit Options:\033[0m")
        print("1. Horizontal (16:9)")
        print("2. Vertical (9:16)")
        submode = djj.prompt_choice("\033[93mChoose sub-mode:\033[0m \n ", ['1', '2'], default='1')
        crop_mode = f"2.{submode}"
    print()

    audio_choice = get_audio_choice()

    total = len(videos)
    successful = 0
    failed = 0
    output_base_dirs = []
    logger = get_op_logger("crop")

    for i, video_path in enumerate(videos, 1):
        width, height = get_video_resolution(video_path)
        crop_filter = None

        if crop_mode == "1":
            raw_crop = get_cropdetect_crop(video_path)
            if not raw_crop:
                logger.error(f"Could not detect borders for {video_path.name}")
                print(f"\033[93m❌ Skipped: Could not detect borders for\033[0m {video_path.name}")
                failed += 1
                continue
            crop_filter = f"crop={raw_crop}"
        elif crop_mode in {"2.1", "2.2"}:
            crop_filter = build_crop_filter(crop_mode, width, height)

        out_dir = video_path.parent / "Output" / "Cropped"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{video_path.stem}_cropped.mp4"

        if out_dir not in output_base_dirs:
            output_base_dirs.append(out_dir)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            *djj.get_audio_options(audio_choice),
            "-vf", crop_filter,
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            str(out_path)
        ]

        progress = (i / total) * 100
        sys.stdout.write(f"\033[93m\rProcessing\033[0m {i}/{total} ({progress:.1f}%)...")
        sys.stdout.flush()

        result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        status = "success" if result.returncode == 0 else "failed"

        if result.returncode == 0:
            successful += 1
            logger.info(f"Cropped {video_path.name} to {out_path}")
        else:
            failed += 1
            logger.error(f"Failed to crop {video_path.name}: {result.stderr}")

        log_crop_to_csv({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "filename": video_path.name,
            "audio_option": audio_choice,
            "crop_mode": crop_mode,
            "status": status,
            "crop_filter": crop_filter,
            "input_resolution": f"{width}x{height}",
            "output_path": str(out_path),
            "ffmpeg_summary": result.stderr.strip().splitlines()[-1] if result.stderr else "",
            "exit_code": result.returncode
        })

    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

    summary = f"Cropped {successful} of {total} videos successfully"
    logger.info(summary)
    print("\033[93m\nCropping Summary\033[0m")
    print("----------------")
    print(f"\033[93mVideos processed:\033[0m {total}")
    print(f"\033[93mVideos successfully cropped:\033[0m {successful}")
    print(f"\033[93mVideos failed:\033[0m {failed}")
    print(f"\033[93mOutput folder(s):\033[0m {', '.join(str(d) for d in output_base_dirs)}")
    print()
    djj.prompt_open_folder(str(output_base_dirs[0]))


# ─── Main ────────────────────────────────────────────────────────────────

def main():
    while True:
        print()
        print("\033[92m" + "=" * 50 + "\033[0m")
        print("\033[1;93mVideo Processor\033[0m")
        print("Re-encode, change speed, or crop/trim videos")
        print("\033[92m" + "=" * 50 + "\033[0m")
        print()

        mode = djj.prompt_choice(
            "\033[93mMode:\033[0m\n1. Re-encode\n2. Speed Change\n3. Crop / Trim Padding\n",
            ['1', '2', '3'], default='1'
        )
        print()

        videos = get_videos_input()
        if not videos:
            action = djj.what_next()
            if action == 'exit':
                break
            continue

        if mode == '1':
            run_reencode(videos)
        elif mode == '2':
            run_speed_change(videos)
        else:
            run_crop(videos)

        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()
