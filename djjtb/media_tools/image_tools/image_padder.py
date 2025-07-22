import os
import subprocess
import sys
import time
from PIL import Image
import pathlib
import logging
import djjtb.utils as djj

def clear_screen():
    """Clear the terminal screen."""
    os.system('clear')

def setup_logging(output_path):
    """Set up logging to a file in the output folder."""
    log_file = os.path.join(output_path, 'padding_errors.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger()


def clean_path(path_str):
    """Clean input path by removing quotes and extra spaces."""
    return path_str.strip().strip('\'"')

def pad_images(input_path, output_format, shape, color, custom_width, custom_height, custom_color, include_subfolders):
    """Pad images to the specified shape and color."""
    output_dir = os.path.join(str(pathlib.Path(input_path).resolve()), "Output", "Padded")
    os.makedirs(output_dir, exist_ok=True)
    logger = setup_logging(output_dir)
    
    input_path = pathlib.Path(input_path).resolve()
    if not input_path.exists():
        logger.error("Input path does not exist.")
        print("\033[33mError: Input path does not exist.\033[0m", file=sys.stderr)
        return [], [], output_dir

    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff')
    images = []
    if input_path.is_file() and input_path.suffix.lower() in image_extensions:
        images = [input_path]
    elif input_path.is_dir():
        pattern = '**/*' if include_subfolders else '*'
        images = [f for f in sorted(input_path.glob(pattern)) if f.suffix.lower() in image_extensions and f.is_file()]
    else:
        logger.error("Input must be a file or directory.")
        print("\033[33mError: Input must be a file or directory.\033[0m", file=sys.stderr)
        return [], [], output_dir
    
    print()
    print("\033[33mScanning for Images...\033[0m")
    print(f"{len(images)} \033[33mimages found\033[0m")
    print()
    print("\033[33mPadding Images...\033[0m")
    
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
                
                new_image = Image.new('RGBA', (new_width, new_height), padding_color)
                offset = ((new_width - width) // 2, (new_height - height) // 2)
                new_image.paste(img, offset, img)
                
                if pillow_format == 'JPEG':
                    new_image = new_image.convert('RGB')
                
                relative_path = os.path.relpath(img_path.parent, input_path)
                output_dir_path = os.path.join(output_dir, relative_path) if relative_path != '.' else output_dir
                os.makedirs(output_dir_path, exist_ok=True)
                output_filename = f"{os.path.splitext(img_path.name)[0]}_padded{file_extension}"
                output_path = os.path.join(output_dir_path, output_filename)
                
                new_image.save(output_path, format=pillow_format, quality=95 if pillow_format == 'JPEG' else None)
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

if __name__ == "__main__":
    while True:
        clear_screen()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mImage Padder\033[0m")
        print("Adds Padding to Images")
        print("\033[92m==================================================\033[0m")
        print()

        max_attempts = 5
        attempt = 0
        input_path = None
        while attempt < max_attempts:
            input_path = input("Enter path: \n > ").strip()
            input_path = clean_path(input_path)
            try:
                normalized_path = str(pathlib.Path(input_path).resolve())
                if os.path.exists(normalized_path):
                    input_path = normalized_path
                    break
                print(f\033[33m"Error: \033[0m'{normalized_path}'\033[33m does not exist. Ensure the path is correct and the external drive (if any) is mounted.\033[0m", file=sys.stderr)
            except Exception as e:
                print(f"\033[33mError resolving path \033[0m'{input_path}': {e}. \033[33mPlease try again.\033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        print()

        include_subfolders = djj.prompt_choice("\033[33mInclude subfolders?\033[0m\n1. Yes, 2. No ", ['1', '2'], default='2') == '1'
        print()

        attempt = 0
        shape = None
        while attempt < max_attempts:
            shape_choice = input("\033[33mShape\033[0m1. Square\n2. Landscape\n3. Portrait\n4. Custom \n -> ").strip()
            if shape_choice == '1':
                shape = 'square'
                break
            elif shape_choice == '2':
                shape = 'landscape'
                break
            elif shape_choice == '3':
                shape = 'portrait'
                break
            elif shape_choice == '4':
                shape = 'custom'
                break
            print("\033[33mPlease enter 1, 2, 3, or 4 only.\033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        print()

        custom_width = None
        custom_height = None
        if shape == 'custom':
            attempt = 0
            while attempt < max_attempts:
                try:
                    custom_width = int(input("\033[33mCustom width in pixels: \033[0m").strip())
                    print()
                    if custom_width > 0:
                        break
                    print("\033[33mPlease enter a positive integer.\033[0m", file=sys.stderr)
                except ValueError:
                    print("\033[33mPlease enter a valid integer.\033[0m", file=sys.stderr)
                attempt += 1
                if attempt == max_attempts:
                    print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                    sys.exit(1)
            print()

            attempt = 0
            while attempt < max_attempts:
                try:
                    custom_height = int(input("\033[33mCustom height in pixels: \033[0m").strip())
                    print()
                    if custom_height > 0:
                        break
                    print("\033[33mPlease enter a positive integer.\033[0m", file=sys.stderr)
                except ValueError:
                    print("\033[33mPlease enter a valid integer.\033[0m", file=sys.stderr)
                attempt += 1
                if attempt == max_attempts:
                    print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                    sys.exit(1)
            print()

        attempt = 0
        color = None
        while attempt < max_attempts:
            color_choice = input("\033[33mPadding color \033[0m\n1. White\n2. Black\n3. Grey\n4. Custom) \n -> ").strip()
            if color_choice == '1':
                color = 'white'
                break
            elif color_choice == '2':
                color = 'black'
                break
            elif color_choice == '3':
                color = 'grey'
                break
            elif color_choice == '4':
                color = 'custom'
                break
            print("\033[33mPlease enter 1, 2, 3, or 4 only.\033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        print()

        custom_color = None
        if color == 'custom':
            attempt = 0
            while attempt < max_attempts:
                try:
                    color_input = input("Custom color (R,G,B,A - e.g., 255,255,255,255): \n > ").strip()
                    r, g, b, a = map(int, color_input.split(','))
                    if all(0 <= x <= 255 for x in [r, g, b, a]):
                        custom_color = (r, g, b, a)
                        break
                    print("\033[33mEach value must be between \033[0m0 \033[33mand\033[0m 255.", file=sys.stderr)
                except ValueError:
                    print("\033[33mPlease enter four integers separated by commas \033[0m(e.g., 255,255,255,255).\n -> ", file=sys.stderr)
                attempt += 1
                if attempt == max_attempts:
                    print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                    sys.exit(1)
            print()

        attempt = 0
        output_format = None
        while attempt < max_attempts:
            format_choice = input("Output format (1. PNG, 2. JPG, 3. BMP, 4. GIF): \n > ").strip()
            if format_choice == '1':
                output_format = 'png'
                break
            elif format_choice == '2':
                output_format = 'jpg'
                break
            elif format_choice == '3':
                output_format = 'bmp'
                break
            elif format_choice == '4':
                output_format = 'gif'
                break
            print("\033[33mPlease enter 1, 2, 3, or 4 only.\033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        print()

        print("-------------")
        successful, failed, output_dir = pad_images(input_path, output_format, shape, color, custom_width, custom_height, custom_color, include_subfolders)
        
        print("\n" * 1)
        print("\033[33mPadding Summary\033[0m")
        print("-------------")
        print(f"✅ \033[33mSuccessfully padded: \033[0m{len(successful)}\033[33m images\033[0m")
        if failed:
            print(f"\033[33mFailed operations:\033[0m {len(failed)}\033[33m (see padding_errors.log in output folder)\033[0m")
        print(f"\033[33mOutput folder:\033[0m \n{output_dir}")
        print("\n" * 2)

        try:
            subprocess.run(['open', output_dir], check=True)
        except subprocess.CalledProcessError as e:
            print(f"\033[33mError opening output folder:\033[0m {e}", file=sys.stderr)

        action = djj.what_next()
        if action == 'exit':
            break