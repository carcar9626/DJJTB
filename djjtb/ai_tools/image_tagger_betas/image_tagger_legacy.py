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
                category = row['category'].strip()
                subcategory = row['subcategory'].strip() if row['subcategory'].strip() else None
                query = row['query'].strip()
                
                if not query or query.startswith('#'):  # Skip empty queries and comments
                    continue
                
                # Initialize nested structure
                if category not in tag_queries:
                    tag_queries[category] = {}
                if subcategory not in tag_queries[category]:
                    tag_queries[category][subcategory] = []
                
                # Add query to appropriate category/subcategory
                tag_queries[category][subcategory].append(query)
        
        print(f"\033[32m✅ Loaded tag queries from:\033[0m {csv_path}")
        
        # Show summary
        total_categories = len(tag_queries)
        total_subcategories = sum(len(subcat) for subcat in tag_queries.values())
        total_queries = sum(len(queries) for cat in tag_queries.values() for queries in cat.values())
        
        print(f"\033[93mLoaded:\033[0m {total_categories} categories, {total_subcategories} subcategories, {total_queries} total queries")
        
        # Show category breakdown
        for category, subcats in tag_queries.items():
            subcat_count = sum(len(queries) for queries in subcats.values())
            print(f"  \033[93m{category}:\033[0m {len(subcats)} subcategories, {subcat_count} queries")
        
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
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            file_name TEXT NOT NULL,
            processed_date TEXT NOT NULL,
            model_used TEXT NOT NULL,
            nsfw_detected INTEGER DEFAULT 0,
            max_nsfw_confidence REAL DEFAULT 0.0
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
            FOREIGN KEY (image_id) REFERENCES images (id)
        )
    ''')
    
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
        if tag['category'] == 'nsfw' and tag['confidence'] > 0.3:  # Higher threshold for NSFW
            nsfw_detected = True
            max_nsfw_confidence = max(max_nsfw_confidence, tag['confidence'])
            tag['is_nsfw'] = 1
    
    return nsfw_detected, max_nsfw_confidence

def process_image_batch(image_paths: List[str], model, processor, tag_queries: Dict, confidence_threshold: float, logger) -> List[Dict]:
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
                category_threshold = max(0.25, confidence_threshold)  # Higher threshold for NSFW
            elif category == 'sfw':
                category_threshold = max(0.2, confidence_threshold - 0.05)  # Lower threshold for SFW confirmation
            
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
                                'is_nsfw': 1 if category == 'nsfw' else 0
                            })
        
        # Clear memory
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
            
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
    
    return results

def save_results_to_db(results: List[Dict], conn, model_name: str, logger):
    """Save tagging results to database with NSFW detection."""
    cursor = conn.cursor()
    
    for result in results:
        img_path = result['image_path']
        img_name = pathlib.Path(img_path).name
        
        # Detect NSFW content
        nsfw_detected, max_nsfw_confidence = detect_nsfw_content(result['tags'])
        
        try:
            # Insert image record with NSFW detection
            cursor.execute('''
                INSERT OR REPLACE INTO images
                (file_path, file_name, processed_date, model_used, nsfw_detected, max_nsfw_confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (img_path, img_name, datetime.now().isoformat(), model_name,
                  1 if nsfw_detected else 0, max_nsfw_confidence))
            
            image_id = cursor.lastrowid
            
            # Delete existing tags for this image
            cursor.execute('DELETE FROM tags WHERE image_id = ?', (image_id,))
            
            # Insert new tags
            for tag in result['tags']:
                cursor.execute('''
                    INSERT INTO tags (image_id, category, subcategory, tag_name, confidence_score, is_nsfw)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (image_id, tag['category'], tag['subcategory'], tag['tag_name'],
                      tag['confidence'], tag.get('is_nsfw', 0)))
            
            # Log NSFW detection
            if nsfw_detected:
                logger.info(f"NSFW detected: {img_name} (confidence: {max_nsfw_confidence:.3f})")
            
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
    """Export XMP sidecar files with proper DigiKam tag structure."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all images and their tags with optional NSFW filtering
    if include_nsfw:
        cursor.execute('''
            SELECT i.file_path, i.file_name, t.category, t.subcategory, t.tag_name,
                   t.confidence_score, i.nsfw_detected
            FROM images i
            LEFT JOIN tags t ON i.id = t.image_id
            WHERE t.tag_name IS NOT NULL
            ORDER BY i.file_path, t.confidence_score DESC
        ''')
    else:
        cursor.execute('''
            SELECT i.file_path, i.file_name, t.category, t.subcategory, t.tag_name,
                   t.confidence_score, i.nsfw_detected
            FROM images i
            LEFT JOIN tags t ON i.id = t.image_id
            WHERE t.tag_name IS NOT NULL AND i.nsfw_detected = 0
            ORDER BY i.file_path, t.confidence_score DESC
        ''')
    
    results = cursor.fetchall()
    images_dict = {}
    nsfw_count = 0
    
    # Group tags by image
    for file_path, file_name, category, subcategory, tag_name, confidence, nsfw_detected in results:
        if file_path not in images_dict:
            images_dict[file_path] = {
                'tags': [],
                'nsfw_detected': nsfw_detected
            }
        
        # Create DigiKam hierarchical tag: Category/Subcategory/TagName
        if subcategory:
            digikam_tag = f"{category.title()}/{subcategory.replace('_', ' ').title()}/{tag_name}"
        else:
            digikam_tag = f"{category.title()}/{tag_name}"
        
        # Avoid duplicates
        if digikam_tag not in [t for t in images_dict[file_path]['tags']]:
            images_dict[file_path]['tags'].append(digikam_tag)
        
        if nsfw_detected:
            nsfw_count += 1
    
    xmp_files_created = 0
    
    for file_path, data in images_dict.items():
        tags = data['tags']
        nsfw_detected = data['nsfw_detected']
        
        if tags:
            xmp_path = f"{file_path}.xmp"
            
            # Handle merge mode
            if merge_mode:
                existing_tags = read_existing_xmp_tags(xmp_path)
                # Combine and deduplicate
                all_tags = list(set(existing_tags + tags))
            else:
                all_tags = tags
            
            # Add NSFW warning tag if detected
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
    """Export tags in DigiKam-compatible format with NSFW filtering."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all images and format tags properly for DigiKam import
    if include_nsfw:
        cursor.execute('''
            SELECT i.file_path, i.file_name, t.category, t.subcategory, t.tag_name,
                   t.confidence_score, i.nsfw_detected
            FROM images i
            LEFT JOIN tags t ON i.id = t.image_id
            ORDER BY i.file_path, t.confidence_score DESC
        ''')
    else:
        cursor.execute('''
            SELECT i.file_path, i.file_name, t.category, t.subcategory, t.tag_name,
                   t.confidence_score, i.nsfw_detected
            FROM images i
            LEFT JOIN tags t ON i.id = t.image_id
            WHERE i.nsfw_detected = 0
            ORDER BY i.file_path, t.confidence_score DESC
        ''')
    
    results = cursor.fetchall()
    images_dict = {}
    nsfw_filtered = 0
    
    # Group and format tags by image
    for file_path, file_name, category, subcategory, tag_name, confidence, nsfw_detected in results:
        if file_path not in images_dict:
            images_dict[file_path] = []
        
        if nsfw_detected and not include_nsfw:
            nsfw_filtered += 1
            continue
        
        # Create proper DigiKam hierarchical tag
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

def main():
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mImage Auto Tagger (AI) - Privacy Optimized\033[0m")
        print("Batch tag images for poses, clothing & NSFW detection")
        print("\033[92m==================================================\033[0m")
        print()

        # Initialize CLIP model with offline support
        model, processor, model_name = initialize_clip_model()
        if model is None:
            print("\033[31m❌ Cannot proceed without CLIP model.\033[0m")
            break
        print()

        # CSV Dataset selection
        csv_path = prompt_csv_dataset()
        tag_queries = load_tag_queries_from_csv(csv_path)
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

        # Setup output and database
        output_dir = os.path.join(folder_path, "Output", "AutoTagger")
        os.makedirs(output_dir, exist_ok=True)
        
        db_path = os.path.join(output_dir, "image_tags.db")
        logger = setup_logging(output_dir, "batch_tagger")
        
        os.system('clear')
        print("\n" * 3)
        print("\n\033[1;33mProcessing images (100% offline)...\033[0m")
        print("\n" * 2)
        
        # Initialize database
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
            results = process_image_batch(batch_images, model, processor, tag_queries, confidence_threshold, logger)
            
            # Count NSFW detections in this batch
            batch_nsfw = sum(1 for result in results
                           if any(tag['category'] == 'nsfw' and tag['confidence'] > 0.3
                                 for tag in result.get('tags', [])))
            total_nsfw_detected += batch_nsfw
            
            # Save to database
            save_results_to_db(results, conn, model_name, logger)
            
            processed_count += len(batch_images)
            progress = int((processed_count / len(images)) * 100)
            
            sys.stdout.write(f"\r\033[93mProcessing batch\033[0m {batch_idx + 1}\033[93m/\033[0m{total_batches} ({progress}%) - {processed_count}\033[93m/\033[0m{len(images)} \033[93mimages...\033[0m")
            if batch_nsfw > 0:
                sys.stdout.write(f" [\033[31m{batch_nsfw} NSFW\033[0m]")
            print()
            sys.stdout.flush()

        sys.stdout.write("\r" + " " * 100 + "\r")
        sys.stdout.flush()

        # Export results
        print("\033[93mExporting results...\033[0m")
        
        include_nsfw = include_nsfw_in_export == '1'
        
        # Always create CSV for backup
        csv_path = export_digikam_tags(db_path, output_dir, include_nsfw, logger)
        
        # Create XMP sidecar files if requested
        xmp_count = 0
        nsfw_count = 0
        if export_xmp:
            print("\033[93mCreating XMP sidecar files...\033[0m")
            xmp_count, nsfw_count = export_xmp_sidecar_files(db_path, merge_existing, include_nsfw, logger)
        
        conn.close()
        
        print()
        print("\033[93mProcessing Complete!\033[0m")
        print("--------------------")
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
        
        logger.info(f"Processing complete: {len(images)} images, {total_nsfw_detected} NSFW detected")
        
        djj.prompt_open_folder(output_dir)
        
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == '__main__':
    main()