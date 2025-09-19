#!/usr/bin/env python3

import os
import csv
import datetime
from pathlib import Path
from typing import List, Tuple
from djjtb import utils as djj
from moviepy.editor import VideoFileClip
from PIL import Image

os.system('clear')

def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def collect_media_files(folder: Path, include_sub: bool) -> List[Path]:
    exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}
    if include_sub:
        return [p for p in folder.rglob('*') if p.suffix.lower() in exts]
    else:
        return [p for p in folder.glob('*') if p.suffix.lower() in exts]

def get_media_info(file_path: Path) -> Tuple[str, str, str, str, str, str, str]:
    filename = file_path.name
    filepath = str(file_path)
    ext = file_path.suffix.lower()
    duration = ""
    dimensions = ""
    fps = ""
    dpi = ""

    try:
        if ext in {'.mp4', '.mov', '.avi', '.mkv', '.webm'}:
            clip = VideoFileClip(str(file_path))
            duration = format_duration(clip.duration)
            dimensions = f"{clip.w}x{clip.h}"
            fps = f"{clip.fps:.2f}"
            clip.close()
        elif ext in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}:
            with Image.open(file_path) as img:
                dimensions = f"{img.width}x{img.height}"
                dpi_tuple = img.info.get('dpi')
                if dpi_tuple:
                    dpi = str(dpi_tuple[0])
    except Exception as e:
        print(f"\033[91mError processing {file_path.name}:\033[0m {e}")

    return filename, filepath, ext, duration, dimensions, fps, dpi

def get_output_dir(mode: str, input_paths: List[Path]) -> Path:
    today = datetime.datetime.now().strftime("%Y%b%d")

    if mode == '1':
        out_dir = Path("/Users/home/Documents/Scripts/DJJTB_output/video_info_extractor")
    elif mode == '2':
        base = input_paths[0].parent if input_paths[0].is_file() else input_paths[0]
        out_dir = base / "Output" / "media_info_extractor"
    else:
        out_dir = djj.get_path_input("Enter custom output folder")

    out_dir.mkdir(parents=True, exist_ok=True)

    base_name = f"{today}.csv"
    output_file = out_dir / base_name

    if output_file.exists():
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        output_file = out_dir / f"{today}_{timestamp}.csv"

    return output_file

def main():
    while True:
        print("\033[92m==================================================\033[0m")
        print("\033[1;93m🛠️  Media Info Extractor\033[0m")
        print("Extract info from Images and Videos")
        print("\033[92m==================================================\033[0m")

        input_mode = djj.prompt_choice(
            "\033[93mSource input mode:\033[0m\n1. Folder Mode\n2. Space-separated file paths",
            ['1', '2'],
            default='1'
        )
        print()
        # --- New media type prompt ---
        mode = djj.prompt_choice(
            "\033[93mMedia type:\033[0m\n1. Images only\n2. Videos only\n3. Both",
            ['1', '2', '3'],
            default='3'
        )
        print()
        mode = {"1": "images", "2": "videos", "3": "both"}.get(mode)
        print(f"\033[93mSelected media type: {mode}\033[0m\n")
        print()

        input_paths = []
        include_sub = False
        
        if input_mode == '1':
            # Folder mode
            src_path = djj.get_path_input("Enter source folder path")
            print()
        
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
        
            input_paths = collect_media_files(Path(src_path), include_sub)
        
        else:
            # File paths mode — one path per line
            print()
            print("\033[93mEnter file paths, one per line. Leave empty line to finish:\033[0m")
            while True:
                line = input("\033[5;93m❯\033[0m ").strip()
                if not line:
                    break
                p = Path(line)
                if p.exists():
                    input_paths.append(p)
                else:
                    print(f"❌ Path does not exist: {line}")
            print()

        if not input_paths:
            print("\033[91m❌ No valid media files found.\033[0m")
            continue

        # --- Filter by media type ---
        if mode == "images":
            input_paths = [p for p in input_paths if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}]
        elif mode == "videos":
            input_paths = [p for p in input_paths if p.suffix.lower() in {'.mp4', '.mov', '.avi', '.mkv', '.webm'}]

        if not input_paths:
            print(f"\033[91m❌ No {mode} found after filtering.\033[0m")
            continue

        # Confirm before executing
        print("\033[92m✅ Ready to process the following files:\033[0m")
        for p in input_paths:
            print(f" - {p}")
        print(f"\n\033[93mTotal: {len(input_paths)} files\033[0m\n")

        output_mode = djj.prompt_choice(
            "\033[93mChoose output folder mode:\033[0m\n1. Default location\n2. Output folder near input\n3. Custom path",
            ['1', '2', '3'],
            default='1'
        )
        print()

        output_file = get_output_dir(output_mode, input_paths)

        print(f"\033[94mOutput CSV will be saved to:\033[0m {output_file}\n")

        proceed = djj.prompt_choice("\033[5;92mProceed with extraction?\033[0m\n 1.Yes 2. No", ['1', '2'], default='1')
        print()

        if proceed != '1':
            print("\033[91m❌ Aborted by user.\033[0m")
            continue

        # Start processing
        rows = []
        for path in input_paths:
            info = get_media_info(Path(path))
            rows.append(info)

        with open(output_file, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Filename", "Filepath", "Extension", "Duration", "Dimensions", "FPS", "DPI"])
            writer.writerows(rows)

        print(f"\n\033[92m✅ Done. CSV saved to:\033[0m {output_file}")

        djj.prompt_open_folder(output_file.parent)

        action = djj.what_next()
        if action == 'exit':
            break
        elif action == 'continue':
            continue

if __name__ == "__main__":
    main()