#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import webbrowser
from PIL import Image
from pathlib import Path
from collections import defaultdict
import traceback
import djjtb.utils as djj

os.system('clear')

# Supported file types
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv"}

# Aspect ratio categories: (lower_bound, upper_bound, suffix)
CATEGORIES = {
    "Landscape_16_9": (1.68, 1.83, "_169"),
    "Portrait_9_16":  (0.50, 0.64, "_916"),
    "Landscape_4_3":  (1.28, 1.44, "_L43"),
    "Portrait_3_4":   (0.70, 0.88, "_P34"),
    "Landscape_3_2":  (1.45, 1.52, "_L32"),
    "Portrait_2_3":   (0.65, 0.69, "_P23"),
    "Square":         (0.98, 1.08, "_SQR"),
}

SUFFIX_TO_TAG = {
    "_169": "169",
    "_916": "916",
    "_L43": "L43",
    "_P34": "P34",
    "_L32": "L32",
    "_P23": "P23",
    "_SQR": "SQR",
    "_LX": "LX",
    "_PX": "PX"
    # No tagging for USL, USP, and _unsorted
}

TAG_PATH = "/opt/homebrew/bin/tag"

def tag_file(file_path, tag_name):
    """Add Finder tag to source files"""
    try:
        subprocess.run([TAG_PATH, "-a", tag_name, str(file_path)], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Failed to tag {os.path.basename(file_path)}: {e}")

def get_aspect_category(width, height):
    if not width or not height:
        return "Unsorted", "_unsorted"

    ratio = width / height

    # 1) Extreme cases first
    if ratio > 2.1:
        return "Extreme_Landscape", "_LX"
    elif ratio < 0.48:
        return "Extreme_Portrait", "_PX"

    # 2) Standard categories
    for category, (low, high, suffix) in CATEGORIES.items():
        if low <= ratio <= high:
            return category, suffix

    # 3) Unsorted landscape or portrait (between extremes and standard categories)
    if width > height:
        return "Unsorted_Landscape", "_USL"
    else:
        return "Unsorted_Portrait", "_USP"

def get_video_resolution(file_path):
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0", str(file_path)
        ], capture_output=True, text=True, timeout=2)

        output = result.stdout.strip()
        if not output:
            print(f"⚠️ ffprobe gave empty output: {file_path}")
            return None, None

        # Clean up output like "2560x1118x" or "2560x1118x\n"
        cleaned = output.strip().rstrip("x").strip()

        parts = cleaned.split("x")
        if len(parts) == 2:
            try:
                width = int(parts[0])
                height = int(parts[1])
                return width, height
            except ValueError:
                print(f"❌ Failed to parse resolution: {output} for {file_path}")
                return None, None
        else:
            print(f"❌ Unexpected ffprobe format: {output} for {file_path}")
            return None, None

    except subprocess.TimeoutExpired:
        print(f"⏱️ ffprobe timeout: {file_path}")
        return None, None
    except Exception as e:
        print(f"❌ ffprobe error on {file_path}: {e}")
        return None, None
        
def get_image_resolution(file_path):
    try:
        with Image.open(file_path) as img:
            return img.width, img.height
    except Exception:
        return None, None

def safe_rename_only(file_path, suffix):
    parent = file_path.parent
    base = file_path.stem
    ext = file_path.suffix
    new_name = f"{base}{suffix}{ext}"
    new_path = parent / new_name
    counter = 1
    while new_path.exists():
        new_name = f"{base}{suffix}({counter}){ext}"
        new_path = parent / new_name
        counter += 1
    file_path.rename(new_path)

def safe_move_and_rename(file_path, output_dir, suffix):
    output_dir.mkdir(parents=True, exist_ok=True)
    base = file_path.stem
    ext = file_path.suffix
    new_name = f"{base}{suffix}{ext}"
    new_path = output_dir / new_name
    counter = 1
    while new_path.exists():
        new_name = f"{base}{suffix}({counter}){ext}"
        new_path = output_dir / new_name
        counter += 1
    shutil.move(str(file_path), str(new_path))

def safe_move_only(file_path, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    base = file_path.stem
    ext = file_path.suffix
    new_name = f"{base}{ext}"
    new_path = output_dir / new_name
    counter = 1
    while new_path.exists():
        new_name = f"{base}({counter}){ext}"
        new_path = output_dir / new_name
        counter += 1
    shutil.move(str(file_path), str(new_path))

def reverse_suffix_files(files_to_process):
    """Remove suffixes from filenames (reverse of adding suffixes)"""
    summary = defaultdict(int)
    skipped = []
    
    # All possible suffixes to remove
    all_suffixes = list(SUFFIX_TO_TAG.keys()) + ["_USL", "_USP", "_unsorted", "_LX", "_PX"]
    
    total = len(files_to_process)
    for i, file_path in enumerate(files_to_process):
        percent = (i + 1) / total * 100
        print(f"\rRemoving suffixes {i+1}/{total} ({percent:.1f}%)...    ", end="", flush=True)
        
        try:
            stem = file_path.stem
            ext = file_path.suffix
            original_name = stem
            
            # Check if file has any suffix to remove (last 4-15 characters)
            suffix_removed = None
            for suffix in all_suffixes:
                if len(suffix) >= 3 and stem.endswith(suffix):
                    new_stem = stem[:-len(suffix)]  # Remove the suffix
                    suffix_removed = suffix
                    break
            
            if suffix_removed:
                # Create new filename without suffix
                new_name = f"{new_stem}{ext}"
                new_path = file_path.parent / new_name
                
                # Handle duplicates
                counter = 1
                while new_path.exists():
                    new_name = f"{new_stem}({counter}){ext}"
                    new_path = file_path.parent / new_name
                    counter += 1
                
                # Rename the file
                file_path.rename(new_path)
                summary[f"Removed {suffix_removed}"] += 1
                
            else:
                skipped.append((file_path, "no recognized suffix found"))
                
        except Exception as e:
            print(f"  ❌ Error processing {file_path.name}: {e}")
            skipped.append((file_path, str(e)))
    
    print("\n📊 Reverse Suffix Summary:")
    for action, count in summary.items():
        print(f"  {action}: {count} file(s)")
    
    if skipped:
        print("\n⚠️ Skipped Files:")
        for f, reason in skipped:
            print(f"  - {f.name} ({reason})")
    
    return summary

def get_media_files_from_input():
    """Get media files using the reference script's input method"""
    print("\033[92m=== MEDIA SORTER - INPUT SELECTION ===\033[0m")
    
    input_mode = djj.prompt_choice(
        "\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
        ['1', '2'],
        default='1'
    )
    
    media_files = []
    root_folder = None
    
    if input_mode == '1':
        # Single folder path
        folder_path = djj.get_path_input("Enter folder path")
        root_folder = Path(folder_path)
        
        include_subfolders = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        
        # Collect files from folder
        for dirpath, _, filenames in os.walk(folder_path):
            current_folder = Path(dirpath)
            for file in filenames:
                file_path = current_folder / file
                ext = file_path.suffix.lower()
                if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
                    media_files.append(file_path)
            if not include_subfolders:
                break
                
    else:
        # Multiple file paths
        print(f"\033[93mEnter file paths (space-separated):\033[0m")
        paths_input = input(" > ").strip()
        if paths_input:
            for path_str in paths_input.split():
                path_str = path_str.strip('\'"')
                try:
                    path = Path(path_str).expanduser().resolve()
                    if path.exists():
                        if path.is_file():
                            ext = path.suffix.lower()
                            if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
                                media_files.append(path)
                        elif path.is_dir():
                            # Collect files from this directory
                            for file in path.iterdir():
                                if file.is_file():
                                    ext = file.suffix.lower()
                                    if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
                                        media_files.append(file)
                    else:
                        print(f"\033[93m Warning: Path '{path}' does not exist.\033[0m")
                except Exception as e:
                    print(f"\033[93m Error resolving path '{path_str}': {e}\033[0m")
        
        # For multi-file mode, use the parent of the first file as root folder
        if media_files:
            root_folder = media_files[0].parent
    
    if not media_files:
        print("\033[93m No valid media files found!\033[0m")
        return [], None
    
    print(f"\033[92m✓ Found {len(media_files)} media file(s)\033[0m")
    for i, file in enumerate(media_files[:5]):  # Show first 5
        print(f"  {i+1}. {file.name}")
    if len(media_files) > 5:
        print(f"  ... and {len(media_files) - 5} more")
    
    return media_files, root_folder
        
def process_media(files_to_process, root_folder, mode, move_files, move_only=False, add_finder_tags=False, tag_only=False):
    summary = defaultdict(int)
    skipped = []
    tagged_count = 0

    total = len(files_to_process)
    for i, file_path in enumerate(files_to_process):
        percent = (i + 1) / total * 100
        print(f"\rSorting files {i+1}/{total}  ({percent:.1f}%)...    ", end="", flush=True)

        try:
            ext = file_path.suffix.lower()
            parent = file_path.parent
            width = height = None

            # Skip files that don't match the selected mode
            if mode == "images" and ext not in IMAGE_EXTS:
                continue
            elif mode == "videos" and ext not in VIDEO_EXTS:
                continue
            elif mode == "both" and ext not in IMAGE_EXTS and ext not in VIDEO_EXTS:
                continue

            if ext in IMAGE_EXTS:
                width, height = get_image_resolution(file_path)
            elif ext in VIDEO_EXTS:
                width, height = get_video_resolution(file_path)

            if not width or not height:
                print(f"  ⚠️ Skipping (couldn't get resolution): {file_path.name}")
                skipped.append((file_path, "resolution not found"))
                continue

            category, suffix = get_aspect_category(width, height)
            if not category:
                print(f"  ⚠️ Skipping (no matching category): {file_path.name}")
                skipped.append((file_path, "no category"))
                continue

            summary[category] += 1

            if tag_only:
                # Tag only mode - just tag the file without moving or renaming
                if suffix in SUFFIX_TO_TAG:
                    tagged_count += 1
                    print(f"\rTagging files {tagged_count} {percent:.1f}%)......    ", end="", flush=True)
                    tag_file(file_path, SUFFIX_TO_TAG[suffix])
                final_path = file_path
            elif move_files:
                output_dir = parent / category
                if move_only:
                    safe_move_only(file_path, output_dir)
                    final_path = output_dir / file_path.name
                else:
                    safe_move_and_rename(file_path, output_dir, suffix)
                    final_path = output_dir / f"{file_path.stem}{suffix}{file_path.suffix}"
            else:
                # Check if already has the suffix in the last 4-7 characters before extension
                stem = file_path.stem
                already_has_suffix = False
                
                # Check for suffixes of length 4-7 characters at the end of filename
                for check_suffix in [suffix] + list(SUFFIX_TO_TAG.keys()) + ["_USL", "_USP", "_unsorted"]:
                    if len(check_suffix) >= 4 and len(check_suffix) <= 7:
                        if stem.endswith(check_suffix):
                            already_has_suffix = True
                            break
                
                if not already_has_suffix:
                    safe_rename_only(file_path, suffix)
                    final_path = file_path.with_name(f"{file_path.stem}{suffix}{file_path.suffix}")
                else:
                    final_path = file_path  # already renamed, just set final_path for tagging
                    
            # Only tag files that have tags defined (no tagging for USL, USP, _unsorted)
            if add_finder_tags and suffix in SUFFIX_TO_TAG:
                tagged_count += 1
                print(f"\rTagging files {tagged_count}...    ", end="", flush=True)
                tag_file(final_path, SUFFIX_TO_TAG[suffix])
                
        except Exception as e:
            print(f"  ❌ Error processing {file_path.name}: {e}")
            traceback.print_exc()
            skipped.append((file_path, str(e)))

    print("\n📊 Sort Summary:")
    for category, count in summary.items():
        print(f"  {category}: {count} file(s)")

    if skipped:
        print("\n⚠️ Skipped Files:")
        for f, reason in skipped:
            print(f"  - {f} ({reason})")

    # Use the reference script's open folder handling
    if root_folder:
        djj.prompt_open_folder(root_folder)
    return summary
    
def main():
    print()
    print()
    print("\033[92m==================================================\033[0m")
    print("            \033[1;93mMedia Sorter\033[0m")
    print("   Sorts media files by tagging,")
    print("       subfolders, renaming")
    print("\033[92m==================================================\033[0m")
    
    while True:
        # Get media files using the new input method
        files_to_process, root_folder = get_media_files_from_input()
        
        if not files_to_process:
            print("❌ No files to process. Try again.")
            continue

        print("\n📦 What type of media do you want to sort?")
        mode = djj.prompt_choice(
            "\033[93mMedia type:\033[0m\n1. Images only\n2. Videos only\n3. Both",
            ['1', '2', '3'],
            default='3'
        )
        mode = {"1": "images", "2": "videos", "3": "both"}.get(mode)

        print("\n🧾 What do you want to do with the sorted files?")
        action = djj.prompt_choice(
            "\033[93mAction:\033[0m\n1. Rename with Suffix Only\n2. Move Subfolders and Rename\n3. Move to Subfolders Only\n4. Tag Only\n5. Remove Suffixes (Reverse)",
            ['1', '2', '3', '4', '5'],
            default='1'
        )
        
        if action == '5':
            # Reverse suffix mode
            os.system('clear')
            print(f"\n\033[1;93m🔄 Removing suffixes from {len(files_to_process)} file(s)...\033[0m")
            reverse_suffix_files(files_to_process)
            
            # Use the reference script's open folder handling
            if root_folder:
                djj.prompt_open_folder(root_folder)
                
            # Use the reference script's "what next" handling
            action = djj.what_next()
            if action == 'exit':
                break
            else:
                continue
        
        move_files = action in ("2", "3")
        move_only = action == "3"
        tag_only = action == "4"
        
        # Only ask about tags if not using tag-only mode
        add_finder_tags = False
        if not tag_only:
            add_finder_tags = djj.prompt_choice(
                "\033[93mAdd Finder tags to sorted files?\033[0m\n1. Yes\n2. No",
                ['1', '2'],
                default='1'
            ) == '1'
        else:
            add_finder_tags = True  # Always tag in tag-only mode

        os.system('clear')
        print(f"\n\033[1;93m📁 Processing {len(files_to_process)} file(s)...\033[0m")
        
        process_media(files_to_process, root_folder, mode, move_files, move_only, add_finder_tags, tag_only)

        # Use the reference script's "what next" handling
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()