import os
import sys
import subprocess
import logging
from pathlib import Path
import djjtb.utils as djj

os.system('clear')

LOG_DIR = Path("~/Documents/Scripts/DJJTB/djjtb/logs").expanduser()
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Maps ffprobe audio codec_name -> output extension for Direct Copy mode.
# Unrecognized codecs fall back to their own name as the extension.
AUDIO_CODEC_EXT = {
    'aac': 'm4a', 'alac': 'm4a', 'mp3': 'mp3', 'flac': 'flac',
    'opus': 'opus', 'vorbis': 'ogg', 'ac3': 'ac3', 'eac3': 'eac3',
    'dts': 'dts', 'wmav2': 'wma', 'wmapro': 'wma', 'wmalossless': 'wma',
    'pcm_s16le': 'wav', 'pcm_s24le': 'wav', 'pcm_s32le': 'wav', 'pcm_f32le': 'wav',
}


def get_op_logger():
    log_file = LOG_DIR / "video_audio_extractor_log.txt"
    logger = logging.getLogger('djjtb.video_audio_extractor')
    logger.setLevel(logging.INFO)
    logger.handlers = []
    logger.propagate = False
    handler = logging.FileHandler(log_file, mode='a')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)
    logger.info("===== RUN START =====")
    return logger


def is_video_file(filename):
    return Path(filename).suffix.lower() in djj.VIDEO_EXTENSIONS


# ─── Format selection (the "double enter" combo picker) ────────────────────

FORMAT_LABELS = {
    '1': 'Direct Copy (source codec, matching ext)',
    '2': 'MP3 320kbps',
    '3': 'WAV (HQ, lossless)',
}


def get_format_choices():
    print("\033[93mOutput format(s):\033[0m")
    print("1. Direct Copy (same codec, matching ext)")
    print("2. MP3 320kbps")
    print("3. WAV (HQ, lossless)")
    print("4. All of the above")
    print()
    return djj.get_multi_choice(
        "\033[93mEnter a number, Enter to add another, blank Enter when done:\033[0m",
        FORMAT_LABELS, allow_all_key='4'
    )


# ─── Extraction ──────────────────────────────────────────────────────────

def get_audio_codec(video_path):
    """Returns the first audio stream's codec_name, or '' if none."""
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(video_path)
        ], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        return ""


def extract_direct_copy(video_path, out_dir, codec, avoid_exts, logger=None):
    ext = AUDIO_CODEC_EXT.get(codec, codec or 'm4a')
    filename = f"{video_path.stem}.{ext}"
    if ext in avoid_exts:
        filename = f"{video_path.stem}_original.{ext}"
    output = out_dir / filename
    cmd = ["ffmpeg", "-i", str(video_path), "-vn", "-acodec", "copy", "-y", str(output)]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    if logger:
        logger.info(f"Direct-copied audio from {video_path.name} ({codec}) -> {output.name}")
    return output


def extract_mp3(video_path, out_dir, codec, avoid_exts, logger=None):
    output = out_dir / f"{video_path.stem}.mp3"
    cmd = ["ffmpeg", "-i", str(video_path), "-vn", "-acodec", "libmp3lame", "-b:a", "320k", "-y", str(output)]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    if logger:
        logger.info(f"Extracted MP3 320k from {video_path.name} -> {output.name}")
    return output


def extract_wav(video_path, out_dir, codec, avoid_exts, logger=None):
    output = out_dir / f"{video_path.stem}.wav"
    cmd = ["ffmpeg", "-i", str(video_path), "-vn", "-acodec", "pcm_s16le", "-y", str(output)]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    if logger:
        logger.info(f"Extracted HQ WAV from {video_path.name} -> {output.name}")
    return output


EXTRACTORS = {
    '1': ('Direct Copy', extract_direct_copy),
    '2': ('MP3 320k', extract_mp3),
    '3': ('WAV HQ', extract_wav),
}
# ext that Direct Copy must avoid colliding with, per other selected mode
REENCODE_EXT_BY_KEY = {'2': 'mp3', '3': 'wav'}


def run_extraction(videos, format_choices):
    logger = get_op_logger()
    total = len(videos)
    successful = 0
    skipped_no_audio = 0
    output_dirs = set()

    avoid_exts = {REENCODE_EXT_BY_KEY[k] for k in format_choices if k in REENCODE_EXT_BY_KEY}

    for i, video_path in enumerate(videos, 1):
        progress = (i / total) * 100
        sys.stdout.write(f"\033[93m\rProcessing \033[0m{i}/{total} ({progress:.1f}%)...")
        sys.stdout.flush()

        codec = get_audio_codec(video_path)
        if not codec:
            sys.stdout.write("\r" + " " * 60 + "\r")
            print(f"\033[93m⚠️  No audio stream, skipping: {video_path.name}\033[0m")
            logger.info(f"No audio stream, skipped: {video_path.name}")
            skipped_no_audio += 1
            continue

        out_dir = video_path.parent / "Output" / "Video_to_Audio"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_dirs.add(out_dir)

        ok_this_video = True
        for key in format_choices:
            label, func = EXTRACTORS[key]
            try:
                func(video_path, out_dir, codec, avoid_exts, logger)
            except subprocess.CalledProcessError as e:
                ok_this_video = False
                logger.error(f"Error extracting {label} from {video_path.name}: {e.stderr}")
                print(f"\n\033[93mError extracting {label} from {video_path.name}\033[0m")

        if ok_this_video:
            successful += 1

        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()

    summary = f"Extracted audio from {successful} of {total} videos ({skipped_no_audio} skipped, no audio)"
    logger.info(summary)
    print("\n\033[93mAudio Extraction Summary\033[0m")
    print("------------------------")
    print(f"\033[93mVideos processed:\033[0m {total}")
    print(f"\033[93mSuccessful:\033[0m {successful}")
    if skipped_no_audio:
        print(f"\033[93mSkipped (no audio):\033[0m {skipped_no_audio}")
    print(f"\033[93mFormats:\033[0m {', '.join(EXTRACTORS[k][0] for k in format_choices)}")
    print(f"\033[93mOutput folder(s):\033[0m {len(output_dirs)}")
    print()
    if output_dirs:
        djj.prompt_open_folder(str(sorted(output_dirs)[0]))


# ─── Input collection ────────────────────────────────────────────────────

def get_videos_input():
    input_mode = djj.prompt_choice(
        "\033[93mInput mode:\033[0m\n1. Folder path\n2. Multiple files / folders (space-separated or Finder drag)\n3. Path list from txt file\n",
        ['1', '2', '3'],
        default='1'
    )
    print()

    videos = []

    if input_mode == '1':
        input_path = djj.get_path_input("📁 Enter folder path")
        print()
        include_sub = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No ",
            ['1', '2'], default='2'
        ) == '1'
        print()
        videos = djj.collect_videos_from_folder(input_path, include_sub)

    elif input_mode == '2':
        raw_files = djj.get_multifile_input(
            "📁 Enter video paths",
            extensions=djj.VIDEO_EXTENSIONS
        )
        videos = [f for f in raw_files if is_video_file(f)]
        print()

    else:
        paths = djj.get_paths_from_txt("Enter txt file path")
        for p in paths:
            p_obj = Path(p)
            if p_obj.is_file() and is_video_file(p_obj.name):
                videos.append(str(p_obj))
            elif p_obj.is_dir():
                videos.extend(djj.collect_videos_from_folder(str(p_obj)))
        videos = sorted(videos, key=str.lower)
        print()

    return [Path(v) for v in videos]


def main():
    print("\033[92m==================================================\033[0m")
    print("\033[1;33mVideo to Audio Extractor\033[0m")
    print("\033[92m==================================================\033[0m")
    print()

    while True:
        videos = get_videos_input()
        if not videos:
            print("❌ \033[93mNo valid video files found. Try again.\033[0m\n")
            continue

        print(f"✅ \033[93m{len(videos)} video(s) found\033[0m")
        print()

        format_choices = get_format_choices()
        print()

        run_extraction(videos, format_choices)

        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()
