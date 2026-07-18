import os
import glob
from pathlib import Path

def update_script(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Find main() function
    main_start = -1
    indent_level = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('def main():'):
            main_start = i
            indent_level = len(line) - len(line.lstrip())
            break

    if main_start == -1:
        print(f"Skipping {file_path}: No main() function found")
        return

    # Check if try-except already exists
    for line in lines[main_start:]:
        if 'except KeyboardInterrupt:' in line:
            print(f"Skipping {file_path}: Already has KeyboardInterrupt handler")
            return

    # Insert try-except block
    indent = ' ' * (indent_level + 4)
    new_lines = (
        lines[:main_start + 1]
        + [f"{indent}try:\n"]
        + [f"{indent}{line}" for line in lines[main_start + 1:]]
        + [
            f"{indent}except KeyboardInterrupt:\n",
            f"{indent}    print(\"\\n\\033[93m⚠️ Process interrupted by user.\\033[0m\")\n",
            f"{indent}    djj.cleanup_tabs()  # Close the current tool tab\n",
            f"{indent}    djj.return_to_djjtb()  # Switch to launcher tab\n",
           "f{indent}    return\n"
        ]
    )

    # Ensure required imports
    imports = ["import djjtb.utils as djj\n", "import sys\n"]
    existing_imports = {line.strip() for line in lines if line.strip().startswith('import')}
    for imp in imports:
        if imp.strip() not in existing_imports:
            for i, line in enumerate(new_lines):
                if line.strip().startswith('import'):
                    new_lines.insert(i, imp)
                    break
            else:
                new_lines.insert(0, imp)

    # Write updated script
    with open(file_path, 'w') as f:
        f.writelines(new_lines)
    print(f"Updated {file_path}")

# Paths to tool directories
project_path = "/Users/home/Documents/Scripts/DJJTB"
tool_dirs = [
    "djjtb/media_tools/video_tools",
    "djjtb/media_tools/image_tools",
    "djjtb/quick_tools"
]

# Update all tool scripts
for tool_dir in tool_dirs:
    for file_path in glob.glob(f"{project_path}/{tool_dir}/*.py"):
        if Path(file_path).stem not in ['__init__']:
            update_script(file_path)