#!/usr/bin/env python3
import os
import sys
import pathlib
import random
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import djjtb.utils as djj

os.system('clear')

def collect_files(input_path, include_subfolders=False):
    """Collect all files (images, videos, symlinks) from folder."""
    input_path_obj = pathlib.Path(input_path)
    
    extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic',
                 '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v',
                 '.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg')
    
    files = []
    if input_path_obj.is_dir():
        if include_subfolders:
            for root, _, filenames in os.walk(input_path):
                for filename in filenames:
                    file_path = pathlib.Path(root) / filename
                    if file_path.is_symlink() or file_path.suffix.lower() in extensions:
                        files.append(file_path)
        else:
            for file_path in input_path_obj.iterdir():
                if file_path.is_file() and (file_path.is_symlink() or file_path.suffix.lower() in extensions):
                    files.append(file_path)
    
    return sorted(files, key=lambda x: x.name.lower())


def collect_files_from_paths(file_paths):
    """Collect files from space-separated file paths."""
    files = []
    paths = file_paths.strip().split()
    
    for path_str in paths:
        path_str = path_str.strip('\'"')
        path_obj = pathlib.Path(path_str)
        
        if path_obj.is_file():
            files.append(path_obj)
        elif path_obj.is_dir():
            files.extend(collect_files(str(path_obj), include_subfolders=False))
    
    return sorted(files, key=lambda x: x.name.lower())


def collect_folders(parent_path, include_subfolders=False):
    """Collect subfolders from a parent folder, skipping hidden ones."""
    parent_path_obj = pathlib.Path(parent_path)
    folders = []

    if include_subfolders:
        for root, dirnames, _ in os.walk(parent_path):
            # Prune hidden dirs so we never descend into them
            dirnames[:] = [d for d in dirnames if not d.startswith('.')]
            for dirname in dirnames:
                folders.append(pathlib.Path(root) / dirname)
    else:
        for item in parent_path_obj.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                folders.append(item)

    return sorted(folders, key=lambda x: x.name.lower())


def rename_files(files, rename_mode, randomize, start_num, step, padding, custom_suffix=""):
    """Rename files according to specified parameters."""
    if not files:
        print("\033[93mNo files to rename.\033[0m")
        return 0
    
    print(f"\n\033[1;33mFound {len(files)} file(s) to process\033[0m")
    print("=" * 50)
    
    for i, file_path in enumerate(files[:5]):
        print(f"  {i+1}. {file_path.name}")
    if len(files) > 5:
        print(f"  ... and {len(files) - 5} more")
    print()
    
    working_files = files.copy()
    
    if randomize:
        random.shuffle(working_files)
        print("\033[93mFiles randomized!\033[0m")
    
    renamed_count = 0
    for i, file_path in enumerate(working_files):
        try:
            sequence_num = start_num + (i * step)
            sequence_str = f"{sequence_num:0{padding}d}"
            
            if rename_mode == 1:
                new_name = f"{sequence_str}{file_path.suffix}"
            elif rename_mode == 2:
                if custom_suffix:
                    new_name = f"{sequence_str}-{file_path.stem}_{custom_suffix}{file_path.suffix}"
                else:
                    new_name = f"{sequence_str}-{file_path.name}"
            
            new_path = file_path.parent / new_name
            
            counter = 1
            original_new_path = new_path
            while new_path.exists() and new_path != file_path:
                name_stem = original_new_path.stem
                suffix = original_new_path.suffix
                new_path = original_new_path.parent / f"{name_stem}_dup{counter}{suffix}"
                counter += 1
            
            file_path.rename(new_path)
            renamed_count += 1
            
            progress = (i + 1) / len(working_files) * 100
            print(f"\r\033[93mRenaming {i+1}/{len(working_files)} ({progress:.0f}%)...\033[0m", end='', flush=True)
            
        except Exception as e:
            print(f"\n\033[93mError renaming {file_path.name}: {e}\033[0m")
            continue
    
    print("\n" + "=" * 50)
    print(f"\033[92m✅ Successfully renamed {renamed_count} files\033[0m")
    return renamed_count


def rename_folders(folders, rename_mode, randomize, start_num, step, padding, custom_suffix=""):
    """Rename folders according to specified parameters."""
    if not folders:
        print("\033[93mNo folders to rename.\033[0m")
        return 0

    print(f"\n\033[1;33mFound {len(folders)} folder(s) to process\033[0m")
    print("=" * 50)

    for i, folder_path in enumerate(folders[:5]):
        print(f"  {i+1}. {folder_path.name}")
    if len(folders) > 5:
        print(f"  ... and {len(folders) - 5} more")
    print()

    working_folders = folders.copy()

    if randomize:
        random.shuffle(working_folders)
        print("\033[93mFolders randomized!\033[0m")

    renamed_count = 0
    for i, folder_path in enumerate(working_folders):
        try:
            sequence_num = start_num + (i * step)
            sequence_str = f"{sequence_num:0{padding}d}"

            if rename_mode == 1:  # Complete rename
                new_name = f"{sequence_str}"
            elif rename_mode == 2:  # Prepend sequence
                if custom_suffix:
                    new_name = f"{sequence_str}-{folder_path.name}_{custom_suffix}"
                else:
                    new_name = f"{sequence_str}-{folder_path.name}"

            new_path = folder_path.parent / new_name

            counter = 1
            original_new_path = new_path
            while new_path.exists() and new_path != folder_path:
                new_path = original_new_path.parent / f"{original_new_path.name}_dup{counter}"
                counter += 1

            folder_path.rename(new_path)
            renamed_count += 1

            progress = (i + 1) / len(working_folders) * 100
            print(f"\r\033[93mRenaming {i+1}/{len(working_folders)} ({progress:.0f}%)...\033[0m", end='', flush=True)

        except Exception as e:
            print(f"\n\033[93mError renaming {folder_path.name}: {e}\033[0m")
            continue

    print("\n" + "=" * 50)
    print(f"\033[92m✅ Successfully renamed {renamed_count} folders\033[0m")
    return renamed_count


if __name__ == '__main__':
    while True:
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mFile Randomizer & Sequencer\033[0m")
        print("Randomize and rename files, folders, images, videos & symlinks")
        print("\033[92m==================================================\033[0m")
        print()

        # 0. Top-level mode: files or folders
        top_mode = djj.prompt_choice(
            "Mode:\n💰\033[4m1\033[0m  Files\n💰\033[4m2\033[0m  Folders\n",
            ['1', '2'],
            default='1'
        )
        print()

        # ── FILES MODE ────────────────────────────────────────────────────────
        if top_mode == '1':

            input_mode = djj.prompt_choice(
                "Input mode:\n💰\033[4m1\033[0m Folder\n💰\033[4m2\033[0m  Multiple files/folders\n\033[4m💰3\033[0m  Single file",
                ['1', '2', '3'],
                default='1'
            )
            print()

            files = []
            folder_path = None

            if input_mode == '1':
                folder_path = djj.get_path_input("Enter folder path")
                print()

                include_sub = djj.prompt_choice(
                    "Include subfolders?\n💰\033[4m1\033[0m  Yes\n💰2  No\n ",
                    ['1', '2'],
                    default='2'
                ) == '1'
                print()

                files = collect_files(folder_path, include_sub)

            elif input_mode == '2':
                file_paths = input("📁 Enter file/folder paths (space-separated):\n -> ").strip()

                if not file_paths:
                    print("❌ No file paths provided.")
                    continue

                files = collect_files_from_paths(file_paths)
                if files:
                    folder_path = str(files[0].parent)
                print()

            elif input_mode == '3':
                file_path = djj.get_path_input("Enter file path")
                files = [pathlib.Path(file_path)]
                folder_path = str(files[0].parent)
                print()

            if not files:
                print("❌ No valid files found. Try again.\n")
                continue

            print(f"✅ Found {len(files)} file(s)")
            print()

            rename_mode = djj.prompt_choice(
                "Rename method:\n💰\033[4m1\033[0m  Complete filename to sequence\n \033[4m2\033[0m  Add sequence before (with separator)\n",
                ['1', '2'],
                default='2'
            )
            print()

            custom_suffix = ""
            if rename_mode == '2':
                add_suffix = djj.prompt_choice(
                    "Add custom suffix?\n💰\033[4m1\033[0m  Yes\n💰\033[4m2\033[0m  No\n",
                    ['1', '2'],
                    default='2'
                ) == '1'
                print()

                if add_suffix:
                    custom_suffix = input("Enter custom suffix (without underscore)\033[5m💰\033[0m ").strip()
                    print()

            randomize = djj.prompt_choice(
                "Randomized filenames?\n💰\033[4m1\033[0m  Yes\n💰\033[4m2\033[0m  No\n",
                ['1', '2'],
                default='2'
            ) == '1'
            print()

            print("\033[93mSequence Parameters:\033[0m")

            start_input = input("Starting number [default: 10000]: ").strip()
            start_num = int(start_input) if start_input else 10000

            while True:
                step_input = input("Step: ").strip()
                if step_input:
                    try:
                        step = int(step_input)
                        break
                    except ValueError:
                        print("Please enter a valid number.")
                else:
                    print("Step is required.")

            padding_input = input("Padding [default: 5]: ").strip()
            padding = int(padding_input) if padding_input else 5

            print()
            print("\033[1;33mProcessing...\033[0m")

            renamed_count = rename_files(
                files=files,
                rename_mode=int(rename_mode),
                randomize=randomize,
                start_num=start_num,
                step=step,
                padding=padding,
                custom_suffix=custom_suffix
            )

            print()
            print("\033[93mFile Renaming Complete!\033[0m")
            print("=" * 30)

            if renamed_count > 0 and folder_path:
                djj.prompt_open_folder(folder_path)

        # ── FOLDERS MODE ──────────────────────────────────────────────────────
        else:

            folder_path = djj.get_path_input("Enter parent folder path")
            print()

            include_sub = djj.prompt_choice(
                "Include subfolders recursively?\n💰\033[4m1\033[0m  Yes\n💰\033[4m2\033[0m  No\n",
                ['1', '2'],
                default='2'
            ) == '1'
            print()

            folders = collect_folders(folder_path, include_sub)

            if not folders:
                print("❌ No valid folders found. Try again.\n")
                continue

            print(f"✅ Found {len(folders)} folder(s)")
            print()

            rename_mode = djj.prompt_choice(
                "Rename method:\n💰\033[4m1\033[0m  Complete folder name to sequence\n💰\033[4m2\033[0m  Add sequence before (with separator)\n",
                ['1', '2'],
                default='2'
            )
            print()

            custom_suffix = ""
            if rename_mode == '2':
                add_suffix = djj.prompt_choice(
                    "Add custom suffix?\n💰\033[4m1\033[0m  Yes\n💰\033[4m2\033[0m  No\n",
                    ['1', '2'],
                    default='2'
                ) == '1'
                print()

                if add_suffix:
                    custom_suffix = input("Enter custom suffix (without underscore)\033[5m💰\033[0m ").strip()
                    print()

            randomize = djj.prompt_choice(
                "Randomize folder order?\n💰\033[4m1\033[0m  Yes\n💰\033[4m2\033[0m  No\n",
                ['1', '2'],
                default='2'
            ) == '1'
            print()

            print("\033[93mSequence Parameters:\033[0m")

            start_input = input("Starting number [default: 10000]: ").strip()
            start_num = int(start_input) if start_input else 10000

            while True:
                step_input = input("Step: ").strip()
                if step_input:
                    try:
                        step = int(step_input)
                        break
                    except ValueError:
                        print("Please enter a valid number.")
                else:
                    print("Step is required.")

            padding_input = input("Padding [default: 5]: ").strip()
            padding = int(padding_input) if padding_input else 5

            print()
            print("\033[1;33mProcessing...\033[0m")

            renamed_count = rename_folders(
                folders=folders,
                rename_mode=int(rename_mode),
                randomize=randomize,
                start_num=start_num,
                step=step,
                padding=padding,
                custom_suffix=custom_suffix
            )

            print()
            print("\033[93mFolder Renaming Complete!\033[0m")
            print("=" * 30)

            if renamed_count > 0 and folder_path:
                djj.prompt_open_folder(folder_path)

        action = djj.what_next()
        if action == 'exit':
            break

    os.system('clear')