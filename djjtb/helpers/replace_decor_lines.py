import os
from pathlib import Path

# ✅ Only process this folder
project_root = Path("/Users/home/Documents/Scripts/DJJTB/djjtb")

# ✅ Only these exact lines will be replaced
replacements = {
    "\033[92m===================================\033[0m": "\033[92m==================================================\033[0m",
    "\033[92m-----------------------------------\033[0m": "\033[92m---------------------------------\092[0m",
    
}

def replace_in_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        print(f"❌ Skipped (encoding error): {file_path}")
        return

    changed = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped in replacements:
            new_line = line.replace(stripped, replacements[stripped])
            new_lines.append(new_line)
            changed = True
        else:
            new_lines.append(line)

    if changed:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"✅ Updated: {file_path}")

def process_folder(path):
    for root, dirs, files in os.walk(path):
        # ✅ Skip any virtualenv or site-packages just in case
        dirs[:] = [d for d in dirs if "venv" not in d and "site-packages" not in d and "__pycache__" not in d]

        for file in files:
            if file.endswith(".py"):
                replace_in_file(Path(root) / file)

if __name__ == "__main__":
    process_folder(project_root)