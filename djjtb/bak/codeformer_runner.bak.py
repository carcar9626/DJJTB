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
        print("\033[93m⚠️  Missing required models:\033[0m")
        for model in missing_models:
            print(f"   {model}")
        print()
        print("💡 \033[93mTo fix this, run these commands in Terminal:\033[0m")
        print("cd /Users/home/Documents/ai_models/CodeFormer/weights/facelib")
        print("mv facelib/* .")
        print("rmdir facelib")
        return False
    
    print("✅ \033[93mAll required models found\033[0m")
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
    print ("\n" * 2)
    print ("🔍 Detecting files...")
    print()
    print(f"\033[93m✅ Found\033[0m {len(valid_paths)} \033[93msupported file(s)\033[0m")
    print()
    print("Choose Your Options:")
    
    return valid_paths, input_mode, src_path if input_mode == '1' else None

def process_files_batch_mode(input_paths, weight, suffix, upscale, save_faces, save_restored_faces, tag_source):
    """Process multiple files in batch mode with consolidated output"""
    print("\n" * 2)
    print(f"\n\033[1;33m🧠 Processing\033[0m {len(input_paths)} \033[1;33mfile(s) in batch mode:\033[0m")
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
    output_paths = set()  # Use set to avoid duplicates
    
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
        
        # Run with reduced output - capture stdout/stderr to prevent excessive echoing
        try:
            result = subprocess.run(cmd, cwd=CODEFORMER_DIR,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  text=True,
                                  timeout=300)  # 5 minute timeout per file
            
            if result.returncode == 0:
                print(f"\033[92m✅ Success:\033[0m {file_name}")
                success_count += 1
                
                # Clean up unwanted folders
                if not save_faces:
                    cleanup_cropped_faces(output_path)
                if not save_restored_faces:
                    cleanup_restored_faces(output_path)
                    
            else:
                print(f"\033[93m❌ Failed:\033[0m {file_name}")
                error_output = result.stdout[-400:] if result.stdout else "No output"
                print(f"   Error: {error_output}")
                error_count += 1
                
        except subprocess.TimeoutExpired:
            print(f"\033[93m⏰ Timeout:\033[0m {file_name} (processing took too long)")
            error_count += 1
        except Exception as e:
            print(f"\033[93m❌ Exception:\033[0m {file_name} - {str(e)}")
            error_count += 1
    
    print()
    print("=" * 50)
    print(f"\033[1;33m🏁 Batch Processing Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {success_count} \033[93mfile(s)\033[0m")
    print(f"❌ \033[93mFailed:\033[0m {error_count} \033[93mfile(s)\033[0m")
    print("=" * 50)
    
    # Tag source files if requested
    if tag_source and success_count > 0:
        tag_source_files(input_paths)
    
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

def process_files(input_paths, input_mode, src_path, weight, suffix, upscale, save_faces, save_restored_faces, tag_source):
    if input_mode == '1':
        # Folder mode - process all files in one command
        output_path = pathlib.Path(src_path) / "CF"
        output_path.mkdir(parents=True, exist_ok=True)
        print("\n" * 2)
        print(f"\n\033[1;33m🧠 Processing \033[0m{len(input_paths)} \033[1;33mfile(s):\033[0m")
        print("---------------")
        print(f"\033[93m📥 Input folder:\033[0m {src_path}")
        print(f"\033[93m📤 Output:\033[0m {output_path}")
        print(f"\033[93m🧪 Weight:\033[0m {weight}")
        print(f"\033[93m🔠 Suffix:\033[0m {suffix}")
        print(f"\033[93m🔼 Upscale:\033[0m {upscale}")
        print(f"\033[93m👤 Save faces:\033[0m {'Yes' if save_faces else 'No'}")
        print(f"\033[93m🫅🏼 Save Restored faces:\033[0m {'Yes' if save_restored_faces else 'No'}")
        print("---------------")
        print()
        print("\033[1;33m🤖 CodeFormer 🤖 \033[0m\033[93mactivating...\033[0m")
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
        
        # Handle opening output folder with user prompt
        if result.returncode == 0:
            if not save_faces:
                cleanup_cropped_faces(output_path)
            if not save_restored_faces:
                cleanup_restored_faces(output_path)
            print(f"🎉 \033[93mSuccessfully processed \033[0m {len(input_paths)} \033[93mfile(s)\033[0m")
            print()
            djj.prompt_open_folder(output_path)
            if tag_source:
                tag_source_files(input_paths)
        else:
            print(f"❌ \033[93mFailed:\033[0m Processing failed")
            print("Check terminal output for details from inference_codeformer.py")
    else:
        # Multi-file mode - use new batch processing method
        process_files_batch_mode(input_paths, weight, suffix, upscale, save_faces, save_restored_faces, tag_source)

def main():
    os.system('clear')
    
    # Check if models exist before starting
    if not verify_models_exist():
        print("\n\033[93mPlease fix the model paths first, then run this script again.\033[0m")
        sys.exit(1)
    
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mCodeformer\033[0m")
        print("Face Restore & UpScale Tool")
        print("\033[92m==================================================\033[0m")
        print()
        
        input_files, input_mode, src_path = get_valid_inputs()
        
        # Get weight with manual default handling
        weight_input = input("\033[93mEnter weight (range 0.0–1.0, default 0.7):\033[0m\n > ").strip()
        try:
            weight_val = float(weight_input) if weight_input else 0.7
            if not 0.0 <= weight_val <= 1.0:
                raise ValueError("Weight must be between 0.0 and 1.0")
        except ValueError:
            print("⚠️  \033[93mUsing default weight 0.7\033[0m")
            weight_val = 0.7
        
        # Get suffix using get_string_input
        suffix = djj.get_string_input(
            "\033[93mEnter suffix (default '_CF'):\033[0m\n > ",
            default="CF"
        )
        
        # Get upscale with manual default handling
        upscale_input = input("\033[93mEnter upscale factor (default 2):\033[0m\n > ").strip()
        try:
            upscale = int(upscale_input) if upscale_input else 2
            if not 1 <= upscale <= 10:
                raise ValueError("Upscale must be between 1 and 10")
        except ValueError:
            print("⚠️  \033[93mUsing default upscale factor 2\033[0m")
            upscale = 2
        
        # Ask about saving cropped faces
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
        os.system('clear')

        # Process all files in one call
        process_files(input_files, input_mode, src_path, weight_val, suffix, upscale, save_faces, save_restored_faces, tag_source)
        print()
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()