#!/usr/bin/env python3
"""
Enhanced File Identifier Tool
Deep file type detection and mismatch identification
Updated: July 30, 2025
"""

import os
import sys
import subprocess
import time
import csv
from pathlib import Path
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
import djjtb.utils as djj

os.system('clear')

def clean_path(path_str):
    return path_str.strip().strip('\'"')

def detect_true_file_type(file_path):
    """Detect true file type using magic numbers if available"""
    if not MAGIC_AVAILABLE:
        return get_file_type_by_extension(file_path), "magic_not_available"
    
    try:
        file_type = magic.from_file(str(file_path), mime=True)
        
        if file_type.startswith('video/'):
            return 'Video', file_type
        elif file_type.startswith('image/'):
            return 'Image', file_type
        elif file_type.startswith('audio/'):
            return 'Audio', file_type
        elif file_type.startswith('text/'):
            return 'Text', file_type
        elif file_type.startswith('application/'):
            if 'pdf' in file_type:
                return 'PDF', file_type
            elif 'zip' in file_type or 'compressed' in file_type:
                return 'Archive', file_type
            else:
                return 'Application', file_type
        else:
            return 'Other', file_type
    except Exception as e:
        return 'Unknown', f"error: {str(e)}"

def get_file_type_by_extension(filename):
    """Fallback file type detection by extension"""
    video_extensions = ['.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v', '.flv', '.wmv', '.3gp']
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.ico', '.heic', '.heif']
    audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.wma']
    text_extensions = ['.txt', '.md', '.rtf', '.log', '.csv', '.json', '.xml', '.html', '.css', '.js', '.py', '.sh']
    archive_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']
    
    ext = Path(filename).suffix.lower()
    if ext in video_extensions:
        return 'Video'
    elif ext in image_extensions:
        return 'Image'
    elif ext in audio_extensions:
        return 'Audio'
    elif ext in text_extensions:
        return 'Text'
    elif ext in archive_extensions:
        return 'Archive'
    elif ext == '.pdf':
        return 'PDF'
    else:
        return 'Unknown'

def collect_and_select_files(input_path, include_sub=False):
    """Collect all files and let user select which ones to analyze"""
    input_path_obj = Path(input_path)
    all_files = []
    
    if input_path_obj.is_dir():
        if include_sub:
            for root, _, files in os.walk(input_path):
                for file in files:
                    if not file.startswith('.'):  # Skip hidden files
                        all_files.append(str(Path(root) / file))
        else:
            for file in input_path_obj.glob('*'):
                if file.is_file() and not file.name.startswith('.'):
                    all_files.append(str(file))
    
    all_files = sorted(all_files, key=str.lower)
    
    if not all_files:
        return []
    
    print(f"📁 Found {len(all_files)} files")
    
    # Show files and let user select
    selection_mode = djj.prompt_choice(
        "\033[93mFile selection:\033[0m\n1. Analyze all files\n2. Select specific files\n",
        ['1', '2'],
        default='1'
    )
    
    if selection_mode == '1':
        return all_files
    
    # Show files for selection (in chunks if too many)
    if len(all_files) > 50:
        print(f"\033[93mToo many files ({len(all_files)}) to display individually.\033[0m")
        analyze_all = djj.prompt_choice(
            "\033[93mProceed with all files?\033[0m\n1. Yes, analyze all\n2. No, go back\n",
            ['1', '2'],
            default='1'
        )
        return all_files if analyze_all == '1' else []
    
    print("\033[93mAvailable files:\033[0m")
    for i, file_path in enumerate(all_files, 1):
        print(f"{i:3d}. {os.path.basename(file_path)}")
    
    print("\nEnter file numbers (e.g., 1,3,5-8,10) or 'all':")
    selection = input(" > ").strip().lower()
    
    if selection == 'all':
        return all_files
    
    # Parse selection
    selected_files = []
    try:
        for part in selection.split(','):
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                for i in range(start, end + 1):
                    if 1 <= i <= len(all_files):
                        selected_files.append(all_files[i-1])
            else:
                i = int(part)
                if 1 <= i <= len(all_files):
                    selected_files.append(all_files[i-1])
    except ValueError:
        print("❌ Invalid selection format")
        return []
    
    return list(dict.fromkeys(selected_files))  # Remove duplicates

def get_file_info_enhanced(file_path):
    """Get enhanced file information including true file type detection"""
    path_obj = Path(file_path)
    try:
        stat = path_obj.stat()
        
        # Get true file type using magic numbers
        true_type, mime_type = detect_true_file_type(file_path)
        extension_type = get_file_type_by_extension(path_obj.name)
        
        # Check if extension matches true type
        type_mismatch = (true_type != extension_type and true_type not in ['Other', 'Unknown'])
        
        return {
            'filename': path_obj.name,
            'extension': path_obj.suffix.lower(),
            'extension_suggests': extension_type,
            'true_file_type': true_type,
            'mime_type': mime_type,
            'type_mismatch': 'Yes' if type_mismatch else 'No',
            'size_bytes': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'path': str(path_obj.parent),
            'full_path': str(path_obj),
            'modified_date': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
        }
    except Exception as e:
        return {
            'filename': path_obj.name,
            'extension': path_obj.suffix.lower(),
            'extension_suggests': get_file_type_by_extension(path_obj.name),
            'true_file_type': 'Error',
            'mime_type': 'unknown',
            'type_mismatch': 'Unknown',
            'size_bytes': 0,
            'size_mb': 0,
            'path': str(path_obj.parent),
            'full_path': str(path_obj),
            'error': str(e)
        }

def export_to_csv(data, csv_path):
    """Export file data to CSV"""
    try:
        valid_data = [item for item in data if item is not None and isinstance(item, dict)]
        if not valid_data:
            return False
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = valid_data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(valid_data)
        return True
    except Exception:
        return False

def main():
    """Enhanced file identification function"""
    djj.setup_terminal()
    
    while True:
        os.system('clear')
        print()
        print("\033[92m==================================================\033[0m")
        print("         \033[1;33m🔍 ENHANCED FILE IDENTIFIER 📋\033[0m")
        print("\033[92m==================================================\033[0m")
        print("Deep file type detection and mismatch identification")
        print("\033[92m==================================================\033[0m")
        print()

        if not MAGIC_AVAILABLE:
            print("\033[93m⚠️  python-magic not available - using extension-based detection only\033[0m")
            print("   Install with: pip install python-magic")
            print()

        # Get input mode
        input_mode = djj.prompt_choice(
            "\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
            ['1', '2'],
            default='1'
        )
        print()

        files_data = []
        input_base_path = None
        is_folder_mode = False

        if input_mode == '1':
            # Folder mode
            input_path = djj.get_path_input("📁 Enter folder path")
            input_base_path = input_path
            is_folder_mode = True
            print()
            
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes, 2. No ",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            
            all_files = collect_and_select_files(input_path, include_sub)
            
        else:
            # File paths mode
            file_paths = input("📁 \033[93mEnter file paths (space-separated): \n\033[0m -> ").strip()
            
            if not file_paths:
                print("❌ \033[93mNo file paths provided.\033[0m")
                continue
            
            all_files = []
            paths = file_paths.strip().split()
            
            for path in paths:
                path = clean_path(path)
                path_obj = Path(path)
                
                if path_obj.is_file():
                    all_files.append(str(path_obj))
                elif path_obj.is_dir():
                    for file in path_obj.glob('*'):
                        if file.is_file() and not file.name.startswith('.'):
                            all_files.append(str(file))
            
            all_files = sorted(all_files, key=str.lower)
            if all_files:
                input_base_path = str(Path(all_files[0]).parent)
            print()

        if not all_files:
            print("❌ \033[93mNo valid files found. Try again.\033[0m\n")
            continue

        print(f"✅ \033[93m{len(all_files)} files selected for analysis\033[0m")
        print()
        print("🧪 Analyzing file types with deep detection...")
        print("-------------")

        # Collect file information with enhanced detection
        mismatched_files = []

        for idx, file_path in enumerate(all_files, 1):
            display_name = os.path.basename(file_path)[:30] + "..." if len(os.path.basename(file_path)) > 30 else os.path.basename(file_path)
            sys.stdout.write(f"\r\033[93mAnalyzing\033[0m {idx}\033[93m/\033[0m{len(all_files)}: {display_name}                    ")
            sys.stdout.flush()
            
            file_info = get_file_info_enhanced(file_path)
            files_data.append(file_info)
            
            # Track mismatched files
            if file_info.get('type_mismatch') == 'Yes':
                mismatched_files.append(file_info)

        sys.stdout.write(f"\r{' ' * 80}\r")
        sys.stdout.flush()

        # Display comprehensive summary
        print()
        print("\033[93m🔍 Enhanced File Analysis Summary\033[0m")
        print("-" * 35)
        
        # Count by detected file type
        true_type_counts = {}
        ext_type_counts = {}
        ext_counts = {}
        mime_counts = {}
        
        for file_data in files_data:
            true_type = file_data['true_file_type']
            ext_type = file_data['extension_suggests']
            extension = file_data['extension']
            mime_type = file_data['mime_type'].split('/')[0] if '/' in file_data['mime_type'] else file_data['mime_type']
            
            true_type_counts[true_type] = true_type_counts.get(true_type, 0) + 1
            ext_type_counts[ext_type] = ext_type_counts.get(ext_type, 0) + 1
            ext_counts[extension] = ext_counts.get(extension, 0) + 1
            mime_counts[mime_type] = mime_counts.get(mime_type, 0) + 1
        
        print(f"\033[93mTotal files analyzed:\033[0m {len(files_data)}")
        print()
        
        print("\033[93m🎯 True file types (magic number detection):\033[0m")
        for file_type, count in sorted(true_type_counts.items()):
            print(f"  {file_type}: {count}")
        
        print()
        print("\033[93m📝 Extension-based types:\033[0m")
        for file_type, count in sorted(ext_type_counts.items()):
            print(f"  {file_type}: {count}")
        
        print()
        print("\033[93m🔗 Extensions (top 10):\033[0m")
        sorted_extensions = sorted(ext_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for ext, count in sorted_extensions:
            ext_display = ext if ext else '(no extension)'
            print(f"  {ext_display}: {count}")
        
        if MAGIC_AVAILABLE:
            print()
            print("\033[93m🧬 MIME types:\033[0m")
            sorted_mimes = sorted(mime_counts.items(), key=lambda x: x[1], reverse=True)[:8]
            for mime, count in sorted_mimes:
                print(f"  {mime}: {count}")

        # Highlight mismatched files
        if mismatched_files:
            print()
            print(f"\033[91m⚠️  TYPE MISMATCHES DETECTED: {len(mismatched_files)} files\033[0m")
            print("\033[93mFiles where extension doesn't match true type:\033[0m")
            for mismatch in mismatched_files[:10]:
                print(f"  {mismatch['filename']}: {mismatch['extension_suggests']} → {mismatch['true_file_type']}")
            if len(mismatched_files) > 10:
                print(f"  ... and {len(mismatched_files) - 10} more (see CSV for full list)")
        else:
            print()
            print("\033[92m✅ No type mismatches detected - all extensions match file contents\033[0m")

        # Ask about CSV export
        print()
        export_csv = djj.prompt_choice(
            "\033[93mExport detailed analysis to CSV?\033[0m\n1. Yes\n2. No\n",
            ['1', '2'],
            default='1'
        ) == '1'

        if export_csv:
            # Determine CSV filename
            if is_folder_mode:
                folder_name = Path(input_base_path).name
                csv_filename = f"{folder_name}_file_analysis.csv"
            else:
                csv_filename = f"file_analysis_{time.strftime('%Y%m%d_%H%M%S')}.csv"
            
            csv_path = Path(input_base_path) / csv_filename
            
            if export_to_csv(files_data, csv_path):
                print(f"\033[93m📊 Enhanced analysis exported to:\033[0m\n{csv_path}")
                print()
                
                open_folder = djj.prompt_choice(
                    "\033[93mOpen output folder?\033[0m\n1. Yes\n2. No\n",
                    ['1', '2'],
                    default='1'
                ) == '1'
                
                if open_folder:
                    subprocess.run(['open', str(csv_path.parent)])
            else:
                print("\033[93m❌ Failed to export CSV\033[0m")

        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()