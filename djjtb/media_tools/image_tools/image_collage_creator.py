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
    """Set up logging to a file in the output folder."""
    log_file = os.path.join(output_path, f"{prefix.lower()}_log.txt")
    logger = djj.setup_logging(output_path, f"collage_{prefix.lower()}")
    return logger

def load_images(folder_path, output_path):
    """Load and categorize images by aspect ratio, excluding output folder."""
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
    landscape, square, portrait = [], [], []

    folder_path = str(pathlib.Path(folder_path).resolve())
    # Get the base Output folder path (not just the specific subfolder)
    base_output_path = str(pathlib.Path(folder_path, "Output").resolve())

    for root, _, files in os.walk(folder_path):
        root_resolved = str(pathlib.Path(root).resolve())
        # Skip any folder that starts with the Output path
        if root_resolved.startswith(base_output_path):
            continue
        for f in files:
            if f.lower().endswith(image_extensions) and not f.startswith('collage_') and not f.startswith('CLG_'):
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
    """Load list of used images from a JSON file."""
    if os.path.exists(used_file):
        try:
            with open(used_file, 'r') as f:
                return set(json.load(f))
        except json.JSONDecodeError:
            return set()
    return set()

def save_used_images(used_images, used_file):
    """Save list of used images to a JSON file."""
    try:
        with open(used_file, 'w') as f:
            json.dump(list(used_images), f)
    except Exception as e:
        logging.error(f"Error saving {used_file}: {e}")

def get_next_collage_number(output_path):
    """Find the next collage number to avoid overwriting."""
    existing_files = glob.glob(os.path.join(output_path, '*_CLG_*.jpg'))
    numbers = [int(os.path.basename(f).split('_CLG_')[1].split('.')[0]) for f in existing_files]
    return max(numbers) + 1 if numbers else 1

def collect_images_from_folder(input_path, include_subfolders=False):
    """Collect images from folder(s)."""
    input_path_obj = pathlib.Path(input_path)
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
    
    images = []
    if input_path_obj.is_dir():
        if include_subfolders:
            for root, _, files in os.walk(input_path):
                images.extend(pathlib.Path(root) / f for f in files if pathlib.Path(f).suffix.lower() in image_extensions)
        else:
            images = [f for f in input_path_obj.glob('*') if f.suffix.lower() in image_extensions and f.is_file()]
    
    return sorted([str(v) for v in images], key=str.lower)

def collect_images_from_paths(file_paths):
    """Collect images from space-separated file paths."""
    images = []
    paths = file_paths.strip().split()
    
    for path in paths:
        path = path.strip('\'"')
        path_obj = pathlib.Path(path)
        
        if path_obj.is_file() and path_obj.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'):
            images.append(str(path_obj))
        elif path_obj.is_dir():
            images.extend(collect_images_from_folder(str(path_obj), include_subfolders=False))
    
    return sorted(images, key=str.lower)

def create_collage(folder_path, output_path, num_collages, orientation, include_subfolders, log_used_images=False, fixed_grid=None, fixed_num_images=None, background_opacity=0.25, background_blur_radius=8):
    """Create tiled collages with category-specific grids and individual backgrounds."""
    os.makedirs(output_path, exist_ok=True)
    
    # Define orientation configurations
    orientation_configs = {
        'horizontal': {
            'name': 'Horizontal',
            'canvas': (1920, 1080),
            'categories': [
                ('landscape', (2, 2), 4),
                ('square', (2, 3), 6),
                ('portrait', (1, 3), 3)
            ]
        },
        'vertical': {
            'name': 'Vertical',
            'canvas': (1080, 1920),
            'categories': [
                ('landscape', (3, 1), 3),
                ('square', (3, 2), 6),
                ('portrait', (2, 2), 4)
            ]
        },
        'square': {
            'name': 'Square',
            'canvas': (1080, 1080),
            'categories': [
                ('landscape', (2, 1), 2),  # if source is landscape then 1x2
                ('square', (2, 2), 4),     # if source is square then 2x2
                ('portrait', (1, 2), 2)    # if source is portrait then 2x1
            ]
        },
        '1280x1080': {
            'name': '1280x1080',
            'canvas': (1280, 1080),
            'categories': [
                ('landscape', (2, 1), 2),  # if source is landscape then 1x3
                ('square', (2, 2), 4),     # if source is square then 1x2
                ('portrait', (1, 2), 2)    # if source is portrait then 2x2
            ]
        },
        '900x1920': {
            'name': '900x1920',
            'canvas': (900, 1920),
            'categories': [
                ('landscape', (3, 1), 3),  # following portrait layout pattern
                ('square', (3, 2), 6),     # following portrait layout pattern
                ('portrait', (2, 2), 4)    # following portrait layout pattern
            ]
        }
    }
    
    config = orientation_configs[orientation]
    subfolder = config['name']
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

    logger.info(f"Available images - Landscape: {len(available_landscape)}, Square: {len(available_square)}, Portrait: {len(available_portrait)}")

    canvas_width, canvas_height = config['canvas']
    
    # Build category configs based on orientation
    category_configs = []
    for category_name, default_grid, default_num_images in config['categories']:
        if category_name == 'landscape':
            category_configs.append(('landscape', available_landscape, default_grid, default_num_images))
        elif category_name == 'square':
            category_configs.append(('square', available_square, default_grid, default_num_images))
        elif category_name == 'portrait':
            category_configs.append(('portrait', available_portrait, default_grid, default_num_images))

    logger.info(f"Creating {subfolder} collage ({canvas_width}x{canvas_height})")

    categories = [(n, imgs, g, num) for n, imgs, g, num in category_configs if len(imgs) >= num]
    if not categories:
        logger.error("No unused images available for selected orientation.")
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
        
        # Debug info
        logger.info(f"Collage {i+1}: Using {category_name} category with {rows}x{cols} grid")

        for idx, (row, col) in enumerate(positions):
            if idx >= len(selected_images):
                break
            img_name = selected_images[idx]
            img_path = os.path.join(folder_path, img_name)
            try:
                img = Image.open(img_path).convert('RGBA')

                # Create individual blurred background for this cell
                bg_img = img.copy().resize((cell_width, cell_height), Image.Resampling.LANCZOS)
                bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=background_blur_radius))
                alpha = Image.new('L', bg_img.size, int(255 * background_opacity))
                bg_img.putalpha(alpha)
                canvas.paste(bg_img, (col * cell_width, row * cell_height), bg_img)

                # Scale and center the foreground image (preserve aspect ratio)
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

                # Remove from appropriate category list
                if category_name == 'landscape' and img_name in available_landscape:
                    available_landscape.remove(img_name)
                elif category_name == 'square' and img_name in available_square:
                    available_square.remove(img_name)
                elif category_name == 'portrait' and img_name in available_portrait:
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

        # Update categories
        category_configs_updated = []
        for category_name, default_grid, default_num_images in config['categories']:
            if category_name == 'landscape':
                category_configs_updated.append(('landscape', available_landscape, default_grid, default_num_images))
            elif category_name == 'square':
                category_configs_updated.append(('square', available_square, default_grid, default_num_images))
            elif category_name == 'portrait':
                category_configs_updated.append(('portrait', available_portrait, default_grid, default_num_images))
        
        categories = [(n, imgs, g, nimg) for n, imgs, g, nimg in category_configs_updated if len(imgs) >= (fixed_num_images or nimg)]
        if not categories:
            break

    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()
    logger.info(f"Collages created: {collages_created}, Images used: {total_images_used}")
    print()
    print("\033[33mCollage Summary\033[0m")
    print("---------------")
    print(f"\033[33mCollages created:\033[0m {collages_created}")
    print(f"\033[33mImages used:\033[0m {total_images_used}")
    print(f"\033[33mOutput folder:\033[0m {output_path}")
    if log_used_images:
        print(f"{total_images_used}\033[33m used images tracked in:\033[0m {used_file}")
    print()

    djj.prompt_open_folder(output_path)

def main():
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mCollage Creator\033[0m")
        print("Auto create collages from folder")
        print("\033[92m==================================================\033[0m")
        print()

        # Input mode selection (like video_reverse_merge reference)
        input_mode = djj.prompt_choice(
            "\033[33mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
            ['1', '2'],
            default='1'
        )
        print()

        images = []
        folder_path = None

        if input_mode == '1':
            # Folder mode
            folder_path = djj.get_path_input("Enter folder path")
            print()
            
            include_sub = djj.prompt_choice(
                "\033[33mInclude subfolders?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            
            images = collect_images_from_folder(folder_path, include_sub)
            
        else:
            # File paths mode
            file_paths = input("📁 \033[33mEnter image paths (space-separated):\n\033[0m -> ").strip()
            
            if not file_paths:
                print("❌ \033[33mNo file paths provided.\033[0m")
                continue
            
            images = collect_images_from_paths(file_paths)
            # Set folder_path to parent of first image for output folder logic
            if images:
                folder_path = str(pathlib.Path(images[0]).parent)
            print()

        if not images:
            print("❌ \033[33mNo valid image files found. Try again.\033[0m\n")
            continue

        print("Scanning for images...")
        print(f"✅ \033[33m{len(images)} images found\033[0m")
        print()

        # Rest of the options
        log_used = djj.prompt_choice(
            "\033[33mLog used images?\033[0m\n1. Yes\n2. No\n",
            ['1', '2'],
            default='1'
        ) == '1'
        print()

        # Updated orientation choices with new 900x1920 option
        orientation_choice = djj.prompt_choice(
            "\033[33mCollage format:\033[0m\n1. Horizontal (1920x1080)\n2. Vertical (1080x1920)\n3. Square (1080x1080)\n4. 1280x1080\n5. 900x1920\n",
            ['1', '2', '3', '4', '5'],
            default='1'
        )
        print()

        # Background opacity setting
        bg_opacity_input = input("\033[33mBackground opacity [0.0-1.0, default: 0.25]:\n\033[0m -> ").strip()
        try:
            bg_opacity = float(bg_opacity_input) if bg_opacity_input else 0.25
            bg_opacity = max(0.0, min(1.0, bg_opacity))  # Clamp between 0 and 1
        except ValueError:
            bg_opacity = 0.25
            print("\033[33mUsing default opacity: 0.25\033[0m")
        print()

        # Background blur setting
        bg_blur_input = input("\033[33mBackground blur radius [1-50, default: 8]:\n\033[0m -> ").strip()
        try:
            bg_blur = int(bg_blur_input) if bg_blur_input else 8
            bg_blur = max(1, min(50, bg_blur))  # Clamp between 1 and 50
        except ValueError:
            bg_blur = 8
            print("\033[33mUsing default blur: 8\033[0m")
        print()

        # Map choices to orientation keys
        orientation_map = {
            '1': 'horizontal',
            '2': 'vertical',
            '3': 'square',
            '4': '1280x1080',
            '5': '900x1920'
        }
        orientation = orientation_map[orientation_choice]

        # Fixed: Get number of collages properly
        while True:
            try:
                num_collages_input = input("\033[33mNumber of collages [default: 10]:\n\033[0m -> ").strip()
                if not num_collages_input:
                    num_collages = 10
                    break
                num_collages = int(num_collages_input)
                if num_collages > 0:
                    break
                else:
                    print("\033[33mPlease enter a positive number.\033[0m")
            except ValueError:
                print("\033[33mPlease enter a valid number.\033[0m")
        
        print("\n" * 2)
        print("\033[1;33mProcessing...\033[0m")

        # Create output path based on orientation
        orientation_names = {
            'horizontal': 'Horizontal',
            'vertical': 'Vertical',
            'square': 'Square',
            '1280x1080': '1280x1080',
            '900x1920': '900x1920'
        }
        subfolder = orientation_names[orientation]
        output = os.path.join(folder_path, "Output", "Collages", subfolder)
        
        create_collage(folder_path, output, num_collages, orientation, input_mode == '1',
                       log_used_images=log_used, background_opacity=bg_opacity,
                       background_blur_radius=bg_blur)
                       

        
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == '__main__':
    main()  