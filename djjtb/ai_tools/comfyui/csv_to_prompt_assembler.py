#!/usr/bin/env python3
"""
CSV to Prompt Assembler JSON Converter
Converts a CSV file with prompt sets into the JSON format used by prompt_assembler.html

CSV Format Expected:
category,title,prompt

Example:
subject,JUDK Anchor Core,"subject_JUDK, a 23-year-old Chinese woman, 5' tall, petite frame, sharp facial structure, dark brown hair."
outfit,Minimalist Casual Set,"Dressed in a form-fitting sleeveless black top paired with micro denim shorts and low-profile athletic footwear."

Output JSON Structure (matches prompt_assembler.html DEFAULT_JSON_DATA):
{
  "category_name": [
    {"title": "...", "prompt": "..."},
    ...
  ]
}
"""

import csv
import json
import os
import sys
import shutil
import djjtb.utils as djj

LOCAL_DEST = "/Users/home/Documents/Scripts/FLOW_TOOLS/prompt_assembler/LOCAL"
DEFAULT_JSON_FILENAME = "prompt_assembler.json"


def csv_to_json(csv_path, json_output_path):
    """
    Convert CSV file to prompt_assembler.json format

    Args:
        csv_path: Path to input CSV file
        json_output_path: Path where JSON should be saved
    """

    if not os.path.exists(csv_path):
        print(f"❌ Error: CSV file not found at: {csv_path}")
        print(f"\nPlease create a CSV file with this format:")
        print("category,title,prompt")
        print("subject,JUDK Anchor Core,\"a 23-year-old Chinese woman, ...\"")
        return False

    prompt_assembler = {}

    try:
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            required = ['category', 'title', 'prompt']
            for col in required:
                if col not in reader.fieldnames:
                    print(f"❌ Error: CSV must have '{col}' column")
                    print(f"Found columns: {reader.fieldnames}")
                    return False

            row_count = 0
            for row in reader:
                category = row.get('category', '').strip()
                title = row.get('title', '').strip()
                prompt = row.get('prompt', '').strip()

                if not category or not title or not prompt:
                    print(f"⚠️  Warning: Skipping row {row_count + 2} - missing category/title/prompt")
                    row_count += 1
                    continue

                if category not in prompt_assembler:
                    prompt_assembler[category] = []

                prompt_assembler[category].append({
                    "title": title,
                    "prompt": prompt
                })
                row_count += 1
                print(f"✅ Added: [{category}] {title}")

        with open(json_output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(prompt_assembler, jsonfile, indent=2, ensure_ascii=False)

        print(f"\n🎉 Success! Created {json_output_path}")
        print(f"📊 Total categories: {len(prompt_assembler)}")
        total_entries = sum(len(v) for v in prompt_assembler.values())
        print(f"📊 Total entries: {total_entries}")
        return True

    except Exception as e:
        print(f"❌ Error processing file: {e}")
        return False


def copy_to_local(json_output_path):
    """
    Prompt user to copy the JSON to the local prompt_assembler folder.
    Uses djj.prompt_choice with default=1 (Yes).
    """
    print()
    choice = djj.prompt_choice(
        f"📦 Copy & overwrite prompt_assembler.json to local folder?\n"
        f"   → {LOCAL_DEST}\n"
        f"1. Yes\n2. No",
        ['1', '2'],
        default='1'
    )

    if choice == '1':
        dest_dir = LOCAL_DEST
        if not os.path.exists(dest_dir):
            print(f"❌ Destination folder not found: {dest_dir}")
            return False

        dest_file = os.path.join(dest_dir, DEFAULT_JSON_FILENAME)
        try:
            shutil.copy2(json_output_path, dest_file)
            print(f"✅ Copied to: {dest_file}")
            print("🔄 Reload prompt_assembler.html to load the updated prompts.")
            return True
        except Exception as e:
            print(f"❌ Error copying file: {e}")
            return False
    else:
        print("⏭️  Skipped copy. JSON saved locally only.")
        return False


def create_example_csv(csv_path):
    """Create an example CSV file to help users get started"""

    example_data = [
        {
            'category': 'subject',
            'title': 'JUDK Anchor Core',
            'prompt': "subject_JUDK, a 23-year-old Chinese woman, 5' tall, petite frame, sharp facial structure, dark brown hair."
        },
        {
            'category': 'subject',
            'title': 'SACH Base Anchor',
            'prompt': "subject_SACH, a 25-year-old Chinese woman, 5'4\" tall, fair complexion, sleek straight dark hair."
        },
        {
            'category': 'outfit',
            'title': 'Minimalist Casual Set',
            'prompt': "Dressed in a form-fitting sleeveless black top paired with micro denim shorts and low-profile athletic footwear."
        },
        {
            'category': 'outfit',
            'title': 'High Fashion Leather Jacket',
            'prompt': "Wearing an oversized structural leather jacket draped cleanly across her shoulders with subtle metal hardware accents."
        },
        {
            'category': 'composition',
            'title': 'Full Portrait Close-Up',
            'prompt': "Full body front-facing close up portrait of the subject centered cleanly within the camera viewport."
        },
        {
            'category': 'composition',
            'title': 'Wide Cinematic Angle',
            'prompt': "A wide-angle landscape framing establishing clean architectural perspective lines across the workspace."
        },
        {
            'category': 'pose/action',
            'title': 'Standing Stance Anchor',
            'prompt': "Standing upright with direct eye contact, shoulders relaxed, hands resting subtly at her sides mid-pose."
        },
        {
            'category': 'pose/action',
            'title': 'Grounded Squat Compression',
            'prompt': "In a compact, low squatting pose flat on the floor surface, with lower-body joints tightly gathered."
        },
        {
            'category': 'spacial/add ons',
            'title': 'Micro Occlusion Shadows',
            'prompt': "Generate deep ambient occlusion micro-shadows where her body contours meet the underlying surfaces."
        },
        {
            'category': 'spacial/add ons',
            'title': 'Scale Proportion Engine Fix',
            'prompt': "First adjust the scale, angle perspective and zoom between the scene and the subject to ensure realistic proportion."
        },
        {
            'category': 'lighting',
            'title': 'Sensual Late Night Late',
            'prompt': "Adopt a warm, sensual, late-night atmospheric lighting profile featuring gentle directional color casting."
        },
        {
            'category': 'lighting',
            'title': 'Studio Volumetric light wrap',
            'prompt': "Soft volumetric studio light wrapping smoothly around the skin textures and clothing folds."
        },
        {
            'category': 'aesthetic',
            'title': 'Mandatory Realism UGC Anchor',
            'prompt': "UGC aesthetic, handheld smartphone photo style, curated fashion portrait. Authentic subject preservation from reference photo. High-fidelity likeness."
        },
        {
            'category': 'aesthetic',
            'title': 'Clean Border Minimalist',
            'prompt': "High-end portrait aesthetic with complete color harmony, deep fabric definitions, and zero background bleed artifacts."
        }
    ]

    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['category', 'title', 'prompt']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for row in example_data:
                writer.writerow(row)

        print(f"✅ Created example CSV at: {csv_path}")
        print(f"📝 Edit this file to add your own prompt categories!")
        return True

    except Exception as e:
        print(f"❌ Error creating example CSV: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = os.path.join(LOCAL_DEST, "prompt_assembler.csv")

    if len(sys.argv) > 2:
        json_path = sys.argv[2]
    else:
        json_path = os.path.join(LOCAL_DEST, DEFAULT_JSON_FILENAME)

    print("=" * 60)
    print("CSV to Prompt Assembler JSON Converter")
    print("=" * 60)
    print(f"CSV Input:  {csv_path}")
    print(f"JSON Output: {json_path}")
    print("=" * 60)
    print()

    os.makedirs(LOCAL_DEST, exist_ok=True)

    if not os.path.exists(csv_path):
        print("CSV file not found. Creating example CSV...")
        print()
        if create_example_csv(csv_path):
            print()
            print("=" * 60)
            print("NEXT STEPS:")
            print("=" * 60)
            print(f"1. Open: {csv_path}")
            print(f"2. Edit the CSV to add your own categories and prompts")
            print(f"3. Run this script again to generate {DEFAULT_JSON_FILENAME}")
            print("=" * 60)
    else:
        success = csv_to_json(csv_path, json_path)

        if success:
            print()
            print("=" * 60)
            print("DONE!")
            print("=" * 60)
            print(f"📄 JSON saved at: {json_path}")
            print("🔄 Reload prompt_assembler.html to load the updated prompts.")
            print("=" * 60)
