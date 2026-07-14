#!/usr/bin/env python3
"""
DJJTB - Automated Mask Generation Engine
Category: ai_tools
Description: Reads Gemini spatial layout JSON data and compiles a pixel-perfect
             black-and-white inpainting mask matching the source dimensions.
"""

import json
import argparse
from pathlib import Path
from PIL import Image, ImageDraw

def generate_binary_mask(json_path: Path):
    # Parse existing structural JSON payload
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    source_img_path = Path(data["meta"]["source_image_path"])
    if not source_img_path.exists():
        raise FileNotFoundError(f"Missing referenced source image graphic: {source_img_path}")

    # Open image to query native, unscaled pixel boundaries (e.g., 819x1024)
    with Image.open(source_img_path) as img:
        width, height = img.size

    # Initialize a pristine, solid black background canvas matching the true aspect ratio
    mask_canvas = Image.new("L", (width, height), 0) # "L" mode handles pure 8-bit grayscale black
    draw = ImageDraw.Draw(mask_canvas)

    print(f"[MASK ENGINE] Generating canvas layout template ({width}x{height}) for: {source_img_path.name}...")

    # 1. OPTIONAL: Mask out the main top header zone completely
    # The top 12% of the vertical space typically houses the overarching category label
    header_clearance_height = int(120 * (height / 1000))
    draw.rectangle([0, 0, width, header_clearance_height], fill=255) # 255 represents pure white

    # 2. LOOP MATRIX AND STAMP WHITE BOXES ONTO WORKSPACE
    for item in data["items"]:
        ymin, xmin, ymax, xmax = item["text_bbox"]

        # Scale normalized 0-1000 coordinates to actual pixel dimensions
        t_left = int(xmin * (width / 1000))
        t_right = int(xmax * (width / 1000))
        t_top = int(ymin * (height / 1000))
        t_bottom = int(ymax * (height / 1000))

        # Add a slight padding safety margin to guarantee full text boundary capture
        padding_x = 12
        padding_y = 6

        wipe_left = max(0, t_left - padding_x)
        wipe_right = min(width, t_right + padding_x)
        wipe_top = max(0, t_top - padding_y)
        wipe_bottom = min(height, t_bottom + padding_y)

        # Draw a solid white masking area over the text block
        draw.rectangle([wipe_left, wipe_top, wipe_right, wipe_bottom], fill=255)

    # 3. EXPORT FILE
    output_path = json_path.with_name(f"{source_img_path.stem}_mask.png")
    mask_canvas.save(output_path, "PNG")
    print(f"[SUCCESS] High-fidelity automated black-and-white mask saved: {output_path.name}")

def main():
    parser = argparse.ArgumentParser(description="DJJTB Structural Mask Compiler")
    parser.add_argument("-j", "--json", required=True, help="Path to layout structure JSON file")
    args = parser.parse_args()
    
    json_target = Path(args.json)
    if not json_target.exists():
        print(f"[ERROR] Specified JSON layout file missing: {json_target}")
        return
        
    try:
        generate_binary_mask(json_target)
    except Exception as e:
        print(f"[CRITICAL ERROR] Mask generation failed: {str(e)}")

if __name__ == "__main__":
    main()