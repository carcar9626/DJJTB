import re
from pathlib import Path
import shutil

# ✅ List of specific scripts to process
files_to_process = [
    "/Users/home/Documents/Scripts/DJJTB/djjtb/ai_tools/image_tagger.py",
    "/Users/home/Documents/Scripts/DJJTB/djjtb/ai_tools/joytag_tagger.py",
]

# ✅ Regex to match green lines inside print statements, 30+ '=' or '-' characters
pattern = re.compile(
    r'(\s*print\(")'      # indentation + print("
    r'(\\033\[92m)'       # literal \033[92m
    r'([=-]{30,})'        # 30 or more '=' or '-'
    r'(\\033\[0m)'        # literal \033[0m
    r'(".*\))'            # closing quote + parentheses
)

def get_terminal_width():
    """Get current terminal width in characters"""
    try:
        return shutil.get_terminal_size().columns
    except:
        return 80  # fallback width

def replace_in_file(file_path: Path, term_width: int):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        print(f"❌ Skipped (encoding error): {file_path}")
        return

    changed = False
    new_lines = []

    for line in lines:
        def repl(m):
            indentation = m.group(1)
            color_start = m.group(2)
            char = m.group(3)[0]  # '=' or '-'
            color_end = m.group(4)
            rest = m.group(5)
            return f"{indentation}{color_start}{char * term_width}{color_end}{rest}"

        new_line = pattern.sub(repl, line)
        if new_line != line:
            changed = True
        new_lines.append(new_line)

    if changed:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"✅ Updated: {file_path}")

if __name__ == "__main__":
    term_width = get_terminal_width()
    for file_path in files_to_process:
        replace_in_file(Path(file_path), term_width)