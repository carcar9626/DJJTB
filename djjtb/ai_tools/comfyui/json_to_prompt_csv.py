#!/usr/bin/env python3
"""
Prompt Library JSON to CSV Converter (Reverse Sync)
Converts prompt_library.json back to CSV format for easy editing

This is the reverse of csv_to_prompt_library.py
Use this to sync changes FROM ComfyUI back TO your CSV file
"""

import csv
import json
import os
import sys
from datetime import datetime

# ============================================================================
# CONFIGURATION - EDIT THESE SETTINGS
# ============================================================================

# Source: ComfyUI's prompt library JSON
JSON_INPUT_PATH = "/Users/home/Documents/ai_models/ComfyUI_App/ComfyUI/custom_nodes/PromptSetSelector/prompt_library.json"

# Destination: Your CSV file for editing
CSV_OUTPUT_PATH = "/Users/home/Documents/ai/Prompts/Comfyui_PromptLibrary/prompt_library.csv"

# Create backup of existing CSV before overwriting?
CREATE_BACKUP = True

# ============================================================================
# SCRIPT CODE
# ============================================================================

def create_backup(csv_path):
    """Create a timestamped backup of the CSV file"""
    if not os.path.exists(csv_path):
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = csv_path.replace(".csv", f"_backup_{timestamp}.csv")
    
    try:
        import shutil
        shutil.copy2(csv_path, backup_path)
        return backup_path
    except Exception as e:
        print(f"⚠️  Warning: Could not create backup: {e}")
        return None


def json_to_csv(json_path, csv_path):
    """
    Convert JSON prompt library to CSV format
    
    Args:
        json_path: Path to input JSON file
        csv_path: Path where CSV should be saved
    """
    
    # Check if JSON exists
    if not os.path.exists(json_path):
        print(f"❌ Error: JSON file not found at: {json_path}")
        return False
    
    # Load JSON
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            prompt_library = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON format: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading JSON: {e}")
        return False
    
    if not prompt_library:
        print("❌ Error: JSON file is empty")
        return False
    
    # Create backup if requested
    if CREATE_BACKUP and os.path.exists(csv_path):
        backup_path = create_backup(csv_path)
        if backup_path:
            print(f"💾 Created backup: {os.path.basename(backup_path)}")
    
    # Convert to CSV
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['set_title'] + [f'prompt_{i}' for i in range(1, 9)]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            row_count = 0
            for set_title, prompts in prompt_library.items():
                # Ensure prompts is a list
                if not isinstance(prompts, list):
                    print(f"⚠️  Warning: Skipping '{set_title}' - invalid format")
                    continue
                
                row = {'set_title': set_title}
                
                # Add prompts (pad with empty strings if less than 8)
                for i in range(1, 9):
                    idx = i - 1
                    if idx < len(prompts):
                        row[f'prompt_{i}'] = prompts[idx]
                    else:
                        row[f'prompt_{i}'] = ''
                
                writer.writerow(row)
                row_count += 1
                print(f"✅ Exported: {set_title} ({len([p for p in prompts if p])} prompts)")
        
        print(f"\n🎉 Success! Exported to {csv_path}")
        print(f"📊 Total sets: {row_count}")
        return True
        
    except Exception as e:
        print(f"❌ Error writing CSV: {e}")
        return False


def main():
    """Main entry point"""
    
    print("=" * 70)
    print("Prompt Library JSON to CSV Converter (Reverse Sync)")
    print("=" * 70)
    print(f"JSON Input:  {JSON_INPUT_PATH}")
    print(f"CSV Output:  {CSV_OUTPUT_PATH}")
    print("=" * 70)
    print()
    
    # Check if JSON exists
    if not os.path.exists(JSON_INPUT_PATH):
        print(f"❌ JSON file not found at: {JSON_INPUT_PATH}")
        print()
        print("This script syncs FROM ComfyUI's JSON TO your CSV.")
        print("Make sure you've created the JSON file first using csv_to_prompt_library.py")
        return
    
    # Convert
    success = json_to_csv(JSON_INPUT_PATH, CSV_OUTPUT_PATH)
    
    if success:
        print()
        print("=" * 70)
        print("NEXT STEPS:")
        print("=" * 70)
        print(f"1. Open: {CSV_OUTPUT_PATH}")
        print("2. Edit your prompts in Excel/Numbers/etc.")
        print("3. Run csv_to_prompt_library.py to sync changes back to ComfyUI")
        print("4. Restart ComfyUI to load updated prompts")
        print("=" * 70)
        print()
        print("💡 TIP: This creates a backup of your CSV automatically!")
        print("   Look for files like: prompt_library_backup_YYYYMMDD_HHMMSS.csv")


if __name__ == "__main__":
    main()
