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
    """Collect images from folder(s) using the reference logic."""
    input_path_obj = pathlib.Path(input_path)
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff')
    
    images = []
    if input_path_obj.is_dir():
        if subfolders:
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
        path = clean_path(path)
        path_obj = pathlib.Path(path)
        
        if path_obj.is_file() and is_valid_image(path_obj.name):
            images.append(str(path_obj))
        elif path_obj.is_dir():
            print(f"⚠️ Skipping directory in file list: {path}")
    
    return sorted(images, key=str.lower)

def get_output_directory(images, is_folder_mode=True, first_folder=None):
    """Determine output directory based on input mode."""
    if is_folder_mode and first_folder:
        return os.path.join(first_folder, "Output", "Padded")
    elif images:
        # Use parent directory of first image
        first_image_dir = os.path.dirname(images[0])
        return os.path.join(first_image_dir, "Output", "Padded")
    else:
        return os.path.join(os.getcwd(), "Output", "Padded")

def calculate_padding_offset(img_width, img_height, new_width, new_height, position):
    """Calculate the offset for padding based on position."""
    if position == 'center':  # Center (default)
        offset_x = (new_width - img_width) // 2
        offset_y = (new_height - img_height) // 2
    elif position == 'left':  # Image on left, padding on right
        offset_x = 0
        offset_y = (new_height - img_height) // 2
    elif position == 'right':  # Image on right, padding on left
        offset_x = new_width - img_width
        offset_y = (new_height - img_height) // 2
    else:  # Default to center
        offset_x = (new_width - img_width) // 2
        offset_y = (new_height - img_height) // 2
    
    return (offset_x, offset_y)

def create_image_background(img, new_width, new_height, bg_mode, blur_radius, opacity):
    """Create an image-based background with blur and opacity."""
    if bg_mode == 'stretched':
        # Stretch the image to fill the canvas
        bg_img = img.copy().resize((new_width, new_height), Image.Resampling.LANCZOS)
    elif bg_mode == 'tiled':
        # Tile the image to fill the canvas
        bg_img = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
        img_width, img_height = img.size
        for y in range(0, new_height, img_height):
            for x in range(0, new_width, img_width):
                bg_img.paste(img, (x, y))
    elif bg_mode == 'centered':
        # Center the image in the canvas
        bg_img = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
        img_width, img_height = img.size
        offset_x = (new_width - img_width) // 2
        offset_y = (new_height - img_height) // 2
        bg_img.paste(img, (offset_x, offset_y))
    else:
        # Default to stretched
        bg_img = img.copy().resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Apply blur
    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    
    # Apply opacity
    alpha = Image.new('L', bg_img.size, int(255 * opacity))
    bg_img.putalpha(alpha)
    
    return bg_img

def pad_images(images, output_dir, output_format, shape, color, custom_width, custom_height, custom_color, padding_position, bg_type, bg_mode, bg_blur, bg_opacity):
    """Pad images to the specified shape and color with positioning."""
    os.makedirs(output_dir, exist_ok=True)
    logger = setup_logging(output_dir)
    
    print()
    print(f"{len(images)} \033[93mimages found\033[0m")
    print()
    print("\033[93mPadding Images...\033[0m")
    
    successful = []
    failed = []
    format_map = {'png': ('PNG', '.png'), 'jpg': ('JPEG', '.jpg'), 'bmp': ('BMP', '.bmp'), 'gif': ('GIF', '.gif')}
    pillow_format, file_extension = format_map[output_format.lower()]
    
    color_map = {'white': (255, 255, 255, 255), 'black': (0, 0, 0, 255), 'grey': (128, 128, 128, 255)}
    padding_color = custom_color if color == 'custom' else color_map[color]
    
    for i, img_path in enumerate(images, 1):
        try:
            with Image.open(img_path) as img:
                img = img.convert('RGBA')
                width, height = img.size
                
                if shape == 'square':
                    target_size = max(width, height)
                    new_width = new_height = target_size
                elif shape == 'landscape':
                    new_width = int(height * 16 / 9)
                    new_height = height
                elif shape == 'portrait':
                    new_width = int(height * 9 / 16)
                    new_height = height
                else:
                    new_width = custom_width
                    new_height = custom_height
                
                # Create the background
                if bg_type == 'image':
                    new_image = create_image_background(img, new_width, new_height, bg_mode, bg_blur, bg_opacity)
                else:
                    # Solid color background
                    new_image = Image.new('RGBA', (new_width, new_height), padding_color)
                
                # Calculate position and paste the original image
                offset = calculate_padding_offset(width, height, new_width, new_height, padding_position)
                new_image.paste(img, offset, img)
                
                if pillow_format == 'JPEG':
                    new_image = new_image.convert('RGB')
                
                # Keep original directory structure for folder mode
                img_path_obj = pathlib.Path(img_path)
                output_filename = f"{img_path_obj.stem}_padded{file_extension}"
                output_path = os.path.join(output_dir, output_filename)
                
                new_image.save(output_path, format=pillow_format, quality=95 if pillow_format == 'JPEG' else None)
                successful.append(img_path_obj.name)
                sys.stdout.write(f"\rProcessing {i}/{len(images)} images ({i/len(images)*100:.1f}%)...")
                sys.stdout.flush()
        except Exception as e:
            failed.append((pathlib.Path(img_path).name, str(e)))
            logger.error(f"Failed to process {img_path}: {e}")
            sys.stdout.write(f"\rProcessing {i}/{len(images)} images ({i/len(images)*100:.1f}%)... (failed)")
            sys.stdout.flush()
    
    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()
    
    return successful, failed

def main():
    while True:
        clear_screen()
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mImage Padder\033[0m")
        print("Adds Padding to Images")
        print("\033[92m==================================================\033[0m")
        print()
        
        # Get input mode
        input_mode = djj.prompt_choice(
            "Input mode:\n1. Folder path\n2. Space-separated file paths\n",
            ['1', '2'],
            default='1'
        )
        print()
        
        images = []
        output_dir = None
        
        if input_mode == '1':
            # Folder mode
            src_dir = input("📁 \033[93mEnter folder path: \n -> \033[0m").strip()
            src_dir = clean_path(src_dir)
            
            if not os.path.isdir(src_dir):
                print(f"❌ \033[93mThe path\033[0m '{src_dir}' \033[93mis not a valid directory\033[0m.")
                continue
            
            print()
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders? \033[0m\n1. Yes, 2. No ",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            
            images = collect_images_from_folder(src_dir, include_sub)
            output_dir = get_output_directory(images, is_folder_mode=True, first_folder=src_dir)
            
        else:
            # File paths mode
            file_paths = input("📁 \033[93mEnter file paths: \n -> \033[0m").strip()
            
            if not file_paths:
                print("❌ No file paths provided.")
                continue
            
            images = collect_images_from_paths(file_paths)
            output_dir = get_output_directory(images, is_folder_mode=False)
            print()
        
        if not images:
            print("❌ \033[93mNo valid image files found.\033[0m")
            continue
        
        print("\033[93mScanning for Images...\033[0m")
        
        # Get padding position
        padding_position = djj.prompt_choice(
            "\033[93mPadding position:\033[0m\n1. Left (image on left, padding on right)\n2. Right (image on right, padding on left)\n3. Center\n",
            ['1', '2', '3'],
            default='3'
        )
        print()
        
        # Convert choice to position string
        position_map = {'1': 'left', '2': 'right', '3': 'center'}
        padding_position = position_map[padding_position]

        # Get shape
        shape = djj.prompt_choice(
            "\033[93mShape:\033[0m\n1. Square\n2. Landscape\n3. Portrait\n4. Custom\n",
            ['1', '2', '3', '4'],
            default='1'
        )
        print()
        
        shape_map = {'1': 'square', '2': 'landscape', '3': 'portrait', '4': 'custom'}
        shape = shape_map[shape]

        custom_width = None
        custom_height = None
        if shape == 'custom':
            custom_width = djj.get_int_input("\033[93mCustom width in pixels\033[0m", min_val=1)
            print()
            custom_height = djj.get_int_input("\033[93mCustom height in pixels\033[0m", min_val=1)
            print()

        # Get background type
        bg_type = djj.prompt_choice(
            "\033[93mBackground type:\033[0m\n1. Solid color\n2. Image background\n",
            ['1', '2'],
            default='1'
        )
        print()
        
        bg_type = 'solid' if bg_type == '1' else 'image'
        bg_mode = None
        bg_blur = 8
        bg_opacity = 0.25
        
        if bg_type == 'image':
            # Get background mode
            bg_mode = djj.prompt_choice(
                "\033[93mImage background mode:\033[0m\n1. Stretched\n2. Tiled\n3. Centered\n",
                ['1', '2', '3'],
                default='1'
            )
            print()
            
            mode_map = {'1': 'stretched', '2': 'tiled', '3': 'centered'}
            bg_mode = mode_map[bg_mode]
            
            # Get background blur
            bg_blur_input = input("\033[93mBackground blur radius [1-50, default: 8]:\n -> \033[0m").strip()
            try:
                bg_blur = int(bg_blur_input) if bg_blur_input else 8
                bg_blur = max(1, min(50, bg_blur))
            except ValueError:
                bg_blur = 8
                print("\033[93mUsing default blur: 8\033[0m")
            print()
            
            # Get background opacity
            bg_opacity_input = input("\033[93mBackground opacity [0.0-1.0, default: 0.25]:\n -> \033[0m").strip()
            try:
                bg_opacity = float(bg_opacity_input) if bg_opacity_input else 0.25
                bg_opacity = max(0.0, min(1.0, bg_opacity))
            except ValueError:
                bg_opacity = 0.25
                print("\033[93mUsing default opacity: 0.25\033[0m")
            print()

        # Get color (only for solid background type)
        custom_color = None
        if bg_type == 'solid':
            color = djj.prompt_choice(
                "\033[93mPadding color:\033[0m\n1. White\n2. Black\n3. Grey\n4. Custom\n",
                ['1', '2', '3', '4'],
                default='1'
            )
            print()
            
            color_map = {'1': 'white', '2': 'black', '3': 'grey', '4': 'custom'}
            color = color_map[color]

            if color == 'custom':
                max_attempts = 5
                attempt = 0
                while attempt < max_attempts:
                    try:
                        color_input = input("\033[93mCustom color (R,G,B,A - e.g., 255,255,255,255): \n -> \033[0m").strip()
                        r, g, b, a = map(int, color_input.split(','))
                        if all(0 <= x <= 255 for x in [r, g, b, a]):
                            custom_color = (r, g, b, a)
                            break
                        print("\033[93mEach value must be between \033[0m0 \033[93mand\033[0m 255.")
                    except ValueError:
                        print("\033[93mPlease enter four integers separated by commas \033[0m(e.g., 255,255,255,255).")
                    attempt += 1
                    if attempt == max_attempts:
                        print("\033[93mToo many invalid attempts. Exiting.\033[0m")
                        sys.exit(1)
                print()
        else:
            # For image backgrounds, color settings are not needed
            color = 'white'

        # Get output format
        output_format = djj.prompt_choice(
            "\033[93mOutput format:\033[0m\n1. PNG\n2. JPG\n3. BMP\n4. GIF\n",
            ['1', '2', '3', '4'],
            default='1'
        )
        print()
        
        format_map = {'1': 'png', '2': 'jpg', '3': 'bmp', '4': 'gif'}
        output_format = format_map[output_format]

        print("-------------")
        successful, failed = pad_images(images, output_dir, output_format, shape, color, custom_width, custom_height, custom_color, padding_position, bg_type, bg_mode, bg_blur, bg_opacity)
        
        print("\n" * 1)
        print("\033[93mPadding Summary\033[0m")
        print("-------------")
        print(f"✅ \033[93mSuccessfully padded: \033[0m{len(successful)}\033[93m images\033[0m")
        if failed:
            print(f"❌ \033[93mFailed operations:\033[0m {len(failed)}\033[93m (see padding_errors.log in output folder)\033[0m")
        print(f"📁\033[93m Output folder:\033[0m \n{output_dir}")
        print("\n" * 2)

        djj.prompt_open_folder(output_dir)

        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()