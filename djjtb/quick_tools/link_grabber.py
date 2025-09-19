from datetime import datetime
import os
import re
import time
import csv
import pyperclip
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Define base paths
data_path = "/Users/home/Documents/Scripts/DJJTB_output/link_grabber"
csv_path = os.path.join(data_path, "csv")
txt_path = os.path.join(data_path, "txt")

# Create folders if missing
os.makedirs(csv_path, exist_ok=True)
os.makedirs(txt_path, exist_ok=True)

# Regex to detect URLs and extract extension
url_pattern = re.compile(r"(https?|ftp|magnet):\/\/[^\s]+", re.IGNORECASE)
extension_pattern = re.compile(r"\.([a-zA-Z0-9]{1,6})(?:\?|$)")

# Store already captured links to avoid duplication
captured_links = set()

def get_today_filenames():
    today_str = datetime.now().strftime("%Y%b%d")
    return (
        os.path.join(csv_path, f"{today_str}_Links.csv"),
        os.path.join(txt_path, f"{today_str}_Links.txt")
    )

def extract_extension(url):
    match = extension_pattern.search(url)
    return match.group(1).lower() if match else ""

def get_page_title(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        return soup.title.string.strip() if soup.title and soup.title.string else "No Title"
    except:
        return "No Title"

def get_domain(url):
    try:
        return urlparse(url).netloc
    except:
        return "unknown"

def log_link(url):
    if url in captured_links:
        return
    
    captured_links.add(url)
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    ext = extract_extension(url)
    title = get_page_title(url)
    csv_file, txt_file = get_today_filenames()
    domain = get_domain(url)
    
    # Print to Terminal
    print(f"🆕 Caught: {domain} | {url}")
    
    # Write CSV
    with open(csv_file, "a", newline='', encoding="utf-8") as f_csv:
        writer = csv.writer(f_csv)
        writer.writerow([title, domain, url, date_str, time_str, ext])
    
    # Write TXT
    with open(txt_file, "a", encoding="utf-8") as f_txt:
        f_txt.write(url + "\n")

def main():
    # Clear screen before starting
    os.system('clear')  # Use 'cls' on Windows
    print()
    last_clipboard = ""
    print("📋 LinkGrabber is running... (press Ctrl+C to stop)")
    
    while True:
        try:
            clipboard = pyperclip.paste()
            if not isinstance(clipboard, str):
                clipboard = str(clipboard or "")
            clipboard = clipboard.strip()
            
            if clipboard and clipboard != last_clipboard:
                last_clipboard = clipboard
                # Find all URLs in clipboard text
                url_matches = url_pattern.finditer(clipboard)
                for match in url_matches:
                    log_link(match.group(0))
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 LinkGrabber stopped.")
            break

if __name__ == "__main__":
    main()