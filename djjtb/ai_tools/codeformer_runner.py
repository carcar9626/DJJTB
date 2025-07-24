import os
import sys
import subprocess
import pathlib
import logging
import djjtb.utils as djj

# Supported extensions
SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi')

# Path to CodeFormer model scripts and virtual environment
CODEFORMER_SCRIPT_PATH = "/Volumes/Desmond_SSD_2TB/CodeFormer/inference_codeformer.py"
CODEFORMER_VENV_PYTHON = "/Volumes/Desmond_SSD_2TB/CodeFormer/cfvenv/bin/python3"
CODEFORMER_DIR = "/Volumes/Desmond_SSD_2TB/CodeFormer"

def clean_path(path_str):
    """Clean path string by removing quotes and whitespace"""
    return path_str.strip().strip('\'"')

def collect_files_from_folder(input_path, subfolders=False):
    """Collect supported files from folder(s)"""
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
    """Collect files from space-separated file paths"""
    files = []
    paths = file_paths.strip().split()
    
    for path in paths:
        path = clean_path(path)
        path_obj = pathlib.Path(path)
        
        if path_obj.is_file() and path_obj.suffix.lower() in SUPPORTED_EXTS:
            files.append(str(path_obj))
        elif path_obj.is_dir():
            dir_files = collect_files_from_folder(path)
            files.extend(dir_files)
    
    return sorted(files, key=str.lower)

def get_valid_inputs():
    """Allow selecting multiple files and/or folders using prompt_choice"""
    print("🔍 Select files or folders to process")
    
    input_mode = djj.prompt_choice(
        "\033[33mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths",
        ['1', '2'],
        default='1'
    )
    print()
    
    valid_paths = []
    
    if input_mode == '1':
        src_path = djj.get_path_input("Enter folder path")
        print()
        
        include_sub = djj.prompt_choice(
            "\033[33mInclude subfolders?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
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
    
    return valid_paths, input_mode, src_path if input_mode == '1' else None

def process_files(input_paths, input_mode, src_path, weight, suffix, upscale):
    if input_mode == '1':
        output_path = pathlib.Path(src_path) / "Output" / "CF"
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\n🧠 Processing {len(input_paths)} file(s):")
        print(f"   \033[33m📥 Input:\033[0m folder: {src_path}")
        print(f"   \033[33m📤 Output:\033[0m {output_path}")
        print(f"   \033[33m🧪 Weight:\033[0m {weight}")
        print(f"   \033[33m🔠 Suffix:\033[0m {suffix}")
        print(f"   \033[33m🔼 Upscale:\033[0m {upscale}")
        print()
        
        cmd = [
            CODEFORMER_VENV_PYTHON, CODEFORMER_SCRIPT_PATH,
            "-i", str(src_path),
            "-o", str(output_path),
            "-w", str(weight),
            "--suffix", suffix,
            "--upscale", str(upscale),
            "--no-open"
        ]
        
        result = subprocess.run(cmd, cwd=CODEFORMER_DIR)
        
        if result.returncode == 0:
            print(f"✅ \033[33mCompleted:\033[0m {len(input_paths)} file(s)")
            subprocess.run(['open', str(output_path)])
        else:
            print(f"❌ \033[33mFailed:\033[0m Processing failed")
            print("Check terminal output for details from inference_codeformer.py")
    else:
        print(f"\n🧠 Processing {len(input_paths)} file(s):")
        print(f"   \033[33m🧪 Weight:\033[0m {weight}")
        print(f"   \033[33m🔠 Suffix:\033[0m {suffix}")
        print(f"   \033[33m🔼 Upscale:\033[0m {upscale}")
        print()
        
        last_output_path = None
        for i, input_path in enumerate(input_paths, 1):
            output_path = pathlib.Path(input_path).parent / "Output" / "CF"
            output_path.mkdir(parents=True, exist_ok=True)
            print(f"Processing file {i}/{len(input_paths)}: {input_path}")
            print(f"   \033[33m📤 Output:\033[0m {output_path}")
            
            cmd = [
                CODEFORMER_VENV_PYTHON, CODEFORMER_SCRIPT_PATH,
                "-i", str(input_path),
                "-o", str(output_path),
                "-w", str(weight),
                "--suffix", suffix,
                "--upscale", str(upscale),
                "--no-open"
            ]
            
            result = subprocess.run(cmd, cwd=CODEFORMER_DIR)
            
            if result.returncode == 0:
                print(f"✅ \033[33mCompleted:\033[0m {input_path}")
            else:
                print(f"❌ \033[33mFailed:\033[0m {input_path}")
                print("Check terminal output for details from inference_codeformer.py")
            
            last_output_path = output_path
        
        if last_output_path and all(subprocess.run([CODEFORMER_VENV_PYTHON, CODEFORMER_SCRIPT_PATH, "-i", str(p), "-o", str(pathlib.Path(p).parent / "Output" / "CF"), "-w", str(weight), "--suffix", suffix, "--upscale", str(upscale), "--no-open"], cwd=CODEFORMER_DIR).returncode == 0 for p in input_paths):
            print(f"✅ \033[33mCompleted:\033[0m {len(input_paths)} file(s)")
            subprocess.run(['open', str(last_output_path)])
def main():
    os.system('clear')
    
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mCodeformer\033[0m")
        print("Face Restore & UpScale Tool")
        print("\033[92m==================================================\033[0m")
        print()
        
        input_files, input_mode, src_path = get_valid_inputs()
        
        # Get weight with manual default handling
        weight_input = input("\033[33mEnter weight (range 0.0–1.0, default 0.7):\033[0m\n > ").strip()
        try:
            weight_val = float(weight_input) if weight_input else 0.7
            if not 0.0 <= weight_val <= 1.0:
                raise ValueError("Weight must be between 0.0 and 1.0")
        except ValueError:
            print("⚠️  \033[33mUsing default weight 0.7\033[0m")
            weight_val = 0.7
        
        # Get suffix using get_string_input
        suffix = djj.get_string_input(
            "\033[33mEnter suffix (default '_CF'):\033[0m\n > ",
            default="_CF"
        )
        
        # Get upscale with manual default handling
        upscale_input = input("\033[33mEnter upscale factor (default 2):\033[0m\n > ").strip()
        try:
            upscale = int(upscale_input) if upscale_input else 2
            if not 1 <= upscale <= 10:
                raise ValueError("Upscale must be between 1 and 10")
        except ValueError:
            print("⚠️  \033[33mUsing default upscale factor 2\033[0m")
            upscale = 2
        
        print()
        
        # Process all files in one call
        process_files(input_files, input_mode, src_path, weight_val, suffix, upscale)
        
        print(f"\033[33m\n🏁 Done!\033[0m Processed {len(input_files)} file(s).")
        
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()