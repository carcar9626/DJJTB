import os
import shutil
import subprocess
import sys
import webbrowser
from PIL import Image
from pathlib import Path
from collections import defaultdict
import traceback

os.system('clear')

# Supported file types
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv"}

# Aspect ratio categories: (lower_bound, upper_bound, suffix)
CATEGORIES = {
    "Landscape_16_9": (1.71, 1.81, "_169"),
    "Portrait_9_16":  (0.54, 0.60, "_916"),
    "Landscape_4_3":  (1.30, 1.36, "_L43"),
    "Portrait_3_4":   (0.73, 0.78, "_P34"),
    "Landscape_3_2":  (1.48, 1.52, "_L32"),
    "Portrait_2_3":   (0.66, 0.68, "_P23"),
    "Square":         (0.98, 1.02, "_SQR"),
}

SUFFIX_TO_TAG = {
    "_169": "169",
    "_916": "916",
    "_L43": "L43",
    "_P43": "P43",
    "_L32": "L32",
    "_P23": "P23",
    "_SQR": "SQR",
}

TAG_PATH = shutil.which("tag") or "/usr/local/bin/tag"  # fallback

def tag_file(file_path, tag_label):
    try:
        subprocess.run([TAG_PATH, "-a", tag_label, str(file_path)], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"\n⚠️ Failed to tag file: {file_path} — {e}")  # Keep error messages

def get_aspect_category(width, height):
    if not width or not height:
        return "Unsorted", "_UNSORTED"

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
        return "Unsorted/Landscape", "_USL"
    else:
        return "Unsorted/Portrait", "_USP"

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
        
def process_media(root_path, mode, include_subfolders, move_files, move_only=False, add_finder_tags=False, tag_only=False):
    root_path = Path(root_path)
    summary = defaultdict(int)
    skipped = []
    tagged_count = 0

    files_to_process = []
    for dirpath, _, filenames in os.walk(root_path):
        current_folder = Path(dirpath)
        for file in filenames:
            file_path = current_folder / file
            ext = file_path.suffix.lower()
            if ((mode in ["images", "both"] and ext in IMAGE_EXTS) or
                (mode in ["videos", "both"] and ext in VIDEO_EXTS)):
                files_to_process.append(file_path)
        if not include_subfolders:
            break

    total = len(files_to_process)
    for i, file_path in enumerate(files_to_process):
        percent = (i + 1) / total * 100
        print(f"\rSorting files {i+1}/{total} ({percent:.1f}%)...    ", end="", flush=True)

        try:
            ext = file_path.suffix.lower()
            parent = file_path.parent
            width = height = None

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
                    print(f"\rTagging files {tagged_count}...    ", end="", flush=True)
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
                 # Skip if already has the suffix
                if not file_path.stem.endswith(suffix):
                    safe_rename_only(file_path, suffix)
                    final_path = file_path.with_name(f"{file_path.stem}{suffix}{file_path.suffix}")
                else:
                    final_path = file_path  # already renamed, just set final_path for tagging
                    
            # Only tag files that have tags defined (no tagging for unsorted files)
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

    webbrowser.open(f"file://{root_path}")
    return summary
    
def main():
    print()
    print()
    print("\033[92m===================================\033[0m")
    print("            \033[1;33mMedia Sorter\033[0m")
    print("   Sorts media files by tagging,")
    print("       subfolders, renaming")
    print("\033[92m===================================\033[0m")
    while True:
        print("\n📁 Enter folder path: \n -> ")
        folder = input("> ").strip()
        if not os.path.isdir(folder):
            print("❌ Not a valid folder. Try again.")
            continue

        print("\n📦 What type of media do you want to sort?")
        print("1. Images only, 2. Videos only,  3. Both : ")
        choice = input("> ").strip()
        mode = {"1": "images", "2": "videos", "3": "both"}.get(choice)
        if not mode:
            print("❌ Invalid choice. Try again.")
            continue

        print("\n🗂️ Include subfolders?")
        print("  1. Yes,  2. No: ")
        sub = input("> ").strip()
        include_subfolders = sub == "1"

        print("\n🧾 What do you want to do with the sorted files?")
        print("  1. Rename with Suffix Only")
        print("  2. Move Subfolders and Rename")
        print("  3. Move to Subfolders Only")
        print("  4. Tag Only")
        action = input("> ").strip()
        move_files = action in ("2", "3")
        move_only = action == "3"
        tag_only = action == "4"
        
        # Only ask about tags if not using tag-only mode
        add_finder_tags = False
        if not tag_only:
            print("\n🏷️  Add Finder tags to sorted files?")
            print("  1. Yes,  2. No: ")
            tag_choice = input("> ").strip()
            add_finder_tags = tag_choice == "1"
        else:
            add_finder_tags = True  # Always tag in tag-only mode

        process_media(folder, mode, include_subfolders, move_files, move_only, add_finder_tags, tag_only)

        print("\n🔁 Go again?")
        print("  1. Yes\n  2. No")
        again = input("> ").strip()
        if again != "1":
            print("👋 Done.")
            break

if __name__ == "__main__":
    main()