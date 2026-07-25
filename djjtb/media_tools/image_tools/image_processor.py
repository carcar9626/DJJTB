import os
import sys
import subprocess
import pathlib
import tempfile
import shutil
import random
from PIL import Image, ImageChops
import numpy as np
from scipy.ndimage import label, find_objects
import djjtb.utils as djj


# Shared by Rotate/Flip and Convert Format: user-chosen format name -> (Pillow format, extension).
OUTPUT_FORMAT_MAP = {
    'png': ('PNG', '.png'),
    'jpg': ('JPEG', '.jpg'),
    'webp': ('WEBP', '.webp'),
    'bmp': ('BMP', '.bmp'),
    'gif': ('GIF', '.gif'),
}


# ─── Shared per-image batch loop (Pad / Crop / Resize / Crop+Resize / Convert) ─

def _default_save_kwargs(pillow_format, image):
    """Standard JPEG/WEBP quality=95 save rule shared by Pad/Crop/Resize/Crop+Resize."""
    save_kwargs = {}
    if pillow_format == 'JPEG':
        if image.mode != 'RGB':
            image = image.convert('RGB')
        save_kwargs['quality'] = 95
    elif pillow_format == 'WEBP':
        save_kwargs['quality'] = 95
    return image, save_kwargs


def _run_batch(images, subfolder_name, suffix, header_msg, transform_fn,
               save_format_fn=None, save_kwargs_fn=None, logger=None, error_verb="process"):
    """
    Shared per-image batch loop for Pad/Crop/Resize/Crop+Resize/Convert.

    transform_fn(img, img_path) -> processed PIL Image ready to save; raise
    to record a per-image failure (caught below like any other error).
    save_format_fn(img_path) -> (pillow_format, file_ext); defaults to
    djj.get_save_format (source format preserved).
    save_kwargs_fn(pillow_format, image) -> (image, save_kwargs); defaults
    to the standard JPEG/WEBP quality=95 rule.
    Output: each image's parent/Output/<subfolder_name>/<stem>_<suffix><ext>.
    """
    if save_format_fn is None:
        save_format_fn = djj.get_save_format
    if save_kwargs_fn is None:
        save_kwargs_fn = _default_save_kwargs

    print()
    print(f"{len(images)} \033[93mimages found\033[0m")
    print()
    print(header_msg)

    successful = []
    failed = []
    skipped = []
    output_dirs_used = set()

    for i, img_path in enumerate(images, 1):
        try:
            with Image.open(img_path) as img:
                processed = transform_fn(img, img_path)

                pillow_format, file_ext = save_format_fn(img_path)
                img_path_obj = pathlib.Path(img_path)
                img_output_dir = img_path_obj.parent / "Output" / subfolder_name
                img_output_dir.mkdir(parents=True, exist_ok=True)
                output_filename = f"{img_path_obj.stem}_{suffix}{file_ext}"
                output_path = img_output_dir / output_filename

                if output_path.exists():
                    skipped.append(img_path_obj.name)
                    output_dirs_used.add(str(img_output_dir))
                    sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)...")
                    sys.stdout.flush()
                    continue

                processed, save_kwargs = save_kwargs_fn(pillow_format, processed)

                processed.save(str(output_path), format=pillow_format, **save_kwargs)
                successful.append(img_path_obj.name)
                output_dirs_used.add(str(img_output_dir))

            sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)...")
            sys.stdout.flush()

        except Exception as e:
            failed.append((pathlib.Path(img_path).name, str(e)))
            if logger:
                logger.error(f"Failed to {error_verb} {img_path}: {e}")
            sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)... ❌")
            sys.stdout.flush()

    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

    return successful, failed, skipped, sorted(output_dirs_used)


# ─── Pad ──────────────────────────────────────────────────────────────────────

def pad_images(images, output_dir, shape, pad_percent, color, custom_width, custom_height,
               custom_color, padding_position, bg_type, bg_mode, bg_blur, bg_opacity):
    """
    Pad images to the specified shape/size.
    shape == 'percent': adds pad_percent% of each image's own width/height on all 4 sides.
    Output format always matches the source file — no conversion.
    """
    os.makedirs(output_dir, exist_ok=True)
    logger = djj.setup_logging(output_dir, script_name="image_processor_pad")

    color_map = {'white': (255, 255, 255, 255), 'black': (0, 0, 0, 255), 'grey': (128, 128, 128, 255)}
    padding_color = custom_color if color == 'custom' else color_map.get(color, (255, 255, 255, 255))

    def transform(img, img_path):
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
            pad_x = int(width * pad_percent / 100)
            pad_y = int(height * pad_percent / 100)
            new_width = width + pad_x * 2
            new_height = height + pad_y * 2
            position = 'center'  # Percent mode always centers
        else:  # custom
            new_width = custom_width
            new_height = custom_height
            position = padding_position

        if bg_type == 'image':
            new_image = djj.create_blurred_background(img, new_width, new_height, bg_mode, bg_blur, bg_opacity)
        else:
            new_image = Image.new('RGBA', (new_width, new_height), padding_color)

        offset = djj.calculate_padding_offset(width, height, new_width, new_height, position)
        new_image.paste(img, offset, img)
        return new_image

    return _run_batch(
        images, "Padded", "padded", "\033[93mPadding images...\033[0m",
        transform, logger=logger, error_verb="process"
    )


# ─── Crop Edges ───────────────────────────────────────────────────────────────

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


def crop_images(images, edges, trim_px):
    """
    Trim `trim_px` pixels off each edge in `edges` for every image.
    Same trim amount applies uniformly to every selected edge.
    Output format always matches the source file — no conversion.
    Output: each image's parent/Output/Cropped/
    """
    edge_label = " + ".join(e.capitalize() for e in sorted(edges))

    def transform(img, img_path):
        width, height = img.size

        left_trim   = trim_px if 'left' in edges else 0
        right_trim  = trim_px if 'right' in edges else 0
        top_trim    = trim_px if 'top' in edges else 0
        bottom_trim = trim_px if 'bottom' in edges else 0

        new_width = width - left_trim - right_trim
        new_height = height - top_trim - bottom_trim
        if new_width <= 0 or new_height <= 0:
            raise ValueError(f"Trim too large for {width}x{height} image")

        box = (left_trim, top_trim, width - right_trim, height - bottom_trim)
        return img.crop(box)

    return _run_batch(
        images, "Cropped", "cropped",
        f"\033[93mCropping images —\033[0m {edge_label} \033[93m@ {trim_px}px...\033[0m",
        transform
    )


# ─── Resize (in-memory, chainable after crop) ────────────────────────────────

def get_resize_target():
    """
    Ask for a resize target.
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


def resize_only_images(images, dimension_type, desired_width, desired_height, manual_mode='1'):
    """
    Resize with no cropping step. Preserves source format.
    Output: each image's parent/Output/Resized/
    """
    def transform(img, img_path):
        return djj.resize_pil_image(img, dimension_type, desired_width, desired_height, manual_mode)

    return _run_batch(images, "Resized", "r", "\033[93mResizing images...\033[0m", transform)


def crop_and_resize_images(images, edges, trim_px, dimension_type, desired_width, desired_height, manual_mode='1'):
    """
    Crop selected edges, then resize — all in-memory per image, one save.
    Output: each image's parent/Output/Cropped_Resized/
    """
    edge_label = " + ".join(label for key, label in CROP_EDGE_OPTIONS if key in edges)

    def transform(img, img_path):
        width, height = img.size

        left_trim   = trim_px if 'left' in edges else 0
        right_trim  = trim_px if 'right' in edges else 0
        top_trim    = trim_px if 'top' in edges else 0
        bottom_trim = trim_px if 'bottom' in edges else 0

        new_width = width - left_trim - right_trim
        new_height = height - top_trim - bottom_trim
        if new_width <= 0 or new_height <= 0:
            raise ValueError(f"Trim too large for {width}x{height} image")

        box = (left_trim, top_trim, width - right_trim, height - bottom_trim)
        cropped = img.crop(box)
        return djj.resize_pil_image(cropped, dimension_type, desired_width, desired_height, manual_mode)

    return _run_batch(
        images, "Cropped_Resized", "cr",
        f"\033[93mCropping ({edge_label} @ {trim_px}px) then resizing...\033[0m",
        transform
    )


def print_batch_summary(title, successful, failed, skipped, output_dirs_used,
                         output_dir_fallback, log_filename=None,
                         success_label="Successfully processed", count_label="images"):
    """
    Shared summary printer for Pad/Crop/Resize/Crop+Resize/Convert/Rotate+Flip/Strip.
    `successful` may be a list (its length is shown) or, for Strip's N-parts-
    per-image case, an int count already computed by the caller.
    """
    print()
    print(f"\033[93m{title}\033[0m")
    print("-------------")
    count = len(successful) if isinstance(successful, list) else successful
    label_suffix = f" {count_label}" if count_label else ""
    print(f"✅ \033[93m{success_label}:\033[0m {count}{label_suffix}")
    if skipped:
        print(f"⏭️  \033[93mSkipped (already exists):\033[0m {len(skipped)}")
    if failed:
        log_suffix = f" (see {log_filename} in output folder)" if log_filename else ""
        print(f"❌ \033[93mFailed:\033[0m {len(failed)}{log_suffix}")
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


def run_pad(images, is_folder_mode, first_folder):
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
        pad_percent = djj.get_float_input(
            "Pad percentage per side [default: 10]", min_val=0.0001, default=10.0
        )
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

    padding_position = 'center'
    if shape in ('landscape', 'portrait', 'custom'):
        pos_choice = djj.prompt_choice(
            "\033[93mImage position:\033[0m\n1. Center\n2. Left\n3. Right\n",
            ['1', '2', '3'],
            default='1'
        )
        padding_position = {'1': 'center', '2': 'left', '3': 'right'}[pos_choice]
        print()

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

    output_dir = djj.get_output_directory(images, is_folder_mode=is_folder_mode, first_folder=first_folder)

    print("-------------")
    successful, failed, skipped, output_dirs_used = pad_images(
        images, output_dir,
        shape, pad_percent,
        color, custom_width, custom_height, custom_color,
        padding_position, bg_type, bg_mode, bg_blur, bg_opacity
    )

    print_batch_summary("Padding Summary", successful, failed, skipped, output_dirs_used, output_dir,
                         log_filename="image_processor_pad_log.txt")

    return output_dir


def run_crop(images, is_folder_mode, first_folder):
    edges = get_crop_edges()
    print()
    trim_px = get_crop_amount()
    print()

    print("-------------")
    successful, failed, skipped, output_dirs_used = crop_images(images, edges, trim_px)

    output_dir = djj.get_output_directory(images, is_folder_mode=is_folder_mode, first_folder=first_folder, subfolder_name="Cropped")
    print_batch_summary(
        "Cropping Summary", successful, failed, skipped, output_dirs_used,
        output_dir
    )

    return output_dir


def run_crop_and_resize(images, is_folder_mode, first_folder):
    edges = get_crop_edges()
    trim_px = get_crop_amount()
    print()
    dimension_type, desired_width, desired_height, manual_mode = get_resize_target()

    print("-------------")
    successful, failed, skipped, output_dirs_used = crop_and_resize_images(
        images, edges, trim_px, dimension_type, desired_width, desired_height, manual_mode
    )

    output_dir = djj.get_output_directory(images, is_folder_mode=is_folder_mode, first_folder=first_folder, subfolder_name="Cropped_Resized")
    print_batch_summary(
        "Crop + Resize Summary", successful, failed, skipped, output_dirs_used,
        output_dir
    )

    return output_dir


def run_resize_only(images, is_folder_mode, first_folder):
    dimension_type, desired_width, desired_height, manual_mode = get_resize_target()

    print("-------------")
    successful, failed, skipped, output_dirs_used = resize_only_images(
        images, dimension_type, desired_width, desired_height, manual_mode
    )

    output_dir = djj.get_output_directory(images, is_folder_mode=is_folder_mode, first_folder=first_folder, subfolder_name="Resized")
    print_batch_summary(
        "Resize Summary", successful, failed, skipped, output_dirs_used,
        output_dir
    )

    return output_dir


# ─── Rotate / Flip ────────────────────────────────────────────────────────────

def rotate_flip_batch(images, base_path, operation, choice, custom_angle, output_format):
    """
    Batch loop: applies djj.rotate_or_flip_image per image, mirrors each
    image's subfolder structure (relative to base_path) under
    base_path/Output/RotatedFlipped/, and saves.
    """
    output_dir = os.path.join(str(pathlib.Path(base_path).resolve()), "Output", "RotatedFlipped")
    os.makedirs(output_dir, exist_ok=True)
    logger = djj.setup_logging(output_dir, script_name="image_processor_rotate_flip")

    print()
    print(f"{len(images)} \033[93mimages found\033[0m")
    print()
    print("\033[93mProcessing images...\033[0m")

    successful = []
    failed = []
    pillow_format, file_extension = OUTPUT_FORMAT_MAP[output_format.lower()]

    for i, img_path in enumerate(images, 1):
        img_path = pathlib.Path(img_path)
        try:
            with Image.open(img_path) as img:
                img = djj.rotate_or_flip_image(img, operation, choice, custom_angle)

                if pillow_format == 'JPEG' and img.mode == 'RGBA':
                    img = img.convert('RGB')

                relative_path = os.path.relpath(img_path.parent, base_path)
                output_dir_path = os.path.join(output_dir, relative_path) if relative_path != '.' else output_dir
                os.makedirs(output_dir_path, exist_ok=True)
                output_filename = f"{os.path.splitext(img_path.name)[0]}_rf{file_extension}"
                output_path = os.path.join(output_dir_path, output_filename)

                img.save(output_path, format=pillow_format, quality=95 if pillow_format == 'JPEG' else None)
                successful.append(img_path.name)
                sys.stdout.write(f"\rProcessing {i}/{len(images)} images ({i/len(images)*100:.1f}%)...")
                sys.stdout.flush()
        except Exception as e:
            failed.append((img_path.name, str(e)))
            logger.error(f"Failed to process {img_path.name}: {e}")
            sys.stdout.write(f"\rProcessing {i}/{len(images)} images ({i/len(images)*100:.1f}%)... (failed)")
            sys.stdout.flush()

    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()

    return successful, failed, output_dir


def run_rotate_flip(images, base_path):
    operation = djj.prompt_choice(
        "\033[93mOperation:\033[0m\n1. Flip\n2. Rotate\n",
        ['1', '2'],
        default='1'
    )
    operation = 'flip' if operation == '1' else 'rotate'
    print()

    choice = None
    custom_angle = None
    if operation == 'flip':
        flip_choice = djj.prompt_choice(
            "\033[93mFlip direction:\033[0m\n1. Horizontal ↔️\n2. Vertical ↕️\n",
            ['1', '2'],
            default='1'
        )
        choice = 'horizontal' if flip_choice == '1' else 'vertical'
        print()
    else:
        rotate_choice = djj.prompt_choice(
            "\033[93mRotation:\033[0m\n1. 90°\n2. 180°\n3. 270°\n4. Custom\n",
            ['1', '2', '3', '4'],
            default='1'
        )
        print()
        if rotate_choice in ('1', '2', '3'):
            choice = {'1': '90', '2': '180', '3': '270'}[rotate_choice]
        else:
            choice = 'custom'
            custom_angle = djj.get_float_input("Enter custom angle (degrees, positive = counterclockwise)")
            print()

    output_format = djj.prompt_choice(
        "\033[93mOutput format:\033[0m\n1. PNG\n2. JPG\n3. BMP\n4. GIF\n",
        ['1', '2', '3', '4'],
        default='1'
    )
    output_format = {'1': 'png', '2': 'jpg', '3': 'bmp', '4': 'gif'}[output_format]
    print()

    print("-------------")
    successful, failed, output_dir = rotate_flip_batch(images, base_path, operation, choice, custom_angle, output_format)

    print_batch_summary(
        "Rotate/Flip Summary", successful, failed, [], [output_dir], output_dir,
        log_filename="image_processor_rotate_flip_log.txt"
    )

    return output_dir


# ─── Convert Format ───────────────────────────────────────────────────────────

def convert_images(images, output_dir, output_format, keep_metadata, quality=95):
    """
    Convert images to the specified format.
    Output: each image's parent/Output/Converted/
    """
    os.makedirs(output_dir, exist_ok=True)
    logger = djj.setup_logging(output_dir, script_name="image_processor_convert")

    pillow_format, file_ext = OUTPUT_FORMAT_MAP[output_format]

    def transform(img, img_path):
        if pillow_format == 'JPEG':
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
        elif pillow_format in ('PNG', 'WEBP'):
            if img.mode not in ('RGB', 'RGBA', 'L', 'LA'):
                img = img.convert('RGBA')
        return img

    def save_kwargs_fn(_pillow_format, image):
        save_kwargs = {}
        if keep_metadata and _pillow_format in ('JPEG', 'PNG', 'WEBP'):
            exif = image.info.get('exif')
            if exif:
                save_kwargs['exif'] = exif
        if _pillow_format in ('JPEG', 'WEBP'):
            save_kwargs['quality'] = quality
        return image, save_kwargs

    return _run_batch(
        images, "Converted", "c", "\033[93mConverting images...\033[0m",
        transform, save_format_fn=lambda p: (pillow_format, file_ext),
        save_kwargs_fn=save_kwargs_fn, logger=logger, error_verb="convert"
    )


def run_convert(images, is_folder_mode, first_folder):
    format_choice = djj.prompt_choice(
        "\033[93mOutput format:\033[0m\n"
        "1. PNG\n"
        "2. JPG\n"
        "3. WebP\n"
        "4. BMP\n"
        "5. GIF\n",
        ['1', '2', '3', '4', '5'],
        default='1'
    )
    print()

    format_map = {'1': 'png', '2': 'jpg', '3': 'webp', '4': 'bmp', '5': 'gif'}
    output_format = format_map[format_choice]

    quality = 95
    if output_format in ('jpg', 'webp'):
        quality_input = input("\033[93mQuality [1-100, default: 95]:\033[0m\n -> ").strip()
        try:
            if quality_input:
                quality = int(quality_input)
                quality = max(1, min(100, quality))
        except ValueError:
            quality = 95
        print()

    keep_metadata = djj.prompt_choice(
        "\033[93mKeep metadata?\033[0m\n1. Yes\n2. No\n",
        ['1', '2'],
        default='2'
    ) == '1'
    print()

    output_dir = djj.get_output_directory(images, is_folder_mode=is_folder_mode, first_folder=first_folder, subfolder_name="Converted")

    print("-------------")
    successful, failed, skipped, output_dirs_used = convert_images(
        images, output_dir, output_format, keep_metadata, quality
    )

    print_batch_summary("Convert Summary", successful, failed, skipped, output_dirs_used, output_dir,
                         log_filename="image_processor_convert_log.txt")

    return output_dir


# ─── Strip Padding / Split Collage ────────────────────────────────────────────

# Commonly used solid padding colors to prioritize (RGB)
KNOWN_BG_COLORS = [
    (255, 255, 255),  # white
    (0, 0, 0),        # black
    (136, 136, 136),  # gray
    (0, 255, 0),      # chroma green
    (0, 0, 255),      # chroma blue
]

def detect_border_color(im, tolerance=5):
    corners = [
        im.getpixel((0, 0)),
        im.getpixel((im.width - 1, 0)),
        im.getpixel((0, im.height - 1)),
        im.getpixel((im.width - 1, im.height - 1)),
    ]
    # Count all corner occurrences
    color_counts = {}
    for c in corners:
        color_counts[c] = color_counts.get(c, 0) + 1

    # Prefer known padding colors if present
    for color in KNOWN_BG_COLORS:
        if color in color_counts:
            return color

    # Fall back to most common corner color
    return max(color_counts, key=color_counts.get)


def trim_multiple_regions(im, tolerance=15, min_width=20, min_height=20):
    im = im.convert("RGB")
    bg_color = detect_border_color(im, tolerance)
    bg = Image.new("RGB", im.size, bg_color)
    diff = ImageChops.difference(im, bg)
    diff = Image.eval(diff, lambda x: 255 if x > tolerance else 0)

    diff_np = np.array(diff)
    mask = diff_np.sum(axis=2) > 0

    labeled, num_features = label(mask)
    slices = find_objects(labeled)

    cropped_images = []
    for s in slices:
        w, h = s[1].stop - s[1].start, s[0].stop - s[0].start
        if w >= min_width and h >= min_height:
            cropped = im.crop((s[1].start, s[0].start, s[1].stop, s[0].stop))
            cropped_images.append(cropped)

    return cropped_images


def strip_images(images, output_dir):
    """
    Split each image into its detected sub-regions (strips padding / splits
    a collage back into its parts). 1-image-in -> N-images-out, so `successful`
    counts parts produced, not images processed.
    Output: each image's parent/Output/Stripped/
    """
    os.makedirs(output_dir, exist_ok=True)
    logger = djj.setup_logging(output_dir, script_name="image_processor_strip")

    print()
    print(f"{len(images)} \033[93mimages found\033[0m")
    print()
    print("\033[93mStripping padding / splitting collage...\033[0m")

    successful = 0
    failed = []
    output_dirs_used = set()

    for i, img_path in enumerate(images, 1):
        img_path_obj = pathlib.Path(img_path)
        try:
            with Image.open(img_path) as img:
                cropped_images = trim_multiple_regions(img)

                img_output_dir = img_path_obj.parent / "Output" / "Stripped"
                img_output_dir.mkdir(parents=True, exist_ok=True)
                output_dirs_used.add(str(img_output_dir))

                for idx, cropped in enumerate(cropped_images, 1):
                    output_filename = f"{img_path_obj.stem}_part{idx}.png"
                    out_path = img_output_dir / output_filename
                    cropped.save(out_path)
                    successful += 1

            sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)...")
            sys.stdout.flush()

        except Exception as e:
            failed.append((img_path_obj.name, str(e)))
            logger.error(f"Failed to process {img_path_obj.name}: {e}")
            sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)... ❌")
            sys.stdout.flush()

    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

    return successful, failed, sorted(output_dirs_used)


def run_strip(images, is_folder_mode, first_folder):
    print("\033[93mSuggested Background Colors for Collages:\033[0m")
    print(" • \033[97mWhite\033[0m \033[94m(255,255,255);(#FFFFFF)\033[0m")
    print(" • \033[30mBlack\033[0m \033[94m(0,0,0);(#000000)\033[0m")
    print(" • \033[90mGray\033[0m \033[94m(136,136,136);(#888888)\033[0m")
    print(" • \033[92mChroma Green\033[0m \033[94m(0,255,0);(#00FF00)\033[0m")
    print(" • \033[96mChroma Blue\033[0m \033[94m(0,0,255);(#0000FF)\033[0m")
    print("\033[93mThese are auto-detected.\n\033[0m")

    output_dir = djj.get_output_directory(images, is_folder_mode=is_folder_mode, first_folder=first_folder, subfolder_name="Stripped")

    print("-------------")
    successful, failed, output_dirs_used = strip_images(images, output_dir)

    print_batch_summary(
        "Strip Padding Summary", successful, failed, [], output_dirs_used, output_dir,
        log_filename="image_processor_strip_log.txt",
        success_label="Parts produced", count_label=""
    )

    return output_dir


# ─── Image Pairing / Joining / Collage ───────────────────────────────────────

def prepare_image_with_background(img_path, canvas_width, canvas_height, bg_opacity=0.8, bg_blur=8):
    """
    Prepare an image with blurred background to fit canvas dimensions.
    No try/except here — caller (process_image_group) logs failures with
    its own logger, since pure-ish helpers shouldn't reach into logging state.
    """
    img = Image.open(img_path)
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    canvas = djj.create_blurred_background(img, canvas_width, canvas_height, 'stretched', bg_blur, bg_opacity)
    resized, paste_x, paste_y = djj.fit_image_to_canvas(img, canvas_width, canvas_height)
    canvas.paste(resized, (paste_x, paste_y), resized)
    return canvas


def process_image_group(image_group, output_path, durations, transition_duration, base_output_name, logger):
    """Process a group of images into a dissolve slideshow video."""
    try:
        canvas_width, canvas_height = djj.get_max_dimensions(image_group)
    except Exception as e:
        logger.error(f"Error getting image dimensions for group starting with {image_group[0]}: {e}")
        return None

    temp_dir = os.path.join(output_path, "temp_pairing")
    os.makedirs(temp_dir, exist_ok=True)

    processed_images = []
    for i, img_path in enumerate(image_group):
        try:
            canvas = prepare_image_with_background(img_path, canvas_width, canvas_height)
        except Exception as e:
            logger.error(f"Error preparing image {img_path}: {e}")
            return None
        temp_path = os.path.join(temp_dir, f"prep_{i:04d}.png")
        canvas.convert('RGB').save(temp_path, 'PNG')
        processed_images.append(temp_path)

    cmd = ["ffmpeg", "-y"]
    for i, (img_path, duration) in enumerate(zip(processed_images, durations)):
        cmd.extend(["-loop", "1", "-t", str(duration), "-i", img_path])

    filter_parts = []
    overlay_chain = []

    for i in range(len(processed_images)):
        scale_filter = (
            f"[{i}:v]scale={canvas_width}:{canvas_height}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={canvas_width}:{canvas_height}:(ow-iw)/2:(oh-ih)/2,"
            f"format=yuva420p"
        )
        if i == 0:
            fade_filter = (
                f"{scale_filter},"
                f"fade=t=out:st={durations[i]-transition_duration}:d={transition_duration}:"
                f"alpha=1,setpts=PTS-STARTPTS[va{i}]"
            )
        else:
            offset_time = sum(durations[:i]) - i * transition_duration
            fade_filter = (
                f"{scale_filter},"
                f"fade=t=in:st=0:d={transition_duration}:alpha=1,"
                f"setpts=PTS-STARTPTS+{offset_time}/TB[va{i}]"
            )
        filter_parts.append(fade_filter)
        overlay_chain.append(f"va{i}")

    if len(processed_images) == 1:
        final_output = overlay_chain[0]
    else:
        current_base = overlay_chain[0]
        for i in range(1, len(overlay_chain)):
            overlay_filter = f"[{current_base}][{overlay_chain[i]}]overlay[ov{i}]"
            filter_parts.append(overlay_filter)
            current_base = f"ov{i}"
        final_output = current_base

    total_duration = sum(durations) - (len(durations) - 1) * transition_duration
    filter_parts.append(f"[{final_output}]trim=duration={total_duration}")
    filter_complex = ";".join(filter_parts)

    output_file = os.path.join(output_path, f"{base_output_name}_paired.mp4")

    cmd.extend([
        "-filter_complex", filter_complex,
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "veryfast",
        "-r", "30",
        "-t", str(total_duration),
        "-fps_mode", "cfr",
        output_file
    ])

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for temp_file in processed_images:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
        return output_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Error creating video: {e.stderr}")
        return None


def process_join_only_groups(groups, join_position, join_audio, logger):
    """
    Join only mode: takes group[0] from each group, finds a matching video,
    and runs join_image_video(). Gracefully skips if no video found.

    Returns:
        (success_count, skip_count, error_count, joined_folders)
    """
    success_count = 0
    skip_count = 0
    error_count = 0
    total_groups = len(groups)
    joined_folders = set()

    for idx, group in enumerate(groups, 1):
        sys.stdout.write(
            f"\r\033[93mJoining \033[0m{idx}/{total_groups} "
            f"\033[93mgroups\033[0m ({idx/total_groups*100:.1f}%)..."
        )
        sys.stdout.flush()

        first_img = pathlib.Path(group[0])
        parent_folder = str(first_img.parent)
        filename_noext = first_img.stem

        video_path = djj.find_video_for_image(str(first_img), parent_folder)
        if not video_path:
            skip_count += 1
            logger.warning(f"No matching video for {first_img.name} — skipped")
            continue

        joined_dir = os.path.join(parent_folder, "Output", "Joined")
        os.makedirs(joined_dir, exist_ok=True)
        joined_folders.add(joined_dir)

        pos_sfx = djj.position_suffix(join_position)
        joined_output = os.path.join(joined_dir, f"{filename_noext}_joined{pos_sfx}.mp4")
        join_ok = djj.join_image_video(
            image_path=str(first_img),
            video_path=video_path,
            output_path=joined_output,
            position=join_position,
            audio_choice=join_audio
        )
        if join_ok:
            success_count += 1
        else:
            error_count += 1
            logger.error(f"Join failed for {first_img.name}")

    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()

    return success_count, skip_count, error_count, list(joined_folders)


def process_all_groups(groups, durations, transition_duration, logger,
                       use_parent_output=False,
                       do_join=False, join_position='1', join_audio='1',
                       do_comp_join=False, comp_join_position='1', comp_join_audio='1',
                       collage_paths_by_stem=None):
    """
    Process all image groups into paired videos, optionally joining:
      - group[0] image + paired video → Output/Joined/
      - collaged image + paired video → Output/Comp_Joined/

    Returns:
        (success_count, error_count, paired_folders, joined_folders, comp_joined_folders)
    """
    success_count = 0
    error_count = 0
    total_groups = len(groups)
    paired_folders = set()
    joined_folders = set()
    comp_joined_folders = set()

    for idx, group in enumerate(groups, 1):
        sys.stdout.write(
            f"\r\033[93mProcessing \033[0m{idx}/{total_groups} "
            f"\033[93mgroups\033[0m ({idx/total_groups*100:.1f}%)..."
        )
        sys.stdout.flush()

        if not all(djj.is_valid_image_file(img) for img in group):
            error_count += 1
            continue

        first_img = pathlib.Path(group[0])
        parent_folder = str(first_img.parent)
        filename_noext = first_img.stem

        paired_dir = os.path.join(parent_folder, "Output", "Paired")
        os.makedirs(paired_dir, exist_ok=True)
        paired_folders.add(paired_dir)

        # Slice durations to this group's actual size — groups can be smaller
        # than len(durations) (auto-match groups vary in size), and
        # process_image_group's own trim/-t math assumes len(durations)
        # matches the group exactly.
        output_file = process_image_group(group, paired_dir, durations[:len(group)], transition_duration, filename_noext, logger)

        if output_file:
            success_count += 1

            # Standard join: group[0] image + paired video
            if do_join:
                joined_dir = os.path.join(parent_folder, "Output", "Joined")
                os.makedirs(joined_dir, exist_ok=True)
                joined_folders.add(joined_dir)
                joined_output = os.path.join(joined_dir, f"{filename_noext}_joined{djj.position_suffix(join_position)}.mp4")
                join_ok = djj.join_image_video(
                    image_path=group[0],
                    video_path=output_file,
                    output_path=joined_output,
                    position=join_position,
                    audio_choice=join_audio
                )
                if not join_ok:
                    logger.error(f"Join failed for group starting with {group[0]}")

            # Comp join: collaged image + paired video
            if do_comp_join and collage_paths_by_stem:
                collage_img = collage_paths_by_stem.get(filename_noext)
                if collage_img and os.path.exists(collage_img):
                    comp_joined_dir = os.path.join(parent_folder, "Output", "Comp_Joined")
                    os.makedirs(comp_joined_dir, exist_ok=True)
                    comp_joined_folders.add(comp_joined_dir)
                    comp_joined_output = os.path.join(comp_joined_dir, f"{filename_noext}_comp_joined{djj.position_suffix(comp_join_position)}.mp4")
                    cj_ok = djj.join_image_video(
                        image_path=collage_img,
                        video_path=output_file,
                        output_path=comp_joined_output,
                        position=comp_join_position,
                        audio_choice=comp_join_audio
                    )
                    if not cj_ok:
                        logger.error(f"Comp join failed for group starting with {group[0]}")
        else:
            error_count += 1

    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()

    return success_count, error_count, list(paired_folders), list(joined_folders), list(comp_joined_folders)


def _ask_grouping_params(top_mode=None):
    """
    Ask grouping mode + group size / match type + num chars.
    Shared by run_pairing's main flow and its Mode 3 re-collage loop.

    Random grouping (mode '3': shuffle the pool, then chunk sequentially —
    same chunking as Sequential, just on a shuffled list) is only offered
    when top_mode == '3' (Collage only). Every other mode also pairs/joins
    each group with a matching video, where group composition isn't just
    cosmetic, so random grouping doesn't apply there.
    """
    allow_random = (top_mode == '3')

    prompt = (
        "\033[93mGrouping mode:\033[0m\n"
        "1. Sequential (by position)\n"
        "2. Auto-match (by prefix/suffix)\n"
    )
    choices = ['1', '2']
    if allow_random:
        prompt += "3. Random (shuffled)\n"
        choices.append('3')

    pairing_mode = djj.prompt_choice(prompt, choices, default='1')
    print()

    group_size = None
    match_type = None
    num_chars = None

    if pairing_mode in ('1', '3'):
        group_size = djj.get_int_input("Images per group [default: 3]", min_val=1, default=3)
        print()
    else:
        match_type_choice = djj.prompt_choice(
            "\033[93mMatch by:\033[0m\n1. Prefix\n2. Suffix\n",
            ['1', '2'],
            default='1'
        )
        match_type = 'prefix' if match_type_choice == '1' else 'suffix'
        print()
        num_chars = djj.get_int_input(f"Number of characters for {match_type} match [default: 4]", min_val=1, default=4)
        print()

    return pairing_mode, group_size, match_type, num_chars


def _build_groups_maybe_random(images, pairing_mode, group_size, match_type, num_chars):
    """
    Like djj.build_groups_for_images, but treats mode '3' as Random:
    shuffle a copy of the pool, then chunk it sequentially (mode '1'
    behavior) instead of taking the images in their existing order.
    """
    if pairing_mode == '3':
        shuffled = list(images)
        random.shuffle(shuffled)
        return djj.build_groups_for_images(shuffled, '1', group_size, match_type, num_chars)
    return djj.build_groups_for_images(images, pairing_mode, group_size, match_type, num_chars)


def _ask_collage_direction_and_edge(edge_calc_image_path, dimension_error_label="first image"):
    """
    Ask collage direction + longest-edge size.
    Shared by run_pairing's main flow and its Mode 3 re-collage loop.
    edge_calc_image_path is probed for the "2x shorter edge" option.
    """
    direction_choice = djj.prompt_choice(
        "\033[93mCollage direction:\033[0m\n"
        "1. Horizontal (default)\n"
        "2. Vertical\n",
        ['1', '2'],
        default='1'
    )
    direction = 'H' if direction_choice == '1' else 'V'
    print()

    edge_choice = djj.prompt_choice(
        "\033[93mLongest edge size:\033[0m\n"
        "1. 1920px (default)\n"
        "2. Custom\n"
        "3. 2× shorter edge of first image\n",
        ['1', '2', '3'],
        default='1'
    )
    print()

    if edge_choice == '1':
        longest_edge = 1920
    elif edge_choice == '2':
        longest_edge = djj.get_int_input(
            "\033[93mEnter longest edge in pixels:\033[0m",
            min_val=100, max_val=9999
        ) or 1920
    else:
        try:
            with Image.open(edge_calc_image_path) as probe_img:
                shorter = min(probe_img.width, probe_img.height)
            longest_edge = shorter * 2
            print(f"\033[93mUsing {longest_edge}px (2× {shorter}px shorter edge)\033[0m")
        except Exception:
            longest_edge = 1920
            print(f"\033[93m⚠️  Could not read {dimension_error_label} dimensions, defaulting to 1920px\033[0m")
    print()

    return direction, longest_edge


def _create_main_collage(folder_path, groups, collage_direction, collage_longest_edge, all_collage_folders):
    """Create the main collage for a folder's groups. Shared by run_pairing modes 3/4/5."""
    comp_dir = os.path.join(folder_path, "Output", "Comp")
    collage_out = djj.create_collage_from_groups(groups, collage_direction, collage_longest_edge, comp_dir)
    all_collage_folders.append(comp_dir)
    return collage_out, comp_dir


def _build_comp_join_collage_paths(groups, collage_out, do_comp_join, same_collage_params,
                                    comp_collage_direction, comp_collage_longest_edge):
    """
    Build {stem: collage_path} for Comp_Joined routing. If comp join uses
    different params, generates an alternate collage into a temp dir (caller
    must clean up the returned temp_comp_dir). Shared by run_pairing modes 4/5.
    """
    temp_comp_dir = None
    if do_comp_join and not same_collage_params:
        temp_comp_dir = tempfile.mkdtemp(prefix="djjtb_comp_join_")
        alt_collage_out = djj.create_collage_from_groups(
            groups, comp_collage_direction, comp_collage_longest_edge, temp_comp_dir
        )
        collage_paths_by_stem = {}
        for grp, cpath in zip(groups, alt_collage_out):
            stem = pathlib.Path(grp[0]).stem
            collage_paths_by_stem[stem] = cpath
    else:
        collage_paths_by_stem = {}
        for grp, cpath in zip(groups, collage_out):
            stem = pathlib.Path(grp[0]).stem
            collage_paths_by_stem[stem] = cpath
    return collage_paths_by_stem, temp_comp_dir


def run_pairing(images, input_mode, input_path, include_subfolders):
    # ── Top-level mode ───────────────────────────────────────────────────
    top_mode = djj.prompt_choice(
        "\033[93mMode:\033[0m\n"
        "1. Pairing only\n"
        "2. Joining only\n"
        "3. Collage only\n"
        "4. Collage + Pair\n"
        "5. Collage + Join only\n",
        ['1', '2', '3', '4', '5'],
        default='4'
    )
    print()

    # ── Grouping mode ────────────────────────────────────────────────────
    # Auto-match mode: group size comes from however many images actually
    # share a match key — no fixed count to ask for.
    pairing_mode, group_size, match_type, num_chars = _ask_grouping_params(top_mode)

    # ── Collage params (modes 3, 4, 5) ────────────────────────────────────
    collage_direction = None
    collage_longest_edge = None
    do_comp_join = False
    comp_join_position = '1'
    comp_join_audio = '1'
    same_collage_params = True
    comp_collage_direction = None
    comp_collage_longest_edge = None

    if top_mode in ('3', '4', '5'):
        collage_direction, collage_longest_edge = _ask_collage_direction_and_edge(images[0])

        # Comp join prompt (modes 4, 5) — ask before pairing params
        if top_mode in ('4', '5'):
            do_comp_join = djj.prompt_choice(
                "\033[93mAlso join collaged image with paired video?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'],
                default='1'
            ) == '1'
            print()

            if do_comp_join:
                opposite_dir = 'V' if collage_direction == 'H' else 'H'
                opposite_label = 'Vertical' if collage_direction == 'H' else 'Horizontal'
                use_opposite = djj.prompt_choice(
                    f"\033[93mUse opposite direction ({opposite_label}) for Comp Join collage?\033[0m\n1. Yes\n2. No (same as main)\n",
                    ['1', '2'],
                    default='1'
                ) == '1'
                print()

                comp_collage_direction = opposite_dir if use_opposite else collage_direction
                comp_collage_longest_edge = collage_longest_edge
                same_collage_params = not use_opposite

                print("\033[93m🖼️  Comp Join — Image Position:\033[0m")
                print("1. Left   (video on right)")
                print("2. Right  (video on left)")
                print("3. Top    (video on bottom)")
                print("4. Bottom (video on top)")
                comp_join_position = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3', '4'], default='1')
                print()

                print("\033[93m🔊 Comp Join — Audio:\033[0m")
                print("1. Keep video's audio")
                print("2. Strip audio")
                print("3. Add silent audio track")
                comp_join_audio = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3'], default='2')
                print()

    # ── Build groups up front ──────────────────────────────────────────────
    # Needed before the duration prompt (modes 1/4): auto-match groups vary
    # in size, so there's no single fixed count to ask "duration per image"
    # against until grouping has actually happened. Sequential mode's groups
    # are already fixed-size, but building them here too keeps one code path.
    process_by_folder = (include_subfolders and input_mode == '1') or (input_mode in ['2', '3'])

    if process_by_folder:
        folder_image_map = djj.group_images_by_parent_folder(images)
    else:
        folder_image_map = {input_path: images}

    folder_groups = {}
    max_group_size = 0
    for folder_path, folder_images in folder_image_map.items():
        groups = _build_groups_maybe_random(folder_images, pairing_mode, group_size, match_type, num_chars)
        folder_groups[folder_path] = groups
        for g in groups:
            max_group_size = max(max_group_size, len(g))
    max_group_size = max(max_group_size, 1)

    # ── Pairing params (modes 1 and 4) ────────────────────────────────────
    durations = []
    transition_duration = 1.0

    if top_mode in ('1', '4'):
        for i in range(max_group_size):
            duration = djj.get_float_input(
                f"Duration for image {i+1} (seconds) [default: 5]", min_val=0.0001, default=5.0
            )
            durations.append(duration)
            print()

        transition_duration = djj.get_float_input(
            "Transition duration (seconds) [default: 2]", min_val=0, default=2.0
        )
        print()

        total_duration = sum(durations) - (len(durations) - 1) * transition_duration
        print(f"\033[93mTotal video duration (for a {max_group_size}-image group):\033[0m {total_duration:.1f}s")
        print()

    # ── Join params (modes 1 and 4) ───────────────────────────────────────
    do_join = False
    join_position = '1'
    join_audio = '1'

    if top_mode in ('1', '4'):
        do_join = djj.prompt_choice(
            "\033[93mJoin first image with paired video?\033[0m\n1. Yes\n2. No\n",
            ['1', '2'],
            default='1'
        ) == '1'
        print()

        if do_join:
            print("\033[93m🖼️  Image Position:\033[0m")
            print("1. Left   (video on right)")
            print("2. Right  (video on left)")
            print("3. Top    (video on bottom)")
            print("4. Bottom (video on top)")
            join_position = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3', '4'], default='1')
            print()

            print("\033[93m🔊 Audio:\033[0m")
            print("1. Keep video's audio")
            print("2. Strip audio")
            print("3. Add silent audio track")
            join_audio = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3'], default='2')
            print()

    # ── Join Only params (modes 2 and 5) ───────────────────────────────────
    join_only_position = '1'
    join_only_audio = '1'

    if top_mode in ('2', '5'):
        print("\033[93m🖼️  Image Position:\033[0m")
        print("1. Left   (video on right)")
        print("2. Right  (video on left)")
        print("3. Top    (video on bottom)")
        print("4. Bottom (video on top)")
        join_only_position = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3', '4'], default='1')
        print()

        print("\033[93m🔊 Audio:\033[0m")
        print("1. Keep video's audio")
        print("2. Strip audio")
        print("3. Add silent audio track")
        join_only_audio = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3'], default='1')
        print()

    # ── Setup logging ─────────────────────────────────────────────────────
    log_output = os.path.join(input_path, "Output", "Paired")
    os.makedirs(log_output, exist_ok=True)
    logger = djj.setup_logging(log_output, script_name="image_processor_pairing")

    print(f"\033[93mProcessing {len(folder_image_map)} folder(s)...\033[0m")
    print()

    # ── Tracking totals ───────────────────────────────────────────────────
    total_success = 0
    total_error = 0
    total_skip = 0
    all_paired_folders = []
    all_joined_folders = []
    all_comp_joined_folders = []
    all_collage_folders = []
    _last_collage_out = []   # Mode 3: holds latest collage outputs for re-collage
    _collage_gen = 1         # Mode 3: suffix generation counter (1=_comp, 2=_comp2…)

    # ── Process each folder ───────────────────────────────────────────────
    for folder_path, folder_images in folder_image_map.items():

        groups = folder_groups[folder_path]

        if not groups:
            print(f"\033[93m⚠️  No complete groups in {folder_path}, skipping.\033[0m")
            continue

        grouped_count = sum(len(g) for g in groups)
        if grouped_count < len(folder_images):
            leftover = len(folder_images) - grouped_count
            print(f"\033[93m⚠️  {leftover} image(s) left over (incomplete group) — skipped\033[0m")

        # ── Mode 1: Pairing only ──────────────────────────────────────────
        if top_mode == '1':
            s, e, pf, jf, cjf = process_all_groups(
                groups, durations, transition_duration, logger,
                use_parent_output=True,
                do_join=do_join, join_position=join_position, join_audio=join_audio
            )
            total_success += s
            total_error += e
            all_paired_folders.extend(pf)
            all_joined_folders.extend(jf)

        # ── Mode 2: Joining only ──────────────────────────────────────────
        elif top_mode == '2':
            s, sk, e, jf = process_join_only_groups(groups, join_only_position, join_only_audio, logger)
            total_success += s
            total_skip += sk
            total_error += e
            all_joined_folders.extend(jf)

        # ── Mode 3: Collage only ──────────────────────────────────────────
        elif top_mode == '3':
            collage_out, comp_dir = _create_main_collage(
                folder_path, groups, collage_direction, collage_longest_edge, all_collage_folders
            )
            total_success += len(collage_out)
            _last_collage_out = list(collage_out)
            _collage_gen = 1

        # ── Mode 4: Collage + Pair ────────────────────────────────────────
        elif top_mode == '4':
            collage_out, comp_dir = _create_main_collage(
                folder_path, groups, collage_direction, collage_longest_edge, all_collage_folders
            )
            collage_paths_by_stem, temp_comp_dir = _build_comp_join_collage_paths(
                groups, collage_out, do_comp_join, same_collage_params,
                comp_collage_direction, comp_collage_longest_edge
            )

            s, e, pf, jf, cjf = process_all_groups(
                groups, durations, transition_duration, logger,
                use_parent_output=True,
                do_join=do_join, join_position=join_position, join_audio=join_audio,
                do_comp_join=do_comp_join, comp_join_position=comp_join_position,
                comp_join_audio=comp_join_audio,
                collage_paths_by_stem=collage_paths_by_stem
            )

            if temp_comp_dir and os.path.exists(temp_comp_dir):
                shutil.rmtree(temp_comp_dir, ignore_errors=True)
            total_success += s
            total_error += e
            all_paired_folders.extend(pf)
            all_joined_folders.extend(jf)
            all_comp_joined_folders.extend(cjf)

        # ── Mode 5: Collage + Join only ───────────────────────────────────
        elif top_mode == '5':
            collage_out, comp_dir = _create_main_collage(
                folder_path, groups, collage_direction, collage_longest_edge, all_collage_folders
            )
            collage_paths_by_stem, temp_comp_dir = _build_comp_join_collage_paths(
                groups, collage_out, do_comp_join, same_collage_params,
                comp_collage_direction, comp_collage_longest_edge
            )

            pos_sfx = djj.position_suffix(join_only_position)
            cj_success = 0
            cj_skip = 0
            cj_error = 0
            for grp, cpath in zip(groups, collage_out):
                stem = pathlib.Path(grp[0]).stem
                collage_img = collage_paths_by_stem.get(stem, cpath)
                first_img = pathlib.Path(grp[0])
                parent_folder = str(first_img.parent)

                video_path = djj.find_video_for_image(str(first_img), parent_folder)
                if not video_path:
                    cj_skip += 1
                    logger.warning(f"No matching video for {first_img.name} — skipped")
                    continue

                comp_joined_dir = os.path.join(parent_folder, "Output", "Comp_Joined")
                os.makedirs(comp_joined_dir, exist_ok=True)
                all_comp_joined_folders.append(comp_joined_dir)

                out_path = os.path.join(comp_joined_dir, f"{stem}_comp_joined{pos_sfx}.mp4")
                ok = djj.join_image_video(
                    image_path=collage_img,
                    video_path=video_path,
                    output_path=out_path,
                    position=join_only_position,
                    audio_choice=join_only_audio
                )
                if ok:
                    cj_success += 1
                else:
                    cj_error += 1
                    logger.error(f"Comp join failed for {first_img.name}")

            if temp_comp_dir and os.path.exists(temp_comp_dir):
                shutil.rmtree(temp_comp_dir, ignore_errors=True)

            total_success += cj_success
            total_skip += cj_skip
            total_error += cj_error

    # ── Mode 3: Re-collage loop ───────────────────────────────────────────
    # After Collage Only, offer to re-collage the outputs.
    while top_mode == '3' and _last_collage_out:
        recap = djj.prompt_choice(
            "\033[93mRe-collage these results?\033[0m\n1. Yes\n2. No\n",
            ['1', '2'],
            default='2'
        )
        print()
        if recap != '1':
            break

        rc_pairing_mode, rc_group_size, rc_match_type, rc_num_chars = _ask_grouping_params(top_mode)

        rc_direction, rc_longest_edge = _ask_collage_direction_and_edge(
            _last_collage_out[0], dimension_error_label="image"
        )

        # Each round gets its own Comp/ subfolder nested one level deeper.
        # Suffix is always _comp — the folder depth is the generation indicator.
        # create_collage_from_groups strips any trailing _comp/_compN from
        # the stem so names never chain regardless of how many rounds deep
        # you go.
        _collage_gen += 1
        next_suffix = '_comp'
        recap_dir = os.path.join(all_collage_folders[-1], 'Comp')
        os.makedirs(recap_dir, exist_ok=True)
        all_collage_folders.append(recap_dir)

        rc_groups = _build_groups_maybe_random(
            _last_collage_out, rc_pairing_mode, rc_group_size,
            rc_match_type, rc_num_chars
        )
        if not rc_groups:
            rc_groups = [_last_collage_out]

        new_collage_out = djj.create_collage_from_groups(
            rc_groups, rc_direction, rc_longest_edge,
            recap_dir, suffix=next_suffix
        )
        if new_collage_out:
            total_success += len(new_collage_out)
            _last_collage_out = list(new_collage_out)
            print(f"\033[92m✅ {len(new_collage_out)} re-collage(s) created → {next_suffix}\033[0m")
        else:
            print("\033[93m⚠️  Re-collage produced no output.\033[0m")
            break

    # ── Summary ───────────────────────────────────────────────────────────
    print()
    print("\033[93mSummary\033[0m")
    print("-------")

    if top_mode in ('2', '5'):
        print(f"✅ \033[93mJoined:\033[0m {total_success}")
        if total_skip:
            print(f"\033[93m⚠️  Skipped (no video found):\033[0m {total_skip}")
        if total_error:
            print(f"❌ \033[93mFailed:\033[0m {total_error}")
    elif top_mode == '3':
        print(f"✅ \033[93mCollages created:\033[0m {total_success}")
    else:
        print(f"✅ \033[93mGroups processed:\033[0m {total_success}")
        if total_error:
            print(f"❌ \033[93mFailed:\033[0m {total_error} (see image_processor_pairing_log.txt)")

    def print_folders(label, folders):
        if not folders:
            return
        unique = sorted(set(folders))
        print(f"\n\033[93m{label}:\033[0m")
        for f in unique[:3]:
            print(f"  - {f}")
        if len(unique) > 3:
            print(f"  ... and {len(unique) - 3} more")

    print_folders("📁 Collage output", all_collage_folders)
    print_folders("📁 Paired output", all_paired_folders)
    print_folders("🔗 Joined output", all_joined_folders)
    print_folders("🔗 Comp Joined output", all_comp_joined_folders)
    print()

    open_folder = (
        all_comp_joined_folders[0] if all_comp_joined_folders else
        all_joined_folders[0] if all_joined_folders else
        all_collage_folders[0] if all_collage_folders else
        all_paired_folders[0] if all_paired_folders else
        None
    )
    if open_folder:
        djj.prompt_open_folder(open_folder)


def main():
    while True:
        os.system('clear')
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mImage Processor\033[0m")
        print("Pad / Crop / Resize / Rotate / Flip / Pair / Join / Collage / Convert / Strip")
        print("\033[92m==================================================\033[0m")
        print()

        # ── Input mode ────────────────────────────────────────────────────────
        input_mode = djj.prompt_choice(
            "Input mode:\n"
            "1. Folder path\n"
            "2. Space-separated file paths\n"
            "3. Path list from txt file\n",
            ['1', '2', '3'],
            default='1'
        )
        print()

        images = []
        input_path = None
        include_subfolders = False

        if input_mode == '1':
            input_path = djj.get_path_input("Enter folder path")
            print()
            include_subfolders = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            images = djj.collect_images_from_folder(input_path, include_subfolders)
            if not include_subfolders:
                images = djj.apply_skip_list(images, root=input_path)

        elif input_mode == '2':
            print("📁 \033[93mEnter image paths (space-separated, drag-and-drop ok):\033[0m")
            raw = input(" -> ").strip()
            if not raw:
                print("❌ No file paths provided.")
                continue
            images = djj.collect_images_from_paths(raw)
            if images:
                input_path = str(pathlib.Path(images[0]).parent)
            print()

        else:
            paths = djj.get_paths_from_txt("Enter txt file path")
            images = djj.collect_images_from_path_list(paths) if paths else []
            if images:
                input_path = str(pathlib.Path(images[0]).parent)
            print()

        if not images:
            print("❌ \033[93mNo valid image files found.\033[0m")
            continue

        is_folder_mode = (input_mode == '1')

        # ── Operation (chains onto its own output if you want to keep going) ───
        while True:
            print(f"✅ \033[93m{len(images)} image(s) found\033[0m")
            print()

            operation = djj.prompt_choice(
                "\033[93mOperation:\033[0m\n"
                "1. Pad images\n"
                "2. Crop edges (trim by pixel amount)\n"
                "3. Crop edges + Resize (trim, then resize to target)\n"
                "4. Resize only (no crop)\n"
                "5. Rotate / Flip\n"
                "6. Image Pairing / Joining / Collage...\n"
                "7. Convert format\n"
                "8. Strip padding / split collage\n",
                ['1', '2', '3', '4', '5', '6', '7', '8'],
                default='1'
            )
            print()

            output_dir = None
            if operation == '1':
                output_dir = run_pad(images, is_folder_mode, input_path)
            elif operation == '2':
                output_dir = run_crop(images, is_folder_mode, input_path)
            elif operation == '3':
                output_dir = run_crop_and_resize(images, is_folder_mode, input_path)
            elif operation == '4':
                output_dir = run_resize_only(images, is_folder_mode, input_path)
            elif operation == '5':
                output_dir = run_rotate_flip(images, input_path)
            elif operation == '6':
                run_pairing(images, input_mode, input_path, include_subfolders)
            elif operation == '7':
                output_dir = run_convert(images, is_folder_mode, input_path)
            else:
                output_dir = run_strip(images, is_folder_mode, input_path)

            # Pairing (6) can produce more than one output folder depending on
            # mode, so it's not offered as a chain source here.
            chained_images = (
                djj.collect_images_from_folder(output_dir, False)
                if output_dir and os.path.isdir(output_dir) else []
            )
            if not chained_images:
                break

            chain_choice = djj.prompt_choice(
                f"\033[93mRun another operation on these {len(chained_images)} output image(s)?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'],
                default='2'
            )
            print()
            if chain_choice != '1':
                break

            images = chained_images
            input_path = output_dir
            is_folder_mode = True

        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()
