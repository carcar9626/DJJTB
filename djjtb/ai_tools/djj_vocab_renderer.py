#!/usr/bin/env python3
"""
DJJTB - Vocabulary Card Canvas Assembly Engine (V3 - Native 4:5 Mapping)
Category: ai_tools
Description: Upscales native 4:5 source graphics directly to 1080x1350,
             wipes old text layout structures proportionally, and overlays
             clean Chinese + English text with perfect alignment.
"""

import json
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# --- DESIGN & PRODUCTION SYSTEM CONFIGURATION ---
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1350

COLOR_TEXT_MAIN = (20, 20, 20)   # Premium Off-Black for Chinese Characters
COLOR_TEXT_SUB = (120, 115, 110) # Elegant Taupe Grey for English tracking

# --- ABSOLUTE FONT ENDPOINTS ---
FONT_ZH_PATH = "/Users/home/Documents/Scripts/DJJTB/assets/fonts/Noto_Sans_SC/NotoSansSC-VariableFont_wght.ttf"
FONT_EN_PATH = "/System/Library/Fonts/Helvetica.ttc"

def load_typography():
    """Initializes high-fidelity font structures for rendering."""
    try:
        font_head_zh = ImageFont.truetype(FONT_ZH_PATH, 42)
        font_item_zh = ImageFont.truetype(FONT_ZH_PATH, 24)
    except IOError:
        print(f"[CRITICAL WARNING] Font missing at: {FONT_ZH_PATH}. Using fallback defaults.")
        font_head_zh = font_item_zh = ImageFont.load_default()

    try:
        font_head_en = ImageFont.truetype(FONT_EN_PATH, 18)
        font_item_en = ImageFont.truetype(FONT_EN_PATH, 13)
    except IOError:
        font_head_en = font_item_en = ImageFont.load_default()

    return font_head_zh, font_head_en, font_item_zh, font_item_en

# --- MAIN CONVERSION ROUTINE ---
def process_native_render(json_path: Path):
    # Parse structured JSON payload
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    source_path = Path(data["meta"]["source_image_path"])
    if not source_path.exists():
        raise FileNotFoundError(f"Referenced source image asset missing: {source_path}")

    # Load and scale source image natively to production 1080x1350 dimensions
    raw_image = Image.open(source_path).convert("RGB")
    scaled_canvas = raw_image.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(scaled_canvas)

    # Automatically sample the background shade at (10, 10) to match the wipe color perfectly
    bg_color_sample = scaled_canvas.getpixel((10, 10))

    # Load typography configuration
    f_head_zh, f_head_en, f_item_zh, f_item_en = load_typography()

    # 1. HEADER ZONE MANAGEMENT
    # Clear out the top header block dynamically (from y=0 to y=130) to overwrite the old title cleanly
    draw.rectangle([0, 0, TARGET_WIDTH, 130], fill=bg_color_sample)

    title_zh = data.get("main_title_chinese", "英语词汇矩阵")
    title_en = data.get("main_title_english", "VOCABULARY MATRIX").upper()

    # Render clean centered title blocks
    draw.text((TARGET_WIDTH // 2, 45), title_zh, fill=COLOR_TEXT_MAIN, font=f_head_zh, anchor="mm")
    draw.text((TARGET_WIDTH // 2, 95), title_en, fill=COLOR_TEXT_SUB, font=f_head_en, anchor="mm")

    # 2. MATRIX TRACKING & WIPING LOOP
    for item in data["items"]:
        ymin, xmin, ymax, xmax = item["text_bbox"]

        # Scale coordinates independently to respect the 4:5 vertical grid proportions
        t_left = int(xmin * (TARGET_WIDTH / 1000))
        t_right = int(xmax * (TARGET_WIDTH / 1000))
        t_top = int(ymin * (TARGET_HEIGHT / 1000))
        t_bottom = int(ymax * (TARGET_HEIGHT / 1000))

        # Apply a protective padding margin to fully enclose the old text boundaries
        # This completely whites out descending letters (g, j, p, q, y)
        wipe_left = t_left - 25
        wipe_right = t_right + 25
        wipe_top = t_top - 14
        wipe_bottom = t_bottom + 14

        # Execute the Wipe Step
        draw.rectangle([wipe_left, wipe_top, wipe_right, wipe_bottom], fill=bg_color_sample)

        # Calculate geometric center of the cleared workspace
        center_x = wipe_left + (wipe_right - wipe_left) // 2
        center_y = wipe_top + (wipe_bottom - wipe_top) // 2

        # Execute the Overwrite Step
        chinese_text = item["chinese_translation"]
        english_text = item["english_text"].upper()

        # Render Bilingual Vertical Layout Stack using pixel-perfect midpoint anchors
        draw.text((center_x, center_y - 10), chinese_text, fill=COLOR_TEXT_MAIN, font=f_item_zh, anchor="mm")
        draw.text((center_x, center_y + 12), english_text, fill=COLOR_TEXT_SUB, font=f_item_en, anchor="mm")

    # 3. WATERMARK INJECTION
    # Add a clean brand handle signature right underneath the main title block
    draw.text((TARGET_WIDTH // 2, 118), "@erfan_.chinese", fill=COLOR_TEXT_SUB, font=f_item_en, anchor="mm")

    # Save output production slide
    output_filename = f"FINAL_IG_Slide_{json_path.stem}.png"
    output_path = json_path.with_name(output_filename)
    scaled_canvas.save(output_path, "PNG", quality=100)
    print(f"[PIPELINE SUCCESS] 4:5 Proportional Card generated: {output_path.name}")

def main():
    parser = argparse.ArgumentParser(description="DJJTB Canvas Rendering Assembly Tool v3")
    parser.add_argument("-j", "--json", required=True, help="Path to layout structure JSON file")
    args = parser.parse_args()
    
    json_target = Path(args.json)
    if not json_target.exists():
        print(f"[ERROR] Target JSON layout file missing: {json_target}")
        return
        
    process_native_render(json_target)

if __name__ == "__main__":
    main()