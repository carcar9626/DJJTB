#artifact version ID: 12345678-1234-1234-1234-123456789012
import pandas as pd
import random
import os
from datetime import datetime

# Paths
csv_path = '/Users/home/Documents/Scripts/DJJTB/Scripts/ai_tools/Prompt_Randomizer/Library/Data/PromptMasterList_Grok.csv'
char_txt_path = '//Users/home/Documents/Scripts/DJJTB/Scripts/ai_tools/Prompt_Randomizer/Library/Data/PromptsCharacterList_Grok.txt'
attr_dir = '/Users/home/Documents/Scripts/DJJTB/Scripts/ai_tools/Prompt_Randomizer/Library/Attributes'
output_dir = '/Users/home/Documents/Scripts/DJJTB/Scripts/ai_tools/Prompt_Randomizer/Output'

# Columns to include in prompts
columns = [
    'Prompt', 'Persona', 'Character', 'Hair Colour', 'Hairstyle', 'Pose/Action',
    'Clothing Style', 'Top Clothing Description', 'Top Clothing',
    'Bottom Clothing Description', 'Bottom Clothing', 'Footwear Description',
    'Footwear', 'Accessories', 'Expression/Emotion', 'Makeup', 'Setting',
    'Mood/Lighting/Vibe', 'Camera Angle', 'Tags/Keywords', 'Orientation',
    'Cinematic Framing'
]

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Load CSV
try:
    df = pd.read_csv(csv_path, encoding='utf-8')
except Exception as e:
    print(f"Error reading CSV: {e}")
    exit(1)

# Load character descriptions from PromptsCharacterList_Grok.txt
char_descriptions = {}
if os.path.exists(char_txt_path):
    with open(char_txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                char_name = line.split(',')[0].strip()
                char_descriptions[char_name] = line

# Load attribute text files
attr_values = {}
for col in columns:
    if col != 'Character':
        filename = col.replace('/', '_').replace(' ', '_') + '.txt'
        file_path = os.path.join(attr_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                attr_values[col] = [line.strip() for line in f if line.strip()]
        else:
            attr_values[col] = []

# Load Character.txt for fallback
char_txt_values = []
char_txt_file = os.path.join(attr_dir, 'Character.txt')
if os.path.exists(char_txt_file):
    with open(char_txt_file, 'r', encoding='utf-8') as f:
        char_txt_values = [line.strip() for line in f if line.strip()]

# Prompt for character selection
print("Select a character:")
print("1. Pizz0")
print("2. Ann4")
print("3. Cataug")
print("4. S@Tw!n5")
print("5. SG")
print("6. ct-jennie2")
print("7. SQ")
print("0. Random")
try:
    char_choice = int(input("Enter your choice (0-7): "))
    if char_choice not in range(0, 8):
        print("Invalid choice. Using random character.")
        char_choice = 0
except ValueError:
    print("Invalid input. Using random character.")
    char_choice = 0

char_map = {
    1: 'Pizz0',
    2: 'Ann4',
    3: 'Cataug',
    4: 'S@Tw!n5',
    5: 'SG',
    6: 'ct-jennie2',
    7: 'SQ'
}
selected_character = char_map.get(char_choice, None)

# Prompt for number of prompts
try:
    num_prompts = int(input("Enter the number of prompts to generate: "))
    if num_prompts <= 0:
        print("Invalid input. Generating 3 prompts by default.")
        num_prompts = 3
except ValueError:
    print("Invalid input. Generating 3 prompts by default.")
    num_prompts = 3

# Generate prompts
prompts = []
used_characters = set()
for _ in range(num_prompts):
    # Select a random row from CSV
    row = df.sample(n=1).iloc[0]
    
    # Initialize prompt attributes
    prompt_attrs = {}
    for col in columns:
        value = str(row[col]).strip() if pd.notna(row[col]) else ''
        if not value or value.lower() == 'nan':
            if col == 'Character' and char_txt_values:
                value = random.choice(char_txt_values)
            elif col in attr_values and attr_values[col]:
                value = random.choice(attr_values[col])
            else:
                value = 'generic'
        prompt_attrs[col] = value
    
    # Handle character selection
    if selected_character:
        prompt_attrs['Character'] = selected_character
    elif not prompt_attrs['Character'] or prompt_attrs['Character'].lower() == 'nan':
        prompt_attrs['Character'] = random.choice(['Ann4', 'Cataug', 'S@Tw!n5', 'Pizz0', 'SG', 'ct-jennie2', 'SQ'])
    
    # Get character description
    char_name = prompt_attrs['Character'].split(',')[0].strip()
    char_desc = char_descriptions.get(char_name, prompt_attrs['Character'])
    used_characters.add(char_desc)
    
    # Apply LoRA tag rules
    tags = prompt_attrs['Tags/Keywords'].split(',') if prompt_attrs['Tags/Keywords'] and pd.notna(prompt_attrs['Tags/Keywords']) else ['photorealistic', 'ultra-detailed', '8K resolution', 'cinematic']
    tags = [tag.strip() for tag in tags if tag.strip()]
    if prompt_attrs['Character'].startswith('Ann4'):
        tags.extend(['1girl', 'solo', 'asian'])
    elif prompt_attrs['Character'].startswith('Cataug'):
        tags.extend(['1girl', 'asian girl'])
    elif prompt_attrs['Character'].startswith('S@Tw!n5'):
        tags.extend(['1girl', 'smile', 'portrait'])
    # Deduplicate tags
    tags = list(dict.fromkeys(tags))
    prompt_attrs['Tags/Keywords'] = ', '.join(tags)
    
    # Paragraph Version (excluding Persona)
    bottom_clothing_text = f"{prompt_attrs['Bottom Clothing Description']} {prompt_attrs['Bottom Clothing']}, " if "dress" not in prompt_attrs['Top Clothing'].lower() else ""
    paragraph = f"with {prompt_attrs['Hair Colour']} hair in a {prompt_attrs['Hairstyle']} is {prompt_attrs['Prompt']}. "
    paragraph += f"She's in a {prompt_attrs['Top Clothing Description']} {prompt_attrs['Top Clothing']}, {bottom_clothing_text}{prompt_attrs['Footwear Description']} {prompt_attrs['Footwear']}, {prompt_attrs['Accessories']} outfit, "
    paragraph += f"{prompt_attrs['Makeup']} makeup with a {prompt_attrs['Expression/Emotion']} expression. "
    paragraph += f"She's in a {prompt_attrs['Setting']}. The mood is {prompt_attrs['Mood/Lighting/Vibe']}. "
    paragraph += f"{prompt_attrs['Camera Angle']}, {prompt_attrs['Tags/Keywords']}, {prompt_attrs['Orientation'].lower()} {prompt_attrs['Cinematic Framing'].lower()}."
    
    # Modular Version
    modular = [f"Selected Character: {char_desc}"]
    for col in columns:
        if col != 'Character':
            modular.append(f"{col}: {prompt_attrs[col]}")
    
    prompts.append({
        'paragraph': paragraph,
        'modular': modular
    })

# Write to output file
date_str = datetime.now().strftime('%Y%m%d')
char_str = selected_character if selected_character else 'Random'
output_file = os.path.join(output_dir, f'{date_str}-{char_str}-{num_prompts}-prompts.txt')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(f"Characters Chosen: {char_str}\n\n")
    for i, char_desc in enumerate(sorted(used_characters), 1):
        f.write(f"{i}. {char_desc}\n")
    f.write("\nParagraph Versions:\n\n")
    for i, prompt in enumerate(prompts, 1):
        f.write(f"Prompt {i}:\n{prompt['paragraph']}\n\n")
    
    f.write("Modular Versions:\n\n")
    for i, prompt in enumerate(prompts, 1):
        f.write(f"Prompt {i}:\n")
        for line in prompt['modular']:
            f.write(f"{line}\n")
        f.write("\n")

print(f"Generated {num_prompts} prompts in {output_file}")

# Open the output folder
os.system(f"open {output_dir}")