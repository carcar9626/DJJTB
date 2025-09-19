import os
import sys
import subprocess
import pathlib
import logging
import shutil
import time
import uuid
import djjtb.utils as djj

# Supported extensions
SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi', '.webm', '.mkv')

# Path to FaceFusion model scripts and virtual environment
FACEFUSION_SCRIPT_PATH = "/Users/home/Documents/ai_models/facefusion/facefusion.py"
FACEFUSION_VENV_PYTHON = "/Users/home/Documents/ai_models/facefusion/ffvenv/bin/python3"
FACEFUSION_DIR = "/Users/home/Documents/ai_models/facefusion"

def verify_facefusion_exists():
    """Check if FaceFusion installation exists"""
    required_paths = [
        FACEFUSION_SCRIPT_PATH,
        FACEFUSION_VENV_PYTHON,
        FACEFUSION_DIR
    ]
    
    missing_paths = []
    for path in required_paths:
        if not pathlib.Path(path).exists():
            missing_paths.append(path)
    
    if missing_paths:
        print("\033[93m⚠️  Missing FaceFusion components:\033[0m")
        for path in missing_paths:
            print(f"   {path}")
        return False
    
    print("✅ \033[93mFaceFusion installation found\033[0m")
    return True

def clean_path(path_str):
    """Clean path string by removing quotes and whitespace"""
    return path_str.strip().strip('\'"')

def tag_source_files(file_paths, tag_name="FF"):
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

def get_swap_mode():
    """Get face swap mode from user"""
    print("\033[1;93m🔄 Select Face Swap Mode\033[0m")
    
    mode = djj.prompt_choice(
        "\033[93mSwap Mode:\033[0m\n1. Single source TO multiple targets (one face → many images/videos)\n2. Single source TO single target (one face → one image/video)\n3. Multiple sources TO single target (many faces → one image/video)\n",
        ['1', '2', '3'],
        default='1'
    )
    print()
    return mode

def get_source_input(mode):
    """Get source files/folders based on swap mode"""
    if mode == '3':
        # Multiple sources to single target - get source folder/files
        print("\033[1;93m📁 Source Selection (Multiple Sources)\033[0m")
        
        input_mode = djj.prompt_choice(
            "\033[93mSource input mode:\033[0m\n1. Folder containing source faces\n2. Space-separated source file paths\n",
            ['1', '2'],
            default='1'
        )
        print()
        
        if input_mode == '1':
            src_path = djj.get_path_input("Enter source folder path")
            print()
            
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            
            source_files = collect_files_from_folder(src_path, include_sub)
            return source_files, 'folder', src_path
            
        else:
            file_paths = input("📁 \033[93mEnter source file paths (space-separated):\033[0m\n -> ").strip()
            
            if not file_paths:
                print("\033[1;93m❌ No file paths provided.\033[0m")
                sys.exit(1)
            
            source_files = collect_files_from_paths(file_paths)
            print()
            return source_files, 'files', None
    
    else:
        # Single source (modes 1 and 2)
        print("\033[1;93m📁 Source Selection (Single Source)\033[0m")
        source_path = djj.get_path_input("Enter source face file path")
        print()
        
        # Validate source file
        source_path_obj = pathlib.Path(source_path)
        if not source_path_obj.exists() or source_path_obj.suffix.lower() not in SUPPORTED_EXTS:
            print(f"\033[93m❌ Invalid source file: {source_path}\033[0m")
            sys.exit(1)
            
        return [str(source_path_obj)], 'single_file', None

def get_target_input(mode):
    """Get target files/folders based on swap mode"""
    if mode == '3':
        # Multiple sources to single target
        print("\033[1;93m🎯 Target Selection (Single Target)\033[0m")
        target_path = djj.get_path_input("Enter target file path")
        print()
        
        # Validate target file
        target_path_obj = pathlib.Path(target_path)
        if not target_path_obj.exists() or target_path_obj.suffix.lower() not in SUPPORTED_EXTS:
            print(f"\033[93m❌ Invalid target file: {target_path}\033[0m")
            sys.exit(1)
            
        return [str(target_path_obj)], 'single_file', None
    
    elif mode == '1':
        # Single source to multiple targets
        print("\033[1;93m🎯 Target Selection (Multiple Targets)\033[0m")
        
        input_mode = djj.prompt_choice(
            "\033[93mTarget input mode:\033[0m\n1. Folder containing target images/videos\n2. Space-separated target file paths\n",
            ['1', '2'],
            default='1'
        )
        print()
        
        if input_mode == '1':
            target_path = djj.get_path_input("Enter target folder path")
            print()
            
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            
            target_files = collect_files_from_folder(target_path, include_sub)
            return target_files, 'folder', target_path
            
        else:
            file_paths = input("📁 \033[93mEnter target file paths (space-separated):\033[0m\n -> ").strip()
            
            if not file_paths:
                print("\033[1;93m❌ No file paths provided.\033[0m")
                sys.exit(1)
            
            target_files = collect_files_from_paths(file_paths)
            print()
            return target_files, 'files', None
            
    else:
        # Mode 2: Single source to single target
        print("\033[1;93m🎯 Target Selection (Single Target)\033[0m")
        target_path = djj.get_path_input("Enter target file path")
        print()
        
        # Validate target file
        target_path_obj = pathlib.Path(target_path)
        if not target_path_obj.exists() or target_path_obj.suffix.lower() not in SUPPORTED_EXTS:
            print(f"\033[93m❌ Invalid target file: {target_path}\033[0m")
            sys.exit(1)
            
        return [str(target_path_obj)], 'single_file', None

def get_output_path_and_suffix(source_files, target_files, mode):
    """Determine output path and get suffix preference based on inputs"""
    
    output_choice = djj.prompt_choice(
        "\033[93mOutput location:\033[0m\n1. Same folder as sources (creates 'Output/FF' subfolder)\n2. Same folder as targets (creates 'Output/FF' subfolder)\n3. Custom path\n",
        ['1', '2', '3'],
        default='1' if mode in ['2', '3'] else '2'  # Default to source for single/multi-to-single, target for single-to-multi
    )
    print()
    
    if output_choice == '1':
        # Same as source folder
        base_path = pathlib.Path(source_files[0]).parent
        
    elif output_choice == '2':
        # Same as target folder
        base_path = pathlib.Path(target_files[0]).parent
        
    else:
        # Custom path
        custom_path = djj.get_path_input("Enter custom output folder path")
        base_path = pathlib.Path(custom_path)
    
    # Create Output/FF structure
    output_path = base_path / "Output" / "FF"
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get suffix preference
    suffix_choice = djj.prompt_choice(
        "\033[93mAdd '_FF' suffix to filenames?\033[0m\n1. Yes\n2. No",
        ['1', '2'],
        default='1'
    ) == '1'
    
    return str(output_path), suffix_choice

def generate_output_filename(source_file, target_file, output_path, add_suffix=True):
    """Generate output filename based on source and target"""
    source_name = pathlib.Path(source_file).stem
    target_name = pathlib.Path(target_file).stem
    target_ext = pathlib.Path(target_file).suffix
    
    if add_suffix:
        output_filename = f"{target_name}_FF{target_ext}"
    else:
        output_filename = f"{target_name}{target_ext}"
    
    return str(pathlib.Path(output_path) / output_filename)

def process_single_headless(source_file, target_file, output_file):
    """Process single source to single target using headless-run"""
    cmd = [
        FACEFUSION_VENV_PYTHON, FACEFUSION_SCRIPT_PATH, "headless-run",
        "-s", str(source_file),
        "-t", str(target_file),
        "-o", str(output_file)
    ]
    
    try:
        result = subprocess.run(cmd, cwd=FACEFUSION_DIR,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              text=True,
                              timeout=300)  # 5 minute timeout per file
        
        return result.returncode == 0, result.stdout if result.stdout else "No output"
    except subprocess.TimeoutExpired:
        return False, "Timeout (processing took too long)"
    except Exception as e:
        return False, str(e)

def process_batch_job(source_file, target_files, output_path, add_suffix=True):
    """Process single source to multiple targets using job system"""
    
    # Generate unique job ID
    job_id = f"ff_batch_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    print(f"\033[93m📋 Creating job:\033[0m {job_id}")
    
    # Step 1: Create job
    cmd_create = [
        FACEFUSION_VENV_PYTHON, FACEFUSION_SCRIPT_PATH, "job-create", job_id
    ]
    
    try:
        result = subprocess.run(cmd_create, cwd=FACEFUSION_DIR,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True,
                              timeout=30)
        
        if result.returncode != 0:
            print(f"\033[93m❌ Failed to create job:\033[0m {result.stderr}")
            return 0, len(target_files), [f"Job creation failed: {result.stderr}"]
            
    except Exception as e:
        print(f"\033[93m❌ Exception creating job:\033[0m {str(e)}")
        return 0, len(target_files), [f"Job creation exception: {str(e)}"]
    
    print(f"\033[92m✅ Job created successfully\033[0m")
    
    # Step 2: Add steps for each target
    print(f"\033[93m📝 Adding {len(target_files)} steps to job...\033[0m")
    
    added_steps = 0
    for target_file in target_files:
        output_file = generate_output_filename(source_file, target_file, output_path, add_suffix)
        
        cmd_add_step = [
            FACEFUSION_VENV_PYTHON, FACEFUSION_SCRIPT_PATH, "job-add-step", job_id,
            "-s", str(source_file),
            "-t", str(target_file),
            "-o", str(output_file)
        ]
        
        try:
            result = subprocess.run(cmd_add_step, cwd=FACEFUSION_DIR,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  text=True,
                                  timeout=30)
            
            if result.returncode == 0:
                added_steps += 1
            else:
                print(f"\033[93m⚠️  Failed to add step for:\033[0m {os.path.basename(target_file)}")
                
        except Exception as e:
            print(f"\033[93m⚠️  Exception adding step for:\033[0m {os.path.basename(target_file)} - {str(e)}")
    
    print(f"\033[92m✅ Added {added_steps}/{len(target_files)} steps\033[0m")
    
    if added_steps == 0:
        print("\033[93m❌ No steps added successfully. Aborting job.\033[0m")
        return 0, len(target_files), ["No steps could be added to job"]
    
    # Step 3: Submit job
    print(f"\033[93m📤 Submitting job...\033[0m")
    cmd_submit = [
        FACEFUSION_VENV_PYTHON, FACEFUSION_SCRIPT_PATH, "job-submit", job_id
    ]
    
    try:
        result = subprocess.run(cmd_submit, cwd=FACEFUSION_DIR,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True,
                              timeout=30)
        
        if result.returncode != 0:
            print(f"\033[93m❌ Failed to submit job:\033[0m {result.stderr}")
            return 0, len(target_files), [f"Job submission failed: {result.stderr}"]
            
    except Exception as e:
        print(f"\033[93m❌ Exception submitting job:\033[0m {str(e)}")
        return 0, len(target_files), [f"Job submission exception: {str(e)}"]
    
    print(f"\033[92m✅ Job submitted successfully\033[0m")
    
    # Step 4: Run job
    print(f"\033[93m🚀 Running job... (this may take a while)\033[0m")
    cmd_run = [
        FACEFUSION_VENV_PYTHON, FACEFUSION_SCRIPT_PATH, "job-run", job_id
    ]
    
    success_count = 0
    error_count = 0
    error_messages = []
    
    try:
        result = subprocess.run(cmd_run, cwd=FACEFUSION_DIR,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              text=True,
                              timeout=len(target_files) * 300)  # 5 minutes per target
        
        if result.returncode == 0:
            print(f"\033[92m✅ Job completed successfully\033[0m")
            
            # Count successful outputs (files that exist)
            for target_file in target_files:
                output_file = generate_output_filename(source_file, target_file, output_path, add_suffix)
                if pathlib.Path(output_file).exists():
                    success_count += 1
                else:
                    error_count += 1
                    error_messages.append(f"Output not created for {os.path.basename(target_file)}")
        else:
            print(f"\033[93m❌ Job failed:\033[0m {result.stdout}")
            error_count = len(target_files)
            error_messages.append(f"Job execution failed: {result.stdout}")
            
    except subprocess.TimeoutExpired:
        print(f"\033[93m⏰ Job timeout:\033[0m Processing took too long")
        error_count = len(target_files)
        error_messages.append("Job execution timed out")
    except Exception as e:
        print(f"\033[93m❌ Exception running job:\033[0m {str(e)}")
        error_count = len(target_files)
        error_messages.append(f"Job execution exception: {str(e)}")
    
    return success_count, error_count, error_messages

def process_face_swap(mode, source_files, target_files, output_path, add_suffix, tag_source):
    """Main processing function that routes to appropriate method"""
    
    print("\n" * 2)
    print(f"\n\033[1;93m🔄 Processing Face Swaps:\033[0m")
    print("\033[92m=\033[0m" * 50)
    if mode == '1':
        print(f"\033[93m📁 Source:\033[0m {os.path.basename(source_files[0])}")
        print(f"\033[93m🎯 Targets:\033[0m {len(target_files)} file(s)")
        mode_desc = "Single source TO multiple targets"
    elif mode == '2':
        print(f"\033[93m📁 Source:\033[0m {os.path.basename(source_files[0])}")
        print(f"\033[93m🎯 Target:\033[0m {os.path.basename(target_files[0])}")
        mode_desc = "Single source TO single target"
    else:  # mode == '3'
        print(f"\033[93m📁 Sources:\033[0m {len(source_files)} file(s)")
        print(f"\033[93m🎯 Target:\033[0m {os.path.basename(target_files[0])}")
        mode_desc = "Multiple sources TO single target"
    
    print(f"\033[93m🔄 Mode:\033[0m {mode_desc}")
    print(f"\033[93m📤 Output:\033[0m {output_path}")
    print(f"\033[93m🏷️  Add suffix:\033[0m {'Yes' if add_suffix else 'No'}")
    print("\033[92m=\033[0m" * 50)
    print()
    print("\033[1;93m🎭 FaceFusion 🎭 \033[0m\033[93mactivating...\033[0m")
    print()
    
    success_count = 0
    error_count = 0
    error_messages = []
    
    if mode == '2':
        # Single source to single target - use headless-run
        source_file = source_files[0]
        target_file = target_files[0]
        output_file = generate_output_filename(source_file, target_file, output_path, add_suffix)
        
        print(f"\033[93mProcessing:\033[0m {os.path.basename(source_file)} → {os.path.basename(target_file)}")
        
        success, error_msg = process_single_headless(source_file, target_file, output_file)
        
        if success:
            print(f"\033[92m✅ Success:\033[0m Face swap completed!")
            success_count = 1
        else:
            print(f"\033[93m❌ Failed:\033[0m {error_msg}")
            error_count = 1
            error_messages.append(error_msg)
    
    elif mode == '1':
        # Single source to multiple targets - use job system
        source_file = source_files[0]
        success_count, error_count, error_messages = process_batch_job(source_file, target_files, output_path, add_suffix)
    
    else:  # mode == '3'
        # Multiple sources to single target - process each source individually
        target_file = target_files[0]
        
        for i, source_file in enumerate(source_files):
            source_name = os.path.basename(source_file)
            print(f"\033[93mProcessing [{i+1}/{len(source_files)}]:\033[0m {source_name}")
            
            # Generate unique output filename for each source
            source_stem = pathlib.Path(source_file).stem
            target_stem = pathlib.Path(target_file).stem
            target_ext = pathlib.Path(target_file).suffix
            
            if add_suffix:
                output_filename = f"{source_stem}_to_{target_stem}_FF{target_ext}"
            else:
                output_filename = f"{source_stem}_to_{target_stem}{target_ext}"
            
            output_file = str(pathlib.Path(output_path) / output_filename)
            
            success, error_msg = process_single_headless(source_file, target_file, output_file)
            
            if success:
                print(f"\033[92m✅ Success:\033[0m {source_name}")
                success_count += 1
            else:
                print(f"\033[93m❌ Failed:\033[0m {source_name}")
                print(f"   Error: {error_msg}")
                error_count += 1
                error_messages.append(f"{source_name}: {error_msg}")
    
    print()
    print("\033[92m=\033[0m" * 50)
    print(f"\033[1;93m🏁 Faceswap Processing Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {success_count} \033[93mswap(s)\033[0m")
    print(f"❌ \033[93mFailed:\033[0m {error_count} \033[93mswap(s)\033[0m")
    
    # Show first few errors if any
    if error_messages:
        print(f"\n\033[93mFirst few errors:\033[0m")
        for error in error_messages[:3]:
            print(f"  • {error}")
        if len(error_messages) > 3:
            print(f"  • ... and {len(error_messages) - 3} more")
    
    print("\033[92m=\033[0m" * 50)
    print("\n" * 2)
    # Tag source files if requested and successful
    if tag_source and success_count > 0:
        if mode == '3':
            tag_source_files(source_files)
        else:
            tag_source_files(source_files + target_files)
    
    # Handle opening output folder
    if success_count > 0:
        djj.prompt_open_folder(output_path)

def main():
    os.system('clear')
    
    # Check if FaceFusion exists before starting
    if not verify_facefusion_exists():
        print("\n\033[93mPlease install FaceFusion first, then run this script again.\033[0m")
        print("Installation: https://docs.facefusion.io")
        sys.exit(1)
    
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mFaceFusion Runner (NSFW Patched)\033[0m")
        print("AI Face Swap Tool")
        print("\033[92m==================================================\033[0m")
        print()
        
        # Get swap mode
        mode = get_swap_mode()
        
        # Get source input
        source_files, source_input_mode, source_folder_path = get_source_input(mode)
        
        if not source_files:
            print("❌ \033[1;93mNo valid source files found.\033[0m")
            sys.exit(1)
        
        # Get target input
        target_files, target_input_mode, target_folder_path = get_target_input(mode)
        
        if not target_files:
            print("❌ \033[1;93mNo valid target files found.\033[0m")
            sys.exit(1)
        
        os.system('clear')
        print("\n" * 2)
        print("🔍 Analyzing inputs...")
        print()
        print(f"\033[93m✅ Found\033[0m {len(source_files)} \033[93msource file(s)\033[0m")
        print(f"\033[93m✅ Found\033[0m {len(target_files)} \033[93mtarget file(s)\033[0m")
        print()
        print("Choose Your Options:")
        
        # Get output path and suffix preference
        output_path, add_suffix = get_output_path_and_suffix(source_files, target_files, mode)
        
        # Ask about tagging processed files
        tag_source = djj.prompt_choice(
            "\033[93mTag processed files with 'FF'?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='1'
        ) == '1'
        
        os.system('clear')
        
        # Process face swaps using appropriate method
        process_face_swap(mode, source_files, target_files, output_path, add_suffix, tag_source)
        
        print()
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()