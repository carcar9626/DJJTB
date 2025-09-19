#!/usr/bin/env python3

import os
import subprocess
import djjtb.utils as djj
from pathlib import Path
from PIL import Image, ImageChops
import sys
import numpy as np
from scipy.ndimage import label, find_objects

os.system('clear')

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

def collect_images_from_folder(input_path, include_subfolders=False):
    """Collect images from folder(s)."""
    input_path_obj = Path(input_path)
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
    
    images = []
    if input_path_obj.is_dir():
        if include_subfolders:
            for root, _, files in os.walk(input_path):
                images.extend(Path(root) / f for f in files if Path(f).suffix.lower() in image_extensions)
        else:
            images = [f for f in input_path_obj.glob('*') if f.suffix.lower() in image_extensions and f.is_file()]
    
    return sorted([Path(v) for v in images], key=lambda x: str(x).lower())

def collect_images_from_paths(file_paths):
    """Collect images from space-separated file paths."""
    images = []
    paths = file_paths.strip().split()
    
    for path in paths:
        path = path.strip('\'"')
        path_obj = Path(path)
        
        if path_obj.is_file() and path_obj.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'):
            images.append(path_obj)
        elif path_obj.is_dir():
            images.extend(collect_images_from_folder(str(path_obj), include_subfolders=False))
    
    return sorted(images, key=lambda x: str(x).lower())

def process_images(images, output_base_path):
    """Process a list of image files."""
    output_base = Path(output_base_path)
    output_base.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📂 \033[93mProcessing {len(images)} images\033[0m")
    print()
    print("\033[93mStripping padding / splitting collage...\033[0m")
    
    successful = 0
    failed = []
    
    for i, file in enumerate(images, 1):
        try:
            with Image.open(file) as img:
                cropped_images = trim_multiple_regions(img)
                
                # For multi-file mode, put all outputs in the same Output/Stripped folder
                output_dir = output_base
                output_dir.mkdir(parents=True, exist_ok=True)
                
                for idx, cropped in enumerate(cropped_images, 1):
                    output_filename = f"{file.stem}_part{idx}.png"
                    out_path = output_dir / output_filename
                    cropped.save(out_path)
                    successful += 1
                
                sys.stdout.write(f"\r\033[93mProcessing image\033[0m {i}\033[93m/\033[0m{len(images)}...")
                sys.stdout.flush()
                
        except Exception as e:
            failed.append((file.name, str(e)))
            sys.stdout.write(f"\r\033[93mProcessing image\033[0m {i}\033[93m/\033[0m{len(images)}... \033[93m(failed)\033[0m")
            sys.stdout.flush()
    
    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()
    
    return successful, failed

def process_folder(folder_path, include_sub=False):
    """Process images in a folder (original logic)."""
    folder = Path(folder_path).expanduser().resolve()
    
    if not folder.exists():
        print("\033[93mError: Input path does not exist.\033[0m", file=sys.stderr)
        return 0, [], None
    
    output_base = folder / "Output" / "Stripped"
    
    print(f"\n📂 \033[93mProcessing images in:\033[0m {folder}")
    if include_sub:
        print("\n📁 \033[93mIncluding subfolders\033[0m")
    
    images = collect_images_from_folder(folder_path, include_sub)
    
    print()
    print("\033[93mScanning for Images...\033[0m")
    print(f"{len(images)} \033[93mimages found\033[0m")
    
    if not images:
        return 0, [], output_base
    
    successful, failed = process_images(images, output_base)
    
    return successful, failed, output_base

def main():
    while True:
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mImage Padding Stripper\033[0m")
        print("Strips paddings of images / splits collages")
        print("\033[92m==================================================\033[0m")
        print()
        
        print("\033[93mSuggested Background Colors for Collages:\033[0m")
        print(" • \033[97mWhite\033[0m \033[94m(255,255,255);(#FFFFFF)\033[0m")
        print(" • \033[30mBlack\033[0m \033[94m(0,0,0);(#000000)\033[0m")
        print(" • \033[90mGray\033[0m \033[94m(136,136,136);(#888888)\033[0m")
        print(" • \033[92mChroma Green\033[0m \033[94m(0,255,0);(#00FF00)\033[0m")
        print(" • \033[96mChroma Blue\033[0m \033[94m(0,0,255);(#0000FF)\033[0m")
        print("\033[93mThese are auto-detected.\n\033[0m")
        
        # Input mode selection
        input_mode = djj.prompt_choice(
            "\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
            ['1', '2'],
            default='1'
        )
        print()

        images = []
        output_base = None
        successful = 0
        failed = []

        if input_mode == '1':
            # Folder mode (original logic)
            max_attempts = 5
            attempt = 0
            input_path = None
            
            while attempt < max_attempts:
                input_path = input("📁 \033[93mEnter folder path:\033[0m \n \033[5m->\033[0m ").strip()
                input_path = input_path.strip("'").strip('"').strip()
                try:
                    normalized_path = str(Path(input_path).resolve())
                    if os.path.exists(normalized_path):
                        input_path = normalized_path
                        break
                    print(f"\033[93mError:\033[0m '{normalized_path}' \033[93mdoes not exist. Please try again.\033[0m", file=sys.stderr)
                except Exception as e:
                    print(f"\033[93mError resolving path \033[0m'{input_path}': {e}. \033[93mPlease try again.\033[0m", file=sys.stderr)
                attempt += 1
                if attempt == max_attempts:
                    print("\033[93mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                    sys.exit(1)
            
            print()
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            
            print("\033[1;33mProcessing...\033[0m")
            successful, failed, output_base = process_folder(input_path, include_sub)
            
        else:
            # File paths mode
            file_paths = input("📁 \033[93mEnter image paths (space-separated):\n\033[0m -> ").strip()
            
            if not file_paths:
                print("❌ \033[93mNo file paths provided.\033[0m")
                continue
            
            images = collect_images_from_paths(file_paths)
            
            if not images:
                print("❌ \033[93mNo valid image files found. Try again.\033[0m\n")
                continue
                
            print()
            print("\033[93mScanning for images...\033[0m")
            print(f"✅ \033[93m{len(images)} images found\033[0m")
            print()
            
            # Set output folder to parent of first image for multi-file mode
            output_base = images[0].parent / "Output" / "Stripped"
            
            print("\033[1;33mProcessing...\033[0m")
            successful, failed = process_images(images, output_base)

        # Display results
        print("\n" * 2)
        print("\033[1;33mStrip Padding Summary\033[0m")
        print("---------------------")
        print(f"\033[93mSuccessfully processed:\033[0m {successful} \033[93mimages\033[0m")
        if failed:
            print("\033[93mFailed processing:\033[0m")
            for name, error in failed:
                print(f"  {name}: {error}")
        if output_base:
            print(f"\033[93mOutput folder: \033[0m\n{output_base}")
        print("\n" * 2)
        
        if output_base:
            try:
                djj.prompt_open_folder(output_base)
            except Exception as e:
                # Fallback: ask user if they want to open the folder manually
                print(f"\033[93mCouldn't auto-open folder. Error: {e}\033[0m")
                open_folder = input("\033[93mOpen output folder manually? (y/n): \033[0m").strip().lower()
                if open_folder == 'y':
                    import subprocess
                    import platform
                    folder_path = str(output_base)
                    try:
                        if platform.system() == "Darwin":  # macOS
                            subprocess.run(["open", folder_path])
                        elif platform.system() == "Windows":  # Windows
                            subprocess.run(["explorer", folder_path])
                        else:  # Linux
                            subprocess.run(["xdg-open", folder_path])
                    except Exception as e2:
                        print(f"\033[93mCouldn't open folder: {e2}\033[0m")
                        print(f"\033[93mFolder location: {folder_path}\033[0m")
        
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()