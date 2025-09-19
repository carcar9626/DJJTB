from datetime import datetime
import os
import time
import csv
import pyperclip
import djjtb.utils as djj

# Define base paths
data_path = "/Users/home/Documents/Scripts/DJJTB_output/path_grabber"
csv_path = os.path.join(data_path, "csv")
txt_path = os.path.join(data_path, "txt")

# Create folders if missing
os.makedirs(csv_path, exist_ok=True)
os.makedirs(txt_path, exist_ok=True)

# Store already captured paths to avoid duplication
captured_paths = set()

def get_today_filenames():
    today_str = datetime.now().strftime("%Y%b%d")
    return (
        os.path.join(csv_path, f"{today_str}_Paths.csv"),
        os.path.join(txt_path, f"{today_str}_Paths.txt")
    )

def get_path_info(path_str):
    """Extract path information"""
    try:
        clean_path = path_str.strip().strip('\'"').replace('\\ ', ' ')
        full_path = os.path.expanduser(clean_path)
        full_path = os.path.abspath(full_path)
        if os.path.exists(full_path):
            filename = os.path.basename(full_path)
            parent_dir = os.path.dirname(full_path)
            return {'full_path': full_path, 'filename': filename, 'parent': parent_dir, 'exists': True}
        else:
            return {'full_path': clean_path, 'filename': os.path.basename(clean_path), 'parent': os.path.dirname(clean_path), 'exists': False}
    except Exception as e:
        return {'full_path': path_str, 'filename': 'error', 'parent': 'error', 'exists': False, 'error': str(e)}

def is_valid_path(text):
    """Check if text contains valid file paths"""
    text = str(text or "").strip()
    valid_path_starts = [
        '/Users/', '/Applications/', '/System/', '/Library/', '/Volumes/',
        '~/Documents/', '~/Desktop/', '~/Downloads/', '~/', '/'
    ]
    lines = text.split('\n')
    for line in lines:
        line = line.strip().strip('\'"')
        if line and any(line.startswith(start) for start in valid_path_starts):
            return True
    return False

def extract_paths_from_text(text):
    """Extract potential file paths from clipboard text"""
    text = str(text or "").strip()
    paths = []
    lines = text.split('\n')
    valid_path_starts = [
        '/Users/', '/Applications/', '/System/', '/Library/', '/Volumes/',
        '~/Documents/', '~/Desktop/', '~/Downloads/', '~/', '/'
    ]
    for line in lines:
        line = line.strip().strip('\'"')
        if not line:
            continue
        is_valid_line = False
        for start in valid_path_starts:
            if line.startswith(start):
                if start == '/' and len(line) > 1:
                    is_valid_line = True
                    break
                elif start != '/' and len(line) > len(start) + 2:
                    is_valid_line = True
                    break
        if is_valid_line and not line.startswith('.') and len(line) > 5:
            paths.append(line)
    return paths

def log_path(path_str):
    if path_str in captured_paths:
        return
    captured_paths.add(path_str)
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    path_info = get_path_info(path_str)
    csv_file, txt_file = get_today_filenames()
    status = "✅" if path_info['exists'] else "❌"
    print(f"🆕 {status} Caught: {path_info['filename']} | {path_info['full_path']}")
    with open(csv_file, "a", newline='', encoding="utf-8") as f_csv:
        writer = csv.writer(f_csv)
        writer.writerow([path_info['full_path'], date_str, time_str])
    with open(txt_file, "a", encoding="utf-8") as f_txt:
        f_txt.write(path_info['full_path'] + "\n")

def main():
    os.system('clear')
    print("📁 PathGrabber is running... (press Ctrl+C to stop)")
    last_clipboard = ""
    while True:
        try:
            clipboard = pyperclip.paste()
            if not isinstance(clipboard, str):
                clipboard = str(clipboard or "")
            clipboard = clipboard.strip()
            
            if clipboard and clipboard != last_clipboard:
                last_clipboard = clipboard
                if is_valid_path(clipboard):
                    paths = extract_paths_from_text(clipboard)
                    for path in paths:
                        log_path(path)
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 PathGrabber stopped.")
            break

if __name__ == "__main__":
    main()