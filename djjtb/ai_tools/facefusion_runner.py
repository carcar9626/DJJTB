import os
import sys
import subprocess
import pathlib
import shutil
import time
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

# Face enhancer applied after the swap
# Options: 'gfpgan_1.4', 'codeformer'
# Blend: 0–100 (how strongly the enhancer is applied over the raw swap)
FACE_ENHANCER_DEFAULT_MODEL = 'gfpgan_1.4'
FACE_ENHANCER_DEFAULT_BLEND = 60

# Expression restorer (Live Portrait) — restores target facial expression onto swapped face
# Only model available in FF 3.3.2: 'live_portrait'
# Factor: 0–100 — how much of the target's expression is restored (default: 80)
EXPRESSION_RESTORER_DEFAULT_MODEL = 'live_portrait'
EXPRESSION_RESTORER_DEFAULT_FACTOR = 80

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

def build_facefusion_args(face_enhancer=None, face_enhancer_blend=FACE_ENHANCER_DEFAULT_BLEND,
                          expression_restorer=False, expression_restorer_factor=EXPRESSION_RESTORER_DEFAULT_FACTOR):
    """Build FaceFusion arguments from configuration.
    face_enhancer: None = no enhancer, 'gfpgan_1.4' or 'codeformer' = use it
    face_enhancer_blend: 0-100 blend strength
    expression_restorer: True = add expression_restorer to processors list
    expression_restorer_factor: 0-100 restore factor (default 80)
    """
    args = []

    args.extend(["--face-mask-padding", str(FACE_MASK_PADDING)])
    args.extend(["--face-mask-blur", str(FACE_MASK_BLUR)])
    args.extend(["--face-selector-gender", str(FACE_SELECTOR_GENDER)])
    args.extend(["--face-detector-score", str(FACE_DETECTOR_SCORE)])
    args.extend(["--face-landmarker-score", str(FACE_LANDMARKER_SCORE)])
    args.extend(["--face-detector-model", FACE_DETECTOR_MODEL])
    args.extend(["--face-mask-type"] + FACE_MASK_TYPES)

    # Build processors list — always starts with face_swapper
    # Order matters: restorer reads the raw swap better before enhancer sharpens it
    processors = ["face_swapper"]
    if expression_restorer:
        processors.append("expression_restorer")
    if face_enhancer:
        processors.append("face_enhancer")

    if len(processors) > 1:
        args.extend(["--processors"] + processors)

    if face_enhancer:
        args.extend(["--face-enhancer-model", face_enhancer])
        args.extend(["--face-enhancer-blend", str(face_enhancer_blend)])

    if expression_restorer:
        args.extend(["--expression-restorer-model", EXPRESSION_RESTORER_DEFAULT_MODEL])
        args.extend(["--expression-restorer-factor", str(expression_restorer_factor)])

    return args

def write_cmd_log(output_file, cmd):
    """
    Write a hidden .txt file alongside the output file recording the exact command run.
    File is named .<output_stem>_cmd.txt so it stays hidden on macOS.
    """
    try:
        out_path = pathlib.Path(output_file)
        log_path = out_path.parent / f".{out_path.stem}_cmd.txt"
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(" ".join(str(c) for c in cmd))
            f.write("\n")
    except Exception:
        pass  # Never block processing over a log write failure


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

DEFAULT_FACES_FOLDER = "/Volumes/Movies_2SSD/UD_Gens/Characters/OG/OG_Process/FACES"


def get_source_input(mode):
    """Get source files/folders based on swap mode"""
    if mode in ['3', '4']:
        # Multiple sources
        print("\033[1;93m📁 Source Selection (Multiple Sources)\033[0m")

        input_mode = djj.prompt_choice(
            "\033[93mSource input mode:\033[0m\n1. Folder containing source faces\n2. Space-separated file paths\n3. Pick from default FACES folder\n",
            ['1', '2', '3'],
            default='3'
        )
        print()

        if input_mode == '1':
            # Folder mode — untouched
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

        elif input_mode == '2':
            # Space-separated paths
            file_paths = input("📁 \033[93mEnter source file paths (space-separated):\033[0m\n -> ").strip()
            if not file_paths:
                print("\033[1;93m❌ No file paths provided.\033[0m")
                sys.exit(1)
            source_files = collect_files_from_paths(file_paths)
            print()
            return source_files, 'files', None

        else:
            # Default FACES folder picker — numbered multi-select
            source_files = [str(p) for p in djj.pick_multiple_from_folder(DEFAULT_FACES_FOLDER, SUPPORTED_EXTS, label="face")]
            if not source_files:
                print("\033[1;93m❌ No files selected.\033[0m")
                sys.exit(1)
            return source_files, 'files', None

    else:
        # Single source (modes 1 and 2)
        print("\033[1;93m📁 Source Selection (Single Source)\033[0m")

        input_mode = djj.prompt_choice(
            "\033[93mSource input mode:\033[0m\n1. Enter file path\n2. Pick from default FACES folder\n",
            ['1', '2'],
            default='2'
        )
        print()

        if input_mode == '1':
            source_path = djj.get_path_input("Enter source face file path")
            print()
            source_path_obj = pathlib.Path(source_path)
            if not source_path_obj.exists() or source_path_obj.suffix.lower() not in SUPPORTED_EXTS:
                print(f"\033[93m❌ Invalid source file: {source_path}\033[0m")
                sys.exit(1)
            return [str(source_path_obj)], 'single_file', None

        else:
            # Default FACES folder picker — single select
            picked = djj.pick_single_from_folder(DEFAULT_FACES_FOLDER, SUPPORTED_EXTS, label="face")
            if not picked:
                print("\033[1;93m❌ No file selected.\033[0m")
                sys.exit(1)
            return [str(picked)], 'single_file', None

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

def get_output_path_and_suffix(source_files, target_files, mode, target_folder_path=None):
    """Determine output path and get suffix preference based on inputs.

    Returns output_mode alongside output_path: 'mirror' means each target file's
    output should land next to that specific file (target_file.parent / "FF"),
    not all lumped into one folder computed from a single target. 'fixed' means
    output_path itself is the single destination for everything.
    """

    output_choice = djj.prompt_choice(
        "\033[33mOutput location:\033[0m\n1. Same folder as sources (creates 'FF' subfolder)\n2. Same folder as targets (creates 'FF' subfolder)\n3. Default — target folder / FF (default)\n4. Custom Path\n",
        ['1', '2', '3', '4'],
        default='3'
    )
    print()

    output_mode = 'fixed'

    if output_choice == '1':
        # Same as source folder
        base_path = pathlib.Path(source_files[0]).parent
        output_path = base_path / "FF"

    elif output_choice in ('2', '3'):
        # Same as target folder(s) — mirror each target file's own parent folder,
        # since targets pulled in "with subfolders" can span multiple directories.
        output_mode = 'mirror'
        if target_folder_path:
            base_path = pathlib.Path(target_folder_path)
        else:
            try:
                base_path = pathlib.Path(os.path.commonpath([str(pathlib.Path(t).parent) for t in target_files]))
            except ValueError:
                base_path = pathlib.Path(target_files[0]).parent
        output_path = base_path / "FF"

    else:  # output_choice == '4'
        # Custom path
        custom_path = djj.get_path_input("Enter custom output folder path")
        output_path = pathlib.Path(custom_path)

    # Create the output directory (in 'mirror' mode this is just the base used
    # for Source/Target copies and the end-of-run folder open; per-file FF
    # folders are created on demand)
    output_path.mkdir(parents=True, exist_ok=True)

    # Get suffix preference
    suffix_choice = djj.prompt_choice(
        "\033[33mAdd '_FF' suffix to filenames?\033[0m\n1. Yes\n2. No",
        ['1', '2'],
        default='1'
    ) == '1'

    # Get source-name-in-filename preference
    include_source_name = djj.prompt_choice(
        "\033[33mInclude source filename in output filename?\033[0m\n1. Yes\n2. No [default: 2]",
        ['1', '2'],
        default='2'
    ) == '1'

    return str(output_path), output_mode, suffix_choice, include_source_name


def get_target_ff_dir(target_file, output_mode, output_path):
    """Destination FF directory for a given target file. Mirrors the target's
    own parent folder in 'mirror' mode; otherwise uses the single fixed output_path."""
    if output_mode == 'mirror':
        return pathlib.Path(target_file).parent / "FF"
    return pathlib.Path(output_path)

def generate_output_filename(source_file, target_file, output_path, add_suffix=True, include_source_name=True):
    """Generate output filename: targetname_sourcename_FF.ext (source name optional)"""
    source_name = pathlib.Path(source_file).stem
    target_name = pathlib.Path(target_file).stem
    target_ext = pathlib.Path(target_file).suffix
    
    base_stem = f"{target_name}_{source_name}" if include_source_name else target_name
    
    if add_suffix:
        base_filename = f"{base_stem}_FF{target_ext}"
    else:
        base_filename = f"{base_stem}{target_ext}"
    
    output_file_path = pathlib.Path(output_path) / base_filename
    
    # Check if file exists and create unique name if needed
    counter = 1
    original_output_path = output_file_path
    while output_file_path.exists():
        stem = original_output_path.stem
        suffix = original_output_path.suffix
        if add_suffix:
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

def process_single_headless(source_file, target_file, output_file,
                            face_enhancer=None, face_enhancer_blend=FACE_ENHANCER_DEFAULT_BLEND,
                            expression_restorer=False, expression_restorer_factor=EXPRESSION_RESTORER_DEFAULT_FACTOR):
    """Process single source to single target using headless-run"""
    cmd = [
        FACEFUSION_VENV_PYTHON, FACEFUSION_SCRIPT_PATH, "headless-run",
        "-s", str(source_file),
        "-t", str(target_file),
        "-o", str(output_file)
    ]

    cmd.extend(build_facefusion_args(face_enhancer, face_enhancer_blend,
                                     expression_restorer, expression_restorer_factor))

    try:
        result = subprocess.run(cmd, cwd=FACEFUSION_DIR,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              text=True,
                              timeout=600)

        if result.returncode == 0:
            write_cmd_log(output_file, cmd)
        return result.returncode == 0, result.stdout if result.stdout else "No output"
    except subprocess.TimeoutExpired:
        return False, "Timeout (processing took too long)"
    except Exception as e:
        return False, str(e)

def process_face_swap(mode, source_files, target_files, output_path, output_mode, add_suffix, tag_source,
                      target_action, face_enhancer=None,
                      face_enhancer_blend=FACE_ENHANCER_DEFAULT_BLEND,
                      expression_restorer=False, expression_restorer_factor=EXPRESSION_RESTORER_DEFAULT_FACTOR,
                      include_source_name=True):
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
    print(f"\033[93m🏷️  Include source name:\033[0m {'Yes' if include_source_name else 'No'}")
    print(f"\033[93m⚙️  Face Mask Padding:\033[0m {FACE_MASK_PADDING}")
    print(f"\033[93m⚙️  Face Mask Blur:\033[0m {FACE_MASK_BLUR}")
    print(f"\033[93m⚙️  Detector Model:\033[0m {FACE_DETECTOR_MODEL}")
    if face_enhancer:
        print(f"\033[93m✨ Face Enhancer:\033[0m {face_enhancer}  blend: {face_enhancer_blend}")
    else:
        print(f"\033[93m✨ Face Enhancer:\033[0m off")
    if expression_restorer:
        print(f"\033[93m😮 Expression Restorer:\033[0m {EXPRESSION_RESTORER_DEFAULT_MODEL}  factor: {expression_restorer_factor}")
    else:
        print(f"\033[93m😮 Expression Restorer:\033[0m off")

    print("\033[92m=\033[0m" * 50)
    print()
    print("\033[1;93m🎭 FaceFusion 🎭 \033[0m\033[93mactivating...\033[0m")
    print()

    success_count = 0
    error_count = 0
    error_messages = []

    if mode == '2':
        # Single source to single target — headless-run
        source_file = source_files[0]
        target_file = target_files[0]
        output_file = generate_output_filename(source_file, target_file, output_path, add_suffix, include_source_name)

        print(f"\033[93mProcessing:\033[0m {os.path.basename(source_file)} → {os.path.basename(target_file)}")

        success, error_msg = process_single_headless(
            source_file, target_file, output_file,
            face_enhancer, face_enhancer_blend,
            expression_restorer, expression_restorer_factor
        )

        if success:
            print(f"\033[92m✅ Success:\033[0m Face swap completed!")
            success_count = 1
        else:
            print(f"\033[93m❌ Failed:\033[0m {error_msg}")
            error_count = 1
            error_messages.append(error_msg)

    elif mode == '1':
        # Single source to multiple targets — headless-run per target (same engine as all other modes)
        source_file = source_files[0]
        for i, target_file in enumerate(target_files):
            target_name = os.path.basename(target_file)
            print(f"\033[93mProcessing [{i+1}/{len(target_files)}]:\033[0m {target_name}")
            dest_dir = get_target_ff_dir(target_file, output_mode, output_path)
            dest_dir.mkdir(parents=True, exist_ok=True)
            output_file = generate_output_filename(source_file, target_file, dest_dir, add_suffix, include_source_name)
            success, error_msg = process_single_headless(
                source_file, target_file, output_file,
                face_enhancer, face_enhancer_blend,
                expression_restorer, expression_restorer_factor
            )
            if success:
                print(f"\033[92m✅ Done\033[0m")
                success_count += 1
            else:
                print(f"\033[93m❌ Failed:\033[0m {error_msg[:80]}")
                error_count += 1
                error_messages.append(f"{target_name}: {error_msg}")

    elif mode == '3':
        # Multiple sources to single target — one headless-run per source
        target_file = target_files[0]

        for i, source_file in enumerate(source_files):
            source_name = os.path.basename(source_file)
            print(f"\033[93mProcessing [{i+1}/{len(source_files)}]:\033[0m {source_name}")

            source_stem = pathlib.Path(source_file).stem
            target_stem = pathlib.Path(target_file).stem
            target_ext  = pathlib.Path(target_file).suffix
            base_stem = f"{target_stem}_{source_stem}" if include_source_name else target_stem
            output_filename = (f"{base_stem}_FF{target_ext}" if add_suffix
                               else f"{base_stem}{target_ext}")
            output_file = str(pathlib.Path(output_path) / output_filename)

            success, error_msg = process_single_headless(
                source_file, target_file, output_file,
                face_enhancer, face_enhancer_blend,
                expression_restorer, expression_restorer_factor
            )

            if success:
                print(f"\033[92m✅ Success:\033[0m {source_name}")
                success_count += 1
            else:
                print(f"\033[93m❌ Failed:\033[0m {source_name}")
                print(f"   Error: {error_msg}")
                error_count += 1
                error_messages.append(f"{source_name}: {error_msg}")

    else:  # mode == '4' — multiple sources × multiple targets
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")

        for source_idx, source_file in enumerate(source_files):
            source_name = pathlib.Path(source_file).stem

            print(f"\n\033[1;93m📁 Processing source [{source_idx+1}/{len(source_files)}]:\033[0m {os.path.basename(source_file)}")
            print(f"\033[93m   Targets:\033[0m {len(target_files)} file(s)")
            print()

            for target_idx, target_file in enumerate(target_files):
                target_name = pathlib.Path(target_file).stem
                target_ext  = pathlib.Path(target_file).suffix
                target_parent_folder = pathlib.Path(target_file).parent.name

                # Mirror each target's own parent folder so mixed-subfolder batches
                # don't all collapse into whichever target happened to be first
                dest_root = get_target_ff_dir(target_file, output_mode, output_path)
                date_folder = dest_root / today_str
                source_output_path = date_folder / f"{source_name}-{target_parent_folder}"
                source_output_path.mkdir(parents=True, exist_ok=True)

                base_name = f"{target_name}_{source_name}" if include_source_name else target_name
                output_filename = (f"{base_name}_FF{target_ext}" if add_suffix
                                   else f"{base_name}{target_ext}")
                output_file = str(source_output_path / output_filename)

                print(f"\033[93m  [{target_idx+1}/{len(target_files)}] Processing:\033[0m {source_name} → {target_name}  \033[90m({today_str}/{source_name}-{target_parent_folder}/)\033[0m")

                success, error_msg = process_single_headless(
                    source_file, target_file, output_file,
                    face_enhancer, face_enhancer_blend,
                    expression_restorer, expression_restorer_factor
                )

                if success:
                    print(f"\033[92m    ✅ Success\033[0m")
                    success_count += 1
                else:
                    print(f"\033[93m    ❌ Failed:\033[0m {error_msg[:50]}...")
                    error_count += 1
                    error_messages.append(f"{source_name}→{target_name}: {error_msg}")

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
            
        use_face_enhancer = djj.prompt_choice(
            "\033[93m✨ Use Face Enhancer?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='1'
        ) == '1'
        print()

        face_enhancer = None
        face_enhancer_blend = FACE_ENHANCER_DEFAULT_BLEND
        if use_face_enhancer:
            enhancer_choice = djj.prompt_choice(
                "\033[93m✨ Enhancer model:\033[0m\n1. gfpgan_1.4\n2. codeformer",
                ['1', '2'],
                default='1'
            )
            face_enhancer = 'gfpgan_1.4' if enhancer_choice == '1' else 'codeformer'
            print(f"✅ \033[92mEnhancer:\033[0m {face_enhancer}  blend: {face_enhancer_blend}")
            print()

        use_expression_restorer = djj.prompt_choice(
            "\033[93m😮 Use Expression Restorer?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        expression_restorer_factor = EXPRESSION_RESTORER_DEFAULT_FACTOR
        if use_expression_restorer:
            factor_raw = input(f"\033[93m   Restore factor (0–100, default {EXPRESSION_RESTORER_DEFAULT_FACTOR}):\033[0m\n > ").strip()
            try:
                expression_restorer_factor = max(0, min(100, int(factor_raw) if factor_raw else EXPRESSION_RESTORER_DEFAULT_FACTOR))
            except ValueError:
                expression_restorer_factor = EXPRESSION_RESTORER_DEFAULT_FACTOR
            print(f"✅ \033[92mExpression Restorer:\033[0m live_portrait  factor: {expression_restorer_factor}")
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
        output_path, output_mode, add_suffix, include_source_name = get_output_path_and_suffix(source_files, target_files, mode, target_folder_path)
        
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
        process_face_swap(mode, source_files, target_files, output_path, output_mode, add_suffix, tag_source,
                          target_action, face_enhancer, face_enhancer_blend,
                          use_expression_restorer, expression_restorer_factor,
                          include_source_name)
        
        print()
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()