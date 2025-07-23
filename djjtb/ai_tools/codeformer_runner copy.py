import os
import sys
import subprocess
import pathlib
import logging
import djjtb.utils as djj

SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi')
CODEFORMER_DIR = pathlib.Path("/Volumes/Desmond_SSD_2TB/CodeFormer")

def get_float_input_with_default(prompt_text, min_val=None, max_val=None, default=None):
    """Local version: get validated float input with optional default"""
    while True:
        raw = input(prompt_text)
        if not raw.strip() and default is not None:
            return default
        try:
            val = float(raw)
            if (min_val is not None and val < min_val) or \
               (max_val is not None and val > max_val):
                print(f"⚠️  Please enter a value between {min_val} and {max_val}")
            else:
                return val
        except ValueError:
            print("❌ Invalid input. Please enter a number.")

def get_int_input_with_default(prompt_text, min_val=None, max_val=None, default=None):
    """Local version: get validated integer input with optional default"""
    while True:
        raw = input(prompt_text + (' ' if not prompt_text.endswith(' ') else ''))
        if not raw.strip() and default is not None:
            return default
        try:
            val = int(raw)
            if (min_val is not None and val < min_val) or \
               (max_val is not None and val > max_val):
                print(f"⚠️  Please enter a value between {min_val} and {max_val}")
            else:
                return val
        except ValueError:
            print("❌ Invalid input. Please enter an integer.")
            
def clean_path(path_str):
    return path_str.strip().strip('\'"')

def collect_files_from_folder(input_path, subfolders=False):
    input_path_obj = pathlib.Path(input_path)
    files = []

    if input_path_obj.is_dir():
        if subfolders:
            for root, _, filenames in os.walk(input_path):
                files.extend(pathlib.Path(root) / f for f in filenames
                           if pathlib.Path(f).suffix.lower() in SUPPORTED_EXTS)
        else:
            files = [f for f in input_path_obj.glob('*')
                     if f.suffix.lower() in SUPPORTED_EXTS and f.is_file()]
    return sorted([str(f) for f in files], key=str.lower)

def collect_files_from_paths(file_paths):
    files = []
    paths = file_paths.strip().split()
    for path in paths:
        path = clean_path(path)
        path_obj = pathlib.Path(path)
        if path_obj.is_file() and path_obj.suffix.lower() in SUPPORTED_EXTS:
            files.append(str(path_obj))
        elif path_obj.is_dir():
            files.extend(collect_files_from_folder(path))
    return sorted(files, key=str.lower)

def get_valid_inputs():
    print("🔍 Select files or folders to process")

    input_mode = djj.prompt_choice(
        "\033[33mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths",
        ['1', '2'], default='1'
    )
    print()
    valid_paths = []

    if input_mode == '1':
        src_path = djj.get_path_input("Enter folder path")
        print()
        include_sub = djj.prompt_choice(
            "\033[33mInclude subfolders?\033[0m\n1. Yes\n2. No", ['1', '2'], default='2'
        ) == '1'
        print()
        valid_paths = collect_files_from_folder(src_path, include_sub)
    else:
        file_paths = input("📁 \033[33mEnter file paths (space-separated):\033[0m\n -> ").strip()
        if not file_paths:
            print("❌ No file paths provided.")
            sys.exit(1)
        valid_paths = collect_files_from_paths(file_paths)
        print()

    if not valid_paths:
        print("❌ \033[33mNo valid files found.\033[0m")
        sys.exit(1)

    print(f"✅ Found {len(valid_paths)} supported file(s)")
    for i, file_path in enumerate(valid_paths[:5]):
        print(f"  {i+1}. {os.path.basename(file_path)}")
    if len(valid_paths) > 5:
        print(f"  ... and {len(valid_paths) - 5} more")
    print()

    return valid_paths

def process_file(input_path, weight, suffix, upscale):
    input_path = pathlib.Path(input_path)
    output_path = input_path.parent / "Output" / "CF"
    output_path.mkdir(parents=True, exist_ok=True)

    print("\n🧠 Running CodeFormer on:")
    print(f"   \033[33m📥 Input:\033[0m {input_path}")
    print(f"   \033[33m📤 Output:\033[0m {output_path}")
    print(f"   \033[33m🧪 Weight:\033[0m {weight}")
    print(f"   \033[33m🔠 Suffix:\033[0m {suffix}")
    print(f"   \033[33m🔼 Upscale:\033[0m {upscale}")
    print()

    result = subprocess.run([
        "python3", str(CODEFORMER_DIR / "inference_codeformer.py"),
        "-i", str(input_path),
        "-o", str(output_path),
        "-w", str(weight),
        "--suffix", suffix,
        "--upscale", str(upscale)
    ])

    if result.returncode == 0:
        print(f"✅ \033[33mCompleted:\033[0m {input_path.name}")
    else:
        print(f"❌ \033[33mFailed:\033[0m {input_path.name}")

def main():
    os.system('clear')

    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mCodeformer\033[0m")
        print("Face Restore & UpScale Tool")
        print("\033[92m==================================================\033[0m")
        print()


        input_files = get_valid_inputs()

        weight_val = get_float_input_with_default(
            "\033[33mEnter weight (range 0.0–1.0, default 0.7):\033[0m\n > ",
            min_val=0.0, max_val=1.0, default=0.7
        )

        suffix = input("\033[33mEnter suffix (default '_CF'):\033[0m\n > ").strip()
        if not suffix:
            suffix = "_CF"
            print("⚠️  \033[33mUsing default suffix '_CF'.\033[0m")

        upscale = get_int_input_with_default(
            "\033[33mEnter upscale factor (default 2):\033[0m", min_val=1, max_val=10, default=2
        )

        print()

        for input_path in input_files:
            process_file(input_path, weight_val, suffix, upscale)

        print(f"\033[33m\n🏁 Done!\033[0m Processed {len(input_files)} file(s).")

        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()