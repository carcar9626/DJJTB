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
    log_file = os.path.join(output_path, 'convert_errors.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger()

def clean_path(path_str):
    """Clean input path by removing quotes and extra spaces."""
    return path_str.strip().strip('\'"')


def convert_images(input_path, output_format, keep_metadata, include_subfolders):
    """Convert images to specified format with metadata option."""
    output_dir = os.path.join(str(pathlib.Path(input_path).resolve()), "Output", "Converted")
    os.makedirs(output_dir, exist_ok=True)
    logger = setup_logging(output_dir)
    
    input_path = pathlib.Path(input_path).resolve()
    if not input_path.exists():
        logger.error("Input path does not exist.")
        print("Error: Input path does not exist.", file=sys.stderr)
        return [], []

    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
    images = []
    if input_path.is_file() and input_path.suffix.lower() in image_extensions:
        images = [input_path]
    elif input_path.is_dir():
        pattern = '**/*' if include_subfolders else '*'
        images = [f for f in sorted(input_path.glob(pattern)) if f.suffix.lower() in image_extensions and f.is_file()]
    else:
        logger.error("Input must be a file or directory.")
        print("\033[93mError: Input must be a file or directory.\033[0m", file=sys.stderr)
        return [], []
    
    print()
    print("\033[93mScanning for Images...\033[0m")
    print(f"{len(images)} \033[93mimages found\033[0m")
    print()
    print("\033[93mConverting Images...\033[0m")
    
    successful = []
    failed = []
    
    format_map = {'png': ('PNG', '.png'), 'jpg': ('JPEG', '.jpg'), 'bmp': ('BMP', '.bmp'), 'gif': ('GIF', '.gif')}
    pillow_format, file_extension = format_map[output_format.lower()]
    
    for i, img_path in enumerate(images, 1):
        try:
            with Image.open(img_path) as img:
                if pillow_format == 'JPEG' and img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                elif img.mode not in ('RGB', 'RGBA', 'L'):
                    img = img.convert('RGB')
                
                metadata = img.info.copy() if keep_metadata else {}
                relative_path = os.path.relpath(img_path.parent, input_path)
                output_dir_path = os.path.join(output_dir, relative_path) if relative_path != '.' else output_dir
                os.makedirs(output_dir_path, exist_ok=True)
                output_filename = f"{os.path.splitext(img_path.name)[0]}_c{file_extension}"
                output_path = os.path.join(output_dir_path, output_filename)
                img.save(output_path, format=pillow_format, **metadata)
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
        print("\033[1;93mImage Converter\033[0m")
        print("Converts Images to New Format")
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
                print(f"\033[93mError:\033[0m '{normalized_path}' \033[93mdoes not exist. Ensure the path is correct and the external drive (if any) is mounted.\033[0m", file=sys.stderr)
            except Exception as e:
                print(f"\033[93mError resolving path \033[0m'{input_path}': {e}. \033[93mPlease try again.\033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[93mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        print()

        include_subfolders = djj.prompt_choice("Include subfolders? \n1. Yes, 2. No ", ['1', '2'], default='2') == '1'
        print()

        attempt = 0
        output_format = None
        while attempt < max_attempts:
            format_choice = input("Output format\n1. PNG, 2. JPG, 3. BMP, 4. GIF:  ").strip()
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
            print("\033[93mPlease enter 1, 2, 3, or 4 only.\033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[93mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        print()

        keep_metadata = djj.prompt_choice("\033[93mKeep metadata? \033[0m\n1. Yes, 2. No ", ['1', '2'], default='2') == '1'
        print()

        print("-------------")
        successful, failed, output_dir = convert_images(input_path, output_format, keep_metadata, include_subfolders)
        
        print("\n" * 1)
        print("\033[93mConversion Summary\033[0m")
        print("-------------")
        print(f"✅ \033[93mSuccessfully converted:\033[0m {len(successful)} \033[93mimages\033[0m")
        if failed:
            print(f"\033[93mFailed conversions: \033[0m{len(failed)} \033[93m(see convert_errors.log in output folder)\033[0m")
        print(f"\033[93mOutput folder:\033[0m \n{output_dir}")
        print()

        djj.prompt_open_folder(output_dir)

        action = djj.what_next()
        if action == 'exit':
            break
os.system('clear')
