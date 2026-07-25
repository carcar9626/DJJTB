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


# ─── Image Collection & Validation Helpers ───────────────────────────────────

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff')


def is_image_extension(filename):
    """Cheap extension-only check — use for fast collection-time filtering."""
    return str(filename).lower().endswith(IMAGE_EXTENSIONS)


def is_valid_image_file(file_path):
    """
    Real corruption check via Image.open()+verify() — slower than
    is_image_extension, so reserve for pre-flight gates (e.g. before handing
    a group of images to ffmpeg), not bulk collection filtering.
    """
    from PIL import Image
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def collect_images_from_folder(folder_path, include_subfolders=False, extensions=None):
    """
    Collect images from a folder, never descending into Output dirs.
    Non-recursive mode only lists the folder's immediate contents.
    extensions defaults to IMAGE_EXTENSIONS; pass a narrower tuple to
    exclude formats a particular caller can't handle (e.g. animated .gif).
    """
    if extensions is None:
        extensions = IMAGE_EXTENSIONS
    folder_path_obj = pathlib.Path(folder_path)

    images = []
    if folder_path_obj.is_dir():
        if include_subfolders:
            for root, dirs, files in os.walk(folder_path):
                # Prune Output folders in-place so walk never descends into them
                dirs[:] = [d for d in dirs if d.lower() != 'output']
                images.extend(pathlib.Path(root) / f for f in files if pathlib.Path(f).suffix.lower() in extensions)
        else:
            images = [f for f in folder_path_obj.glob('*') if f.suffix.lower() in extensions and f.is_file()]

    return sorted([str(v) for v in images], key=str.lower)


def collect_images_from_paths(raw_input, extensions=None):
    """
    Collect images from space-separated paths (supports drag-and-drop).
    Handles quoted paths, escaped spaces, files and folders mixed together.
    extensions defaults to IMAGE_EXTENSIONS; pass a narrower tuple to
    exclude formats a particular caller can't handle (e.g. animated .gif).
    """
    if extensions is None:
        extensions = IMAGE_EXTENSIONS
    images = []
    raw = raw_input.strip()

    # Rebuild tokens: split on spaces, but re-join tokens that are escaped spaces
    # (macOS drag-and-drop escapes spaces as '\ ')
    tokens = []
    current = ''
    i = 0
    while i < len(raw):
        if raw[i] == '\\' and i + 1 < len(raw) and raw[i + 1] == ' ':
            current += ' '
            i += 2
        elif raw[i] == ' ':
            if current:
                tokens.append(current)
                current = ''
            i += 1
        else:
            current += raw[i]
            i += 1
    if current:
        tokens.append(current)

    for token in tokens:
        path_str = token.strip().strip('\'"')
        if not path_str:
            continue
        try:
            path_obj = pathlib.Path(path_str).expanduser().resolve()
            if path_obj.is_file() and path_obj.suffix.lower() in extensions:
                images.append(str(path_obj))
            elif path_obj.is_dir():
                images.extend(collect_images_from_folder(str(path_obj), include_subfolders=False, extensions=extensions))
            else:
                print(f"  ⚠️  \033[93mNot found or unsupported:\033[0m {path_str}")
        except Exception as e:
            print(f"  ⚠️  \033[93mError resolving path\033[0m '{path_str}': {e}")

    return sorted(set(images), key=str.lower)


def collect_images_from_path_list(paths, include_subfolders=False):
    """
    Given a list of already-resolved paths (files + dirs, e.g. from a txt
    file), filter files by extension and expand dirs one level via
    collect_images_from_folder. The interactive "ask for txt path" prompt
    stays in the caller's CLI flow — this only handles the resolved list.
    """
    images = []
    for path in paths:
        path_obj = pathlib.Path(path)
        if path_obj.is_file():
            if path_obj.suffix.lower() in IMAGE_EXTENSIONS:
                images.append(str(path_obj))
        elif path_obj.is_dir():
            images.extend(collect_images_from_folder(str(path_obj), include_subfolders=include_subfolders))

    return sorted(set(images), key=str.lower)


# ─── Video Collection Helpers ─────────────────────────────────────────────────

VIDEO_EXTENSIONS = ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.wmv', '.flv')


def collect_videos_from_folder(folder_path, include_subfolders=False):
    """
    Collect videos from a folder, never descending into Output dirs.
    Non-recursive mode only lists the folder's immediate contents.
    """
    folder_path_obj = pathlib.Path(folder_path)

    videos = []
    if folder_path_obj.is_dir():
        if include_subfolders:
            for root, dirs, files in os.walk(folder_path):
                # Prune Output folders in-place so walk never descends into them
                dirs[:] = [d for d in dirs if d.lower() != 'output']
                videos.extend(pathlib.Path(root) / f for f in files if pathlib.Path(f).suffix.lower() in VIDEO_EXTENSIONS)
        else:
            videos = [f for f in folder_path_obj.glob('*') if f.suffix.lower() in VIDEO_EXTENSIONS and f.is_file()]

    return sorted([str(v) for v in videos], key=str.lower)


def collect_videos_from_paths(raw_input):
    """
    Collect videos from space-separated paths (supports drag-and-drop).
    Handles quoted paths, escaped spaces, files and folders mixed together.
    """
    videos = []
    raw = raw_input.strip()

    # Rebuild tokens: split on spaces, but re-join tokens that are escaped spaces
    # (macOS drag-and-drop escapes spaces as '\ ')
    tokens = []
    current = ''
    i = 0
    while i < len(raw):
        if raw[i] == '\\' and i + 1 < len(raw) and raw[i + 1] == ' ':
            current += ' '
            i += 2
        elif raw[i] == ' ':
            if current:
                tokens.append(current)
                current = ''
            i += 1
        else:
            current += raw[i]
            i += 1
    if current:
        tokens.append(current)

    for token in tokens:
        path_str = token.strip().strip('\'"')
        if not path_str:
            continue
        try:
            path_obj = pathlib.Path(path_str).expanduser().resolve()
            if path_obj.is_file() and path_obj.suffix.lower() in VIDEO_EXTENSIONS:
                videos.append(str(path_obj))
            elif path_obj.is_dir():
                videos.extend(collect_videos_from_folder(str(path_obj), include_subfolders=False))
            else:
                print(f"  ⚠️  \033[93mNot found or unsupported:\033[0m {path_str}")
        except Exception as e:
            print(f"  ⚠️  \033[93mError resolving path\033[0m '{path_str}': {e}")

    return sorted(set(videos), key=str.lower)


def get_output_directory(images, is_folder_mode=True, first_folder=None, subfolder_name="Padded"):
    """Determine output directory based on input mode."""
    if is_folder_mode and first_folder:
        return os.path.join(first_folder, "Output", subfolder_name)
    elif images:
        first_image_dir = os.path.dirname(images[0])
        return os.path.join(first_image_dir, "Output", subfolder_name)
    else:
        return os.path.join(os.getcwd(), "Output", subfolder_name)


# ─── Image Grouping Helpers ───────────────────────────────────────────────────

def group_images_by_parent_folder(image_paths):
    """
    Group images by their immediate parent folder.
    Returns dict: {parent_folder_path: [image_paths]}
    """
    grouped = {}
    for img_path in image_paths:
        parent = str(pathlib.Path(img_path).parent)
        if parent not in grouped:
            grouped[parent] = []
        grouped[parent].append(img_path)
    return grouped


def get_match_key(filename, match_type, num_chars):
    """Extract match key from filename based on prefix/suffix."""
    name_no_ext = os.path.splitext(filename)[0]
    if match_type == 'prefix':
        return name_no_ext[:num_chars] if len(name_no_ext) >= num_chars else name_no_ext
    else:
        return name_no_ext[-num_chars:] if len(name_no_ext) >= num_chars else name_no_ext


def group_images_by_match(images, match_type, num_chars):
    """Group images by their prefix/suffix match key."""
    from collections import defaultdict
    groups = defaultdict(list)
    for img_path in images:
        filename = os.path.basename(img_path)
        match_key = get_match_key(filename, match_type, num_chars)
        groups[match_key].append(img_path)
    return dict(groups)


def create_sequential_groups(images, group_size):
    """Create sequential groups of images, only including complete groups."""
    groups = []
    for i in range(0, len(images), group_size):
        group = images[i:i + group_size]
        if len(group) == group_size:
            groups.append(group)
    return groups


def build_groups_for_images(images, pairing_mode, group_size=None, match_type=None, num_chars=None):
    """
    Build groups from an image list using sequential or auto-match mode.
    Sequential ('1'): fixed-size groups of group_size, trailing partial
    group dropped.
    Auto-match ('2'): groups sized naturally by shared prefix/suffix match
    key — group_size is ignored, nothing is dropped or truncated to fit a
    target size.
    """
    if pairing_mode == '1':
        return create_sequential_groups(images, group_size)
    else:
        matched = group_images_by_match(images, match_type, num_chars)
        return list(matched.values())


def get_max_dimensions(image_paths):
    """Get maximum dimensions from a list of images, ensuring even numbers."""
    from PIL import Image
    max_width = 0
    max_height = 0
    for img_path in image_paths:
        with Image.open(img_path) as img:
            max_width = max(max_width, img.width)
            max_height = max(max_height, img.height)
    max_width = max_width if max_width % 2 == 0 else max_width + 1
    max_height = max_height if max_height % 2 == 0 else max_height + 1
    return max_width, max_height


# ─── Image Transform Helpers ──────────────────────────────────────────────────

def calculate_padding_offset(img_width, img_height, new_width, new_height, position):
    """Calculate the offset for padding based on position."""
    if position == 'center':
        offset_x = (new_width - img_width) // 2
        offset_y = (new_height - img_height) // 2
    elif position == 'left':
        offset_x = 0
        offset_y = (new_height - img_height) // 2
    elif position == 'right':
        offset_x = new_width - img_width
        offset_y = (new_height - img_height) // 2
    else:
        offset_x = (new_width - img_width) // 2
        offset_y = (new_height - img_height) // 2
    return (offset_x, offset_y)


def create_blurred_background(img, new_width, new_height, bg_mode, blur_radius, opacity):
    """Create an image-based background with blur and opacity."""
    from PIL import Image, ImageFilter
    if bg_mode == 'stretched':
        bg_img = img.copy().resize((new_width, new_height), Image.Resampling.LANCZOS)
    elif bg_mode == 'tiled':
        bg_img = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
        img_width, img_height = img.size
        for y in range(0, new_height, img_height):
            for x in range(0, new_width, img_width):
                bg_img.paste(img, (x, y))
    elif bg_mode == 'centered':
        bg_img = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
        img_width, img_height = img.size
        offset_x = (new_width - img_width) // 2
        offset_y = (new_height - img_height) // 2
        bg_img.paste(img, (offset_x, offset_y))
    else:
        bg_img = img.copy().resize((new_width, new_height), Image.Resampling.LANCZOS)

    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    alpha = Image.new('L', bg_img.size, int(255 * opacity))
    bg_img.putalpha(alpha)
    return bg_img


def get_save_format(img_path):
    """
    Return (pillow_format_str, extension) matching the source file's format.
    Preserves original format silently — no conversion.
    """
    ext = pathlib.Path(img_path).suffix.lower()
    format_map = {
        '.jpg':  ('JPEG', '.jpg'),
        '.jpeg': ('JPEG', '.jpeg'),
        '.png':  ('PNG',  '.png'),
        '.bmp':  ('BMP',  '.bmp'),
        '.gif':  ('GIF',  '.gif'),
        '.webp': ('WEBP', '.webp'),
        '.tiff': ('TIFF', '.tiff'),
    }
    return format_map.get(ext, ('PNG', '.png'))


def resize_pil_image(img, dimension_type, desired_width, desired_height, manual_mode='1'):
    """
    Resize an already-open PIL Image in-memory.
    dimension_type: '1'=Width '2'=Height '3'=Longest Edge '4'=Manual (exact W x H)
    manual_mode (only for '4'): '1'=Stretch '2'=Pad (white, keeps aspect)
    """
    from PIL import Image
    orig_width, orig_height = img.size

    if dimension_type == '1':  # Width
        target_width = desired_width
        target_height = max(1, int(orig_height * (desired_width / orig_width)))
    elif dimension_type == '2':  # Height
        target_height = desired_height
        target_width = max(1, int(orig_width * (desired_height / orig_height)))
    elif dimension_type == '3':  # Longest Edge
        if orig_width >= orig_height:
            target_width = desired_width
            target_height = max(1, int(orig_height * (desired_width / orig_width)))
        else:
            target_height = desired_width
            target_width = max(1, int(orig_width * (desired_width / orig_height)))
    else:  # '4' Manual
        target_width = desired_width
        target_height = desired_height

    if dimension_type == '4' and manual_mode == '2':  # Pad mode — letterbox, keep aspect
        scale = min(target_width / orig_width, target_height / orig_height)
        new_w = max(1, int(orig_width * scale))
        new_h = max(1, int(orig_height * scale))
        img_scaled = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        bg_color = (255, 255, 255, 255) if img_scaled.mode == 'RGBA' else (255, 255, 255)
        canvas = Image.new(img_scaled.mode, (target_width, target_height), bg_color)
        offset = ((target_width - new_w) // 2, (target_height - new_h) // 2)
        if img_scaled.mode == 'RGBA':
            canvas.paste(img_scaled, offset, img_scaled)
        else:
            canvas.paste(img_scaled, offset)
        return canvas
    else:
        return img.resize((target_width, target_height), Image.Resampling.LANCZOS)


def fit_image_to_canvas(img, canvas_width, canvas_height):
    """
    Aspect-preserving fit of img within (canvas_width, canvas_height).
    Returns (resized_img, paste_x, paste_y) — resized_img is not pasted yet.
    """
    img_ratio = img.width / img.height
    target_width = canvas_width
    target_height = int(target_width / img_ratio)
    if target_height > canvas_height:
        target_height = canvas_height
        target_width = int(target_height * img_ratio)

    from PIL import Image
    resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    paste_x = (canvas_width - target_width) // 2
    paste_y = (canvas_height - target_height) // 2
    return resized, paste_x, paste_y


def rotate_or_flip_image(img, operation, choice, custom_angle=None):
    """
    Pure rotate/flip transform on an already-open PIL Image.
    operation: 'rotate' or 'flip'
    choice: for rotate — '90'/'180'/'270'/'custom'; for flip — 'horizontal'/'vertical'
    custom_angle: degrees, positive = counterclockwise (only used when choice == 'custom')
    """
    from PIL import Image
    if operation == 'rotate':
        if choice == '90':
            return img.rotate(90, expand=True)
        elif choice == '180':
            return img.rotate(180, expand=True)
        elif choice == '270':
            return img.rotate(270, expand=True)
        else:
            return img.rotate(-custom_angle, expand=True)
    else:
        if choice == 'horizontal':
            return img.transpose(Image.FLIP_LEFT_RIGHT)
        else:
            return img.transpose(Image.FLIP_TOP_BOTTOM)


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
    """
    return {'1': '_lft', '2': '_rgt', '3': '_top', '4': '_btm'}.get(position, '')


def find_video_for_image(image_path, folder):
    """
    Find a matching video in folder whose stem starts with the image stem.
    Returns the video path string, or None if not found.
    """
    video_exts = ('.mp4', '.mov', '.webm')
    img_stem = pathlib.Path(image_path).stem
    candidates = [
        f for f in os.listdir(folder)
        if pathlib.Path(f).suffix.lower() in video_exts
        and pathlib.Path(f).stem.startswith(img_stem)
    ]
    if candidates:
        return os.path.join(folder, sorted(candidates)[0])
    return None


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

def _collage_one_group(group, direction, longest_edge, output_dir, suffix):
    """
    Build and save one collage image from `group` (any size >= 1).
    Returns the saved path, or None on failure (caller reports the error).
    """
    from PIL import Image

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
    return out_path


def create_collage_from_groups(groups, direction, longest_edge, output_dir, suffix='_comp'):
    """
    Collage pre-built groups directly — each group (whatever size it is)
    becomes one collage image. Use this when groups come from auto-match
    (variable sizes); for fixed-size sequential groups, create_collage's
    chunking gives an identical result.

    Args:
        groups:       list of image-path lists, each already a complete group
        direction:    'H' (horizontal) or 'V' (vertical)
        longest_edge: int, target size for the longest edge after resize
        output_dir:   folder to save collages into (will be created if needed)

    Returns:
        List of saved collage file paths (in order; groups that fail are skipped)
    """
    os.makedirs(output_dir, exist_ok=True)
    collage_paths = []

    for idx, group in enumerate(groups, 1):
        try:
            out_path = _collage_one_group(group, direction, longest_edge, output_dir, suffix)
            collage_paths.append(out_path)
            sys.stdout.write(f"\r\033[93mCollaging \033[0m{idx}/{len(groups)}...")
            sys.stdout.flush()
        except Exception as e:
            print(f"\033[93m❌ Error creating collage for group {idx}: {e}\033[0m")

    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()
    print(f"\033[92m✅ {len(collage_paths)} collage(s) created → {output_dir}\033[0m")
    return collage_paths


def create_collage(image_paths, direction, longest_edge, output_dir, group_size, suffix='_comp'):
    """
    Group images sequentially into fixed-size chunks, then collage each
    group (see create_collage_from_groups). Trailing partial group is
    dropped with a warning.

    Args:
        image_paths:  flat list of image paths (already sorted/ordered)
        direction:    'H' (horizontal) or 'V' (vertical)
        longest_edge: int, target size for the longest edge after resize
        output_dir:   folder to save collages into (will be created if needed)
        group_size:   how many images per collage

    Returns:
        List of saved collage file paths (in order)
    """
    groups = [image_paths[i:i + group_size] for i in range(0, len(image_paths), group_size)]
    complete_groups = [g for g in groups if len(g) == group_size]

    if len(complete_groups) < len(groups):
        leftover = len(image_paths) - len(complete_groups) * group_size
        print(f"\033[93m⚠️  {leftover} image(s) left over (incomplete group) — skipped\033[0m")

    return create_collage_from_groups(complete_groups, direction, longest_edge, output_dir, suffix)


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