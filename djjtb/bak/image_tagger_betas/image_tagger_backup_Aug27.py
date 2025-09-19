import os
import sys
import json
import sqlite3
import pathlib
import logging
from datetime import datetime
import djjtb.utils as djj
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
import numpy as np
from typing import List, Dict, Tuple
import csv
import glob

os.system('clear')

# Supported image formats
SUPPORTED_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff")

# Optimized batch size for M2 MBA 8GB RAM
BATCH_SIZE = 30

def setup_logging(output_path, prefix):
    """Set up logging to a file in the output folder."""
    logger = djj.setup_logging(output_path, f"autotagger_{prefix.lower()}")
    return logger

def initialize_clip_model():
    """Initialize CLIP model with online/offline mode selection."""
    
    # Prompt for online/offline mode
    mode_choice = djj.prompt_choice(
        "\033[93mSelect processing mode:\033[0m\n1. Online (download/verify models)\n2. Offline (use cached models only)\n",
        ['1', '2'],
        default='2'
    )
    
    use_offline = mode_choice == '2'
    
    print(f"\033[93mLoading CLIP model ({'offline' if use_offline else 'online'} mode)...\033[0m")
    
    try:
        # Try LAION model first (better for diverse content including artistic)
        model_name = "laion/CLIP-ViT-B-32-laion2B-s34B-b79K"
        if use_offline:
            model = CLIPModel.from_pretrained(model_name, local_files_only=True)
            processor = CLIPProcessor.from_pretrained(model_name, local_files_only=True)
        else:
            model = CLIPModel.from_pretrained(model_name)
            processor = CLIPProcessor.from_pretrained(model_name)
        print(f"\033[32m✅ Loaded model ({'offline' if use_offline else 'online'}):\033[0m {model_name}")
        return model, processor, model_name
    except Exception as e:
        print(f"\033[93mFailed to load LAION model, trying fallback...\033[0m")
        try:
            # Fallback to standard CLIP
            model_name = "openai/clip-vit-base-patch32"
            if use_offline:
                model = CLIPModel.from_pretrained(model_name, local_files_only=True)
                processor = CLIPProcessor.from_pretrained(model_name, local_files_only=True)
            else:
                model = CLIPModel.from_pretrained(model_name)
                processor = CLIPProcessor.from_pretrained(model_name)
            print(f"\033[32m✅ Loaded fallback model ({'offline' if use_offline else 'online'}):\033[0m {model_name}")
            return model, processor, model_name
        except Exception as e2:
            if use_offline:
                print(f"\033[31m❌ No offline models found. Run once with online mode to download.\033[0m")
            else:
                print(f"\033[31m❌ Failed to load any CLIP model:\033[0m {e2}")
            return None, None, None

def get_default_csv_path():
    """Get the default CSV path in a private location."""
    return os.path.expanduser("/Users/home/Documents/Scripts/image_tagger_data/tag_queries.csv")

def get_csv_folder_path():
    """Get the default CSV folder path for folder mode."""
    return os.path.expanduser("/Users/home/Documents/Scripts/image_tagger_data/csv_batches/")

def prompt_processing_mode():
    """Prompt user to choose between single CSV or folder mode."""
    mode_choice = djj.prompt_choice(
        "\033[93mSelect processing mode:\033[0m\n1. Single CSV file (original mode)\n2. Folder mode (process multiple CSVs)\n",
        ['1', '2'],
        default='1'
    )
    
    return mode_choice == '2'  # True for folder mode

def prompt_csv_dataset():
    """Prompt user to choose CSV dataset with your pattern."""
    csv_choice = djj.prompt_choice(
        "\033[93mSelect tag dataset:\033[0m\n1. Optimized dataset (recommended)\n2. Load custom CSV file\n",
        ['1', '2'],
        default='1'
    )
    
    if csv_choice == '1':
        # Use default CSV
        default_csv = get_default_csv_path()
        
        if not os.path.exists(default_csv):
            print(f"\033[93m⚠️  Default CSV not found at:\033[0m {default_csv}")
            print("\033[93mCreating optimized dataset...\033[0m")
            create_optimized_csv(default_csv)
        
        return default_csv
    else:
        # Custom CSV
        csv_path = djj.get_path_input("Enter CSV file path")
        if not csv_path.endswith('.csv'):
            print("\033[93m⚠️  Warning: File doesn't have .csv extension\033[0m")
        return csv_path

def prompt_csv_folder():
    """Prompt user to choose CSV folder for folder mode."""
    folder_choice = djj.prompt_choice(
        "\033[93mSelect CSV folder:\033[0m\n1. Default batch folder\n2. Choose custom folder\n",
        ['1', '2'],
        default='1'
    )
    
    if folder_choice == '1':
        folder_path = get_csv_folder_path()
        
        if not os.path.exists(folder_path):
            print(f"\033[93m⚠️  Default folder not found at:\033[0m {folder_path}")
            choice = djj.prompt_choice(
                "\033[93mCreate default folder structure with examples?\033[0m\n1. Yes, create examples\n2. No, choose different folder\n",
                ['1', '2'],
                default='1'
            )
            
            if choice == '1':
                create_example_csv_batches(folder_path)
            else:
                folder_path = djj.get_path_input("Enter CSV folder path")
        
        return folder_path
    else:
        return djj.get_path_input("Enter CSV folder path")

def create_example_csv_batches(folder_path: str):
    """Create example CSV batch files for demonstration."""
    os.makedirs(folder_path, exist_ok=True)
    
    # Example batch files - each focused on specific categories
    batches = {
        "01_clothing_colors.csv": [
            ["clothing", "red", "person wearing red clothing"],
            ["clothing", "red", "red colored outfit"],
            ["clothing", "blue", "person wearing blue clothing"],
            ["clothing", "blue", "blue colored outfit"],
            ["clothing", "black", "person wearing black clothing"],
            ["clothing", "black", "black colored outfit"],
            ["clothing", "white", "person wearing white clothing"],
            ["clothing", "white", "white colored outfit"],
            ["clothing", "colorful", "person wearing bright colorful clothing"],
            ["clothing", "neutral", "person wearing neutral colored clothing"],
        ],
        
        "02_clothing_types.csv": [
            ["clothing", "dress", "person wearing dress"],
            ["clothing", "dress", "woman in dress"],
            ["clothing", "bikini", "person wearing bikini"],
            ["clothing", "bikini", "woman in bikini"],
            ["clothing", "lingerie", "person wearing lingerie"],
            ["clothing", "casual", "person wearing casual clothing"],
            ["clothing", "formal", "person wearing formal clothing"],
            ["clothing", "minimal", "person wearing very little clothing"],
            ["clothing", "topless", "person not wearing top"],
        ],
        
        "03_poses.csv": [
            ["poses", "standing", "person standing upright"],
            ["poses", "standing", "person standing casually"],
            ["poses", "sitting", "person sitting down"],
            ["poses", "sitting", "person sitting on furniture"],
            ["poses", "lying", "person lying down"],
            ["poses", "lying", "person reclining on bed"],
            ["poses", "kneeling", "person kneeling down"],
            ["poses", "crawling", "person on hands and knees"],
            ["poses", "squatting", "person squatting down"],
        ],
        
        "04_composition.csv": [
            ["composition", "closeup", "close-up portrait"],
            ["composition", "closeup", "face closeup shot"],
            ["composition", "fullbody", "full body shot"],
            ["composition", "fullbody", "whole person visible"],
            ["composition", "upper_body", "upper body or torso shot"],
            ["composition", "upper_body", "waist up portrait"],
        ],
        
        "05_nsfw_detection.csv": [
            ["nsfw", "explicit", "sexually explicit content"],
            ["nsfw", "nude", "nude person"],
            ["nsfw", "topless", "topless person"],
            ["nsfw", "sexual", "sexual activity"],
            ["nsfw", "intimate", "intimate pose or setting"],
            ["nsfw", "suggestive", "suggestive pose or clothing"],
            ["sfw", "safe", "safe for work content"],
            ["sfw", "family", "family friendly image"],
        ]
    }
    
    for filename, data in batches.items():
        csv_path = os.path.join(folder_path, filename)
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['category', 'subcategory', 'query'])  # Header
                writer.writerows(data)
            print(f"\033[32m✅ Created:\033[0m {filename}")
        except Exception as e:
            print(f"\033[31m❌ Error creating {filename}:\033[0m {e}")
    
    print(f"\033[32m✅ Example CSV batches created in:\033[0m {folder_path}")
    print("\033[93mTip:\033[0m Edit these files to customize your tagging categories")

def get_csv_files_from_folder(folder_path: str) -> List[str]:
    """Get all CSV files from folder, sorted by name."""
    csv_pattern = os.path.join(folder_path, "*.csv")
    csv_files = glob.glob(csv_pattern)
    
    if not csv_files:
        print(f"\033[93m⚠️  No CSV files found in:\033[0m {folder_path}")
        return []
    
    # Sort files to ensure consistent processing order
    csv_files.sort()
    
    print(f"\033[32m✅ Found {len(csv_files)} CSV files:\033[0m")
    for i, csv_file in enumerate(csv_files, 1):
        filename = os.path.basename(csv_file)
        print(f"  {i}. {filename}")
    
    return csv_files

def create_optimized_csv(csv_path: str):
    """Create the optimized CSV file focused on pose, clothing, and NSFW detection."""
    
    template_data = [
        # POSES - Core body positions (most important)
        ["poses", "standing", "person standing upright"],
        ["poses", "standing", "person standing casually"],
        ["poses", "sitting", "person sitting down"],
        ["poses", "sitting", "person sitting on furniture"],
        ["poses", "lying", "person lying down"],
        ["poses", "lying", "person reclining on bed"],
        ["poses", "kneeling", "person kneeling down"],
        ["poses", "kneeling", "person on knees"],
        ["poses", "crawling", "person on hands and knees"],
        ["poses", "crawling", "person crawling on all fours"],
        ["poses", "squatting", "person squatting down"],
        ["poses", "squatting", "person crouching"],
        
        # CAMERA INTERACTION - Important for sorting
        ["poses", "camera", "person looking at camera"],
        ["poses", "camera", "person looking away from camera"],
        ["poses", "camera", "person side profile view"],
        
        # CLOTHING COLORS - Simplified to primary colors only
        ["clothing", "red", "person wearing red clothing"],
        ["clothing", "blue", "person wearing blue clothing"],
        ["clothing", "black", "person wearing black clothing"],
        ["clothing", "white", "person wearing white clothing"],
        ["clothing", "colorful", "person wearing bright colorful clothing"],
        ["clothing", "neutral", "person wearing neutral colored clothing"],
        
        # CLOTHING TYPES - Focus on major distinguishable items
        ["clothing", "dress", "person wearing dress"],
        ["clothing", "bikini", "person wearing bikini"],
        ["clothing", "lingerie", "person wearing lingerie"],
        ["clothing", "casual", "person wearing casual clothing"],
        ["clothing", "formal", "person wearing formal clothing"],
        ["clothing", "minimal", "person wearing very little clothing"],
        ["clothing", "topless", "person not wearing top"],
        
        # CLOTHING BOTTOMS - Key distinguishable types
        ["clothing", "pants", "person wearing pants or trousers"],
        ["clothing", "shorts", "person wearing shorts"],
        ["clothing", "skirt", "person wearing skirt"],
        ["clothing", "no_bottom", "person not wearing bottom clothing"],
        
        # ACCESSORIES - Only highly visible items
        ["clothing", "heels", "person wearing high heels"],
        ["clothing", "glasses", "person wearing eyeglasses"],
        ["clothing", "jewelry", "person wearing jewelry"],
        ["clothing", "hat", "person wearing hat"],
        
        # COMPOSITION - Shot types for organization
        ["composition", "closeup", "close-up portrait"],
        ["composition", "fullbody", "full body shot"],
        ["composition", "upper_body", "upper body or torso shot"],
        
        # NSFW DETECTION - Critical for filtering
        ["nsfw", "explicit", "sexually explicit content"],
        ["nsfw", "nude", "nude person"],
        ["nsfw", "topless", "topless person"],
        ["nsfw", "sexual", "sexual activity"],
        ["nsfw", "intimate", "intimate pose or setting"],
        ["nsfw", "suggestive", "suggestive pose or clothing"],
        
        # SFW CONFIRMATION - To distinguish safe content
        ["sfw", "safe", "safe for work content"],
        ["sfw", "family", "family friendly image"],
        ["sfw", "professional", "professional or business appropriate"],
        
        # LOCATION - Basic settings for context
        ["location", "indoor", "indoor setting"],
        ["location", "outdoor", "outdoor setting"],
        ["location", "bedroom", "bedroom interior"],
        ["location", "bathroom", "bathroom setting"],
        ["location", "pool", "pool or poolside"],
        
        # EXPRESSION - Basic emotions
        ["expression", "smiling", "person smiling"],
        ["expression", "serious", "person with serious expression"],
    ]
    
    try:
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['category', 'subcategory', 'query'])  # Header
            writer.writerows(template_data)
        print(f"\033[32m✅ Created optimized CSV:\033[0m {csv_path}")
    except Exception as e:
        print(f"\033[31m❌ Error creating CSV template:\033[0m {e}")

def load_tag_queries_from_csv(csv_path: str) -> Dict:
    """Enhanced CSV loader with support for nested categories."""
    
    if not os.path.exists(csv_path):
        print(f"\033[31m❌ CSV file not found:\033[0m {csv_path}")
        return create_default_tag_queries()
    
    tag_queries = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                category = row['category'].strip() if row['category'] else ""
                subcategory = row['subcategory'].strip() if row['subcategory'] else None
                query = row['query'].strip() if row['query'] else ""
                
                if not query or query.startswith('#'):  # Skip empty queries and comments
                    continue
                
                # Initialize nested structure
                if category not in tag_queries:
                    tag_queries[category] = {}
                if subcategory not in tag_queries[category]:
                    tag_queries[category][subcategory] = []
                
                # Add query to appropriate category/subcategory
                tag_queries[category][subcategory].append(query)
        
        csv_name = os.path.basename(csv_path)
        print(f"\033[32m✅ Loaded tag queries from:\033[0m {csv_name}")
        
        # Show summary
        total_categories = len(tag_queries)
        total_subcategories = sum(len(subcat) for subcat in tag_queries.values())
        total_queries = sum(len(queries) for cat in tag_queries.values() for queries in cat.values())
        
        print(f"  \033[93mLoaded:\033[0m {total_categories} categories, {total_subcategories} subcategories, {total_queries} total queries")
        
    except Exception as e:
        print(f"\033[31m❌ Error loading CSV:\033[0m {e}")
        print("\033[93mUsing default tag queries instead...\033[0m")
        return create_default_tag_queries()
    
    return tag_queries

def create_default_tag_queries():
    """Create default tag queries (fallback)."""
    return {
        'poses': {
            'standing': ["person standing upright", "person standing casually"],
            'sitting': ["person sitting down", "person sitting on furniture"],
            'lying': ["person lying down", "person reclining"],
            'crawling': ["person on hands and knees", "person crawling"],
        },
        'clothing': {
            'red': ["person wearing red clothing"],
            'blue': ["person wearing blue clothing"],
            'black': ["person wearing black clothing"],
            'white': ["person wearing white clothing"],
            'bikini': ["person wearing bikini"],
            'dress': ["person wearing dress"],
        },
        'nsfw': {
            'explicit': ["sexually explicit content"],
            'nude': ["nude person"],
            'topless': ["topless person"],
        },
        'sfw': {
            'safe': ["safe for work content"],
            'family': ["family friendly image"],
        }
    }

def setup_database(db_path):
    """Create SQLite database for storing tags."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables with batch tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            file_name TEXT NOT NULL,
            processed_date TEXT NOT NULL,
            model_used TEXT NOT NULL,
            nsfw_detected INTEGER DEFAULT 0,
            max_nsfw_confidence REAL DEFAULT 0.0,
            batch_count INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER,
            category TEXT NOT NULL,
            subcategory TEXT,
            tag_name TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            is_nsfw INTEGER DEFAULT 0,
            batch_round INTEGER DEFAULT 1,
            csv_source TEXT,
            FOREIGN KEY (image_id) REFERENCES images (id)
        )
    ''')
    
    # Add indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_path ON images(file_path)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tag_image ON tags(image_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tag_category ON tags(category, subcategory)')
    
    conn.commit()
    return conn

def collect_images_from_folder(input_path, include_subfolders=False):
    """Collect images from folder(s) - following your exact pattern."""
    input_path_obj = pathlib.Path(input_path)
    
    images = []
    if input_path_obj.is_dir():
        if include_subfolders:
            for root, _, files in os.walk(input_path):
                images.extend(pathlib.Path(root) / f for f in files if pathlib.Path(f).suffix.lower() in SUPPORTED_EXTS)
        else:
            images = [f for f in input_path_obj.glob('*') if f.suffix.lower() in SUPPORTED_EXTS and f.is_file()]
    
    return sorted([str(v) for v in images], key=str.lower)

def clean_tag_name(query: str, category: str, subcategory: str) -> str:
    """Clean up tag names for DigiKam compatibility - keep it simple."""
    # Remove common prefixes
    cleaned = query.lower()
    
    # Remove "person" prefix
    if cleaned.startswith("person "):
        cleaned = cleaned[7:]
    
    if cleaned.startswith("woman "):
        cleaned = cleaned[6:]
        
    if cleaned.startswith("is "):
        cleaned = cleaned[4:]
        
    if cleaned.startswith("has "):
        cleaned = cleaned[4:]
        
    if cleaned.startswith("clothing "):
        cleaned = cleaned[9:]
    
    if cleaned.startswith("in "):
        cleaned = cleaned[3:]
    
    if cleaned.startswith("on "):
        cleaned = cleaned[3:]
    
    if cleaned.startswith("only "):
        cleaned = cleaned[5:]
    
    # Remove "wearing" for clothing items
    if cleaned.startswith("wearing "):
        cleaned = cleaned[8:]
        
    # Clean up extra spaces and capitalize properly
    cleaned = " ".join(cleaned.split())
    cleaned = cleaned.title()
    
    # Return the cleaned query as the tag name - don't overthink it
    return cleaned

def detect_nsfw_content(tags_data: List[Dict]) -> Tuple[bool, float]:
    """Detect if image contains NSFW content based on tags."""
    nsfw_detected = False
    max_nsfw_confidence = 0.0
    
    for tag in tags_data:
        if tag['category'] == 'nsfw' and tag['confidence'] > 0.6:  # Higher threshold for NSFW
            nsfw_detected = True
            max_nsfw_confidence = max(max_nsfw_confidence, tag['confidence'])
            tag['is_nsfw'] = 1
    
    return nsfw_detected, max_nsfw_confidence

def process_image_batch(image_paths: List[str], model, processor, tag_queries: Dict, confidence_threshold: float, batch_round: int, csv_source: str, logger) -> List[Dict]:
    """Process a batch of images and return tags with NSFW detection."""
    results = []
    
    try:
        # Load images
        images = []
        valid_paths = []
        
        for img_path in image_paths:
            try:
                img = Image.open(img_path).convert('RGB')
                images.append(img)
                valid_paths.append(img_path)
            except Exception as e:
                logger.error(f"Failed to load {img_path}: {e}")
                continue
        
        if not images:
            return results
        
        # Process each category of queries
        for category, subcategories in tag_queries.items():
            # Adjust confidence threshold for NSFW detection
            category_threshold = confidence_threshold
            if category == 'nsfw':
                category_threshold = max(0.6, confidence_threshold)  # Higher threshold for NSFW
            elif category == 'sfw':
                category_threshold = max(0.5, confidence_threshold - 0.05)  # Lower threshold for SFW confirmation
            
            for subcategory, queries in subcategories.items():
                
                # Process all queries for this subcategory
                inputs = processor(
                    text=queries,
                    images=images,
                    return_tensors="pt",
                    padding=True
                )
                
                with torch.no_grad():
                    outputs = model(**inputs)
                    logits_per_image = outputs.logits_per_image
                    probs = logits_per_image.softmax(dim=1)
                
                # Get best matching query for each image
                for img_idx, img_path in enumerate(valid_paths):
                    best_query_idx = probs[img_idx].argmax().item()
                    confidence = probs[img_idx][best_query_idx].item()
                    
                    # Only keep high-confidence tags
                    if confidence > category_threshold:
                        original_query = queries[best_query_idx]
                        tag_name = clean_tag_name(original_query, category, subcategory)
                        
                        # Find or create result entry for this image
                        img_result = next((r for r in results if r['image_path'] == img_path), None)
                        if img_result is None:
                            img_result = {
                                'image_path': img_path,
                                'tags': []
                            }
                            results.append(img_result)
                        
                        # Add tag (avoid duplicates)
                        existing_tag = next((t for t in img_result['tags'] if t['tag_name'] == tag_name), None)
                        if existing_tag is None or confidence > existing_tag['confidence']:
                            if existing_tag:
                                img_result['tags'].remove(existing_tag)
                            
                            img_result['tags'].append({
                                'category': category,
                                'subcategory': subcategory,
                                'tag_name': tag_name,
                                'confidence': confidence,
                                'original_query': original_query,
                                'is_nsfw': 1 if category == 'nsfw' else 0,
                                'batch_round': batch_round,
                                'csv_source': csv_source
                            })
        
        # Clear memory
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
            
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
    
    return results

def save_results_to_db(results: List[Dict], conn, model_name: str, batch_round: int, logger):
    """Save tagging results to database with batch tracking."""
    cursor = conn.cursor()
    
    for result in results:
        img_path = result['image_path']
        img_name = pathlib.Path(img_path).name
        
        # Detect NSFW content
        nsfw_detected, max_nsfw_confidence = detect_nsfw_content(result['tags'])
        
        try:
            # Check if image already exists
            cursor.execute('SELECT id, batch_count FROM images WHERE file_path = ?', (img_path,))
            existing = cursor.fetchone()
            
            if existing:
                image_id, current_batch_count = existing
                # Update existing image record
                cursor.execute('''
                    UPDATE images
                    SET processed_date = ?, batch_count = ?,
                        nsfw_detected = CASE WHEN ? = 1 OR nsfw_detected = 1 THEN 1 ELSE 0 END,
                        max_nsfw_confidence = CASE WHEN ? > max_nsfw_confidence THEN ? ELSE max_nsfw_confidence END
                    WHERE id = ?
                ''', (datetime.now().isoformat(), current_batch_count + 1,
                      1 if nsfw_detected else 0, max_nsfw_confidence, max_nsfw_confidence, image_id))
            else:
                # Insert new image record
                cursor.execute('''
                    INSERT INTO images
                    (file_path, file_name, processed_date, model_used, nsfw_detected, max_nsfw_confidence, batch_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (img_path, img_name, datetime.now().isoformat(), model_name,
                      1 if nsfw_detected else 0, max_nsfw_confidence, 1))
                image_id = cursor.lastrowid
            
            # Insert new tags for this batch round (don't delete existing ones)
            for tag in result['tags']:
                cursor.execute('''
                    INSERT INTO tags (image_id, category, subcategory, tag_name, confidence_score, is_nsfw, batch_round, csv_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (image_id, tag['category'], tag['subcategory'], tag['tag_name'],
                      tag['confidence'], tag.get('is_nsfw', 0), tag['batch_round'], tag['csv_source']))
            
            # Log NSFW detection
            if nsfw_detected:
                logger.info(f"NSFW detected (Round {batch_round}): {img_name} (confidence: {max_nsfw_confidence:.3f})")
            
        except Exception as e:
            logger.error(f"Database error for {img_path}: {e}")
    
    conn.commit()

def read_existing_xmp_tags(xmp_path):
    """Read existing tags from XMP file if it exists."""
    if not os.path.exists(xmp_path):
        return []
    
    try:
        with open(xmp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple regex to extract rdf:li tags
        import re
        tags = re.findall(r'<rdf:li>(.*?)</rdf:li>', content)
        return [tag.strip() for tag in tags if tag.strip()]
    except Exception:
        return []

def export_xmp_sidecar_files(db_path: str, merge_mode: bool, include_nsfw: bool, logger):
    """Export XMP sidecar files with proper DigiKam tag structure (merged from all batches)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all images and their tags with optional NSFW filtering, merged across all batch rounds
    if include_nsfw:
        cursor.execute('''
            SELECT i.file_path, i.file_name, t.category, t.subcategory, t.tag_name,
                   MAX(t.confidence_score) as max_confidence, i.nsfw_detected, i.batch_count
            FROM images i
            LEFT JOIN tags t ON i.id = t.image_id
            WHERE t.tag_name IS NOT NULL
            GROUP BY i.file_path, t.category, t.subcategory, t.tag_name
            ORDER BY i.file_path, max_confidence DESC
        ''')
    else:
        cursor.execute('''
            SELECT i.file_path, i.file_name, t.category, t.subcategory, t.tag_name,
                   MAX(t.confidence_score) as max_confidence, i.nsfw_detected, i.batch_count
            FROM images i
            LEFT JOIN tags t ON i.id = t.image_id
            WHERE t.tag_name IS NOT NULL AND i.nsfw_detected = 0
            GROUP BY i.file_path, t.category, t.subcategory, t.tag_name
            ORDER BY i.file_path, max_confidence DESC
        ''')
    
    results = cursor.fetchall()
    images_dict = {}
    nsfw_count = 0
    
    # Group tags by image
    for file_path, file_name, category, subcategory, tag_name, confidence, nsfw_detected, batch_count in results:
        if file_path not in images_dict:
            images_dict[file_path] = {
                'tags': [],
                'nsfw_detected': nsfw_detected,
                'batch_count': batch_count
            }
        
        # Create DigiKam hierarchical tag without commas
        if subcategory:
            digikam_tag = f"{category.title()}/{subcategory.replace('_', ' ').title()}/{tag_name}"
        else:
            digikam_tag = f"{category.title()}/{tag_name}"
        
        # Avoid duplicates
        if digikam_tag not in images_dict[file_path]['tags']:
            images_dict[file_path]['tags'].append(digikam_tag)
        
        if nsfw_detected:
            nsfw_count += 1
    
    xmp_files_created = 0
    
    for file_path, data in images_dict.items():
        tags = data['tags']
        nsfw_detected = data['nsfw_detected']
        batch_count = data['batch_count']
        
        if tags:
            xmp_path = f"{file_path}.xmp"
            
            # Handle merge mode
            if merge_mode:
                existing_tags = read_existing_xmp_tags(xmp_path)
                # Combine and deduplicate
                all_tags = list(set(existing_tags + tags))
            else:
                all_tags = tags
            
            # Add batch processing info and NSFW warning tag if detected
            if batch_count > 1:
                all_tags.append(f"Processing/Batch Count {batch_count}")
            
            if nsfw_detected and include_nsfw:
                all_tags.append("NSFW/Detected")
            
            # Create XMP content with proper DigiKam structure
            xmp_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/">
      <dc:subject>
        <rdf:Bag>
{chr(10).join(f'          <rdf:li>{tag}</rdf:li>' for tag in sorted(all_tags))}
        </rdf:Bag>
      </dc:subject>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>'''
            
            try:
                with open(xmp_path, 'w', encoding='utf-8') as xmp_file:
                    xmp_file.write(xmp_content)
                xmp_files_created += 1
            except Exception as e:
                logger.error(f"Failed to create XMP for {file_path}: {e}")
    
    logger.info(f"Created {xmp_files_created} XMP sidecar files ({'merge' if merge_mode else 'overwrite'} mode)")
    if nsfw_count > 0:
        logger.info(f"NSFW content detected in {nsfw_count} images")
    conn.close()
    return xmp_files_created, nsfw_count

def export_digikam_tags(db_path: str, output_path: str, include_nsfw: bool, logger):
    """Export tags in DigiKam-compatible format with NSFW filtering (merged from all batches)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all images and format tags properly for DigiKam import, merged across all batch rounds
    if include_nsfw:
        cursor.execute('''
            SELECT i.file_path, i.file_name, t.category, t.subcategory, t.tag_name,
                   MAX(t.confidence_score) as max_confidence, i.nsfw_detected, i.batch_count
            FROM images i
            LEFT JOIN tags t ON i.id = t.image_id
            GROUP BY i.file_path, t.category, t.subcategory, t.tag_name
            ORDER BY i.file_path, max_confidence DESC
        ''')
    else:
        cursor.execute('''
            SELECT i.file_path, i.file_name, t.category, t.subcategory, t.tag_name,
                   MAX(t.confidence_score) as max_confidence, i.nsfw_detected, i.batch_count
            FROM images i
            LEFT JOIN tags t ON i.id = t.image_id
            WHERE i.nsfw_detected = 0
            GROUP BY i.file_path, t.category, t.subcategory, t.tag_name
            ORDER BY i.file_path, max_confidence DESC
        ''')
    
    results = cursor.fetchall()
    images_dict = {}
    nsfw_filtered = 0
    
    # Group and format tags by image
    for file_path, file_name, category, subcategory, tag_name, confidence, nsfw_detected, batch_count in results:
        if file_path not in images_dict:
            images_dict[file_path] = []
        
        if nsfw_detected and not include_nsfw:
            nsfw_filtered += 1
            continue
        
        # Create proper DigiKam hierarchical tag
        if subcategory:
            digikam_tag = f"{category.title()}/{subcategory.replace('_', ' ').title()}/{tag_name}"
        else:
            digikam_tag = f"{category.title()}/{tag_name}"
        
        if digikam_tag not in images_dict[file_path]:
            images_dict[file_path].append(digikam_tag)
    
    # Create CSV for DigiKam import
    csv_path = os.path.join(output_path, "digikam_tags.csv")
    with open(csv_path, 'w') as f:
        f.write("file_path,tags\n")
        for file_path, tags in images_dict.items():
            if tags:
                # Join tags with semicolon for DigiKam
                tag_string = ";".join(tags)
                f.write(f'"{file_path}","{tag_string}"\n')
    
    logger.info(f"DigiKam tags exported to: {csv_path}")
    if nsfw_filtered > 0:
        logger.info(f"Filtered out {nsfw_filtered} NSFW images from export")
    conn.close()
    return csv_path

def process_folder_mode(images: List[str], csv_files: List[str], model, processor, output_dir: str,
                       confidence_threshold: float, batch_size: int, include_nsfw: bool,
                       export_xmp: bool, merge_existing: bool, logger):
    """Process multiple CSV files in sequence, merging results."""
    
    # Setup database
    db_path = os.path.join(output_dir, "image_tags_merged.db")
    conn = setup_database(db_path)
    
    total_csv_files = len(csv_files)
    total_nsfw_detected = 0
    
    print(f"\n\033[1;33mFolder Mode: Processing {total_csv_files} CSV files...\033[0m\n")
    
    # Process each CSV file
    for csv_round, csv_file in enumerate(csv_files, 1):
        csv_name = os.path.basename(csv_file)
        print(f"\033[93m--- Round {csv_round}/{total_csv_files}: {csv_name} ---\033[0m")
        
        # Load tag queries for this CSV
        tag_queries = load_tag_queries_from_csv(csv_file)
        
        if not tag_queries:
            print(f"\033[93m⚠️  Skipping {csv_name} - no valid queries\033[0m")
            continue
        
        # Process images in batches for this CSV
        total_batches = (len(images) + batch_size - 1) // batch_size
        processed_count = 0
        csv_nsfw_detected = 0
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(images))
            batch_images = images[start_idx:end_idx]
            
            # Process batch
            results = process_image_batch(batch_images, model, processor, tag_queries,
                                        confidence_threshold, csv_round, csv_name, logger)
            
            # Count NSFW detections in this batch
            batch_nsfw = sum(1 for result in results
                           if any(tag['category'] == 'nsfw' and tag['confidence'] > 0.3
                                 for tag in result.get('tags', [])))
            csv_nsfw_detected += batch_nsfw
            
            # Save to database
            save_results_to_db(results, conn, f"Round {csv_round}", csv_round, logger)
            
            processed_count += len(batch_images)
            progress = int((processed_count / len(images)) * 100)
            
            sys.stdout.write(f"\r  \033[93mBatch\033[0m {batch_idx + 1}\033[93m/\033[0m{total_batches} ({progress}%) - {processed_count}\033[93m/\033[0m{len(images)} \033[93mimages...\033[0m")
            if batch_nsfw > 0:
                sys.stdout.write(f" [\033[31m{batch_nsfw} NSFW\033[0m]")
            sys.stdout.flush()
        
        sys.stdout.write("\r" + " " * 100 + "\r")
        sys.stdout.flush()
        
        total_nsfw_detected += csv_nsfw_detected
        print(f"\033[32m✅ Round {csv_round} complete:\033[0m {len(images)} images processed")
        if csv_nsfw_detected > 0:
            print(f"  \033[31mNSFW detected:\033[0m {csv_nsfw_detected} images")
        print()
    
    conn.close()
    
    return db_path, total_nsfw_detected

def main():
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mImage Auto Tagger (AI) - Privacy Optimized\033[0m")
        print("Batch tag images for poses, clothing & NSFW detection")
        print("\033[93m+ NEW: Folder Mode for Multi-CSV Processing\033[0m")
        print("\033[92m==================================================\033[0m")
        print()

        # Initialize CLIP model with offline support
        model, processor, model_name = initialize_clip_model()
        if model is None:
            print("\033[31m❌ Cannot proceed without CLIP model.\033[0m")
            break
        print()

        # Choose processing mode
        folder_mode = prompt_processing_mode()
        print()

        # Get CSV files or folder
        if folder_mode:
            csv_folder = prompt_csv_folder()
            csv_files = get_csv_files_from_folder(csv_folder)
            
            if not csv_files:
                print("\033[31m❌ No CSV files found. Try again.\033[0m")
                continue
                
            print()
        else:
            # Single CSV mode (original)
            csv_path = prompt_csv_dataset()
            tag_queries = load_tag_queries_from_csv(csv_path)
            csv_files = [csv_path]  # For consistency
            print()

        # Input path
        folder_path = djj.get_path_input("Enter folder path")
        print()
        
        include_sub = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No\n",
            ['1', '2'],
            default='2'
        ) == '1'
        print()

        # Collect images
        print("Scanning for images...")
        images = collect_images_from_folder(folder_path, include_sub)
        print()
        if not images:
            print("❌ \033[93mNo valid image files found. Try again.\033[0m\n")
            continue
            
        print(f"✅ \033[93m{len(images)} images found\033[0m")
        print()

        # NSFW handling options
        include_nsfw_in_export = djj.prompt_choice(
            "\033[93mHow to handle NSFW content?\033[0m\n1. Include NSFW tags in export\n2. Filter out NSFW content from export\n3. NSFW detection only (no export)\n",
            ['1', '2', '3'],
            default='2'
        )
        print()

        # Export options
        export_xmp = djj.prompt_choice(
            "\033[93mCreate XMP sidecar files?\033[0m\n1. Yes (recommended for DigiKam)\n2. No, CSV only\n",
            ['1', '2'],
            default='1'
        ) == '1'
        print()
        
        merge_existing = False
        if export_xmp:
            merge_existing = djj.prompt_choice(
                "\033[93mMerge with existing XMP files?\033[0m\n1. No, overwrite (default)\n2. Yes, merge tags\n",
                ['1', '2'],
                default='1'
            ) == '2'
        print()

        # Processing options
        batch_size = BATCH_SIZE
        batch_input = input(f"\033[93mBatch size [default: {BATCH_SIZE}]:\n\033[0m -> ").strip()
        if batch_input.isdigit():
            batch_size = min(int(batch_input), 50)  # Max 50 for M2 MBA
        print()

        # Confidence threshold
        confidence_input = input("\033[93mConfidence threshold [0.1-0.9, default: 0.15]:\n\033[0m -> ").strip()
        try:
            confidence_threshold = float(confidence_input) if confidence_input else 0.15
            confidence_threshold = max(0.1, min(0.9, confidence_threshold))
        except ValueError:
            confidence_threshold = 0.15
        print()

        # Setup output directory
        if folder_mode:
            output_dir = os.path.join(folder_path, "Output", "AutoTagger_FolderMode")
        else:
            output_dir = os.path.join(folder_path, "Output", "AutoTagger")
        
        os.makedirs(output_dir, exist_ok=True)
        logger = setup_logging(output_dir, "batch_tagger")
        
        os.system('clear')
        print("\n" * 3)
        
        if folder_mode:
            print(f"\n\033[1;33mFolder Mode: Processing {len(csv_files)} CSV files...\033[0m")
        else:
            print("\n\033[1;33mProcessing images...\033[0m")
        print("\n" * 2)
        
        include_nsfw = include_nsfw_in_export == '1'
        
        if folder_mode:
            # Process multiple CSV files
            db_path, total_nsfw_detected = process_folder_mode(
                images, csv_files, model, processor, output_dir,
                confidence_threshold, batch_size, include_nsfw,
                export_xmp, merge_existing, logger
            )
        else:
            # Single CSV processing (original logic)
            db_path = os.path.join(output_dir, "image_tags.db")
            conn = setup_database(db_path)
            
            # Process images in batches
            total_batches = (len(images) + batch_size - 1) // batch_size
            processed_count = 0
            total_nsfw_detected = 0
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(images))
                batch_images = images[start_idx:end_idx]
                
                # Process batch
                results = process_image_batch(batch_images, model, processor, tag_queries,
                                            confidence_threshold, 1, os.path.basename(csv_files[0]), logger)
                
                # Count NSFW detections in this batch
                batch_nsfw = sum(1 for result in results
                               if any(tag['category'] == 'nsfw' and tag['confidence'] > 0.3
                                     for tag in result.get('tags', [])))
                total_nsfw_detected += batch_nsfw
                
                # Save to database
                save_results_to_db(results, conn, model_name, 1, logger)
                
                processed_count += len(batch_images)
                progress = int((processed_count / len(images)) * 100)
                
                sys.stdout.write(f"\r\033[93mProcessing batch\033[0m {batch_idx + 1}\033[93m/\033[0m{total_batches} ({progress}%) - {processed_count}\033[93m/\033[0m{len(images)} \033[93mimages...\033[0m")
                if batch_nsfw > 0:
                    sys.stdout.write(f" [\033[31m{batch_nsfw} NSFW\033[0m]")
                print()
                sys.stdout.flush()

            sys.stdout.write("\r" + " " * 100 + "\r")
            sys.stdout.flush()
            conn.close()

        # Export results
        print("\033[93mExporting results...\033[0m")
        
        # Always create CSV for backup
        csv_path = export_digikam_tags(db_path, output_dir, include_nsfw, logger)
        
        # Create XMP sidecar files if requested
        xmp_count = 0
        nsfw_count = 0
        if export_xmp:
            print("\033[93mCreating XMP sidecar files...\033[0m")
            xmp_count, nsfw_count = export_xmp_sidecar_files(db_path, merge_existing, include_nsfw, logger)
        
        print()
        print("\033[93mProcessing Complete!\033[0m")
        print("--------------------")
        print(f"\033[93mProcessing Mode:\033[0m {'Folder Mode (' + str(len(csv_files)) + ' CSVs)' if folder_mode else 'Single CSV'}")
        print(f"\033[93mImages processed:\033[0m {len(images)}")
        print(f"\033[93mNSFW detected:\033[0m {total_nsfw_detected}")
        print(f"\033[93mDatabase:\033[0m {db_path}")
        print(f"\033[93mDigiKam CSV:\033[0m {csv_path}")
        if export_xmp and xmp_count > 0:
            print(f"\033[93mXMP files created:\033[0m {xmp_count}")
            if nsfw_count > 0:
                print(f"\033[93mNSFW content:\033[0m {nsfw_count} images {'included' if include_nsfw else 'filtered out'}")
        print(f"\033[93mOutput folder:\033[0m {output_dir}")
        print()
        
        if folder_mode:
            logger.info(f"Folder mode complete: {len(csv_files)} CSVs processed, {len(images)} images, {total_nsfw_detected} NSFW detected")
        else:
            logger.info(f"Processing complete: {len(images)} images, {total_nsfw_detected} NSFW detected")
        
        djj.prompt_open_folder(output_dir)
        
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == '__main__':
    main()