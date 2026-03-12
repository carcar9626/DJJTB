import os
import sys
import subprocess
import pathlib
import logging
import shutil
import time
import warnings
import djjtb.utils as djj

# Suppress common warnings
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', message='.*torchvision.transforms.functional_tensor.*')
warnings.filterwarnings('ignore', message='.*pretrained.*deprecated.*')

# Supported extensions
SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi')
IMAGE_EXTS = ('.jpg', '.jpeg', '.png')
VIDEO_EXTS = ('.mp4', '.mov', '.avi')

# Path to GFPGAN and virtual environment
GFPGAN_DIR = "/Users/home/Documents/ai_models/GFPGAN"
GFPGAN_MODEL_PATH = "/Users/home/Documents/ai_models/GFPGAN/experiments/pretrained_models/GFPGANv1.4.pth"
GFPGAN_VENV_PYTHON = "/Users/home/Documents/ai_models/GFPGAN/gfvenv/bin/python3"

def format_elapsed_time(seconds):
    """Format elapsed time in a readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.1f}s"

def verify_setup():
    """Check if GFPGAN model and directory exist"""
    issues = []
    
    if not os.path.exists(GFPGAN_DIR):
        issues.append(f"GFPGAN directory not found: {GFPGAN_DIR}")
        issues.append("  → Create it with: mkdir -p /Users/home/Documents/ai_models/GFPGAN")
    
    if not os.path.exists(GFPGAN_MODEL_PATH):
        issues.append(f"GFPGAN model not found: {GFPGAN_MODEL_PATH}")
        issues.append("  → Place your model in: /Users/home/Documents/ai_models/GFPGAN/experiments/pretrained_models/")
    
    if not os.path.exists(GFPGAN_VENV_PYTHON):
        issues.append(f"Python virtual environment not found: {GFPGAN_VENV_PYTHON}")
        issues.append("  → Create venv and install dependencies")
    
    if issues:
        print("\033[93m⚠️  Setup Issues Found:\033[0m")
        for issue in issues:
            print(f"   {issue}")
        print()
        return False
    
    print("✅ \033[93mGFPGAN setup verified\033[0m")
    return True

def clean_path(path_str):
    """Clean path string by removing quotes and whitespace"""
    return path_str.strip().strip('\'"')

def cleanup_cropped_faces(output_path):
    """Remove the cropped_faces folder if it exists"""
    cropped_faces_path = pathlib.Path(output_path) / "cropped_faces"
    if cropped_faces_path.exists():
        try:
            shutil.rmtree(cropped_faces_path)
        except Exception as e:
            print(f"⚠️  Could not remove cropped faces folder: {e}")

def cleanup_restored_faces(output_path):
    """Remove the restored_faces folder if it exists"""
    restored_faces_path = pathlib.Path(output_path) / "restored_faces"
    if restored_faces_path.exists():
        try:
            shutil.rmtree(restored_faces_path)
        except Exception as e:
            print(f"⚠️  Could not remove restored faces folder: {e}")

def cleanup_comparison(output_path):
    """Remove the cmp (comparison) folder if it exists"""
    cmp_path = pathlib.Path(output_path) / "cmp"
    if cmp_path.exists():
        try:
            shutil.rmtree(cmp_path)
        except Exception as e:
            print(f"⚠️  Could not remove comparison folder: {e}")

def tag_source_files(file_paths, tag_name="GF"):
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

def categorize_files(file_paths):
    """Separate files into images and videos"""
    images = []
    videos = []
    
    for file_path in file_paths:
        ext = pathlib.Path(file_path).suffix.lower()
        if ext in IMAGE_EXTS:
            images.append(file_path)
        elif ext in VIDEO_EXTS:
            videos.append(file_path)
    
    return images, videos

def check_output_exists(output_path, input_path, suffix):
    """Check if GFPGAN actually created output files"""
    input_name = pathlib.Path(input_path).stem
    
    # GFPGAN creates files in restored_imgs subfolder
    restored_imgs_path = pathlib.Path(output_path) / "restored_imgs"
    
    if not restored_imgs_path.exists():
        return False
    
    # Look for the output file with suffix
    expected_output = restored_imgs_path / f"{input_name}_{suffix}.png"
    
    return expected_output.exists()

def process_individual_file(input_path, output_path, upscale, suffix, current_num, total_files, timeout_seconds=600):
    """Process a single file with GFPGAN"""
    file_start_time = time.time()
    
    # Calculate percentage
    percentage = int((current_num / total_files) * 100)
    file_name = os.path.basename(input_path)
    
    print(f"\033[93mProcessing {current_num}/{total_files} ({percentage}%):\033[0m {file_name}")
    
    # GFPGAN command
    cmd = [
        GFPGAN_VENV_PYTHON, "-m", "inference_gfpgan",
        "-i", str(input_path),
        "-o", str(output_path),
        "-v", "1.4",
        "-s", str(upscale),
        "--suffix", suffix,
        "--bg_upsampler", "realesrgan"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=GFPGAN_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_seconds
        )
        
        file_elapsed = time.time() - file_start_time
        
        # Always check if output files exist (GFPGAN might error but still create files)
        output_files_exist = check_output_exists(output_path, input_path, suffix)
        
        return output_files_exist, "Success" if output_files_exist else result.stdout, file_elapsed
        
    except subprocess.TimeoutExpired:
        file_elapsed = time.time() - file_start_time
        output_files_exist = check_output_exists(output_path, input_path, suffix)
        return output_files_exist, "Timeout" if not output_files_exist else "Success", file_elapsed
    except Exception as e:
        file_elapsed = time.time() - file_start_time
        output_files_exist = check_output_exists(output_path, input_path, suffix)
        return output_files_exist, str(e) if not output_files_exist else "Success", file_elapsed

def process_folder_mode(input_paths, src_path, output_path, upscale, suffix, save_cropped, save_restored, save_comparison, tag_source):
    """Process all files in folder mode (faster, less verbose)"""
    overall_start_time = time.time()
    
    print("\n" * 2)
    print(f"\n\033[1;33m🧠 Processing\033[0m {len(input_paths)} \033[1;33mfile(s) (folder mode):\033[0m")
    print("---------------")
    print(f"\033[93m📥 Input folder:\033[0m {src_path}")
    print(f"\033[93m📤 Output:\033[0m {output_path}")
    print(f"\033[93m🔼 Upscale:\033[0m {upscale}")
    print(f"\033[93m🔠 Suffix:\033[0m {suffix}")
    print(f"\033[93m👤 Save Cropped faces:\033[0m {'Yes' if save_cropped else 'No'}")
    print(f"\033[93m🫅🏼 Save Restored faces:\033[0m {'Yes' if save_restored else 'No'}")
    print(f"\033[93m🔀 Save Comparison:\033[0m {'Yes' if save_comparison else 'No'}")
    print("---------------")
    print()
    print("\033[1;33m🤖 GFPGAN 🤖 \033[0m\033[93mactivating...\033[0m")
    print()
    
    print(f"\033[93mProcessing {len(input_paths)} files...\033[0m")
    print()
    
    # Process entire folder at once
    cmd = [
        GFPGAN_VENV_PYTHON, "-m", "inference_gfpgan",
        "-i", str(src_path),
        "-o", str(output_path),
        "-v", "1.4",
        "-s", str(upscale),
        "--suffix", suffix,
        "--bg_upsampler", "realesrgan"
    ]
    
    result = subprocess.run(
        cmd,
        cwd=GFPGAN_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    folder_elapsed = time.time() - overall_start_time
    
    # Check if files were created
    restored_imgs_path = pathlib.Path(output_path) / "restored_imgs"
    success = restored_imgs_path.exists() and any(restored_imgs_path.glob('*'))
    
    # Clean up unwanted folders regardless of success
    if not save_cropped:
        cleanup_cropped_faces(output_path)
    if not save_restored:
        cleanup_restored_faces(output_path)
    if not save_comparison:
        cleanup_comparison(output_path)
    
    if success:
        print(f"🎉 \033[93mSuccessfully processed\033[0m {len(input_paths)} \033[93mfile(s)\033[0m")
        print(f"  \033[36mProcessing time:\033[0m {format_elapsed_time(folder_elapsed)}")
        print()
        
        if tag_source:
            tag_source_files(input_paths)
        
        djj.prompt_open_folder(output_path)
    else:
        print(f"⚠️  \033[93mNo output files created\033[0m")
        print(f"  \033[36mTime elapsed:\033[0m {format_elapsed_time(folder_elapsed)}")
        print("  Check GFPGAN setup and model files")

def process_multifile_mode(input_paths, upscale, suffix, save_cropped, save_restored, save_comparison, tag_source):
    """Process files one at a time with detailed progress"""
    overall_start_time = time.time()
    
    print("\n" * 2)
    print(f"\n\033[1;33m🧠 Processing\033[0m {len(input_paths)} \033[1;33mfile(s) in multi-file mode:\033[0m")
    print("---------------")
    print(f"\033[93m🔼 Upscale:\033[0m {upscale}")
    print(f"\033[93m🔠 Suffix:\033[0m {suffix}")
    print(f"\033[93m👤 Save Cropped faces:\033[0m {'Yes' if save_cropped else 'No'}")
    print(f"\033[93m🫅🏼 Save Restored faces:\033[0m {'Yes' if save_restored else 'No'}")
    print(f"\033[93m🔀 Save Comparison:\033[0m {'Yes' if save_comparison else 'No'}")
    print("---------------")
    print()
    print("\033[1;33m🤖 GFPGAN 🤖 \033[0m\033[93mactivating...\033[0m")
    print()
    
    success_count = 0
    output_paths = set()
    
    for i, input_path in enumerate(input_paths, start=1):
        file_name = os.path.basename(input_path)
        file_ext = pathlib.Path(input_path).suffix.lower()
        
        output_path = pathlib.Path(input_path).parent / "GFPGAN"
        output_path.mkdir(parents=True, exist_ok=True)
        output_paths.add(output_path)
        
        # Longer timeout for videos
        timeout = 480 if file_ext in VIDEO_EXTS else 300
        
        success, output_msg, file_elapsed = process_individual_file(
            input_path, output_path, upscale, suffix, i, len(input_paths), timeout
        )
        
        total_elapsed = time.time() - overall_start_time
        
        if success:
            print(f"\033[92m✅ Success:\033[0m {file_name}")
            print(f"  \033[36mFile time:\033[0m {format_elapsed_time(file_elapsed)}")
            print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
            success_count += 1
        
        print()
    
    # Clean up folders after all processing
    for output_path in output_paths:
        if not save_cropped:
            cleanup_cropped_faces(output_path)
        if not save_restored:
            cleanup_restored_faces(output_path)
        if not save_comparison:
            cleanup_comparison(output_path)
    
    # Final summary
    final_total_elapsed = time.time() - overall_start_time
    
    print("=" * 50)
    print(f"\033[1;33m🏁 Processing Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {success_count}/{len(input_paths)} \033[93mfile(s)\033[0m")
    print(f"⏱️  \033[36mTotal processing time:\033[0m {format_elapsed_time(final_total_elapsed)}")
    print("=" * 50)
    print()
    
    if tag_source and success_count > 0:
        tag_source_files(input_paths)
    
    # Handle opening output folders
    if len(output_paths) == 1:
        output_path = list(output_paths)[0]
        djj.prompt_open_folder(output_path)
    elif len(output_paths) > 1:
        print(f"\033[93m📁 Created files in {len(output_paths)} different output folders.\033[0m")
        open_choice = djj.prompt_choice(
            "\033[93mOpen output folders?\033[0m\n1. Yes, open all\n2. Yes, open first one only\n3. No",
            ['1', '2', '3'],
            default='2'
        )
        
        if open_choice == '1':
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
            first_folder = sorted(output_paths)[0]
            subprocess.run(['open', str(first_folder)])
            print(f"\033[92m✓ Opened: {first_folder}\033[0m")

def process_files(input_paths, input_mode, src_path, upscale, suffix, save_cropped, save_restored, save_comparison, tag_source):
    """Main processing dispatcher"""
    images, videos = categorize_files(input_paths)
    
    if input_mode == '1' and src_path and not videos:
        # Folder mode - fast processing
        output_path = pathlib.Path(src_path) / "GFPGAN"
        output_path.mkdir(parents=True, exist_ok=True)
        
        process_folder_mode(input_paths, src_path, output_path, upscale, suffix,
                          save_cropped, save_restored, save_comparison, tag_source)
    else:
        # Multi-file mode - detailed progress
        process_multifile_mode(input_paths, upscale, suffix,
                             save_cropped, save_restored, save_comparison, tag_source)

def main():
    os.system('clear')
    
    # Verify setup
    if not verify_setup():
        print("\n\033[93mPlease fix the setup issues first, then run this script again.\033[0m")
        sys.exit(1)
    
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mGFPGAN Face Restoration\033[0m")
        print("Enhance & Upscale Tool")
        print("\033[92m==================================================\033[0m")
        print()
        
        input_files, input_mode, src_path = get_valid_inputs()
        
        # Get upscale factor
        upscale_input = input("\033[93mEnter upscale factor (1-4, default 2):\033[0m\n > ").strip()
        try:
            upscale = int(upscale_input) if upscale_input else 2
            if not 1 <= upscale <= 4:
                raise ValueError("Upscale must be between 1 and 4")
        except ValueError:
            print("⚠️  \033[93mUsing default upscale factor 2\033[0m")
            upscale = 2
        
        # Get suffix
        suffix = djj.get_string_input(
            "\033[93mEnter suffix (default '_GF'):\033[0m\n > ",
            default="GF"
        )
        
        # Ask about saving cropped faces
        save_cropped = djj.prompt_choice(
            "\033[93mSave cropped faces?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        
        # Ask about saving restored faces
        save_restored = djj.prompt_choice(
            "\033[93mSave restored faces?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        
        # Ask about saving comparison images
        save_comparison = djj.prompt_choice(
            "\033[93mSave comparison images?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        
        # Ask about tagging
        tag_source = djj.prompt_choice(
            "\033[93mTag source files with 'GF'?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='1'
        ) == '1'
        
        os.system('clear')
        
        # Process all files
        process_files(input_files, input_mode, src_path, upscale, suffix,
                     save_cropped, save_restored, save_comparison, tag_source)
        
        print()
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()