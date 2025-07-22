import os
import subprocess
import sys
import time
import pathlib
import logging
import djjtb.utils as djj

os.system('clear')

def clean_path(path_str):
    """Clean input path by removing quotes and extra spaces."""
    return path_str.strip().strip('\'"')

def get_video_duration(video_path):
    """Get the duration of a video file using ffprobe."""
    ffprobe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
    ]
    try:
        ffprobe_output = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=True)
        duration_str = ffprobe_output.stdout.strip()
        if not duration_str:
            raise ValueError("ffprobe returned an empty duration. Ensure the video file is valid.")
        return float(duration_str)
    except subprocess.CalledProcessError as e:
        print(f"\033[33mError running ffprobe:\033[0m {e}", file=sys.stderr)
        raise
    except ValueError as e:
        print(f"\033[33mError parsing video duration:\033[0m {e}", file=sys.stderr)
        raise

def collect_videos_from_folder(input_path, subfolders=False):
    """Collect videos from folder(s) using consistent logic"""
    input_path_obj = pathlib.Path(input_path)
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm')
    
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
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm')
    
    for path in paths:
        path = clean_path(path)
        path_obj = pathlib.Path(path)
        
        if path_obj.is_file() and path_obj.suffix.lower() in video_extensions:
            videos.append(str(path_obj))
        elif path_obj.is_dir():
            # If it's a directory, collect videos from it
            folder_videos = collect_videos_from_folder(str(path_obj), subfolders=False)
            videos.extend(folder_videos)
    
    return sorted(videos, key=str.lower)

def get_video_input():
    """Get video input using consistent pattern from reference script"""
    input_mode = djj.prompt_choice(
        "\033[33mInput mode:\033[0m\n1. Folder path, 2. Files & Folders (space-divided)\n",
        ['1', '2'],
        default='1'
    )
    print()
    
    videos = []
    
    if input_mode == '1':
        # Folder mode
        src_dir = input("📁 \033[33mEnter folder path: \n -> \033[0m").strip()
        src_dir = clean_path(src_dir)
        
        if not os.path.isdir(src_dir):
            print(f"❌ \033[33mThe path\033[0m '{src_dir}' \033[33mis not a valid directory\033[0m.")
            return []
        
        print()
        include_sub = djj.prompt_choice(
            "\033[33mInclude subfolders? \033[0m\n1. Yes, 2. No ",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        
        videos = collect_videos_from_folder(src_dir, include_sub)
        
    else:
        # File/folder paths mode
        file_paths = input("📁 \033[33mEnter file/folder paths (space-separated): \n -> \033[0m").strip()
        
        if not file_paths:
            print("❌ \033[33mNo paths provided.\033[0m")
            return []
        
        videos = collect_videos_from_paths(file_paths)
        print()
    
    if not videos:
        print("❌ \033[33mNo valid video files found.\033[0m")
        return []
    
    print(f"\033[33m✓ Found \033[0m{len(videos)} \033[33mvideo file(s)\033[0m")
    # Show first few files
    for i, video in enumerate(videos[:3]):
        print(f"  \033[33m{i+1}. \033[0m{os.path.basename(video)}")
    if len(videos) > 3:
        print(f"  \033[33m... and\033[0m {len(videos) - 3} \033[33mmore\033[0m")
    print()
    
    return videos

def split_video_by_duration(videos, clip_duration, audio_choice):
    """Split videos into clips of specified duration, with output in each video's parent folder."""
    if not videos:
        return [], [], None

    print()
    print("\033[33mSplitting Videos...\033[0m")
    
    
    successful = []
    failed = []
    output_dirs = set()
    total_videos = len(videos)
    
    for i, video_path in enumerate(videos, 1):
        video_path_obj = pathlib.Path(video_path)
        try:
            video_name = video_path_obj.stem
            output_dir = video_path_obj.parent / "Output" / "Duration_Split" / f"{int(clip_duration)}s" / video_name
            output_dir.mkdir(parents=True, exist_ok=True)
            logger = djj.setup_logging(str(output_dir), "video_split")
            output_dirs.add(str(output_dir))
            
            duration = get_video_duration(video_path)
            if clip_duration >= duration:
                error_msg = f"Clip duration ({clip_duration}s) must be less than video duration ({duration}s) for {video_path_obj.name}"
                logger.error(error_msg)
                print(f"\033[33mError:\033[0m {error_msg}", file=sys.stderr)
                failed.append((video_path_obj.name, None, "\033[33mClip duration too long\033[0m"))
                continue
            
            num_clips = int(duration // clip_duration)
            if duration % clip_duration > 0:
                num_clips += 1
            
            for j in range(num_clips):
                start_time = j * clip_duration
                remaining_time = min(clip_duration, duration - start_time)
                output_file = output_dir / f"{video_name}_{clip_duration}s-{j+1:04d}.mp4"

                progress = ((i - 1 + (j + 1) / num_clips) / total_videos) * 100
                status_line = f"\033[33mProcessing\033[0m {i}\033[33m/\033[0m{total_videos} \033[33mvideos\033[0m, \033[33mclips\033[0m {j+1}\033[33m/\033[0m{num_clips} ({progress:.1f}%)"
                print(f"\r\033[33m{status_line}\033[0m", end='', flush=True)
                
                try:
                    # Build FFmpeg command based on audio choice
                    audio_options = djj.get_audio_options(audio_choice)
                    
                    if audio_choice == '3':  # Silent audio track
                        ffmpeg_cmd = [
                            "ffmpeg", "-y", "-ss", str(start_time), "-i", str(video_path),
                            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                            "-t", str(remaining_time), "-c:v", "libx264", "-c:a", "aac", "-shortest", str(output_file)
                        ]
                    else:
                        ffmpeg_cmd = [
                            "ffmpeg", "-y", "-ss", str(start_time), "-i", str(video_path),
                            "-t", str(remaining_time), "-c:v", "libx264"
                        ] + audio_options + [str(output_file)]
                    
                    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    successful.append((video_path_obj.name, j+1))
                except subprocess.CalledProcessError as e:
                    failed.append((video_path_obj.name, j+1, str(e)))
                    logger.error(f"Error generating {output_file}: {e}")
                    print(f"\r{status_line}... (failed)    ", end='', flush=True)
            
        except Exception as e:
            failed.append((video_path_obj.name, None, str(e)))
            print(f"\r\033[33mProcessing\033[0m {i}\033[33m/\033[0m{total_videos} \033[33mvideos\033[0m ({i/total_videos*100:.1f}%)... \033[33m(failed) \033[0m   ", end='', flush=True)
    
    print("\r" + " " * 80 + "\r", end='', flush=True)
    
    return successful, failed, output_dirs

def split_video_by_portions(videos, num_portions, audio_choice):
    """Split videos into equal portions."""
    if not videos:
        return [], [], None
    print()
    print("\033[33mSplitting Videos...\033[0m")
    
    successful = []
    failed = []
    output_dirs = set()
    
    for i, video_path in enumerate(videos, 1):
        video_path_obj = pathlib.Path(video_path)
        try:
            video_name = video_path_obj.stem
            # Modified: Remove the video_name folder level for portion mode
            output_dir = video_path_obj.parent / "Output" / "Portion_Split" / f"{num_portions}_portions"
            output_dir.mkdir(parents=True, exist_ok=True)
            logger = djj.setup_logging(str(output_dir), "video_split")
            output_dirs.add(str(output_dir))
            
            duration = get_video_duration(video_path)
            if num_portions > duration:
                error_msg = f"Number of portions ({num_portions}) cannot exceed video duration ({duration}s) for {video_path_obj.name}"
                logger.error(error_msg)
                print(f"\033[33mError:\033[0m {error_msg}", file=sys.stderr)
                failed.append((video_path_obj.name, None, "\033[33mToo many portions for video duration\033[0m"))
                continue
            
            clip_duration = duration / num_portions
            
            for j in range(num_portions):
                start_time = j * clip_duration
                remaining_time = duration - start_time if j == num_portions - 1 else clip_duration
            
                output_file = output_dir / f"{video_name}-part{j+1:02d}.mp4"
            
                part_num = j + 1
                percent = int((part_num / num_portions) * 100)
            
                print(f"\r\033[33mSplitting Videos\033[0m {i}\033[33m/\033[0m{len(videos)} , \033[33mParts\033[0m {part_num}\033[33m/\033[0m{num_portions} ({percent}%)...", end='', flush=True)
                try:
                    # Build FFmpeg command based on audio choice
                    if audio_choice == '3':  # Add Silent Audio Track
                        ffmpeg_cmd = [
                            "ffmpeg", "-y", "-ss", str(start_time), "-i", str(video_path),
                            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                            "-t", str(remaining_time), "-c:v", "libx264", "-c:a", "aac", "-shortest",
                            str(output_file)
                        ]
                    else:
                        audio_options = djj.get_audio_options(audio_choice)
                        ffmpeg_cmd = [
                            "ffmpeg", "-y", "-ss", str(start_time), "-i", str(video_path),
                            "-t", str(remaining_time), "-c:v", "libx264"
                        ] + audio_options + [str(output_file)]
                
                    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    successful.append((video_path_obj.name, j+1))
                except subprocess.CalledProcessError as e:
                    failed.append((video_path_obj.name, j+1, str(e)))
                    logger.error(f"Error generating {output_file}: {e}")
                    progress = ((i - 1 + (j + 1) / num_portions) / len(videos)) * 100
                    print(f"\r\033[33mProcessing\033[0m {i}\033[33m/\033[0m{len(videos)} \033[33mvideos,\033[0m \033[33mpart\033[0m {j+1}\033[33m/\033[0m{num_portions} ({progress:.1f}%)... (failed)    ", end='', flush=True)
        except Exception as e:
            failed.append((video_path_obj.name, None, str(e)))
            logger.error(f"\033[33mFailed to process\033[0m {video_path_obj.name}: {e}")
            print(f"\033[33m\rProcessing \033[0m{i}\033[33m/\033[0m{len(videos)} \033[33mvideos\033[0m ({i/len(videos)*100:.1f}%)...\033[33m (failed) \033[0m   ", end='', flush=True)
    
    print("\r" + " " * 80 + "\r", end='', flush=True)
    
    return successful, failed, output_dirs

if __name__ == "__main__":
    while True:
        os.system('clear')
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mVideo Splitter\033[0m")
        print("Splits Videos into Clips")
        print("\033[92m==================================================\033[0m")
        print()

        # Get video input using consistent pattern
        videos = get_video_input()
        if not videos:
            continue

        # Choose splitting method
        split_method = djj.prompt_choice("\033[33mSplit method?\033[0m\n1. By Duration, 2. By Portions ", ['1', '2'], default='1')
        print()

        if split_method == '1':
            # Duration-based splitting
            clip_duration = djj.get_float_input("Clip Duration in seconds (ie. 8): ", min_val=0.1)
            print()
        else:
            # Portion-based splitting
            num_portions = djj.get_int_input("\033[33mNumber of portions:\n(ie. 4)\033[0m: ", min_val=2)
            print()

        audio_choice = djj.prompt_choice("\033[33mAudio handling?\033[0m\n1. Keep Original Audio\n2. Strip Audio\n3. Add Silent Audio Track)\n", ['1', '2', '3'], default='1')
        print()

        print("\033[33m-------------\033[0m")
        
        if split_method == '1':
            successful, failed, output_dirs = split_video_by_duration(videos, clip_duration, audio_choice)
        else:
            successful, failed, output_dirs = split_video_by_portions(videos, num_portions, audio_choice)
        
        print("\n" * 1)
        print("\033[33mSplitting Summary\033[0m")
        print("-------------")
        print(f"\033[33m✅ Successfully split:\033[0m {len(successful)} \033[33mclips\033[0m")
        if failed:
            print(f"❌ \033[33mFailed operations:\033[0m {len(failed)} \033[33m(see logs in output folders)\033[0m")
        if output_dirs:
            print("📁 \033[33mOutput folders:\033[0m")
            for output_dir in sorted(output_dirs):
                print(f"  {output_dir}")
        else:
            print("\033[33mNo output folders created.\033[0m")
        print("\n" * 2)

        if output_dirs:
            try:
                subprocess.run(['open', sorted(output_dirs)[0]], check=True)
            except subprocess.CalledProcessError as e:
                print(f"\033[33mError opening output folder:\033[0m {e}", file=sys.stderr)

        action = djj.what_next()
        if action == 'exit':
            break

    os.system('clear')