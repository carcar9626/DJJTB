import os
import sys
import json
import glob
import random
import pathlib
import logging
import subprocess
import djjtb.utils as djj
from PIL import Image, ImageFilter
os.system('clear')
def setup_logging(output_path, prefix):
    log_file = os.path.join(output_path, f"{prefix.lower()}_log.txt")
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(prompt)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger()
    
def return_to_djjtb():
    """Switch back to DJJTB tab (Command+1)"""
    subprocess.run([
        "osascript", "-e",
        'tell application "Terminal" to tell application "System Events" to keystroke "1" using command down'
    ])

def load_images(folder_path, output_path):
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
    landscape, square, portrait = [], [], []

    folder_path = str(pathlib.Path(folder_path).resolve())
    output_path = str(pathlib.Path(output_path).resolve())

    for root, _, files in os.walk(folder_path):
        root_resolved = str(pathlib.Path(root).resolve())
        if root_resolved.startswith(output_path):
            continue
        for f in files:
            if f.lower().endswith(image_extensions) and not f.startswith('collage_'):
                img_path = os.path.join(root, f)
                rel_path = os.path.relpath(img_path, folder_path)
                try:
                    with Image.open(img_path) as img:
                        width, height = img.size
                        aspect_ratio = width / height
                        if aspect_ratio > 1.2:
                            landscape.append(rel_path)
                        elif aspect_ratio < 0.8:
                            portrait.append(rel_path)
                        else:
                            square.append(rel_path)
                except Exception as e:
                    logging.error(f"Error reading {rel_path}: {e}")

    return landscape, square, portrait

def load_used_images(used_file):
    if os.path.exists(used_file):
        try:
            with open(used_file, 'r') as f:
                return set(json.load(f))
        except json.JSONDecodeError:
            return set()
    return set()

def save_used_images(used_images, used_file):
    try:
        with open(used_file, 'w') as f:
            json.dump(list(used_images), f)
    except Exception as e:
        logging.error(f"Error saving {used_file}: {e}")

def get_next_collage_number(output_path):
    existing_files = glob.glob(os.path.join(output_path, '*_CLG_*.jpg'))
    numbers = [int(os.path.basename(f).split('_CLG_')[1].split('.')[0]) for f in existing_files]
    return max(numbers) + 1 if numbers else 1


def create_collage(folder_path, output_path, num_collages, orientation, include_subfolders, log_used_images=False, fixed_grid=None, fixed_num_images=None, background_opacity=0.25, background_blur_radius=8):
    os.makedirs(output_path, exist_ok=True)
    subfolder = 'Landscape' if orientation else 'Portrait'
    logger = setup_logging(output_path, f"Collages_{subfolder}")
    used_file = os.path.join(output_path, f'used_images_{subfolder.lower()}.json')
    
    if log_used_images and not os.path.exists(used_file):
        with open(used_file, 'w') as f:
            json.dump([], f)

    landscape, square, portrait = load_images(folder_path, output_path)
    used_images = load_used_images(used_file) if log_used_images else set()

    available_landscape = [img for img in landscape if img not in used_images]
    available_square = [img for img in square if img not in used_images]
    available_portrait = [img for img in portrait if img not in used_images]

    # Log available images for debugging
    logger.info(f"Available images - Landscape: {len(available_landscape)}, Square: {len(available_square)}, Portrait: {len(available_portrait)}")

    # Explicitly map orientation: True (landscape) = 1920x1080, False (portrait) = 1080x1920
    # Explicitly map orientation: True (landscape) = 1920x1080, False (portrait) = 1080x1920
    if orientation:  # True means landscape (from djj.prompt_choice "1")
        category_configs = [
            ('landscape', available_landscape, (2, 2), 4),
            ('square', available_square, (2, 3), 6),
            ('portrait', available_portrait, (1, 3), 3)
        ]
        canvas_width, canvas_height = 1920, 1080
        logger.info("Creating landscape collage (1920x1080)")
    else:  # False means portrait (from djj.prompt_choice "2")
        category_configs = [
            ('landscape', available_landscape, (3, 1), 3),
            ('square', available_square, (3, 2), 6),
            ('portrait', available_portrait, (2, 2), 4)
        ]
        canvas_width, canvas_height = 1080, 1920
        logger.info("Creating portrait collage (1080x1920)")

    categories = [(n, imgs, g, num) for n, imgs, g, num in category_configs if len(imgs) >= num]
    if not categories:
        logger.error("\033[33mNo unused images available for selected orientation.\033[0m")
        print("\033[33mNo unused images available for selected orientation.\033[0m", file=sys.stderr)
        return

    collages_created = 0
    total_images_used = 0
    collage_start_num = get_next_collage_number(output_path)
    parent_folder = os.path.basename(os.path.normpath(folder_path))

    for i in range(num_collages):
        collage_used_images = set()
        category_name, available_images, default_grid, default_num_images = random.choice(categories)
        grid = fixed_grid or default_grid
        num_images = fixed_num_images or default_num_images

        available_for_collage = [img for img in available_images if img not in collage_used_images]
        if len(available_for_collage) < num_images:
            logger.warning(f"Not enough images for collage {i+1} in category {category_name}")
            continue

        selected_images = random.sample(available_for_collage, num_images)
        canvas = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
        rows, cols = grid
        cell_width = canvas_width // cols
        cell_height = canvas_height // rows
        positions = [(r, c) for r in range(rows) for c in range(cols)]
        random.shuffle(positions)

        for idx, (row, col) in enumerate(positions):
            if idx >= len(selected_images):
                break
            img_name = selected_images[idx]
            img_path = os.path.join(folder_path, img_name)
            try:
                img = Image.open(img_path).convert('RGBA')

                bg_img = img.copy().resize((cell_width, cell_height), Image.Resampling.LANCZOS)
                bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=background_blur_radius))
                alpha = Image.new('L', bg_img.size, int(255 * background_opacity))
                bg_img.putalpha(alpha)
                canvas.paste(bg_img, (col * cell_width, row * cell_height), bg_img)

                img_ratio = img.width / img.height
                target_w = cell_width
                target_h = int(target_w / img_ratio)
                if target_h > cell_height:
                    target_h = cell_height
                    target_w = int(target_h * img_ratio)
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                paste_x = col * cell_width + (cell_width - target_w) // 2
                paste_y = row * cell_height + (cell_height - target_h) // 2
                canvas.paste(img, (paste_x, paste_y), img)

                collage_used_images.add(img_name)
                used_images.add(img_name)
                total_images_used += 1

                if category_name == 'landscape':
                    available_landscape.remove(img_name)
                elif category_name == 'square':
                    available_square.remove(img_name)
                elif category_name == 'portrait':
                    available_portrait.remove(img_name)

            except Exception as e:
                logger.error(f"Error processing {img_name}: {e}")
                continue

        output_file = os.path.join(output_path, f'{parent_folder}_CLG_{collage_start_num + i:03d}.jpg')
        canvas.convert('RGB').save(output_file, 'JPEG', quality=95)
        collages_created += 1

        if log_used_images:
            save_used_images(used_images, used_file)

        progress = int(((i + 1) / num_collages) * 100)
        sys.stdout.write(f"\r\033[33mCreating Collages\033[0m {i + 1}\033[33m/\033[0m{num_collages} ({progress}%)...")
        sys.stdout.flush()

        categories = [(n, imgs, g, nimg) for n, imgs, g, nimg in category_configs if len(imgs) >= (fixed_num_images or nimg)]
        if not categories:
            break

    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()
    logger.info(f"Collages created: {collages_created}, Images used: {total_images_used}")
    print()
    print("\033[33m\nCollage Summary\033[0m")
    print("---------------")
    print(f"\033[33mCollages created:\033[0m {collages_created}")
    print(f"\033[33mImages used: \033[0m{total_images_used}")
    print(f"\033[33mOutput folder:\033[0m {output_path}")
    if log_used_images:
        print(f"Used images tracked in: {used_file}")
    print()

    try:
        subprocess.run(['open', output_path], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"\033[33mError opening output folder:\033[0m {e}")

def main():
    while True:
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mCollage Creator\033[0m")
        print("Auto create collages from folder")
        print("\033[92m==================================================\033[0m")
        print()
        folder = input("\033[33mEnter path: \033[0m\n -> ").strip()
        print ()
        if not folder or not os.path.exists(folder):
            print("\033[33mInvalid path.\033[0m")
            continue

        include_sub = djj.prompt_choice("\033[33mInclude subfolders?\033[0m \n1. Yes, 2. No", ['1', '2'], default='2') == '1'

        log_used = djj.prompt_choice("\033[33mLog images?\033[0m\n1. Yes, 2. No ", ['1', '2'], default='1') == '1'
        print()
        orient = djj.prompt_choice("\033[33mCollage Orientation\033[0m \n1. Landscape, 2. Portrait ", ['1', '2'], default='1') == '1'
        print()
        num_collages = int(djj.prompt_choice("\033[33mNumber of collages?\033[0m\n Enter a number", None, default='10'))

        subfolder = 'Landscape' if orient else 'Portrait'
        output = os.path.join(folder, "Output", "Collages", subfolder)
        create_collage(folder, output, num_collages, orient, include_sub, log_used_images=log_used)

        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == '__main__':
    main()