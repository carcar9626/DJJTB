#!/usr/bin/env python3
"""
Metadata Stripper & Injector Tool
Strip metadata and optionally inject fake data
Updated: July 30, 2025
"""

import os
import sys
import subprocess
import time
import csv
import json
import random
from pathlib import Path
from PIL import Image, PngImagePlugin
import djjtb.utils as djj

# Fake metadata constants
FAKE_PROMPTS = [
    "a hyper-detailed futuristic city at sunset, ultra HD, trending on artstation",
    "ethereal fantasy landscape with magical creatures, mystical atmosphere",
    "cyberpunk street scene with neon lights, rain reflections, cinematic lighting",
    "serene mountain lake at dawn, misty atmosphere, photorealistic",
    "ancient temple ruins covered in vines, dramatic lighting, concept art",
    "space station interior with holographic displays, sci-fi environment",
    "medieval castle on a cliff during golden hour, epic fantasy art",
    "underwater coral reef teeming with colorful fish, nature photography",
    "steampunk clockwork mechanism, intricate details, bronze and copper tones",
    "abstract geometric patterns with vibrant colors, digital art"
]

NEGATIVE_PROMPTS = [
    "blurry, low quality, bad anatomy", "distorted, ugly, deformed, poorly drawn",
    "watermark, signature, text, copyright", "dark, underexposed, overexposed",
    "cartoon, anime, painting, drawing", "monochrome, black and white, sepia"
]

SAMPLERS = [
    "DPM++ 2M Karras", "Euler a", "DDIM", "LMS", "Heun", "DPM2", "DPM++ SDE",
    "UniPC", "PLMS", "DPM fast", "DPM adaptive"
]

MODELS = [
    "deliberate_v2", "realistic_vision_v5", "dreamshaper_8", "absolute_reality",
    "cyberrealistic_v3", "epic_realism", "photon_v1", "analog_diffusion"
]

CAMERA_MAKES = ["Canon", "Nikon", "Sony", "Apple", "Samsung", "Fujifilm", "Panasonic"]
CAMERA_MODELS = ["EOS 5D Mark IV", "D850", "A7R III", "iPhone 14 Pro", "Galaxy S23", "X-T4"]

os.system('clear')

def clean_path(path_str):
    return path_str.strip().strip('\'"')

def generate_fake_metadata(file_type="image"):
    """Generate creative fake metadata"""
    if file_type.lower() == "image":
        prompt = random.choice(FAKE_PROMPTS)
        negative = random.choice(NEGATIVE_PROMPTS)
        sampler = random.choice(SAMPLERS)
        model = random.choice(MODELS)
        
        steps = random.randint(20, 50)
        cfg_scale = round(random.uniform(4.0, 12.0), 1)
        seed = random.randint(1000000, 99999999)
        width = random.choice([512, 768, 1024, 1152, 1344])
        height = random.choice([512, 768, 1024, 1152, 1344])
        model_hash = ''.join(random.choices('abcdef0123456789', k=8))
        
        return {
            "parameters": (
                f"prompt: {prompt}\n"
                f"negative_prompt: {negative}\n"
                f"Steps: {steps}, Sampler: {sampler}, CFG scale: {cfg_scale}, "
                f"Seed: {seed}, Size: {width}x{height},\n"
                f"Model hash: {model_hash}, Model: {model}"
            ),
            "Software": "Stable Diffusion WebUI",
            "Make": random.choice(CAMERA_MAKES),
            "Model": random.choice(CAMERA_MODELS),
            "DateTime": time.strftime("%Y:%m:%d %H:%M:%S"),
            "Artist": random.choice(["AI Generator", "Digital Artist", "CreativeStudio"]),
            "Copyright": f"© {time.strftime('%Y')} AI Generated Content"
        }
    else:
        return {
            "title": random.choice(["Creative Video", "Digital Content", "Media File"]),
            "artist": random.choice(["ContentCreator", "DigitalStudio", "MediaProducer"]),
            "encoder": random.choice(["HandBrake", "FFmpeg", "Adobe Media Encoder"]),
            "comment": "Processed with advanced encoding settings",
            "date": time.strftime("%Y"),
            "software": random.choice(["Final Cut Pro", "Premiere Pro", "DaVinci Resolve"])
        }

def get_file_type_by_extension(filename):
    video_extensions = ['.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v', '.flv', '.wmv', '.3gp']
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.ico', '.heic', '.heif']
    audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.wma']
    
    ext = Path(filename).suffix.lower()
    if ext in video_extensions:
        return 'Video'
    elif ext in image_extensions:
        return 'Image'
    elif ext in audio_extensions:
        return 'Audio'
    else:
        return 'Unknown'

def is_media_file(filename, file_types='both'):
    video_extensions = ['.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v', '.flv', '.wmv', '.3gp']
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.ico', '.heic', '.heif']
    audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.wma']
    
    if file_types == 'videos':
        return any(filename.lower().endswith(ext) for ext in video_extensions)
    elif file_types == 'images':
        return any(filename.lower().endswith(ext) for ext in image_extensions)
    elif file_types == 'audio':
        return any(filename.lower().endswith(ext) for ext in audio_extensions)
    else:
        return any(filename.lower().endswith(ext) for ext in video_extensions + image_extensions + audio_extensions)

def collect_and_select_files(input_path, include_sub=False, file_types='both'):
    """Collect files and let user select which ones to process"""
    input_path_obj = Path(input_path)
    all_files = []
    
    if input_path_obj.is_dir():
        if include_sub:
            for root, _, files in os.walk(input_path):
                for file in files:
                    if is_media_file(file, file_types):
                        all_files.append(str(Path(root) / file))
        else:
            for file in input_path_obj.glob('*'):
                if file.is_file() and is_media_file(file.name, file_types):
                    all_files.append(str(file))
    
    all_files = sorted(all_files, key=str.lower)
    
    if not all_files:
        return []
    
    print(f"📁 Found {len(all_files)} media files")
    
    # Show files and let user select
    selection_mode = djj.prompt_choice(
        "\033[93mFile selection:\033[0m\n1. Process all files\n2. Select specific files\n",
        ['1', '2'],
        default='1'
    )
    
    if selection_mode == '1':
        return all_files
    
    # Show files for selection
    print("\033[93mAvailable files:\033[0m")
    for i, file_path in enumerate(all_files, 1):
        print(f"{i:3d}. {os.path.basename(file_path)}")
    
    print("\nEnter file numbers (e.g., 1,3,5-8,10) or 'all':")
    selection = input(" > ").strip().lower()
    
    if selection == 'all':
        return all_files
    
    # Parse selection
    selected_files = []
    try:
        for part in selection.split(','):
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                for i in range(start, end + 1):
                    if 1 <= i <= len(all_files):
                        selected_files.append(all_files[i-1])
            else:
                i = int(part)
                if 1 <= i <= len(all_files):
                    selected_files.append(all_files[i-1])
    except ValueError:
        print("❌ Invalid selection format")
        return []
    
    return list(dict.fromkeys(selected_files))  # Remove duplicates while preserving order

def collect_files_from_paths(file_paths, file_types='both'):
    media_files = []
    paths = file_paths.strip().split()
    
    for path in paths:
        path = clean_path(path)
        path_obj = Path(path)
        
        if path_obj.is_file() and is_media_file(path_obj.name, file_types):
            media_files.append(str(path_obj))
        elif path_obj.is_dir():
            # For directories in file paths, collect all files
            for file in path_obj.glob('*'):
                if file.is_file() and is_media_file(file.name, file_types):
                    media_files.append(str(file))
    
    return sorted(media_files, key=str.lower)

def run_ffmpeg_strip(input_file, output_file):
    try:
        cmd = ['ffmpeg', '-y', '-i', str(input_file), '-map_metadata', '-1', '-c', 'copy', str(output_file)]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def run_exiftool_strip(input_file, output_file):
    try:
        cmd = ['exiftool', '-all=', '-overwrite_original', str(input_file)]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if str(input_file) != str(output_file):
            Path(input_file).rename(output_file)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def inject_fake_metadata_to_image(image_path, output_path, fake_data):
    try:
        img = Image.open(image_path)
        pnginfo = PngImagePlugin.PngInfo()
        for key, value in fake_data.items():
            pnginfo.add_text(key, str(value))
        img.save(output_path, pnginfo=pnginfo)
        return True
    except Exception:
        return False

def inject_fake_metadata_to_video(video_path, output_path, fake_data):
    try:
        cmd = ['ffmpeg', '-y', '-i', str(video_path)]
        for key, value in fake_data.items():
            cmd.extend(['-metadata', f'{key}={value}'])
        cmd.extend(['-c', 'copy', str(output_path)])
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def get_metadata_with_exiftool(file_path):
    try:
        import json
        cmd = ['exiftool', '-j', str(file_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)[0]
        return metadata
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return None

def get_metadata_with_ffprobe(file_path):
    try:
        import json
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', str(file_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)
        return metadata
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return None

def export_to_csv(data, csv_path):
    try:
        valid_data = [item for item in data if item is not None and isinstance(item, dict)]
        if not valid_data:
            return False
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = valid_data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(valid_data)
        return True
    except Exception:
        return False

def main():
    djj.setup_terminal()
    
    while True:
        os.system('clear')
        print()
        print("\033[92m==================================================\033[0m")
        print("           \033[1;33m🔒 METADATA STRIPPER & INJECTOR 💉\033[0m")
        print("\033[92m==================================================\033[0m")
        print("Strip metadata and optionally inject fake data")
        print("\033[92m==================================================\033[0m")
        print()

        # Get input mode
        input_mode = djj.prompt_choice(
            "\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
            ['1', '2'],
            default='2'
        )
        print()

        # Ask for file type filter
        file_types = djj.prompt_choice(
            "\033[93mProcess which files?\033[0m\n1. Videos only\n2. Images only\n3. Audio only\n4. All media files\n",
            ['1', '2', '3', '4'],
            default='4'
        )
        file_type_filter = ['videos', 'images', 'audio', 'both'][int(file_types) - 1]
        print()

        media_files = []
        input_base_path = None

        if input_mode == '1':
            input_path = djj.get_path_input("📁 Enter folder path")
            input_base_path = input_path
            print()
            
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes, 2. No ",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            
            media_files = collect_and_select_files(input_path, include_sub, file_type_filter)
        else:
            file_paths = input("📁 \033[93mEnter file paths (space-separated): \n\033[0m -> ").strip()
            if not file_paths:
                print("❌ \033[93mNo file paths provided.\033[0m")
                continue
            
            media_files = collect_files_from_paths(file_paths, file_type_filter)
            if media_files:
                input_base_path = str(Path(media_files[0]).parent)
            print()

        if not media_files:
            print("❌ \033[93mNo valid media files selected. Try again.\033[0m\n")
            continue

        print(f"✅ \033[93m{len(media_files)} files selected for processing\033[0m")
        print()

        # Ask about metadata export first
        export_metadata = djj.prompt_choice(
            "\033[93mExport detailed metadata to CSV?\033[0m\n1. Yes\n2. No\n",
            ['1', '2'],
            default='2'
        ) == '1'
        print()

        # Export metadata if requested
        if export_metadata:
            print("📊 Extracting comprehensive metadata...")
            metadata_data = []
            
            for idx, file_path in enumerate(media_files, 1):
                display_name = os.path.basename(file_path)[:30] + "..." if len(os.path.basename(file_path)) > 30 else os.path.basename(file_path)
                sys.stdout.write(f"\r\033[93mExtracting metadata\033[0m {idx}\033[93m/\033[0m{len(media_files)}: {display_name}                    ")
                sys.stdout.flush()
                
                try:
                    file_type = get_file_type_by_extension(file_path)
                    comprehensive_data = {
                        'filename': Path(file_path).name,
                        'extension': Path(file_path).suffix.lower(),
                        'file_type': file_type,
                        'full_path': str(file_path),
                        'file_size_mb': round(Path(file_path).stat().st_size / (1024 * 1024), 2)
                    }
                    
                    # Get metadata
                    if file_type == 'Video':
                        ffprobe_data = get_metadata_with_ffprobe(file_path)
                        if ffprobe_data and 'format' in ffprobe_data:
                            format_info = ffprobe_data['format']
                            tags = format_info.get('tags', {})
                            comprehensive_data.update({
                                'duration': format_info.get('duration', ''),
                                'bitrate': format_info.get('bit_rate', ''),
                                'title': tags.get('title', ''),
                                'artist': tags.get('artist', ''),
                                'encoder': tags.get('encoder', '')
                            })
                    else:
                        exif_data = get_metadata_with_exiftool(file_path)
                        if exif_data:
                            comprehensive_data.update({
                                'make': exif_data.get('Make', ''),
                                'model': exif_data.get('Model', ''),
                                'software': exif_data.get('Software', ''),
                                'artist': exif_data.get('Artist', ''),
                                'copyright': exif_data.get('Copyright', ''),
                                'create_date': exif_data.get('CreateDate', '')
                            })
                    
                    metadata_data.append(comprehensive_data)
                except Exception:
                    metadata_data.append({
                        'filename': Path(file_path).name,
                        'error': 'Failed to extract metadata'
                    })
            
            sys.stdout.write(f"\r{' ' * 80}\r")
            sys.stdout.flush()
            
            if metadata_data:
                csv_filename = f"metadata_export_{time.strftime('%Y%m%d_%H%M%S')}.csv"
                csv_path = Path(input_base_path) / csv_filename
                
                if export_to_csv(metadata_data, csv_path):
                    print(f"✅ \033[93mMetadata exported to:\033[0m {csv_path}")
                    print()

        # Processing workflow
        workflow = djj.prompt_choice(
            "\033[93mProcessing workflow:\033[0m\n1. Strip metadata, then inject fake\n2. Only inject fake (don't strip)\n3. Only strip metadata\n",
            ['1', '2', '3'],
            default='1'
        )
        print()

        replace_mode = djj.prompt_choice(
            "\033[93mFile handling:\033[0m\n1. Replace original files\n2. Create new files\n",
            ['1', '2'],
            default='2'
        ) == '1'
        print()

        if workflow in ['1', '3']:
            method = djj.prompt_choice(
                "\033[93mMetadata removal method:\033[0m\n1. FFmpeg\n2. ExifTool\n",
                ['1', '2'],
                default='1'
            )
            method_name = 'ffmpeg' if method == '1' else 'exiftool'
            print()

        # Process files
        print("🔄 Processing files...")
        print("-------------")

        successful = 0
        failed = []
        processed_files = []

        for idx, file_path in enumerate(media_files, 1):
            display_name = os.path.basename(file_path)[:30] + "..." if len(os.path.basename(file_path)) > 30 else os.path.basename(file_path)
            sys.stdout.write(f"\r\033[93mProcessing\033[0m {idx}\033[93m/\033[0m{len(media_files)}: {display_name}                    ")
            sys.stdout.flush()
            
            try:
                input_file = Path(file_path)
                
                if replace_mode:
                    # Process in place
                    if workflow == '2':  # Only inject fake
                        file_type = get_file_type_by_extension(file_path)
                        fake_data = generate_fake_metadata(file_type)
                        
                        if file_type == 'Image' and file_path.lower().endswith('.png'):
                            success = inject_fake_metadata_to_image(str(input_file), str(input_file), fake_data)
                        elif file_type == 'Video':
                            temp_file = input_file.with_suffix('.tmp')
                            success = inject_fake_metadata_to_video(str(input_file), str(temp_file), fake_data)
                            if success and temp_file.exists():
                                temp_file.replace(input_file)
                        else:
                            success = False
                    else:  # Strip (with or without injection later)
                        temp_file = input_file.with_suffix('.tmp')
                        if method_name == 'ffmpeg':
                            success = run_ffmpeg_strip(str(input_file), str(temp_file))
                        else:
                            success = run_exiftool_strip(str(input_file), str(temp_file))
                        if success and temp_file.exists():
                            temp_file.replace(input_file)
                    
                    if success:
                        successful += 1
                        processed_files.append(str(input_file))
                else:
                    # Create new files
                    file_parent = input_file.parent
                    
                    if workflow == '1':
                        output_dir = file_parent / "Output" / "stripped_fake_injected"
                        suffix = "_clean_fake"
                    elif workflow == '2':
                        output_dir = file_parent / "Output" / "fake_injected"
                        suffix = "_fake"
                    else:
                        output_dir = file_parent / "Output" / "stripped"
                        suffix = "_clean"
                    
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_file = output_dir / f"{input_file.stem}{suffix}{input_file.suffix}"
                    
                    import shutil
                    shutil.copy2(str(input_file), str(output_file))
                    
                    if workflow == '2':  # Only inject fake
                        file_type = get_file_type_by_extension(file_path)
                        fake_data = generate_fake_metadata(file_type)
                        
                        if file_type == 'Image' and file_path.lower().endswith('.png'):
                            success = inject_fake_metadata_to_image(str(output_file), str(output_file), fake_data)
                        elif file_type == 'Video':
                            temp_file = output_file.with_suffix('.tmp')
                            success = inject_fake_metadata_to_video(str(output_file), str(temp_file), fake_data)
                            if success and temp_file.exists():
                                temp_file.replace(output_file)
                        else:
                            success = True
                    else:  # Strip metadata
                        if method_name == 'ffmpeg':
                            success = run_ffmpeg_strip(str(output_file), str(output_file))
                        else:
                            success = run_exiftool_strip(str(output_file), str(output_file))
                    
                    if success:
                        successful += 1
                        processed_files.append(str(output_file))
                        
            except Exception as e:
                failed.append((os.path.basename(file_path), str(e)))

        sys.stdout.write(f"\r{' ' * 80}\r")
        sys.stdout.flush()

        # Inject fake metadata if workflow 1 (strip + inject)
        if workflow == '1' and processed_files:
            print()
            print("💉 Injecting fake metadata...")
            
            fake_success = 0
            for idx, file_path in enumerate(processed_files, 1):
                display_name = os.path.basename(file_path)[:30] + "..." if len(os.path.basename(file_path)) > 30 else os.path.basename(file_path)
                sys.stdout.write(f"\r\033[93mInjecting\033[0m {idx}\033[93m/\033[0m{len(processed_files)}: {display_name}                    ")
                sys.stdout.flush()
                
                try:
                    file_type = get_file_type_by_extension(file_path)
                    fake_data = generate_fake_metadata(file_type)
                    
                    if file_type == 'Image' and file_path.lower().endswith('.png'):
                        success = inject_fake_metadata_to_image(file_path, file_path, fake_data)
                    elif file_type == 'Video':
                        temp_file = str(Path(file_path).with_suffix('.tmp'))
                        success = inject_fake_metadata_to_video(file_path, temp_file, fake_data)
                        if success and Path(temp_file).exists():
                            Path(temp_file).replace(file_path)
                    else:
                        continue
                    
                    if success:
                        fake_success += 1
                except Exception:
                    pass
            
            sys.stdout.write(f"\r{' ' * 80}\r")
            sys.stdout.flush()
            print(f"✅ Fake metadata injected: {fake_success} files")

        print()
        print(f"✅ \033[93mProcessing complete:\033[0m {successful} files processed")
        if failed:
            print(f"❌ \033[93mFailed:\033[0m {len(failed)} files")

        # Show output location
        if not replace_mode and input_base_path:
            workflow_names = ["stripped_fake_injected", "fake_injected", "stripped"]
            output_base = Path(input_base_path) / "Output" / workflow_names[int(workflow) - 1]
            
            if output_base.exists():
                print(f"\n📁 \033[93mOutput folder:\033[0m\n{output_base}")
                
                open_folder = djj.prompt_choice(
                    "\033[93mOpen output folder?\033[0m\n1. Yes\n2. No\n",
                    ['1', '2'],
                    default='1'
                ) == '1'
                
                if open_folder:
                    subprocess.run(['open', str(output_base)])

        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()