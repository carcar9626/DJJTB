import os
import subprocess
import sys
import time
from PIL import Image, ImageFilter
import pathlib
import logging
import djjtb.utils as djj

def clear_screen():
    """Clear the terminal screen."""
    os.system('clear')

def clean_path(path_str):
    """Clean input path by removing quotes and extra spaces."""
    return path_str.strip().strip('\'"')

def setup_logging(output_path):
    """Set up logging to a file in the output folder."""
    log_file = os.path.join(output_path, 'padding_errors.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger()

def is_valid_image(filename):
    """Check if filename has a valid image extension."""
    return filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff'))

def collect_images_from_folder(input_path, subfolders=False):
    """Collect images from folder(s), never descending into Output dirs."""
    input_path_obj = pathlib.Path(input_path)
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff')

    images = []
    if input_path_obj.is_dir():
        if subfolders:
            for root, dirs, files in os.walk(input_path):
                # Prune Output folders in-place so walk never descends into them
                dirs[:] = [d for d in dirs if d.lower() != 'output']
                images.extend(pathlib.Path(root) / f for f in files if pathlib.Path(f).suffix.lower() in image_extensions)
        else:
            images = [f for f in input_path_obj.glob('*') if f.suffix.lower() in image_extensions and f.is_file()]

    return sorted([str(v) for v in images], key=str.lower)

def collect_images_from_paths(raw_input):
    """
    Collect images from space-separated paths (supports drag-and-drop).
    Handles quoted paths, escaped spaces, files and folders mixed together.
    """
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff')
    images = []

    # Split on whitespace but respect quoted paths — handle both quoted and unquoted drag-drop
    # Strategy: strip outer quotes first, then split on whitespace
    # This covers macOS drag-and-drop which escapes spaces as '\ '
    raw = raw_input.strip()

    # Rebuild tokens: split on spaces, but re-join tokens that are escaped spaces
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
            if path_obj.is_file() and path_obj.suffix.lower() in image_extensions:
                images.append(str(path_obj))
            elif path_obj.is_dir():
                images.extend(collect_images_from_folder(str(path_obj), subfolders=False))
            else:
                print(f"  ⚠️  \033[93mNot found or unsupported:\033[0m {path_str}")
        except Exception as e:
            print(f"  ⚠️  \033[93mError resolving path\033[0m '{path_str}': {e}")

    return sorted(set(images), key=str.lower)

def get_output_directory(images, is_folder_mode=True, first_folder=None, subfolder_name="Padded"):
    """Determine output directory based on input mode."""
    if is_folder_mode and first_folder:
        return os.path.join(first_folder, "Output", subfolder_name)
    elif images:
        first_image_dir = os.path.dirname(images[0])
        return os.path.join(first_image_dir, "Output", subfolder_name)
    else:
        return os.path.join(os.getcwd(), "Output", subfolder_name)

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

def create_image_background(img, new_width, new_height, bg_mode, blur_radius, opacity):
    """Create an image-based background with blur and opacity."""
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

def pad_images(images, output_dir, shape, pad_percent, color, custom_width, custom_height,
               custom_color, padding_position, bg_type, bg_mode, bg_blur, bg_opacity):
    """
    Pad images to the specified shape/size.
    shape == 'percent': adds pad_percent% of each image's own width/height on all 4 sides.
    Output format always matches the source file — no conversion.
    """
    os.makedirs(output_dir, exist_ok=True)
    logger = setup_logging(output_dir)

    print()
    print(f"{len(images)} \033[93mimages found\033[0m")
    print()
    print("\033[93mPadding images...\033[0m")

    successful = []
    failed = []
    skipped = []
    output_dirs_used = set()

    color_map = {'white': (255, 255, 255, 255), 'black': (0, 0, 0, 255), 'grey': (128, 128, 128, 255)}
    padding_color = custom_color if color == 'custom' else color_map.get(color, (255, 255, 255, 255))

    for i, img_path in enumerate(images, 1):
        try:
            with Image.open(img_path) as img:
                img = img.convert('RGBA')
                width, height = img.size

                if shape == 'square':
                    target_size = max(width, height)
                    new_width = new_height = target_size
                    position = 'center'
                elif shape == 'landscape':
                    new_width = int(height * 16 / 9)
                    new_height = height
                    position = padding_position
                elif shape == 'portrait':
                    new_width = int(height * 9 / 16)
                    new_height = height
                    position = padding_position
                elif shape == 'percent':
                    # Add pad_percent% of each dimension on each side
                    pad_x = int(width * pad_percent / 100)
                    pad_y = int(height * pad_percent / 100)
                    new_width = width + pad_x * 2
                    new_height = height + pad_y * 2
                    position = 'center'  # Percent mode always centers
                else:  # custom
                    new_width = custom_width
                    new_height = custom_height
                    position = padding_position

                # Create background
                if bg_type == 'image':
                    new_image = create_image_background(img, new_width, new_height, bg_mode, bg_blur, bg_opacity)
                else:
                    new_image = Image.new('RGBA', (new_width, new_height), padding_color)

                # Paste original centered/positioned
                offset = calculate_padding_offset(width, height, new_width, new_height, position)
                new_image.paste(img, offset, img)

                # Save in source format — output sits in each image's own parent/Output/Padded/
                pillow_format, file_ext = get_save_format(img_path)
                img_path_obj = pathlib.Path(img_path)
                img_output_dir = img_path_obj.parent / "Output" / "Padded"
                img_output_dir.mkdir(parents=True, exist_ok=True)
                output_filename = f"{img_path_obj.stem}_padded{file_ext}"
                output_path = img_output_dir / output_filename

                if output_path.exists():
                    skipped.append(img_path_obj.name)
                    output_dirs_used.add(str(img_output_dir))
                    sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)...")
                    sys.stdout.flush()
                    continue

                save_kwargs = {}
                if pillow_format == 'JPEG':
                    new_image = new_image.convert('RGB')
                    save_kwargs['quality'] = 95
                elif pillow_format == 'WEBP':
                    save_kwargs['quality'] = 95

                new_image.save(str(output_path), format=pillow_format, **save_kwargs)
                successful.append(img_path_obj.name)
                output_dirs_used.add(str(img_output_dir))

            sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)...")
            sys.stdout.flush()

        except Exception as e:
            failed.append((pathlib.Path(img_path).name, str(e)))
            logger.error(f"Failed to process {img_path}: {e}")
            sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)... ❌")
            sys.stdout.flush()

    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

    return successful, failed, skipped, sorted(output_dirs_used)


# ─── Crop Edges (new feature) ────────────────────────────────────────────────

# Toggle-style multi-select, matching the pattern used in
# facefusion_runner.py's pick_multiple_from_default_faces(): re-display the
# menu with checkmarks after each toggle, empty Enter confirms the selection.
CROP_EDGE_OPTIONS = [
    ('top', 'Top'),
    ('bottom', 'Bottom'),
    ('left', 'Left'),
    ('right', 'Right'),
]

def get_crop_edges():
    """
    Toggle which edge(s) to trim, one number at a time. Press Enter on an
    empty line to confirm. "5. All" toggles all four at once.
    Returns a set of strings from {'top','bottom','left','right'}.
    """
    selected = set()
    all_keys = {key for key, _ in CROP_EDGE_OPTIONS}

    while True:
        print("\033[93mWhich edges to trim?\033[0m")
        print("\033[93m" + "-" * 30 + "\033[0m")
        for i, (key, label) in enumerate(CROP_EDGE_OPTIONS, 1):
            marker = " ✅" if key in selected else ""
            print(f"  {i}. {label}{marker}")
        all_marker = " ✅" if selected == all_keys else ""
        print(f"  5. All{all_marker}")
        print("\033[93m" + "-" * 30 + "\033[0m")

        if selected:
            chosen_labels = [label for key, label in CROP_EDGE_OPTIONS if key in selected]
            print(f"\033[92mCurrently selected:\033[0m {', '.join(chosen_labels)}")

        print("\033[93mEnter a number to toggle, or press Enter to confirm:\033[0m")
        raw = input(" > ").strip()

        if raw == '':
            if not selected:
                print("\033[93m⚠️  No edges selected. Pick at least one.\033[0m\n")
                continue
            break

        if raw in ('1', '2', '3', '4'):
            idx = int(raw) - 1
            key, label = CROP_EDGE_OPTIONS[idx]
            if key in selected:
                selected.remove(key)
                print(f"\033[93m➖ Removed:\033[0m {label}\n")
            else:
                selected.add(key)
                print(f"\033[92m➕ Added:\033[0m {label}\n")
        elif raw == '5':
            if selected == all_keys:
                selected.clear()
                print("\033[93m➖ Removed:\033[0m All\n")
            else:
                selected = set(all_keys)
                print("\033[92m➕ Added:\033[0m All\n")
        else:
            print(f"\033[93mInvalid input. Enter 1-5, or press Enter to confirm.\033[0m\n")

    print(f"\033[92m✅ {len(selected)} edge(s) selected.\033[0m")
    print()
    return selected


def get_crop_amount():
    """Ask for trim amount in pixels: 4px / 8px presets, or custom."""
    choice = djj.prompt_choice(
        "\033[93mTrim amount:\033[0m\n1. 4px\n2. 8px\n3. Custom\n",
        ['1', '2', '3'],
        default='1'
    )
    if choice == '1':
        return 4
    elif choice == '2':
        return 8
    else:
        return djj.get_int_input("\033[93mCustom trim amount in pixels\033[0m", min_val=1)


# ─── Resize (ported from image_resizer.py, operates in-memory) ──────────────

def get_resize_target():
    """
    Ask for a resize target, mirroring image_resizer.py's dimension modes.
    Returns (dimension_type, desired_width, desired_height, manual_mode)
    dimension_type: '1'=Width '2'=Height '3'=Longest Edge '4'=Manual (exact W x H)
    """
    dimension_type = djj.prompt_choice(
        "\033[93mResize target:\033[0m\n"
        "1. Width\n"
        "2. Height\n"
        "3. Longest Edge\n"
        "4. Manual (exact W x H)\n",
        ['1', '2', '3', '4'],
        default='4'
    )
    print()

    desired_width = 0
    desired_height = 0
    manual_mode = '1'

    if dimension_type != '4':
        desired_width = djj.get_int_input("\033[93mTarget dimension in px\033[0m", min_val=1)
        print()
    else:
        manual_mode = djj.prompt_choice(
            "\033[93mManual mode:\033[0m\n1. Stretch\n2. Pad (white, keeps aspect)\n",
            ['1', '2'],
            default='1'
        )
        print()
        desired_width = djj.get_int_input("\033[93mTarget width in px\033[0m", min_val=1)
        print()
        desired_height = djj.get_int_input("\033[93mTarget height in px\033[0m", min_val=1)
        print()

    return dimension_type, desired_width, desired_height, manual_mode


def resize_pil_image(img, dimension_type, desired_width, desired_height, manual_mode='1'):
    """
    Resize an already-open PIL Image in-memory. Mirrors image_resizer.py's
    resize_images() math exactly, just operating on an Image object instead
    of reading/writing files, so it can be chained after a crop with no
    intermediate disk write.
    """
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


def resize_only_images(images, dimension_type, desired_width, desired_height, manual_mode='1'):
    """
    Resize with no cropping step. Preserves source format (unlike the old
    image_resizer.py, which forced PNG/JPG output).
    Output: each image's parent/Output/Resized/
    """
    print()
    print(f"{len(images)} \033[93mimages found\033[0m")
    print()
    print("\033[93mResizing images...\033[0m")

    successful = []
    failed = []
    skipped = []
    output_dirs_used = set()

    for i, img_path in enumerate(images, 1):
        try:
            with Image.open(img_path) as img:
                resized = resize_pil_image(img, dimension_type, desired_width, desired_height, manual_mode)

                pillow_format, file_ext = get_save_format(img_path)
                img_path_obj = pathlib.Path(img_path)
                img_output_dir = img_path_obj.parent / "Output" / "Resized"
                img_output_dir.mkdir(parents=True, exist_ok=True)
                output_filename = f"{img_path_obj.stem}_r{file_ext}"
                output_path = img_output_dir / output_filename

                if output_path.exists():
                    skipped.append(img_path_obj.name)
                    output_dirs_used.add(str(img_output_dir))
                    sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)...")
                    sys.stdout.flush()
                    continue

                save_kwargs = {}
                if pillow_format == 'JPEG' and resized.mode == 'RGBA':
                    resized = resized.convert('RGB')
                    save_kwargs['quality'] = 95
                elif pillow_format == 'JPEG':
                    save_kwargs['quality'] = 95
                elif pillow_format == 'WEBP':
                    save_kwargs['quality'] = 95

                resized.save(str(output_path), format=pillow_format, **save_kwargs)
                successful.append(img_path_obj.name)
                output_dirs_used.add(str(img_output_dir))

            sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)...")
            sys.stdout.flush()

        except Exception as e:
            failed.append((pathlib.Path(img_path).name, str(e)))
            sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)... ❌")
            sys.stdout.flush()

    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

    return successful, failed, skipped, sorted(output_dirs_used)


def crop_and_resize_images(images, edges, trim_px, dimension_type, desired_width, desired_height, manual_mode='1'):
    """
    Crop selected edges, then resize — all in-memory per image, one save.
    Output: each image's parent/Output/Cropped_Resized/
    """
    print()
    print(f"{len(images)} \033[93mimages found\033[0m")
    print()
    edge_label = " + ".join(label for key, label in CROP_EDGE_OPTIONS if key in edges)
    print(f"\033[93mCropping ({edge_label} @ {trim_px}px) then resizing...\033[0m")

    successful = []
    failed = []
    skipped = []
    output_dirs_used = set()

    for i, img_path in enumerate(images, 1):
        try:
            with Image.open(img_path) as img:
                width, height = img.size

                left_trim   = trim_px if 'left' in edges else 0
                right_trim  = trim_px if 'right' in edges else 0
                top_trim    = trim_px if 'top' in edges else 0
                bottom_trim = trim_px if 'bottom' in edges else 0

                new_width = width - left_trim - right_trim
                new_height = height - top_trim - bottom_trim

                if new_width <= 0 or new_height <= 0:
                    failed.append((pathlib.Path(img_path).name,
                                   f"Trim too large for {width}x{height} image"))
                    sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)... ❌")
                    sys.stdout.flush()
                    continue

                box = (left_trim, top_trim, width - right_trim, height - bottom_trim)
                cropped = img.crop(box)
                resized = resize_pil_image(cropped, dimension_type, desired_width, desired_height, manual_mode)

                pillow_format, file_ext = get_save_format(img_path)
                img_path_obj = pathlib.Path(img_path)
                img_output_dir = img_path_obj.parent / "Output" / "Cropped_Resized"
                img_output_dir.mkdir(parents=True, exist_ok=True)
                output_filename = f"{img_path_obj.stem}_cr{file_ext}"
                output_path = img_output_dir / output_filename

                if output_path.exists():
                    skipped.append(img_path_obj.name)
                    output_dirs_used.add(str(img_output_dir))
                    sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)...")
                    sys.stdout.flush()
                    continue

                save_kwargs = {}
                if pillow_format == 'JPEG' and resized.mode == 'RGBA':
                    resized = resized.convert('RGB')
                    save_kwargs['quality'] = 95
                elif pillow_format == 'JPEG':
                    save_kwargs['quality'] = 95
                elif pillow_format == 'WEBP':
                    save_kwargs['quality'] = 95

                resized.save(str(output_path), format=pillow_format, **save_kwargs)
                successful.append(img_path_obj.name)
                output_dirs_used.add(str(img_output_dir))

            sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)...")
            sys.stdout.flush()

        except Exception as e:
            failed.append((pathlib.Path(img_path).name, str(e)))
            sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)... ❌")
            sys.stdout.flush()

    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

    return successful, failed, skipped, sorted(output_dirs_used)


def crop_images(images, edges, trim_px):
    """
    Trim `trim_px` pixels off each edge in `edges` for every image.
    Same trim amount applies uniformly to every selected edge.
    Output format always matches the source file — no conversion.
    Output: each image's parent/Output/Cropped/
    """
    print()
    print(f"{len(images)} \033[93mimages found\033[0m")
    print()
    edge_label = " + ".join(e.capitalize() for e in sorted(edges))
    print(f"\033[93mCropping images —\033[0m {edge_label} \033[93m@ {trim_px}px...\033[0m")

    successful = []
    failed = []
    skipped = []
    output_dirs_used = set()

    for i, img_path in enumerate(images, 1):
        try:
            with Image.open(img_path) as img:
                width, height = img.size

                left_trim   = trim_px if 'left' in edges else 0
                right_trim  = trim_px if 'right' in edges else 0
                top_trim    = trim_px if 'top' in edges else 0
                bottom_trim = trim_px if 'bottom' in edges else 0

                new_width = width - left_trim - right_trim
                new_height = height - top_trim - bottom_trim

                if new_width <= 0 or new_height <= 0:
                    failed.append((pathlib.Path(img_path).name,
                                   f"Trim too large for {width}x{height} image"))
                    sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)... ❌")
                    sys.stdout.flush()
                    continue

                box = (left_trim, top_trim, width - right_trim, height - bottom_trim)
                cropped = img.crop(box)

                pillow_format, file_ext = get_save_format(img_path)
                img_path_obj = pathlib.Path(img_path)
                img_output_dir = img_path_obj.parent / "Output" / "Cropped"
                img_output_dir.mkdir(parents=True, exist_ok=True)
                output_filename = f"{img_path_obj.stem}_cropped{file_ext}"
                output_path = img_output_dir / output_filename

                if output_path.exists():
                    skipped.append(img_path_obj.name)
                    output_dirs_used.add(str(img_output_dir))
                    sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)...")
                    sys.stdout.flush()
                    continue

                save_kwargs = {}
                if pillow_format == 'JPEG' and cropped.mode == 'RGBA':
                    cropped = cropped.convert('RGB')
                    save_kwargs['quality'] = 95
                elif pillow_format == 'JPEG':
                    save_kwargs['quality'] = 95
                elif pillow_format == 'WEBP':
                    save_kwargs['quality'] = 95

                cropped.save(str(output_path), format=pillow_format, **save_kwargs)
                successful.append(img_path_obj.name)
                output_dirs_used.add(str(img_output_dir))

            sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)...")
            sys.stdout.flush()

        except Exception as e:
            failed.append((pathlib.Path(img_path).name, str(e)))
            sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)... ❌")
            sys.stdout.flush()

    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

    return successful, failed, skipped, sorted(output_dirs_used)


def print_summary(title, successful, failed, skipped, output_dirs_used, output_dir_fallback):
    """Shared summary printer for both Pad and Crop operations."""
    print()
    print(f"\033[93m{title}\033[0m")
    print("-------------")
    print(f"✅ \033[93mSuccessfully processed:\033[0m {len(successful)} images")
    if skipped:
        print(f"⏭️  \033[93mSkipped (already exists):\033[0m {len(skipped)}")
    if failed:
        print(f"❌ \033[93mFailed:\033[0m {len(failed)} (see padding_errors.log in output folder)")
        for name, err in failed[:3]:
            print(f"   • {name}: {err}")
    if len(output_dirs_used) == 1:
        print(f"📁 \033[93mOutput folder:\033[0m\n{output_dirs_used[0]}")
    elif output_dirs_used:
        print(f"📁 \033[93mOutput folders:\033[0m {len(output_dirs_used)} (one per source folder)")
        for d in output_dirs_used[:4]:
            print(f"   {d}")
        if len(output_dirs_used) > 4:
            print(f"   ... and {len(output_dirs_used) - 4} more")
    print()

    open_target = output_dirs_used[0] if output_dirs_used else output_dir_fallback
    djj.prompt_open_folder(open_target)


def main():
    while True:
        clear_screen()
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mImage Padder\033[0m")
        print("Adds padding to images / crops edges")
        print("\033[92m==================================================\033[0m")
        print()

        # ── Input mode ────────────────────────────────────────────────────────
        input_mode = djj.prompt_choice(
            "Input mode:\n1. Folder path\n2. Space-separated file paths\n",
            ['1', '2'],
            default='1'
        )
        print()

        images = []
        output_dir = None

        if input_mode == '1':
            src_dir = djj.get_path_input("Enter folder path")
            print()
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            images = collect_images_from_folder(src_dir, include_sub)
            if not include_sub:
                images = djj.apply_skip_list(images, root=src_dir)
            output_dir = get_output_directory(images, is_folder_mode=True, first_folder=src_dir)

        else:
            print("📁 \033[93mEnter image paths (space-separated, drag-and-drop ok):\033[0m")
            raw = input(" -> ").strip()
            if not raw:
                print("❌ No file paths provided.")
                continue
            images = collect_images_from_paths(raw)
            output_dir = get_output_directory(images, is_folder_mode=False)
            print()

        if not images:
            print("❌ \033[93mNo valid image files found.\033[0m")
            continue

        print(f"✅ \033[93m{len(images)} image(s) found\033[0m")
        print()

        # ── Operation: Pad vs Crop vs Crop+Resize vs Resize only ─────────────
        operation = djj.prompt_choice(
            "\033[93mOperation:\033[0m\n"
            "1. Pad images\n"
            "2. Crop edges (trim by pixel amount)\n"
            "3. Crop edges + Resize (trim, then resize to target)\n"
            "4. Resize only (no crop)\n",
            ['1', '2', '3', '4'],
            default='1'
        )
        print()

        # ═══════════════════════════════════════════════════════════════════
        #  RESIZE ONLY
        # ═══════════════════════════════════════════════════════════════════
        if operation == '4':
            dimension_type, desired_width, desired_height, manual_mode = get_resize_target()

            print("-------------")
            successful, failed, skipped, output_dirs_used = resize_only_images(
                images, dimension_type, desired_width, desired_height, manual_mode
            )

            print_summary("Resize Summary", successful, failed, skipped,
                         output_dirs_used, get_output_directory(images, is_folder_mode=False, subfolder_name="Resized"))

            action = djj.what_next()
            if action == 'exit':
                break
            continue

        # ═══════════════════════════════════════════════════════════════════
        #  CROP EDGES + RESIZE
        # ═══════════════════════════════════════════════════════════════════
        if operation == '3':
            edges = get_crop_edges()
            trim_px = get_crop_amount()
            print()
            dimension_type, desired_width, desired_height, manual_mode = get_resize_target()

            print("-------------")
            successful, failed, skipped, output_dirs_used = crop_and_resize_images(
                images, edges, trim_px, dimension_type, desired_width, desired_height, manual_mode
            )

            print_summary("Crop + Resize Summary", successful, failed, skipped,
                         output_dirs_used, get_output_directory(images, is_folder_mode=False, subfolder_name="Cropped_Resized"))

            action = djj.what_next()
            if action == 'exit':
                break
            continue

        # ═══════════════════════════════════════════════════════════════════
        #  CROP EDGES
        # ═══════════════════════════════════════════════════════════════════
        if operation == '2':
            edges = get_crop_edges()
            print()
            trim_px = get_crop_amount()
            print()

            print("-------------")
            successful, failed, skipped, output_dirs_used = crop_images(images, edges, trim_px)

            print_summary("Cropping Summary", successful, failed, skipped,
                         output_dirs_used, get_output_directory(images, is_folder_mode=False, subfolder_name="Cropped"))

            action = djj.what_next()
            if action == 'exit':
                break
            continue

        # ═══════════════════════════════════════════════════════════════════
        #  PAD IMAGES (existing flow, unchanged)
        # ═══════════════════════════════════════════════════════════════════

        # ── Shape / size mode ─────────────────────────────────────────────────
        shape_choice = djj.prompt_choice(
            "\033[93mPadding mode:\033[0m\n"
            "1. Square (pad shorter edge to match longer)\n"
            "2. Landscape (16:9)\n"
            "3. Portrait (9:16)\n"
            "4. Custom dimensions\n"
            "5. Pad by % (add equal padding all 4 sides)\n",
            ['1', '2', '3', '4', '5'],
            default='1'
        )
        print()

        shape_map = {'1': 'square', '2': 'landscape', '3': 'portrait', '4': 'custom', '5': 'percent'}
        shape = shape_map[shape_choice]

        pad_percent = 0.0
        custom_width = None
        custom_height = None

        if shape == 'percent':
            while True:
                pct_input = input("\033[93mPad percentage per side [default: 10]:\033[0m\n -> ").strip()
                try:
                    pad_percent = float(pct_input) if pct_input else 10.0
                    if pad_percent <= 0:
                        print("\033[93mPlease enter a positive number.\033[0m")
                        continue
                    break
                except ValueError:
                    print("\033[93mPlease enter a valid number.\033[0m")
            img_w_example, img_h_example = 0, 0
            try:
                with Image.open(images[0]) as _ex:
                    img_w_example, img_h_example = _ex.size
                pad_px_w = int(img_w_example * pad_percent / 100)
                pad_px_h = int(img_h_example * pad_percent / 100)
                print(f"  → First image ({img_w_example}×{img_h_example}): adds {pad_px_w}px left/right, {pad_px_h}px top/bottom")
                print(f"    Canvas will be {img_w_example + pad_px_w*2}×{img_h_example + pad_px_h*2}")
            except Exception:
                pass
            print()

        elif shape == 'custom':
            custom_width = djj.get_int_input("\033[93mCustom width in pixels\033[0m", min_val=1)
            print()
            custom_height = djj.get_int_input("\033[93mCustom height in pixels\033[0m", min_val=1)
            print()

        # ── Padding position (not used in percent/square modes, shown for others) ──
        padding_position = 'center'
        if shape in ('landscape', 'portrait', 'custom'):
            pos_choice = djj.prompt_choice(
                "\033[93mImage position:\033[0m\n1. Center\n2. Left\n3. Right\n",
                ['1', '2', '3'],
                default='1'
            )
            padding_position = {'1': 'center', '2': 'left', '3': 'right'}[pos_choice]
            print()

        # ── Background type ───────────────────────────────────────────────────
        bg_type_choice = djj.prompt_choice(
            "\033[93mBackground type:\033[0m\n1. Solid color\n2. Blurred image fill\n",
            ['1', '2'],
            default='1'
        )
        print()

        bg_type = 'solid' if bg_type_choice == '1' else 'image'
        bg_mode = None
        bg_blur = 8
        bg_opacity = 0.25
        color = 'white'
        custom_color = None

        if bg_type == 'image':
            bg_mode_choice = djj.prompt_choice(
                "\033[93mImage background mode:\033[0m\n1. Stretched\n2. Tiled\n3. Centered\n",
                ['1', '2', '3'],
                default='1'
            )
            bg_mode = {'1': 'stretched', '2': 'tiled', '3': 'centered'}[bg_mode_choice]
            print()

            bg_blur_input = input("\033[93mBlur radius [1-50, default 8]:\033[0m\n -> ").strip()
            try:
                bg_blur = int(bg_blur_input) if bg_blur_input else 8
                bg_blur = max(1, min(50, bg_blur))
            except ValueError:
                bg_blur = 8
            print()

            bg_opacity_input = input("\033[93mOpacity [0.0–1.0, default 0.25]:\033[0m\n -> ").strip()
            try:
                bg_opacity = float(bg_opacity_input) if bg_opacity_input else 0.25
                bg_opacity = max(0.0, min(1.0, bg_opacity))
            except ValueError:
                bg_opacity = 0.25
            print()

        else:
            # Solid color
            color_choice = djj.prompt_choice(
                "\033[93mPadding color:\033[0m\n1. White\n2. Black\n3. Grey\n4. Custom RGBA\n",
                ['1', '2', '3', '4'],
                default='1'
            )
            print()
            color = {'1': 'white', '2': 'black', '3': 'grey', '4': 'custom'}[color_choice]

            if color == 'custom':
                for attempt in range(5):
                    try:
                        color_input = input("\033[93mCustom color (R,G,B,A e.g. 255,200,100,255):\033[0m\n -> ").strip()
                        r, g, b, a = map(int, color_input.split(','))
                        if all(0 <= x <= 255 for x in [r, g, b, a]):
                            custom_color = (r, g, b, a)
                            break
                        print("\033[93mEach value must be 0–255.\033[0m")
                    except ValueError:
                        print("\033[93mPlease enter four comma-separated integers.\033[0m")
                else:
                    print("\033[93mToo many invalid attempts. Exiting.\033[0m")
                    sys.exit(1)
                print()

        # ── Process ───────────────────────────────────────────────────────────
        print("-------------")
        successful, failed, skipped, output_dirs_used = pad_images(
            images, output_dir,
            shape, pad_percent,
            color, custom_width, custom_height, custom_color,
            padding_position, bg_type, bg_mode, bg_blur, bg_opacity
        )

        print_summary("Padding Summary", successful, failed, skipped, output_dirs_used, output_dir)

        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()