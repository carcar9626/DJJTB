#!/usr/bin/env python3
"""
Advanced Link Scrapper Tool for DJJTB
Updated: Sep 16, 2025

Features:
- Link Generator with numerical substitution
- Advanced link scrapping with rate limiting
- Multi-domain support
- Export to organized folder structure
"""

import os
import sys
import time
import requests
import pathlib
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import djjtb.utils as djj

os.system('clear')

def create_output_directories(base_path="/Users/home/Documents/Scripts/DJJTB_output/Link_Scrapper"):
    """Create the output directory structure"""
    os.makedirs(base_path, exist_ok=True)
    return base_path

def get_domain_name(url):
    """Extract domain name from URL for folder naming"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. and common prefixes
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain.replace('.', '_')
    except:
        return "unknown_domain"

def generate_links(base_url, start_val, end_val, step, padding):
    """Generate links by substituting (*) with numbered values"""
    if '(*)' not in base_url:
        print("\033[93m⚠️  Warning: No (*) placeholder found in URL\033[0m")
        return []
    
    generated_links = []
    current = start_val
    
    print(f"\033[93mGenerating links from {start_val} to {end_val} (step: {step}, padding: {padding})\033[0m")
    
    # Check if we should add the unpadded "1" URL first
    if start_val == 2:
        add_unpadded = djj.prompt_choice(
            "\033[93mStarting at 2 - also include unpadded '1' URL?\033[0m\n(Some sites use 'pic' instead of '01pic')\n1. Yes, add unpadded\n2. No, skip it",
            ['1', '2'],
            default='1'
        )
        
        if add_unpadded == '1':
            # Create the unpadded version by removing (*) entirely or replacing with empty
            unpadded_url = base_url.replace('(*)', '')
            generated_links.append(unpadded_url)
            print(f"\033[92m✓ Added unpadded URL:\033[0m {unpadded_url}")
    
    while current <= end_val:
        # Format with padding (zero-fill)
        formatted_num = str(current).zfill(padding)
        generated_url = base_url.replace('(*)', formatted_num)
        generated_links.append(generated_url)
        current += step
    
    print(f"\033[92m✅ Generated {len(generated_links)} links total\033[0m")
    return generated_links

def export_generated_links(links, domain_name, base_output_path):
    """Export generated links to text file"""
    if not links:
        return None
    
    domain_folder = os.path.join(base_output_path, domain_name)
    generator_folder = os.path.join(domain_folder, "Generator")
    os.makedirs(generator_folder, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%b%d_%H%M%S")
    filename = f"{timestamp}_{domain_name}_generated.txt"
    filepath = os.path.join(generator_folder, filename)
    
    try:
        with open(filepath, 'w') as file:
            for link in links:
                file.write(link + "\n")
        
        print(f"\033[92m✅ Generated links saved to: {filepath}\033[0m")
        return filepath
    except Exception as e:
        print(f"\033[93m⚠️  Error saving generated links: {e}\033[0m")
        return None

def get_links_with_keyword(url, keyword):
    """Scrape links from a website that contain the keyword - based on your original code"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract all links that contain the keyword
        links = [a["href"] for a in soup.find_all("a", href=True) if keyword in a["href"]]
        return links
    except requests.exceptions.RequestException as e:
        print(f"\033[93mError fetching {url}: {e}\033[0m")
        return []

def scrape_links_from_list(websites, keyword, rate_limit_threshold=40, pause_duration=6):
    """Scrape links from a list of websites with rate limiting"""
    all_filtered_links = []
    processed_count = 0
    
    print(f"\033[93mScrapping {len(websites)} websites for keyword: '{keyword}'\033[0m")
    print("\033[92m" + "="*50 + "\033[0m")
    
    for i, site in enumerate(websites, 1):
        print(f"\033[93m[{i}/{len(websites)}] Processing:\033[0m {site}")
        
        links = get_links_with_keyword(site, keyword)
        
        if links:
            all_filtered_links.extend(links)
            print(f"\033[92m  ✅ Found {len(links)} links\033[0m")
        else:
            print(f"\033[93m  ⚠️  No links found\033[0m")
        
        processed_count += 1
        
        # Rate limiting
        if processed_count >= rate_limit_threshold and i < len(websites):
            print(f"\033[93m  ⏸️  Pausing for {pause_duration}s (processed {rate_limit_threshold} sites)\033[0m")
            time.sleep(pause_duration)
            processed_count = 0
        elif i < len(websites):
            time.sleep(0.5)  # Small delay between requests
    
    print("\033[92m" + "="*50 + "\033[0m")
    print(f"\033[92m✅ Scrapping complete! Found {len(all_filtered_links)} total links\033[0m")
    return all_filtered_links

def load_links_from_file(filepath):
    """Load links from a text file (one link per line)"""
    try:
        with open(filepath, 'r') as file:
            links = [line.strip() for line in file if line.strip()]
        print(f"\033[92m✅ Loaded {len(links)} links from file\033[0m")
        return links
    except Exception as e:
        print(f"\033[93m⚠️  Error loading file: {e}\033[0m")
        return []

def export_scrapped_links(links, domain_name, base_output_path):
    """Export scrapped links to text file"""
    if not links:
        return None
    
    domain_folder = os.path.join(base_output_path, domain_name)
    scrapper_folder = os.path.join(domain_folder, "Scrapper")
    os.makedirs(scrapper_folder, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%b%d")
    time_suffix = datetime.now().strftime("%H%M%S")
    filename = f"{timestamp}_{domain_name}.txt"
    filepath = os.path.join(scrapper_folder, filename)
    
    # Check for duplicates and add time if needed
    counter = 1
    original_filepath = filepath
    while os.path.exists(filepath):
        base, ext = os.path.splitext(original_filepath)
        filepath = f"{base}_{time_suffix}{ext}"
        counter += 1
        if counter > 10:  # Prevent infinite loop
            break
    
    try:
        with open(filepath, 'w') as file:
            for link in links:
                file.write(link + "\n")
        
        print(f"\033[92m✅ Scrapped links saved to: {filepath}\033[0m")
        return filepath
    except Exception as e:
        print(f"\033[93m⚠️  Error saving scrapped links: {e}\033[0m")
        return None

def link_generation_workflow():
    """Handle the link generation workflow"""
    print("\033[92m" + "="*60 + "\033[0m")
    print("\033[1;33m🔗 LINK GENERATION\033[0m")
    print("\033[92m" + "="*60 + "\033[0m")
    
    # Get base URL with placeholder
    base_url = input("\033[93mEnter the base URL with (*) as placeholder:\n\033[0m > ").strip()
    
    if not base_url or '(*)' not in base_url:
        print("\033[93m⚠️  Invalid URL format. Must contain (*) placeholder.\033[0m")
        return None, None
    
    print(f"\033[92m✓ Base URL:\033[0m {base_url}")
    
    # Get parameters
    start_val = djj.get_int_input("Starting value", min_val=0)
    end_val = djj.get_int_input("Ending value", min_val=start_val)
    step = djj.get_int_input("Step size", min_val=1) or 1
    padding = djj.get_int_input("Minimum padding (zero-fill)", min_val=1) or 1
    
    print(f"\033[92m✓ Parameters:\033[0m Start={start_val}, End={end_val}, Step={step}, Padding={padding}")
    
    # Generate links
    generated_links = generate_links(base_url, start_val, end_val, step, padding)
    
    if not generated_links:
        return None, None
    
    # Preview
    print(f"\033[93mPreview of generated links:\033[0m")
    for i, link in enumerate(generated_links[:3]):
        print(f"  {i+1}. {link}")
    if len(generated_links) > 3:
        print(f"  ... and {len(generated_links)-3} more")
    
    # Export option
    export_choice = djj.prompt_choice(
        "\033[93mExport generated links to text file?\033[0m\n1. Yes\n2. No",
        ['1', '2'],
        default='1'
    )
    
    exported_file = None
    if export_choice == '1':
        base_output_path = create_output_directories()
        domain_name = get_domain_name(base_url)
        exported_file = export_generated_links(generated_links, domain_name, base_output_path)
    
    return generated_links, exported_file

def scrapping_workflow(use_generated_links=False, generated_links=None):
    """Handle the link scrapping workflow"""
    print("\033[92m" + "="*60 + "\033[0m")
    print("\033[1;33m🌐 LINK SCRAPPING\033[0m")
    print("\033[92m" + "="*60 + "\033[0m")
    
    websites = []
    
    if use_generated_links and generated_links:
        websites = generated_links
        print(f"\033[92m✓ Using {len(websites)} previously generated links\033[0m")
    else:
        # Get links from user
        link_source = djj.prompt_choice(
            "\033[93mHow do you want to provide links?\033[0m\n1. Import from text file\n2. Enter custom links",
            ['1', '2'],
            default='1'
        )
        
        if link_source == '1':
            # Import from file
            file_path = djj.get_path_input("Enter path to text file containing links")
            websites = load_links_from_file(file_path)
        else:
            # Custom links (rare due to terminal limits)
            print("\033[93mEnter links (space-separated, or one per line - press Enter twice when done):\033[0m")
            links_input = []
            while True:
                line = input(" > ").strip()
                if not line:
                    break
                links_input.extend(line.split())
            websites = [link.strip() for link in links_input if link.strip()]
    
    if not websites:
        print("\033[93m⚠️  No websites to scrape\033[0m")
        return None
    
    print(f"\033[92m✓ Ready to scrape {len(websites)} websites\033[0m")
    
    # Get keyword parameter
    keyword = input("\033[93mEnter the keyword to filter links (e.g., '/photos/'):\n\033[0m > ").strip()
    
    if not keyword:
        print("\033[93m⚠️  No keyword provided\033[0m")
        return None
    
    print(f"\033[92m✓ Filter keyword:\033[0m {keyword}")
    
    # Scrape links
    scrapped_links = scrape_links_from_list(websites, keyword)
    
    if not scrapped_links:
        print("\033[93m⚠️  No links found with the specified keyword\033[0m")
        return None
    
    # Export results
    base_output_path = create_output_directories()
    domain_name = get_domain_name(websites[0]) if websites else "multi_domain"
    
    # Handle multi-domain case
    unique_domains = set(get_domain_name(url) for url in websites[:5])  # Check first 5
    if len(unique_domains) > 1:
        domain_name = "multi_domain"
    
    exported_file = export_scrapped_links(scrapped_links, domain_name, base_output_path)
    
    return exported_file

def main():
    """Main function with enhanced workflow"""
    while True:
        print()
        print("\033[92m" + "="*50 + "\033[0m")
        print("\033[1;93m🔗 ADVANCED LINK SCRAPPER TOOL 🌐\033[0m")
        print("\033[92m" + "="*50 + "\033[0m")
        print()
        
        # Main workflow choice
        workflow_choice = djj.prompt_choice(
            "\033[93mChoose workflow:\033[0m\n1. Link Creation + Scrapping\n2. Scrapping Only",
            ['1', '2'],
            default='2'
        )
        
        print()
        
        generated_links = None
        generated_file = None
        scrapped_file = None
        
        if workflow_choice == '1':
            # Link Creation + Scrapping
            generated_links, generated_file = link_generation_workflow()
            
            if generated_links:
                print()
                use_generated = djj.prompt_choice(
                    "\033[93mUse the generated links for scrapping?\033[0m\n1. Yes\n2. No",
                    ['1', '2'],
                    default='1'
                )
                
                print()
                if use_generated == '1':
                    scrapped_file = scrapping_workflow(True, generated_links)
                else:
                    scrapped_file = scrapping_workflow(False)
            else:
                print("\033[93m⚠️  Link generation failed. Skipping scrapping.\033[0m")
                
        else:
            # Scrapping Only
            scrapped_file = scrapping_workflow(False)
        
        # Summary
        print()
        print("\033[92m" + "="*50 + "\033[0m")
        print("\033[1;33m📊 SESSION SUMMARY\033[0m")
        print("\033[92m" + "="*50 + "\033[0m")
        
        total_links_scrapped = 0
        if generated_file:
            print(f"🔗 Generated links: {generated_file}")
        if scrapped_file:
            # Count scrapped links
            try:
                with open(scrapped_file, 'r') as f:
                    total_links_scrapped = len([line for line in f if line.strip()])
            except:
                total_links_scrapped = 0
            
            print(f"🌐 Scrapped links: {scrapped_file}")
            print(f"📊 Total links scrapped: {total_links_scrapped}")
            
            # Open output folder
            folder_to_open = os.path.dirname(scrapped_file)
            djj.prompt_open_folder(folder_to_open)
        elif generated_file:
            folder_to_open = os.path.dirname(generated_file)
            djj.prompt_open_folder(folder_to_open)
        
        print()
        
        # Custom What Next with scrapper option
        action = scrapper_what_next(scrapped_file, generated_links)
        if action == 'exit':
            break
        elif action == 'continue':
            continue
        elif action == 'scrapper_generated':
            # Jump directly to scrapping workflow with previous generated links
            print()
            scrapping_workflow(True, generated_links)
            continue
        elif action == 'scrapper_scrapped':
            # Load scrapped links and use them for scrapping
            print()
            if scrapped_file:
                scrapped_links = load_links_from_file(scrapped_file)
                if scrapped_links:
                    scrapping_workflow(True, scrapped_links)
                else:
                    print("\033[93m⚠️  Could not load scrapped links.\033[0m")
                    time.sleep(2)
            continue

def scrapper_what_next(last_scrapped_file=None, last_generated_links=None):
    """Custom what_next for link scrapper with scrapper-only option"""
    print()
    print("---------------")
    print()
    
    # Build options based on what's available
    options = ['1', '2', '3', '4', '5']
    prompt_text = "\033[93mWhat Next? 🤷🏻‍♂️ \033[0m\n1. Go Again 🔁\n"
    
    if last_generated_links:
        prompt_text += "2. Send generated links to scrapper 🔗\n"
    else:
        prompt_text += "2. Send generated links to scrapper 🔗 (none available)\n"
    
    if last_scrapped_file:
        prompt_text += "3. Send scrapped links to scrapper 🌐\n"
    else:
        prompt_text += "3. Send scrapped links to scrapper 🌐 (none available)\n"
        
    prompt_text += "4. Return to DJJTB ⏮️\n5. Exit ✋🏼\n> "
    
    choice = djj.prompt_choice(prompt_text, options, default='4')
    
    if choice == '5':
        print("👋 Exiting.")
        return 'exit'
    elif choice == '4':
        return_to_djjtb()
        return 'exit'
    elif choice == '3':
        if last_scrapped_file:
            return 'scrapper_scrapped'
        else:
            print("\033[93m⚠️  No scrapped links available. Returning to main menu.\033[0m")
            time.sleep(1)
            return 'continue'
    elif choice == '2':
        if last_generated_links:
            return 'scrapper_generated'
        else:
            print("\033[93m⚠️  No generated links available. Returning to main menu.\033[0m")
            time.sleep(1)
            return 'continue'
    else:  # choice == '1'
        os.system('clear')
        return 'continue'

def return_to_djjtb():
    """Switch back to DJJTB tab (Command+1) - extracted from utils"""
    subprocess.run([
        "osascript", "-e",
        'tell application "Terminal" to tell application "System Events" to keystroke "1" using command down'
    ])

if __name__ == "__main__":
    main()