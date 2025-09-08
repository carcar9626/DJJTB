import os
import sys
import subprocess
import shlex
import time
import glob
import djjtb.utils as djj
from pathlib import Path
os.system('clear')

def sanitize_path(path):
    path = path.strip().strip('"').strip("'")
    return os.path.abspath(path)

def clean_path(path_str):
    """Clean path string by removing quotes"""
    return path_str.strip().strip('\'"')

def is_video_file(filename):
    extensions = ['.mp4', '.mov', '.mkv', '.avi', '.webm']
    return any(filename.lower().endswith(ext) for ext in extensions)

def run_ffmpeg(cmd):
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError as e:
        # Suppress error output during processing to avoid breaking progress line
        raise RuntimeError(f"FFmpeg failed for command: {' '.join(cmd)}")

def reverse_and_merge(video_path, index, total, speed_factor, input_base):
    folder, filename = os.path.split(video_path)
    name, ext = os.path.splitext(filename)
    ext = ext.lower()

    # Create output directories in the same folder as the video file
    # This way each subfolder gets its own output folder
    output_base = Path(folder) / "Output"  # Changed from input_base to folder
    reversed_dir = output_base / "Reversed"
    merged_dir = output_base / "Merge"
    reversed_dir.mkdir(parents=True, exist_ok=True)
    merged_dir.mkdir(parents=True, exist_ok=True)

    # Output files go directly in their respective folder's output directory
    reversed_file = reversed_dir / f"{name}_reversed{ext}"
    merged_file = merged_dir / f"{name}_merged{ext}"

    # Rest of your function stays the same...
    vf_filter = "reverse,trim=start_frame=1"
    af_filter = "areverse"
    if speed_factor and speed_factor != 1.0:
        vf_filter += f",setpts={1/speed_factor}*PTS"
        af_filter += f",atempo={speed_factor}" if 0.5 <= speed_factor <= 2.0 else ""
    
    run_ffmpeg([
        'ffmpeg', '-y',
        '-i', str(video_path),
        '-vf', vf_filter,
        '-af', af_filter,
        str(reversed_file)
    ])

    if not reversed_file.exists():
        raise RuntimeError(f"Failed to create reversed file: {reversed_file}")

    concat_list = Path(folder) / f'concat_temp_{index}.txt'
    with open(concat_list, 'w') as f:
        f.write(f"file '{video_path}'\n")
        f.write(f"file '{reversed_file}'\n")

    run_ffmpeg([
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_list),
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '18',
        '-c:a', 'aac',
        '-b:a', '192k',
        str(merged_file)
    ])

    if not merged_file.exists():
        raise RuntimeError(f"Failed to create merged file: {merged_file}")

    concat_list.unlink(missing_ok=True)

def collect_videos_from_folder(input_path, subfolders=False):
    """Collect videos from folder(s) - adapted from video_group_merger"""
    input_path_obj = Path(input_path)
    video_extensions = ('.mp4', '.mov', '.mkv', '.avi', '.webm')
    
    videos = []
    if input_path_obj.is_dir():
        if subfolders:
            for root, _, files in os.walk(input_path):
                videos.extend(Path(root) / f for f in files if Path(f).suffix.lower() in video_extensions)
        else:
            videos = [f for f in input_path_obj.glob('*') if f.suffix.lower() in video_extensions and f.is_file()]
    
    return sorted([str(v) for v in videos], key=str.lower)

def collect_videos_from_paths(file_paths):
    """Collect videos from space-separated file paths - adapted from video_group_merger"""
    videos = []
    paths = file_paths.strip().split()
    
    for path in paths:
        path = clean_path(path)
        path_obj = Path(path)
        
        if path_obj.is_file() and is_video_file(path_obj.name):
            videos.append(str(path_obj))
        elif path_obj.is_dir():
            # If it's a directory, collect videos from it
            videos.extend(collect_videos_from_folder(str(path_obj), subfolders=False))
    
    return sorted(videos, key=str.lower)

def open_output_folder(path):
    try:
        subprocess.run(['open', str(path)], check=False)
    except Exception:
        pass

def ask_speed_factor():
    answer = djj.prompt_choice(
        "Change speed of reversed?\n1. Yes\n2. No\n",
        ['1', '2'],
        default='2'
    )
    
    if answer == "1":
        while True:
            try:
                speed = djj.get_float_input("Enter speed multiplier\n(e.g., 0.5, 2.0)", min_val=0.1, max_val=10.0)
                return speed
            except SystemExit:
                # Handle the exit from get_float_input gracefully
                return 1.0
    return 1.0

def main():
    print("\033[92m==================================================\033[0m")
    print("\033[1;33mVideo Reverse Merge\033[0m")
    print("Reverse & merge with speed options")
    print("\033[92m==================================================\033[0m")
    print()

    while True:
        # Get input mode using utils prompt_choice
        input_mode = djj.prompt_choice(
            "\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
            ['1', '2'],
            default='2'
        )
        print()

        videos = []
        include_sub = False
        input_path = None

        if input_mode == '1':
            # Folder mode
            input_path = djj.get_path_input("Enter folder path")
            print()
            
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes, 2. No ",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            
            videos = collect_videos_from_folder(input_path, include_sub)
            
        else:
            # File paths mode
            file_paths = input("📁 \033[93mEnter file paths (space-separated): \n\033[0m -> ").strip()
            
            if not file_paths:
                print("❌ \033[93mNo file paths provided.\033[0m")
                continue
            
            videos = collect_videos_from_paths(file_paths)
            # Set input_path to parent of first video for output folder logic
            if videos:
                input_path = str(Path(videos[0]).parent)
            print()

        if not videos:
            print("❌ \033[93mNo valid video files found. Try again.\033[0m\n")
            continue

        print("Scanning for videos...")
        print(f"✅ \033[93m{len(videos)} videos found\033[0m")
        print()

        speed_factor = ask_speed_factor()
        print()
        print("-------------")

        total = len(videos)
        successful = 0
        failed = []

        # Calculate prefix length dynamically based on total
        prefix = f"\033[93mProcessing video\033[0m {total}\033[93m/\033[0m{total}: "
        max_name_len = max(len(os.path.basename(v)[:30] + ("..." if len(os.path.basename(v)) > 30 else "")) for v in videos) + len(prefix) + 10

        for idx, vid_path in enumerate(videos, 1):
            # Update progress line with truncated filename
            display_name = os.path.basename(vid_path)[:30] + "..." if len(os.path.basename(vid_path)) > 30 else os.path.basename(vid_path)
            sys.stdout.write(f"\r\033[93mProcessing video\033[0m {idx}\033[93m/\033[0m{total}: {display_name}")
            sys.stdout.flush()
            try:
                reverse_and_merge(vid_path, idx, total, speed_factor, input_path)
                successful += 1
            except Exception as e:
                failed.append((os.path.basename(vid_path), str(e)))

        # Clear progress line
        sys.stdout.write("\r" + " " * max_name_len + "\r")
        sys.stdout.flush()

        # Display results
        print()
        print("\033[93mReverse Merge Summary\033[0m")
        print("---------------------")
        print(f"\033[93mSuccessfully processed:\033[0m {successful} \033[93mvideos\033[0m")
        if failed:
            print("\033[93mFailed processing:\033[0m")
            for name, error in failed:
                print(f"  {name}: {error}")

        # Handle output folder opening based on subfolder processing
        if include_sub and input_mode == '1':
            print(f"\033[93mOutput folders created in each processed directory\033[0m")
            print(f"\033[93mMain input folder: \033[0m\n{input_path}")
            print("\n" * 2)
            djj.prompt_open_folder(input_path)
        else:
            # Original logic for single folder processing
            if input_path:
                output_base = Path(input_path) / "Output"
                print(f"\033[93mOutput folder: \033[0m\n{output_base}")
                print("\n" * 2)
                djj.prompt_open_folder(output_base)
                    
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()