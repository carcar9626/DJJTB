import pandas as pd
import csv
import os
import shutil
from datetime import datetime
import random

# Paths
csv_path = '/Users/home/Documents/Scripts/DJJTB/Scripts/ai_tools/Prompt_Randomizer/Library/Data/PromptMasterList_Grok.csv'
char_txt_path = '/Users/home/Documents/Scripts/DJJTB/Scripts/ai_tools/Prompt_Randomizer/Library/Data/PromptsCharacterList_Grok.txt'
output_dir = '/Users/home/Documents/Scripts/DJJTB/Scripts/ai_tools/Prompt_Randomizer/Library/Attributes'
backup_dir = '/Users/home/Documents/Scripts/DJJTB/Scripts/ai_tools/Prompt_Randomizer/Library/Attributes/Backups'

# All columns to generate text files for
attr_columns = [
    'Prompt', 'Persona', 'Character', 'Hair Colour', 'Hairstyle', 'Pose/Action',
    'Clothing Style', 'Top Clothing Description', 'Top Clothing',
    'Bottom Clothing Description', 'Bottom Clothing', 'Footwear Description',
    'Footwear', 'Accessories', 'Expression/Emotion', 'Makeup', 'Setting',
    'Mood/Lighting/Vibe', 'Camera Angle', 'Tags/Keywords', 'Orientation',
    'Cinematic Framing'
]

# Default values for empty columns
default_values = {
    'Prompt': ['generic prompt'],
    'Persona': ['happy', 'sensual', 'dreamy'],
    'Character': ['generic character'],
    'Hair Colour': ['black', 'blonde', 'brown'],
    'Hairstyle': ['ponytail', 'bun', 'loose waves'],
    'Pose/Action': ['posing', 'standing', 'sitting'],
    'Clothing Style': ['casual', 'elegant', 'bohemian'],
    'Top Clothing Description': ['white', 'black', 'colorful'],
    'Top Clothing': ['top', 'blouse', 'jumpsuit'],
    'Bottom Clothing Description': ['denim', 'black', 'floral'],
    'Bottom Clothing': ['skirt', 'jeans', 'leggings'],
    'Footwear Description': ['black', 'white', 'tan'],
    'Footwear': ['sneakers', 'heels', 'sandals'],
    'Accessories': ['none', 'necklace', 'bracelet'],
    'Expression/Emotion': ['happy', 'curious', 'relaxed'],
    'Makeup': ['natural', 'bold', 'dewy'],
    'Setting': ['generic setting'],
    'Mood/Lighting/Vibe': ['neutral mood'],
    'Camera Angle': ['frontal shot'],
    'Tags/Keywords': ['photorealistic, ultra-detailed, 8K resolution, cinematic'],
    'Orientation': ['Portrait'],
    'Cinematic Framing': ['Medium Shot']
}

# Load CSV
try:
    df = pd.read_csv(csv_path, encoding='utf-8', quoting=csv.QUOTE_ALL)
except pd.errors.ParserError as e:
    print(f"Error parsing CSV: {e}")
    exit(1)

# Ensure output and backup directories exist
os.makedirs(output_dir, exist_ok=True)
os.makedirs(backup_dir, exist_ok=True)

# Backup CSV before modification
if os.path.exists(csv_path):
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    csv_backup_path = os.path.join(backup_dir, f"PromptMasterList_Grok_{timestamp}.csv")
    shutil.copy(csv_path, csv_backup_path)
    print(f"Backed up CSV to: {csv_backup_path}")

# Generate or update text files and update CSV (except Character column)
for col in attr_columns:
    # Handle Character column specially (overwrite with CSV entries only)
    if col == 'Character':
        # Extract non-empty Character values from CSV (keep duplicates)
        values = df['Character'].astype(str).dropna().str.strip()
        values = [v for v in values if v and v != 'nan']
        if not values:
            values = default_values['Character']
    else:
        # Extract unique non-empty values from CSV
        csv_values = df[col].astype(str).dropna().str.strip()
        csv_values = [v for v in csv_values if v and v != 'nan']
        csv_values = list(dict.fromkeys(csv_values))  # Remove duplicates
        if not csv_values:
            csv_values = default_values.get(col, ['generic'])
        
        # Read existing text file content
        filename = col.replace('/', '_').replace(' ', '_') + '.txt'
        output_file = os.path.join(output_dir, filename)
        existing_values = []
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_values = [line.strip() for line in f if line.strip()]
        
        # Merge values (deduplicate)
        values = list(dict.fromkeys(existing_values + csv_values))
        
        # Update CSV column with text file values
        if existing_values:
            # Identify empty cells
            def is_empty(x):
                if pd.isna(x):
                    return True
                x_str = str(x).strip()
                return x_str == '' or x_str.lower() == 'nan' or x_str == 'None'
            
            # Fill empty cells with random text file values
            empty_mask = df[col].apply(is_empty)
            if empty_mask.any():
                df.loc[empty_mask, col] = [random.choice(existing_values) for _ in range(empty_mask.sum())]
            else:
                # If no empty cells, create new rows for new text file values
                new_values = [v for v in existing_values if v not in csv_values]
                if new_values:
                    # Create new rows with only the updated column filled
                    new_rows = pd.DataFrame({col: new_values}, index=range(len(new_values)))
                    # Ensure all attr_columns exist in new_rows, filled with NaN
                    for c in attr_columns:
                        if c not in new_rows:
                            new_rows[c] = pd.NA
                    # Reorder columns to match df
                    new_rows = new_rows[df.columns]
                    # Append new rows to df
                    df = pd.concat([df, new_rows], ignore_index=True)

    # Replace spaces and slashes in filename
    filename = col.replace('/', '_').replace(' ', '_') + '.txt'
    output_file = os.path.join(output_dir, filename)
    
    # Backup existing text file
    if os.path.exists(output_file):
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_file = os.path.join(backup_dir, f"{col.replace('/', '_').replace(' ', '_')}_{timestamp}.txt")
        shutil.copy(output_file, backup_file)
    
    # Write to text file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(values))
    print(f"Generated/Updated: {output_file}")

# Save updated CSV (except Character column)
try:
    df.to_csv(csv_path, index=False, encoding='utf-8', quoting=csv.QUOTE_ALL)
    print(f"Updated CSV: {csv_path} (Character column unchanged)")
except Exception as e:
    print(f"Error saving CSV: {e}")
    exit(1)

print(f"Processed {len(attr_columns)} attribute text files in {output_dir}")