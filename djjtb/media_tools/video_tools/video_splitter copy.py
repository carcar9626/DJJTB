import os
import subprocess
import sys
import time
import pathlib
import logging
import djjtb.utils as djj
    
os.system('clear')

def setup_logging(output_path):
    """Set up logging to a file in the output folder."""
    log_file = os.path.join(output_path, 'video_split_errors.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger()

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
        logger = setup_logging(video_path.parent)
        logger.error(f"Error running ffprobe: {e}\nffprobe stderr: {e.stderr}")
        print(f"Error running ffprobe: {e}", file=sys.stderr)
        raise
    except ValueError as e:
        logger = setup_logging(video_path.parent)
        logger.error(f"Error parsing video duration: {e}")
        print(f"Error parsing video duration: {e}", file=sys.stderr)
        raise

def get_audio_options(audio_choice):
    """Get FFmpeg audio options based on user choice."""
    if audio_choice == '1':  # Keep Original Audio
        return ["-c:a", "aac"]
    elif audio_choice == '2':  # Strip Audio
        return ["-an"]
    elif audio_choice == '3':  # Add Silent Audio Track
        return ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000", "-c:a", "aac", "-shortest"]
    else:
        return ["-c:a", "aac"]  # Default to keep original

def split_video_by_duration(input_path, clip_duration, include_subfolders, audio_choice):
    """Split videos into clips of specified duration, with output in each video's parent folder."""
    input_path = pathlib.Path(input_path).resolve()
    if not input_path.exists():
        print("Error: Input path does not exist.", file=sys.stderr)
        return [], [], None

    video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv')
    videos = []
    if input_path.is_file() and input_path.suffix.lower() in video_extensions:
        videos = [input_path]
    elif input_path.is_dir():
        pattern = '**/*' if include_subfolders else '*'
        videos = [f for f in sorted(input_path.glob(pattern)) if f.suffix.lower() in video_extensions and f.is_file()]
    else:
        print("Error: Input must be a video file or directory.", file=sys.stderr)
        return [], [], None
    
    print("Scanning for Videos...")
    print(f"{len(videos)} videos found")
    print()
    print("Splitting Videos...")
    
    successful = []
    failed = []
    output_dirs = set()
    
    for i, video_path in enumerate(videos, 1):
        try:
            video_name = os.path.splitext(video_path.name)[0]
            output_dir = os.path.join(str(video_path.parent), "Output", "Duration_Split", f"{int(clip_duration)}s", video_name)
            os.makedirs(output_dir, exist_ok=True)
            logger = setup_logging(output_dir)
            output_dirs.add(output_dir)
            
            duration = get_video_duration(video_path)
            if clip_duration >= duration:
                logger.error(f"Clip duration ({clip_duration}s) must be less than video duration ({duration}s) for {video_path.name}")
                print(f"Error: Clip duration ({clip_duration}s) must be less than video duration ({duration}s) for {video_path.name}", file=sys.stderr)
                failed.append((video_path.name, None, "Clip duration too long"))
                continue
            
            video_name = os.path.splitext(video_path.name)[0]
            num_clips = int(duration // clip_duration)
            if duration % clip_duration > 0:
                num_clips += 1
            
            for j in range(num_clips):
                start_time = j * clip_duration
                remaining_time = min(clip_duration, duration - start_time)
                output_file = os.path.join(output_dir, f"{video_name}-{j+1:04d}.mp4")
                
                progress = ((i - 1 + (j + 1) / num_portions) / total_videos) * 100
                print_progress(i, len(videos), j + 1, num_portions, f"{progress:.1f}%")
                print(" " * 80, end='\r')  # Clear any leftover characters
                print(status_line, end='', flush=True)
                
                try:
                    # Build FFmpeg command based on audio choice
                    audio_options = get_audio_options(audio_choice)
                    
                    if audio_choice == '3':  # Silent audio track
                        # Need to add silent audio as a second input
                        ffmpeg_cmd = [
                            "ffmpeg", "-y", "-ss", str(start_time), "-i", str(video_path),
                            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                            "-t", str(remaining_time), "-c:v", "libx264", "-c:a", "aac", "-shortest", output_file
                        ]
                    else:
                        ffmpeg_cmd = [
                            "ffmpeg", "-y", "-ss", str(start_time), "-i", str(video_path),
                            "-t", str(remaining_time), "-c:v", "libx264"
                        ] + audio_options + [output_file]
                    
                    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    if result.stderr:
                        logger.warning(f"FFmpeg stderr for {output_file}: {result.stderr}")
                    successful.append((video_path.name, j+1))
                except subprocess.CalledProcessError as e:
                    failed.append((video_path.name, j+1, str(e)))
                    logger.error(f"Error generating {output_file}: {e}\nFFmpeg stderr: {e.stderr}")
                    print(f"\rProcessing {i}/{len(videos)} videos, clip {j+1}/{num_clips} ({progress:.1f}%)... (failed)    ", end='', flush=True)
            
        except Exception as e:
            failed.append((video_path.name, None, str(e)))
            logger.error(f"Failed to process {video_path.name}: {e}")
            print(f"\rProcessing {i}/{len(videos)} videos ({i/len(videos)*100:.1f}%)... (failed)    ", end='', flush=True)
    
    print("\r" + " " * 80 + "\r", end='', flush=True)
    
    return successful, failed, output_dirs

def split_video_by_portions(input_path, num_portions, output_dir, video_index=1, total_videos=1):
    """Split videos into equal portions."""
    input_path = pathlib.Path(input_path).resolve()
    if not input_path.exists():
        print("Error: Input path does not exist.", file=sys.stderr)
        return [], [], None

    video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv')
    videos = []
    if input_path.is_file() and input_path.suffix.lower() in video_extensions:
        videos = [input_path]
    elif input_path.is_dir():
        pattern = '**/*' if include_subfolders else '*'
        videos = [f for f in sorted(input_path.glob(pattern)) if f.suffix.lower() in video_extensions and f.is_file()]
    else:
        print("Error: Input must be a video file or directory.", file=sys.stderr)
        return [], [], None
    
    print("Scanning for Videos...")
    print(f"{len(videos)} videos found")
    print()
    print("Splitting Videos...")
    
    successful = []
    failed = []
    output_dirs = set()
    
    for i, video_path in enumerate(videos, 1):
        try:
            video_name = os.path.splitext(video_path.name)[0]
            output_dir = os.path.join(str(video_path.parent), "Output", "Portion_Split", f"{num_portions}_portions", video_name)
            os.makedirs(output_dir, exist_ok=True)
            logger = setup_logging(output_dir)
            output_dirs.add(output_dir)
            
            duration = get_video_duration(video_path)
            if num_portions > duration:
                logger.error(f"Number of portions ({num_portions}) cannot exceed video duration ({duration}s) for {video_path.name}")
                print(f"Error: Number of portions ({num_portions}) cannot exceed video duration ({duration}s) for {video_path.name}", file=sys.stderr)
                failed.append((video_path.name, None, "Too many portions for video duration"))
                continue
            
            clip_duration = duration / num_portions
            
            for j in range(num_portions):
                start_time = j * clip_duration
                remaining_time = duration - start_time if j == num_portions - 1 else clip_duration
            
                output_file = os.path.join(output_dir, f"{video_name}-part{j+1:02d}.mp4")
            
                part_num = j + 1
                percent = int((part_num / num_portions) * 100)
            
                print(f"\rSplitting Videos {i}/{len(videos)} , Parts {part_num}/{num_portions} ({percent}%)...", end='', flush=True)
                try:
                    # Build FFmpeg command based on audio choice
                    if audio_choice == '3':  # Add Silent Audio Track
                        ffmpeg_cmd = [
                            "ffmpeg", "-y", "-ss", str(start_time), "-i", str(video_path),
                            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                            "-t", str(remaining_time), "-c:v", "libx264", "-c:a", "aac", "-shortest",
                            output_file
                        ]
                    else:
                        audio_options = get_audio_options(audio_choice)
                        ffmpeg_cmd = [
                            "ffmpeg", "-y", "-ss", str(start_time), "-i", str(video_path),
                            "-t", str(remaining_time), "-c:v", "libx264"
                        ] + audio_options + [output_file]
                
                    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    if result.stderr:
                        logger.warning(f"FFmpeg stderr for {output_file}: {result.stderr}")
                    successful.append((video_path.name, j+1))
                except subprocess.CalledProcessError as e:
                    failed.append((video_path.name, j+1, str(e)))
                    logger.error(f"Error generating {output_file}: {e}\nFFmpeg stderr: {e.stderr}")
                    print(f"\rProcessing {i}/{len(videos)} videos, part {j+1}/{num_portions} ({progress:.1f}%)... (failed)    ", end='', flush=True)
                print()  # Just to move to the next line cleanly
        except Exception as e:
            failed.append((video_path.name, None, str(e)))
            logger.error(f"Failed to process {video_path.name}: {e}")
            print(f"\rProcessing {i}/{len(videos)} videos ({i/len(videos)*100:.1f}%)... (failed)    ", end='', flush=True)
    
    print("\r" + " " * 80 + "\r", end='', flush=True)
    
    return successful, failed, output_dirs

def print_progress(current_video, total_videos, current_part, num_portions, message=""):
    status = f"Processing {current_video}/{total_videos} videos, part {current_part}/{num_portions}"
    if message:
        status += f" ({message})"
    print("\r" + " " * 80, end='\r')  # clear the line
    print(f"\r{status}", end='', flush=True)
    
    
if __name__ == "__main__":
    while True:
        os.system('clear')
        print("\033[92m=================================================================\033[0m")
        print("\033[1;33mVideo Splitter\033[0m")
        print("Splits Videos into Clips")
        print("\033[92m=================================================================\033[0m")
        print()

        max_attempts = 5
        attempt = 0
        input_path = None
        while attempt < max_attempts:
            input_path = input("Enter path to video file or directory: \n > ").strip()
            input_path = clean_path(input_path)
            try:
                normalized_path = str(pathlib.Path(input_path).resolve())
                if os.path.exists(normalized_path):
                    input_path = normalized_path
                    break
                print(f"Error: '{normalized_path}' does not exist. Ensure the path is correct and the external drive (if any) is mounted.", file=sys.stderr)
            except Exception as e:
                print(f"Error resolving path '{input_path}': {e}. Please try again.", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("Too many invalid attempts. Exiting.", file=sys.stderr)
                sys.exit(1)
        print()

        include_subfolders = djj.prompt_choice("Include subfolders? (1. Yes, 2. No)\n > ", ['1', '2'], default='2') == '1'
        print()

        # Choose splitting method
        split_method = djj.prompt_choice("Split method? (1. By Duration, 2. By Portions)\n > ", ['1', '2'], default='1')
        print()

        if split_method == '1':
            # Duration-based splitting
            attempt = 0
            clip_duration = None
            while attempt < max_attempts:
                try:
                    clip_duration = float(input("Clip Duration\nin seconds (ie. 8): ").strip())
                    if clip_duration <= 0:
                        print("Clip duration must be a positive number.", file=sys.stderr)
                        continue
                    break
                except ValueError:
                    print("Please enter a valid number.", file=sys.stderr)
                attempt += 1
                if attempt == max_attempts:
                    print("Too many invalid attempts. Exiting.", file=sys.stderr)
                    sys.exit(1)
            print()
        else:
            # Portion-based splitting
            attempt = 0
            num_portions = None
            while attempt < max_attempts:
                try:
                    num_portions = int(input("Number of portions\n(ie. 4): ").strip())
                    if num_portions <= 0:
                        print("Number of portions must be a positive integer.", file=sys.stderr)
                        continue
                    if num_portions == 1:
                        print("Number of portions must be greater than 1.", file=sys.stderr)
                        continue
                    break
                except ValueError:
                    print("Please enter a valid integer.", file=sys.stderr)
                attempt += 1
                if attempt == max_attempts:
                    print("Too many invalid attempts. Exiting.", file=sys.stderr)
                    sys.exit(1)
            print()

        audio_choice = djj.prompt_choice("Audio handling? (1. Keep Original Audio, 2. Strip Audio, 3. Add Silent Audio Track)\n > ", ['1', '2', '3'], default='1')
        print()

        print("-------------")
        
        if split_method == '1':
            successful, failed, output_dirs = split_video_by_duration(input_path, clip_duration, include_subfolders, audio_choice)
        else:
            successful, failed, output_dirs = split_video_by_portions(input_path, num_portions, include_subfolders, audio_choice)
        
        print("\n" * 1)
        print("Splitting Summary")
        print("-------------")
        print(f"✅ Successfully split: {len(successful)} clips")
        if failed:
            print(f"Failed operations: {len(failed)} (see video_split_errors.log in output folders)")
        if output_dirs:
            print("Output folders:")
            for output_dir in sorted(output_dirs):
                print(f"  {output_dir}")
        else:
            print("No output folders created.")
        print("\n" * 2)

        if output_dirs:
            try:
                subprocess.run(['open', sorted(output_dirs)[0]], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error opening output folder: {e}", file=sys.stderr)

        action = djj.what_next()
        if action == 'exit':
            break