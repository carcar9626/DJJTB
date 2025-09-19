#!/usr/bin/env python3

import os
import pathlib
import shutil
import subprocess
import sqlite3
from datetime import datetime
import csv
import djjtb.utils as djj

SUPPORTED_EXTS = (".jpg", ".jpeg", ".png", ".webp")
VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv")
os.system('clear')

def safe_filename(name):
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in name.strip().lower())

def open_folder_mac(folder_path):
    subprocess.run(["open", str(folder_path)], check=False)

def search_tags_in_db(db_path, search_term, confidence_threshold):
    matches = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT i.file_path, t.confidence_score
            FROM images i
            JOIN tags t ON i.id = t.image_id
            WHERE t.tag_name LIKE ?
            AND t.confidence_score >= ?
            ORDER BY t.confidence_score DESC
        ''', (f'%{search_term}%', confidence_threshold))
        results = cursor.fetchall()
        matches = [(pathlib.Path(row[0]), row[1]) for row in results]
        conn.close()
    except Exception as e:
        print(f"\n\033[91m❌ DB Error:\033[0m {e}\n")
    return matches

def search_tags_in_xmp(folder_path, search_term, include_subfolders=True):
    import xml.etree.ElementTree as ET
    folder_path = pathlib.Path(folder_path)
    xmp_files = folder_path.rglob("*.xmp") if include_subfolders else folder_path.glob("*.xmp")
    matches = []
    terms = [t.strip().lower() for t in search_term.split(',')]

    for xmp_file in xmp_files:
        # Skip XMPs for videos
        if any(xmp_file.name.lower().endswith(ext + ".xmp") for ext in VIDEO_EXTS):
            continue

        try:
            tree = ET.parse(xmp_file)
            root = tree.getroot()
            text = ET.tostring(root, encoding='utf-8', method='text').decode('utf-8').lower()
            if any(term in text for term in terms):
                for ext in SUPPORTED_EXTS:
                    candidate = xmp_file.with_suffix(ext)
                    if candidate.exists():
                        matches.append(candidate)
                        break
        except Exception as e:
            print(f"⚠️ Failed to read {xmp_file.name}: {e}")
    return matches

def xmp_only_mode(input_path_obj, include_sub):
    print("\n\033[93mXMP-only mode activated. Searching sidecar files only...\033[0m\n")
    search_input = input("\033[93m🔍 Enter tag(s) to search (comma-separated for multiple):\n -> \033[0m").strip()
    if not search_input:
        print("\033[93m❌ No tag entered.\033[0m\n")
        return
    search_terms = [t.strip() for t in search_input.split(',') if t.strip()]

    use_and = False
    if len(search_terms) > 1:
        and_or_choice = djj.prompt_choice(
            "\033[93mMultiple terms detected. Use AND or OR search?\033[0m\n1. AND (all terms must match)\n2. OR (any term matches)",
            ['1', '2'],
            default='2'
        )
        use_and = and_or_choice == '1'

    all_matches = None if use_and else set()
    term_matches_dict = {}

    for term in search_terms:
        term_matches = {m for m in search_tags_in_xmp(input_path_obj, term, include_sub)
                        if m.suffix.lower() in SUPPORTED_EXTS}
        if use_and:
            if all_matches is None:
                all_matches = term_matches
            else:
                all_matches &= term_matches
        else:
            term_matches_dict[term] = term_matches
            if all_matches is None:
                all_matches = set()
            all_matches.update(term_matches)

    if not all_matches:
        print(f"\n\033[91m⚠️ No matching results found.\033[0m\n")
        return

    matched_paths = sorted(all_matches)
    print(f"\n✅ Found \033[92m{len(matched_paths)}\033[0m image(s) matching your search.\n")

    base_output_dir = input_path_obj / "Output" / "image_finder_results"
    base_output_dir.mkdir(parents=True, exist_ok=True)

    # Output choice: subfolder or CSV
    output_choice = djj.prompt_choice(
        "\033[93mOutput results as:\033[0m\n1. Subfolder(s)\n2. CSV",
        ['1', '2'],
        default='1'
    )

    if output_choice == '1':
        if use_and:
            safe_term = safe_filename("_".join(search_terms))
            output_dir = base_output_dir / safe_term
            if output_dir.exists():
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                output_dir = base_output_dir / f"{safe_term}_{timestamp}"
            output_dir.mkdir(parents=True, exist_ok=True)
            for src in matched_paths:
                if include_sub and not src.is_file():
                    continue
                if not include_sub and src.parent != input_path_obj:
                    continue
                dest = output_dir / src.name
                try:
                    shutil.copy2(src, dest)
                except Exception as e:
                    print(f"\033[93m⚠️ Failed to copy\033[0m {src.name}: {e}")
            open_folder_mac(output_dir)
        else:  # OR mode
            for term, term_matches in term_matches_dict.items():
                if not term_matches:
                    continue
                term_safe = safe_filename(term)
                term_dir = base_output_dir / term_safe
                term_dir.mkdir(parents=True, exist_ok=True)
                for src in term_matches:
                    if include_sub and not src.is_file():
                        continue
                    if not include_sub and src.parent != input_path_obj:
                        continue
                    dest = term_dir / src.name
                    try:
                        shutil.copy2(src, dest)
                    except Exception as e:
                        print(f"\033[93m⚠️ Failed to copy\033[0m {src.name}: {e}")
                open_folder_mac(term_dir)
    else:  # CSV output
        csv_file = base_output_dir / f"image_finder_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['filename', 'absolute_path'])
            for src in matched_paths:
                writer.writerow([src.name, str(src.resolve())])
        print(f"\n✅ CSV saved: {csv_file}")

    djj.prompt_open_folder(base_output_dir)

def main():
    while True:
        print("\n\n\033[92m==================================================\033[0m")
        print("\033[1;33mImage Finder\033[0m")
        print("Search Images with Tags from JoyTag or CLIP")
        print("\033[92m==================================================\033[0m\n")

        input_path = input("\033[93m📁 Enter folder path:\n -> \033[0m").strip()
        input_path_obj = pathlib.Path(input_path).resolve()
        if not input_path_obj.exists():
            print(f"\033[93m❌ Error: \033[0m'{input_path}' \033[93mnot found.\033[0m\n")
            continue

        # Ask if XMP-only mode
        xmp_only = djj.prompt_choice(
            "\033[93mDo you want XMP-only mode (skip DB)?\033[0m\n1. Yes\n2. No",
            ['1','2'], default='2'
        ) == '1'

        include_sub = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes, 2. No",
            ['1', '2'],
            default='2'
        ) == '1'

        if xmp_only:
            xmp_only_mode(input_path_obj, include_sub)
            continue

        # Regular DB + optional XMP
        db_path = input("\033[93m🧠 Enter full path to JoyTag or CLIP .db file:\n -> \033[0m").strip()
        db_path = pathlib.Path(db_path).resolve()
        if not db_path.exists():
            print(f"\033[93m❌ DB not found at:\033[0m {db_path}\n")
            continue

        use_xmp = djj.prompt_choice(
            "\033[93mRead XMP sidecar files too?\033[0m\n1. Yes, 2. No",
            ['1', '2'],
            default='2'
        ) == '1'

        while True:
            search_input = input("\033[93m🔍 Enter tag(s) to search (comma-separated for multiple):\n -> \033[0m").strip()
            if not search_input:
                print("\033[93m❌ No tag entered.\033[0m\n")
                continue

            threshold_input = input("\033[93m🎯 Confidence threshold [0.1–1.0, default 0.5]:\n -> \033[0m").strip()
            try:
                confidence_threshold = float(threshold_input) if threshold_input else 0.5
                confidence_threshold = max(0.1, min(1.0, confidence_threshold))
            except:
                confidence_threshold = 0.5

            search_terms = [t.strip() for t in search_input.split(',') if t.strip()]

            use_and = False
            if len(search_terms) > 1:
                and_or_choice = djj.prompt_choice(
                    "\033[93mMultiple terms detected. Use AND or OR search?\033[0m\n1. AND (all terms must match)\n2. OR (any term matches)",
                    ['1', '2'],
                    default='2'
                )
                use_and = and_or_choice == '1'

            all_matches = None if use_and else set()
            term_matches_dict = {}

            for term in search_terms:
                matches = search_tags_in_db(db_path, term, confidence_threshold)
                term_matches = {m[0] for m in matches if m[0].suffix.lower() in SUPPORTED_EXTS}

                if use_xmp:
                    xmp_matches = search_tags_in_xmp(input_path_obj, term, include_sub)
                    term_matches.update(m for m in xmp_matches if m.suffix.lower() in SUPPORTED_EXTS)

                if use_and:
                    if all_matches is None:
                        all_matches = term_matches
                    else:
                        all_matches &= term_matches
                else:
                    term_matches_dict[term] = term_matches
                    if all_matches is None:
                        all_matches = set()
                    all_matches.update(term_matches)

            if not all_matches:
                print(f"\n\033[91m⚠️ No matching results found.\033[0m\n")
                break

            matched_paths = sorted(all_matches)
            print(f"\n✅ Found \033[92m{len(matched_paths)}\033[0m image(s) matching your search.\n")

            base_output_dir = input_path_obj / "Output" / "image_finder_results"
            base_output_dir.mkdir(parents=True, exist_ok=True)

            # Output choice: subfolder or CSV
            output_choice = djj.prompt_choice(
                "\033[93mOutput results as:\033[0m\n1. Subfolder(s)\n2. CSV",
                ['1', '2'],
                default='1'
            )

            if output_choice == '1':
                if use_and:
                    safe_term = safe_filename("_".join(search_terms))
                    output_dir = base_output_dir / safe_term
                    if output_dir.exists():
                        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                        output_dir = base_output_dir / f"{safe_term}_{timestamp}"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    for src in matched_paths:
                        if include_sub and not src.is_file():
                            continue
                        if not include_sub and src.parent != input_path_obj:
                            continue
                        dest = output_dir / src.name
                        try:
                            shutil.copy2(src, dest)
                        except Exception as e:
                            print(f"\033[93m⚠️ Failed to copy\033[0m {src.name}: {e}")
                    open_folder_mac(output_dir)
                else:  # OR mode
                    for term, term_matches in term_matches_dict.items():
                        if not term_matches:
                            continue
                        term_safe = safe_filename(term)
                        term_dir = base_output_dir / term_safe
                        term_dir.mkdir(parents=True, exist_ok=True)
                        for src in term_matches:
                            if include_sub and not src.is_file():
                                continue
                            if not include_sub and src.parent != input_path_obj:
                                continue
                            dest = term_dir / src.name
                            try:
                                shutil.copy2(src, dest)
                            except Exception as e:
                                print(f"\033[93m⚠️ Failed to copy\033[0m {src.name}: {e}")
                        open_folder_mac(term_dir)
            else:  # CSV output
                csv_file = base_output_dir / f"image_finder_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                with open(csv_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['filename', 'absolute_path'])
                    for src in matched_paths:
                        writer.writerow([src.name, str(src.resolve())])
                print(f"\n✅ CSV saved: {csv_file}")
            
            djj.prompt_open_folder(base_output_dir)
                        # Inline custom what_next with 4 options
            print()
            print("---------------")
            print()
            print("\033[93mWhat Next? 🤷🏻‍♂️ \033[0m")
            print("1. Go Again (search term)")
            print("2. Return to DJJTB")
            print("3. Exit")
            print("4. Restart from folder selection")
            action = input("> ").strip()

            if action == '1':
                os.system('clear')
                continue  # Go again (search term)
            elif action == '2':
                djj.return_to_djjtb()
                return
            elif action == '3':
                print("👋 Exiting Image Finder.")
                return
            elif action == '4':
                break  # Restart from folder selection
            else:
                print("⚠️ Invalid choice, going back to search term input.\n")
                continue
if __name__ == "__main__":
    main()