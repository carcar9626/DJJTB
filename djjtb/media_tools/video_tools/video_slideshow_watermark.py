#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
import shutil
from collections import defaultdict
import djjtb.utils as djj
os.system('clear')

# Block 1 – FFmpeg Helper
def get_video_dimensions(video_path):
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        output = result.stdout.strip().split('\n')
        width = int(float(output[0]))
        height = int(float(output[1]))
        duration = float(output[2])
        return duration, width, height
    except Exception as e:
        print(f"❌ ffprobe failed on {video_path}: {e}")
        return None, None, None

# Block 2 – Build slideshow
def build_slideshow(images, image_duration, video_duration, output_size, slideshow_path):
    concat_list = slideshow_path.with_suffix(".txt")
    loop_count = max(1, int(video_duration // (image_duration * len(images))) + 1)

    with open(concat_list, "w") as f:
        for _ in range(loop_count):
            for img in images:
                f.write(f"file '{os.path.abspath(img)}'\n")
                f.write(f"duration {image_duration}\n")
        f.write(f"file '{os.path.abspath(images[-1])}'\n")

    print(f"🛠️ Building slideshow for: {slideshow_path.name}")
    print(f"   {len(images)} images x {loop_count} loops → {loop_count * len(images)} total entries")

    safe_height = output_size if output_size % 2 == 0 else output_size - 1
    slideshow_filter = f"scale=-2:{safe_height}"
    
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-vf", slideshow_filter,
        "-pix_fmt", "yuv420p",
        "-color_range", "mpeg",
        "-t", str(video_duration),
        str(slideshow_path),
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not slideshow_path.exists() or slideshow_path.stat().st_size == 0:
        print(f"❌ Failed to generate slideshow: {slideshow_path.name}")
    else:
        print(f"✅ Slideshow created: {slideshow_path}")

    concat_list.unlink(missing_ok=True)

# Block 3 – Overlay slideshow with flexible positioning
def get_overlay_position(position_choice):
    """Get overlay position coordinates based on user choice"""
    positions = {
        '1': ('10', '10'),                    # Top-left
        '2': ('W-w-10', '10'),               # Top-right
        '3': ('10', 'H-h-10'),               # Bottom-left
        '4': ('W-w-10', 'H-h-10')            # Bottom-right (default)
    }
    return positions.get(position_choice, positions['4'])  # Default to bottom-right

def overlay_watermark(video_path, slideshow_path, output_path, scale_ratio, video_width, video_height, overlay_position):
    overlay_h = int(video_height * scale_ratio)

    # 🔍 Get actual slideshow width (after FFmpeg scales it)
    try:
        probe = subprocess.run([
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(slideshow_path)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        overlay_w = int(probe.stdout.strip())
    except:
        print(f"⚠️ Could not get slideshow width, using fallback.")
        overlay_w = int(video_width * 0.5)

    # Get position coordinates
    pos_x, pos_y = get_overlay_position(overlay_position)

    # ✅ FFmpeg: drop shadow matches scaled overlay exactly
    filter_complex = (
        f"[1:v]scale={overlay_w}:{overlay_h}[wm];"
        f"color=black@0.4:size={overlay_w}x{overlay_h}:duration=1[shadow];"
        f"[shadow][wm]overlay=3:3[wm_with_shadow];"
        f"[0:v][wm_with_shadow]overlay={pos_x}:{pos_y}"
    )

    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", str(slideshow_path),
        "-filter_complex", filter_complex,
        "-map", "0:a?",
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "fast",
        "-shortest",
        str(output_path)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Block 4 – Main processing
def process_folder(folder, image_duration, scale_ratio, overlay_position, is_flat_mode, base_output_dir=None):
    valid_exts = (".mp4", ".mov", ".webm")
    image_exts = (".jpg", ".jpeg", ".png", ".webp")
    videos = [f for f in os.listdir(folder) if f.lower().endswith(valid_exts)]
    if len(videos) != 1:
        print(f"⚠️ Skipping {folder}: needs exactly 1 video.")
        return

    video_path = os.path.join(folder, videos[0])
    video_stem = Path(video_path).stem

    images = sorted([
        os.path.join(folder, f) for f in os.listdir(folder)
        if f.lower().endswith(image_exts)
    ])
    if not images:
        print(f"⚠️ No matching images in {folder}, skipping.")
        return

    video_duration, video_width, video_height = get_video_dimensions(video_path)
    if not video_duration or not video_height:
        print(f"❌ Could not retrieve video info for {video_path}")
        return

    if is_flat_mode:
        out_slideshow = Path(base_output_dir) / "Slideshow"
        out_watermarked = Path(base_output_dir) / "Watermarked"
    else:
        out_slideshow = Path(folder)
        out_watermarked = Path(folder) / "WM_Output"

    out_slideshow.mkdir(parents=True, exist_ok=True)
    out_watermarked.mkdir(parents=True, exist_ok=True)

    slideshow_path = out_slideshow / f"{video_stem}_slideshow.mp4"
    build_slideshow(
        images,
        image_duration,
        video_duration,
        int(video_height * scale_ratio),
        slideshow_path
    )

    output_path = out_watermarked / f"{video_stem}_watermarked.mp4"
    overlay_watermark(video_path, slideshow_path, output_path, scale_ratio, video_width, video_height, overlay_position)

    print(f"✅ Done: {output_path}")
    print()
    
# Block 5 – Flat Mode Processor
def process_flat_mode(parent, image_duration, scale_ratio, overlay_position):
    valid_exts = (".mp4", ".mov", ".webm")
    image_exts = (".jpg", ".jpeg", ".png", ".webp")
    videos = [f for f in os.listdir(parent) if f.lower().endswith(valid_exts)]

    total = len(videos)
    for idx, video_file in enumerate(videos, 1):
        percent = int((idx / total) * 100)
        print(f"\033[93m📽️ Processing \033[0m{idx}\033[93m/\033[0m{total} \033[93mvideos\033[0m ({percent}%)\033[93m...\033[0m")
        video_path = os.path.join(parent, video_file)
        video_stem = Path(video_file).stem

        # Find matching images
        images = sorted([
            os.path.join(parent, f) for f in os.listdir(parent)
            if f.lower().endswith(image_exts) and Path(f).stem.startswith(video_stem)
        ])
        if not images:
            print(f"\033[93m⚠️ No matching images for\033[0m {video_file}, \033[93mskipping.\033[0m")
            continue

        # Get video info
        video_duration, video_width, video_height = get_video_dimensions(video_path)
        if not video_duration or not video_height:
            print(f"\033[93m❌ Could not retrieve video info for \033[0m{video_path}")
            continue

        # Prepare output directories
        base_output = Path(parent) / "Output"
        slides_dir = base_output / "Slideshow"
        watermarked_dir = base_output / "Watermarked"
        slides_dir.mkdir(parents=True, exist_ok=True)
        watermarked_dir.mkdir(parents=True, exist_ok=True)

        # Temp build folder
        temp_dir = Path(parent) / f"_TMP_{video_stem}"
        temp_dir.mkdir(exist_ok=True)

        slideshow_path = temp_dir / f"{video_stem}_slideshow.mp4"
        build_slideshow(
            images,
            image_duration,
            video_duration,
            int(video_height * scale_ratio),
            slideshow_path
        )

        if not slideshow_path.exists():
            print("⚠️ Could not get slideshow width, using fallback.")
            slideshow_path = ""

        final_slideshow = slides_dir / f"{video_stem}_slideshow.mp4"
        if slideshow_path:
            shutil.copy(str(slideshow_path), str(final_slideshow))

        output_path = watermarked_dir / f"{video_stem}_watermarked.mp4"
        overlay_watermark(video_path, slideshow_path, output_path, scale_ratio, video_width, video_height, overlay_position)

        # Clean temp if you want (can remove this later)
        shutil.rmtree(temp_dir, ignore_errors=True)

        print(f"✅ Done: {output_path}")
        print()  # Line break

# Block 6 – Main Loop
def main():
    print()
    print()
    print("\033[92m==================================================\033[0m")
    print("\033[1;93mSlideshow Watermark\033[0m")
    print("Generate slideshow from images, overlay on video")
    print("\033[92m==================================================\033[0m")
    print()
    
    while True:
        # Use proper path input handling
        parent = djj.get_path_input("📁 Enter path")
        print()
        
        mode = djj.prompt_choice(
            "📂 Are videos in subfolders?\n1. Yes (per-video subfolders), 2. No (flat folder) ",
            ['1', '2'],
            default='1'
        )
        is_flat_mode = mode == '2'
        print()

        # Use proper float input handling with defaults
        image_duration = djj.get_float_input(
            "🕒 Duration per image in seconds (default: 3): ",
            min_val=0.1,
            max_val=30.0
        )
        if image_duration is None:
            image_duration = 3.0
        print()

        # Use proper float input for scale ratio
        scale_percentage = djj.get_float_input(
            "📏 Overlay height as percentage of video (default: 30)",
            min_val=5.0,
            max_val=80.0
        )
        if scale_percentage is None:
            scale_percentage = 30.0
        scale_ratio = round(scale_percentage / 100, 2)
        print()

        # Get overlay position
        print("\033[93mOverlay Position:\033[0m")
        print("1. Top-left")
        print("2. Top-right")
        print("3. Bottom-left")
        print("4. Bottom-right")
        
        overlay_position = djj.prompt_choice(
            " \033[93mChoice \033[0m ",
            ['1', '2', '3', '4'],
            default='4'
        )
        print()

        if is_flat_mode:
            process_flat_mode(parent, image_duration, scale_ratio, overlay_position)
            djj.prompt_open_folder(parent)
        else:
            subdirs = [os.path.join(parent, d) for d in os.listdir(parent)
                       if os.path.isdir(os.path.join(parent, d))]
            total = len(subdirs)
            for idx, sub in enumerate(subdirs, 1):
                percent = int((idx / total) * 100)
                print(f"\033[93m📽️ Processing\033[0m {idx}\033[93m/\033[0m{total} \033[93mvideos\033[0m ({percent}%)\033[93m...\033[0m")
                process_folder(sub, image_duration, scale_ratio, overlay_position, False)
                print ("\n" * 2)
            djj.prompt_open_folder(parent)

        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()