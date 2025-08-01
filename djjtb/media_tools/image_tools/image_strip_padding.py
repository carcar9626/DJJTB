import os
import subprocess
import djjtb.utils as djj
from pathlib import Path
from PIL import Image, ImageChops
import sys
os.system('clear')
    

def detect_border_color(im, tolerance=5):
    # Sample corners to guess padding color
    corners = [
        im.getpixel((0, 0)),
        im.getpixel((im.width - 1, 0)),
        im.getpixel((0, im.height - 1)),
        im.getpixel((im.width - 1, im.height - 1)),
    ]
    # Find the most common corner color
    colors = {}
    for c in corners:
        colors[c] = colors.get(c, 0) + 1
    border_color = max(colors, key=colors.get)
    return border_color

def trim_solid_padding(im, tolerance=5):
    im = im.convert("RGB")
    bg_color = detect_border_color(im)
    bg = Image.new("RGB", im.size, bg_color)
    # Create a diff mask that flags anything different from the bg color
    diff = ImageChops.difference(im, bg)
    diff = Image.eval(diff, lambda x: 255 if x > tolerance else 0)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox), im.size, (bbox[2] - bbox[0], bbox[3] - bbox[1])
    else:
        return im, im.size, im.size  # No crop

def process_folder(folder_path, include_sub=False):
    folder = Path(folder_path).expanduser().resolve()
    
    # Validate input path
    if not folder.exists():
        print("\033[33mError: Input path does not exist.\033[0m", file=sys.stderr)
        return 0, []
    
    # Set output directory to ***input_path***/Output/Stripped (matching resizer pattern)
    output_base = folder / "Output" / "Stripped"
    output_base.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📂 \033[33mProcessing images in:\033[0m {folder}")
    if include_sub:
        print("\n📁 \033[33mIncluding subfolders\033[0m")
    print()
    
    # Collect images using same logic as resizer
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.tiff', '.bmp')
    images = []
    
    if folder.is_file() and folder.suffix.lower() in image_extensions:
        images = [folder]
    elif folder.is_dir():
        # Use same pattern logic as resizer
        pattern = '**/*' if include_sub else '*'
        images = [f for f in folder.glob(pattern) if f.suffix.lower() in image_extensions and f.is_file()]
    else:
        print("\033[33mError: Input must be a file or directory.\033[0m", file=sys.stderr)
        return 0, []
    
    print("\033[33mScanning for Images...\033[0m")
    print(f"{len(images)} \033[33mimages found\033[0m")
    print()
    print("\033[33mStripping padding...\033[0m")
    
    successful = 0
    failed = []
    
    for i, file in enumerate(images, 1):
        try:
            with Image.open(file) as img:
                cropped, original_size, new_size = trim_solid_padding(img)
                
                # Determine output path, preserving subfolder structure (like resizer)
                relative_path = os.path.relpath(file.parent, folder)
                output_dir = output_base / relative_path if relative_path != '.' else output_base
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Save with original filename + '_stripped'
                output_filename = f"{file.stem}_stripped.png"
                out_path = output_dir / output_filename
                cropped.save(out_path)
                
                successful += 1
                sys.stdout.write(f"\r\033[33mProcessing image\033[0m {i}\033[33m/\033[0m{len(images)}...")
                sys.stdout.flush()
                
        except Exception as e:
            failed.append((file.name, str(e)))
            sys.stdout.write(f"\rP\033[33mrocessing image\033[0m {i}\033[33m/\033[0m{len(images)}... \033[33m(failed)\033[0m")
            sys.stdout.flush()
    
    # Clear processing line
    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()
    
    return successful, failed, output_base

def main():
    while True:
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mImage Padding Stripper\033[0m")
        print("Strips paddings of images")
        print("\033[92m==================================================\033[0m")
        print()
        
        # Prompt for input path (using same validation as resizer)
        max_attempts = 5
        attempt = 0
        input_path = None
        
        while attempt < max_attempts:
            input_path = input("📁 Enter path: \n -> ").strip()
            # Remove quotes if present
            input_path = input_path.strip("'").strip('"')
            # Remove any leading/trailing spaces again after stripping quotes
            input_path = input_path.strip()
            
            # Normalize the path to handle spaces and special characters
            try:
                normalized_path = str(Path(input_path).resolve())
                if os.path.exists(normalized_path):
                    input_path = normalized_path
                    break
                print(f"\033[33mError:\033[0m '{normalized_path}' \033[33mdoes not exist. Ensure the path is correct and the external drive (if any) is mounted. Please try again.\033[0m", file=sys.stderr)
            except Exception as e:
                print(f"\033[33mError resolving path \033[0m'{input_path}': {e}. \033[33mPlease try again.\033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        
        print()
        
        # Prompt for subfolder inclusion (same as resizer)
        include_sub = djj.prompt_choice("\033[33mInclude subfolders?\033[0m\n1. Yes, 2. No ", ['1', '2'], default='2') == '1'
        print()
        print("\033[1;33mProcessing...\033[0m")

        # Process images
        successful, failed, output_base = process_folder(input_path, include_sub)
        print("\n" * 2)
        # Display results (matching resizer format)
        print("\033[1;33mStrip Padding Summary\033[0m")
        print("---------------------")
        print(f"\033[33mSuccessfully processed:\033[0m {successful} \033[33mimages\033[0m")
        if failed:
            print("\033[33mFailed processing:\033[0m")
            for name, error in failed:
                print(f"  {name}: {error}")
        print(f"\033[33mOutput folder: \033[0m\n{output_base}")
        print("\n" * 2)
        
        # Open output folder
        djj.prompt_open_folder(output_base)
        
        # Prompt to go again
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()