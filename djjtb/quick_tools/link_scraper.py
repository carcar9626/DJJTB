#!/usr/bin/env python3
"""
Enhanced Link Scraper Tool for DJJTB
Updated: Sep 30, 2025

Features:
- Fixed multiple keyword support (comma-separated)
- Link Generator with numerical substitution
- Advanced link scraping with rate limiting
- Browser automation with Selenium (optional)
- Auto-scroll and delay options
- Multi-domain support
- Export to organized folder structure
- Default slink.txt option
- Random wait times (5-15 seconds) and batch sizes (25-40)
- Elapsed time tracking
- CSV export with source tracking
"""

import os
import sys
import time
import random
import requests
import pathlib
import re
import csv
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import djjtb.utils as djj

# Optional Selenium imports (only load if needed)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

os.system('clear')

def create_output_directories(base_path="/Users/home/Documents/Scripts/DJJTB_output/link_scraper"):
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

def get_title_from_soup(soup, fallback_url):
    """Extract page title from an already-parsed soup object."""
    title = soup.find('title')
    if title and title.string:
        return title.string.strip()
    return fallback_url

def parse_keywords(keyword_input):
    """Parse comma-separated keywords and return list"""
    if not keyword_input:
        return []
    
    # Split by comma and clean each keyword
    keywords = [k.strip() for k in keyword_input.split(',')]
    # Remove empty keywords
    keywords = [k for k in keywords if k]
    
    return keywords

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

def get_links_with_keywords_requests(url, keywords):
    """
    Scrape links from a website that contain ANY of the keywords using requests.
    Single fetch — extracts both the links and the page title from one response
    instead of hitting the site twice.
    Returns: (matching_links: list, page_title: str)
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        page_title = get_title_from_soup(soup, url)

        matching_links = []
        all_links = soup.find_all("a", href=True)

        for a in all_links:
            href = a["href"]
            for keyword in keywords:
                if keyword in href:
                    absolute_url = urljoin(url, href)
                    matching_links.append(absolute_url)
                    break

        return matching_links, page_title
    except requests.exceptions.RequestException as e:
        print(f"\033[93mError fetching {url}: {e}\033[0m")
        return [], url

def perform_login(driver, login_config):
    """Perform login using provided configuration"""
    try:
        login_url = login_config.get('login_url')
        username = login_config.get('username')
        password = login_config.get('password')
        username_selector = login_config.get('username_selector', 'input[type="email"], input[name="username"], input[name="email"]')
        password_selector = login_config.get('password_selector', 'input[type="password"], input[name="password"]')
        submit_selector = login_config.get('submit_selector', 'button[type="submit"], input[type="submit"]')
        post_login_wait = login_config.get('post_login_wait', 5)
        
        print(f"\033[93m  🔑 Logging in to {login_url}...\033[0m")
        
        # Navigate to login page
        driver.get(login_url)
        time.sleep(3)
        
        # Wait for and fill username field
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, username_selector))
        )
        username_field.clear()
        username_field.send_keys(username)
        
        # Fill password field
        password_field = driver.find_element(By.CSS_SELECTOR, password_selector)
        password_field.clear()
        password_field.send_keys(password)
        
        # Submit form
        submit_button = driver.find_element(By.CSS_SELECTOR, submit_selector)
        submit_button.click()
        
        # Wait for login to complete
        time.sleep(post_login_wait)
        
        # Check if login was successful (basic check - could be improved)
        if "login" not in driver.current_url.lower() and "sign" not in driver.current_url.lower():
            print(f"\033[92m  ✓ Login appears successful\033[0m")
            return True
        else:
            print(f"\033[93m  ⚠️  Login may have failed (still on login page)\033[0m")
            return False
            
    except Exception as e:
        print(f"\033[93m  ❌ Login failed: {e}\033[0m")
        return False

def get_links_with_keywords_selenium(url, keywords, use_scroll=True, scroll_delay=2, page_wait=3, login_config=None):
    """
    Scrape links using Selenium with optional scrolling, delays, and login.
    Returns: (matching_links: list, page_title: str)
    """
    if not SELENIUM_AVAILABLE:
        print("\033[93m⚠️  Selenium not available. Install with: pip install selenium\033[0m")
        return [], url
    
    options = Options()
    options.add_argument('--headless')  # Run in background
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('--log-level=3')
        
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        
        # Perform login if configured
        if login_config:
            login_success = perform_login(driver, login_config)
            if not login_success:
                print(f"\033[93m  ⚠️  Continuing without login...\033[0m")
        
        # Navigate to target URL
        driver.get(url)
        
        # Wait for page to load
        time.sleep(page_wait)
        
        if use_scroll:
            # Auto-scroll to load dynamic content
            print(f"\033[93m  🔄 Auto-scrolling with {scroll_delay}s delays...\033[0m")
            scroll_attempts = 0
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            while scroll_attempts < 10:  # Max 10 scroll attempts
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_delay)
                
                # Check if new content loaded
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                    
                last_height = new_height
                scroll_attempts += 1
            
            print(f"\033[92m  ✓ Completed {scroll_attempts} scroll attempts\033[0m")
        
        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        page_title = get_title_from_soup(soup, url)
        
        # Extract all links that contain any of the keywords
        matching_links = []
        all_links = soup.find_all("a", href=True)
        
        for a in all_links:
            href = a["href"]
            # Check if any keyword is in the href
            for keyword in keywords:
                if keyword in href:
                    # Convert relative URLs to absolute URLs
                    absolute_url = urljoin(url, href)
                    matching_links.append(absolute_url)
                    break  # Found a match, no need to check other keywords for this link
        
        return matching_links, page_title
        
    except Exception as e:
        print(f"\033[93mError with Selenium scraping {url}: {e}\033[0m")
        return [], url
    finally:
        if driver:
            driver.quit()

def scrape_links_from_list(websites, keywords, use_selenium=False, use_scroll=True,
                          scroll_delay=2, page_wait=3, login_config=None, output_filepath=None):
    """
    Scrape links from a list of websites with multiple keyword support,
    within-session de-duplication, and live streaming writes to disk.

    Dedup: exact-string match against everything found so far in this run.
    Streaming: each new unique link is appended + flushed to output_filepath
    immediately, so an interrupted run doesn't lose progress.

    Returns: (all_filtered_links: list[str], results_by_source: list[dict])
    """
    results_by_source = []
    all_filtered_links = []
    seen = set()
    duplicate_count = 0
    processed_count = 0

    keywords_str = ", ".join(f"'{k}'" for k in keywords)
    print(f"\033[93mScraping {len(websites)} websites for keywords: {keywords_str}\033[0m")

    if use_selenium:
        if not SELENIUM_AVAILABLE:
            print("\033[93m⚠️  Selenium not available, falling back to requests method\033[0m")
            use_selenium = False
        else:
            selenium_info = f"Using Selenium with scroll={'ON' if use_scroll else 'OFF'}, delays={scroll_delay}s"
            if login_config:
                selenium_info += f", login=ON"
            print(f"\033[93m{selenium_info}\033[0m")

    if output_filepath:
        print(f"\033[96mℹ️  Streaming results to:\033[0m {output_filepath}")

    print("\033[92m" + "="*50 + "\033[0m")

    # Random batch size for this session
    rate_limit_threshold = random.randint(25, 40)
    print(f"\033[96mℹ️  Using batch size: {rate_limit_threshold} sites\033[0m")

    # Open output file once, append mode — created fresh by resolve_scraped_output_path
    # so this always starts empty. Kept open for the whole loop; flushed per-write.
    out_file = open(output_filepath, 'a', encoding='utf-8') if output_filepath else None

    try:
        for i, site in enumerate(websites, 1):
            print(f"\033[93m[{i}/{len(websites)}] Processing:\033[0m {site}")

            if use_selenium:
                links, page_title = get_links_with_keywords_selenium(
                    site, keywords, use_scroll, scroll_delay, page_wait, login_config
                )
            else:
                links, page_title = get_links_with_keywords_requests(site, keywords)

            # Dedup against everything seen so far this session
            new_links = []
            for link in links:
                if link in seen:
                    duplicate_count += 1
                else:
                    seen.add(link)
                    new_links.append(link)

            if new_links:
                all_filtered_links.extend(new_links)

                if out_file:
                    for link in new_links:
                        out_file.write(link + "\n")
                    out_file.flush()  # disk write is microseconds vs the request's hundreds of ms — negligible cost, big safety win

                dupe_note = f" ({len(links) - len(new_links)} dupe(s) skipped)" if len(links) != len(new_links) else ""
                print(f"\033[92m  ✅ Found {len(new_links)} new link(s)\033[0m{dupe_note}")

                results_by_source.append({
                    'source_title': page_title,
                    'source_url': site,
                    'keywords': keywords_str,
                    'links': new_links,
                    'link_count': len(new_links)
                })
            elif links:
                duplicate_count += len(links)
                print(f"\033[93m  ⚠️  {len(links)} link(s) found, all duplicates — skipped\033[0m")
            else:
                print(f"\033[93m  ⚠️  No links found\033[0m")

            processed_count += 1

            # Rate limiting with random wait time and random batch size
            if processed_count >= rate_limit_threshold and i < len(websites):
                random_pause = random.randint(5, 15)  # Random between 5-15 seconds
                print(f"\033[93m  ⏸️  Pausing for {random_pause}s (processed {rate_limit_threshold} sites)\033[0m")
                time.sleep(random_pause)
                processed_count = 0
                # Set new random batch size for next round
                rate_limit_threshold = random.randint(25, 40)
                print(f"\033[96mℹ️  Next batch size: {rate_limit_threshold} sites\033[0m")
            elif i < len(websites) and not use_selenium:
                time.sleep(0.5)  # Small delay between requests (Selenium has built-in delays)
    finally:
        if out_file:
            out_file.close()

    print("\033[92m" + "="*50 + "\033[0m")
    print(f"\033[92m✅ Scraping complete! Found {len(all_filtered_links)} unique link(s)\033[0m", end="")
    if duplicate_count:
        print(f" \033[93m({duplicate_count} duplicate(s) skipped)\033[0m")
    else:
        print()
    return all_filtered_links, results_by_source

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

def resolve_scraped_output_path(domain_name, base_output_path):
    """
    Determine the output txt filepath up front (before scraping starts),
    so scrape_links_from_list can open it immediately and write as it goes.
    """
    domain_folder = os.path.join(base_output_path, domain_name)
    scraper_folder = os.path.join(domain_folder, "Scraper")
    os.makedirs(scraper_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%b%d")
    time_suffix = datetime.now().strftime("%H%M%S")
    filename = f"{timestamp}_{domain_name}.txt"
    filepath = os.path.join(scraper_folder, filename)

    # Avoid clobbering an existing file from earlier today
    if os.path.exists(filepath):
        base, ext = os.path.splitext(filepath)
        filepath = f"{base}_{time_suffix}{ext}"

    return filepath

def export_scraped_csv(results_by_source, domain_name, base_output_path):
    """Export scraped results to CSV with source tracking"""
    if not results_by_source:
        return None
    
    domain_folder = os.path.join(base_output_path, domain_name)
    scraper_folder = os.path.join(domain_folder, "Scraper")
    os.makedirs(scraper_folder, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%b%d_%H%M%S")
    filename = f"{timestamp}_{domain_name}_detailed.csv"
    filepath = os.path.join(scraper_folder, filename)
    
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['source_title', 'source_url', 'search_terms', 'scraped_link']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            for result in results_by_source:
                for link in result['links']:
                    writer.writerow({
                        'source_title': result['source_title'],
                        'source_url': result['source_url'],
                        'search_terms': result['keywords'],
                        'scraped_link': link
                    })
        
        print(f"\033[92m✅ Detailed CSV saved to: {filepath}\033[0m")
        return filepath
    except Exception as e:
        print(f"\033[93m⚠️  Error saving CSV: {e}\033[0m")
        return None

def link_generation_workflow():
    """Handle the link generation workflow"""
    start_time = time.time()
    
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
    
    elapsed_time = time.time() - start_time
    print(f"\033[96m⏱️  Link generation completed in {elapsed_time:.2f} seconds\033[0m")
    
    return generated_links, exported_file

def setup_login_config():
    """Setup login configuration interactively"""
    print("\033[92m" + "="*40 + "\033[0m")
    print("\033[1;33m🔑 LOGIN CONFIGURATION\033[0m")
    print("\033[92m" + "="*40 + "\033[0m")
    
    login_url = input("\033[93mLogin page URL:\n\033[0m > ").strip()
    if not login_url:
        return None
    
    username = input("\033[93mUsername/Email:\n\033[0m > ").strip()
    if not username:
        return None
    
    import getpass
    password = getpass.getpass("\033[93mPassword (hidden): \033[0m")
    if not password:
        return None
    
    print("\033[96mAdvanced options (press Enter for defaults):\033[0m")
    
    # Username field selector
    username_selector = input("\033[96mUsername field CSS selector [default: auto-detect]:\n\033[0m > ").strip()
    if not username_selector:
        username_selector = 'input[type="email"], input[name="username"], input[name="email"], input[id*="user"], input[id*="email"]'
    
    # Password field selector
    password_selector = input("\033[96mPassword field CSS selector [default: auto-detect]:\n\033[0m > ").strip()
    if not password_selector:
        password_selector = 'input[type="password"], input[name="password"], input[id*="pass"]'
    
    # Submit button selector
    submit_selector = input("\033[96mSubmit button CSS selector [default: auto-detect]:\n\033[0m > ").strip()
    if not submit_selector:
        submit_selector = 'button[type="submit"], input[type="submit"], button:contains("Log"), button:contains("Sign")'
    
    # Post-login wait time
    wait_input = input("\033[96mWait time after login (seconds) [default: 5]:\n\033[0m > ").strip()
    try:
        post_login_wait = int(wait_input) if wait_input else 5
    except ValueError:
        post_login_wait = 5
    
    config = {
        'login_url': login_url,
        'username': username,
        'password': password,
        'username_selector': username_selector,
        'password_selector': password_selector,
        'submit_selector': submit_selector,
        'post_login_wait': post_login_wait
    }
    
    print(f"\033[92m✓ Login configured for: {login_url}\033[0m")
    return config

def scraping_workflow(use_generated_links=False, generated_links=None):
    """Handle the link scraping workflow"""
    start_time = time.time()
    
    print("\033[92m" + "="*60 + "\033[0m")
    print("\033[1;33m🌐 LINK SCRAPING\033[0m")
    print("\033[92m" + "="*60 + "\033[0m")
    
    websites = []
    
    if use_generated_links and generated_links:
        websites = generated_links
        print(f"\033[92m✓ Using {len(websites)} previously generated links\033[0m")
    else:
        # Get links from user
        link_source = djj.prompt_choice(
            "\033[93mHow do you want to provide links?\033[0m\n1. Import from text file\n2. Enter custom links\n3. Use default slink.txt",
            ['1', '2', '3'],
            default='3'
        )
        
        if link_source == '1':
            # Import from file
            file_path = djj.get_path_input("Enter path to text file containing links")
            websites = load_links_from_file(file_path)
        elif link_source == '2':
            # Custom links (rare due to terminal limits)
            print("\033[93mEnter links (space-separated, or one per line - press Enter twice when done):\033[0m")
            links_input = []
            while True:
                line = input(" > ").strip()
                if not line:
                    break
                links_input.extend(line.split())
            websites = [link.strip() for link in links_input if link.strip()]
        elif link_source == '3':
            # Use default slink.txt file
            default_path = "/Users/home/Documents/Scripts/DJJTB_output/slink.txt"
            websites = load_links_from_file(default_path)
    
    if not websites:
        print("\033[93m⚠️  No websites to scrape\033[0m")
        return None, None
    
    print(f"\033[92m✓ Ready to scrape {len(websites)} websites\033[0m")
    
    # Get keyword parameter with examples
    print("\033[93mEnter keywords to filter links (comma-separated):\033[0m")
    print("\033[96mExamples: .jpg, .png, .webp")
    print("         /photos/, /images/")
    print("         .mp3, .mp4, .pdf\033[0m")
    keyword_input = input(" > ").strip()
    
    if not keyword_input:
        print("\033[93m⚠️  No keywords provided\033[0m")
        return None, None
    
    # Parse keywords
    keywords = parse_keywords(keyword_input)
    if not keywords:
        print("\033[93m⚠️  No valid keywords found\033[0m")
        return None, None
    
    print(f"\033[92m✓ Parsed {len(keywords)} keywords:\033[0m {', '.join(repr(k) for k in keywords)}")
    
    # Scraping method choice
    use_selenium = False
    use_scroll = True
    scroll_delay = 2
    page_wait = 3
    login_config = None
    
    if SELENIUM_AVAILABLE:
        scraping_method = djj.prompt_choice(
            "\033[93mChoose scraping method:\033[0m\n1. Standard (requests) - faster\n2. Browser automation (Selenium) - handles dynamic content",
            ['1', '2'],
            default='1'
        )
        
        if scraping_method == '2':
            use_selenium = True
            
            # Login option
            login_choice = djj.prompt_choice(
                "\033[93mDo you need to login to access the content?\033[0m\n1. No login required\n2. Setup login credentials",
                ['1', '2'],
                default='1'
            )
            
            if login_choice == '2':
                login_config = setup_login_config()
                if not login_config:
                    print("\033[93m⚠️  Login setup cancelled. Continuing without login.\033[0m")
            
            # Selenium options
            scroll_choice = djj.prompt_choice(
                "\033[93mEnable auto-scrolling for dynamic content?\033[0m\n1. Yes (recommended)\n2. No",
                ['1', '2'],
                default='1'
            )
            use_scroll = (scroll_choice == '1')
            
            if use_scroll:
                scroll_delay = djj.get_int_input("Scroll delay in seconds", min_val=1, max_val=30) or 2
                
            page_wait = djj.get_int_input("Page load wait time in seconds", min_val=1, max_val=30) or 3
            
            config_str = f"scroll={use_scroll}, delays={scroll_delay}s, wait={page_wait}s"
            if login_config:
                config_str += f", login=ON"
            print(f"\033[92m✓ Selenium config:\033[0m {config_str}")
    else:
        print("\033[96mℹ️  Selenium not available. Using standard requests method.\033[0m")
        print("\033[96m   To enable browser automation: pip install selenium\033[0m")
    
    # Resolve the output path BEFORE scraping starts, so links can stream to disk live
    base_output_path = create_output_directories()
    domain_name = get_domain_name(websites[0]) if websites else "multi_domain"

    # Handle multi-domain case
    unique_domains = set(get_domain_name(url) for url in websites[:5])  # Check first 5
    if len(unique_domains) > 1:
        domain_name = "multi_domain"

    txt_file = resolve_scraped_output_path(domain_name, base_output_path)

    # Scrape links — streams to txt_file live, link by link, with within-session dedup
    scraped_links, results_by_source = scrape_links_from_list(
        websites, keywords, use_selenium, use_scroll,
        scroll_delay, page_wait, login_config=login_config,
        output_filepath=txt_file
    )

    if not scraped_links:
        print("\033[93m⚠️  No links found with the specified keywords\033[0m")
        elapsed_time = time.time() - start_time
        print(f"\033[96m⏱️  Scraping completed in {elapsed_time:.2f} seconds\033[0m")
        # Nothing was written — remove the empty file so we don't leave clutter
        try:
            if os.path.exists(txt_file) and os.path.getsize(txt_file) == 0:
                os.remove(txt_file)
        except OSError:
            pass
        return None, None

    print(f"\033[92m✅ Scraped links saved to: {txt_file}\033[0m")

    # CSV is a summary artifact (per-source breakdown) — fine to write once at the end
    csv_file = export_scraped_csv(results_by_source, domain_name, base_output_path)

    elapsed_time = time.time() - start_time
    print(f"\033[96m⏱️  Scraping completed in {elapsed_time:.2f} seconds\033[0m")

    return txt_file, csv_file

def main():
    """Main function with enhanced workflow"""
    session_start_time = time.time()
    
    while True:
        print()
        print("\033[92m" + "="*50 + "\033[0m")
        print("\033[1;93m🔗 ENHANCED LINK SCRAPER TOOL 🌐\033[0m")
        print("\033[92m" + "="*50 + "\033[0m")
        if SELENIUM_AVAILABLE:
            print("\033[92m✅ Browser automation available\033[0m")
        else:
            print("\033[96mℹ️  Browser automation disabled (pip install selenium to enable)\033[0m")
        print()
        
        # Main workflow choice
        workflow_choice = djj.prompt_choice(
            "\033[93mChoose workflow:\033[0m\n1. Link Creation + Scraping\n2. Scraping Only",
            ['1', '2'],
            default='2'
        )
        
        print()
        
        generated_links = None
        generated_file = None
        scraped_txt_file = None
        scraped_csv_file = None
        
        if workflow_choice == '1':
            # Link Creation + Scraping
            generated_links, generated_file = link_generation_workflow()
            
            if generated_links:
                print()
                use_generated = djj.prompt_choice(
                    "\033[93mUse the generated links for scraping?\033[0m\n1. Yes\n2. No",
                    ['1', '2'],
                    default='1'
                )
                
                print()
                if use_generated == '1':
                    scraped_txt_file, scraped_csv_file = scraping_workflow(True, generated_links)
                else:
                    scraped_txt_file, scraped_csv_file = scraping_workflow(False)
            else:
                print("\033[93m⚠️  Link generation failed. Skipping scraping.\033[0m")
                
        else:
            # Scraping Only
            scraped_txt_file, scraped_csv_file = scraping_workflow(False)
        
        # Summary
        print()
        print("\033[92m" + "="*50 + "\033[0m")
        print("\033[1;33m📊 SESSION SUMMARY\033[0m")
        print("\033[92m" + "="*50 + "\033[0m")
        
        total_links_scraped = 0
        if generated_file:
            print(f"🔗 Generated links: {generated_file}")
        if scraped_txt_file:
            # Count scraped links
            try:
                with open(scraped_txt_file, 'r') as f:
                    total_links_scraped = len([line for line in f if line.strip()])
            except:
                total_links_scraped = 0
            
            print(f"🌐 Scraped links (TXT): {scraped_txt_file}")
            if scraped_csv_file:
                print(f"📊 Scraped links (CSV): {scraped_csv_file}")
            print(f"📈 Total links scraped: {total_links_scraped}")
            
            # Open output folder
            folder_to_open = os.path.dirname(scraped_txt_file)
            djj.prompt_open_folder(folder_to_open)
        elif generated_file:
            folder_to_open = os.path.dirname(generated_file)
            djj.prompt_open_folder(folder_to_open)
        
        # Session elapsed time
        session_elapsed_time = time.time() - session_start_time
        minutes = int(session_elapsed_time // 60)
        seconds = session_elapsed_time % 60
        if minutes > 0:
            print(f"\033[96m⏱️  Total session time: {minutes}m {seconds:.1f}s\033[0m")
        else:
            print(f"\033[96m⏱️  Total session time: {seconds:.2f} seconds\033[0m")
        print()
        
        # Custom What Next with scraper option
        action = scraper_what_next(scraped_txt_file, generated_links)
        if action == 'exit':
            break
        elif action == 'continue':
            continue
        elif action == 'scraper_generated':
            # Jump directly to scraping workflow with previous generated links
            print()
            scraping_workflow(True, generated_links)
            continue
        elif action == 'scraper_scraped':
            # Load scraped links and use them for scraping
            print()
            if scraped_txt_file:
                scraped_links = load_links_from_file(scraped_txt_file)
                if scraped_links:
                    scraping_workflow(True, scraped_links)
                else:
                    print("\033[93m⚠️  Could not load scraped links.\033[0m")
                    time.sleep(2)
            continue

def scraper_what_next(last_scraped_file=None, last_generated_links=None):
    """Custom what_next for link scraper with scraper-only option"""
    print()
    print("---------------")
    print()
    
    # Build options based on what's available
    options = ['1', '2', '3', '4', '5']
    prompt_text = "\033[93mWhat Next? 🤷🏻‍♂️ \033[0m\n1. Go Again 🔁\n"
    
    if last_generated_links:
        prompt_text += "2. Send generated links to scraper 🔗\n"
    else:
        prompt_text += "2. Send generated links to scraper 🔗 (none available)\n"
    
    if last_scraped_file:
        prompt_text += "3. Send scraped links to scraper 🌐\n"
    else:
        prompt_text += "3. Send scraped links to scraper 🌐 (none available)\n"
        
    prompt_text += "4. Return to DJJTB ⏮️\n5. Exit ✋🏼\n> "
    
    choice = djj.prompt_choice(prompt_text, options, default='4')
    
    if choice == '5':
        print("👋 Exiting.")
        return 'exit'
    elif choice == '4':
        return_to_djjtb()
        return 'exit'
    elif choice == '3':
        if last_scraped_file:
            return 'scraper_scraped'
        else:
            print("\033[93m⚠️  No scraped links available. Returning to main menu.\033[0m")
            time.sleep(1)
            return 'continue'
    elif choice == '2':
        if last_generated_links:
            return 'scraper_generated'
        else:
            print("\033[93m⚠️  No generated links available. Returning to main menu.\033[0m")
            time.sleep(1)
            return 'continue'
    else:  # choice == '1'
        os.system('clear')
        return 'continue'

def return_to_djjtb():
    """Switch back to DJJTB tab (Command+1) - extracted from utils"""
    import subprocess
    subprocess.run([
        "osascript", "-e",
        'tell application "Terminal" to tell application "System Events" to keystroke "1" using command down'
    ])

if __name__ == "__main__":
    main()