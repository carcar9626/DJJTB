import os
import sys
import subprocess
import pathlib
import logging
import shutil
import time
import djjtb.utils as djj

# Supported extensions (images only - RealSR doesn't handle videos directly)
SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif')
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif')

# Path to RealSR executable and models
REALSR_EXECUTABLE = "/Users/home/Documents/ai_models/realsr-ncnn-vulkan-20220728-macos/realsr-ncnn-vulkan"
REALSR_DIR = "/Users/home/Documents/ai_models/realsr-ncnn-vulkan-20220728-macos"


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

def verify_executable_exists():
    """Check if RealSR executable exists"""
    exec_path = pathlib.Path(REALSR_EXECUTABLE)
    
    if not exec_path.exists():
        print("\033[93m⚠️  RealSR executable not found:\033[0m")
        print(f"   {REALSR_EXECUTABLE}")
        print()
        print("💡 \033[93mTo fix this:\033[0m")
        print("1. Make sure RealSR is downloaded and extracted")
        print("2. Update the REALSR_EXECUTABLE path in this script")
        print("3. Make the executable runnable: chmod +x realsr-ncnn-vulkan")
        return False
    
    # Check if it's executable
    if not os.access(exec_path, os.X_OK):
        print("\033[93m⚠️  RealSR executable is not executable:\033[0m")
        print(f"   {REALSR_EXECUTABLE}")
        print()
        print("💡 \033[93mTo fix this, run:\033[0m")
        print(f"chmod +x {REALSR_EXECUTABLE}")
        return False
    
    print("✅ \033[93mRealSR executable found and ready\033[0m")
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
    """Collect supported image files from folder(s)"""
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
    print("\033[1;33m🔍 Select image files or folders to process\033[0m")
    
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
        src_path = None
    
    if not valid_paths:
        print("❌ \033[1;33mNo valid image files found.\033[0m")
        sys.exit(1)
    
    os.system('clear')
    print ("\n" * 2)
    print ("🔍 Detecting files...")
    print()
    print(f"\033[93m✅ Found\033[0m {len(valid_paths)} \033[93msupported image file(s)\033[0m")
    print()
    print("Choose Your Options:")
    
    return valid_paths, input_mode, src_path if input_mode == '1' else None

def create_output_path(input_path, base_name="RealSR"):
    """Create output path following the pattern: /input/path/Output/RealSR"""
    input_path_obj = pathlib.Path(input_path)
    
    if input_path_obj.is_file():
        parent_dir = input_path_obj.parent
    else:
        parent_dir = input_path_obj
    
    output_path = parent_dir / "Output" / base_name
    output_path.mkdir(parents=True, exist_ok=True)
    
    return output_path

def show_patience_message(file_count, is_folder_mode=False):
    """Show a reassuring message about processing time"""
    print()
    print("\033[93m🧠 RealSR is crunching pixels silently...\033[0m")
    if is_folder_mode:
        print(f"   Processing \033[92m{file_count}\033[0m files in batch mode")
    else:
        print(f"   This may take a while for larger images")
    print("   \033[36m☕ Grab some coffee and watch your GPU work at 100%!\033[0m")
    print()

def process_single_image(input_file, output_dir, timeout_seconds=300):
    """Process a single image file with RealSR"""
    file_start_time = time.time()
    
    input_path = pathlib.Path(input_file)
    output_filename = f"{input_path.stem}_UP{input_path.suffix}"
    output_file = output_dir / output_filename
    
    # Build command
    cmd = [
        REALSR_EXECUTABLE,
        "-i", str(input_file),
        "-o", str(output_file),
    ]
    
        # Update output filename with new format
    output_filename = f"{input_path.stem}_UP"
    output_file = output_dir / output_filename
    cmd[-5] = str(output_file)  # Update the output path in command
    
    # Show patience message
    show_patience_message(1)
    
    try:
        result = subprocess.run(
            cmd,
            cwd=REALSR_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_seconds
        )
        
        file_elapsed = time.time() - file_start_time
        return result.returncode == 0, result.stdout, file_elapsed, str(output_file)
        
    except subprocess.TimeoutExpired:
        file_elapsed = time.time() - file_start_time
        return False, "Processing timeout", file_elapsed, None
    except Exception as e:
        file_elapsed = time.time() - file_start_time
        return False, str(e), file_elapsed, None

def process_folder_batch(input_folder, output_dir, file_count, timeout_seconds=600):
    """Process entire folder at once using RealSR batch mode"""
    folder_start_time = time.time()
    
    # Build command for folder processing
    cmd = [
        REALSR_EXECUTABLE,
        "-i", str(input_folder),
        "-o", str(output_dir),
    ]
    
    # Show patience message for batch processing
    show_patience_message(file_count, is_folder_mode=True)
    
    try:
        result = subprocess.run(
            cmd,
            cwd=REALSR_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_seconds
        )
        
        folder_elapsed = time.time() - folder_start_time
        return result.returncode == 0, result.stdout, folder_elapsed
        
    except subprocess.TimeoutExpired:
        folder_elapsed = time.time() - folder_start_time
        return False, "Processing timeout", folder_elapsed
    except Exception as e:
        folder_elapsed = time.time() - folder_start_time
        return False, str(e), folder_elapsed

def rename_batch_outputs(output_dir, suffix="_UP"):
    """Rename batch processed files to include the specified suffix"""
    renamed_count = 0
    
    for file_path in output_dir.glob('*'):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTS:
            # Check if it already has the suffix
            if not file_path.stem.endswith(suffix):
                new_name = f"{file_path.stem}{suffix}{file_path.suffix}"
                new_path = file_path.parent / new_name
                
                try:
                    file_path.rename(new_path)
                    renamed_count += 1
                except Exception as e:
                    print(f"⚠️  Could not rename {file_path.name}: {e}")
    
    if renamed_count > 0:
        print(f"\033[93m📝 Renamed\033[0m {renamed_count} \033[93mfile(s) with suffix\033[0m '{suffix}'")

def process_files_batch_mode(input_paths, tag_source):
    """Process multiple files individually with consolidated output"""
    overall_start_time = time.time()
    
    print("\n" * 2)
    print(f"\n\033[1;33m🔼 Processing\033[0m {len(input_paths)} \033[1;33mfile(s) individually:\033[0m")
    print("=" * 50)
    print()
    print("\033[1;33m🚀 RealSR \033[0m\033[93mactivating...\033[0m")
    print()
    
    success_count = 0
    error_count = 0
    output_paths = set()
    
    for i, input_path in enumerate(input_paths):
        file_name = os.path.basename(input_path)
        print(f"\033[93mProcessing [{i+1}/{len(input_paths)}]:\033[0m {file_name}")
        
        # Create output directory
        output_dir = create_output_path(input_path)
        output_paths.add(output_dir)
        
        success, output_msg, file_elapsed, output_file = process_single_image(
            input_path, output_dir
        )
        
        total_elapsed = time.time() - overall_start_time
        
        if success:
            print(f"\033[92m✅ Success:\033[0m {file_name}")
            print(f"  \033[36mFile time:\033[0m {format_elapsed_time(file_elapsed)}")
            print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
            if output_file:
                print(f"  \033[36mOutput:\033[0m {os.path.basename(output_file)}")
            success_count += 1
        else:
            print(f"\033[93m❌ Failed:\033[0m {file_name}")
            print(f"  \033[36mFile time:\033[0m {format_elapsed_time(file_elapsed)}")
            print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
            if "timeout" in output_msg.lower():
                print(f"   \033[93mTimeout:\033[0m Processing took too long")
            else:
                error_preview = output_msg[-200:] if output_msg else "No output"
                print(f"   Error: {error_preview}")
            error_count += 1
        
        print()
    
    # Final summary
    final_total_elapsed = time.time() - overall_start_time
    
    print("=" * 50)
    print(f"\033[1;33m🏁 Individual Processing Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {success_count} \033[93mfile(s)\033[0m")
    print(f"❌ \033[93mFailed:\033[0m {error_count} \033[93mfile(s)\033[0m")
    print(f"⏱️  \033[36mTotal processing time:\033[0m {format_elapsed_time(final_total_elapsed)}")
    print("=" * 50)
    
    # Tag source files if requested
    if tag_source and success_count > 0:
        tag_source_files(input_paths, "UP")
    
    # Handle opening output folders
    djj.open_multiple_folders(list(output_paths))

def process_files_folder_mode(input_paths, src_path, tag_source):
    """Process files using folder mode (more efficient for batch processing)"""
    overall_start_time = time.time()
    
    output_dir = create_output_path(src_path)
    
    print("\n" * 2)
    print(f"\n\033[1;33m🔼 Processing \033[0m{len(input_paths)} \033[1;33mfile(s) (folder mode):\033[0m")
    print("=" * 50)
    print(f"\033[93m📥 Input folder:\033[0m {src_path}")
    print(f"\033[93m📤 Output:\033[0m {output_dir}")
    print("=" * 50)
    print()
    print("\033[1;33m🚀 RealSR \033[0m\033[93mactivating...\033[0m")
    print()
    
    success, output_msg, folder_elapsed = process_folder_batch(
        src_path, output_dir, len(input_paths)
    )
    
    total_elapsed = time.time() - overall_start_time
    
    if success:
        # Rename files to include suffix
        rename_batch_outputs(output_dir, "_UP")
        
        print(f"🎉 \033[93mSuccessfully processed \033[0m {len(input_paths)} \033[93mfile(s)\033[0m")
        print(f"  \033[36mProcessing time:\033[0m{format_elapsed_time(folder_elapsed)}")
        print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
        print()
        
        # Tag source files if requested
        if tag_source:
            tag_source_files(input_paths, "UP")
        
        djj.prompt_open_folder(output_dir)
    else:
        print(f"❌ \033[93mFailed:\033[0m Processing failed")
        print(f"  \033[36mTime elapsed:\033[0m{format_elapsed_time(total_elapsed)}")
        print("Check terminal output for details from RealSR")
        if output_msg:
            print(f"Error details: {output_msg[-500:]}")  # Show last 500 chars

def process_files(input_paths, input_mode, src_path, tag_source):
    """Main processing dispatcher"""
    if input_mode == '1' and src_path:
        # Folder mode - use batch processing for efficiency
        process_files_folder_mode(input_paths, src_path, tag_source)
    else:
        # Multi-file mode - process individually
        process_files_batch_mode(input_paths, tag_source)

def main():
    os.system('clear')
    
    # Check if executable exists before starting
    if not verify_executable_exists():
        print("\n\033[93mPlease fix the executable path first, then run this script again.\033[0m")
        sys.exit(1)
    
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mRealSR Upscaler\033[0m")
        print("AI Image Upscaling Tool")
        print("\033[92m==================================================\033[0m")
        print()
        
        input_files, input_mode, src_path = get_valid_inputs()
        
                # Ask about tagging source files
        tag_source = djj.prompt_choice(
            "\033[93mTag source files with 'UP'?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='1'
        ) == '1'
        
        os.system('clear')
        
        # Process all files
        process_files(input_files, input_mode, src_path, tag_source)
        print()
        
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()