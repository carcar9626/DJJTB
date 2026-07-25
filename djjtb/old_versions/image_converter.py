import os
import sys
import pathlib
import logging
import djjtb.utils as djj
from PIL import Image

os.system('clear')

def setup_logging(output_path):
    """Set up logging to a file in the output folder."""
    logger = djj.setup_logging(output_path, "image_converter")
    return logger

def collect_images_from_folder(input_path, include_subfolders=False):
    """Collect image files from a directory."""
    input_path_obj = pathlib.Path(input_path)
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
    
    images = []
    if input_path_obj.is_dir():
        if include_subfolders:
            images = [f for f in input_path_obj.rglob('*')
                     if f.suffix.lower() in image_extensions and f.is_file()]
        else:
            images = [f for f in input_path_obj.glob('*')
                     if f.suffix.lower() in image_extensions and f.is_file()]
    
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

def collect_images_from_txt():
    """Collect images from txt file (files and folders)."""
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
    txt_path = djj.get_path_input("Enter txt file path")
    
    if not os.path.exists(txt_path):
        return []
    
    images = []
    try:
        with open(txt_path, 'r') as f:
            paths = [line.strip() for line in f if line.strip()]
        
        for path in paths:
            path_obj = pathlib.Path(path)
            if path_obj.is_file() and path_obj.suffix.lower() in image_extensions:
                images.append(str(path_obj))
            elif path_obj.is_dir():
                images.extend(collect_images_from_folder(str(path_obj), include_subfolders=False))
    except Exception as e:
        print(f"\033[93m⚠️  Error reading txt file: {e}\033[0m")
    
    return sorted(set(images), key=str.lower)

def convert_images(image_list, output_folder, output_format, keep_metadata, quality=95):
    """
    Convert images to specified format.
    
    Args:
        image_list: List of image file paths
        output_folder: Output directory
        output_format: Target format ('png', 'jpg', 'bmp', 'gif', 'webp')
        keep_metadata: Whether to preserve EXIF data
        quality: JPEG/WebP quality (1-100)
    
    Returns:
        tuple: (successful_list, failed_list)
    """
    os.makedirs(output_folder, exist_ok=True)
    logger = setup_logging(output_folder)
    
    format_map = {
        'png': ('PNG', '.png'),
        'jpg': ('JPEG', '.jpg'),
        'jpeg': ('JPEG', '.jpg'),
        'bmp': ('BMP', '.bmp'),
        'gif': ('GIF', '.gif'),
        'webp': ('WebP', '.webp')
    }
    
    if output_format.lower() not in format_map:
        print(f"\033[93m⚠️  Unsupported format: {output_format}\033[0m")
        return [], []
    
    pillow_format, file_extension = format_map[output_format.lower()]
    
    print()
    print(f"\033[93m📊 Found {len(image_list)} image(s)\033[0m")
    print()
    print("\033[1;33m🔄 Converting Images...\033[0m")
    print("=" * 60)
    
    successful = []
    failed = []
    
    for i, img_path in enumerate(image_list):
        filename = os.path.basename(img_path)
        try:
            with Image.open(img_path) as img:
                # Handle color mode conversions
                if pillow_format == 'JPEG':
                    if img.mode in ('RGBA', 'LA', 'P'):
                        # Create white background for transparent images
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    elif img.mode not in ('RGB', 'L'):
                        img = img.convert('RGB')
                
                elif pillow_format in ('PNG', 'WebP'):
                    if img.mode not in ('RGB', 'RGBA', 'L', 'LA'):
                        img = img.convert('RGBA')
                
                # Prepare metadata
                save_kwargs = {}
                if keep_metadata and pillow_format in ('JPEG', 'PNG', 'WebP'):
                    exif = img.info.get('exif')
                    if exif:
                        save_kwargs['exif'] = exif
                
                # Add quality for JPEG/WebP
                if pillow_format in ('JPEG', 'WebP'):
                    save_kwargs['quality'] = quality
                
                # Build output filename
                base_name = os.path.splitext(filename)[0]
                output_filename = f"{base_name}_c{file_extension}"
                output_path = os.path.join(output_folder, output_filename)
                
                # Save image
                img.save(output_path, format=pillow_format, **save_kwargs)
                successful.append(filename)
                
                # Progress indicator
                progress = int(((i + 1) / len(image_list)) * 100)
                sys.stdout.write(f"\r\033[93m[{i+1}/{len(image_list)}]\033[0m Processing... ({progress}%)")
                sys.stdout.flush()
                
        except Exception as e:
            failed.append((filename, str(e)))
            logger.error(f"Failed to convert {filename}: {e}")
    
    # Clear progress line
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()
    
    print("=" * 60)
    print(f"\033[1;33m🏁 Conversion Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {len(successful)}")
    print(f"❌ \033[91mFailed:\033[0m {len(failed)}")
    
    if failed:
        print(f"\n\033[93m⚠️  Failed conversions (see log):\033[0m")
        for fname, error in failed[:3]:
            print(f"   • {fname}: {error[:50]}")
        if len(failed) > 3:
            print(f"   • ... and {len(failed) - 3} more")
    
    return successful, failed

def main():
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mImage Converter\033[0m")
        print("Convert images to different formats")
        print("\033[92m==================================================\033[0m")
        print()
        
        # Input mode selection
        input_mode = djj.prompt_choice(
            "\033[93mInput mode:\033[0m\n"
            "1. Folder path\n"
            "2. Space-separated file paths\n"
            "3. Path list from txt file\n",
            ['1', '2', '3'],
            default='1'
        )
        print()
        
        images = []
        source_folder = None
        
        if input_mode == '1':
            # Folder mode
            source_folder = djj.get_path_input("Enter folder path")
            print()
            
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            
            images = collect_images_from_folder(source_folder, include_sub)
            
        elif input_mode == '2':
            # File paths mode
            file_paths = input("📁 \033[93mEnter image paths (space-separated):\n\033[0m -> ").strip()
            
            if not file_paths:
                print("❌ \033[93mNo file paths provided.\033[0m")
                continue
            
            images = collect_images_from_paths(file_paths)
            if images:
                source_folder = str(pathlib.Path(images[0]).parent)
            print()
        
        else:  # input_mode == '3'
            # Txt file mode
            images = collect_images_from_txt()
            
            if not images:
                print("❌ \033[93mNo valid images found.\033[0m")
                continue
            
            if images:
                source_folder = str(pathlib.Path(images[0]).parent)
            print()
        
        if not images:
            print("❌ \033[93mNo image files found. Try again.\033[0m\n")
            continue
        
        print(f"✅ \033[93mFound {len(images)} image(s)\033[0m")
        
        # Show sample
        for i, img in enumerate(images[:5]):
            print(f"   {i+1}. {os.path.basename(img)}")
        if len(images) > 5:
            print(f"   ... and {len(images) - 5} more")
        print()
        
        # Output format
        format_choice = djj.prompt_choice(
            "\033[93mOutput format:\033[0m\n"
            "1. PNG\n"
            "2. JPG\n"
            "3. WebP\n"
            "4. BMP\n"
            "5. GIF\n",
            ['1', '2', '3', '4', '5'],
            default='1'
        )
        print()
        
        format_map = {'1': 'png', '2': 'jpg', '3': 'webp', '4': 'bmp', '5': 'gif'}
        output_format = format_map[format_choice]
        
        # Quality setting for JPEG/WebP
        quality = 95
        if output_format in ['jpg', 'webp']:
            quality_input = input(
                f"\033[93mQuality [1-100, default: 95]:\n\033[0m -> "
            ).strip()
            try:
                if quality_input:
                    quality = int(quality_input)
                    quality = max(1, min(100, quality))
            except ValueError:
                quality = 95
            print(f"\033[92m✓ Using quality: {quality}\033[0m")
            print()
        
        # Metadata option
        keep_metadata = djj.prompt_choice(
            "\033[93mKeep metadata?\033[0m\n1. Yes\n2. No\n",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        
        # Default output: source_folder/Output/Converted
        output_folder = os.path.join(source_folder, "Output", "Converted")
        print(f"\033[92m✓ Output folder: {output_folder}\033[0m")
        
        # Process images
        print("\n" * 2)
        print("\033[1;93mStarting conversion...\033[0m")
        
        successful, failed = convert_images(
            images,
            output_folder,
            output_format,
            keep_metadata,
            quality
        )
        
        print()
        print(f"\033[92m✓ Output folder:\033[0m {output_folder}")
        print()
        
        djj.prompt_open_folder(output_folder)
        
        print("\n" * 2)
        
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == '__main__':
    main()