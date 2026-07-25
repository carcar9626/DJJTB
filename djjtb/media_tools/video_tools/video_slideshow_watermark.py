#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
import shutil
from collections import defaultdict
import djjtb.utils as djj
os.system('clear')

VIDEO_EXTS = (".mp4", ".mov", ".webm")
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")

# Block 1 – FFmpeg Helper
def get_video_info(video_path):
    """Returns (duration, width, height, fps) from a video file."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate",
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
        # r_frame_rate comes as a fraction e.g. "30000/1001" or "30/1"
        fps_raw = output[2]
        if '/' in fps_raw:
            num, den = fps_raw.split('/')
            fps = round(int(num) / int(den), 3)
        else:
            fps = float(fps_raw)
        duration = float(output[3])
        return duration, width, height, fps
    except Exception as e:
        print(f"❌ ffprobe failed on {video_path}: {e}")
        return None, None, None, None

def get_image_dimensions(image_path):
    """Get image dimensions using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "default=noprint_wrappers=1:nokey=1",
                image_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        output = result.stdout.strip().split('\n')
        width = int(float(output[0]))
        height = int(float(output[1]))
        return width, height
    except Exception as e:
        print(f"⚠️ Could not get image dimensions for {image_path}: {e}")
        return 1920, 1080  # fallback

# Block 2 – Build slideshow
def build_slideshow(images, image_duration, video_duration, output_size, slideshow_path, fps=30):
    concat_list = slideshow_path.with_suffix(".txt")
    loop_count = max(1, int(video_duration // (image_duration * len(images))) + 1)

    with open(concat_list, "w") as f:
        for _ in range(loop_count):
            for img in images:
                f.write(f"file '{os.path.abspath(img)}'\n")
                f.write(f"duration {image_duration}\n")
        f.write(f"file '{os.path.abspath(images[-1])}'\n")

    print(f"🛠️ Building slideshow for: {slideshow_path.name}")
    print(f"   {len(images)} images x {loop_count} loops → {loop_count * len(images)} total entries | {fps}fps")

    safe_height = output_size if output_size % 2 == 0 else output_size - 1
    slideshow_filter = f"scale=-2:{safe_height}"

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-vf", slideshow_filter,
        "-r", str(fps),
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

def build_slideshow_native_size(images, image_duration, video_duration, output_path, fps=30):
    """
    Build a slideshow using the native dimensions of the first image.
    Used in Slideshow Only mode.
    """
    concat_list = output_path.with_suffix(".txt")
    loop_count = max(1, int(video_duration // (image_duration * len(images))) + 1)

    # Get native dimensions from first image
    img_w, img_h = get_image_dimensions(str(images[0]))
    safe_w = img_w if img_w % 2 == 0 else img_w - 1
    safe_h = img_h if img_h % 2 == 0 else img_h - 1

    with open(concat_list, "w") as f:
        for _ in range(loop_count):
            for img in images:
                f.write(f"file '{os.path.abspath(img)}'\n")
                f.write(f"duration {image_duration}\n")
        f.write(f"file '{os.path.abspath(images[-1])}'\n")

    print(f"🛠️ Building slideshow: {output_path.name}")
    print(f"   {len(images)} image(s) | {image_duration}s/slide | {safe_w}x{safe_h} | {fps}fps | {loop_count} loop(s)")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-vf", f"scale={safe_w}:{safe_h}",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        "-color_range", "mpeg",
        "-t", str(video_duration),
        str(output_path),
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not output_path.exists() or output_path.stat().st_size == 0:
        print(f"❌ Failed to generate slideshow: {output_path.name}")
    else:
        print(f"✅ Slideshow created: {output_path}")

    concat_list.unlink(missing_ok=True)

# Block 3 – Overlay slideshow with flexible positioning
def get_overlay_position(position_choice):
    """Get overlay position coordinates based on user choice"""
    positions = {
        '1': ('10', '10'),
        '2': ('W-w-10', '10'),
        '3': ('10', 'H-h-10'),
        '4': ('W-w-10', 'H-h-10')
    }
    return positions.get(position_choice, positions['4'])

def overlay_watermark(video_path, slideshow_path, output_path, scale_ratio, video_width, video_height, overlay_position):
    overlay_h = int(video_height * scale_ratio)

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

    pos_x, pos_y = get_overlay_position(overlay_position)

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

# Block 4 – Split images for 2-slideshow mode
def split_images_for_two(images):
    """
    Split a list of images into two groups as evenly as possible.
    Extra image goes to group 1. If only 1 image, both groups get it.
    Examples: 1→[1],[1]  2→[1],[1]  3→[2],[1]  4→[2],[2]  5→[3],[2]
    """
    if len(images) == 0:
        return [], []
    if len(images) == 1:
        return [images[0]], [images[0]]

    mid = (len(images) + 1) // 2  # ceiling division → group1 gets the extra
    return images[:mid], images[mid:]

# Block 5 – Slideshow Only mode processors
def process_slideshow_only_folder(folder, image_duration, image_duration2, num_slideshows):
    """
    Process a single subfolder for Slideshow Only mode.
    Finds 1 video (for duration reference) and all images, then builds slideshows.
    """

    videos = [f for f in os.listdir(folder) if f.lower().endswith(VIDEO_EXTS)]
    if len(videos) != 1:
        print(f"⚠️ Skipping {folder}: needs exactly 1 video as duration reference.")
        return

    video_path = os.path.join(folder, videos[0])
    video_stem = Path(video_path).stem

    images = sorted([
        os.path.join(folder, f) for f in os.listdir(folder)
        if f.lower().endswith(IMAGE_EXTS)
    ])
    if not images:
        print(f"⚠️ No images found in {folder}, skipping.")
        return

    video_duration, _, _, fps = get_video_info(video_path)
    if not video_duration:
        print(f"❌ Could not retrieve video duration for {video_path}")
        return

    # Output sits right beside the reference video
    if num_slideshows == 1:
        out_path = Path(folder) / f"{video_stem}_slideshow.mp4"
        build_slideshow_native_size(images, image_duration, video_duration, out_path, fps=fps)
    else:
        group1, group2 = split_images_for_two(images)
        durations = [image_duration, image_duration2]
        for idx, (group, dur) in enumerate(zip([group1, group2], durations), 1):
            out_path = Path(folder) / f"{video_stem}_slideshow{idx}.mp4"
            build_slideshow_native_size(group, dur, video_duration, out_path, fps=fps)

    print()

def process_slideshow_only_flat(parent, image_duration, image_duration2, num_slideshows):
    """
    Flat mode for Slideshow Only: each video pairs with matching-stem images.
    """

    videos = sorted([f for f in os.listdir(parent) if f.lower().endswith(VIDEO_EXTS)])
    total = len(videos)

    if total == 0:
        print("⚠️ No videos found in folder.")
        return


    for idx, video_file in enumerate(videos, 1):
        percent = int((idx / total) * 100)
        print(f"\033[93m📽️ Processing \033[0m{idx}\033[93m/\033[0m{total} \033[93mvideos\033[0m ({percent}%)\033[93m...\033[0m")

        video_path = os.path.join(parent, video_file)
        video_stem = Path(video_file).stem

        images = sorted([
            os.path.join(parent, f) for f in os.listdir(parent)
            if f.lower().endswith(IMAGE_EXTS) and Path(f).stem.startswith(video_stem)
        ])
        if not images:
            print(f"\033[93m⚠️ No matching images for\033[0m {video_file}\033[93m, skipping.\033[0m")
            continue

        video_duration, _, _, fps = get_video_info(video_path)
        if not video_duration:
            print(f"❌ Could not retrieve video duration for {video_path}")
            continue

        # Output sits right beside the reference video
        if num_slideshows == 1:
            out_path = Path(parent) / f"{video_stem}_slideshow.mp4"
            build_slideshow_native_size(images, image_duration, video_duration, out_path, fps=fps)
        else:
            group1, group2 = split_images_for_two(images)
            durations = [image_duration, image_duration2]
            for grp_idx, (group, dur) in enumerate(zip([group1, group2], durations), 1):
                out_path = Path(parent) / f"{video_stem}_slideshow{grp_idx}.mp4"
                build_slideshow_native_size(group, dur, video_duration, out_path, fps=fps)

        print()

# Block 6 – Original Slideshow + Watermark processors
def process_folder(folder, image_duration, scale_ratio, overlay_position, is_flat_mode, parent=None):
    videos = [f for f in os.listdir(folder) if f.lower().endswith(VIDEO_EXTS)]
    if len(videos) != 1:
        print(f"⚠️ Skipping {folder}: needs exactly 1 video.")
        return

    video_path = os.path.join(folder, videos[0])
    video_stem = Path(video_path).stem

    images = sorted([
        os.path.join(folder, f) for f in os.listdir(folder)
        if f.lower().endswith(IMAGE_EXTS)
    ])
    if not images:
        print(f"⚠️ No matching images in {folder}, skipping.")
        return

    video_duration, video_width, video_height, fps = get_video_info(video_path)
    if not video_duration or not video_height:
        print(f"❌ Could not retrieve video info for {video_path}")
        return

    root = Path(parent) if parent else Path(folder)
    out_slideshow = root / "Slideshows"
    out_watermarked = root / "Watermarked"

    out_slideshow.mkdir(parents=True, exist_ok=True)
    out_watermarked.mkdir(parents=True, exist_ok=True)

    slideshow_path = out_slideshow / f"{video_stem}_slideshow.mp4"
    build_slideshow(
        images,
        image_duration,
        video_duration,
        int(video_height * scale_ratio),
        slideshow_path,
        fps=fps
    )

    output_path = out_watermarked / f"{video_stem}_watermarked.mp4"
    overlay_watermark(video_path, slideshow_path, output_path, scale_ratio, video_width, video_height, overlay_position)

    print(f"✅ Done: {output_path}")
    print()

def process_flat_mode(parent, image_duration, scale_ratio, overlay_position):
    videos = [f for f in os.listdir(parent) if f.lower().endswith(VIDEO_EXTS)]

    total = len(videos)
    for idx, video_file in enumerate(videos, 1):
        percent = int((idx / total) * 100)
        print(f"\033[93m📽️ Processing \033[0m{idx}\033[93m/\033[0m{total} \033[93mvideos\033[0m ({percent}%)\033[93m...\033[0m")
        video_path = os.path.join(parent, video_file)
        video_stem = Path(video_file).stem

        images = sorted([
            os.path.join(parent, f) for f in os.listdir(parent)
            if f.lower().endswith(IMAGE_EXTS) and Path(f).stem.startswith(video_stem)
        ])
        if not images:
            print(f"\033[93m⚠️ No matching images for\033[0m {video_file}, \033[93mskipping.\033[0m")
            continue

        video_duration, video_width, video_height, fps = get_video_info(video_path)
        if not video_duration or not video_height:
            print(f"\033[93m❌ Could not retrieve video info for \033[0m{video_path}")
            continue

        slides_dir = Path(parent) / "Slideshows"
        watermarked_dir = Path(parent) / "Watermarked"
        slides_dir.mkdir(parents=True, exist_ok=True)
        watermarked_dir.mkdir(parents=True, exist_ok=True)

        slideshow_path = slides_dir / f"{video_stem}_slideshow.mp4"
        build_slideshow(
            images,
            image_duration,
            video_duration,
            int(video_height * scale_ratio),
            slideshow_path,
            fps=fps
        )

        output_path = watermarked_dir / f"{video_stem}_watermarked.mp4"
        overlay_watermark(video_path, slideshow_path, output_path, scale_ratio, video_width, video_height, overlay_position)

        print(f"✅ Done: {output_path}")
        print()

# Block 7 – Image Join (Mode 3)
# get_join_dimensions and join_image_video now live in djjtb.media_utils
# and are imported via djj.get_join_dimensions / djj.join_image_video


def process_join_folder(folder, position, audio_choice):
    """Subfolder mode: expects exactly 1 image + 1 video per subfolder."""

    videos = [f for f in os.listdir(folder) if f.lower().endswith(VIDEO_EXTS)]
    images = [f for f in os.listdir(folder) if f.lower().endswith(IMAGE_EXTS)]

    if len(videos) != 1 or len(images) != 1:
        print(f"  ⚠️  Skipping {Path(folder).name}: needs exactly 1 image + 1 video "
              f"(found {len(images)} image(s), {len(videos)} video(s))")
        return

    video_path = os.path.join(folder, videos[0])
    image_path = os.path.join(folder, images[0])
    video_stem = Path(videos[0]).stem

    out_dir = Path(folder).parent / "Joined"
    out_dir.mkdir(parents=True, exist_ok=True)

    output_path = out_dir / f"{video_stem}_joined.mp4"

    print(f"  🖼️  Image : {images[0]}")
    print(f"  🎬 Video : {videos[0]}")

    success = djj.join_image_video(image_path, video_path, output_path, position, audio_choice)
    if success:
        print(f"  ✅ Output: {output_path.name}")
    print()


def process_join_flat(parent, position, audio_choice):
    """Flat mode: pairs image+video by matching stem, like existing flat modes."""

    videos = sorted([f for f in os.listdir(parent) if f.lower().endswith(VIDEO_EXTS)])
    total = len(videos)

    if total == 0:
        print("⚠️  No videos found in folder.")
        return

    out_dir = Path(parent) / "Joined"
    out_dir.mkdir(parents=True, exist_ok=True)

    for idx, video_file in enumerate(videos, 1):
        percent = int((idx / total) * 100)
        print(f"\033[93m🔗 Joining \033[0m{idx}\033[93m/\033[0m{total} ({percent}%)\033[93m...\033[0m")

        video_path = os.path.join(parent, video_file)
        video_stem = Path(video_file).stem

        matched_images = sorted([
            os.path.join(parent, f) for f in os.listdir(parent)
            if f.lower().endswith(IMAGE_EXTS) and Path(f).stem.startswith(video_stem)
        ])

        if not matched_images:
            print(f"  ⚠️  No matching image for {video_file}, skipping.")
            continue

        image_path = matched_images[0]
        output_path = out_dir / f"{video_stem}_joined.mp4"

        print(f"  🖼️  Image : {Path(image_path).name}")
        print(f"  🎬 Video : {video_file}")

        success = djj.join_image_video(image_path, video_path, output_path, position, audio_choice)
        if success:
            print(f"  ✅ Output: {output_path.name}")
        print()



# Block 8 – Slideshow + Join (Mode 4) processors
def process_slideshow_join_folder(folder, image_duration, position, audio_choice, max_longest_edge=1920):
    """
    Subfolder mode for Slideshow + Join.
    Expects exactly 1 video + 1+ images per subfolder.
    Builds a slideshow from the images (matching video duration/fps),
    then joins it to the video.
    Output: parent/Output/Slideshow_Joined/
    """

    videos = [f for f in os.listdir(folder) if f.lower().endswith(VIDEO_EXTS)]
    if len(videos) != 1:
        print(f"  ⚠️  Skipping {Path(folder).name}: needs exactly 1 video (found {len(videos)})")
        return

    video_path = os.path.join(folder, videos[0])
    video_stem = Path(video_path).stem

    images = sorted([
        os.path.join(folder, f) for f in os.listdir(folder)
        if f.lower().endswith(IMAGE_EXTS)
    ])
    if not images:
        print(f"  ⚠️  No images found in {Path(folder).name}, skipping.")
        return

    video_duration, _, _, fps = get_video_info(video_path)
    if not video_duration:
        print(f"  ❌ Could not get video duration: {video_path}")
        return

    out_dir = Path(folder).parent / "Output" / "Slideshow_Joined"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build slideshow to a temp location beside the video
    suffix = djj.position_suffix(position)
    temp_slideshow = Path(folder) / f"{video_stem}_temp_slideshow.mp4"
    build_slideshow_native_size(images, image_duration, video_duration, temp_slideshow, fps=fps)

    if not temp_slideshow.exists() or temp_slideshow.stat().st_size == 0:
        print(f"  ❌ Slideshow build failed for {video_stem}")
        return

    output_path = out_dir / f"{video_stem}_sl_joined{suffix}.mp4"
    print(f"  🔗 Joining slideshow to video...")
    success = djj.build_slideshow_and_join(video_path, str(temp_slideshow), output_path, position, audio_choice,
                                           max_longest_edge=max_longest_edge)

    temp_slideshow.unlink(missing_ok=True)

    if success:
        print(f"  ✅ Output: {output_path.name}")
    print()


def process_slideshow_join_flat(parent, image_duration, position, audio_choice, max_longest_edge=1920):
    """
    Flat mode for Slideshow + Join.
    Pairs video with matching-stem images.
    Output: parent/Output/Slideshow_Joined/
    """

    videos = sorted([f for f in os.listdir(parent) if f.lower().endswith(VIDEO_EXTS)])
    total = len(videos)
    if total == 0:
        print("⚠️  No videos found in folder.")
        return

    out_dir = Path(parent) / "Output" / "Slideshow_Joined"
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = djj.position_suffix(position)

    for idx, video_file in enumerate(videos, 1):
        percent = int((idx / total) * 100)
        print(f"\033[93m🎞️ Processing \033[0m{idx}\033[93m/\033[0m{total} ({percent}%)\033[93m...\033[0m")

        video_path = os.path.join(parent, video_file)
        video_stem = Path(video_file).stem

        images = sorted([
            os.path.join(parent, f) for f in os.listdir(parent)
            if f.lower().endswith(IMAGE_EXTS) and Path(f).stem.startswith(video_stem)
        ])
        if not images:
            print(f"  ⚠️  No matching images for {video_file}, skipping.")
            continue

        video_duration, _, _, fps = get_video_info(video_path)
        if not video_duration:
            print(f"  ❌ Could not get video duration: {video_path}")
            continue

        temp_slideshow = Path(parent) / f"{video_stem}_temp_slideshow.mp4"
        build_slideshow_native_size(images, image_duration, video_duration, temp_slideshow, fps=fps)

        if not temp_slideshow.exists() or temp_slideshow.stat().st_size == 0:
            print(f"  ❌ Slideshow build failed for {video_stem}")
            continue

        output_path = out_dir / f"{video_stem}_sl_joined{suffix}.mp4"
        print(f"  🔗 Joining slideshow to video...")
        success = djj.build_slideshow_and_join(video_path, str(temp_slideshow), output_path, position, audio_choice,
                                               max_longest_edge=max_longest_edge)

        temp_slideshow.unlink(missing_ok=True)

        if success:
            print(f"  ✅ Output: {output_path.name}")
        print()


# Block 9 – Collage + Join (Mode 5) processors
def process_collage_join_folder(folder, position, audio_choice,
                                collage_direction, collage_longest_edge):
    """
    Subfolder mode for Collage + Join.
    Expects exactly 1 video + 1+ images per subfolder.
    Creates a collage from all images, then joins it to the video.
    Output: parent/Output/Collage_Joined/
    """

    videos = [f for f in os.listdir(folder) if f.lower().endswith(VIDEO_EXTS)]
    if len(videos) != 1:
        print(f"  ⚠️  Skipping {Path(folder).name}: needs exactly 1 video (found {len(videos)})")
        return

    video_path = os.path.join(folder, videos[0])
    video_stem = Path(video_path).stem

    images = sorted([
        os.path.join(folder, f) for f in os.listdir(folder)
        if f.lower().endswith(IMAGE_EXTS)
    ])
    if not images:
        print(f"  ⚠️  No images found in {Path(folder).name}, skipping.")
        return

    out_dir = Path(folder).parent / "Output" / "Collage_Joined"
    out_dir.mkdir(parents=True, exist_ok=True)

    suffix = djj.position_suffix(position)
    output_path = out_dir / f"{video_stem}_col_joined{suffix}.mp4"
    temp_dir = Path(folder) / ".djjtb_temp_collage"

    print(f"  🖼️  Building collage from {len(images)} image(s)...")
    success = djj.build_collage_and_join(
        video_path, images, output_path, position, audio_choice,
        collage_direction, collage_longest_edge,
        collage_group_size=len(images),
        temp_dir=temp_dir
    )

    # Clean up temp dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)

    if success:
        print(f"  ✅ Output: {output_path.name}")
    print()


def process_collage_join_flat(parent, position, audio_choice,
                              collage_direction, collage_longest_edge):
    """
    Flat mode for Collage + Join.
    Pairs video with matching-stem images, collages them, then joins.
    Output: parent/Output/Collage_Joined/
    """

    videos = sorted([f for f in os.listdir(parent) if f.lower().endswith(VIDEO_EXTS)])
    total = len(videos)
    if total == 0:
        print("⚠️  No videos found in folder.")
        return

    out_dir = Path(parent) / "Output" / "Collage_Joined"
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = djj.position_suffix(position)

    for idx, video_file in enumerate(videos, 1):
        percent = int((idx / total) * 100)
        print(f"\033[93m🖼️ Processing \033[0m{idx}\033[93m/\033[0m{total} ({percent}%)\033[93m...\033[0m")

        video_path = os.path.join(parent, video_file)
        video_stem = Path(video_file).stem

        images = sorted([
            os.path.join(parent, f) for f in os.listdir(parent)
            if f.lower().endswith(IMAGE_EXTS) and Path(f).stem.startswith(video_stem)
        ])
        if not images:
            print(f"  ⚠️  No matching images for {video_file}, skipping.")
            continue

        output_path = out_dir / f"{video_stem}_col_joined{suffix}.mp4"
        temp_dir = Path(parent) / f".djjtb_temp_collage_{video_stem}"

        print(f"  🖼️  Building collage from {len(images)} image(s)...")
        success = djj.build_collage_and_join(
            video_path, images, output_path, position, audio_choice,
            collage_direction, collage_longest_edge,
            collage_group_size=len(images),
            temp_dir=temp_dir
        )

        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

        if success:
            print(f"  ✅ Output: {output_path.name}")
        print()


# Block 10 – Main Loop
def main():
    print()
    print()
    print("\033[92m==================================================\033[0m")
    print("\033[1;93mSlideshow Watermark\033[0m")
    print("Generate slideshow from images, overlay on video")
    print("\033[92m==================================================\033[0m")
    print()

    while True:
        # ── Step 1: path input ──────────────────────────────────────────────
        parent = djj.get_path_input("📁 Enter path")
        print()

        # ── Step 2: top-level mode ──────────────────────────────────────────
        top_mode = djj.prompt_choice(
            "🎬 What would you like to do?\n1. Slideshow + Watermark\n2. Slideshow Only\n3. Image Join\n4. Slideshow + Join\n5. Collage + Join",
            ['1', '2', '3', '4', '5'],
            default='1'
        )
        print()

        # ── IMAGE JOIN branch ───────────────────────────────────────────────
        if top_mode == '3':

            mode = djj.prompt_choice(
                "📂 Are files in subfolders?\n1. Yes (per-pair subfolders), 2. No (flat folder) ",
                ['1', '2'],
                default='1'
            )
            is_flat_mode = mode == '2'
            print()

            print("\033[93m🖼️  Image Position:\033[0m")
            print("1. Left   (video on right)")
            print("2. Right  (video on left)")
            print("3. Top    (video on bottom)")
            print("4. Bottom (video on top)")
            position = djj.prompt_choice(
                "\033[93mChoice\033[0m",
                ['1', '2', '3', '4'],
                default='1'
            )
            print()

            print("\033[93m🔊 Audio:\033[0m")
            print("1. Keep video's audio")
            print("2. Strip audio")
            print("3. Add silent audio track")
            audio_choice = djj.prompt_choice(
                "\033[93mChoice\033[0m",
                ['1', '2', '3'],
                default='1'
            )
            print()

            if is_flat_mode:
                process_join_flat(parent, position, audio_choice)
            else:
                subdirs = [
                    os.path.join(parent, d) for d in sorted(os.listdir(parent))
                    if os.path.isdir(os.path.join(parent, d))
                ]
                total = len(subdirs)
                for idx, sub in enumerate(subdirs, 1):
                    percent = int((idx / total) * 100)
                    print(f"\033[93m🔗 Processing folder \033[0m{idx}\033[93m/\033[0m{total} ({percent}%)\033[93m...\033[0m")
                    process_join_folder(sub, position, audio_choice)

            out_folder = Path(parent) / "Joined"
            djj.prompt_open_folder(str(out_folder) if out_folder.exists() else parent)

        # ── SLIDESHOW ONLY branch ───────────────────────────────────────────
        elif top_mode == '2':

            mode = djj.prompt_choice(
                "📂 Are videos in subfolders?\n1. Yes (per-video subfolders), 2. No (flat folder) ",
                ['1', '2'],
                default='1'
            )
            is_flat_mode = mode == '2'
            print()

            num_slideshows_str = djj.prompt_choice(
                "🎞️  How many slideshows to create?\n1. One slideshow\n2. Two slideshows (images auto-split)",
                ['1', '2'],
                default='1'
            )
            num_slideshows = int(num_slideshows_str)
            print()

            if num_slideshows == 2:
                print("\033[93mℹ️  Images will be split as evenly as possible between the two slideshows.")
                print("   If only 1 image is available, it will be used in both.\033[0m")
                print()

            def ask_duration(label="🕒 Duration per slide in seconds (default 3, decimals ok e.g. 2.5): "):
                val = djj.get_float_input(label, min_val=0.1, max_val=30.0)
                return val if val is not None else 3.0

            image_duration = ask_duration(
                "🕒 Slideshow 1 — duration per slide (default 3, decimals ok e.g. 2.5): "
                if num_slideshows == 2 else
                "🕒 Duration per slide (default 3, decimals ok e.g. 2.5): "
            )
            if num_slideshows == 2:
                image_duration2 = ask_duration("🕒 Slideshow 2 — duration per slide (default 3, decimals ok e.g. 2.5): ")
            else:
                image_duration2 = image_duration
            print()

            if is_flat_mode:
                process_slideshow_only_flat(parent, image_duration, image_duration2, num_slideshows)
                output_folder = parent
            else:
                subdirs = [
                    os.path.join(parent, d) for d in sorted(os.listdir(parent))
                    if os.path.isdir(os.path.join(parent, d))
                ]
                total = len(subdirs)
                for idx, sub in enumerate(subdirs, 1):
                    percent = int((idx / total) * 100)
                    print(f"\033[93m📁 Processing folder \033[0m{idx}\033[93m/\033[0m{total} ({percent}%)\033[93m...\033[0m")
                    process_slideshow_only_folder(sub, image_duration, image_duration2, num_slideshows)
                    print("\n" * 1)
                output_folder = parent

            djj.prompt_open_folder(output_folder)

        # ── SLIDESHOW + WATERMARK branch ────────────────────────────────────
        elif top_mode == '1':

            mode = djj.prompt_choice(
                "📂 Are videos in subfolders?\n1. Yes (per-video subfolders), 2. No (flat folder) ",
                ['1', '2'],
                default='1'
            )
            is_flat_mode = mode == '2'
            print()

            image_duration = djj.get_float_input(
                "🕒 Duration per image in seconds (default: 3): ",
                min_val=0.1,
                max_val=30.0
            )
            if image_duration is None:
                image_duration = 3.0
            print()

            scale_percentage = djj.get_float_input(
                "📏 Overlay height as percentage of video (default: 30)",
                min_val=5.0,
                max_val=80.0
            )
            if scale_percentage is None:
                scale_percentage = 30.0
            scale_ratio = round(scale_percentage / 100, 2)
            print()

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
            else:
                subdirs = [
                    os.path.join(parent, d) for d in sorted(os.listdir(parent))
                    if os.path.isdir(os.path.join(parent, d))
                ]   
                total = len(subdirs)
                for idx, sub in enumerate(subdirs, 1):
                    percent = int((idx / total) * 100)
                    print(f"\033[93m📽️ Processing\033[0m {idx}\033[93m/\033[0m{total} \033[93mvideos\033[0m ({percent}%)\033[93m...\033[0m")
                    process_folder(sub, image_duration, scale_ratio, overlay_position, False, parent=parent)
                    print("\n" * 2)

            djj.prompt_open_folder(parent)

        # ── SLIDESHOW + JOIN branch ─────────────────────────────────────────
        elif top_mode == '4':

            mode = djj.prompt_choice(
                "📂 Are files in subfolders?\n1. Yes (per-video subfolders), 2. No (flat folder) ",
                ['1', '2'],
                default='1'
            )
            is_flat_mode = mode == '2'
            print()

            image_duration = djj.get_float_input(
                "🕒 Duration per slide (default 3, decimals ok e.g. 2.5): ",
                min_val=0.1, max_val=30.0
            )
            if image_duration is None:
                image_duration = 3.0
            print()

            print("\033[93m📐 Max output longest edge (total joined width or height):\033[0m")
            print("1. 1280")
            print("2. 1920  (default)")
            print("3. 2560")
            print("4. 3840")
            _edge_map = {'1': 1280, '2': 1920, '3': 2560, '4': 3840}
            sl_max_edge = _edge_map[djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3', '4'], default='2')]
            print()

            print("\033[93m🖼️  Slideshow Position:\033[0m")
            print("1. Left   (video on right)")
            print("2. Right  (video on left)")
            print("3. Top    (video on bottom)")
            print("4. Bottom (video on top)")
            position = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3', '4'], default='1')
            print()

            print("\033[93m🔊 Audio:\033[0m")
            print("1. Keep video's audio")
            print("2. Strip audio")
            print("3. Add silent audio track")
            audio_choice = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3'], default='1')
            print()

            if is_flat_mode:
                process_slideshow_join_flat(parent, image_duration, position, audio_choice, sl_max_edge)
            else:
                subdirs = [
                    os.path.join(parent, d) for d in sorted(os.listdir(parent))
                    if os.path.isdir(os.path.join(parent, d))
                ]
                total = len(subdirs)
                for idx, sub in enumerate(subdirs, 1):
                    percent = int((idx / total) * 100)
                    print(f"\033[93m🎞️ Processing folder \033[0m{idx}\033[93m/\033[0m{total} ({percent}%)\033[93m...\033[0m")
                    process_slideshow_join_folder(sub, image_duration, position, audio_choice, sl_max_edge)

            out_folder = Path(parent) / "Output" / "Slideshow_Joined"
            djj.prompt_open_folder(str(out_folder) if out_folder.exists() else parent)

        # ── COLLAGE + JOIN branch ────────────────────────────────────────────
        elif top_mode == '5':

            mode = djj.prompt_choice(
                "📂 Are files in subfolders?\n1. Yes (per-video subfolders), 2. No (flat folder) ",
                ['1', '2'],
                default='1'
            )
            is_flat_mode = mode == '2'
            print()

            print("\033[93m🎑 Collage direction:\033[0m")
            print("1. Horizontal (images side by side)")
            print("2. Vertical   (images stacked)")
            coll_dir_choice = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2'], default='1')
            collage_direction = 'H' if coll_dir_choice == '1' else 'V'
            print()

            print("\033[93m📐 Max output longest edge (total joined width or height):\033[0m")
            print("1. 1280")
            print("2. 1920  (default)")
            print("3. 2560")
            print("4. 3840")
            _edge_map = {'1': 1280, '2': 1920, '3': 2560, '4': 3840}
            collage_longest_edge = _edge_map[djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3', '4'], default='2')]
            print()

            print("\033[93m🖼️  Collage Position:\033[0m")
            print("1. Left   (video on right)")
            print("2. Right  (video on left)")
            print("3. Top    (video on bottom)")
            print("4. Bottom (video on top)")
            position = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3', '4'], default='1')
            print()

            print("\033[93m🔊 Audio:\033[0m")
            print("1. Keep video's audio")
            print("2. Strip audio")
            print("3. Add silent audio track")
            audio_choice = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3'], default='1')
            print()

            if is_flat_mode:
                process_collage_join_flat(parent, position, audio_choice, collage_direction, collage_longest_edge)
            else:
                subdirs = [
                    os.path.join(parent, d) for d in sorted(os.listdir(parent))
                    if os.path.isdir(os.path.join(parent, d))
                ]
                total = len(subdirs)
                for idx, sub in enumerate(subdirs, 1):
                    percent = int((idx / total) * 100)
                    print(f"\033[93m🖼️ Processing folder \033[0m{idx}\033[93m/\033[0m{total} ({percent}%)\033[93m...\033[0m")
                    process_collage_join_folder(sub, position, audio_choice, collage_direction, collage_longest_edge)

            out_folder = Path(parent) / "Output" / "Collage_Joined"
            djj.prompt_open_folder(str(out_folder) if out_folder.exists() else parent)

        # ── What Next ───────────────────────────────────────────────────────
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()
    
    