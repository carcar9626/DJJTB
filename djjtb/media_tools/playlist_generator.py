#!/usr/bin/env python3
import os
import sys
import pathlib
import subprocess
from pathlib import Path
from datetime import datetime
import djjtb.utils as djj

os.system('clear')
MEDIA_EXTENSIONS = ('.mp4', '.mov', '.webm', '.mkv', '.mp3', '.aac', '.flac', '.wav', '.m4a')

def collect_media_files(input_path):
    input_path = Path(input_path)
    if input_path.is_file():
        return [str(input_path)] if input_path.suffix.lower() in MEDIA_EXTENSIONS else []
    elif input_path.is_dir():
        media_files = []
        for root, _, files in os.walk(input_path):
            for file in sorted(files):
                if file.lower().endswith(MEDIA_EXTENSIONS):
                    media_files.append(os.path.join(root, file))
        return media_files
    return []

def display_media_list(media_files):
    """Display numbered list of media files with filename + extension only"""
    print(f"\n\033[92mFound {len(media_files)} media file(s):\033[0m")
    for i, file_path in enumerate(media_files, 1):
        filename = Path(file_path).name
        print(f"{i}. {filename}")
    print()

def write_playlist(media_paths, destination_path):
    with open(destination_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for path in media_paths:
            # Get just the filename without extension for display
            filename = Path(path).stem  # filename without extension
            # Convert path to file:// URL format
            file_url = Path(path).as_uri()
            # Write EXTINF tag with filename as title, then the file URL
            f.write(f"#EXTINF:-1,{filename}\n")
            f.write(f"{file_url}\n")

def get_playlist_path(custom_name=None):
    """Generate playlist path with optional custom name"""
    # Ask if user wants to save to default path or choose custom
    use_default = djj.prompt_choice(
        "\033[93mSave to default path?\033[0m\n1. Yes (~/Desktop/Playlists)\n2. No (choose custom path)",
        ['1', '2'],
        default='1'
    )
    
    if use_default == '1':
        # Default path
        output_dir = Path.home() / "Desktop" / "Playlists"
    else:
        # Custom path
        custom_path_str = djj.get_path_input("Enter output folder path")
        output_dir = Path(custom_path_str)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    now = datetime.now()
    date_str = now.strftime("%Y%b%d")  # e.g., 2025Jul21
    
    if custom_name:
        # Custom name format: date_customname.m3u8
        base_filename = f"{date_str}_{custom_name}.m3u8"
    else:
        # Default format: date_playlist.m3u8
        base_filename = f"{date_str}_playlist.m3u8"
    
    playlist_path = output_dir / base_filename
    
    # If file exists, add timestamp to make it unique
    if playlist_path.exists():
        timestamp = now.strftime("%H%M%S")  # HHMMSS format
        if custom_name:
            filename_with_timestamp = f"{date_str}_{timestamp}_{custom_name}.m3u8"
        else:
            filename_with_timestamp = f"{date_str}_{timestamp}_playlist.m3u8"
        playlist_path = output_dir / filename_with_timestamp
    
    return playlist_path

def generate_playlist():
    os.system('clear')
    print()
    print("\033[92m===================================\033[0m")
    print("         \033[1;33mPlaylist Generator\033[0m")
    print("       Create M3U8 Playlists")
    print("\033[92m===================================\033[0m")
    print()
    
    media_files = djj.get_media_input("📁 Enter folder or media file path(s)", extensions=MEDIA_EXTENSIONS)
    print()
    
    if not media_files:
        print("\n\033[93m⚠️  No supported media files found.\033[0m\n")
        return
    
    # Display the found media files
    display_media_list(media_files)
    
    # Confirmation prompt before generation
    confirm = djj.prompt_choice(
        "\033[93mProceed with playlist generation?\033[0m\n1. Yes\n2. No ",
        ['1', '2'], default='1'
    )
    
    if confirm != '1':
        print("\n\033[93mCancelled.\033[0m")
        return
    
    print()
    
    # Ask if user wants to give the playlist a custom name
    name_choice = djj.prompt_choice(
        "\033[93mGive the playlist a custom name?\033[0m\n1. Yes\n2. No ",
        ['1', '2'],
        default='2'
    )
    
    custom_name = None
    if name_choice == '1':
        custom_name = djj.get_string_input("\033[93mEnter playlist name\033[0m")
    
    print()
    
    # Get playlist path (with custom name if provided)
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