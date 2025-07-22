import os
import subprocess
from PIL import Image
import pathlib
import sys
import time
import logging
import djjtb.utils as djj
os.system('clear')
# Increase Pillow's decompression bomb limit
Image.MAX_IMAGE_PIXELS = 200000000  # Set to 200 million pixels

def setup_logging(output_path):
    """Set up logging to a file in the output folder."""
    log_file = os.path.join(output_path, 'resize_errors.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def resize_images(input_path, dimension_type, desired_dimension, include_sub, output_format):
    """Resize images proportionally based on desired width or height, skipping if original is smaller."""
    # Resolve input path
    input_path = pathlib.Path(input_path).resolve()
    if not input_path.exists():
        print("Error: Input path does not exist.", file=sys.stderr)
        return [], []
    
    # Set output directory to ***input_path***/Output/Resized
    output_base = os.path.join(str(input_path), "Output", "Resized")
    os.makedirs(output_base, exist_ok=True)
    
    # Set up logging in the base output directory
    setup_logging(output_base)
    
    # Collect images
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.tiff')
    images = []
    if input_path.is_file() and input_path.suffix.lower() in image_extensions:
        images = [input_path]
    elif input_path.is_dir():
        pattern = '**/*' if include_sub else '*'
        images = [f for f in input_path.glob(pattern) if f.suffix.lower() in image_extensions and f.is_file()]
    else:
        print("\033[33mError: Input must be a file or directory.\033[0m", file=sys.stderr)
        return [], []
    
    print ("\033[33mScanning for Images...\033[0m")
    print(f"{len(images)} \033[33mimages found\033[0m")
    print ()
    print ("\033[33mResizing Images...\033[0m")
    successful = []
    failed = []
    
    # Map output_format to Pillow format and file extension
    format_map = {'png': ('PNG', '.png'), 'jpg': ('JPEG', '.jpg')}
    pillow_format, file_extension = format_map[output_format.lower()]
    
    # Process each image
    for i, img_path in enumerate(images, 1):
        try:
            with Image.open(img_path) as img:
                # Convert to RGB if saving as JPEG (JPEG doesn't support RGBA)
                if pillow_format == 'JPEG' and img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                elif img.mode not in ('RGB', 'RGBA', 'L'):
                    img = img.convert('RGB')
                
                # Get original dimensions
                orig_width, orig_height = img.size
                
                # Determine target dimensions
                if dimension_type == 1:  # Width
                    if orig_width <= desired_dimension:
                        target_width = orig_width
                        target_height = orig_height
                    else:
                        target_width = desired_dimension
                        target_height = int(orig_height * (desired_dimension / orig_width))
                else:  # Height
                    if orig_height <= desired_dimension:
                        target_height = orig_height
                        target_width = orig_width
                    else:
                        target_height = desired_dimension
                        target_width = int(orig_width * (desired_dimension / orig_height))
                
                # Resize only if dimensions change
                if target_width != orig_width or target_height != orig_height:
                    img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                else:
                    img_resized = img
                
                # Determine output path, preserving subfolder structure
                relative_path = os.path.relpath(img_path.parent, input_path)
                output_dir = os.path.join(output_base, relative_path) if relative_path != '.' else output_base
                os.makedirs(output_dir, exist_ok=True)
                
                # Save with original filename + '_r' + chosen extension
                output_filename = f"{os.path.splitext(img_path.name)[0]}_r{file_extension}"
                output_path = os.path.join(output_dir, output_filename)
                img_resized.save(output_path, format=pillow_format, quality=95)
                successful.append(img_path.name)
                sys.stdout.write(f"\rProcessing image {i}/{len(images)}...")
                sys.stdout.flush()
        except Exception as e:
            failed.append((img_path.name, str(e)))
            logging.error(f"Error processing {img_path.name}: {e}")
            sys.stdout.write(f"\033[33m\rProcessing image\033[0m {i}/{len(images)}... (failed)")
            sys.stdout.flush()
    
    # Clear processing line
    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()
    
    return successful, failed

if __name__ == '__main__':
    while True:
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mImage Resizer\033[0m")
        print("Resizes Images by Dimension")
        print("\033[92m==================================================\033[0m")
        print()
        # Prompt for input path
        max_attempts = 5
        attempt = 0
        input_path = None
        while attempt < max_attempts:
            input_path = input("\033[33mEnter path: \n -> \033[0m").strip()
            # Remove quotes if present
            input_path = input_path.strip("'").strip('"')
            # Remove any leading/trailing spaces again after stripping quotes
            input_path = input_path.strip()
            # Normalize the path to handle spaces and special characters
            try:
                normalized_path = str(pathlib.Path(input_path).resolve())
                if os.path.exists(normalized_path):
                    input_path = normalized_path
                    break
                print(f"\033[33mError:\033[0m '{normalized_path}' \033[33mdoes not exist. Ensure the path is correct and the external drive (if any) is mounted. Please try again.\033[0m", file=sys.stderr)
            except Exception as e:
                print(f"\033[33mError resolving path \033[0m'{input_path}': {e}. \033[33mPlease try again\033[0m.", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        print ()
        # Prompt for subfolder inclusion
        include_sub = djj.prompt_choice("\033[33mInclude subfolders? \033[0m\m1. Yes, 2. No ", ['1', '2'], default='2') == '1'

        # Prompt for dimension type
        attempt = 0
        dimension_type = None
        while attempt < max_attempts:
            time.sleep(0.1)
            dim_choice = input("\033[33mDimension Anchor\033[0m\n 1.↔️ , 2.↕️ ): ").strip()
            if dim_choice == '1':
                dimension_type = 1
                break
            elif dim_choice == '2':
                dimension_type = 2
                break
            print("\033[33mPlease enter 1 or 2 only\033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        
        # Prompt for desired dimension
        attempt = 0
        desired_dimension = None
        while attempt < max_attempts:
            try:
                dim_input = input("\033[33mOutput dimension in px:\n > \033[0m ").strip()
                desired_dimension = int(dim_input)
                if desired_dimension > 0:
                    break
                print("\033[33mPlease enter a positive integer.\n\ > 033[0m ", file=sys.stderr)
            except ValueError:
                print("\033[33mPlease enter a valid integer.\n > \033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        
        # Prompt for output format
        attempt = 0
        output_format = None
        while attempt < max_attempts:
            format_choice = input("\033[33mFormat \033[0m(1.png 2.jpg): \n > ").strip()
            if format_choice == '1':
                output_format = 'png'
                break
            elif format_choice == '2':
                output_format = 'jpg'
                break
            print("\033[33mPlease enter '1' for PNG or '2' for JPG only.\n\033[0m >", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        print ()
        print ("-------------")
        # Resize images
        successful, failed = resize_images(input_path, dimension_type, desired_dimension, include_sub, output_format)
        
        # Determine the base output path for display
        output_base = os.path.join(str(pathlib.Path(input_path).resolve()), "Output", "Resized")
        
        # Display results
        print("\n" * 1)
        print("\033[33mResize Summary\033[0m")
        print("-------------")
        print(f"\033[33mSuccessfully resized:\033[0m {len(successful)} \033[33mimages\033[0m")
        if failed:
            print("\033[33mFailed resizes:\033[0m")
            for name, error in failed:
                print(f"  {name}: {error}")
        print(f"\033[33mOutput folder: \033[0m\n{output_base}")
        print("\n" * 2)
        
        # Open output folder (base directory)
        try:
            subprocess.run(['open', output_base], check=True)
        except subprocess.CalledProcessError as e:
            print(f"\033[33mError opening output folder:\033[0m {e}", file=sys.stderr)
        
        # Prompt to go again
        action = djj.what_next()
        if action == 'exit':
            break