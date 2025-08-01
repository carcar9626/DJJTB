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
        for root, _, files in os.walk(input_path):  # Fixed the typo here
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

def get_unique_playlist_path():
    """Generate a unique playlist path with date and timestamp if needed"""
    # Create the output directory - FIXED: Convert string to Path object
    output_dir = Path("/Users/home/Desktop/Playlists")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate base filename with current date
    now = datetime.now()
    date_str = now.strftime("%Y%b%d")  # e.g., 2025Jul21
    base_filename = f"{date_str}_playlist.m3u8"
    
    playlist_path = output_dir / base_filename
    
    # If file exists, add timestamp to make it unique
    if playlist_path.exists():
        timestamp = now.strftime("%H%M%S")  # HHMMSS format
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
        print("\n\033[33m⚠️  No supported media files found.\033[0m\n")
        return
    
    # Display the found media files
    display_media_list(media_files)
    
    # Confirmation prompt before generation
    confirm = djj.prompt_choice(
        "\033[33mProceed with playlist generation?\033[0m\n1. Yes\n2. No ",
        ['1', '2'], default='1'
    )
    
    if confirm != '1':
        print("\n\033[33mCancelled.\033[0m")
        return
    
    # Get unique playlist path (no overwriting, silent timestamp addition)
    playlist_path = get_unique_playlist_path()
    
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