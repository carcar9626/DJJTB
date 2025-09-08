#!/usr/bin/env python3

import subprocess
import json
import time
import os
import pathlib
from datetime import datetime
from djjtb.utils import PathManager, print_error

def load_paths():
    """Load centralized input/output paths from temp JSON"""
    try:
        with open("/tmp/djjtb_paths.json") as f:
            data = json.load(f)
        input_files = data.get("inputs", [])
        if not input_files:
            raise ValueError("No input files found in path data.")
        output_path = data.get("output")
        if not output_path:
            raise ValueError("No output path found in path data.")
        return input_files, output_path
    except Exception as e:
        print_error(f"[Path Load Error] {e}")
        exit(1)

def run_cropdetect(video_path):
    """Run ffmpeg cropdetect to estimate crop values"""
    try:
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", "cropdetect=24:16:0",
            "-frames:v", "20",
            "-f", "null", "-"
        ]
        result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        crop_lines = [line for line in result.stderr.splitlines() if "crop=" in line]
        crop_values = sorted(set(line.split("crop=")[-1] for line in crop_lines))
        return crop_values
    except Exception as e:
        print_error(f"[Cropdetect Error] {e}")
        return []

def crop_video(input_file, crop_value, output_folder):
    """Apply crop to a video using given crop value"""
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = pathlib.Path(input_file).stem
        ext = pathlib.Path(input_file).suffix
        out_path = pathlib.Path(output_folder) / f"{filename}_cropped_{ts}{ext}"
        
        cmd = [
            "ffmpeg", "-i", input_file,
            "-vf", f"crop={crop_value}",
            "-c:a", "copy",  # preserve original audio
            str(out_path)
        ]
        subprocess.run(cmd)
        print(f"✅ Cropped saved to: {out_path}")
    except Exception as e:
        print_error(f"[Crop Error] {e}")

def main():
    input_files, _ = load_paths()
# Derive per-input output dir: [input parent]/Output/video_cropper
    input_path_obj = pathlib.Path(input_files[0])  # just grab one to get parent
    output_dir = (
        input_path_obj.parent
        / "Output"
        / "Cropped"
)
output_dir.mkdir(parents=True, exist_ok=True)
    
    for file in input_files:
        print(f"\n🔍 Analyzing: {file}")
        crop_values = run_cropdetect(file)
        
        if not crop_values:
            print_error("No crop values detected. Skipping file.")
            continue
        
        # Always use first suggested crop value (beta logic)
        selected_crop = crop_values[0]
        print(f"👉 Using crop: {selected_crop}")
        crop_video(file, selected_crop, output_dir)

if __name__ == "__main__":
    main()