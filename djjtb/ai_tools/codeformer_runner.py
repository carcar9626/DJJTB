import os
import sys
import subprocess
import pathlib
import logging
import shutil
import time
import select
import djjtb.utils as djj

# Supported extensions
SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi')
IMAGE_EXTS = ('.jpg', '.jpeg', '.png')
VIDEO_EXTS = ('.mp4', '.mov', '.avi')

# Path to CodeFormer model scripts and virtual environment
CODEFORMER_SCRIPT_PATH = "/Users/home/Documents/ai_models/CodeFormer/inference_codeformer.py"
CODEFORMER_VENV_PYTHON = "/Users/home/Documents/ai_models/CodeFormer/cfvenv/bin/python3"
CODEFORMER_DIR = "/Users/home/Documents/ai_models/CodeFormer"

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

def run_process_with_live_output(cmd, cwd, timeout_seconds=600):
    """
    Run subprocess with live output streaming while also capturing for error reporting.
    Returns success, captured_output, elapsed_time
    """
    import subprocess
    import time
    import select
    import sys
    
    start_time = time.time()
    captured_output = []
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        # Live stream output while capturing it
        while True:
            # Check if process is still running
            if process.poll() is not None:
                break
                
            # Check for timeout
            if time.time() - start_time > timeout_seconds:
                process.kill()
                elapsed = time.time() - start_time
                return False, "Processing timeout", elapsed
            
            # Read available output
            try:
                ready, _, _ = select.select([process.stdout], [], [], 0.1)
                if ready:
                    line = process.stdout.readline()
                    if line:
                        print(line.rstrip())  # Show live output
                        captured_output.append(line.rstrip())
            except:
                pass
        
        # Get any remaining output
        remaining_output, _ = process.communicate()
        if remaining_output:
            remaining_lines = remaining_output.strip().split('\n')
            for line in remaining_lines:
                if line.strip():
                    print(line)
                    captured_output.append(line)
        
        elapsed = time.time() - start_time
        success = process.returncode == 0
        full_output = '\n'.join(captured_output)
        
        return success, full_output, elapsed
        
    except Exception as e:
        elapsed = time.time() - start_time
        return False, str(e), elapsed

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

def process_folder_images(src_path, output_path, weight, suffix, upscale, save_faces, save_restored_faces):
    """Process all images in a folder using folder mode with live output and timing"""
    
    cmd = [
        CODEFORMER_VENV_PYTHON, CODEFORMER_SCRIPT_PATH,
        "-i", str(src_path),
        "-o", str(output_path),
        "-w", str(weight),
        "--suffix", suffix,
        "--upscale", str(upscale),
        "--no-open"
    ]
    
    # Add some visual separation for the processing output
    print("   " + "=" * 60)
    print("   \033[36mFolder Processing - Live Output:\033[0m")
    print("   " + "=" * 60)
    
    success, output_msg, folder_elapsed = run_process_with_live_output(cmd, CODEFORMER_DIR, 1200)  # 20 min timeout for folders
    
    print("   " + "=" * 60)
    
    if success:
        if not save_faces:
            cleanup_cropped_faces(output_path)
        if not save_restored_faces:
            cleanup_restored_faces(output_path)
    
    return success, folder_elapsed


def process_individual_file(input_path, output_path, weight, suffix, upscale, timeout_seconds=600):
    """Process a single file (video or image) with live output streaming and timing"""
    
    cmd = [
        CODEFORMER_VENV_PYTHON, CODEFORMER_SCRIPT_PATH,
        "-i", str(input_path),
        "-o", str(output_path),
        "-w", str(weight),
        "--suffix", suffix,
        "--upscale", str(upscale),
        "--no-open"
    ]
    
    # Show what's being processed with some spacing for readability
    print(f"   \033[36mProcessing:\033[0m {os.path.basename(input_path)}")
    print("   " + "-" * 50)
    
    success, output_msg, file_elapsed = run_process_with_live_output(cmd, CODEFORMER_DIR, timeout_seconds)
    
    print("   " + "-" * 50)
    
    return success, output_msg, file_elapsed

def process_files_batch_mode(input_paths, weight, suffix, upscale, save_faces, save_restored_faces, tag_source):
    """Process multiple files in batch mode with consolidated output"""
    overall_start_time = time.time()
    
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
    
    # Categorize files
    images, videos = categorize_files(input_paths)
    
    for i, input_path in enumerate(input_paths):
        file_name = os.path.basename(input_path)
        file_ext = pathlib.Path(input_path).suffix.lower()
        
        print(f"\033[93mProcessing [{i+1}/{len(input_paths)}]:\033[0m {file_name}")
        
        output_path = pathlib.Path(input_path).parent / "CF"
        output_path.mkdir(parents=True, exist_ok=True)
        output_paths.add(output_path)
        
        # Use longer timeout for videos but not excessive - 8 mins instead of 20
        timeout = 480 if file_ext in VIDEO_EXTS else 300  # 8 mins for video, 5 mins for images
        
        success, output_msg, file_elapsed = process_individual_file(input_path, output_path, weight, suffix, upscale, timeout)
        
        # Calculate total elapsed time
        total_elapsed = time.time() - overall_start_time
        
        if success:
            print(f"\033[92m✅ Success:\033[0m {file_name}")
            print(f"   \033[36mFile time:\033[0m {format_elapsed_time(file_elapsed)}")
            print(f"   \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
            success_count += 1
            
            # Clean up unwanted folders
            if not save_faces:
                cleanup_cropped_faces(output_path)
            if not save_restored_faces:
                cleanup_restored_faces(output_path)
                
        else:
            print(f"\033[93m❌ Failed:\033[0m {file_name}")
            print(f"   \033[36mFile time:\033[0m {format_elapsed_time(file_elapsed)}")
            print(f"   \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
            if "timeout" in output_msg.lower():
                print(f"   \033[93mTimeout:\033[0m Processing took too long")
            else:
                error_preview = output_msg[-200:] if output_msg else "No output"
                print(f"   Error: {error_preview}")
            error_count += 1
        
        print()  # Add spacing between files
    
    # Final summary with total time
    final_total_elapsed = time.time() - overall_start_time
    
    print("=" * 50)
    print(f"\033[1;33m🏁 Batch Processing Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {success_count} \033[93mfile(s)\033[0m")
    print(f"❌ \033[93mFailed:\033[0m {error_count} \033[93mfile(s)\033[0m")
    print(f"⏱️  \033[36mTotal processing time:\033[0m {format_elapsed_time(final_total_elapsed)}")
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

def process_files_smart_mode(input_paths, src_path, weight, suffix, upscale, save_faces, save_restored_faces, tag_source):
    """Smart processing: Use folder mode for images when possible, individual processing for videos"""
    overall_start_time = time.time()
    images, videos = categorize_files(input_paths)
    
    print("\n" * 2)
    print(f"\n\033[1;33m🧠 Smart Processing Mode:\033[0m")
    print(f"   \033[93mImages:\033[0m {len(images)} file(s)")
    print(f"   \033[93mVideos:\033[0m {len(videos)} file(s)")
    print("---------------")
    print(f"\033[93m🧪 Weight:\033[0m {weight}")
    print(f"\033[93m🔠 Suffix:\033[0m {suffix}")
    print(f"\033[93m🔼 Upscale:\033[0m {upscale}")
    print(f"\033[93m👤 Save Cropped faces:\033[0m {'Yes' if save_faces else 'No'}")
    print(f"\033[93m🫅🏼 Save Restored faces:\033[0m {'Yes' if save_restored_faces else 'No'}")
    print("---------------")
    print()
    
    success_count = 0
    error_count = 0
    output_paths = set()
    
    # Process images in folder mode if they're all from the same directory
    if images:
        # Check if all images are from the same directory as src_path
        all_same_dir = all(pathlib.Path(img).parent == pathlib.Path(src_path) for img in images)
        
        if all_same_dir and src_path:
            print("\033[1;33m🤖 CodeFormer 🤖 \033[0m\033[93mactivating for images (folder mode)...\033[0m")
            folder_start_time = time.time()
            
            output_path = pathlib.Path(src_path) / "CF"
            output_path.mkdir(parents=True, exist_ok=True)
            output_paths.add(output_path)
            
            # Create a temporary folder with only the images for processing
            temp_img_dir = pathlib.Path(src_path) / "temp_images_for_cf"
            temp_img_dir.mkdir(exist_ok=True)
            
            try:
                # Copy images to temp directory
                for img in images:
                    shutil.copy2(img, temp_img_dir)
                
                # Process the temp directory
                if process_folder_images(temp_img_dir, output_path, weight, suffix, upscale, save_faces, save_restored_faces):
                    folder_elapsed = time.time() - folder_start_time
                    total_elapsed = time.time() - overall_start_time
                    
                    print(f"\033[92m✅ Folder Mode Success:\033[0m {len(images)} image(s)")
                    print(f"  \033[36mFolder time:\033[0m {format_elapsed_time(folder_elapsed)}")
                    print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
                    success_count += len(images)
                else:
                    folder_elapsed = time.time() - folder_start_time
                    total_elapsed = time.time() - overall_start_time
                    
                    print(f"\033[93m❌ Folder Mode Failed:\033[0m {len(images)} image(s)")
                    print(f"  \033[36mFolder time:\033[0m {format_elapsed_time(folder_elapsed)}")
                    print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
                    error_count += len(images)
                
                # Clean up temp directory
                shutil.rmtree(temp_img_dir)
                
            except Exception as e:
                folder_elapsed = time.time() - folder_start_time
                total_elapsed = time.time() - overall_start_time
                
                print(f"\033[93m❌ Folder Mode Error:\033[0m {e}")
                print(f"  \033[36mFolder time:\033[0m {format_elapsed_time(folder_elapsed)}")
                print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
                
                # Clean up temp directory if it exists
                if temp_img_dir.exists():
                    shutil.rmtree(temp_img_dir)
                # Fall back to individual processing
                print("\033[93mFalling back to individual image processing...\033[0m")
                for img in images:
                    output_path = pathlib.Path(img).parent / "CF"
                    output_path.mkdir(parents=True, exist_ok=True)
                    output_paths.add(output_path)
                    success, _, file_elapsed = process_individual_file(img, output_path, weight, suffix, upscale, 300)
                    
                    current_total_elapsed = time.time() - overall_start_time
                    
                    if success:
                        print(f"\033[92m✅ Success:\033[0m {os.path.basename(img)}")
                        print(f"  \033[36mFile time:\033[0m {format_elapsed_time(file_elapsed)}")
                        print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(current_total_elapsed)}")
                        success_count += 1
                        if not save_faces:
                            cleanup_cropped_faces(output_path)
                        if not save_restored_faces:
                            cleanup_restored_faces(output_path)
                    else:
                        print(f"\033[93m❌ Failed:\033[0m {os.path.basename(img)}")
                        print(f"  \033[36mFile time:\033[0m {format_elapsed_time(file_elapsed)}")
                        print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(current_total_elapsed)}")
                        error_count += 1
        else:
            # Process images individually
            print("\033[1;33m🤖 CodeFormer 🤖 \033[0m\033[93mactivating for images (individual mode)...\033[0m")
            for i, img in enumerate(images):
                file_name = os.path.basename(img)
                print(f"\033[93mProcessing image [{i+1}/{len(images)}]:\033[0m {file_name}")
                
                output_path = pathlib.Path(img).parent / "CF"
                output_path.mkdir(parents=True, exist_ok=True)
                output_paths.add(output_path)
                
                success, output_msg, file_elapsed = process_individual_file(img, output_path, weight, suffix, upscale, 300)
                total_elapsed = time.time() - overall_start_time
                
                if success:
                    print(f"\033[92m✅ Success:\033[0m {file_name}")
                    print(f"  \033[36mFile time:\033[0m {format_elapsed_time(file_elapsed)}")
                    print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
                    success_count += 1
                    if not save_faces:
                        cleanup_cropped_faces(output_path)
                    if not save_restored_faces:
                        cleanup_restored_faces(output_path)
                else:
                    print(f"\033[93m❌ Failed:\033[0m {file_name}")
                    print(f"  \033[36mFile time:\033[0m {format_elapsed_time(file_elapsed)}")
                    print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
                    error_count += 1
                print()
    
    # Process videos individually
    if videos:
        print()
        print("\033[1;33m🤖 CodeFormer 🤖 \033[0m\033[93mactivating for videos...\033[0m")
        
        for i, video in enumerate(videos):
            file_name = os.path.basename(video)
            print(f"\033[93mProcessing video [{i+1}/{len(videos)}]:\033[0m {file_name}")
            
            output_path = pathlib.Path(video).parent / "CF"
            output_path.mkdir(parents=True, exist_ok=True)
            output_paths.add(output_path)
            
            # Timeout for videos - reduced from 20 mins to 8 mins since frame processing is usually done quickly
            success, output_msg, file_elapsed = process_individual_file(video, output_path, weight, suffix, upscale, 480)
            total_elapsed = time.time() - overall_start_time
            
            if success:
                print(f"\033[92m✅ Success:\033[0m {file_name}")
                print(f"  \033[36mFile time:\033[0m {format_elapsed_time(file_elapsed)}")
                print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
                success_count += 1
                if not save_faces:
                    cleanup_cropped_faces(output_path)
                if not save_restored_faces:
                    cleanup_restored_faces(output_path)
            else:
                print(f"\033[93m❌ Failed:\033[0m {file_name}")
                print(f"  \033[36mFile time:\033[0m {format_elapsed_time(file_elapsed)}")
                print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
                if "timeout" in output_msg.lower():
                    print(f"   \033[93mTimeout:\033[0m Video processing took too long")
                else:
                    error_preview = output_msg[-200:] if output_msg else "No output"
                    print(f"   Error: {error_preview}")
                error_count += 1
            print()
    
    # Final summary with total time
    final_total_elapsed = time.time() - overall_start_time
    
    print("=" * 50)
    print(f"\033[1;33m🏁 Smart Processing Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {success_count} \033[93mfile(s)\033[0m")
    print(f"❌ \033[93mFailed:\033[0m {error_count} \033[93mfile(s)\033[0m")
    print(f"⏱️  \033[36mTotal processing time:\033[0m {format_elapsed_time(final_total_elapsed)}")
    print("=" * 50)(f"✅ \033[92mSuccessful:\033[0m {success_count} \033[93mfile(s)\033[0m")
    print(f"❌ \033[93mFailed:\033[0m {error_count} \033[93mfile(s)\033[0m")
    print("=" * 50)
    
    # Tag source files if requested
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

def process_files(input_paths, input_mode, src_path, weight, suffix, upscale, save_faces, save_restored_faces, tag_source):
    """Main processing dispatcher"""
    images, videos = categorize_files(input_paths)
    
    if input_mode == '1' and src_path and not videos:
        # Folder mode with only images - use original efficient method
        overall_start_time = time.time()
        
        output_path = pathlib.Path(src_path) / "CF"
        output_path.mkdir(parents=True, exist_ok=True)
        print("\n" * 2)
        print(f"\n\033[1;33m🧠 Processing \033[0m{len(input_paths)} \033[1;33mfile(s) (folder mode):\033[0m")
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
        
        success, folder_elapsed = process_folder_images(src_path, output_path, weight, suffix, upscale, save_faces, save_restored_faces)
        
        total_elapsed = time.time() - overall_start_time
        
        if success:
            print(f"🎉 \033[93mSuccessfully processed \033[0m {len(input_paths)} \033[93mfile(s)\033[0m")
            print(f"  \033[36mProcessing time:\033[0m {format_elapsed_time(folder_elapsed)}")
            print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
            print()
            djj.prompt_open_folder(output_path)
            if tag_source:
                tag_source_files(input_paths)
        else:
            print(f"❌ \033[93mFailed:\033[0m Processing failed")
            print(f"  \033[36mTime elapsed:\033[0m {format_elapsed_time(total_elapsed)}")
            print("Check terminal output for details from inference_codeformer.py")
    
    elif input_mode == '1' and src_path:
        # Folder mode with mixed content - use smart mode
        process_files_smart_mode(input_paths, src_path, weight, suffix, upscale, save_faces, save_restored_faces, tag_source)
    
    else:
        # Multi-file mode - use batch processing
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

        # Process all files
        process_files(input_files, input_mode, src_path, weight_val, suffix, upscale, save_faces, save_restored_faces, tag_source)
        print()
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()