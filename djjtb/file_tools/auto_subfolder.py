import os
import sys
import shutil
import re
import pathlib
import json
import datetime
import djjtb.utils as djj

os.system('clear')

# ── Undo Manifest Helpers ─────────────────────────────────────────────────────

DJJTB_HIDDEN = ".djjtb"
UNDO_PREFIX  = "subfolder_sort_undo"

def get_undo_dir(parent_folder):
    return os.path.join(parent_folder, DJJTB_HIDDEN)

def list_undo_manifests(parent_folder):
    """Return sorted list of undo manifest paths (oldest first)."""
    undo_dir = get_undo_dir(parent_folder)
    if not os.path.isdir(undo_dir):
        return []
    manifests = sorted([
        os.path.join(undo_dir, f)
        for f in os.listdir(undo_dir)
        if f.startswith(UNDO_PREFIX) and f.endswith(".json")
    ])
    return manifests

def save_undo_manifest(parent_folder, move_map):
    """
    Save a manifest of {dest: src} so the sort can be reversed later.
    move_map is {destination_path: original_path}.
    """
    undo_dir = get_undo_dir(parent_folder)
    os.makedirs(undo_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"{UNDO_PREFIX}_{timestamp}.json"
    filepath  = os.path.join(undo_dir, filename)

    with open(filepath, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "parent_folder": parent_folder,
            "moves": move_map
        }, f, indent=2)

    return filepath

def run_undo(parent_folder):
    """Offer user a choice of undo manifests and reverse the selected sort."""
    manifests = list_undo_manifests(parent_folder)
    if not manifests:
        print("\033[93m⚠️  No undo history found for this folder.\033[0m")
        return

    print(f"\033[93mUndo history ({len(manifests)} operation(s)):\033[0m")
    for i, m in enumerate(reversed(manifests), 1):
        data = json.load(open(m))
        print(f"  {i}. {data['timestamp']}  ({len(data['moves'])} files)")

    choices = [str(i) for i in range(1, len(manifests) + 1)]
    choice = djj.prompt_choice("\033[93mWhich operation to undo?\033[0m", choices, default='1')
    print()

    selected = list(reversed(manifests))[int(choice) - 1]
    data = json.load(open(selected))
    moves = data["moves"]

    restored = 0
    missing  = 0
    failed   = 0

    print("\033[1;93mRestoring files...\033[0m")
    for dest, src in moves.items():
        if not os.path.isfile(dest):
            print(f"  \033[93m⚠️  Not found (skipping): {os.path.basename(dest)}\033[0m")
            missing += 1
            continue
        try:
            os.makedirs(os.path.dirname(src), exist_ok=True)
            shutil.move(dest, src)
            restored += 1
        except Exception as e:
            print(f"  \033[91m❌ Error restoring {os.path.basename(dest)}: {e}\033[0m")
            failed += 1

    # Clean up empty folders created by the sort
    for dest in moves.keys():
        folder = os.path.dirname(dest)
        try:
            if os.path.isdir(folder) and not os.listdir(folder):
                os.rmdir(folder)
        except Exception:
            pass

    os.remove(selected)

    print()
    print("\033[93mUndo Summary\033[0m")
    print("---------------")
    print(f"\033[92m✅ Restored:\033[0m  {restored}")
    if missing:
        print(f"\033[93m⚠️  Not found:\033[0m {missing}")
    if failed:
        print(f"\033[91m❌ Failed:\033[0m    {failed}")
    print()

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


def sort_files_by_pattern(files, match_type, char_count, parent_folder, move_map=None):
    """Sort files into subfolders based on prefix or suffix pattern."""
    if move_map is None:
        move_map = {}

    sorted_count = 0
    skipped_count = 0
    folders_created = set()
    
    for file_path in files:
        filename = os.path.basename(file_path)
        
        if match_type == 'prefix':
            if len(filename) < char_count:
                print(f"\033[93m⚠️  Skipping (too short): {filename}\033[0m")
                skipped_count += 1
                continue
            pattern = filename[:char_count]
        else:
            name_without_ext = os.path.splitext(filename)[0]
            if len(name_without_ext) < char_count:
                print(f"\033[93m⚠️  Skipping (too short): {filename}\033[0m")
                skipped_count += 1
                continue
            pattern = name_without_ext[-char_count:]
        
        dest_folder = os.path.join(parent_folder, pattern)
        
        if dest_folder not in folders_created:
            os.makedirs(dest_folder, exist_ok=True)
            folders_created.add(dest_folder)
        
        dest_path = os.path.join(dest_folder, filename)
        
        try:
            shutil.move(file_path, dest_path)
            move_map[dest_path] = file_path
            sorted_count += 1
        except Exception as e:
            print(f"\033[93m❌ Error moving {filename}: {e}\033[0m")
            skipped_count += 1
    
    return sorted_count, skipped_count, len(folders_created), move_map


def sort_files_by_count(files, files_per_folder, parent_folder, num_groups=None, remainder=0, move_map=None):
    """Sort files into sequentially numbered subfolders."""
    if move_map is None:
        move_map = {}

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
        return 0, 0, 0, move_map

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
                move_map[dest_path] = file_path
                sorted_count += 1
            except Exception as e:
                print(f"\033[93m❌ Error moving {filename}: {e}\033[0m")
                skipped_count += 1

    if num_groups is not None and orphan_count > 0:
        orphan_folder = os.path.join(parent_folder, f"{parent_name}-orphans")
        os.makedirs(orphan_folder, exist_ok=True)
        folders_created.add(orphan_folder)
        for file_path in files[num_groups * files_per_folder:]:
            filename  = os.path.basename(file_path)
            dest_path = os.path.join(orphan_folder, filename)
            try:
                shutil.move(file_path, dest_path)
                move_map[dest_path] = file_path
                sorted_count += 1
            except Exception as e:
                print(f"\033[93m❌ Error moving {filename}: {e}\033[0m")
                skipped_count += 1
        print(f"\033[93m⚠️  {orphan_count} file(s) moved to orphan folder.\033[0m")

    elif orphan_count:
        print(f"\033[93m⚠️  {orphan_count} orphan file(s) left in place "
              f"(not enough to fill a full batch of {files_per_folder}).\033[0m")

    return sorted_count, skipped_count, len(folders_created), move_map


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
        include_sub = False
        folder_file_map = None  # {folder: [files]} used for subfolder-aware sorting

        if input_mode == '1':
            parent_folder = djj.get_path_input("Enter folder path")
            print()

            # ── Check for undo history before asking anything else ────────────
            manifests = list_undo_manifests(parent_folder)
            if manifests:
                undo_choice = djj.prompt_choice(
                    f"\033[93m↩️  Undo history found ({len(manifests)} operation(s)). What would you like to do?\033[0m\n"
                    "1. Sort files (new operation)\n"
                    "2. Undo a previous sort\n",
                    ['1', '2'],
                    default='1'
                )
                print()
                if undo_choice == '2':
                    run_undo(parent_folder)
                    djj.prompt_open_folder(parent_folder)
                    action = djj.what_next()
                    if action == 'exit':
                        break
                    continue

            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'],
                default='2'
            ) == '1'
            print()

            if include_sub:
                # Build per-folder map so we sort within each folder independently
                folder_file_map = {}
                for root, dirs, filenames in os.walk(parent_folder):
                    # Skip hidden dirs (including .djjtb) and dirs created by previous sorts
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    folder_files = sorted(
                        [os.path.join(root, f) for f in filenames if not f.startswith('.')],
                        key=str.lower
                    )
                    if folder_files:
                        folder_file_map[root] = folder_files
                files = [f for fl in folder_file_map.values() for f in fl]
            else:
                files = collect_files_from_folder(parent_folder)

        elif input_mode == '2':
            file_paths = input("📁 \033[93mEnter file paths (space-separated):\n\033[0m -> ").strip()
            if not file_paths:
                print("❌ \033[93mNo file paths provided.\033[0m")
                continue
            files = djj.parse_multipath_input(file_paths)
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

        # Exclude hidden files
        files = [f for f in files if os.path.isfile(f) and not os.path.basename(f).startswith('.')]
        if folder_file_map:
            folder_file_map = {
                folder: [f for f in flist if not os.path.basename(f).startswith('.')]
                for folder, flist in folder_file_map.items()
                if any(not os.path.basename(f).startswith('.') for f in flist)
            }

        print(f"✅ \033[93m{len(files)} file(s) found\033[0m")
        if include_sub and folder_file_map:
            print(f"   across \033[93m{len(folder_file_map)} folder(s)\033[0m")
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

        # ── Collect sort parameters ──────────────────────────────────────────
        match_type = None
        char_count = None
        files_per_folder = None
        num_groups = None

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
            label = "from beginning" if match_type == 'prefix' else "from end (before extension)"
            while True:
                char_input = input(f"\033[93mNumber of characters {label}:\n\033[0m -> ").strip()
                try:
                    char_count = int(char_input)
                    if char_count > 0:
                        break
                    print("\033[93mPlease enter a positive number.\033[0m")
                except ValueError:
                    print("\033[93mPlease enter a valid number.\033[0m")

        elif sort_mode == '2':
            while True:
                count_input = input("\033[93mNumber of files per subfolder:\n\033[0m -> ").strip()
                try:
                    files_per_folder = int(count_input)
                    if files_per_folder > 0:
                        break
                    print("\033[93mPlease enter a positive number.\033[0m")
                except ValueError:
                    print("\033[93mPlease enter a valid number.\033[0m")

            full_batches = len(files) // files_per_folder
            orphans      = len(files) %  files_per_folder
            print()
            print(f"  → \033[93m{full_batches} subfolder(s)\033[0m of {files_per_folder} files each", end="")
            if orphans:
                print(f", \033[93m{orphans} orphan(s)\033[0m left in place", end="")
            print()
            print()
            confirm = djj.prompt_choice("\033[93mProceed?\033[0m\n1. Yes\n2. No\n", ['1', '2'], default='1')
            print()
            if confirm != '1':
                print("Cancelled.\n")
                action = djj.what_next()
                if action == 'exit':
                    break
                continue

        else:  # sort_mode == '3'
            while True:
                group_input = input("\033[93mNumber of groups:\n\033[0m -> ").strip()
                try:
                    num_groups = int(group_input)
                    if num_groups > 0:
                        break
                    print("\033[93mPlease enter a positive number.\033[0m")
                except ValueError:
                    print("\033[93mPlease enter a valid number.\033[0m")

            total_files     = len(files)
            files_per_group = total_files // num_groups
            remainder       = total_files %  num_groups
            print()
            if remainder:
                print(f"  → \033[93m{num_groups}\033[0m even group(s) of \033[93m{files_per_group}\033[0m files"
                      f" + \033[93m1\033[0m orphan folder with \033[93m{remainder}\033[0m file(s)")
            else:
                print(f"  → \033[93m{num_groups}\033[0m group(s) of \033[93m{files_per_group}\033[0m files each, no orphans")
            print()
            confirm = djj.prompt_choice("\033[93mProceed?\033[0m\n1. Yes\n2. No\n", ['1', '2'], default='1')
            print()
            if confirm != '1':
                print("Cancelled.\n")
                action = djj.what_next()
                if action == 'exit':
                    break
                continue

        # ── Process ──────────────────────────────────────────────────────────
        print("\n\033[1;93mProcessing...\033[0m\n")

        global_move_map = {}
        total_sorted = total_skipped = total_folders = 0

        # Helper: run one sort call and accumulate results
        def run_sort(file_list, target_folder):
            nonlocal total_sorted, total_skipped, total_folders
            if sort_mode == '1':
                s, sk, f, mm = sort_files_by_pattern(
                    file_list, match_type, char_count, target_folder, global_move_map
                )
            elif sort_mode == '2':
                s, sk, f, mm = sort_files_by_count(
                    file_list, files_per_folder, target_folder, move_map=global_move_map
                )
            else:
                fpp = len(file_list) // num_groups
                if fpp == 0:
                    print(f"\033[93m⚠️  Skipping {os.path.basename(target_folder)}: fewer files than groups.\033[0m")
                    return
                s, sk, f, mm = sort_files_by_count(
                    file_list, fpp, target_folder, num_groups=num_groups, move_map=global_move_map
                )
            total_sorted  += s
            total_skipped += sk
            total_folders += f

        if include_sub and folder_file_map:
            # Sort within each original subfolder independently
            for folder, folder_files in folder_file_map.items():
                run_sort(folder_files, folder)
        else:
            run_sort(files, parent_folder)

        # Save undo manifest
        if global_move_map:
            manifest_path = save_undo_manifest(parent_folder, global_move_map)
            print(f"\033[92m💾 Undo manifest saved\033[0m ({len(global_move_map)} files)")

        # ── Summary ──────────────────────────────────────────────────────────
        print()
        print("\033[93mSorting Summary\033[0m")
        print("---------------")
        print(f"\033[93mFiles sorted:\033[0m   {total_sorted}")
        print(f"\033[93mFiles skipped:\033[0m  {total_skipped}")
        print(f"\033[93mFolders created:\033[0m {total_folders}")
        print(f"\033[93mParent folder:\033[0m  {parent_folder}")
        print()

        djj.prompt_open_folder(parent_folder)
        print()

        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == '__main__':
    main()
