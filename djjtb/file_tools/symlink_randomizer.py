#!/usr/bin/env python3
import os
import random
from pathlib import Path

# Folder containing your symlinks
symlink_folder = Path("/Volumes/Movies_2SSD/UD_Gens/Characters/OG/OG_Process/PZZO/movies")

# Get all symlinks in folder
symlinks = [f for f in symlink_folder.iterdir() if f.is_symlink()]

# Shuffle randomly
random.shuffle(symlinks)

# Naming parameters
start = 10000
step = 9
padding = 5

for i, symlink in enumerate(symlinks):
    new_name = f"{start + i * step:0{padding}d}{symlink.suffix}"
    new_path = symlink_folder / new_name
    symlink.rename(new_path)

print(f"Renamed {len(symlinks)} symlinks successfully.")