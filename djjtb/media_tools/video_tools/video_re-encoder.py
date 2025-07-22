import os
import sys
import pathlib
import subprocess
import logging
import djjtb.utils as djj

def reencode_videos(input_path, subfolders=False, audio_choice='1'):
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
        print("\033[33mError: Input must be a video file or directory.\033[0m", file=sys.stderr)
        return

    if not videos:
        print("\033[33mError: No video files found.\033[0m", file=sys.stderr)
        return

    codec_choice = djj.prompt_choice("\033[33mChoose codec\033[0m\n1. H.264, 2. H.265", ['1', '2'], default='1')
    if codec_choice == '1':
        codec = "libx264"
        crf = "23"
        suffix = "_reencoded"
        tag = ""
        print("\033[33mRe-encoding with H.264...\033[0m")
    else:
        codec = "libx265"
        crf = "28"
        suffix = "_hevc"
        tag = "-tag:v hvc1"
        print("\033[33mRe-encoding with H.265...\033[0m")

    output_base_dirs = []
    total_videos = len(videos)
    successful_videos = 0
    
    first_video_dir = os.path.dirname(videos[0])
    first_output_dir = os.path.join(first_video_dir, "Output", "Reencoded")
    os.makedirs(first_output_dir, exist_ok=True)
    logger = djj.setup_logging(first_output_dir, "reencode_videos")
    
    for i, video_path in enumerate(videos, 1):
        video_dir = os.path.dirname(video_path)
        output_base_dir = os.path.join(video_dir, "Output", "Reencoded")
        os.makedirs(output_base_dir, exist_ok=True)

        filename = os.path.basename(video_path)
        name = os.path.splitext(filename)[0]
        output = os.path.join(output_base_dir, f"{name}{suffix}.mp4")

        default_stream = "0"
        if audio_choice != '3':  # Only need stream mapping for non-silent audio
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
                logger.error(f"Error getting stream info for {filename}: {e}")

        progress = (i / total_videos) * 100
        sys.stdout.write(f"\033[33m\rProcessing \033[0m{i}/{total_videos} ({progress:.1f}%)...")
        sys.stdout.flush()
        
        cmd = ["ffmpeg", "-i", str(video_path)]
        if audio_choice != '3':
            cmd.extend(["-map", f"0:v:{default_stream}"])
        cmd.extend(djj.get_audio_options(audio_choice))
        cmd.extend(["-c:v", codec, "-preset", "medium", "-crf", crf])
        if tag:
            cmd.extend(tag.split())
        cmd.extend(["-y", output])
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"\033[33mRe-encoded\033[0m {filename} \033[33m to\033[0m {output}")
            successful_videos += 1
        except subprocess.CalledProcessError as e:
            logger.error(f"\033[33mError re-encoding\033[0m {filename}: {e.stderr}")
            print(f"\n\033[33mError re-encoding {filename}: {e.stderr}\033[0m")

        if output_base_dir not in output_base_dirs:
            output_base_dirs.append(output_base_dir)

    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()
    
    logger.info(f"\033[33mRe-encoded\033[0m {successful_videos} \033[33mof\033[0m {total_videos} \033[33mvideos successfully\033[0m")
    print("\n\033[33mRe-encoding Summary\033[0m")
    print("-------------------")
    print(f"\033[33mVideos processed:\033[0m {total_videos}")
    print(f"\033[33mVideos successfully re-encoded:\033[0m {successful_videos}")
    print(f"\033[33mOutput folder(s):\033[0m {', '.join(output_base_dirs)}")
    print()

    if output_base_dirs:
        try:
            subprocess.run(['open', output_base_dirs[0]], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"\033[33mError opening output folder: {e}\033[0m")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    while True:
        clear_screen()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mVideo Encoder\033[0m")
        print("Re-encode videos in a folder")
        print("\033[92m==================================================\033[0m")
        print()
        folder = input("\033[33mEnter path: \n -> \033[0m").strip()
        if not folder or not os.path.exists(folder):
            print("Invalid path.")
            continue
        print()
        include_sub = djj.prompt_choice("\033[33mInclude subfolders?\033[0m\n1. Yes, 2. No ", ['1', '2'], default='2') == '1'
        print()
        audio_choice = djj.prompt_choice("\033[33mAudio handling?\033[0m \n1. Keep Original Audio\n2. Strip Audio\n3. Add Silent Audio Track\n", ['1', '2', '3'], default='3')
        print()
        reencode_videos(folder, include_sub, audio_choice)

        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()