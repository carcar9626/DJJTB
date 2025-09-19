import os
import sys
import subprocess
import pathlib
import logging
import shutil
import djjtb.utils as djj

# Supported extensions
SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')

# Path to rem-wm setup
REMWM_DIR = "/Users/home/Documents/ai_models/rem-wm"
REMWM_VENV_PYTHON = "/Users/home/Documents/ai_models/rem-wm/remwmvenv/bin/python3"
REMWM_SCRIPT = "/Users/home/Documents/ai_models/rem-wm/remwm.py"

def verify_setup():
    """Check if rem-wm is properly set up"""
    required_components = [
        (REMWM_DIR, "rem-wm directory"),
        (REMWM_VENV_PYTHON, "Python virtual environment"),
        (REMWM_SCRIPT, "rem-wm script")
    ]
    
    missing_components = []
    for path, description in required_components:
        if not pathlib.Path(path).exists():
            missing_components.append(f"   {description}: {path}")
    
    if missing_components:
        print("\033[33m⚠️  Missing rem-wm components:\033[0m")
        for component in missing_components:
            print(component)
        print()
        print("💡 \033[33mTo fix this, run these commands in Terminal:\033[0m")
        print("cd /Users/home/Documents/ai_models/")
        print("git clone https://github.com/Damarcreative/rem-wm.git")
        print("cd rem-wm")
        print("python3 -m venv remwmvenv")
        print("source remwmvenv/bin/activate")
        print("pip install -r requirements.txt")
        return False
    
    print("✅ \033[33mrem-wm setup verified\033[0m")
    return True

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
            dir_files = collect_files_from_folder(path)
            files.extend(dir_files)
    
    return sorted(files, key=str.lower)

def get_valid_inputs():
    """Allow selecting multiple files and/or folders using prompt_choice"""
    print("\033[1;33m🔍 Select images to remove watermarks from\033[0m")
    
    input_mode = djj.prompt_choice(
        "\033[33mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
        ['1', '2'],
        default='1'
    )
    print()
    
    valid_paths = []
    
    if input_mode == '1':
        src_path = djj.get_path_input("Enter folder path")
        print()
        
        include_sub = djj.prompt_choice(
            "\033[33mInclude subfolders?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        
        valid_paths = collect_files_from_folder(src_path, include_sub)
        
    else:
        file_paths = input("📁 \033[33mEnter file paths (space-separated):\033[0m\n -> ").strip()
        
        if not file_paths:
            print("\033[1;33m❌ No file paths provided.\033[0m")
            sys.exit(1)
        
        valid_paths = collect_files_from_paths(file_paths)
        print()
    
    if not valid_paths:
        print("❌ \033[1;33mNo valid image files found.\033[0m")
        sys.exit(1)
    
    os.system('clear')
    print("\n" * 2)
    print("🔍 Detecting files...")
    print()
    print(f"\033[33m✅ Found\033[0m {len(valid_paths)} \033[33msupported image(s)\033[0m")
    print()
    print("Choose Your Options:")
    
    return valid_paths, input_mode, src_path if input_mode == '1' else None

def tag_source_files(file_paths, tag_name="WM"):
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
        print(f"\033[33m🏷️  Tagged\033[0m {tagged_count} \033[33mfile(s) with\033[0m '\033[92m{tag_name}\033[0m'")

def create_processing_script(input_paths, output_path, max_workers=4):
    """Create a temporary Python script to run the watermark removal"""
    script_content = f'''
import sys
sys.path.append("{REMWM_DIR}")
from remwm import WatermarkRemover
import os
from pathlib import Path

# Initialize remover (first run will download models)
print("🤖 Initializing AI models (Florence-2 + LAMA)...")
print("   📥 Downloading models on first run (~1.7GB total)")
print("   ⏳ This may take a few minutes...")

try:
    remover = WatermarkRemover()
    print("✅ Models loaded successfully!")
except Exception as e:
    print(f"❌ Error loading models: {{str(e)}}")
    sys.exit(1)

# Input files and output directory
input_paths = {input_paths}
output_dir = "{output_path}"

success_count = 0
error_count = 0

print()
print("🔍 Florence-2 detecting watermarks...")
print("🎨 LAMA inpainting...")
print()

for i, input_file in enumerate(input_paths):
    file_name = os.path.basename(input_file)
    print(f"Processing [{{i+1}}/{{len(input_paths)}}]: {{file_name}}")
    
    try:
        # Create output filename
        input_path = Path(input_file)
        output_file = Path(output_dir) / f"{{input_path.stem}}_clean{{input_path.suffix}}"
        
        # Process the image
        remover.process_images_florence_lama(str(input_path), str(output_file))
        print(f"  ✅ Success")
        success_count += 1
        
    except Exception as e:
        print(f"  ❌ Failed: {{str(e)}}")
        error_count += 1

print()
print("=" * 50)
print(f"🏁 AI Watermark Removal Complete!")
print(f"✅ Successful: {{success_count}} file(s)")
print(f"❌ Failed: {{error_count}} file(s)")
print("=" * 50)
'''
    
    script_path = pathlib.Path(REMWM_DIR) / "temp_process.py"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    return script_path

def process_files(input_paths, input_mode, src_path, max_workers, tag_source):
    """Process files using rem-wm"""
    
    if input_mode == '1':
        # Folder mode - create output folder next to input
        output_path = pathlib.Path(src_path) / "WM"
        output_path.mkdir(parents=True, exist_ok=True)
        
        print("\n" * 2)
        print(f"\n\033[1;33m🤖 AI Watermark Detection & Removal\033[0m")
        print(f"\033[33mProcessing\033[0m {len(input_paths)} \033[33mfile(s)\033[0m")
        print("---------------")
        print(f"\033[33m📥 Input folder:\033[0m {src_path}")
        print(f"\033[33m📤 Output:\033[0m {output_path}")
        print(f"\033[33m⚡ Workers:\033[0m {max_workers}")
        print("---------------")
        print()
        
        # Create and run processing script
        script_path = create_processing_script(input_paths, str(output_path), max_workers)
        
        try:
            result = subprocess.run([
                REMWM_VENV_PYTHON, str(script_path)
            ], cwd=REMWM_DIR)
            
            # Clean up temp script
            script_path.unlink()
            
            if result.returncode == 0:
                print()
                djj.prompt_open_folder(output_path)
                if tag_source:
                    tag_source_files(input_paths)
            else:
                print("❌ \033[33mProcessing failed. Check output above for details.\033[0m")
                
        except Exception as e:
            print(f"❌ \033[33mError during processing: {e}\033[0m")
            if script_path.exists():
                script_path.unlink()
    
    else:
        # Multi-file mode - create output folders next to each input
        print("\n" * 2)
        print(f"\n\033[1;33m🤖 AI Watermark Detection & Removal\033[0m")
        print(f"\033[33mProcessing\033[0m {len(input_paths)} \033[33mfile(s) individually\033[0m")
        print("---------------")
        print(f"\033[33m⚡ Workers:\033[0m {max_workers}")
        print("---------------")
        print()
        
        success_count = 0
        error_count = 0
        output_paths = set()
        
        # Group files by directory for batch processing
        files_by_dir = {}
        for file_path in input_paths:
            parent_dir = pathlib.Path(file_path).parent
            if parent_dir not in files_by_dir:
                files_by_dir[parent_dir] = []
            files_by_dir[parent_dir].append(file_path)
        
        # Process each directory group
        for parent_dir, files in files_by_dir.items():
            output_path = parent_dir / "WM"
            output_path.mkdir(parents=True, exist_ok=True)
            output_paths.add(output_path)
            
            # Create and run processing script for this group
            script_path = create_processing_script(files, str(output_path), max_workers)
            
            try:
                result = subprocess.run([
                    REMWM_VENV_PYTHON, str(script_path)
                ], cwd=REMWM_DIR)
                
                script_path.unlink()
                
                if result.returncode == 0:
                    success_count += len(files)
                else:
                    error_count += len(files)
                    
            except Exception as e:
                print(f"❌ Error processing files in {parent_dir}: {e}")
                error_count += len(files)
                if script_path.exists():
                    script_path.unlink()
        
        # Tag source files if requested and successful
        if tag_source and success_count > 0:
            tag_source_files(input_paths)
        
        # Handle opening output folders
        if len(output_paths) == 1:
            output_path = list(output_paths)[0]
            djj.prompt_open_folder(output_path)
        elif len(output_paths) > 1:
            print(f"\033[33m📁 Created files in {len(output_paths)} different output folders.\033[0m")
            djj.open_multiple_folders(list(output_paths), max_open=3)

def main():
    os.system('clear')
    
    # Check if rem-wm is set up
    if not verify_setup():
        print("\n\033[33mPlease set up rem-wm first, then run this script again.\033[0m")
        sys.exit(1)
    
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mAI Watermark Remover\033[0m")
        print("Auto-Detect & Remove with Florence-2 + LAMA")
        print("\033[92m==================================================\033[0m")
        print()
        
        input_files, input_mode, src_path = get_valid_inputs()
        
        # Get processing options
        max_workers_input = input("\033[33mNumber of parallel workers (default 4):\033[0m\n > ").strip()
        try:
            max_workers = int(max_workers_input) if max_workers_input else 4
            if not 1 <= max_workers <= 8:
                raise ValueError("Workers must be between 1 and 8")
        except ValueError:
            print("⚠️  \033[33mUsing default 4 workers\033[0m")
            max_workers = 4
        
        tag_source = djj.prompt_choice(
            "\033[33mTag source files with 'WM' (watermark processed)?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='1'
        ) == '1'
        
        os.system('clear')
        
        # Process files
        process_files(input_files, input_mode, src_path, max_workers, tag_source)
        
        print()
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()