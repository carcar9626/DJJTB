import os
import sys
import pathlib
import subprocess
import logging
from pathlib import Path
import djjtb.utils as djj
os.system('clear')
def setup_logging(output_path):
    log_file = os.path.join(output_path, "speed_adjustment_log.txt")
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger()

def sanitize_path(path):
    """Clean and normalize file paths."""
    return os.path.abspath(path.strip().strip('"').strip("'"))

def get_input_paths():
    """Get input paths from user, supporting multiple space-separated paths."""
    import shlex
    raw = input("path(s) (space-separated for multiple): \n -> ").strip()
    print()
    if not raw:
        return []
    
    try:
        raw_paths = shlex.split(raw)
        return [sanitize_path(p) for p in raw_paths if os.path.exists(sanitize_path(p))]
    except ValueError:
        # If shlex fails, try simple split
        raw_paths = raw.split()
        return [sanitize_path(p) for p in raw_paths if os.path.exists(sanitize_path(p))]
def prompt_choice(message, options, default=None):
    while True:
        default_str = f" (default: {default})" if default else ""
        choice = input(f"{message}{default_str}: ").strip()
        if not choice and default:
            return default
        if options is None:
            if choice.isdigit():
                return choice
            print("Invalid input. Please enter a number.")
        elif choice in options:
            return choice
        else:
            print("Invalid input. Please choose from:", ", ".join(options))

def get_atempo_chain(speed):
    """Generate atempo filter chain for audio speed adjustment."""
    if speed == 1.0:
        return ""
    
    # FFmpeg atempo filter supports 0.5-2.0 range
    # For speeds outside this range, chain multiple atempo filters
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

def change_speed(input_paths, subfolders=False):
    video_extensions = ('.mp4', '.mkv', '.avi', '.mov')
    
    videos = []
    for input_path in input_paths:
        input_path_obj = pathlib.Path(input_path)
        if input_path_obj.is_file() and input_path_obj.suffix.lower() in video_extensions:
            videos.append(input_path_obj)
        elif input_path_obj.is_dir():
            if subfolders:
                for root, _, files in os.walk(input_path):
                    videos.extend(pathlib.Path(root) / f for f in files if pathlib.Path(f).suffix.lower() in video_extensions)
            else:
                videos.extend(f for f in input_path_obj.glob('*') if f.suffix.lower() in video_extensions and f.is_file())
        else:
            print(f"Error: Invalid path: {input_path}", file=sys.stderr)
    
    if len(videos) == 0:
        print("Error: No video files found.", file=sys.stderr)
        return
    
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
    
    overwrite = prompt_choice("Overwrite existing output files?\n 1. Yes, 2. No ", ['1', '2'], default='2')
    print()
    # Handle output directory - if all videos from same parent, use single output
    if len(videos) == 1 or all(os.path.dirname(str(v)) == os.path.dirname(str(videos[0])) for v in videos):
        # Single output directory for all videos from same parent
        base_input_dir = os.path.dirname(str(videos[0]))
        output_base_dir = os.path.join(base_input_dir, "Output", "Speed_Adjusted")
        os.makedirs(output_base_dir, exist_ok=True)
        logger = setup_logging(output_base_dir)
        single_output = True
    else:
        # Multiple output directories for videos from different parents
        first_video_dir = os.path.dirname(videos[0])
        first_output_dir = os.path.join(first_video_dir, "Output", "Speed_Adjusted")
        os.makedirs(first_output_dir, exist_ok=True)
        logger = setup_logging(first_output_dir)
        single_output = False
    
    output_base_dirs = []
    total_videos = len(videos)
    
    for i, video_path in enumerate(videos, 1):
        if single_output:
            # Use the single output directory
            current_output_dir = output_base_dir
        else:
            # Create output directory for each video's parent
            video_dir = os.path.dirname(video_path)
            current_output_dir = os.path.join(video_dir, "Output", "Speed_Adjusted")
            os.makedirs(current_output_dir, exist_ok=True)
        
        name = os.path.splitext(os.path.basename(video_path))[0]
        ext = os.path.splitext(video_path)[1]
        output_filename = f"{name}_{speed}x{ext}"
        output = os.path.join(current_output_dir, output_filename)
        
        if os.path.exists(output) and overwrite != '1':
            logger.info(f"Skipped {name} (file exists)")
            continue
        
        # Check for audio stream
        try:
            audio_stream = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                "-of", "csv=p=0", "-select_streams", "a", str(video_path)
            ], capture_output=True, text=True).stdout.strip()
            audio_exists = "audio" in audio_stream
        except subprocess.CalledProcessError:
            audio_exists = False
        
        pts = 1 / speed
        progress = (i / total_videos) * 100
        sys.stdout.write(f"\rProcessing {i}/{total_videos} ({progress:.1f}%)...")
        sys.stdout.flush()
        
        try:
            if audio_exists:
                atempo = get_atempo_chain(speed)
                cmd = [
                    "ffmpeg", "-i", str(video_path),
                    "-filter_complex", f"[0:v]setpts={pts}*PTS[v];[0:a]{atempo}[a]",
                    "-map", "[v]", "-map", "[a]", "-loglevel", "quiet", "-y", output
                ]
            else:
                cmd = [
                    "ffmpeg", "-i", str(video_path),
                    "-filter:v", f"setpts={pts}*PTS",
                    "-an", "-loglevel", "quiet", "-y", output
                ]
            
            subprocess.run(cmd, check=True)
            logger.info(f"Speed adjusted {name} to {speed}x -> {output}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error processing {name}: FFmpeg failed to adjust speed")
            sys.stdout.write(f"\r{' ' * 60}\r")
            sys.stdout.flush()
            print(f"Error processing {name}: FFmpeg failed to adjust speed.")
        
        if current_output_dir not in output_base_dirs:
            output_base_dirs.append(current_output_dir)
    
    sys.stdout.write(f"\r{' ' * 60}\r")
    sys.stdout.flush()
    
    logger.info(f"Speed adjustment complete for {total_videos} videos at {speed}x")
    print()
    print("\nSpeed Adjustment Summary")
    print("------------------------")
    print(f"Videos processed: {total_videos}")
    print(f"Speed multiplier: {speed}x")
    print(f"Output folder(s): {', '.join(output_base_dirs)}")
    print()
    
    djj.prompt_open_folder(output_base_dirs[0])
    
    return output_base_dirs

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    while True:
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mSpeed Changer\033[0m")
        print("Adjust video playback speed")
        print("\033[92m==================================================\033[0m")
        print()
        
        input_paths = get_input_paths()
        if not input_paths:
            print("No valid paths provided.")
            continue
        
        include_sub = prompt_choice("Include subfolders?\n1. Yes, 2. No", ['1', '2'], default='2') == '1'
        print()
        
        change_speed(input_paths, include_sub)
        
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()