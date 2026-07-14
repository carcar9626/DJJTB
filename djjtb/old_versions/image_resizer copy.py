import os
import subprocess
from PIL import Image
import pathlib
import sys
import time
import logging
import djjtb.utils as djj

os.system('clear')
Image.MAX_IMAGE_PIXELS = 200000000

def setup_logging(output_path):
    """Set up logging to a file in the output folder."""
    log_file = os.path.join(output_path, 'resize_errors.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def collect_images_from_folder(input_path, subfolders=False):
    """Collect supported images from folder"""
    input_path_obj = pathlib.Path(input_path)
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.tiff')
    
    images = []
    if input_path_obj.is_dir():
        if subfolders:
            for root, _, filenames in os.walk(input_path):
                images.extend(pathlib.Path(root) / f for f in filenames
                            if pathlib.Path(f).suffix.lower() in image_extensions)
        else:
            images = [f for f in input_path_obj.glob('*')
                     if f.suffix.lower() in image_extensions and f.is_file()]
    
    return sorted([str(f) for f in images], key=str.lower)

def collect_images_from_paths(file_paths):
    """Collect images from space-separated paths"""
    images = []
    paths = file_paths.strip().split()
    
    for path in paths:
        path = path.strip('\'"')
        path_obj = pathlib.Path(path)
        
        if path_obj.is_file() and path_obj.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.tiff'):
            images.append(str(path_obj))
        elif path_obj.is_dir():
            images.extend(collect_images_from_folder(path))
    
    return sorted(images, key=str.lower)

def get_valid_inputs():
    """Get and validate input files"""
    print("\033[1;93m🖼️  Select images to resize\033[0m")
    
    input_mode = djj.prompt_choice(
        "\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
        ['1', '2'],
        default='1'
    )
    print()
    
    valid_paths = []
    src_path = None
    
    if input_mode == '1':
        src_path = djj.get_path_input("Enter folder path")
        print()
        
        include_sub = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        
        valid_paths = collect_images_from_folder(src_path, include_sub)
        
    else:
        file_paths = input("📁 \033[93mEnter image paths (space-separated):\033[0m\n -> ").strip()
        
        if not file_paths:
            print("❌ \033[93mNo file paths provided.\033[0m")
            sys.exit(1)
        
        valid_paths = collect_images_from_paths(file_paths)
        # Set src_path to parent of first image for output
        if valid_paths:
            src_path = str(pathlib.Path(valid_paths[0]).parent)
        print()
    
    if not valid_paths:
        print("❌ \033[93mNo valid image files found.\033[0m")
        sys.exit(1)
    
    os.system('clear')
    print("\n" * 2)
    print(f"✅ \033[93mFound\033[0m {len(valid_paths)} \033[93msupported image(s)\033[0m")
    print()
    
    return valid_paths, src_path

def resize_images(images, src_path, dimension_type, desired_dimension, output_format):
    """Resize images proportionally based on desired width or height."""
    # Set output directory
    output_base = os.path.join(src_path, "Output", "Resized")
    os.makedirs(output_base, exist_ok=True)
    
    setup_logging(output_base)
    
    print("\033[93mResizing Images...\033[0m")
    successful = []
    failed = []
    
    format_map = {'png': ('PNG', '.png'), 'jpg': ('JPEG', '.jpg')}
    pillow_format, file_extension = format_map[output_format.lower()]
    
    for i, img_path in enumerate(images, 1):
        try:
            with Image.open(img_path) as img:
                if pillow_format == 'JPEG' and img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                elif img.mode not in ('RGB', 'RGBA', 'L'):
                    img = img.convert('RGB')
                
                orig_width, orig_height = img.size
                
                if dimension_type == 1:  # Width
                    if orig_width <= desired_dimension:
                        target_width = orig_width
                        target_height = orig_height
                    else:
                        target_width = desired_dimension
                        target_height = int(orig_height * (desired_dimension / orig_width))
                elif dimension_type == 2:  # Height
                    if orig_height <= desired_dimension:
                        target_height = orig_height
                        target_width = orig_width
                    else:
                        target_height = desired_dimension
                        target_width = int(orig_width * (desired_dimension / orig_height))
                else:  # Longest Edge
                    longest = max(orig_width, orig_height)
                    if longest <= desired_dimension:
                        target_width = orig_width
                        target_height = orig_height
                    elif orig_width >= orig_height:
                        target_width = desired_dimension
                        target_height = int(orig_height * (desired_dimension / orig_width))
                    else:
                        target_height = desired_dimension
                        target_width = int(orig_width * (desired_dimension / orig_height))
                
                if target_width != orig_width or target_height != orig_height:
                    img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                else:
                    img_resized = img
                
                # Save directly to output base (no subfolder structure for now)
                output_filename = f"{pathlib.Path(img_path).stem}_r{file_extension}"
                output_path = os.path.join(output_base, output_filename)
                img_resized.save(output_path, format=pillow_format, quality=95)
                successful.append(pathlib.Path(img_path).name)
                
                sys.stdout.write(f"\rProcessing image {i}/{len(images)}...")
                sys.stdout.flush()
        except Exception as e:
            failed.append((pathlib.Path(img_path).name, str(e)))
            logging.error(f"Error processing {pathlib.Path(img_path).name}: {e}")
            sys.stdout.write(f"\033[93m\rProcessing image\033[0m {i}/{len(images)}... (failed)")
            sys.stdout.flush()
    
    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()
    
    return successful, failed, output_base

if __name__ == '__main__':
    while True:
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mImage Resizer\033[0m")
        print("Resizes Images by Dimension")
        print("\033[92m==================================================\033[0m")
        print()
        
        # Get input files using new pattern
        images, src_path = get_valid_inputs()
        
        # Dimension type
        dimension_type = djj.prompt_choice(
            "\033[93mDimension Anchor:\033[0m\n1. Width (↔️)\n2. Height (↕️)\n3. Longest Edge (⤢)\n",
            ['1', '2', '3'],
            default='3'
        )
        dimension_type = int(dimension_type)
        print()
        
        # Desired dimension
        desired_dimension = djj.get_int_input(
            "Output dimension in px",
            min_val=1
        )
        print()
        
        # Output format
        output_format = djj.prompt_choice(
            "\033[93mFormat:\033[0m\n1. PNG\n2. JPG\n",
            ['1', '2'],
            default='2'
        )
        output_format = 'png' if output_format == '1' else 'jpg'
        print()
        print("-------------")
        
        # Resize images
        successful, failed, output_base = resize_images(
            images, src_path, dimension_type, desired_dimension, output_format
        )
        
        # Display results
        print("\n")
        print("\033[93mResize Summary\033[0m")
        print("-------------")
        print(f"\033[93mSuccessfully resized:\033[0m {len(successful)} \033[93mimages\033[0m")
        if failed:
            print("\033[93mFailed resizes:\033[0m")
            for name, error in failed:
                print(f"  {name}: {error}")
        print(f"\033[93mOutput folder:\033[0m\n{output_base}")
        print("\n" * 2)
        
        djj.prompt_open_folder(output_base)
        
        action = djj.what_next()
        if action == 'exit':
            break