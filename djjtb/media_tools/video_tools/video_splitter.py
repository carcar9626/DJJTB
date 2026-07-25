import os
import subprocess
import sys
import pathlib
import djjtb.utils as djj
from scenedetect import open_video, SceneManager
from scenedetect.detectors import AdaptiveDetector

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
        print(f"\033[93mError running ffprobe:\033[0m {e}", file=sys.stderr)
        raise
    except ValueError as e:
        print(f"\033[93mError parsing video duration:\033[0m {e}", file=sys.stderr)
        raise


def get_video_input():
    """Get video input using consistent pattern from reference script"""
    input_mode = djj.prompt_choice(
        "\033[93mInput mode:\033[0m\n1. Folder path, 2. Files & Folders (space-divided)\n",
        ['1', '2'],
        default='1'
    )
    print()
    
    videos = []
    
    if input_mode == '1':
        # Folder mode
        src_dir = input("📁 \033[93mEnter folder path: \n -> \033[0m").strip()
        src_dir = clean_path(src_dir)
        
        if not os.path.isdir(src_dir):
            print(f"❌ \033[93mThe path\033[0m '{src_dir}' \033[93mis not a valid directory\033[0m.")
            return []
        
        print()
        include_sub = djj.prompt_choice(
            "\033[93mInclude subfolders? \033[0m\n1. Yes, 2. No ",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        
        videos = djj.collect_videos_from_folder(src_dir, include_sub)

    else:
        # File/folder paths mode
        file_paths = input("📁 \033[93mEnter file/folder paths (space-separated): \n -> \033[0m").strip()

        if not file_paths:
            print("❌ \033[93mNo paths provided.\033[0m")
            return []

        videos = djj.collect_videos_from_paths(file_paths)
        print()
    
    if not videos:
        print("❌ \033[93mNo valid video files found.\033[0m")
        return []
    
    print(f"\033[93m✓ Found \033[0m{len(videos)} \033[93mvideo file(s)\033[0m")
    # Show first few files
    for i, video in enumerate(videos[:3]):
        print(f"  \033[93m{i+1}. \033[0m{os.path.basename(video)}")
    if len(videos) > 3:
        print(f"  \033[93m... and\033[0m {len(videos) - 3} \033[93mmore\033[0m")
    print()
    
    return videos

def build_split_cmd(video_path, start_time, remaining_time, output_file, audio_choice):
    """Build the ffmpeg command for one split clip, based on audio choice."""
    if audio_choice == '3':  # Add silent audio track
        return [
            "ffmpeg", "-y", "-ss", str(start_time), "-i", str(video_path),
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t", str(remaining_time), "-c:v", "libx264", "-c:a", "aac", "-shortest",
            str(output_file)
        ]
    audio_options = djj.get_audio_options(audio_choice)
    return [
        "ffmpeg", "-y", "-ss", str(start_time), "-i", str(video_path),
        "-t", str(remaining_time), "-c:v", "libx264"
    ] + audio_options + [str(output_file)]

def detect_scenes(video_path, min_scene_duration):
    """
    Detect scenes via PySceneDetect (AdaptiveDetector), then merge any
    scene shorter than min_scene_duration into its neighbor -- otherwise
    fast-cut montage footage (e.g. GRWM-style outfit-change clips) explodes
    into dozens of sub-second fragments instead of a few usable scenes.
    Returns a list of (start_seconds, end_seconds) tuples.
    """
    video = open_video(str(video_path))
    scene_manager = SceneManager()
    scene_manager.add_detector(AdaptiveDetector())
    scene_manager.detect_scenes(video=video)
    scenes = scene_manager.get_scene_list()

    if not scenes:
        return []

    merged = []
    group_start = scenes[0][0]
    group_end = scenes[0][1]
    for start, end in scenes[1:]:
        if group_end.get_seconds() - group_start.get_seconds() < min_scene_duration:
            group_end = end
        else:
            merged.append((group_start.get_seconds(), group_end.get_seconds()))
            group_start = start
            group_end = end
    merged.append((group_start.get_seconds(), group_end.get_seconds()))

    if len(merged) > 1:
        last_start, last_end = merged[-1]
        if last_end - last_start < min_scene_duration:
            prev_start, prev_end = merged[-2]
            merged[-2] = (prev_start, last_end)
            merged.pop()

    return merged

def split_video_by_scenes(videos, min_scene_duration, audio_choice):
    """Split videos at auto-detected scene boundaries."""
    if not videos:
        return [], [], None

    print()
    print("\033[93mDetecting scenes...\033[0m")

    successful = []
    failed = []
    output_dirs = set()
    total_videos = len(videos)

    for i, video_path in enumerate(videos, 1):
        video_path_obj = pathlib.Path(video_path)
        logger = None
        try:
            video_name = video_path_obj.stem
            output_dir = video_path_obj.parent / "Output" / "Scene_Split" / video_name
            output_dir.mkdir(parents=True, exist_ok=True)
            logger = djj.setup_logging(str(output_dir), "video_split")
            output_dirs.add(str(output_dir))

            print(f"\r\033[93mAnalyzing\033[0m {i}\033[93m/\033[0m{total_videos}: {video_path_obj.name}...", end='', flush=True)
            scenes = detect_scenes(video_path, min_scene_duration)

            if not scenes:
                logger.error(f"No scenes detected for {video_path_obj.name}")
                print(f"\n\033[93mNo scenes detected for\033[0m {video_path_obj.name}\033[93m, skipping.\033[0m")
                failed.append((video_path_obj.name, None, "No scenes detected"))
                continue

            num_scenes = len(scenes)
            for j, (start_time, end_time) in enumerate(scenes):
                clip_duration = end_time - start_time
                output_file = output_dir / f"{video_name}-scene{j+1:04d}.mp4"

                progress = ((i - 1 + (j + 1) / num_scenes) / total_videos) * 100
                status_line = f"\033[93mSplitting\033[0m {i}\033[93m/\033[0m{total_videos} \033[93mvideos\033[0m, \033[93mscenes\033[0m {j+1}\033[93m/\033[0m{num_scenes} ({progress:.1f}%)"
                print(f"\r\033[93m{status_line}\033[0m", end='', flush=True)

                try:
                    ffmpeg_cmd = build_split_cmd(video_path, start_time, clip_duration, output_file, audio_choice)
                    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    successful.append((video_path_obj.name, j+1))
                except subprocess.CalledProcessError as e:
                    failed.append((video_path_obj.name, j+1, str(e)))
                    logger.error(f"Error generating {output_file}: {e}")
                    print(f"\r{status_line}... (failed)    ", end='', flush=True)

        except Exception as e:
            failed.append((video_path_obj.name, None, str(e)))
            if logger:
                logger.error(f"Failed to process {video_path_obj.name}: {e}")
            print(f"\r\033[93mProcessing\033[0m {i}\033[93m/\033[0m{total_videos} \033[93mvideos\033[0m ({i/total_videos*100:.1f}%)... \033[93m(failed) \033[0m   ", end='', flush=True)

    print("\r" + " " * 80 + "\r", end='', flush=True)

    return successful, failed, output_dirs

def split_video_by_duration(videos, clip_duration, audio_choice):
    """Split videos into clips of specified duration, with output in each video's parent folder."""
    if not videos:
        return [], [], None

    print()
    print("\033[93mSplitting Videos...\033[0m")
    
    
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
                print(f"\033[93mError:\033[0m {error_msg}", file=sys.stderr)
                failed.append((video_path_obj.name, None, "\033[93mClip duration too long\033[0m"))
                continue
            
            num_clips = int(duration // clip_duration)
            if duration % clip_duration > 0:
                num_clips += 1
            
            for j in range(num_clips):
                start_time = j * clip_duration
                remaining_time = min(clip_duration, duration - start_time)
                output_file = output_dir / f"{video_name}_{clip_duration}s-{j+1:04d}.mp4"

                progress = ((i - 1 + (j + 1) / num_clips) / total_videos) * 100
                status_line = f"\033[93mProcessing\033[0m {i}\033[93m/\033[0m{total_videos} \033[93mvideos\033[0m, \033[93mclips\033[0m {j+1}\033[93m/\033[0m{num_clips} ({progress:.1f}%)"
                print(f"\r\033[93m{status_line}\033[0m", end='', flush=True)
                
                try:
                    ffmpeg_cmd = build_split_cmd(video_path, start_time, remaining_time, output_file, audio_choice)
                    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    successful.append((video_path_obj.name, j+1))
                except subprocess.CalledProcessError as e:
                    failed.append((video_path_obj.name, j+1, str(e)))
                    logger.error(f"Error generating {output_file}: {e}")
                    print(f"\r{status_line}... (failed)    ", end='', flush=True)
            
        except Exception as e:
            failed.append((video_path_obj.name, None, str(e)))
            print(f"\r\033[93mProcessing\033[0m {i}\033[93m/\033[0m{total_videos} \033[93mvideos\033[0m ({i/total_videos*100:.1f}%)... \033[93m(failed) \033[0m   ", end='', flush=True)
    
    print("\r" + " " * 80 + "\r", end='', flush=True)
    
    return successful, failed, output_dirs

def split_video_by_portions(videos, num_portions, audio_choice):
    """Split videos into equal portions."""
    if not videos:
        return [], [], None
    print()
    print("\033[93mSplitting Videos...\033[0m")
    
    successful = []
    failed = []
    output_dirs = set()
    
    for i, video_path in enumerate(videos, 1):
        video_path_obj = pathlib.Path(video_path)
        logger = None
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
                print(f"\033[93mError:\033[0m {error_msg}", file=sys.stderr)
                failed.append((video_path_obj.name, None, "\033[93mToo many portions for video duration\033[0m"))
                continue
            
            clip_duration = duration / num_portions
            
            for j in range(num_portions):
                start_time = j * clip_duration
                remaining_time = duration - start_time if j == num_portions - 1 else clip_duration
            
                output_file = output_dir / f"{video_name}-part{j+1:02d}.mp4"
            
                part_num = j + 1
                percent = int((part_num / num_portions) * 100)
            
                print(f"\r\033[93mSplitting Videos\033[0m {i}\033[93m/\033[0m{len(videos)} , \033[93mParts\033[0m {part_num}\033[93m/\033[0m{num_portions} ({percent}%)...", end='', flush=True)
                try:
                    ffmpeg_cmd = build_split_cmd(video_path, start_time, remaining_time, output_file, audio_choice)
                    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    successful.append((video_path_obj.name, j+1))
                except subprocess.CalledProcessError as e:
                    failed.append((video_path_obj.name, j+1, str(e)))
                    logger.error(f"Error generating {output_file}: {e}")
                    progress = ((i - 1 + (j + 1) / num_portions) / len(videos)) * 100
                    print(f"\r\033[93mProcessing\033[0m {i}\033[93m/\033[0m{len(videos)} \033[93mvideos,\033[0m \033[93mpart\033[0m {j+1}\033[93m/\033[0m{num_portions} ({progress:.1f}%)... (failed)    ", end='', flush=True)
        except Exception as e:
            failed.append((video_path_obj.name, None, str(e)))
            if logger:
                logger.error(f"\033[93mFailed to process\033[0m {video_path_obj.name}: {e}")
            print(f"\033[93m\rProcessing \033[0m{i}\033[93m/\033[0m{len(videos)} \033[93mvideos\033[0m ({i/len(videos)*100:.1f}%)...\033[93m (failed) \033[0m   ", end='', flush=True)
    
    print("\r" + " " * 80 + "\r", end='', flush=True)
    
    return successful, failed, output_dirs

if __name__ == "__main__":
    while True:
        os.system('clear')
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mVideo Splitter\033[0m")
        print("Splits Videos into Clips")
        print("\033[92m==================================================\033[0m")
        print()

        # Get video input using consistent pattern
        videos = get_video_input()
        if not videos:
            continue

        # Choose splitting method
        split_method = djj.prompt_choice(
            "\033[93mSplit method?\033[0m\n1. By Duration, 2. By Portions, 3. By Scene Detection (auto) ",
            ['1', '2', '3'],
            default='1'
        )
        print()

        if split_method == '1':
            # Duration-based splitting
            clip_duration = djj.get_float_input("Clip Duration in seconds (ie. 8): ", min_val=0.1)
            print()
        elif split_method == '2':
            # Portion-based splitting
            num_portions = djj.get_int_input("\033[93mNumber of portions:\n(ie. 4)\033[0m: ", min_val=2)
            print()
        else:
            # Scene-detection splitting
            min_scene_duration = djj.get_float_input(
                "\033[93mMinimum scene length in seconds (ie. 2.0):\033[0m ",
                min_val=0.1, max_val=30.0
            )
            print()

        audio_choice = djj.prompt_choice("\033[93mAudio handling?\033[0m\n1. Keep Original Audio\n2. Strip Audio\n3. Add Silent Audio Track)\n", ['1', '2', '3'], default='1')
        print()

        print("\033[93m-------------\033[0m")

        if split_method == '1':
            successful, failed, output_dirs = split_video_by_duration(videos, clip_duration, audio_choice)
        elif split_method == '2':
            successful, failed, output_dirs = split_video_by_portions(videos, num_portions, audio_choice)
        else:
            successful, failed, output_dirs = split_video_by_scenes(videos, min_scene_duration, audio_choice)

        print("\n" * 1)
        print("\033[93mSplitting Summary\033[0m")
        print("-------------")
        print(f"\033[93m✅ Successfully split:\033[0m {len(successful)} \033[93mclips\033[0m")
        if failed:
            print(f"❌ \033[93mFailed operations:\033[0m {len(failed)} \033[93m(see logs in output folders)\033[0m")
        if output_dirs:
            print("📁 \033[93mOutput folders:\033[0m")
            for output_dir in sorted(output_dirs):
                print(f"  {output_dir}")
            print("\n" * 2)
            djj.prompt_open_folder(output_dir)
        else:
            print("\033[93mNo output folders created.\033[0m")
            print("\n" * 2)

        action = djj.what_next()
        if action == 'exit':
            break

    os.system('clear')