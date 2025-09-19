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
CODEFORMER_SCRIPT_PATH = "/Users/home/Documents/ai_models/CodeFormer/inference_codeformer.py"
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

def verify_models_exist():
    """Check if required models exist in the correct location"""
    required_models = [
        "weights/facelib/detection_Resnet50_Final.pth",
        "weights/CodeFormer/codeformer.pth"
    ]
    
    missing_models = []
    for model in required_models:
        model_path = pathlib.Path(CODEFORMER_DIR) / model
        if not model_path.exists():
            missing_models.append(str(model_path))
    
    if missing_models:
        print("\033[93m⚠️  Missing required CodeFormer models:\033[0m")
        for model in missing_models:
            print(f"   {model}")
        print()
        print("💡 \033[93mTo fix this, run these commands in Terminal:\033[0m")
        print("cd /Users/home/Documents/ai_models/CodeFormer/weights/facelib")
        print("mv facelib/* .")
        print("rmdir facelib")
        return False
    
    print("✅ \033[93mCodeFormer models found\033[0m")
    return True

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
    print("\033[1;33m🔍 Select files or folders to process\033[0m")
    
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

def get_processing_mode():
    """Get the processing mode from user"""
    print("\033[1;33m🛠️  Choose processing mode:\033[0m")
    print("\033[92m--------------------------------------------------\033[0m")
    print("1. 🤖 CodeFormer Only (Face restoration)")
    print("2. 🔼 Upscaler Only (Image enhancement)")
    print("3. 🤖➡️🔼 CodeFormer + Upscaler (Full workflow)")
    print("\033[92m--------------------------------------------------\033[0m")
    
    mode = djj.prompt_choice(
        "\033[93mSelect mode\033[0m",
        ['1', '2', '3'],
        default='1'
    )
    print()
    return mode

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

def upscale_files(input_files, upscaler_model, suffix, input_mode=None, src_path=None):
    """Upscale files using Real-ESRGAN via subprocess"""
    print(f"\n\033[1;33m🔼 Upscaling\033[0m {len(input_files)} \033[1;33mfile(s):\033[0m")
    print("---------------")
    print(f"\033[93m🤖 Model:\033[0m {upscaler_model['name']}")
    print(f"\033[93m📏 Scale:\033[0m {upscaler_model['scale']}x")
    print(f"\033[93m🔠 Suffix:\033[0m {suffix}")
    print("---------------")
    print()
    print("\033[1;33m🔼 Real-ESRGAN \033[0m\033[93mactivating...\033[0m")
    print()
    
    # Determine output path
    if input_mode == '1' and src_path:
        output_base = pathlib.Path(src_path) / "Upscaled"
    else:
        # Use first file's directory for output
        output_base = pathlib.Path(input_files[0]).parent / "Upscaled"
    
    output_base.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    error_count = 0
    
    for i, input_file in enumerate(input_files):
        file_name = os.path.basename(input_file)
        print(f"\033[93mUpscaling [{i+1}/{len(input_files)}]:\033[0m {file_name}")
        
        try:
            # Create output filename
            base_name = pathlib.Path(input_file).stem
            ext = pathlib.Path(input_file).suffix
            output_file = output_base / f"{base_name}_{suffix}{ext}"
            
            # Build Real-ESRGAN command
            cmd = [
                CODEFORMER_VENV_PYTHON, "-m", "realesrgan.inference_realesrgan",
                "-i", str(input_file),
                "-o", str(output_file),
                "-m", upscaler_model['path'],
                "-s", str(upscaler_model['scale']),
                "--tile", "400"
            ]
            
            # Run Real-ESRGAN
            result = subprocess.run(cmd,
                                  cwd=CODEFORMER_DIR,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  text=True,
                                  timeout=120)  # 2 minute timeout per file
            
            if result.returncode == 0:
                print(f"\033[92m✅ Success:\033[0m {file_name}")
                success_count += 1
            else:
                print(f"\033[93m❌ Failed:\033[0m {file_name}")
                error_count += 1
                
        except subprocess.TimeoutExpired:
            print(f"\033[93m⏰ Timeout:\033[0m {file_name} (upscaling took too long)")
            error_count += 1
        except Exception as e:
            print(f"\033[93m❌ Failed:\033[0m {file_name} - {str(e)}")
            error_count += 1
    
    print()
    print("=" * 50)
    print(f"\033[1;33m🏁 Upscaling Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {success_count} \033[93mfile(s)\033[0m")
    print(f"❌ \033[93mFailed:\033[0m {error_count} \033[93mfile(s)\033[0m")
    print("=" * 50)
    
    return str(output_base), success_count > 0

def process_codeformer_batch(input_paths, weight, suffix, upscale, save_faces, save_restored_faces):
    """Process multiple files with CodeFormer in batch mode"""
    print(f"\n\033[1;33m🧠 Processing\033[0m {len(input_paths)} \033[1;33mfile(s) with CodeFormer:\033[0m")
    print("---------------")
    print(f"\033[93m🧪 Weight:\033[0m {weight}")
    print(f"\033[93m🔠 Suffix:\033[0m {suffix}")
    print(f"\033[93m🔼 Upscale:\033[0m {upscale}")
    print(f"\033[93m👤 Save Cropped faces:\033[0m {'Yes' if save_faces else 'No'}")
    print(f"\033[93m🫅🏼 Save Restored faces:\033[0m {'Yes' if save_restored_faces else 'No'}")
    print("---------------")
    print()
    print("\033[1;33m🤖 CodeFormer 🤖 \033[0m\033[93mactivating...\033[0m")
    print()
    
    success_count = 0
    error_count = 0
    output_paths = set()
    processed_files = []
    
    for i, input_path in enumerate(input_paths):
        file_name = os.path.basename(input_path)
        print(f"\033[93mProcessing [{i+1}/{len(input_paths)}]:\033[0m {file_name}")
        
        output_path = pathlib.Path(input_path).parent / "CF"
        output_path.mkdir(parents=True, exist_ok=True)
        output_paths.add(output_path)
        
        cmd = [
            CODEFORMER_VENV_PYTHON, CODEFORMER_SCRIPT_PATH,
            "-i", str(input_path),
            "-o", str(output_path),
            "-w", str(weight),
            "--suffix", suffix,
            "--upscale", str(upscale),
            "--no-open"
        ]
        
        try:
            result = subprocess.run(cmd, cwd=CODEFORMER_DIR,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  text=True,
                                  timeout=300)
            
            if result.returncode == 0:
                print(f"\033[92m✅ Success:\033[0m {file_name}")
                success_count += 1
                
                # Track processed file location for potential upscaling
                base_name = pathlib.Path(input_path).stem
                processed_file = output_path / f"{base_name}_{suffix}.png"
                if processed_file.exists():
                    processed_files.append(str(processed_file))
                
                if not save_faces:
                    cleanup_cropped_faces(output_path)
                if not save_restored_faces:
                    cleanup_restored_faces(output_path)
                    
            else:
                print(f"\033[93m❌ Failed:\033[0m {file_name}")
                error_count += 1
                
        except subprocess.TimeoutExpired:
            print(f"\033[93m⏰ Timeout:\033[0m {file_name} (processing took too long)")
            error_count += 1
        except Exception as e:
            print(f"\033[93m❌ Exception:\033[0m {file_name} - {str(e)}")
            error_count += 1
    
    print()
    print("=" * 50)
    print(f"\033[1;33m🏁 CodeFormer Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {success_count} \033[93mfile(s)\033[0m")
    print(f"❌ \033[93mFailed:\033[0m {error_count} \033[93mfile(s)\033[0m")
    print("=" * 50)
    
    return list(output_paths), processed_files, success_count > 0

def main():
    os.system('clear')
    
    # Check if models exist before starting
    cf_ok = verify_models_exist()
    up_ok = verify_upscaler_models()
    
    if not cf_ok and not up_ok:
        print("\n\033[93mPlease fix the model paths first, then run this script again.\033[0m")
        sys.exit(1)
    
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mFace Restoration & Image Upscaler\033[0m")
        print("CodeFormer + Real-ESRGAN")
        print("\033[92m==================================================\033[0m")
        print()
        
        # Get processing mode first
        processing_mode = get_processing_mode()
        
        # Get input files
        input_files, input_mode, src_path = get_valid_inputs()
        
        # Mode-specific configurations
        if processing_mode in ['1', '3']:  # CodeFormer involved
            if not cf_ok:
                print("\033[93m❌ CodeFormer models not available. Please fix and restart.\033[0m")
                continue
                
            # Get CodeFormer settings
            weight_input = input("\033[93mEnter weight (range 0.0–1.0, default 0.7):\033[0m\n > ").strip()
            try:
                weight_val = float(weight_input) if weight_input else 0.7
                if not 0.0 <= weight_val <= 1.0:
                    raise ValueError("Weight must be between 0.0 and 1.0")
            except ValueError:
                print("⚠️  \033[93mUsing default weight 0.7\033[0m")
                weight_val = 0.7
            
            cf_suffix = djj.get_string_input(
                "\033[93mEnter CodeFormer suffix (default '_CF'):\033[0m\n > ",
                default="CF"
            )
            
            upscale_input = input("\033[93mEnter upscale factor (default 2):\033[0m\n > ").strip()
            try:
                upscale = int(upscale_input) if upscale_input else 2
                if not 1 <= upscale <= 10:
                    raise ValueError("Upscale must be between 1 and 10")
            except ValueError:
                print("⚠️  \033[93mUsing default upscale factor 2\033[0m")
                upscale = 2
            
            save_faces = djj.prompt_choice(
                "\033[93mSave cropped faces? \033[0m\n1. Yes, 2. No",
                ['1', '2'],
                default='2'
            ) == '1'
            
            save_restored_faces = djj.prompt_choice(
                "\033[93mSave restored faces? \033[0m\n1. Yes, 2. No",
                ['1', '2'],
                default='2'
            ) == '1'
            
            tag_source = djj.prompt_choice(
                "\033[93mTag source files with 'CF'?\033[0m\n1. Yes\n2. No",
                ['1', '2'],
                default='1'
                ) == '1'
        
        if processing_mode in ['2', '3']:  # Upscaler involved
            if not up_ok:
                print("\033[93m❌ Upscaler models not available. Please check paths.\033[0m")
                continue
                
            # Get upscaler settings
            upscaler_model = get_upscaler_model()
            upscaler_suffix = get_upscaler_suffix()
            
            if processing_mode == '3':
                tag_upscaled = djj.prompt_choice(
                    "\033[93mTag upscaled files with 'UP'?\033[0m\n1. Yes\n2. No",
                    ['1', '2'],
                    default='1'
                    ) == '1'
        
        os.system('clear')
        
        # Execute based on mode
        if processing_mode == '1':  # CodeFormer only
            if input_mode == '1':
                # Folder mode
                output_path = pathlib.Path(src_path) / "CF"
                output_path.mkdir(parents=True, exist_ok=True)
                
                cmd = [
                    CODEFORMER_VENV_PYTHON, CODEFORMER_SCRIPT_PATH,
                    "-i", str(src_path),
                    "-o", str(output_path),
                    "-w", str(weight_val),
                    "--suffix", cf_suffix,
                    "--upscale", str(upscale),
                    "--no-open"
                ]
                
                result = subprocess.run(cmd, cwd=CODEFORMER_DIR)
                
                if result.returncode == 0:
                    if not save_faces:
                        cleanup_cropped_faces(output_path)
                    if not save_restored_faces:
                        cleanup_restored_faces(output_path)
                    print(f"🎉 \033[93mSuccessfully processed \033[0m {len(input_files)} \033[93mfile(s)\033[0m")
                    print()
                    djj.prompt_open_folder(output_path)
                    if tag_source:
                        tag_source_files(input_files)
                else:
                    print(f"❌ \033[93mFailed:\033[0m Processing failed")
            else:
                # Multi-file mode
                output_paths, _, success = process_codeformer_batch(
                    input_files, weight_val, cf_suffix, upscale, save_faces, save_restored_faces)
                
                if success and tag_source:
                    tag_source_files(input_files)
                
                # Handle opening output folders
                if len(output_paths) == 1:
                    djj.prompt_open_folder(list(output_paths)[0])
                elif len(output_paths) > 1:
                    print(f"\033[93m📁 Created files in {len(output_paths)} different output folders.\033[0m")
                    open_choice = djj.prompt_choice(
                        "\033[93mOpen output folders?\033[0m\n1. Yes, open first one\n2. No",
                        ['1', '2'],
                        default='1'
                    )
                    if open_choice == '1':
                        first_folder = sorted(output_paths)[0]
                        subprocess.run(['open', str(first_folder)])
        
        elif processing_mode == '2':  # Upscaler only
            output_path, success = upscale_files(input_files, upscaler_model, upscaler_suffix, input_mode, src_path)
            if success and output_path:
                if processing_mode == '2' and 'tag_upscaled' in locals() and tag_upscaled:
                    # Find upscaled files for tagging
                    upscaled_files = list(pathlib.Path(output_path).glob(f"*_{upscaler_suffix}.*"))
                    if upscaled_files:
                        tag_source_files([str(f) for f in upscaled_files], "UP")
                djj.prompt_open_folder(output_path)
        
        elif processing_mode == '3':  # CodeFormer + Upscaler
            # Step 1: Run CodeFormer
            if input_mode == '1':
                # Folder mode - process all at once
                cf_output_path = pathlib.Path(src_path) / "CF"
                cf_output_path.mkdir(parents=True, exist_ok=True)
                
                cmd = [
                    CODEFORMER_VENV_PYTHON, CODEFORMER_SCRIPT_PATH,
                    "-i", str(src_path),
                    "-o", str(cf_output_path),
                    "-w", str(weight_val),
                    "--suffix", cf_suffix,
                    "--upscale", str(upscale),
                    "--no-open"
                ]
                
                result = subprocess.run(cmd, cwd=CODEFORMER_DIR)
                
                if result.returncode == 0:
                    if not save_faces:
                        cleanup_cropped_faces(cf_output_path)
                    if not save_restored_faces:
                        cleanup_restored_faces(cf_output_path)
                    
                    # Collect CodeFormer output files for upscaling
                    cf_files = list(cf_output_path.glob(f"*_{cf_suffix}.png"))
                    
                    if cf_files:
                        print(f"\n\033[93m➡️  Chaining to upscaler...\033[0m")
                        up_output_path, up_success = upscale_files([str(f) for f in cf_files], upscaler_model, upscaler_suffix)
                        
                        print(f"🎉 \033[93mFull workflow complete!\033[0m")
                        if tag_source:
                            tag_source_files(input_files)
                        if up_success and 'tag_upscaled' in locals() and tag_upscaled:
                            upscaled_files = list(pathlib.Path(up_output_path).glob(f"*_{upscaler_suffix}.*"))
                            if upscaled_files:
                                tag_source_files([str(f) for f in upscaled_files], "UP")
                        
                        # Offer to open both folders
                        open_choice = djj.prompt_choice(
                            "\033[93mWhich output to open?\033[0m\n1. CodeFormer results\n2. Final upscaled results\n3. Both\n4. None",
                            ['1', '2', '3', '4'],
                            default='2'
                        )
                        
                        if open_choice == '1':
                            subprocess.run(['open', str(cf_output_path)])
                        elif open_choice == '2':
                            subprocess.run(['open', up_output_path])
                        elif open_choice == '3':
                            subprocess.run(['open', str(cf_output_path)])
                            subprocess.run(['open', up_output_path])
                    else:
                        print("\033[93m⚠️  No CodeFormer output files found to upscale\033[0m")
                        djj.prompt_open_folder(cf_output_path)
                else:
                    print(f"❌ \033[93mFailed:\033[0m CodeFormer processing failed")
            else:
                # Multi-file mode
                cf_output_paths, processed_files, cf_success = process_codeformer_batch(
                    input_files, weight_val, cf_suffix, upscale, save_faces, save_restored_faces)
                
                if cf_success and processed_files:
                    print(f"\n\033[93m➡️  Chaining to upscaler...\033[0m")
                    up_output_path, up_success = upscale_files(processed_files, upscaler_model, upscaler_suffix)
                    
                    print(f"🎉 \033[93mFull workflow complete!\033[0m")
                    if tag_source:
                        tag_source_files(input_files)
                    if up_success and 'tag_upscaled' in locals() and tag_upscaled:
                        upscaled_files = list(pathlib.Path(up_output_path).glob(f"*_{upscaler_suffix}.*"))
                        if upscaled_files:
                            tag_source_files([str(f) for f in upscaled_files], "UP")
                    
                    # Handle opening multiple output folders
                    if len(cf_output_paths) == 1 and up_output_path:
                        open_choice = djj.prompt_choice(
                            "\033[93mWhich output to open?\033[0m\n1. CodeFormer results\n2. Final upscaled results\n3. Both\n4. None",
                            ['1', '2', '3', '4'],
                            default='2'
                        )
                        
                        if open_choice == '1':
                            subprocess.run(['open', str(list(cf_output_paths)[0])])
                        elif open_choice == '2':
                            subprocess.run(['open', up_output_path])
                        elif open_choice == '3':
                            subprocess.run(['open', str(list(cf_output_paths)[0])])
                            subprocess.run(['open', up_output_path])
                    else:
                        print(f"\033[93m📁 Workflow created files in multiple locations.\033[0m")
                        if up_output_path:
                            open_choice = djj.prompt_choice(
                                "\033[93mOpen final upscaled results?\033[0m\n1. Yes\n2. No",
                                ['1', '2'],
                                default='1'
                            )
                            if open_choice == '1':
                                subprocess.run(['open', up_output_path])
                else:
                    print("\033[93m⚠️  No CodeFormer output files found to upscale\033[0m")
                    # Just handle CF output folders
                    if len(cf_output_paths) == 1:
                        djj.prompt_open_folder(list(cf_output_paths)[0])
        
        print()
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()