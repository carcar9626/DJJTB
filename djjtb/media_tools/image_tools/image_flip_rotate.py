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
    log_file = os.path.join(output_path, 'rotate_flip_errors.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger()



def clean_path(path_str):
    """Clean input path by removing quotes and extra spaces."""
    return path_str.strip().strip('\'"')


def rotate_or_flip_images(input_path, operation, choice, custom_angle, include_subfolders, output_format):
    """Rotate or flip images based on user input."""
    output_dir = os.path.join(str(pathlib.Path(input_path).resolve()), "Output", "RotatedFlipped")
    os.makedirs(output_dir, exist_ok=True)
    logger = setup_logging(output_dir)
    
    input_path = pathlib.Path(input_path).resolve()
    if not input_path.exists():
        logger.error("Input path does not exist.")
        print("\033[33mError: Input path does not exist\033[0m.", file=sys.stderr)
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
    
    print("\033[33mScanning for Images...\033[0m")
    print(f"{len(images)} \033[33mimages found\033[0m")
    print()
    print("\033[33mProcessing Images...\033[0m")
    print
    
    successful = []
    failed = []
    format_map = {'png': ('PNG', '.png'), 'jpg': ('JPEG', '.jpg'), 'bmp': ('BMP', '.bmp'), 'gif': ('GIF', '.gif')}
    pillow_format, file_extension = format_map[output_format.lower()]
    
    for i, img_path in enumerate(images, 1):
        try:
            with Image.open(img_path) as img:
                if operation == 'rotate':
                    if choice == '90':
                        img = img.rotate(90, expand=True)
                    elif choice == '180':
                        img = img.rotate(180, expand=True)
                    elif choice == '270':
                        img = img.rotate(270, expand=True)
                    else:
                        img = img.rotate(-custom_angle, expand=True)
                else:
                    if choice == 'horizontal':
                        img = img.transpose(Image.FLIP_LEFT_RIGHT)
                    else:
                        img = img.transpose(Image.FLIP_TOP_BOTTOM)
                
                if pillow_format == 'JPEG' and img.mode == 'RGBA':
                    img = img.convert('RGB')
                
                relative_path = os.path.relpath(img_path.parent, input_path)
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

if __name__ == "__main__":
    while True:
        clear_screen()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mImage Rotate/Flip\033[0m")
        print("Rotates or Flips Images")
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
                print(f"\033[33mError: \033[0m'{normalized_path}' \033[33mdoes not exist. Ensure the path is correct and the external drive (if any) is mounted.\033[0m", file=sys.stderr)
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
        operation = None
        while attempt < max_attempts:
            op_choice = input("\033[33mOperation\033[0m\n1. Flip, 2. Rotate:  ").strip()
            if op_choice == '1':
                operation = 'flip'
                break
            elif op_choice == '2':
                operation = 'rotate'
                break
            print("\033[33mPlease enter 1 or 2 only.\033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        print()

        choice = None
        custom_angle = None
        if operation == 'flip':
            attempt = 0
            while attempt < max_attempts:
                flip_choice = input("\033[33mFlip direction\033[0m\n1. Horizontal ↔️, 2. Vertical ↕️: ").strip()
                print()
                if flip_choice == '1':
                    choice = 'horizontal'
                    break
                elif flip_choice == '2':
                    choice = 'vertical'
                    break
                print("\033[33mPlease enter 1 or 2 only.\033[0m", file=sys.stderr)
                attempt += 1
                if attempt == max_attempts:
                    print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                    sys.exit(1)
        else:
            attempt = 0
            while attempt < max_attempts:
                rotate_choice = input("\033[33mRotation\033[0m\n1. 90°, 2. 180°, 3. 270°, 4. Custom: ").strip()
                print()
                if rotate_choice in ['1', '2', '3']:
                    choice = {'1': '90', '2': '180', '3': '270'}[rotate_choice]
                    break
                elif rotate_choice == '4':
                    choice = 'custom'
                    attempt2 = 0
                    while attempt2 < max_attempts:
                        try:
                            custom_angle = float(input("Enter custom angle (degrees, positive = counterclockwise): \n > ").strip())
                            break
                        except ValueError:
                            print("Please enter a valid number.", file=sys.stderr)
                        attempt2 += 1
                        if attempt2 == max_attempts:
                            print("Too many invalid attempts. Exiting.", file=sys.stderr)
                            sys.exit(1)
                    break
                print("\033[33mPlease enter 1, 2, 3, or 4 only.\033[0m", file=sys.stderr)
                attempt += 1
                if attempt == max_attempts:
                    print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                    sys.exit(1)
        print()

        attempt = 0
        output_format = None
        while attempt < max_attempts:
            format_choice = input("\033[33mOutput format \033[0m\n1. PNG, 2. JPG, 3. BMP, 4. GIF: ").strip()
            print()
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
        successful, failed, output_dir = rotate_or_flip_images(input_path, operation, choice, custom_angle, include_subfolders, output_format)
        
        print("\n" * 1)
        print("\033[33mRotate/Flip Summary\033[0m")
        print("-------------")
        print(f"\033[33m✅ Successfully processed:\033[0m {len(successful)}\033[33m images\033[0m")
        if failed:
            print(f"\033[33mFailed operations:\033[0m {len(failed)} \033[33m(see rotate_flip_errors.log in output folder)\033[0m")
        print(f"\033[33mOutput folder:\033[0m \n{output_dir}")
        print("\n" * 2)

        try:
            subprocess.run(['open', output_dir], check=True)
        except subprocess.CalledProcessError as e:
            print(f"\033[33mError opening output folder:\033[0m {e}", file=sys.stderr)

        action = djj.what_next()
        if action == 'exit':
            break