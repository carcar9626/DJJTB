import os
import sys
import subprocess
import pathlib
import logging
import shutil
import djjtb.utils as djj

# Supported extensions
SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')

# Path to CodeFormer virtual environment (we'll use it for Real-ESRGAN)
CODEFORMER_VENV_PYTHON = "/Users/home/Documents/ai_models/CodeFormer/cfvenv/bin/python3"
CODEFORMER_DIR = "/Users/home/Documents/ai_models/CodeFormer"

# Upscaler models and paths
UPSCALER_MODELS = {
    '1': {
        'name': 'RealESRGAN 4x+ (Best General)',
        'path': '/Users/home/Documents/ai_models/upscalers/RealESRGAN_x4plus.pth',
        'scale': 4
    },
    '2': {
        'name': '4x UltraSharp (Detailed/Anime)',
        'path': '/Users/home/Documents/ai_models/upscalers/4x-UltraSharp.pth',
        'scale': 4
    },
    '3': {
        'name': 'RealESRGAN 2x (Subtle)',
        'path': '/Users/home/Documents/ai_models/upscalers/RealESRGAN_x2.pth',
        'scale': 2
    }
}

def verify_upscaler_models():
    """Check if upscaler models exist and Real-ESRGAN is available"""
    missing_models = []
    for key, model_info in UPSCALER_MODELS.items():
        if not pathlib.Path(model_info['path']).exists():
            missing_models.append(f"{model_info['name']}: {model_info['path']}")
    
    if missing_models:
        print("\033[93m⚠️  Missing upscaler models:\033[0m")
        for model in missing_models:
            print(f"   {model}")
        print()
        return False
    
    # Check if Real-ESRGAN is available in cfvenv
    try:
        result = subprocess.run([
            CODEFORMER_VENV_PYTHON, "-c", "import realesrgan"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print("\033[93m⚠️  Real-ESRGAN not installed in cfvenv.\033[0m")
            print("💡 \033[93mTo install Real-ESRGAN:\033[0m")
            print(f"   cd {CODEFORMER_DIR}")
            print("   source cfvenv/bin/activate")
            print("   pip install realesrgan")
            print()
            return False
    except Exception as e:
        print(f"\033[93m⚠️  Could not check Real-ESRGAN installation: {e}\033[0m")
        return False
    
    print("✅ \033[93mUpscaler models and Real-ESRGAN found\033[0m")
    return True

def clean_path(path_str):
    """Clean path string by removing quotes and whitespace"""
    return path_str.strip().strip('\'"')

def tag_source_files(file_paths, tag_name="UP"):
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
        print(f"\033[93m🏷️  Tagged\033[0m {tagged_count} \033[93mfile(s) with\033[0m '\033[92m{tag_name}\033[0m'")

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
    print("\033[1;33m🔍 Select files or folders to upscale\033[0m")
    
    input_mode = djj.prompt_choice(
        "\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
        ['1', '2'],
        default='1'
    )
    print()
    
    valid_paths = []
    
    if input_mode == '1':
        src_path = djj.get_path_input("Enter folder path")
        print()
        
        include_sub = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        
        valid_paths = collect_files_from_folder(src_path, include_sub)
        
    else:
        file_paths = input("📁 \033[93mEnter file paths (space-separated):\033[0m\n -> ").strip()
        
        if not file_paths:
            print("\033[1;33m❌ No file paths provided.\033[0m")
            sys.exit(1)
        
        valid_paths = collect_files_from_paths(file_paths)
        print()
    
    if not valid_paths:
        print("❌ \033[1;33mNo valid files found.\033[0m")
        sys.exit(1)
    
    os.system('clear')
    print("\n" * 2)
    print("🔍 Detecting files...")
    print()
    print(f"\033[93m✅ Found\033[0m {len(valid_paths)} \033[93msupported file(s)\033[0m")
    print()
    print("Choose Your Options:")
    
    return valid_paths, input_mode, src_path if input_mode == '1' else None

def get_upscaler_model():
    """Get upscaler model selection from user"""
    print("\033[1;33m🔼 Choose upscaler model:\033[0m")
    print("\033[92m--------------------------------------------------\033[0m")
    for key, model_info in UPSCALER_MODELS.items():
        print(f"{key}. {model_info['name']} ({model_info['scale']}x)")
    print("\033[92m--------------------------------------------------\033[0m")
    
    choice = djj.prompt_choice(
        "\033[93mSelect upscaler model\033[0m",
        list(UPSCALER_MODELS.keys()),
        default='1'
    )
    print()
    return UPSCALER_MODELS[choice]

def get_upscaler_suffix(default_suffix="upscaled"):
    """Get suffix for upscaled files"""
    suffix = djj.get_string_input(
        f"\033[93mEnter upscaler suffix (default '_{default_suffix}'):\033[0m\n > ",
        default=default_suffix
    )
    return suffix

def upscale_files_batch_mode(input_paths, upscaler_model, suffix, tag_output):
    """Process multiple files in batch mode with individual outputs"""
    print("\n" * 2)
    print(f"\n\033[1;33m🔼 Upscaling\033[0m {len(input_paths)} \033[1;33mfile(s) in batch mode:\033[0m")
    print("---------------")
    print(f"\033[93m🤖 Model:\033[0m {upscaler_model['name']}")
    print(f"\033[93m📏 Scale:\033[0m {upscaler_model['scale']}x")
    print(f"\033[93m🔠 Suffix:\033[0m {suffix}")
    print("---------------")
    print()
    print("\033[1;33m🔼 Real-ESRGAN 🔼 \033[0m\033[93mactivating...\033[0m")
    print()
    
    success_count = 0
    error_count = 0
    output_paths = set()  # Use set to avoid duplicates
    upscaled_files = []
    
    for i, input_path in enumerate(input_paths):
        file_name = os.path.basename(input_path)
        print(f"\033[93mUpscaling [{i+1}/{len(input_paths)}]:\033[0m {file_name}")
        
        output_dir = pathlib.Path(input_path).parent / "Upscaled"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_paths.add(output_dir)
        
        # Create output filename
        base_name = pathlib.Path(input_path).stem
        ext = pathlib.Path(input_path).suffix
        output_file = output_dir / f"{base_name}_{suffix}{ext}"
        
        # Build Real-ESRGAN command
        cmd = [
            CODEFORMER_VENV_PYTHON, "-m", "realesrgan.inference_realesrgan",
            "-i", str(input_path),
            "-o", str(output_file),
            "-m", upscaler_model['path'],
            "-s", str(upscaler_model['scale']),
            "--tile", "400"
        ]
        
        # Run with reduced output - capture stdout/stderr to prevent excessive echoing
        try:
            result = subprocess.run(cmd, cwd=CODEFORMER_DIR,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  text=True,
                                  timeout=180)  # 3 minute timeout per file
            
            if result.returncode == 0:
                print(f"\033[92m✅ Success:\033[0m {file_name}")
                success_count += 1
                upscaled_files.append(str(output_file))
                    
            else:
                print(f"\033[93m❌ Failed:\033[0m {file_name}")
                error_output = result.stdout[-400:] if result.stdout else "No output"
                print(f"   Error: {error_output}")
                error_count += 1
                
        except subprocess.TimeoutExpired:
            print(f"\033[93m⏰ Timeout:\033[0m {file_name} (upscaling took too long)")
            error_count += 1
        except Exception as e:
            print(f"\033[93m❌ Exception:\033[0m {file_name} - {str(e)}")
            error_count += 1
    
    print()
    print("=" * 50)
    print(f"\033[1;33m🏁 Upscaling Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {success_count} \033[93mfile(s)\033[0m")
    print(f"❌ \033[93mFailed:\033[0m {error_count} \033[93mfile(s)\033[0m")
    print("=" * 50)
    
    # Tag upscaled files if requested
    if tag_output and success_count > 0 and upscaled_files:
        tag_source_files(upscaled_files, "UP")
    
    # Handle opening output folders
    if len(output_paths) == 1:
        # Single output folder - use standard prompt
        output_path = list(output_paths)[0]
        djj.prompt_open_folder(output_path)
    elif len(output_paths) > 1:
        # Multiple output folders - ask user
        print(f"\033[93m📁 Created files in {len(output_paths)} different output folders.\033[0m")
        open_choice = djj.prompt_choice(
            "\033[93mOpen output folders?\033[0m\n1. Yes, open all\n2. Yes, open first one only\n3. No",
            ['1', '2', '3'],
            default='2'
        )
        
        if open_choice == '1':
            # Open all folders (limited to 5 to avoid overwhelming)
            folders_opened = 0
            for output_path in sorted(output_paths):
                if folders_opened < 5:
                    subprocess.run(['open', str(output_path)])
                    folders_opened += 1
                else:
                    break
            if len(output_paths) > 5:
                print(f"\033[93mNote: Opened first 5 folders. Total: {len(output_paths)}\033[0m")
        elif open_choice == '2':
            # Open just the first folder
            first_folder = sorted(output_paths)[0]
            subprocess.run(['open', str(first_folder)])
            print(f"\033[92m✓ Opened: {first_folder}\033[0m")

def upscale_files_folder_mode(input_files, src_path, upscaler_model, suffix, tag_output):
    """Process folder mode - all files in one output folder"""
    output_dir = pathlib.Path(src_path) / "Upscaled"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" * 2)
    print(f"\n\033[1;33m🔼 Upscaling \033[0m{len(input_files)} \033[1;33mfile(s):\033[0m")
    print("---------------")
    print(f"\033[93m📥 Input folder:\033[0m {src_path}")
    print(f"\033[93m📤 Output:\033[0m {output_dir}")
    print(f"\033[93m🤖 Model:\033[0m {upscaler_model['name']}")
    print(f"\033[93m📏 Scale:\033[0m {upscaler_model['scale']}x")
    print(f"\033[93m🔠 Suffix:\033[0m {suffix}")
    print("---------------")
    print()
    print("\033[1;33m🔼 Real-ESRGAN 🔼 \033[0m\033[93mactivating...\033[0m")
    print()
    
    success_count = 0
    error_count = 0
    upscaled_files = []
    
    for i, input_path in enumerate(input_files):
        file_name = os.path.basename(input_path)
        print(f"\033[93mUpscaling [{i+1}/{len(input_files)}]:\033[0m {file_name}")
        
        # Create output filename
        base_name = pathlib.Path(input_path).stem
        ext = pathlib.Path(input_path).suffix
        output_file = output_dir / f"{base_name}_{suffix}{ext}"
        
        # Build Real-ESRGAN command
        cmd = [
            CODEFORMER_VENV_PYTHON, "-m", "realesrgan.inference_realesrgan",
            "-i", str(input_path),
            "-o", str(output_file),
            "-m", upscaler_model['path'],
            "-s", str(upscaler_model['scale']),
            "--tile", "400"
        ]
        
        try:
            result = subprocess.run(cmd, cwd=CODEFORMER_DIR,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  text=True,
                                  timeout=180)
            
            if result.returncode == 0:
                print(f"\033[92m✅ Success:\033[0m {file_name}")
                success_count += 1
                upscaled_files.append(str(output_file))
            else:
                print(f"\033[93m❌ Failed:\033[0m {file_name}")
                error_count += 1
                
        except subprocess.TimeoutExpired:
            print(f"\033[93m⏰ Timeout:\033[0m {file_name} (upscaling took too long)")
            error_count += 1
        except Exception as e:
            print(f"\033[93m❌ Exception:\033[0m {file_name} - {str(e)}")
            error_count += 1
    
    print()
    print("=" * 50)
    print(f"\033[1;33m🏁 Upscaling Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {success_count} \033[93mfile(s)\033[0m")
    print(f"❌ \033[93mFailed:\033[0m {error_count} \033[93mfile(s)\033[0m")
    print("=" * 50)
    
    # Tag upscaled files if requested
    if tag_output and success_count > 0 and upscaled_files:
        tag_source_files(upscaled_files, "UP")
    
    # Handle opening output folder
    if success_count > 0:
        print(f"🎉 \033[93mSuccessfully upscaled \033[0m {success_count} \033[93mfile(s)\033[0m")
        print()
        djj.prompt_open_folder(output_dir)
    else:
        print(f"❌ \033[93mFailed:\033[0m Processing failed")

def main():
    os.system('clear')
    
    # Check if models exist before starting
    if not verify_upscaler_models():
        print("\n\033[93mPlease install Real-ESRGAN and ensure model paths are correct, then run this script again.\033[0m")
        sys.exit(1)
    
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mImage Upscaler\033[0m")
        print("Real-ESRGAN Image Enhancement Tool")
        print("\033[92m==================================================\033[0m")
        print()
        
        input_files, input_mode, src_path = get_valid_inputs()
        
        # Get upscaler settings
        upscaler_model = get_upscaler_model()
        upscaler_suffix = get_upscaler_suffix()
        
        tag_output = djj.prompt_choice(
            "\033[93mTag upscaled files with 'UP'?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='1'
            ) == '1'
        
        os.system('clear')
        
        # Execute based on input mode
        if input_mode == '1':
            # Folder mode
            upscale_files_folder_mode(input_files, src_path, upscaler_model, upscaler_suffix, tag_output)
        else:
            # Multi-file mode
            upscale_files_batch_mode(input_files, upscaler_model, upscaler_suffix, tag_output)
        
        print()
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()