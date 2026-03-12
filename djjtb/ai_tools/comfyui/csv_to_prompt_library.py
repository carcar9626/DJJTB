#!/usr/bin/env python3
"""
CSV to Prompt Library JSON Converter
Converts a CSV file with prompt sets into ComfyUI prompt_library.json format

CSV Format Expected:
set_title,prompt_1,prompt_2,prompt_3,prompt_4,prompt_5,prompt_6,prompt_7,prompt_8

Example:
nature_landscapes,forest at sunrise,mountain with snow,ocean sunset,...
urban_scenes,cyberpunk city,vintage street,modern building,...
"""

import csv
import json
import os
import sys
import shutil
import djjtb.utils as djj

COMFYUI_DEST = "/Users/home/Documents/ai_models/ComfyUI_App/ComfyUI/custom_nodes/PromptSetSelector"

def csv_to_json(csv_path, json_output_path):
    """
    Convert CSV file to prompt_library.json format
    
    Args:
        csv_path: Path to input CSV file
        json_output_path: Path where JSON should be saved
    """
    
    # Check if CSV exists
    if not os.path.exists(csv_path):
        print(f"❌ Error: CSV file not found at: {csv_path}")
        print(f"\nPlease create a CSV file with this format:")
        print("set_title,prompt_1,prompt_2,prompt_3,prompt_4,prompt_5,prompt_6,prompt_7,prompt_8")
        return False
    
    prompt_library = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Check if required columns exist
            if 'set_title' not in reader.fieldnames:
                print("❌ Error: CSV must have 'set_title' column")
                print(f"Found columns: {reader.fieldnames}")
                return False
            
            row_count = 0
            for row in reader:
                set_title = row.get('set_title', '').strip()
                
                if not set_title:
                    print(f"⚠️  Warning: Skipping row {row_count + 2} - no set_title")
                    row_count += 1
                    continue
                
                # Extract prompts (prompt_1 through prompt_8)
                prompts = []
                for i in range(1, 9):
                    prompt_key = f'prompt_{i}'
                    prompt_value = row.get(prompt_key, '').strip()
                    prompts.append(prompt_value)
                
                # Add to library
                prompt_library[set_title] = prompts
                row_count += 1
                print(f"✅ Added: {set_title} ({len([p for p in prompts if p])} prompts)")
        
        # Save to JSON
        with open(json_output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(prompt_library, jsonfile, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 Success! Created {json_output_path}")
        print(f"📊 Total sets: {len(prompt_library)}")
        return True
        
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        return False


def copy_to_comfyui(json_output_path):
    """
    Prompt user to copy the JSON to ComfyUI PromptSetSelector folder.
    Uses djj.prompt_choice with default=1 (Yes).
    """
    print()
    choice = djj.prompt_choice(
        f"📦 Copy & overwrite prompt_library.json to ComfyUI PromptSetSelector?\n"
        f"   → {COMFYUI_DEST}\n"
        f"1. Yes\n2. No",
        ['1', '2'],
        default='1'
    )

    if choice == '1':
        dest_dir = COMFYUI_DEST
        if not os.path.exists(dest_dir):
            print(f"❌ Destination folder not found: {dest_dir}")
            print("   Please check your ComfyUI installation path.")
            return False

        dest_file = os.path.join(dest_dir, "prompt_library.json")
        try:
            shutil.copy2(json_output_path, dest_file)
            print(f"✅ Copied to: {dest_file}")
            print("🔄 Restart ComfyUI to load the updated prompts.")
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
            'set_title': 'nature_landscapes',
            'prompt_1': 'beautiful forest at sunrise, high quality, detailed',
            'prompt_2': 'mountain landscape with snow peaks, dramatic lighting',
            'prompt_3': 'ocean waves at sunset, golden hour, cinematic',
            'prompt_4': 'desert dunes under moonlight, serene atmosphere',
            'prompt_5': 'tropical beach paradise, crystal clear water',
            'prompt_6': 'autumn forest with fog, mysterious mood',
            'prompt_7': 'spring meadow with wildflowers, vibrant colors',
            'prompt_8': 'winter wonderland scene, pristine snow'
        },
        {
            'set_title': 'urban_scenes',
            'prompt_1': 'futuristic cyberpunk city, neon lights, rainy street',
            'prompt_2': 'vintage street photography, black and white, 1950s',
            'prompt_3': 'modern architecture glass building, minimalist design',
            'prompt_4': 'busy market street scene, vibrant colors, people',
            'prompt_5': 'neon lit alley at night, moody atmosphere',
            'prompt_6': 'rooftop city view at dusk, purple sky',
            'prompt_7': 'subway station underground, cinematic lighting',
            'prompt_8': 'cozy coffee shop interior, warm tones, inviting'
        }
    ]
    
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['set_title'] + [f'prompt_{i}' for i in range(1, 9)]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in example_data:
                writer.writerow(row)
        
        print(f"✅ Created example CSV at: {csv_path}")
        print(f"📝 Edit this file to add your own prompt sets!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating example CSV: {e}")
        return False


if __name__ == "__main__":
    # Default paths
    CSV_DIR = "/Users/home/Documents/ai/Prompts/Comfyui_PromptLibrary"
    CSV_FILENAME = "prompt_library.csv"
    JSON_FILENAME = "prompt_library.json"
    
    # You can also specify custom paths as command line arguments
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = os.path.join(CSV_DIR, CSV_FILENAME)
    
    if len(sys.argv) > 2:
        json_path = sys.argv[2]
    else:
        json_path = os.path.join(CSV_DIR, JSON_FILENAME)
    
    print("=" * 60)
    print("CSV to Prompt Library JSON Converter")
    print("=" * 60)
    print(f"CSV Input:  {csv_path}")
    print(f"JSON Output: {json_path}")
    print("=" * 60)
    print()
    
    # Create directory if it doesn't exist
    os.makedirs(CSV_DIR, exist_ok=True)
    
    # If CSV doesn't exist, create example
    if not os.path.exists(csv_path):
        print("CSV file not found. Creating example CSV...")
        print()
        if create_example_csv(csv_path):
            print()
            print("=" * 60)
            print("NEXT STEPS:")
            print("=" * 60)
            print(f"1. Open: {csv_path}")
            print("2. Edit the CSV to add your prompt sets")
            print("3. Run this script again to generate the JSON")
            print("=" * 60)
    else:
        # Convert CSV to JSON
        success = csv_to_json(csv_path, json_path)
        
        if success:
            # Offer to copy to ComfyUI
            copy_to_comfyui(json_path)

            print()
            print("=" * 60)
            print("DONE!")
            print("=" * 60)