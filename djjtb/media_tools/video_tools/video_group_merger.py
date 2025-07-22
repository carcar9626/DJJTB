import os
import sys
import subprocess
import pathlib
import logging
import djjtb.utils as djj

os.system('clear')

def clean_path(path_str):
    return path_str.strip().strip('\'"')

def return_to_djjtb():
    """Switch back to DJJTB tab (Command+1)"""
    subprocess.run([
        "osascript", "-e",
        'tell application "Terminal" to tell application "System Events" to keystroke "1" using command down'
    ])

def is_valid_video(filename):
    return filename.lower().endswith(('.mp4', '.mov', '.webm', '.mkv'))

def get_user_group_size():
    try:
        group_size = int(input("How many files to merge per group? \n (default 2): ") or 2)
        if group_size < 2:
            raise ValueError
        return group_size
    except ValueError:
        print("❌ Invalid input. Using default of 2.")
        return 2

def collect_videos_from_folder(input_path, subfolders=False):
    """Collect videos from folder(s) using the re-encoder logic"""
    input_path_obj = pathlib.Path(input_path)
    video_extensions = ('.mp4', '.mkv', '.webm', '.mov')
    
    videos = []
    if input_path_obj.is_dir():
        if subfolders:
            for root, _, files in os.walk(input_path):
                videos.extend(pathlib.Path(root) / f for f in files if pathlib.Path(f).suffix.lower() in video_extensions)
        else:
            videos = [f for f in input_path_obj.glob('*') if f.suffix.lower() in video_extensions and f.is_file()]
    
    return sorted([str(v) for v in videos], key=str.lower)

def collect_videos_from_paths(file_paths):
    """Collect videos from space-separated file paths"""
    videos = []
    paths = file_paths.strip().split()
    
    for path in paths:
        path = clean_path(path)
        path_obj = pathlib.Path(path)
        
        if path_obj.is_file() and is_valid_video(path_obj.name):
            videos.append(str(path_obj))
        elif path_obj.is_dir():
            print(f"⚠️ Skipping directory in file list: {path}")
    
    return sorted(videos, key=str.lower)

def get_output_directory(videos, is_folder_mode=True, first_folder=None):
    """Determine output directory based on input mode"""
    if is_folder_mode and first_folder:
        return os.path.join(first_folder, "Output", "Grouped")
    elif videos:
        # Use parent directory of first video
        first_video_dir = os.path.dirname(videos[0])
        return os.path.join(first_video_dir, "Output", "Grouped")
    else:
        return os.path.join(os.getcwd(), "Output", "Grouped")

def merge_video_groups(videos, output_dir, group_size):
    """Merge videos into groups"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Setup logging
    logger = djj.setup_logging(output_dir, "merge_videos")
    
    total_groups = len(videos) // group_size
    remaining = len(videos) % group_size
    
    if remaining != 0:
        print(f"⚠️ {remaining} file(s) will be skipped (not enough to complete a group of {group_size}).")
    
    print(f"📄 Found {len(videos)} videos. Merging into {total_groups} group(s) of {group_size}...")
    
    success_count = 0
    error_count = 0
    
    for g in range(total_groups):
        group_videos = videos[g * group_size : (g + 1) * group_size]
        
        # Create temporary concat list file
        concat_list_path = os.path.join(output_dir, f"concat_list_{g}.txt")
        with open(concat_list_path, "w") as f:
            for vid in group_videos:
                # Use absolute path and escape single quotes
                escaped_path = vid.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
        
        # Generate output filename based on first video in group
        base_name = os.path.splitext(os.path.basename(group_videos[0]))[0]
        output_file = os.path.join(output_dir, f"{base_name}_grouped.mp4")
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            output_file
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"✅ Group {g+1}: Created {os.path.basename(output_file)}")
            logger.info(f"Group {g+1}: Merged {len(group_videos)} videos to {output_file}")
            success_count += 1
        except subprocess.CalledProcessError as e:
            error_msg = f"Group {g+1} failed: {e.stderr}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            error_count += 1
        finally:
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)
    
    return success_count, error_count, output_dir

def main():
    while True:
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mVideo Group Merger\033[0m")
        print("Merge every N videos")
        print("\033[92m==================================================\033[0m")
        print()
        
        # Get input mode
        input_mode = djj.prompt_choice(
            "Input mode:\n1. Folder path\n2. Space-separated file paths\n",
            ['1', '2'],
            default='1'
        )
        print()
        
        videos = []
        output_dir = None
        
        if input_mode == '1':
            # Folder mode
            src_dir = input("📁 \033[33mEnter folder path: \n -> \033[0m").strip()
            src_dir = clean_path(src_dir)
            
            if not os.path.isdir(src_dir):
                print(f"❌ \033[33mThe path\033[0m '{src_dir}' \033[33mis not a valid directory\033[0m.")
                continue
            
            print()
            include_sub = djj.prompt_choice(
                "\033[33mInclude subfolders? \033[0m\n1. Yes, 2. No ",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            
            videos = collect_videos_from_folder(src_dir, include_sub)
            output_dir = get_output_directory(videos, is_folder_mode=True, first_folder=src_dir)
            
        else:
            # File paths mode
            file_paths = input("📁 \033[33mEnter file paths: \n -> \033[0m").strip()
            
            if not file_paths:
                print("❌ No file paths provided.")
                continue
            
            videos = collect_videos_from_paths(file_paths)
            output_dir = get_output_directory(videos, is_folder_mode=False)
            print()
        
        if not videos:
            print("❌ \033[33mNo valid video files found.\033[0m")
            continue
        
        group_size = get_user_group_size()
        print()
        
        success_count, error_count, final_output_dir = merge_video_groups(videos, output_dir, group_size)
        
        print(f"\033[33m\n🏁 Done!\033[0m {success_count} \033[33mgroup(s) merged, \033[0m{error_count} \033[33merror(s).\033[0m")
        print(f"📁\033[33m Output folder:\033[0m {final_output_dir}")
        
        try:
            subprocess.run(["open", final_output_dir], check=True)
        except subprocess.CalledProcessError as e:
            print(f"⚠️ \033[33mCould not open output folder: \033[0m{e}")
        
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()