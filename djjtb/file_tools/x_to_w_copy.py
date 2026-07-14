#!/usr/bin/env python3
"""
X-to-W Folder Broadcaster — DJJTB File Tools
Copies files from x## source folders into every w## target folder,
renaming the suffix: -x01 → -w##a, -x02 → -w##b, etc.
Matching is positional (sorted order). Skips existing files.
"""

import os
import sys
import shutil
import pathlib
import djjtb.utils as djj

os.system('clear')

# x01→a, x02→b ... x26→z
def x_index_to_letter(x_folder_name):
    """Extract the numeric index from x01/x02/... and return matching letter."""
    digits = ''.join(c for c in x_folder_name if c.isdigit())
    if not digits:
        return None
    idx = int(digits)
    if 1 <= idx <= 26:
        return chr(ord('a') + idx - 1)
    return None


def collect_sorted_files(folder_path):
    """Return sorted list of files (not dirs) in a folder."""
    folder = pathlib.Path(folder_path)
    return sorted(
        [f for f in folder.iterdir() if f.is_file() and not f.name.startswith('.')],
        key=lambda f: f.name.lower()
    )


def strip_suffix_token(stem, suffix_token):
    """
    Remove a trailing -token from a filename stem.
    e.g. strip_suffix_token('JUDK_XMAS_Gemini-01-a01-x01', 'x01') → 'JUDK_XMAS_Gemini-01-a01'
    Handles the case where the token appears at the very end preceded by a dash.
    """
    tag = f"-{suffix_token}"
    if stem.endswith(tag):
        return stem[: -len(tag)]
    # Fallback: return as-is so we don't silently mangle names
    return stem


def build_new_filename(x_file, x_folder_name, w_folder_name, letter):
    """
    Given an x-file and destination w-folder, construct the new filename.
    e.g. JUDK_XMAS_Gemini-01-a01-x01.png  →  JUDK_XMAS_Gemini-01-a01-w00a.png
    """
    ext = x_file.suffix
    stem = x_file.stem  # e.g. JUDK_XMAS_Gemini-01-a01-x01
    base = strip_suffix_token(stem, x_folder_name)  # strip -x01
    new_stem = f"{base}-{w_folder_name}{letter}"    # append -w00a
    return f"{new_stem}{ext}"


def scan_base_folder(base_path):
    """
    Scan base_path for w## and x## subfolders.
    Returns (w_folders sorted, x_folders sorted) as lists of Path objects.
    """
    base = pathlib.Path(base_path)
    w_folders = sorted(
        [d for d in base.iterdir() if d.is_dir() and d.name.lower().startswith('w')],
        key=lambda d: d.name.lower()
    )
    x_folders = sorted(
        [d for d in base.iterdir() if d.is_dir() and d.name.lower().startswith('x')],
        key=lambda d: d.name.lower()
    )
    return w_folders, x_folders


def preview(base_path, w_folders, x_folders):
    """Print a structured preview before any copying happens."""
    print()
    print(f"\033[93m📁 Base folder:\033[0m {base_path}")
    print()
    print(f"\033[93m🎯 Target folders (w##) — {len(w_folders)} found:\033[0m")
    for w in w_folders:
        files = collect_sorted_files(w)
        print(f"   {w.name}  ({len(files)} file(s))")
    print()
    print(f"\033[93m📤 Source folders (x##) — {len(x_folders)} found:\033[0m")
    for x in x_folders:
        files = collect_sorted_files(x)
        letter = x_index_to_letter(x.name)
        print(f"   {x.name}  ({len(files)} file(s))  →  suffix letter: '{letter}'")
    print()

    # Show a concrete rename example using first x folder and first w folder
    if x_folders and w_folders:
        x = x_folders[0]
        w = w_folders[0]
        x_files = collect_sorted_files(x)
        letter = x_index_to_letter(x.name)
        if x_files and letter:
            example_new = build_new_filename(x_files[0], x.name, w.name, letter)
            print(f"\033[93m✏️  Rename example:\033[0m")
            print(f"   {x_files[0].name}")
            print(f"   → {example_new}")
            print()


def run_copy(w_folders, x_folders):
    """
    Main copy loop.
    For each x folder × each w folder: copy files positionally, renaming suffix.
    Returns (copied, skipped, errors) counts.
    """
    copied = 0
    skipped = 0
    errors = 0
    error_log = []

    total_ops = len(x_folders) * len(w_folders)
    op = 0

    for x_folder in x_folders:
        x_name = x_folder.name          # e.g. x01
        letter = x_index_to_letter(x_name)

        if letter is None:
            print(f"\033[93m⚠️  Could not map {x_name} to a letter — skipping this x folder.\033[0m")
            continue

        x_files = collect_sorted_files(x_folder)
        if not x_files:
            print(f"\033[93m⚠️  {x_name} is empty — skipping.\033[0m")
            continue

        for w_folder in w_folders:
            op += 1
            w_name = w_folder.name      # e.g. w00

            # Validate matching file count
            w_files = collect_sorted_files(w_folder)
            if len(w_files) != len(x_files):
                msg = (f"{x_name} has {len(x_files)} file(s) but {w_name} has "
                       f"{len(w_files)} — counts don't match, skipping this pair.")
                print(f"\033[93m⚠️  {msg}\033[0m")
                error_log.append(msg)
                errors += len(x_files)
                continue

            sys.stdout.write(
                f"\r\033[93mCopying\033[0m {x_name} → {w_name}  "
                f"({op}/{total_ops} folder pairs)..."
            )
            sys.stdout.flush()

            for x_file in x_files:
                new_name = build_new_filename(x_file, x_name, w_name, letter)
                dest = w_folder / new_name

                if dest.exists():
                    skipped += 1
                    continue

                try:
                    shutil.copy2(str(x_file), str(dest))
                    copied += 1
                except Exception as e:
                    msg = f"Error copying {x_file.name} → {w_name}/{new_name}: {e}"
                    error_log.append(msg)
                    errors += 1

    # Clear progress line
    sys.stdout.write("\r" + " " * 70 + "\r")
    sys.stdout.flush()

    return copied, skipped, errors, error_log


def main():
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mX-to-W Folder Broadcaster\033[0m")
        print("Copy x## files into w## folders with suffix rename")
        print("\033[92m==================================================\033[0m")
        print()

        base_path = djj.get_path_input("📁 Enter base folder path")
        print()

        w_folders, x_folders = scan_base_folder(base_path)

        if not w_folders:
            print("❌ \033[93mNo w## folders found in that path.\033[0m")
            action = djj.what_next()
            if action == 'exit':
                break
            continue

        if not x_folders:
            print("❌ \033[93mNo x## folders found in that path.\033[0m")
            action = djj.what_next()
            if action == 'exit':
                break
            continue

        preview(base_path, w_folders, x_folders)

        confirm = djj.prompt_choice(
            "\033[93mProceed with copy?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='1'
        )
        print()

        if confirm != '1':
            print("\033[93mCancelled.\033[0m")
            action = djj.what_next()
            if action == 'exit':
                break
            continue

        copied, skipped, errors, error_log = run_copy(w_folders, x_folders)

        # ── Summary ───────────────────────────────────────────────────────
        print()
        print("\033[93mSummary\033[0m")
        print("-------")
        print(f"✅ \033[92mCopied:\033[0m  {copied}")
        if skipped:
            print(f"⏭️  \033[93mSkipped (already existed):\033[0m {skipped}")
        if errors:
            print(f"❌ \033[93mErrors:\033[0m  {errors}")
            for msg in error_log[:5]:
                print(f"   • {msg}")
            if len(error_log) > 5:
                print(f"   ... and {len(error_log) - 5} more")
        print()

        djj.prompt_open_folder(base_path)

        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()
