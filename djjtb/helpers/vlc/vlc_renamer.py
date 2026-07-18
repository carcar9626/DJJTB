import os
import time
import shutil
import subprocess
import psutil
from pathlib import Path

SNAPSHOT_DIR = Path("/Users/home/Desktop/VLCSnaps")
SNAPSHOT_PREFIX = "vlcsnap"

def is_vlc_running():
    """Check if VLC is currently running"""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'vlc' in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def get_video_filepath():
    """Use AppleScript to get the full file path of the current VLC video"""
    try:
        result = subprocess.check_output([
            "osascript",
            "-e", 'tell application "VLC" to path of current item'
        ], stderr=subprocess.DEVNULL)
        
        mac_path = result.decode("utf-8").strip()
        # Convert HFS path to POSIX using AppleScript
        result = subprocess.check_output([
            "osascript",
            "-e", f'set p to POSIX path of "{mac_path}"'
        ], stderr=subprocess.DEVNULL)
        return Path(result.decode("utf-8").strip())
    except subprocess.CalledProcessError:
        return None

def get_next_filename(base_name, ext, dest_folder):
    i = 1
    while True:
        candidate = dest_folder / f"{base_name}_{i:03d}{ext}"
        if not candidate.exists():
            return candidate
        i += 1

def wait_for_vlc():
    """Wait until VLC starts running"""
    print("🔍 Waiting for VLC to start...")
    while not is_vlc_running():
        time.sleep(2)
    print("🎬 VLC detected! Starting screenshot monitoring...")

def monitor_screenshots():
    """Monitor and rename screenshots while VLC is running"""
    seen = set(SNAPSHOT_DIR.glob(f"{SNAPSHOT_PREFIX}*"))
    
    while is_vlc_running():
        current = set(SNAPSHOT_DIR.glob(f"{SNAPSHOT_PREFIX}*"))
        new_files = current - seen
        
        for file in sorted(new_files):
            video_path = get_video_filepath()
            if not video_path or not video_path.exists():
                print("⚠️  Could not fetch current video path from VLC.")
                continue
            
            base_name = video_path.stem  # e.g., "MyVideo"
            dest_folder = video_path.parent
            target_path = get_next_filename(base_name, file.suffix, dest_folder)
            
            try:
                shutil.move(str(file), str(target_path))
                print(f"✅ Moved & Renamed: {file.name} → {target_path}")
            except Exception as e:
                print(f"❌ Failed to move {file.name}: {e}")
        
        seen = current
        time.sleep(0.5)
    
    print("🛑 VLC closed. Stopping screenshot monitoring...")

def main():
    print("📸 VLC Auto Screenshot Renamer + Mover")
    
    while True:
        wait_for_vlc()
        monitor_screenshots()
        print("💤 Waiting for VLC to restart...")
        time.sleep(3)  # Brief pause before checking again

if __name__ == "__main__":
    main()