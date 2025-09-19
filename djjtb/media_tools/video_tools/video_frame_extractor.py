import os
import sys
import pathlib
import subprocess
import json
import logging
from pathlib import Path
import djjtb.utils as djj

os.system('clear')


def prompt_integer(prompt, min_value=1):
    while True:
        try:
            value = int(input(f"{prompt}: ").strip())
            if value >= min_value:
                return value
            else:
                print(f"\033[93mPlease enter a number >\033[0m= {min_value}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def extract_frames(input_path, subfolders=False, frame_interval=None):
    input_path_obj = pathlib.Path(input_path)
    video_extensions = ('.mp4', '.mkv', '.webm', '.mov')
    
    videos = []
    if input_path_obj.is_file() and input_path_obj.suffix.lower() in video_extensions:
        videos = [input_path_obj]
    elif input_path_obj.is_dir():
        if subfolders:
            for root, _, files in os.walk(input_path):
                videos.extend(pathlib.Path(root) / f for f in files if pathlib.Path(f).suffix.lower() in video_extensions)
        else:
            videos = [f for f in input_path_obj.glob('*') if f.suffix.lower() in video_extensions and f.is_file()]
    else:
        print("\033[93mError: Input must be a video file or directory.\033[0m", file=sys.stderr)
        return
    
    if len(videos) == 0:
        print("\033[93mError: No video files found.\033[0m", file=sys.stderr)
        return
    
    if frame_interval is None:
        frame_interval = prompt_integer("Enter the frame interval, \n (e.g., 10 for every 10th frame): ", min_value=1)
    
    output_base_dirs = []
    total_videos = len(videos)
    
    first_video_dir = os.path.dirname(videos[0])
    first_output_dir = os.path.join(first_video_dir, "Output", "Frames")
    os.makedirs(first_output_dir, exist_ok=True)
    logger = djj.setup_logging(first_output_dir, "video_frame_extractor")
    
    for i, video_path in enumerate(videos, 1):
        video_name = Path(video_path).stem
        video_dir = os.path.dirname(video_path)
        output_base_dir = os.path.join(video_dir, "Output", "Frames", video_name)
        Path(output_base_dir).mkdir(parents=True, exist_ok=True)
        
        progress = (i / total_videos) * 100
        sys.stdout.write(f"\rProcessing {i}/{total_videos} ({progress:.1f}%)...")
        sys.stdout.flush()
        
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
                if nb_frames and abs(nb_frames - expected_frames) > 0.1 * expected_frames:
                    logger.warning(f"Frame count mismatch for {video_name}: ffprobe reports {nb_frames} frames, but duration ({duration}s) * frame_rate ({frame_rate}) suggests {expected_frames} frames. Using {expected_frames}.")
                    nb_frames = expected_frames
                elif not nb_frames:
                    nb_frames = expected_frames
        except (subprocess.CalledProcessError, KeyError, ValueError) as e:
            logger.error(f"Error retrieving video info for {video_path}: {e}")
            nb_frames = 0
            frame_rate = 0
        
        try:
            total_images = max(1, int(nb_frames / frame_interval))
            
            if total_images > 3000:
                sys.stdout.write(f"\r{' ' * 60}\r")
                sys.stdout.flush()
                print(f"\n\033[93mWarning: \033[0m{total_images} \033[93mimages will be extracted from \033[0m{video_name}\033[93m.\033[0m")
                proceed = djj.prompt_choice("\033[93mThis is a large number of frames. Do you want to proceed?\033[0m\n1. Yes, 2. No ", ['1', '2'], default='2')
                if proceed != '1':
                    print(f"\033[93mFrame extraction cancelled for \033[0m{video_name}\033[93m.\033[0m")
                    logger.info(f"Frame extraction cancelled for {video_name} (user choice)")
                    output_base_dirs.append(output_base_dir)
                    continue
        except (subprocess.CalledProcessError, KeyError, ValueError) as e:
            logger.error(f"Error estimating frames for {video_path}: {e}")
            total_images = 0
        
        cmd = [
            'ffmpeg', '-i', str(video_path), '-vf', f'select=not(mod(n\,{frame_interval}))',
            '-vsync', '0', '-q:v', '2', f'{output_base_dir}/{video_name}_F%03d.jpg'
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            extracted_files = len([f for f in os.listdir(output_base_dir) if f.endswith('.jpg')])
            logger.info(f"Extracted {extracted_files} frames for {video_name} to {output_base_dir}")
            
            if total_images > 0 and (extracted_files > total_images * 1.2 or extracted_files < total_images * 0.8):
                logger.warning(f"Expected {total_images} frames, but extracted {extracted_files} for {video_name}. This may indicate an issue with frame extraction.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error processing {video_name}: {e.stderr}")
            sys.stdout.write(f"\r{' ' * 60}\r")
            sys.stdout.flush()
            print(f"\033[93mError processing\033[0m {video_name}: {e.stderr}")
        
        output_base_dirs.append(output_base_dir)
    
    sys.stdout.write(f"\r{' ' * 60}\r")
    sys.stdout.flush()
    
    logger.info(f"\033[93mFrame extraction complete for \033[0m{total_videos}\033[93m videos\033[0m")
    print()
    print("\n\033[93mFrame Extraction Summary\033[0m")
    print("------------------------")
    print(f"\033[93mVideos processed:\033[0m {total_videos}")
    print(f"\033[93mFrame interval:\033[0m {frame_interval}")
    print(f"\033[93mOutput folder(s):\033[0m {len(output_base_dirs)} \033[93mcreated.\033[0m")
    print()
    
    djj.prompt_open_folder(output_base_dir)
    
    return output_base_dirs

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    while True:
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mFrame Extractor\033[0m")
        print("Extract frames from videos")
        print("\033[92m==================================================\033[0m")
        print()
        
        folder = input("\033[93mEnter path: \n -> \033[0m").strip()
        if not folder or not os.path.exists(folder):
            print("\033[93mInvalid path.\033[0m")
            continue
        
        include_sub = djj.prompt_choice("\033[93mInclude subfolders? \033[0m\n1. Yes, 2. No ", ['1', '2'], default='2') == '1'
        print()
        
        extract_frames(folder, include_sub)
        
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()