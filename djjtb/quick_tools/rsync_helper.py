#!/usr/bin/env python3
"""
DJJTB Rsync Helper
File sync tool for rsync operations
Updated: September 13, 2025
"""

import os
import sys
import pathlib
import subprocess
import djjtb.utils as djj

os.system('clear')

def filter_files_by_extensions(source_files, extensions):
    """Filter source files by extensions"""
    if not extensions:
        return source_files
    
    filtered_files = []
    extensions_lower = [ext.lower() for ext in extensions]
    
    for file_path in source_files:
        file_ext = pathlib.Path(file_path).suffix.lower().lstrip('.')
        if file_ext in extensions_lower:
            filtered_files.append(file_path)
    
    return filtered_files

def collect_files_from_folder(input_path, include_subfolders=False):
    """Collect files from folder - adapted from your utils pattern"""
    input_path_obj = pathlib.Path(input_path)
    
    files = []
    if input_path_obj.is_dir():
        if include_subfolders:
            for root, _, file_list in os.walk(input_path):
                files.extend(pathlib.Path(root) / f for f in file_list)
        else:
            files = [f for f in input_path_obj.glob('*') if f.is_file()]
    elif input_path_obj.is_file():
        files = [input_path_obj]
    
    return sorted([str(v) for v in files], key=str.lower)

def get_source_input():
    """Get source input using djj utility functions"""
    print(f"\033[92m=== RSYNC - SOURCE INPUT ===\033[0m")
    
    # Use your standard input mode selection pattern
    input_mode = djj.prompt_choice(
        "\033[93mInput mode:\033[0m\n1. Folder path\n2. Multiple files/folders (space-separated)\n",
        ['1', '2'],
        default='1'
    )
    print()
    
    source_files = []
    base_source_path = None
    
    if input_mode == '1':
        # Single folder mode
        folder_path = djj.get_path_input("📁 Enter source folder path")
        base_source_path = folder_path
        print()
        
        # Subfolder prompt (like your collage creator reference)
        include_sub = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No\n",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        
        # Use your collect_files_from_folder pattern
        source_files = collect_files_from_folder(folder_path, include_sub)
                
    else:
        # Use your multifile input handler
        source_files = djj.get_multifile_input(
            prompt_text="📁 Enter source paths",
            extensions=None,  # Accept all file types for file operations
            max_display=5
        )
        
        if source_files:
            # Set base path to parent of first file
            base_source_path = str(pathlib.Path(source_files[0]).parent)
    
    if not source_files:
        print("❌ \033[93mNo valid files found.\033[0m")
        return [], None
    
    return source_files, base_source_path

def get_destination_path(base_source_path):
    """Get destination path with default options"""
    print(f"\033[92m=== RSYNC - DESTINATION ===\033[0m")
    
    # Default to same path as source, right beside it
    default_dest = str(pathlib.Path(base_source_path).parent / f"{pathlib.Path(base_source_path).name}_rsync")
    
    dest_choice = djj.prompt_choice(
        f"\033[93mDestination location:\033[0m\n1. Same location as source ({default_dest})\n2. Custom path\n",
        ['1', '2'],
        default='1'
    )
    print()
    
    if dest_choice == '1':
        destination = default_dest
    else:
        destination = djj.get_path_input("📁 Enter destination path")
    
    # Create destination if it doesn't exist
    os.makedirs(destination, exist_ok=True)
    print(f"✅ \033[92mDestination: {destination}\033[0m")
    print()
    
    return destination

def perform_rsync(source_files, destination, delete_source, extensions, base_source_path, exclude_folders, exclude_extensions):
    """Perform rsync operations matching user's desired behavior"""
    print(f"\033[1;33m🔄 RSYNC OPERATION\033[0m")
    print("=" * 50)
    
    # Use folder-level rsync when we have a base source path
    if base_source_path:
        # Create destination path that includes the source folder name
        source_folder_name = os.path.basename(base_source_path.rstrip('/'))
        final_destination = os.path.join(destination, source_folder_name)
        
        print(f"Using folder-level rsync preserving structure")
        if extensions:
            print(f"Including extensions: {', '.join(extensions)}")
        if exclude_folders:
            print(f"Excluding folders: {', '.join(exclude_folders)}")
        if exclude_extensions:
            print(f"Excluding extensions: {', '.join(exclude_extensions)}")
        print(f"Source: {base_source_path}")
        print(f"Destination: {final_destination}")
        print()
        
        # Ensure destination exists
        os.makedirs(final_destination, exist_ok=True)
        
        # Build rsync command matching your example
        rsync_cmd = ['rsync', '-av']
        
        # Always include directories for traversal (unless specifically excluded)
        rsync_cmd.extend(['--include', '*/'])
        
        # Add exclude patterns for folders (folder mode only)
        if exclude_folders:
            for folder in exclude_folders:
                # Exclude both the folder itself and its contents
                rsync_cmd.extend(['--exclude', f"{folder}/"])
                rsync_cmd.extend(['--exclude', f"{folder}"])
        
        # Add exclude patterns for file extensions
        if exclude_extensions:
            for ext in exclude_extensions:
                rsync_cmd.extend(['--exclude', f"*.{ext}"])
                rsync_cmd.extend(['--exclude', f"*.{ext.upper()}"])
        
        # Add include patterns for extensions if specified
        if extensions:
            for ext in extensions:
                rsync_cmd.extend(['--include', f"*.{ext}"])
                rsync_cmd.extend(['--include', f"*.{ext.upper()}"])
            # Exclude everything else
            rsync_cmd.extend(['--exclude', '*'])
        
        # Add remove-source-files if delete requested
        if delete_source:
            rsync_cmd.append('--remove-source-files')
        
        # Add source (with trailing slash) and destination
        source_with_slash = base_source_path.rstrip('/') + '/'
        dest_with_slash = final_destination.rstrip('/') + '/'
        rsync_cmd.extend([source_with_slash, dest_with_slash])
        
        try:
            print("Running command:")
            print(' '.join(f'"{arg}"' if ' ' in arg else arg for arg in rsync_cmd))
            print()
            result = subprocess.run(rsync_cmd, text=True, timeout=600)
            
            if result.returncode == 0:
                print(f"\033[92m✅ Rsync completed successfully!\033[0m")
                if delete_source:
                    print(f"\033[93m🗑️  Source files were moved (deleted from source)\033[0m")
            else:
                print(f"\033[91m❌ Rsync failed with return code: {result.returncode}\033[0m")
                
        except subprocess.TimeoutExpired:
            print(f"\033[93m⏰ Rsync timed out\033[0m")
        except Exception as e:
            print(f"\033[93m❌ Error running rsync: {e}\033[0m")
    
    else:
        # Fallback for individual files (when using multiple files mode)
        # Filter files if extensions specified
        if extensions:
            original_count = len(source_files)
            source_files = filter_files_by_extensions(source_files, extensions)
            print(f"Filtered to {len(source_files)} files (from {original_count}) matching extensions: {', '.join(extensions)}")
            print()
        
        # Filter out excluded extensions
        if exclude_extensions:
            original_count = len(source_files)
            source_files = [f for f in source_files if not any(f.lower().endswith(f'.{ext.lower()}') for ext in exclude_extensions)]
            excluded_count = original_count - len(source_files)
            if excluded_count > 0:
                print(f"Excluded {excluded_count} files with extensions: {', '.join(exclude_extensions)}")
                print()
        
        if not source_files:
            print("❌ \033[93mNo files match the criteria after filtering.\033[0m")
            return
        
        print("Processing individual files...")
        success_count = 0
        error_count = 0
        
        for i, source_file in enumerate(source_files):
            file_name = os.path.basename(source_file)
            dest_file = os.path.join(destination, file_name)
            
            print(f"\033[93m[{i+1}/{len(source_files)}]:\033[0m {file_name}")
            
            try:
                result = subprocess.run([
                    'rsync', '-av', '--progress', source_file, dest_file
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    print(f"\033[92m  ✅ Synced\033[0m")
                    success_count += 1
                    
                    if delete_source:
                        try:
                            os.remove(source_file)
                            print(f"\033[93m  🗑️  Source deleted\033[0m")
                        except Exception as e:
                            print(f"\033[93m  ⚠️  Could not delete source: {e}\033[0m")
                else:
                    print(f"\033[91m  ❌ Failed: {result.stderr}\033[0m")
                    error_count += 1
                    
            except subprocess.TimeoutExpired:
                print(f"\033[93m  ⏰ Timeout\033[0m")
                error_count += 1
            except Exception as e:
                print(f"\033[93m  ❌ Error: {e}\033[0m")
                error_count += 1
        
        print("=" * 50)
        print(f"\033[1;33m🏁 RSYNC Complete!\033[0m")
        print(f"✅ \033[92mSuccessful:\033[0m {success_count}")
        print(f"❌ \033[93mFailed:\033[0m {error_count}")
        if delete_source:
            print(f"🗑️  \033[93mSource files deleted:\033[0m {success_count}")
    
    print()

def main():
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mRsync Helper\033[0m")
        print("File sync tool for rsync operations")
        print("\033[92m==================================================\033[0m")
        print()
        
        # Get source input
        source_files, base_source_path = get_source_input()
        if not source_files:
            continue
        
        # Get destination path
        destination = get_destination_path(base_source_path)
        
        # Rsync specific options
        
        # Include extensions
        extensions_input = input("\033[93mInclude file extensions (without dots, comma-separated) [leave empty for all files]:\n\033[0m -> ").strip()
        extensions = []
        if extensions_input:
            extensions = [ext.strip() for ext in extensions_input.split(',') if ext.strip()]
            print(f"Will include files with extensions: {', '.join(extensions)}")
        else:
            print("Will include all files")
        print()
        
        # Exclude options - different for folder vs multi-file mode
        exclude_folders = []
        exclude_extensions = []
        
        if base_source_path:  # Folder mode
            # Exclude folders
            exclude_folders_input = input("\033[93mExclude subfolders (folder names only, comma-separated) [e.g. __pycache__,node_modules] [leave empty for none]:\n\033[0m -> ").strip()
            if exclude_folders_input:
                exclude_folders = [folder.strip() for folder in exclude_folders_input.split(',') if folder.strip()]
                print(f"Will exclude folders: {', '.join(exclude_folders)}")
            else:
                print("No folders excluded")
            print()
            
            # Exclude file extensions
            exclude_ext_input = input("\033[93mExclude file extensions (without dots, comma-separated) [leave empty for none]:\n\033[0m -> ").strip()
            if exclude_ext_input:
                exclude_extensions = [ext.strip() for ext in exclude_ext_input.split(',') if ext.strip()]
                print(f"Will exclude files with extensions: {', '.join(exclude_extensions)}")
            else:
                print("No file extensions excluded")
            print()
        
        else:  # Multi-file mode
            # Only exclude file extensions
            exclude_ext_input = input("\033[93mExclude file extensions (without dots, comma-separated) [leave empty for none]:\n\033[0m -> ").strip()
            if exclude_ext_input:
                exclude_extensions = [ext.strip() for ext in exclude_ext_input.split(',') if ext.strip()]
                print(f"Will exclude files with extensions: {', '.join(exclude_extensions)}")
            else:
                print("No file extensions excluded")
            print()
        
        # Delete source option
        delete_source = djj.prompt_choice(
            "\033[93mDelete source files after sync?\033[0m\n1. Yes\n2. No\n",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        
        # Perform rsync operation
        perform_rsync(source_files, destination, delete_source, extensions, base_source_path, exclude_folders, exclude_extensions)
        
        # Open output folder and what next
        djj.prompt_open_folder(destination)
        
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == '__main__':
    main()