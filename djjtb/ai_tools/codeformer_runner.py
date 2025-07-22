import os
import sys
import subprocess
import pathlib
import logging
import djjtb.utils as djj

# Supported extensions
SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi')

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
            # If it's a directory, collect files from it
            dir_files = collect_files_from_folder(path)
            files.extend(dir_files)
    
    return sorted(files, key=str.lower)

def get_valid_inputs():
    """Allow selecting multiple files and/or folders using prompt_choice"""
    print("🔍 Select files or folders to process")
    
    # Get input mode using prompt_choice
    input_mode = djj.prompt_choice(
        "\033[33mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths",
        ['1', '2'],
        default='1'
    )
    print()
    
    valid_paths = []
    
    if input_mode == '1':
        # Folder mode
        src_path = input("📁 \033[33mEnter folder path:\033[0m\n -> ").strip()
        src_path = clean_path(src_path)
        
        if not os.path.exists(src_path):
            print(f"❌ \033[33mPath does not exist:\033[0m {src_path}")
            sys.exit(1)
        
        if not os.path.isdir(src_path):
            print(f"❌ \033[33mPath is not a directory:\033[0m {src_path}")
            sys.exit(1)
        
        print()
        include_sub = djj.prompt_choice(
            "\033[33mInclude subfolders?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        
        valid_paths = collect_files_from_folder(src_path, include_sub)
        
    else:
        # File paths mode
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
    for i, file_path in enumerate(valid_paths[:5]):  # Show first 5
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
        "python3", "inference_codeformer.py",
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
        
        # Get weight using prompt_text with validation
        weight = djj.prompt_text(
            "\033[33mEnter weight\033[0m\n(range 0.0–1.0):",
            default="0.7"
        )
        try:
            weight_val = float(weight)
            if not (0.0 <= weight_val <= 1.0):
                raise ValueError
        except ValueError:
            print("⚠️  Invalid weight. Using default 0.7.")
            weight_val = 0.7
        
        # Get suffix
        suffix = djj.prompt_text(
            "\033[33mEnter suffix\033[0m\n(default *CF):",
            default="*CF"
        )
        if not suffix.strip():
            print("⚠️  \033[33mEmpty suffix not allowed. Using '_CF'.\033[0m")
            suffix = "_CF"
        
        # Get upscale factor
        upscale = djj.prompt_text(
            "\033[33mEnter upscale factor\033[0m\n(default 2):",
            default="2"
        )
        if not upscale.isdigit() or int(upscale) < 1:
            print("⚠️  \033[33mInvalid upscale. Using default 2.\033[0m")
            upscale = "2"
        
        print()
        
        # Process all files
        for input_path in input_files:
            process_file(input_path, weight_val, suffix, upscale)
        
        print(f"\033[33m\n🏁 Done!\033[0m Processed {len(input_files)} file(s).")
        
        # What next using the utils function
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()