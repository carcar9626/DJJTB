import os
import sys
import subprocess
import pathlib
import logging
import shutil
import time
import uuid
import djjtb.utils as djj

# ============================================================================
# 🎚️ FACE ALIGNMENT CONFIGURATION - EDIT THESE TO FIX CHIN ISSUES
# ============================================================================
# If you're getting "double chin" shadows or the face seems "too small":
# - Increase FACE_MASK_PADDING (try 30-50 for chin coverage)
# - Increase FACE_MASK_BLUR for smoother blending (0.3-0.5)
# - Lower scores = more lenient/flexible detection

# Face mask extends the swap area (CRITICAL for chin issues!)
# Higher = more coverage of chin/jaw area
# Range: 0-100 | Default: 0 | Recommended for chin fix: 30-40
FACE_MASK_PADDING = 25

# Smooths the edges where face meets background
# Higher = softer blend (helps hide seams)
# Range: 0.0-1.0 | Default: 0.3 | Recommended: 0.3-0.5
FACE_MASK_BLUR = 0.4

# How confident the detector needs to be about finding faces
# Lower = more lenient (finds faces easier)
# Range: 0.0-1.0 | Default: 0.5 | Recommended: 0.5-0.65
FACE_DETECTOR_SCORE = 0.5

# Precision of facial landmark detection (eyes, nose, jaw points)
# Lower = more flexible alignment
# Range: 0.0-1.0 | Default: 0.5 | Recommended: 0.5-0.65
FACE_LANDMARKER_SCORE = 0.5

# Face detection model to use
# Options: 'retinaface', 'yunet', 'many' (tries multiple)
# Recommended: 'retinaface' (most accurate) or 'many' (most thorough)
FACE_DETECTOR_MODEL = 'retinaface'
FACE_MASK_TYPES = ['box', 'occlusion']
FACE_SELECTOR_GENDER = 'female'

# ============================================================================
# END CONFIGURATION - Don't edit below unless you know what you're doing!
# ============================================================================
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

def copy_source_files(source_files, output_path):
    """Copy source files to output/Source directory"""
    source_dir = pathlib.Path(output_path) / "Source"
    source_dir.mkdir(parents=True, exist_ok=True)
    
    copied_count = 0
    
    for source_file in source_files:
        try:
            source_path = pathlib.Path(source_file)
            destination_path = source_dir / source_path.name
            
            # Avoid overwriting if file already exists with same name
            counter = 1
            original_destination = destination_path
            while destination_path.exists():
                stem = original_destination.stem
                suffix = original_destination.suffix
                destination_path = original_destination.parent / f"{stem}_{counter}{suffix}"
                counter += 1
            
            shutil.copy2(source_file, destination_path)
            copied_count += 1
            
        except Exception as e:
            print(f"⚠️  Failed to copy {os.path.basename(source_file)}: {e}")
    
    if copied_count > 0:
        print(f"\033[93m📁 Copied\033[0m {copied_count} \033[93msource file(s) to output/Source\033[0m")

def handle_target_files(target_files, output_path, action):
    """Handle target files based on user action (copy/move/nothing)"""
    if action == '3':  # Nothing
        return
    
    target_dir = pathlib.Path(output_path) / "Target"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    processed_count = 0
    action_name = "Copied" if action == '1' else "Moved"
    
    for target_file in target_files:
        try:
            target_path = pathlib.Path(target_file)
            destination_path = target_dir / target_path.name
            
            # Avoid overwriting if file already exists with same name
            counter = 1
            original_destination = destination_path
            while destination_path.exists():
                stem = original_destination.stem
                suffix = original_destination.suffix
                destination_path = original_destination.parent / f"{stem}_{counter}{suffix}"
                counter += 1
            
            if action == '1':  # Copy
                shutil.copy2(target_file, destination_path)
            else:  # Move
                shutil.move(target_file, destination_path)
            
            processed_count += 1
            
        except Exception as e:
            print(f"⚠️  Failed to {action_name.lower()} {os.path.basename(target_file)}: {e}")
    
    if processed_count > 0:
        print(f"\033[93m📁 {action_name}\033[0m {processed_count} \033[93mtarget file(s) to output/Target\033[0m")

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

def build_facefusion_args():
    """Build FaceFusion arguments from configuration"""
    args = []
    
    
    # Add face mask padding (CRITICAL for chin coverage!)
    args.extend(["--face-mask-padding", str(FACE_MASK_PADDING)])
    
    # Add face mask blur
    args.extend(["--face-mask-blur", str(FACE_MASK_BLUR)])
    # Add face gender selector
    args.extend(["--face-selector-gender", str(FACE_SELECTOR_GENDER)])
    # Add face detector score
    args.extend(["--face-detector-score", str(FACE_DETECTOR_SCORE)])
    
    # Add face landmarker score
    args.extend(["--face-landmarker-score", str(FACE_LANDMARKER_SCORE)])
    
    # Add face detector model
    args.extend(["--face-detector-model", FACE_DETECTOR_MODEL])
    args.extend(["--face-mask-types"] + FACE_MASK_TYPES)
    
    
    return args

def get_swap_mode():
    """Get face swap mode from user"""
    print("\033[1;93m🔄 Select Face Swap Mode\033[0m")
    
    mode = djj.prompt_choice(
        "\033[93mSwap Mode:\033[0m\n1. Single source TO multiple targets (one face → many images/videos)\n2. Single source TO single target (one face → one image/video)\n3. Multiple sources TO single target (m   any faces → one image/video)\n4. Multiple sources TO multiple targets (many faces → many images/videos)\n",
        ['1', '2', '3', '4'],
        default='1'
    )
    print()
    return mode

def get_source_input(mode):
    """Get source files/folders based on swap mode"""
    if mode in ['3', '4']:
        # Multiple sources
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
    
    elif mode in ['1', '4']:
        # Multiple targets
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
        "\033[33mOutput location:\033[0m\n1. Same folder as sources (creates 'Output/FF' subfolder)\n2. Same folder as targets (creates 'Output/FF' subfolder)\n3. Default Path\n4. Custom Path\n",
        ['1', '2', '3', '4'],
        default='3'
    )
    print()
    
    if output_choice == '1':
        # Same as source folder
        base_path = pathlib.Path(source_files[0]).parent
        # Create Output/FF structure
        output_path = base_path / "Output" / "FF"
        
    elif output_choice == '2':
        # Same as target folder
        base_path = pathlib.Path(target_files[0]).parent
        # Create Output/FF structure
        output_path = base_path / "Output" / "FF"
        
    elif output_choice == '3':
        # Default path - /Volumes/Movies_2SSD/UD_Gens/Characters/UD/FF_outputs/Runner/first_target_parent
        first_target_parent = pathlib.Path(target_files[0]).parent.name
        default_base = pathlib.Path("/Volumes/Movies_2SSD/UD_Gens/Characters/UD/FF_outputs/Runner")
        output_path = default_base / first_target_parent
        
    else:  # output_choice == '4'
        # Custom path
        custom_path = djj.get_path_input("Enter custom output folder path")
        output_path = pathlib.Path(custom_path)
    
    # Create the output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get suffix preference
    suffix_choice = djj.prompt_choice(
        "\033[33mAdd '_FF' suffix to filenames?\033[0m\n1. Yes\n2. No",
        ['1', '2'],
        default='1'
    ) == '1'
    
    return str(output_path), suffix_choice

def generate_output_filename(source_file, target_file, output_path, add_suffix=True):
    """Generate output filename based on source and target, avoiding overwrites"""
    source_name = pathlib.Path(source_file).stem
    target_name = pathlib.Path(target_file).stem
    target_ext = pathlib.Path(target_file).suffix
    
    if add_suffix:
        base_filename = f"{target_name}_FF{target_ext}"
    else:
        base_filename = f"{target_name}{target_ext}"
    
    output_file_path = pathlib.Path(output_path) / base_filename
    
    # Check if file exists and create unique name if needed
    counter = 1
    original_output_path = output_file_path
    while output_file_path.exists():
        stem = original_output_path.stem
        suffix = original_output_path.suffix
        if add_suffix:
            # Remove _FF from stem to insert counter before it
            if stem.endswith('_FF'):
                base_stem = stem[:-3]  # Remove '_FF'
                new_filename = f"{base_stem}_{counter}_FF{suffix}"
            else:
                new_filename = f"{stem}_{counter}{suffix}"
        else:
            new_filename = f"{stem}_{counter}{suffix}"
        
        output_file_path = original_output_path.parent / new_filename
        counter += 1
    
    return str(output_file_path)

def process_single_headless(source_file, target_file, output_file, use_enhanced_mode=False):
    """Process single source to single target using headless-run"""
    cmd = [
        FACEFUSION_VENV_PYTHON, FACEFUSION_SCRIPT_PATH, "headless-run",
        "-s", str(source_file),
        "-t", str(target_file),
        "-o", str(output_file)
    ]
    
    # Add configuration arguments
    cmd.extend(build_facefusion_args())
    
    try:
        result = subprocess.run(cmd, cwd=FACEFUSION_DIR,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              text=True,
                              timeout=600)  # 10 minute timeout per file
        
        return result.returncode == 0, result.stdout if result.stdout else "No output"
    except subprocess.TimeoutExpired:
        return False, "Timeout (processing took too long)"
    except Exception as e:
        return False, str(e)

def process_batch_job(source_file, target_files, output_path, add_suffix=True, use_enhanced_mode=False):
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
    
    # Step 2: Add steps for each target and store expected output files
    print(f"\033[93m📝 Adding {len(target_files)} steps to job...\033[0m")
    
    added_steps = 0
    expected_outputs = []
    
    # Build base configuration args
    config_args = build_facefusion_args()
    
    for target_file in target_files:
        output_file = generate_output_filename(source_file, target_file, output_path, add_suffix)
        expected_outputs.append(output_file)
        
        cmd_add_step = [
            FACEFUSION_VENV_PYTHON, FACEFUSION_SCRIPT_PATH, "job-add-step", job_id,
            "-s", str(source_file),
            "-t", str(target_file),
            "-o", str(output_file)
        ]
        
        # Add configuration arguments to each step
        cmd_add_step.extend(config_args)
        
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
                print(f"     Error: {result.stderr}")
                
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
                              timeout=len(target_files) * 600)  # 10 minutes per target
        
        print(f"\033[93m🔍 Job execution output:\033[0m")
        if result.stdout:
            # Print last few lines of output for debugging
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines[-10:]:  # Show last 10 lines
                if line.strip():
                    print(f"   {line}")
        
        if result.returncode == 0:
            print(f"\033[92m✅ Job completed successfully\033[0m")
            
            # Wait a moment for files to be written
            time.sleep(2)
            
            # Check for successful outputs using the expected file paths
            for i, expected_output in enumerate(expected_outputs):
                target_file = target_files[i]
                
                if pathlib.Path(expected_output).exists():
                    print(f"\033[92m✅ Found output:\033[0m {os.path.basename(expected_output)}")
                    success_count += 1
                else:
                    # Also check if file exists in output directory with any similar name
                    output_dir = pathlib.Path(output_path)
                    target_stem = pathlib.Path(target_file).stem
                    
                    # Look for files that might match this target
                    possible_matches = list(output_dir.glob(f"*{target_stem}*"))
                    
                    if possible_matches:
                        print(f"\033[93m⚠️  Expected file not found, but similar files exist:\033[0m")
                        for match in possible_matches[:3]:  # Show first 3 matches
                            print(f"     {match.name}")
                        success_count += 1  # Count as success if similar file exists
                    else:
                        print(f"\033[93m❌ No output found for:\033[0m {os.path.basename(target_file)}")
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

def process_face_swap(mode, source_files, target_files, output_path, add_suffix, tag_source, target_action, use_enhanced_mode):
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
    elif mode == '3':
        print(f"\033[93m📁 Sources:\033[0m {len(source_files)} file(s)")
        print(f"\033[93m🎯 Target:\033[0m {os.path.basename(target_files[0])}")
        mode_desc = "Multiple sources TO single target"
    else:  # mode == '4'
        print(f"\033[93m📁 Sources:\033[0m {len(source_files)} file(s)")
        print(f"\033[93m🎯 Targets:\033[0m {len(target_files)} file(s)")
        mode_desc = "Multiple sources TO multiple targets"
    
    print(f"\033[93m🔄 Mode:\033[0m {mode_desc}")
    print(f"\033[93m📤 Output:\033[0m {output_path}")
    print(f"\033[93m🏷️  Add suffix:\033[0m {'Yes' if add_suffix else 'No'}")
    
    # Show current configuration settings
    print(f"\033[93m⚙️  Face Mask Padding:\033[0m {FACE_MASK_PADDING}")
    print(f"\033[93m⚙️  Face Mask Blur:\033[0m {FACE_MASK_BLUR}")
    print(f"\033[93m⚙️  Detector Model:\033[0m {FACE_DETECTOR_MODEL}")
    
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
        
        success, error_msg = process_single_headless(source_file, target_file, output_file, use_enhanced_mode)
        
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
        success_count, error_count, error_messages = process_batch_job(source_file, target_files, output_path, add_suffix, use_enhanced_mode)
    
    elif mode == '3':
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
            
            success, error_msg = process_single_headless(source_file, target_file, output_file, use_enhanced_mode)
            
            if success:
                print(f"\033[92m✅ Success:\033[0m {source_name}")
                success_count += 1
            else:
                print(f"\033[93m❌ Failed:\033[0m {source_name}")
                print(f"   Error: {error_msg}")
                error_count += 1
                error_messages.append(f"{source_name}: {error_msg}")
                
    else:  # mode == '4' - Multi to Multi
    # Multiple sources to multiple targets
    # Process each source with all targets, organized by source-targetparent subfolder
        
        # Get today's date for folder structure
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Get target parent folder name (use first target's parent)
        target_parent_folder = pathlib.Path(target_files[0]).parent.name
        
        # Process each source with all targets
        for source_idx, source_file in enumerate(source_files):
            source_name = pathlib.Path(source_file).stem
            
            # Create subfolder: YYYY-MM-DD/sourcename-targetparent/
            date_folder = pathlib.Path(output_path) / today_str
            source_output_path = date_folder / f"{source_name}-{target_parent_folder}"
            source_output_path.mkdir(parents=True, exist_ok=True)
            
            print(f"\n\033[1;93m📁 Processing source [{source_idx+1}/{len(source_files)}]:\033[0m {os.path.basename(source_file)}")
            print(f"\033[93m   Output folder:\033[0m {today_str}/{source_name}-{target_parent_folder}/")
            print(f"\033[93m   Targets:\033[0m {len(target_files)} file(s)")
            print()
            
            # Process each target with this source
            for target_idx, target_file in enumerate(target_files):
                target_name = pathlib.Path(target_file).stem
                target_ext = pathlib.Path(target_file).suffix
                
                # Generate output filename: sourcename_targetname_FF.ext
                if add_suffix:
                    output_filename = f"{source_name}_{target_name}_FF{target_ext}"
                else:
                    output_filename = f"{source_name}_{target_name}{target_ext}"
                
                output_file = str(source_output_path / output_filename)
                
                print(f"\033[93m  [{target_idx+1}/{len(target_files)}] Processing:\033[0m {source_name} → {target_name}")
                
                success, error_msg = process_single_headless(source_file, target_file, output_file, use_enhanced_mode)
                
                if success:
                    print(f"\033[92m    ✅ Success\033[0m")
                    success_count += 1
                else:
                    print(f"\033[93m    ❌ Failed:\033[0m {error_msg[:50]}...")
                    error_count += 1
                    error_messages.append(f"{source_name}→{target_name}: {error_msg}")

    # else:  # mode == '4' - Multi to Multi
    #     # Multiple sources to multiple targets
    #     # Process each target with all sources, organized by target subfolder
    #
    #     for target_idx, target_file in enumerate(target_files):
    #         target_name = pathlib.Path(target_file).stem
    #         target_output_path = pathlib.Path(output_path) / target_name
    #         target_output_path.mkdir(parents=True, exist_ok=True)
    #
    #         print(f"\n\033[1;93m🎯 Processing target [{target_idx+1}/{len(target_files)}]:\033[0m {os.path.basename(target_file)}")
    #         print(f"\033[93m   Output folder:\033[0m {target_output_path.name}/")
    #         print(f"\033[93m   Sources:\033[0m {len(source_files)} file(s)")
    #         print()
    #
    #         # Process each source individually for this target
    #         for source_idx, source_file in enumerate(source_files):
    #             source_name = pathlib.Path(source_file).stem
    #             target_ext = pathlib.Path(target_file).suffix
    #
    #             # Generate output filename: sourcename_targetname_FF.ext
    #             if add_suffix:
    #                 output_filename = f"{source_name}_{target_name}_FF{target_ext}"
    #             else:
    #                 output_filename = f"{source_name}_{target_name}{target_ext}"
    #
    #             output_file = str(target_output_path / output_filename)
    #
    #             print(f"\033[93m  [{source_idx+1}/{len(source_files)}] Processing:\033[0m {source_name} → {target_name}")
    #
    #             success, error_msg = process_single_headless(source_file, target_file, output_file, use_enhanced_mode)
    #
    #             if success:
    #                 print(f"\033[92m    ✅ Success\033[0m")
    #                 success_count += 1
    #             else:
    #                 print(f"\033[93m    ❌ Failed:\033[0m {error_msg[:50]}...")
    #                 error_count += 1
    #                 error_messages.append(f"{source_name}→{target_name}: {error_msg}")
    
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
    
    # Copy source files to output/Source directory if processing was successful
    if success_count > 0:
        copy_source_files(source_files, output_path)
    
    # Handle target files based on user choice
    if success_count > 0:
        handle_target_files(target_files, output_path, target_action)
    
    # Tag source files if requested and successful
    if tag_source and success_count > 0:
        if mode in ['3', '4']:
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
        print("\033[1;93mFaceFusion Runner (NSFW Patched + Chin Fix)\033[0m")
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
        
        # For mode 4 (multi to multi), check if output count is reasonable
        if mode == '4':
            total_outputs = len(source_files) * len(target_files)
            if total_outputs > 100:
                print(f"\n\033[93m⚠️  WARNING: This will create {total_outputs} output files!\033[0m")
                print(f"   {len(source_files)} sources × {len(target_files)} targets = {total_outputs} outputs")
                print()
                
                continue_choice = djj.prompt_choice(
                    "\033[93mDo you want to continue?\033[0m\n1. Yes, continue\n2. No, go back",
                    ['1', '2'],
                    default='2'
                )
                
                if continue_choice == '2':
                    os.system('clear')
                    continue
                print()
            
        use_enhanced_mode = djj.prompt_choice(
            "\033[93m🎚️  Use Enhanced Quality Mode?\033[0m\n1. Yes (better results, slower)\n2. No (faster, default)",
            ['1', '2'],
            default='1'
        ) == '1'
        print()
        
        os.system('clear')
        print("\n" * 2)
        print("🔍 Analyzing inputs...")
        print()
        print(f"\033[93m✅ Found\033[0m {len(source_files)} \033[93msource file(s)\033[0m")
        print(f"\033[93m✅ Found\033[0m {len(target_files)} \033[93mtarget file(s)\033[0m")
        
        if mode == '4':
            total_outputs = len(source_files) * len(target_files)
            print(f"\033[93m📊 Total outputs:\033[0m {total_outputs} file(s)")
        
        print()
        print("Choose Your Options:")
        
        # Get output path and suffix preference
        output_path, add_suffix = get_output_path_and_suffix(source_files, target_files, mode)
        
        # Ask about target file handling
        target_action = djj.prompt_choice(
            "\033[93mWhat to do with target files?\033[0m\n1. Copy to output/Target\n2. Move to output/Target\n3. Nothing (leave in place)",
            ['1', '2', '3'],
            default='3'
        )
        print()
        
        # Ask about tagging processed files
        tag_source = djj.prompt_choice(
            "\033[93mTag processed files with 'FF'?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='1'
        ) == '1'
        
        os.system('clear')
        
        # Process face swaps using appropriate method
        process_face_swap(mode, source_files, target_files, output_path, add_suffix, tag_source, target_action, use_enhanced_mode)
        
        print()
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()