import os
import sys
import shutil
import re
import pathlib
import djjtb.utils as djj

os.system('clear')

def collect_files_from_folder(folder_path, extensions=None):
    """Collect files from a folder (non-recursive)."""
    folder_path_obj = pathlib.Path(folder_path)
    
    if not folder_path_obj.is_dir():
        return []
    
    files = []
    for item in folder_path_obj.iterdir():
        if item.is_file():
            if extensions is None or item.suffix.lower() in extensions:
                files.append(str(item))
    
    return sorted(files, key=str.lower)


def collect_files_from_paths(file_paths, extensions=None):
    """Collect files from space-separated paths (files or folders, non-recursive)."""
    files = []
    paths = file_paths.strip().split()
    
    for path in paths:
        path = path.strip('\'"')
        path_obj = pathlib.Path(path).expanduser().resolve()
        
        if path_obj.is_file():
            if extensions is None or path_obj.suffix.lower() in extensions:
                files.append(str(path_obj))
        elif path_obj.is_dir():
            files.extend(collect_files_from_folder(str(path_obj), extensions))
    
    return sorted(files, key=str.lower)


def collect_files_from_txt(txt_path, extensions=None):
    """Collect files from paths listed in a txt file."""
    paths = djj.get_paths_from_txt("Enter txt file path")
    
    if not paths:
        return []
    
    files = []
    for path in paths:
        path_obj = pathlib.Path(path)
        if path_obj.is_file():
            if extensions is None or path_obj.suffix.lower() in extensions:
                files.append(str(path))
        elif path_obj.is_dir():
            files.extend(collect_files_from_folder(str(path), extensions))
    
    return sorted(set(files), key=str.lower)


def sort_files_by_pattern(files, match_type, char_count, parent_folder):
    """Sort files into subfolders based on prefix or suffix pattern."""
    
    sorted_count = 0
    skipped_count = 0
    folders_created = set()
    
    for file_path in files:
        filename = os.path.basename(file_path)
        
        # Extract the pattern string
        if match_type == 'prefix':
            if len(filename) < char_count:
                print(f"\033[93m⚠️  Skipping (too short): {filename}\033[0m")
                skipped_count += 1
                continue
            pattern = filename[:char_count]
        
        else:  # suffix
            name_without_ext = os.path.splitext(filename)[0]
            if len(name_without_ext) < char_count:
                print(f"\033[93m⚠️  Skipping (too short): {filename}\033[0m")
                skipped_count += 1
                continue
            pattern = name_without_ext[-char_count:]
        
        # Create destination folder
        dest_folder = os.path.join(parent_folder, pattern)
        
        if dest_folder not in folders_created:
            os.makedirs(dest_folder, exist_ok=True)
            folders_created.add(dest_folder)
        
        # Move the file
        dest_path = os.path.join(dest_folder, filename)
        
        try:
            shutil.move(file_path, dest_path)
            sorted_count += 1
        except Exception as e:
            print(f"\033[93m❌ Error moving {filename}: {e}\033[0m")
            skipped_count += 1
    
    return sorted_count, skipped_count, len(folders_created)


def sort_files_by_count(files, files_per_folder, parent_folder, num_groups=None, remainder=0):
    """Sort files into sequentially numbered subfolders.

    Count mode (num_groups=None): N files per folder, last partial batch
    stays put as orphans.
    Group mode (num_groups set): exactly N even folders + a separate
    orphan folder for any remainder files.
    """

    # Re-verify every file still exists (guards against stale lists / re-runs)
    files        = [f for f in files if os.path.isfile(f)]
    total_files  = len(files)

    if num_groups is not None:
        full_batches = num_groups
        orphan_count = total_files - (num_groups * files_per_folder)
    else:
        full_batches = total_files // files_per_folder
        orphan_count = total_files  % files_per_folder

    if full_batches == 0:
        print(f"\033[93m⚠️  All {total_files} file(s) are orphans "
              f"(fewer than {files_per_folder} files). Nothing moved.\033[0m")
        return 0, 0, 0

    pad_width       = max(3, len(str(full_batches)))
    sorted_count    = 0
    skipped_count   = 0
    folders_created = set()
    parent_name     = os.path.basename(parent_folder)

    for batch_idx in range(full_batches):
        folder_name = f"{parent_name}-{str(batch_idx + 1).zfill(pad_width)}"
        dest_folder = os.path.join(parent_folder, folder_name)

        if dest_folder not in folders_created:
            os.makedirs(dest_folder, exist_ok=True)
            folders_created.add(dest_folder)

        batch_files = files[batch_idx * files_per_folder : (batch_idx + 1) * files_per_folder]

        for file_path in batch_files:
            filename  = os.path.basename(file_path)
            dest_path = os.path.join(dest_folder, filename)
            try:
                shutil.move(file_path, dest_path)
                sorted_count += 1
            except Exception as e:
                print(f"\033[93m❌ Error moving {filename}: {e}\033[0m")
                skipped_count += 1

    # Group mode: move remainder into a dedicated orphan folder
    if num_groups is not None and orphan_count > 0:
        orphan_folder = os.path.join(parent_folder, f"{parent_name}-orphans")
        os.makedirs(orphan_folder, exist_ok=True)
        folders_created.add(orphan_folder)
        for file_path in files[num_groups * files_per_folder:]:
            filename  = os.path.basename(file_path)
            dest_path = os.path.join(orphan_folder, filename)
            try:
                shutil.move(file_path, dest_path)
                sorted_count += 1
            except Exception as e:
                print(f"\033[93m❌ Error moving {filename}: {e}\033[0m")
                skipped_count += 1
        print(f"\033[93m⚠️  {orphan_count} file(s) moved to orphan folder.\033[0m")

    elif orphan_count:
        print(f"\033[93m⚠️  {orphan_count} orphan file(s) left in place "
              f"(not enough to fill a full batch of {files_per_folder}).\033[0m")

    return sorted_count, skipped_count, len(folders_created)


def main():
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mSubfolder Sorter\033[0m")
        print("Sort files into subfolders by filename pattern")
        print("\033[92m==================================================\033[0m")
        print()

        # A. Input mode selection
        input_mode = djj.prompt_choice(
            "\033[93mInput mode:\033[0m\n"
            "1. Folder path\n"
            "2. Multiple files (space-separated)\n"
            "3. Path list from txt file\n",
            ['1', '2', '3'],
            default='1'
        )
        print()

        files = []
        parent_folder = None

        if input_mode == '1':
            parent_folder = djj.get_path_input("Enter folder path")
            print()
            
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            
            if include_sub:
                for root, _, filenames in os.walk(parent_folder):
                    for filename in filenames:
                        files.append(os.path.join(root, filename))
                files = sorted(files, key=str.lower)
            else:
                files = collect_files_from_folder(parent_folder)
        
        elif input_mode == '2':
            file_paths = input("📁 \033[93mEnter file paths (space-separated):\n\033[0m -> ").strip()
            
            if not file_paths:
                print("❌ \033[93mNo file paths provided.\033[0m")
                continue
            
            files = collect_files_from_paths(file_paths)
            
            if files:
                parent_folder = str(pathlib.Path(files[0]).parent)
            print()
        
        else:  # input_mode == '3'
            files = collect_files_from_txt("")
            
            if not files:
                print("❌ \033[93mNo valid files found.\033[0m")
                continue
            
            if files:
                parent_folder = str(pathlib.Path(files[0]).parent)
            print()

        if not files:
            print("❌ \033[93mNo valid files found. Try again.\033[0m\n")
            continue

        # Always exclude folders and hidden files (e.g. .DS_Store) from the working list
        files = [f for f in files if os.path.isfile(f) and not os.path.basename(f).startswith('.')]

        print(f"✅ \033[93m{len(files)} file(s) found\033[0m")
        
        print("\nSample files:")
        for i, file in enumerate(files[:5]):
            print(f"  {i+1}. {os.path.basename(file)}")
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more")
        print()

        # B. Sort mode selection
        sort_mode = djj.prompt_choice(
            "\033[93mSort mode:\033[0m\n"
            "1. By filename pattern (prefix / suffix)\n"
            "2. By file count (N files per subfolder)\n"
            "3. By group count (divide into N groups evenly)\n",
            ['1', '2', '3'],
            default='1'
        )
        print()

        # ── Mode 1: pattern-based ────────────────────────────────────────────
        if sort_mode == '1':

            match_type_choice = djj.prompt_choice(
                "\033[93mMatch pattern by:\033[0m\n"
                "1. Prefix (from beginning)\n"
                "2. Suffix (from end, before extension)\n",
                ['1', '2'],
                default='1'
            )
            print()

            match_type = 'prefix' if match_type_choice == '1' else 'suffix'

            if match_type == 'prefix':
                while True:
                    char_input = input("\033[93mNumber of characters from beginning:\n\033[0m -> ").strip()
                    try:
                        char_count = int(char_input)
                        if char_count > 0:
                            break
                        else:
                            print("\033[93mPlease enter a positive number.\033[0m")
                    except ValueError:
                        print("\033[93mPlease enter a valid number.\033[0m")
            else:
                while True:
                    char_input = input("\033[93mNumber of characters from end (before extension):\n\033[0m -> ").strip()
                    try:
                        char_count = int(char_input)
                        if char_count > 0:
                            break
                        else:
                            print("\033[93mPlease enter a positive number.\033[0m")
                    except ValueError:
                        print("\033[93mPlease enter a valid number.\033[0m")

            print("\n" * 2)
            print("\033[1;93mProcessing...\033[0m")
            print()

            sorted_count, skipped_count, folders_created = sort_files_by_pattern(
                files, match_type, char_count, parent_folder
            )

        # ── Mode 2: count-based ──────────────────────────────────────────────
        elif sort_mode == '2':
            while True:
                count_input = input("\033[93mNumber of files per subfolder:\n\033[0m -> ").strip()
                try:
                    files_per_folder = int(count_input)
                    if files_per_folder > 0:
                        break
                    else:
                        print("\033[93mPlease enter a positive number.\033[0m")
                except ValueError:
                    print("\033[93mPlease enter a valid number.\033[0m")

            # Preview how it will split
            full_batches = len(files) // files_per_folder
            orphans      = len(files) %  files_per_folder
            print()
            print(f"  → \033[93m{full_batches} subfolder(s)\033[0m of {files_per_folder} files each", end="")
            if orphans:
                print(f", \033[93m{orphans} orphan(s)\033[0m left in place", end="")
            print()
            print()

            confirm = djj.prompt_choice(
                "\033[93mProceed?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'],
                default='1'
            )
            print()

            if confirm != '1':
                print("Cancelled.\n")
                action = djj.what_next()
                if action == 'exit':
                    break
                continue

            print("\033[1;93mProcessing...\033[0m")
            print()

            sorted_count, skipped_count, folders_created = sort_files_by_count(
                files, files_per_folder, parent_folder
            )

        # ── Mode 3: group-based ──────────────────────────────────────────────
        else:
            while True:
                group_input = input("\033[93mNumber of groups:\n\033[0m -> ").strip()
                try:
                    num_groups = int(group_input)
                    if num_groups > 0:
                        break
                    else:
                        print("\033[93mPlease enter a positive number.\033[0m")
                except ValueError:
                    print("\033[93mPlease enter a valid number.\033[0m")

            total_files      = len(files)
            files_per_group  = total_files // num_groups
            remainder        = total_files %  num_groups

            # Preview
            print()
            if remainder:
                print(f"  → \033[93m{num_groups}\033[0m even group(s) of \033[93m{files_per_group}\033[0m files"
                      f" + \033[93m1\033[0m orphan folder with \033[93m{remainder}\033[0m file(s)")
            else:
                print(f"  → \033[93m{num_groups}\033[0m group(s) of \033[93m{files_per_group}\033[0m files each, no orphans")
            print()

            confirm = djj.prompt_choice(
                "\033[93mProceed?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'],
                default='1'
            )
            print()

            if confirm != '1':
                print("Cancelled.\n")
                action = djj.what_next()
                if action == 'exit':
                    break
                continue

            print("\033[1;93mProcessing...\033[0m")
            print()

            sorted_count, skipped_count, folders_created = sort_files_by_count(
                files, files_per_group, parent_folder, num_groups=num_groups
            )

        # ── Summary ──────────────────────────────────────────────────────────
        print()
        print("\033[93mSorting Summary\033[0m")
        print("---------------")
        print(f"\033[93mFiles sorted:\033[0m {sorted_count}")
        print(f"\033[93mFiles skipped:\033[0m {skipped_count}")
        print(f"\033[93mFolders created:\033[0m {folders_created}")
        print(f"\033[93mParent folder:\033[0m {parent_folder}")
        print()

        djj.prompt_open_folder(parent_folder)
        print()
        
        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == '__main__':
    main()
