import os
import csv
import subprocess
import sys
import djjtb.utils as djj
from pathlib import Path
from datetime import datetime
import logging

os.system('clear')

VIDEO_EXTENSIONS = [".mp4", ".mkv", ".mov", ".avi", ".webm"]
LOG_DIR = Path("~/Documents/Scripts/DJJTB/djjtb/Logs").expanduser()
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "video_cropper_log.csv"


def open_output_folder(folder_path):
    try:
        subprocess.run(["open", str(folder_path)])
    except Exception as e:
        print(f"\033[33m⚠️ Could not open folder:\033[0m {e}")


def get_cropdetect_crop(video_path):
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-t", "5",
        "-vf", "cropdetect=24:16:0",
        "-f", "null", "-"
    ]
    try:
        result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        lines = result.stderr.splitlines()
        crops = [line for line in lines if "crop=" in line]
        if crops:
            raw_crop = crops[-1].split("crop=")[-1].strip()
            return raw_crop, result.stderr
    except Exception as e:
        return None, str(e)
    return None, "No crop info"


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


def get_audio_flag(option):
    if option == "1":
        return []
    elif option == "2":
        return ["-an", "-f", "lavfi", "-i", "anullsrc", "-shortest"]
    elif option == "3":
        return ["-an"]
    return []


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


def log_to_csv(entry):
    file_exists = LOG_FILE.exists()
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=entry.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(entry)


def clean_path(path_str):
    return path_str.strip().strip('\'"')


def collect_videos_from_folder(input_path, subfolders=False):
    """Collect videos from folder using re-encoder logic"""
    input_path_obj = Path(input_path).expanduser().resolve()
    video_extensions = tuple(VIDEO_EXTENSIONS)
    
    videos = []
    if input_path_obj.is_file() and input_path_obj.suffix.lower() in video_extensions:
        videos = [input_path_obj]
    elif input_path_obj.is_dir():
        if subfolders:
            for root, _, files in os.walk(input_path_obj):
                videos.extend(Path(root) / f for f in files if Path(f).suffix.lower() in video_extensions)
        else:
            videos = [f for f in input_path_obj.glob('*') if f.suffix.lower() in video_extensions and f.is_file()]
    else:
        print("\033[33mError: Input must be a video file or directory.\033[0m", file=sys.stderr)
        return []

    if not videos:
        print("\033[33mError: No video files found\033[0m.", file=sys.stderr)
        return []
    
    return sorted(videos, key=lambda x: str(x).lower())


def collect_videos_from_paths(file_paths):
    """Collect videos from space-separated file paths"""
    videos = []
    paths = file_paths.strip().split()
    
    for path in paths:
        path = clean_path(path)
        path_obj = Path(path).expanduser().resolve()
        
        if path_obj.is_file() and path_obj.suffix.lower() in VIDEO_EXTENSIONS:
            videos.append(path_obj)
        elif path_obj.is_dir():
            print(f"\033[33m⚠️ Skipping directory in file list: \033[0m{path}")
        else:
            print(f"\033[33m⚠️ Skipping invalid video file:\033[0m {path}")
    
    return sorted(videos, key=lambda x: str(x).lower())


def process_videos(video_paths, audio_option, crop_mode):
    total = len(video_paths)
    successful_videos = 0
    failed_videos = 0
    output_base_dirs = []
    
    # Setup logging for the first video's directory
    first_video_dir = video_paths[0].parent
    first_output_dir = first_video_dir / "Output" / "Cropped"
    first_output_dir.mkdir(parents=True, exist_ok=True)
    logger = djj.setup_logging(first_output_dir, "video_cropper")
    
    for i, file in enumerate(video_paths, start=1):
        width, height = get_video_resolution(file)
        crop_filter, raw_log = (None, "")

        if crop_mode == "1":
            crop_filter, raw_log = get_cropdetect_crop(file)
            if not crop_filter:
                logger.error(f"Could not detect borders for {file.name}")
                print(f"\033[33m❌ Skipped: Could not detect borders for\033[0m {file.name}")
                failed_videos += 1
                continue
        elif crop_mode in {"2.1", "2.2"}:
            crop_filter = build_crop_filter(crop_mode, width, height)

        out_folder = file.parent / "Output" / "Cropped"
        out_folder.mkdir(parents=True, exist_ok=True)
        out_path = out_folder / f"{file.stem}_cropped.mp4"

        # Track unique output directories
        if out_folder not in output_base_dirs:
            output_base_dirs.append(out_folder)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(file),
            *get_audio_flag(audio_option),
            "-vf", crop_filter if crop_filter.startswith("crop=") else f"crop={crop_filter}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            str(out_path)
        ]

        # Progress indicator
        progress = (i / total) * 100
        sys.stdout.write(f"\033[33m\rProcessing\033[0m {i}/{total} ({progress:.1f}%)...")
        sys.stdout.flush()

        result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        status = "success" if result.returncode == 0 else "failed"
        
        if result.returncode == 0:
            successful_videos += 1
            logger.info(f"Cropped {file.name} to {out_path}")
        else:
            failed_videos += 1
            logger.error(f"Failed to crop {file.name}: {result.stderr}")

        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "filename": file.name,
            "audio_option": audio_option,
            "crop_mode": crop_mode,
            "status": status,
            "crop_filter": crop_filter,
            "input_resolution": f"{width}x{height}",
            "output_path": str(out_path),
            "ffmpeg_summary": result.stderr.strip().splitlines()[-1] if result.stderr else "",
            "exit_code": result.returncode
        }
        log_to_csv(log_entry)

    # Clear progress line
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()
    
    logger.info(f"\033[33mCropped\033[0m {successful_videos} \033[33mof\033[0m {total} \033[33mvideos successfully\033[0m")
    print("\033[33m\nCropping Summary\033[0m")
    print("----------------")
    print(f"\033[33mVideos processed:\033[0m {total}")
    print(f"\033[33mVideos successfully cropped:\033[0m {successful_videos}")
    print(f"\033[33mVideos failed:\033[0m {failed_videos}")
    print(f"\033[33mOutput folder(s):\033[0m {', '.join(str(d) for d in output_base_dirs)}")
    print()

    if output_base_dirs:
        open_output_folder(output_base_dirs[0])


def main():
    while True:
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("Video Cropper / Padding Stripper\033[0m")
        print("\e[1;33m\033[0mStrips padding/Crops videos")
        print("\033[92m==================================================\033[0m")
        print()
        
        # Get input mode
        input_mode = djj.prompt_choice(
            "\033[33mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
            ['1', '2'],
            default='1'
        )
        print()
        
        video_paths = []
        
        if input_mode == '1':
            # Folder mode
            input_path = input("📁 \033[33mEnter folder path: \n ->\033[0m ").strip().strip('"')
            if not input_path:
                print("\033[33mNo input path provided.\033[0m")
                continue
            
            print()
            include_sub = djj.prompt_choice(
                "\033[33mInclude subfolders?\033[0m\n1. Yes, 2. No",
                ['1', '2'],
                default='2'
            ) == '1'
            print()

            video_paths = collect_videos_from_folder(input_path, include_sub)
            
        else:
            # File paths mode
            file_paths = input("📁 \033[33mEnter space-separated file paths: \n ->\033[0m ").strip()
            
            if not file_paths:
                print("❌ \033[33mNo file paths provided.\033[0m")
                continue
            
            video_paths = collect_videos_from_paths(file_paths)
            print()
            
        if not video_paths:
            continue

        print("\033[33mAudio options:\033[0m")
        print("1. Keep original audio")
        print("2. Add silent track")
        print("3. Remove audio")
        audio_option = djj.prompt_choice("Choose audio option: \n ", ['1', '2', '3'], default='1')
        print()

        print("\033[33mCropping Mode:\033[0m")
        print("1. Trim Paddings")
        print("2. Crop to Fit")
        crop_mode = djj.prompt_choice("C\033[33mhoose cropping mode: \n\033[0m", ['1', '2'], default='1')

        if crop_mode == '2':
            print()
            print("\033[33mCrop to Fit Options:\033[0m")
            print("1. Horizontal (16:9)")
            print("2. Vertical (9:16)")
            submode = djj.prompt_choice("\033[33mChoose sub-mode:\033[0m \n ", ['1', '2'], default='1')
            crop_mode = f"2.{submode}"
        print()

        process_videos(video_paths, audio_option, crop_mode)

        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()