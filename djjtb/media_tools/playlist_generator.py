#!/usr/bin/env python3
import os
import sys
import pathlib
import subprocess
from pathlib import Path
from datetime import datetime
import djjtb.utils as djj

os.system('clear')
MEDIA_EXTENSIONS = ('.mp4', '.mov', '.webm', '.mkv', '.wmv', '.ts', '.avi', '.mpg', 'avi')

def collect_media_files(input_path, include_subfolders=False):
    input_path = Path(input_path)
    if input_path.is_file():
        return [str(input_path)] if input_path.suffix.lower() in MEDIA_EXTENSIONS else []
    elif input_path.is_dir():
        media_files = []
        if include_subfolders:
            for root, _, files in os.walk(input_path):
                for file in sorted(files):
                    if file.lower().endswith(MEDIA_EXTENSIONS):
                        media_files.append(os.path.join(root, file))
        else:
            for file in sorted(os.listdir(input_path)):
                if file.lower().endswith(MEDIA_EXTENSIONS):
                    full_path = os.path.join(input_path, file)
                    if os.path.isfile(full_path):
                        media_files.append(full_path)
        return media_files
    return []


def collect_media_from_txt():
    """Read file paths from a txt file (one path per line). Inline — no utils dependency."""
    txt_path = input("\033[93mEnter path to txt file:\033[0m\n > ").strip().strip('\'"')
    if not txt_path:
        print("\033[93mNo path provided.\033[0m")
        return [], None

    txt_path_obj = Path(txt_path).expanduser().resolve()
    if not txt_path_obj.exists() or not txt_path_obj.is_file():
        print(f"\033[93m❌ File not found: {txt_path}\033[0m")
        return [], None

    media_files = []
    with open(txt_path_obj, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip().strip('\'"')
            if not line or line.startswith('#'):
                continue
            p = Path(line).expanduser().resolve()
            if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS:
                media_files.append(str(p))
            elif p.is_dir():
                media_files.extend(collect_media_files(p, include_subfolders=False))

    return sorted(set(media_files)), None


def display_media_list(media_files):
    print(f"\n\033[92mFound {len(media_files)} media file(s):\033[0m")
    for i, file_path in enumerate(media_files, 1):
        filename = Path(file_path).name
        print(f"{i}. {filename}")
    print()

def write_playlist(media_paths, destination_path):
    with open(destination_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for path in media_paths:
            filename = Path(path).stem
            file_url = Path(path).as_uri()
            f.write(f"#EXTINF:-1,{filename}\n")
            f.write(f"{file_url}\n")

def get_playlist_path(custom_name=None):
    use_default = djj.prompt_choice(
        "\033[93mSave to default path?\033[0m\n1. Yes (~/Desktop/Playlists)\n2. No (choose custom path)",
        ['1', '2'],
        default='1'
    )

    if use_default == '1':
        output_dir = Path.home() / "Desktop" / "Playlists"
    else:
        custom_path_str = djj.get_path_input("Enter output folder path")
        output_dir = Path(custom_path_str)

    output_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    date_str = now.strftime("%Y%m%d")   # 20260501 format

    if custom_name:
        base_filename = f"{date_str}_{custom_name}.m3u8"
    else:
        base_filename = f"{date_str}_playlist.m3u8"

    playlist_path = output_dir / base_filename

    if playlist_path.exists():
        timestamp = now.strftime("%H%M%S")
        stem = f"{date_str}_{timestamp}_{custom_name}" if custom_name else f"{date_str}_{timestamp}_playlist"
        playlist_path = output_dir / f"{stem}.m3u8"

    return playlist_path

def generate_playlist():
    os.system('clear')
    print()
    print("\033[92m==================================================\033[0m")
    print("         \033[1;33mPlaylist Generator\033[0m")
    print("       Create M3U8 Playlists")
    print("\033[92m==================================================\033[0m")
    print()

    # ── Input mode ────────────────────────────────────────────────────────────
    input_mode = djj.prompt_choice(
        "\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n3. Path list from txt file\n",
        ['1', '2', '3'],
        default='1'
    )
    print()

    media_files = []
    default_name_suggestion = None   # carries the smart default for playlist naming

    if input_mode == '1':
        folder_path = djj.get_path_input("Enter folder path")
        print()
        include_sub = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        media_files = collect_media_files(folder_path, include_subfolders=include_sub)
        default_name_suggestion = Path(folder_path).name  # parent folder name

    elif input_mode == '2':
        raw = input("📁 \033[93mEnter file paths (space-separated):\033[0m\n -> ").strip()
        if not raw:
            print("\033[93m⚠️  No paths provided.\033[0m")
            return
        for p_str in raw.split():
            p_str = p_str.strip('\'"')
            p = Path(p_str).expanduser().resolve()
            if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS:
                media_files.append(str(p))
            elif p.is_dir():
                media_files.extend(collect_media_files(p))
        media_files = sorted(set(media_files))
        if media_files:
            default_name_suggestion = Path(media_files[0]).parent.name
        print()

    else:  # txt file
        media_files, _ = collect_media_from_txt()
        if media_files:
            default_name_suggestion = Path(media_files[0]).parent.name
        print()

    if not media_files:
        print("\n\033[93m⚠️  No supported media files found.\033[0m\n")
        return

    display_media_list(media_files)

    confirm = djj.prompt_choice(
        "\033[93mProceed with playlist generation?\033[0m\n1. Yes\n2. No ",
        ['1', '2'], default='1'
    )
    if confirm != '1':
        print("\n\033[93mCancelled.\033[0m")
        return
    print()

    # ── Playlist naming ───────────────────────────────────────────────────────
    # Options: use smart default (parent folder name) OR enter custom
    name_choice = djj.prompt_choice(
        f"\033[93mPlaylist name:\033[0m\n1. Use '{default_name_suggestion}' (from input)\n2. Enter custom name\n3. No custom name (date only)\n",
        ['1', '2', '3'],
        default='1'
    )

    if name_choice == '1':
        custom_name = default_name_suggestion
    elif name_choice == '2':
        custom_name = djj.get_string_input("\033[93mEnter playlist name:\033[0m\n > ")
    else:
        custom_name = None
    print()

    playlist_path = get_playlist_path(custom_name)

    write_playlist(media_files, playlist_path)
    print(f"\n✅ \033[32mPlaylist saved to:\033[0m {playlist_path}")

    djj.prompt_open_folder(playlist_path.parent)

def main():
    while True:
        generate_playlist()
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()
