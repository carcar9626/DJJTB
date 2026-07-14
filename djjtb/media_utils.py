#!/usr/bin/env python3
"""
DJJTB Media Utilities
Media-processing helpers used by media_tools and ai_tools scripts.
Imported via djjtb.utils re-export so all existing djj.* calls work unchanged.
"""

import os
import sys
import subprocess
import logging
import pathlib
import pathlib


# ─── FFmpeg Dimension Helpers ─────────────────────────────────────────────────

def make_even_dimensions(width: int, height: int) -> tuple[int, int, int, int]:
    even_width = width + (width % 2)
    even_height = height + (height % 2)
    pad_x = (even_width - width) // 2
    pad_y = (even_height - height) // 2
    return even_width, even_height, pad_x, pad_y

def get_pad_filter(width: int, height: int) -> str:
    if width % 2 == 0 and height % 2 == 0:
        return "null"
    ew, eh, px, py = make_even_dimensions(width, height)
    return f"pad={ew}:{eh}:{px}:{py}:color=black"

def get_gif_dimensions(gif_path: str) -> tuple[int, int]:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0", gif_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    width, height = map(int, result.stdout.strip().split('x'))
    return width, height


# ─── Audio Options ────────────────────────────────────────────────────────────

def get_audio_options(audio_choice):
    """Get FFmpeg audio options based on user choice."""
    if audio_choice == '1':  # Keep Original Audio
        return ["-c:a", "aac"]
    elif audio_choice == '2':  # Strip Audio
        return ["-an"]
    elif audio_choice == '3':  # Add Silent Audio Track
        return ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000", "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-shortest"]
    else:
        return ["-c:a", "aac"]


# ─── Dissolve Slideshow ───────────────────────────────────────────────────────

def create_dissolve_slideshow(images, output_file, duration_per_slide=4, transition_duration=1.0,
                              canvas_width=1920, canvas_height=1080):
    """
    Create a slideshow with dissolve transitions using proven ffmpeg logic.

    Args:
        images: List of image file paths
        output_file: Output video file path
        duration_per_slide: How long each slide shows (seconds)
        transition_duration: Duration of dissolve transition (seconds)
        canvas_width: Output video width
        canvas_height: Output video height

    Returns:
        tuple: (success: bool, message: str)
    """
    if not images:
        return False, "No images provided"

    if len(images) == 1:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(duration_per_slide), "-i", images[0],
            "-vf", f"scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=decrease,pad={canvas_width}:{canvas_height}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
            "-r", "30", "-fps_mode", "cfr",
            output_file
        ]
    else:
        cmd = ["ffmpeg", "-y"]
        for img_path in images:
            cmd.extend(["-loop", "1", "-t", str(duration_per_slide), "-i", img_path])

        filter_parts = []
        overlay_chain = []

        for i in range(len(images)):
            scale_filter = f"[{i}:v]scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=decrease,pad={canvas_width}:{canvas_height}:(ow-iw)/2:(oh-ih)/2,format=yuva420p"
            if i == 0:
                fade_filter = f"{scale_filter},fade=t=out:st={duration_per_slide-transition_duration}:d={transition_duration}:alpha=1,setpts=PTS-STARTPTS[va{i}]"
            else:
                offset_time = i * (duration_per_slide - transition_duration)
                fade_filter = f"{scale_filter},fade=t=in:st=0:d={transition_duration}:alpha=1,setpts=PTS-STARTPTS+{offset_time}/TB[va{i}]"
            filter_parts.append(fade_filter)
            overlay_chain.append(f"va{i}")

        current_base = overlay_chain[0]
        for i in range(1, len(overlay_chain)):
            overlay_filter = f"[{current_base}][{overlay_chain[i]}]overlay[ov{i}]"
            current_base = f"ov{i}"
            filter_parts.append(overlay_filter)

        final_duration = len(images) * duration_per_slide - (len(images) - 1) * transition_duration
        filter_parts.append(f"[{current_base}]trim=duration={final_duration}")

        cmd.extend([
            "-filter_complex", ";".join(filter_parts),
            "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
            "-r", "30", "-t", str(final_duration), "-fps_mode", "cfr",
            output_file
        ])

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True, f"Successfully created slideshow: {output_file}"
    except subprocess.CalledProcessError as e:
        error_msg = f"FFmpeg error: {e.stderr}"
        logging.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logging.error(error_msg)
        return False, error_msg


def calculate_slideshow_duration(num_images, duration_per_slide, transition_duration=1.0):
    """
    Calculate total slideshow duration with transitions.

    Args:
        num_images: Number of images in slideshow
        duration_per_slide: Duration each slide is visible
        transition_duration: Duration of each transition

    Returns:
        float: Total video duration in seconds
    """
    if num_images <= 1:
        return duration_per_slide
    return num_images * duration_per_slide - (num_images - 1) * transition_duration


# ─── XMP Helpers ─────────────────────────────────────────────────────────────

def has_xmp_file(image_path):
    """Check if an XMP sidecar file exists for the given image."""
    if isinstance(image_path, pathlib.Path):
        image_path = str(image_path)
    return os.path.exists(f"{image_path}.xmp")


def filter_images_without_xmp(image_paths, show_stats=True):
    """
    Filter out images that already have XMP sidecar files.

    Returns:
        tuple: (images_without_xmp, images_with_xmp, stats_dict)
    """
    images_without_xmp = []
    images_with_xmp = []

    for img_path in image_paths:
        if has_xmp_file(img_path):
            images_with_xmp.append(img_path)
        else:
            images_without_xmp.append(img_path)

    stats = {
        'total_images': len(image_paths),
        'with_xmp': len(images_with_xmp),
        'without_xmp': len(images_without_xmp),
        'skip_percentage': (len(images_with_xmp) / len(image_paths) * 100) if image_paths else 0
    }

    if show_stats and image_paths:
        print(f"\033[93m📊 XMP Detection Results:\033[0m")
        print(f"   Total images: {stats['total_images']}")
        print(f"   Already tagged (with XMP): \033[92m{stats['with_xmp']}\033[0m")
        print(f"   Need tagging: \033[93m{stats['without_xmp']}\033[0m")
        if stats['with_xmp'] > 0:
            print(f"   Skipping: \033[92m{stats['skip_percentage']:.1f}%\033[0m")
        print()

    return images_without_xmp, images_with_xmp, stats


def check_xmp_files_in_folder(folder_path, extensions=('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'), include_subfolders=False):
    """Check XMP file status for all images in a folder."""
    folder_path = pathlib.Path(folder_path)

    images = []
    scan = folder_path.rglob if include_subfolders else folder_path.glob
    for ext in extensions:
        images.extend(scan(f'*{ext}'))
        images.extend(scan(f'*{ext.upper()}'))

    images = [str(img) for img in images]
    without_xmp, with_xmp, stats = filter_images_without_xmp(images, show_stats=False)

    return {
        'folder_path': str(folder_path),
        'include_subfolders': include_subfolders,
        'stats': stats,
        'images_without_xmp': without_xmp,
        'images_with_xmp': with_xmp,
        'sample_with_xmp': with_xmp[:5] if with_xmp else [],
        'sample_without_xmp': without_xmp[:5] if without_xmp else []
    }


def prompt_xmp_handling_mode():
    """
    Prompt user for how to handle existing XMP files.
    Returns the chosen mode and relevant settings.
    Note: calls prompt_choice via djjtb.utils to avoid circular import.
    """
    from djjtb.utils import prompt_choice

    print("\033[93m🏷️  XMP File Handling:\033[0m")
    mode = prompt_choice(
        "How should existing XMP files be handled?\n"
        "1. Skip images that already have XMP files (recommended)\n"
        "2. Process all images (overwrite existing XMP)\n"
        "3. Process all images (merge with existing XMP)\n",
        ['1', '2', '3'],
        default='1'
    )

    config = {
        'skip_existing': mode == '1',
        'overwrite_existing': mode == '2',
        'merge_existing': mode == '3',
        'mode_description': {
            '1': 'Skip existing XMP files',
            '2': 'Overwrite existing XMP files',
            '3': 'Merge with existing XMP files'
        }[mode]
    }

    print(f"✅ \033[93mSelected:\033[0m {config['mode_description']}")
    print()
    return config


# ─── Video / Image Join Helpers ───────────────────────────────────────────────

def get_join_dimensions(img_w, img_h, vid_w, vid_h, position):
    """
    Calculate scaled dimensions so image and video join seamlessly.
    Left/Right: match height. Top/Bottom: match width.
    All dims forced even for ffmpeg compatibility.
    position: '1'=left, '2'=right, '3'=top, '4'=bottom
    Returns: (img_w_out, img_h_out, vid_w_out, vid_h_out)
    """
    def even(n):
        return n if n % 2 == 0 else n - 1

    if position in ('1', '2'):
        master_h = even(img_h)
        img_w_out = even(int(img_w * master_h / img_h))
        img_h_out = master_h
        vid_w_out = even(int(vid_w * master_h / vid_h))
        vid_h_out = master_h
    else:
        master_w = even(img_w)
        img_w_out = master_w
        img_h_out = even(int(img_h * master_w / img_w))
        vid_w_out = master_w
        vid_h_out = even(int(vid_h * master_w / vid_w))

    return img_w_out, img_h_out, vid_w_out, vid_h_out


def position_suffix(position):
    """
    Return a short filename suffix for a join position choice.
    '1'→'_lft', '2'→'_rgt', '3'→'_top', '4'→'_btm'
    Matches the convention used in image_pairing.py.
    """
    return {'1': '_lft', '2': '_rgt', '3': '_top', '4': '_btm'}.get(position, '')


def clamp_to_longest_edge(w, h, max_longest_edge):
    """
    Scale (w, h) down so the longest edge == max_longest_edge.
    Returns (new_w, new_h) both forced even. No-op if already within limit.
    """
    def even(n):
        return n if n % 2 == 0 else n - 1

    if max(w, h) <= max_longest_edge:
        return even(w), even(h)
    if w >= h:
        new_w = max_longest_edge
        new_h = int(h * max_longest_edge / w)
    else:
        new_h = max_longest_edge
        new_w = int(w * max_longest_edge / h)
    return even(new_w), even(new_h)


def _cap_join_dims(w1, h1, w2, h2, position, max_longest_edge):
    """
    Cap the TOTAL joined output (w1+w2 for H-join, h1+h2 for V-join) to
    max_longest_edge. Uses a remainder approach so the sum is exactly
    max_longest_edge (even-safe), not max-2 due to independent truncation.
    w1/h1 = image/slideshow panel, w2/h2 = video panel.
    Returns: (w1_out, h1_out, w2_out, h2_out)
    """
    def even(n):
        return n if n % 2 == 0 else n - 1

    if position in ('1', '2'):  # H-join: widths add, heights shared
        total_long = w1 + w2
        shared = h1
    else:                       # V-join: heights add, widths shared
        total_long = h1 + h2
        shared = w1

    if total_long <= max_longest_edge:
        return w1, h1, w2, h2

    ratio = max_longest_edge / total_long
    new_shared = even(int(shared * ratio))

    if position in ('1', '2'):
        # Scale smaller panel proportionally; give remainder to larger
        new_w1 = even(int(w1 * ratio))
        new_w2 = max_longest_edge - new_w1
        if new_w2 % 2 != 0:
            new_w2 -= 1
            new_w1 = max_longest_edge - new_w2
        return new_w1, new_shared, new_w2, new_shared
    else:
        new_h1 = even(int(h1 * ratio))
        new_h2 = max_longest_edge - new_h1
        if new_h2 % 2 != 0:
            new_h2 -= 1
            new_h1 = max_longest_edge - new_h2
        return new_shared, new_h1, new_shared, new_h2


def join_image_video(image_path, video_path, output_path, position, audio_choice='1',
                     max_longest_edge=None):
    """
    Join a single image (held as video) side-by-side or top/bottom with a video.
    position: '1'=left, '2'=right, '3'=top, '4'=bottom
    audio_choice: '1'=keep original, '2'=strip, '3'=add silent track
    max_longest_edge: if set, caps the TOTAL joined output's longest dimension
    Returns: True on success, False on failure
    """
    def even(n):
        return n if n % 2 == 0 else n - 1

    # Get video info
    try:
        probe_v = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        v_out = probe_v.stdout.strip().split('\n')
        vid_w = int(float(v_out[0]))
        vid_h = int(float(v_out[1]))
        fps_raw = v_out[2]
        fps = round(int(fps_raw.split('/')[0]) / int(fps_raw.split('/')[1]), 3) if '/' in fps_raw else float(fps_raw)
        vid_dur = float(v_out[3])
    except Exception as e:
        print(f"  ❌ Could not read video info: {video_path} — {e}")
        return False

    # Get image dimensions
    try:
        probe_i = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(image_path)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        i_out = probe_i.stdout.strip().split('\n')
        img_w = int(float(i_out[0]))
        img_h = int(float(i_out[1]))
    except Exception as e:
        print(f"  ❌ Could not read image dimensions: {image_path} — {e}")
        return False

    img_w_out, img_h_out, vid_w_out, vid_h_out = get_join_dimensions(img_w, img_h, vid_w, vid_h, position)

    # Cap the TOTAL joined output to max_longest_edge if specified
    if max_longest_edge:
        img_w_out, img_h_out, vid_w_out, vid_h_out = _cap_join_dims(
            img_w_out, img_h_out, vid_w_out, vid_h_out, position, max_longest_edge
        )

    fps_str = str(round(fps))

    img_scale = f"[0:v]scale={img_w_out}:{img_h_out},fps={fps_str}[img]"
    vid_scale = f"[1:v]scale={vid_w_out}:{vid_h_out}[vid]"

    if position == '1':
        stack = "[img][vid]hstack=inputs=2[out]"
    elif position == '2':
        stack = "[vid][img]hstack=inputs=2[out]"
    elif position == '3':
        stack = "[img][vid]vstack=inputs=2[out]"
    else:
        stack = "[vid][img]vstack=inputs=2[out]"

    filter_complex = f"{img_scale};{vid_scale};{stack}"

    if audio_choice == '3':
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(vid_dur), "-i", str(image_path),
            "-i", str(video_path),
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-filter_complex", filter_complex,
            "-map", "[out]", "-map", "2:a",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(output_path)
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(vid_dur), "-i", str(image_path),
            "-i", str(video_path),
            "-filter_complex", filter_complex,
            "-map", "[out]",
        ]
        if audio_choice == '1':
            cmd += ["-map", "1:a?", "-c:a", "aac"]
        cmd += [
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-pix_fmt", "yuv420p", "-shortest",
            str(output_path)
        ]

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"  ❌ FFmpeg error:\n{result.stderr[-300:]}")
        return False
    return True


# ─── Collage Helper ───────────────────────────────────────────────────────────

def create_collage(image_paths, direction, longest_edge, output_dir, group_size, suffix='_comp'):
    """
    Group images sequentially, collage each group into a single image,
    resize so longest edge == longest_edge, save to output_dir with _comp suffix.

    Args:
        image_paths:  flat list of image paths (already sorted/ordered)
        direction:    'H' (horizontal) or 'V' (vertical)
        longest_edge: int, target size for the longest edge after resize
        output_dir:   folder to save collages into (will be created if needed)
        group_size:   how many images per collage

    Returns:
        List of saved collage file paths (in order)
    """
    from PIL import Image

    os.makedirs(output_dir, exist_ok=True)
    collage_paths = []

    # Build sequential groups
    groups = [image_paths[i:i + group_size] for i in range(0, len(image_paths), group_size)]
    complete_groups = [g for g in groups if len(g) == group_size]

    if len(complete_groups) < len(groups):
        leftover = len(image_paths) - len(complete_groups) * group_size
        print(f"\033[93m⚠️  {leftover} image(s) left over (incomplete group) — skipped\033[0m")

    for idx, group in enumerate(complete_groups):
        try:
            imgs = [Image.open(p).convert('RGB') for p in group]

            if direction == 'H':
                # Scale all images to the tallest image's height, then paste side by side
                target_h = max(im.height for im in imgs)
                resized = [
                    im.resize((int(im.width * target_h / im.height), target_h), Image.Resampling.LANCZOS)
                    for im in imgs
                ]
                total_w = sum(im.width for im in resized)
                canvas = Image.new('RGB', (total_w, target_h))
                x = 0
                for im in resized:
                    canvas.paste(im, (x, 0))
                    x += im.width
            else:  # V
                # Scale all images to the widest image's width, then stack vertically
                target_w = max(im.width for im in imgs)
                resized = [
                    im.resize((target_w, int(im.height * target_w / im.width)), Image.Resampling.LANCZOS)
                    for im in imgs
                ]
                total_h = sum(im.height for im in resized)
                canvas = Image.new('RGB', (target_w, total_h))
                y = 0
                for im in resized:
                    canvas.paste(im, (0, y))
                    y += im.height

            # Resize so longest edge hits the target
            cw, ch = canvas.size
            if cw >= ch:
                new_w = longest_edge
                new_h = int(ch * longest_edge / cw)
            else:
                new_h = longest_edge
                new_w = int(cw * longest_edge / ch)
            # Force even dims for ffmpeg compatibility downstream
            new_w = new_w if new_w % 2 == 0 else new_w - 1
            new_h = new_h if new_h % 2 == 0 else new_h - 1
            canvas = canvas.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Name based on first image in group.
            # Strip any trailing _comp or _compN so re-collage passes don't
            # chain into ugly _comp_comp_comp names — the folder nesting
            # (Comp/ → Comp/Comp/ → …) carries the generation info instead.
            import re as _re
            first_stem = pathlib.Path(group[0]).stem
            first_stem = _re.sub(r'_comp\d*$', '', first_stem)
            out_path = os.path.join(output_dir, f"{first_stem}{suffix}.jpg")
            canvas.save(out_path, 'JPEG', quality=95)
            collage_paths.append(out_path)

            sys.stdout.write(f"\r\033[93mCollaging \033[0m{idx + 1}/{len(complete_groups)}...")
            sys.stdout.flush()

        except Exception as e:
            print(f"\033[93m❌ Error creating collage for group {idx + 1}: {e}\033[0m")

    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()
    print(f"\033[92m✅ {len(collage_paths)} collage(s) created → {output_dir}\033[0m")
    return collage_paths


# ─── Slideshow/Collage + Join Helpers ────────────────────────────────────────

def build_slideshow_and_join(video_path, slideshow_path, output_path, position, audio_choice='1',
                             max_longest_edge=1920):
    """
    Join a pre-built slideshow video to a source video.
    max_longest_edge caps the TOTAL joined output's longest dimension
    (combined width for H-join, combined height for V-join).

    Args:
        video_path:       Path to the source video
        slideshow_path:   Path to the pre-built slideshow .mp4
        output_path:      Path for the joined output .mp4
        position:         '1'=left, '2'=right, '3'=top, '4'=bottom
        audio_choice:     '1'=keep, '2'=strip, '3'=silent
        max_longest_edge: Cap on the total output's longest edge

    Returns:
        bool: True on success
    """
    try:
        probe_s = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(slideshow_path)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        s_out = probe_s.stdout.strip().split('\n')
        sl_w = int(float(s_out[0]))
        sl_h = int(float(s_out[1]))
    except Exception as e:
        print(f"  ❌ Could not read slideshow info: {slideshow_path} — {e}")
        return False

    try:
        probe_v = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        v_out = probe_v.stdout.strip().split('\n')
        vid_w = int(float(v_out[0]))
        vid_h = int(float(v_out[1]))
        fps_raw = v_out[2]
        fps = round(int(fps_raw.split('/')[0]) / int(fps_raw.split('/')[1]), 3) if '/' in fps_raw else float(fps_raw)
        vid_dur = float(v_out[3])
    except Exception as e:
        print(f"  ❌ Could not read video info: {video_path} — {e}")
        return False

    sl_w_out, sl_h_out, vid_w_out, vid_h_out = get_join_dimensions(sl_w, sl_h, vid_w, vid_h, position)

    # Cap the TOTAL joined output to max_longest_edge (exact, no off-by-one)
    sl_w_out, sl_h_out, vid_w_out, vid_h_out = _cap_join_dims(
        sl_w_out, sl_h_out, vid_w_out, vid_h_out, position, max_longest_edge
    )

    fps_str = str(round(fps))

    sl_scale  = f"[0:v]scale={sl_w_out}:{sl_h_out},fps={fps_str}[sl]"
    vid_scale = f"[1:v]scale={vid_w_out}:{vid_h_out}[vid]"

    if position == '1':
        stack = "[sl][vid]hstack=inputs=2[out]"
    elif position == '2':
        stack = "[vid][sl]hstack=inputs=2[out]"
    elif position == '3':
        stack = "[sl][vid]vstack=inputs=2[out]"
    else:
        stack = "[vid][sl]vstack=inputs=2[out]"

    filter_complex = f"{sl_scale};{vid_scale};{stack}"

    if audio_choice == '3':
        cmd = [
            "ffmpeg", "-y",
            "-i", str(slideshow_path),
            "-i", str(video_path),
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-filter_complex", filter_complex,
            "-map", "[out]", "-map", "2:a",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(output_path)
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(slideshow_path),
            "-i", str(video_path),
            "-filter_complex", filter_complex,
            "-map", "[out]",
        ]
        if audio_choice == '1':
            cmd += ["-map", "1:a?", "-c:a", "aac"]
        cmd += [
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-pix_fmt", "yuv420p", "-shortest",
            str(output_path)
        ]

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"  ❌ FFmpeg error:\n{result.stderr[-300:]}")
        return False
    return True


def build_collage_and_join(video_path, image_paths, output_path, position, audio_choice,
                           collage_direction, collage_longest_edge, collage_group_size,
                           temp_dir):
    """
    Create a collage from images (resized to collage_longest_edge), then join to video.
    collage_longest_edge also caps the TOTAL joined output's longest dimension.
    """
    temp_dir = pathlib.Path(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    collage_paths = create_collage(
        image_paths,
        collage_direction,
        collage_longest_edge,
        str(temp_dir),
        collage_group_size
    )

    if not collage_paths:
        print("  ❌ Collage creation failed — no output produced.")
        return False

    collage_image = collage_paths[0]

    # Pass collage_longest_edge as the total-output cap into join_image_video
    success = join_image_video(collage_image, video_path, output_path, position, audio_choice,
                               max_longest_edge=collage_longest_edge)

    # Clean up temp collage image
    try:
        os.remove(collage_image)
    except Exception:
        pass

    return success