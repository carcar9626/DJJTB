import os
import sys
import subprocess
import pathlib
import logging
import shutil
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

def cleanup_cropped_faces(output_path):
    """Remove the cropped_faces folder if it exists"""
    cropped_faces_path = pathlib.Path(output_path) / "cropped_faces"
    if cropped_faces_path.exists():
        import shutil
        try:
            shutil.rmtree(cropped_faces_path)
        except Exception as e:
            print(f"⚠️  Could not remove cropped faces folder: {e}")
            
def cleanup_restored_faces(output_path):
    """Remove the restored_faces folder if it exists"""
    restored_faces_path = pathlib.Path(output_path) / "restored_faces"
    if restored_faces_path.exists():
        import shutil
        try:
            shutil.rmtree(restored_faces_path)
        except Exception as e:
            print(f"⚠️  Could not remove restored faces folder: {e}")

def tag_source_files(file_paths, tag_name="CF"):
    """Add Finder tag to source files"""
    TAG_PATH = "/opt/homebrew/bin/tag"
    tagged_count = 0
    
    for file_path in file_paths:
        try:
            subprocess.run([TAG_PATH, "-a", tag_name, str(file_path)], check=True, capture_output=True)
            tagged_count += 1
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to tag {os.path.basename(file_path)}: {e}")
    
    if tagged_count > 0:
        print(f"\033[33m🏷️  Tagged\033[0m {tagged_count} \033[33mfile(s) with\033[0m '\033[92m{tag_name}\033[0m'")

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
    print("\033[1;33m🔍 Select files or folders to process\033[0m")
    
    input_mode = djj.prompt_choice(
        "\033[33mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
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
            print("\033[1;33m❌ No file paths provided.\033[0m")
            sys.exit(1)
        
        valid_paths = collect_files_from_paths(file_paths)
        print()
    
    if not valid_paths:
        print("❌ \033[1;33mNo valid files found.\033[0m")
        sys.exit(1)
    os.system('clear')
    print ("\n" * 2)
    print ("🔍 Detecting files...")
    print()
    print(f"\033[33m✅ Found\033[0m {len(valid_paths)} \033[33msupported file(s)\033[0m")
    print()
    print("Choose Your Options:")
    
    return valid_paths, input_mode, src_path if input_mode == '1' else None

def process_files(input_paths, input_mode, src_path, weight, suffix, upscale, save_faces, save_restored_faces, tag_source):
    if input_mode == '1':
        # Folder mode - process all files in one command
        output_path = pathlib.Path(src_path) / "CF"
        output_path.mkdir(parents=True, exist_ok=True)
        print("\n" * 2)
        print(f"\n\033[1;33m🧠 Processing \033[0m{len(input_paths)} \033[1;33mfile(s):\033[0m")
        print("---------------")
        print(f"\033[33m📥 Input folder:\033[0m {src_path}")
        print(f"\033[33m📤 Output:\033[0m {output_path}")
        print(f"\033[33m🧪 Weight:\033[0m {weight}")
        print(f"\033[33m🔠 Suffix:\033[0m {suffix}")
        print(f"\033[33m🔼 Upscale:\033[0m {upscale}")
        print(f"\033[33m👤 Save faces:\033[0m {'Yes' if save_faces else 'No'}")
        print(f"\033[33m🫅🏼 Save Restored faces:\033[0m {'Yes' if save_restored_faces else 'No'}")
        print("---------------")
        print()
        print("\033[1;33m🤖 CodeFormer 🤖 \033[0m\033[33mactivating...\033[0m")
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
        
        # Clean up cropped faces if user doesn't want them
        if result.returncode == 0:
            if not save_faces:
                cleanup_cropped_faces(output_path)
            if not save_restored_faces:
                cleanup_restored_faces(output_path)
            print(f"🎉 \033[33mSuccessfully processed \033[0m {len(input_paths)} \033[33mfile(s)\033[0m")
            subprocess.run(['open', str(output_path)])
            if tag_source:
                tag_source_files(input_paths)
        else:
            print(f"❌ \033[33mFailed:\033[0m Processing failed")
            print("Check terminal output for details from inference_codeformer.py")
    else:
        # Multi-file mode - let inference_codeformer.py handle all output
        # Just show basic setup info and stay quiet during processing
        print("\n" * 2)
        print(f"\n\033[1;33m🧠 Processing\033[0m {len(input_paths)} \033[1;33m file(s):\033[0m")
        print("---------------")
        print(f"\033[33m🧪 Weight:\033[0m {weight}")
        print(f"\033[33m🔠 Suffix:\033[0m {suffix}")
        print(f"\033[33m🔼 Upscale:\033[0m {upscale}")
        print(f"\033[33m👤 Save Cropped faces:\033[0m {'Yes' if save_faces else 'No'}")
        print(f"\033[33m🫅🏼 Save Restored faces:\033[0m {'Yes' if save_restored_faces else 'No'}")
        print("---------------")
        print()
        print("\033[1;33m🤖 CodeFormer 🤖 \033[0m\033[33mactivating...\033[0m")
        print()
        
        first_output_path = None
        
        for i, input_path in enumerate(input_paths):
            output_path = pathlib.Path(input_path).parent / "CF"
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Store the first output path to open later
            if first_output_path is None:
                first_output_path = output_path
            
            cmd = [
                CODEFORMER_VENV_PYTHON, CODEFORMER_SCRIPT_PATH,
                "-i", str(input_path),
                "-o", str(output_path),
                "-w", str(weight),
                "--suffix", suffix,
                "--upscale", str(upscale),
                "--no-open"
            ]
            
            # Let inference_codeformer.py handle all terminal output
            result = subprocess.run(cmd, cwd=CODEFORMER_DIR)
            
            # Clean up cropped faces if user doesn't want them
            if result.returncode == 0:
                if not save_faces:
                    cleanup_cropped_faces(output_path)
                if not save_restored_faces:
                    cleanup_restored_faces(output_path)
                if tag_source:
                    tag_source_files(input_paths)
        
        # Open only the first output folder at the end
        if first_output_path:
            subprocess.run(['open', str(first_output_path)])

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
            default="CF"
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
        
        # Ask about saving cropped faces
        save_faces = djj.prompt_choice(
            "\033[33mSave cropped faces? \033[0m\n1. Yes, 2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        
        save_restored_faces = djj.prompt_choice(
            "\033[33mSave restored faces? \033[0m\n1. Yes, 2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        
        tag_source = djj.prompt_choice(
            "\033[33mTag source files with 'CF'?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='1'
            ) == '1'
        os.system('clear')

        # Process all files in one call
        process_files(input_files, input_mode, src_path, weight_val, suffix, upscale, save_faces, save_restored_faces, tag_source)
        print()
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()