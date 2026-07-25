import os
import sys
import subprocess
import djjtb.utils as djj
from pathlib import Path
os.system('clear')

# ── Encoding Config (defaults — overridden at runtime by prompt) ──────────────
VIDEO_BITRATE = '15000k'             # Used with h264_videotoolbox only
VIDEO_CRF = '18'                     # Used with libx264 only
VIDEO_PRESET = 'fast'                # Used with libx264 only

VIDEO_EXTENSIONS = ('.mp4', '.mov', '.mkv', '.avi', '.webm')


def is_video_file(filename):
    return filename.lower().endswith(VIDEO_EXTENSIONS)

def run_ffmpeg(cmd):
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg failed for command: {' '.join(cmd)}")

def get_video_fps(video_path):
    """Get fps from video file via ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=r_frame_rate",
             "-of", "default=noprint_wrappers=1:nokey=1",
             str(video_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        fps_raw = result.stdout.strip()
        if '/' in fps_raw:
            num, den = fps_raw.split('/')
            return round(int(num) / int(den), 3)
        return float(fps_raw)
    except Exception:
        return 30

def get_duration(video_path):
    """Get video duration in seconds via ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def encoder_flags(encoder):
    """Return quality flags for the chosen encoder."""
    if encoder == 'h264_videotoolbox':
        return ['-b:v', VIDEO_BITRATE]
    else:
        return ['-preset', VIDEO_PRESET, '-crf', VIDEO_CRF]

def get_atempo_chain(speed):
    """Chain atempo filters so audio tracks any speed, not just ffmpeg's native 0.5-2.0 range."""
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


def reverse_and_merge(video_path, index, total, speed_factor, input_base, encoder, audio_choice):
    folder, filename = os.path.split(video_path)
    name, ext = os.path.splitext(filename)
    ext = ext.lower()
    fps = get_video_fps(video_path)
    source_duration = get_duration(video_path)

    output_base = Path(folder) / "Output"
    reversed_dir = output_base / "Reversed"
    merged_dir = output_base / "Merge"
    reversed_dir.mkdir(parents=True, exist_ok=True)
    merged_dir.mkdir(parents=True, exist_ok=True)

    reversed_file = reversed_dir / f"{name}_reversed{ext}"
    normalized_file = reversed_dir / f"{name}_normalized{ext}"
    merged_file = merged_dir / f"{name}_merged{ext}"

    audio_flags = djj.get_audio_options(audio_choice)

    vf_filter = "reverse,select='gt(n,0)',setpts=PTS-STARTPTS"
    af_filter = "areverse"
    if speed_factor and speed_factor != 1.0:
        vf_filter += f",setpts={1/speed_factor}*PTS"
        if audio_choice == '1':
            atempo_chain = get_atempo_chain(speed_factor)
            if atempo_chain:
                af_filter += f",{atempo_chain}"

    # Step 1: Create reversed clip
    run_ffmpeg([
        'ffmpeg', '-y',
        '-i', str(video_path),
        '-vf', vf_filter,
        *([ '-af', af_filter ] if audio_choice == '1' else []),
        '-c:v', encoder,
        *encoder_flags(encoder),
        *audio_flags,
        '-r', str(fps),
        str(reversed_file)
    ])

    if not reversed_file.exists():
        raise RuntimeError(f"Failed to create reversed file: {reversed_file}")

    # Step 2: Re-encode original to normalize timestamps
    run_ffmpeg([
        'ffmpeg', '-y',
        '-i', str(video_path),
        '-c:v', encoder,
        *encoder_flags(encoder),
        *audio_flags,
        '-r', str(fps),
        str(normalized_file)
    ])

    if not normalized_file.exists():
        raise RuntimeError(f"Failed to create normalized file: {normalized_file}")

    # Step 3: Concat normalized original + reversed
    concat_list = Path(folder) / f'concat_temp_{index}.txt'
    with open(concat_list, 'w') as f:
        f.write(f"file '{normalized_file}'\n")
        f.write(f"file '{reversed_file}'\n")

    run_ffmpeg([
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_list),
        '-c:v', encoder,
        *encoder_flags(encoder),
        *audio_flags,
        str(merged_file)
    ])

    if not merged_file.exists():
        raise RuntimeError(f"Failed to create merged file: {merged_file}")

    # Step 4: Trim 3 frames from start, clip tail to exact expected duration
    trim_start_frames = 3
    clean_duration = round((source_duration * 2) - round(trim_start_frames / fps, 6), 6)
    trimmed_file = merged_dir / f"{name}_merged_trim{ext}"

    trim_vf = f'select=gte(n\\,{trim_start_frames}),setpts=PTS-STARTPTS'
    trim_cmd = [
        'ffmpeg', '-y',
        '-i', str(merged_file),
        '-vf', trim_vf,
        *([ '-af', f'aselect=gte(n\\,{trim_start_frames}),asetpts=PTS-STARTPTS' ] if audio_choice == '1' else []),
        '-t', str(clean_duration),
        '-c:v', encoder,
        *encoder_flags(encoder),
        *audio_flags,
        str(trimmed_file)
    ]
    run_ffmpeg(trim_cmd)

    merged_file.unlink(missing_ok=True)
    trimmed_file.rename(merged_file)

    concat_list.unlink(missing_ok=True)
    normalized_file.unlink(missing_ok=True)


def collect_videos_from_folder(input_path, subfolders=False):
    input_path_obj = Path(input_path)
    videos = []
    if input_path_obj.is_dir():
        if subfolders:
            for root, _, files in os.walk(input_path):
                videos.extend(Path(root) / f for f in files if Path(f).suffix.lower() in VIDEO_EXTENSIONS)
        else:
            videos = [f for f in input_path_obj.glob('*') if f.suffix.lower() in VIDEO_EXTENSIONS and f.is_file()]
    return sorted([str(v) for v in videos], key=str.lower)

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
                return 1.0
    return 1.0


def main():
    print("\033[92m==================================================\033[0m")
    print("\033[1;33mVideo Reverse Merge\033[0m")
    print("Reverse & merge with speed options")
    print("\033[92m==================================================\033[0m")
    print()

    while True:
        # Input mode
        input_mode = djj.prompt_choice(
            "\033[93mInput mode:\033[0m\n1. Folder path\n2. Multiple files / folders (space-separated or Finder drag)\n3. Path list from txt file\n",
            ['1', '2', '3'],
            default='1'
        )
        print()

        videos = []
        include_sub = False
        input_path = None

        if input_mode == '1':
            input_path = djj.get_path_input("Enter folder path")
            print()
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No ",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            videos = collect_videos_from_folder(input_path, include_sub)

        elif input_mode == '2':
            raw_files = djj.get_multifile_input(
                "📁 Enter video paths",
                extensions=VIDEO_EXTENSIONS
            )
            videos = [f for f in raw_files if is_video_file(f)]
            if videos:
                input_path = str(Path(videos[0]).parent)
            print()

        else:  # txt file
            paths = djj.get_paths_from_txt("Enter txt file path")
            for p in paths:
                p_obj = Path(p)
                if p_obj.is_file() and is_video_file(p_obj.name):
                    videos.append(str(p_obj))
                elif p_obj.is_dir():
                    videos.extend(collect_videos_from_folder(str(p_obj)))
            videos = sorted(videos, key=str.lower)
            if videos:
                input_path = str(Path(videos[0]).parent)
            print()

        if not videos:
            print("❌ \033[93mNo valid video files found. Try again.\033[0m\n")
            continue

        print(f"✅ \033[93m{len(videos)} video(s) found\033[0m")
        print()

        # Encoder choice
        encoder_choice = djj.prompt_choice(
            "\033[93mEncoder:\033[0m\n1. h264_videotoolbox  (fast, Apple Silicon)\n2. libx264            (quality, slower)\n",
            ['1', '2'],
            default='1'
        )
        encoder = 'h264_videotoolbox' if encoder_choice == '1' else 'libx264'
        print()

        # Audio choice
        audio_choice = djj.prompt_choice(
            "\033[93mAudio:\033[0m\n1. Keep original\n2. Strip audio  (recommended)\n3. Add silent track\n",
            ['1', '2', '3'],
            default='2'
        )
        print()

        speed_factor = ask_speed_factor()
        print()
        print("-------------")

        total = len(videos)
        successful = 0
        failed = []

        prefix = f"\033[93mProcessing video\033[0m {total}\033[93m/\033[0m{total}: "
        max_name_len = max(len(os.path.basename(v)[:30] + ("..." if len(os.path.basename(v)) > 30 else "")) for v in videos) + len(prefix) + 10

        for idx, vid_path in enumerate(videos, 1):
            display_name = os.path.basename(vid_path)[:30] + "..." if len(os.path.basename(vid_path)) > 30 else os.path.basename(vid_path)
            sys.stdout.write(f"\r\033[93mProcessing video\033[0m {idx}\033[93m/\033[0m{total}: {display_name}")
            sys.stdout.flush()
            try:
                reverse_and_merge(vid_path, idx, total, speed_factor, input_path, encoder, audio_choice)
                successful += 1
            except Exception as e:
                failed.append((os.path.basename(vid_path), str(e)))

        sys.stdout.write("\r" + " " * max_name_len + "\r")
        sys.stdout.flush()

        print()
        print("\033[93mReverse Merge Summary\033[0m")
        print("---------------------")
        print(f"\033[93mSuccessfully processed:\033[0m {successful} \033[93mvideos\033[0m")
        if failed:
            print("\033[93mFailed processing:\033[0m")
            for name, error in failed:
                print(f"  {name}: {error}")

        if include_sub and input_mode == '1':
            print(f"\033[93mOutput folders created in each processed directory\033[0m")
            print(f"\033[93mMain input folder: \033[0m\n{input_path}")
            print("\n" * 2)
            djj.prompt_open_folder(input_path)
        else:
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
