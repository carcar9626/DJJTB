import os
import shutil
from pathlib import Path

# 🔧 Set your video folder path here
video_folder = Path("/Users/home/Documents/2025/SC/Upskirt/TGUS_0703_HK")

# Create folders and move files
for file in video_folder.iterdir():
    if file.is_file() and file.suffix.lower() in [".mp4", ".mkv", ".mov", ".avi"]:
        prefix = file.name[:2]
        if prefix.isdigit():
            dest_folder = video_folder / prefix
            dest_folder.mkdir(exist_ok=True)
            target_path = dest_folder / file.name
            print(f"📦 Moving: {file.name} → {dest_folder}/")
            shutil.move(str(file), str(target_path))

print("✅ Done.")