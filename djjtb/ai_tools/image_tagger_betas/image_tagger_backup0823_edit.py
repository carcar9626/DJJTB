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

os.system('clear')

# Supported image formats
SUPPORTED_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff")

# Batch size for processing (adjust for M2 MBA 8GB RAM)
BATCH_SIZE = 50

def setup_logging(output_path, prefix):
    """Set up logging to a file in the output folder."""
    logger = djj.setup_logging(output_path, f"autotagger_{prefix.lower()}")
    return logger

def initialize_clip_model():
    """Initialize CLIP model for fashion/artistic content."""
    print("\033[93mLoading CLIP model...\033[0m")
    try:
        # Try LAION model first (better for diverse content including artistic)
        model_name = "laion/CLIP-ViT-B-32-laion2B-s34B-b79K"
        model = CLIPModel.from_pretrained(model_name)
        processor = CLIPProcessor.from_pretrained(model_name)
        print(f"\033[32m✅ Loaded model:\033[0m {model_name}")
        return model, processor, model_name
    except Exception as e:
        print(f"\033[93mFailed to load LAION model, trying fallback...\033[0m")
        try:
            # Fallback to standard CLIP
            model_name = "openai/clip-vit-base-patch32"
            model = CLIPModel.from_pretrained(model_name)
            processor = CLIPProcessor.from_pretrained(model_name)
            print(f"\033[32m✅ Loaded fallback model:\033[0m {model_name}")
            return model, processor, model_name
        except Exception as e2:
            print(f"\033[31m❌ Failed to load any CLIP model:\033[0m {e2}")
            return None, None, None

def get_default_csv_path():
    """Get the default CSV path in a private location."""
    # Put it in your Documents folder, outside the repo
    return os.path.expanduser("/Users/home/Documents/Scripts/image_tagger_data/tag_queries.csv")

def prompt_csv_dataset():
    """Prompt user to choose CSV dataset with your pattern."""
    csv_choice = djj.prompt_choice(
        "\033[93mSelect tag dataset:\033[0m\n1. Default dataset (recommended)\n2. Load custom CSV file\n",
        ['1', '2'],
        default='1'
    )
    
    if csv_choice == '1':
        # Use default CSV
        default_csv = get_default_csv_path()
        
        if not os.path.exists(default_csv):
            print(f"\033[93m⚠️  Default CSV not found at:\033[0m {default_csv}")
            print("\033[93mCreating default dataset...\033[0m")
            create_csv_template(default_csv)
        
        return default_csv
    else:
        # Custom CSV
        csv_path = djj.get_path_input("Enter CSV file path")
        if not csv_path.endswith('.csv'):
            print("\033[93m⚠️  Warning: File doesn't have .csv extension\033[0m")
        return csv_path

def load_tag_queries_from_csv(csv_path: str) -> Dict:
    """Enhanced CSV loader with support for nested categories."""
    import csv
    
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
                
                if not query:  # Skip empty queries
                    continue
                
                # Handle different nesting scenarios:
                # 1. Just category: "car" -> category="general", subcategory="vehicles", query="car"
                # 2. Category + subcategory: "clothing > top" -> category="clothing", subcategory="top"
                # 3. Deep nesting: "clothing > top > crop top" -> category="clothing", subcategory="top/crop_top"
                
                # If subcategory is empty, create a default one
                if not subcategory:
                    if category in tag_queries:
                        subcategory = "general"
                    else:
                        subcategory = "main"
                
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
            'standing': [
                "person standing casually",
                "person standing formally posed",
                "person standing with confident pose",
                "person standing elegantly"
            ],
            'sitting': [
                "person sitting on chair",
                "person sitting on floor",
                "person sitting on bed",
                "person sitting casually"
            ],
            'lying': [
                "person lying on bed",
                "person reclining elegantly",
                "person lying on side",
                "person lying down relaxed"
            ],
            'action': [
                "person walking",
                "person dancing",
                "person jumping",
                "person in motion"
            ]
        },
        'clothing': {
            'general': [
                "person wearing clothing",
                "dressed person"
            ],
            'dresses': [
                "person wearing red dress",
                "person wearing blue dress",
                "person wearing black dress",
                "person wearing white dress",
                "person wearing evening gown",
                "person wearing casual dress"
            ],
            'tops': [
                "person wearing shirt",
                "person wearing blouse",
                "person wearing jacket",
                "person wearing top"
            ],
            'accessories': [
                "person wearing glasses",
                "person wearing jewelry",
                "person wearing hat",
                "person wearing heels",
                "person wearing high heels"
            ],
            'styles': [
                "person in casual clothing",
                "person in formal attire",
                "person in evening wear",
                "person in swimwear",
                "person in lingerie"
            ]
        },
        'composition': {
            'shots': [
                "close up portrait",
                "full body shot",
                "three quarter portrait",
                "headshot photography"
            ],
            'style': [
                "professional photography",
                "artistic photography",
                "fashion photography",
                "glamour photography",
                "editorial photography"
            ]
        },
        # NSFW/Artistic category
        'artistic': {
            'nudity': [
                "artistic nude photography",
                "topless artistic portrait",
                "artistic partial nudity",
                "nude figure study"
            ],
            'sensual': [
                "sensual portrait",
                "intimate photography",
                "boudoir photography",
                "romantic portrait"
            ]
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
            model_used TEXT NOT NULL
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
    """Clean up tag names for DigiKam compatibility."""
    # Remove common prefixes
    cleaned = query.lower()
    
    # Remove "person" prefix
    if cleaned.startswith("person "):
        cleaned = cleaned[7:]
    
    # Remove "wearing" for clothing items
    if cleaned.startswith("wearing "):
        cleaned = cleaned[8:]
        
    # Remove "on" for poses
    if cleaned.startswith("on "):
        cleaned = cleaned[3:]
        
    # Clean up extra spaces and capitalize properly
    cleaned = " ".join(cleaned.split())
    cleaned = cleaned.title()
    
    # For DigiKam, create hierarchical tags using category/subcategory
    # This creates proper tag hierarchy in DigiKam
    if subcategory:
        # Create format: "Category/Subcategory/Tag"
        return f"{category.title()}/{subcategory.title()}/{cleaned}"
    else:
        return f"{category.title()}/{cleaned}"


def process_image_batch(image_paths: List[str], model, processor, tag_queries: Dict, confidence_threshold: float, logger) -> List[Dict]:
    """Process a batch of images and return tags."""
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
                    if confidence > confidence_threshold:
                        original_query = queries[best_query_idx]
                        tag_name = clean_tag_name(original_query, category)
                        
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
                                'original_query': original_query
                            })
        
        # Clear memory
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
            
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
    
    return results

def save_results_to_db(results: List[Dict], conn, model_name: str, logger):
    """Save tagging results to database."""
    cursor = conn.cursor()
    
    for result in results:
        img_path = result['image_path']
        img_name = pathlib.Path(img_path).name
        
        try:
            # Insert image record
            cursor.execute('''
                INSERT OR REPLACE INTO images (file_path, file_name, processed_date, model_used)
                VALUES (?, ?, ?, ?)
            ''', (img_path, img_name, datetime.now().isoformat(), model_name))
            
            image_id = cursor.lastrowid
            
            # Delete existing tags for this image
            cursor.execute('DELETE FROM tags WHERE image_id = ?', (image_id,))
            
            # Insert new tags
            for tag in result['tags']:
                cursor.execute('''
                    INSERT INTO tags (image_id, category, subcategory, tag_name, confidence_score)
                    VALUES (?, ?, ?, ?, ?)
                ''', (image_id, tag['category'], tag['subcategory'], tag['tag_name'], tag['confidence']))
            
        except Exception as e:
            logger.error(f"Database error for {img_path}: {e}")
    
    conn.commit()

def create_csv_template(csv_path: str):
    """Create a CSV template file with sample queries including NSFW content."""
    import csv
    
    template_data = [
        # Poses
        ["poses", "standing", "person standing casually"],
        ["poses", "standing", "person standing formally posed"],
        ["poses", "standing", "person standing with confident pose"],
        ["poses", "standing", "person standing elegantly"],
        ["poses", "sitting", "person sitting on chair"],
        ["poses", "sitting", "person sitting on floor"],
        ["poses", "sitting", "person sitting on bed"],
        ["poses", "sitting", "person sitting casually"],
        ["poses", "lying", "person lying on bed"],
        ["poses", "lying", "person reclining elegantly"],
        ["poses", "lying", "person lying on side"],
        ["poses", "lying", "person lying down relaxed"],
        ["poses", "squatting", "person squatting"],
        ["poses", "squatting", "person crouching down"],
        ["poses", "action", "person walking"],
        ["poses", "action", "person dancing"],
        ["poses", "action", "person jumping"],
        ["poses", "action", "person in motion"],
        
        # Clothing - Basic structure
        ["clothing", "general", "person wearing clothing"],
        ["clothing", "general", "dressed person"],
        
        # Clothing - Dresses (you can add color variants)
        ["clothing", "dresses", "person wearing dress"],
        ["clothing", "dresses", "person wearing evening gown"],
        ["clothing", "dresses", "person wearing casual dress"],
        ["clothing", "dresses", "person wearing formal dress"],
        
        # Clothing - Tops (easily expandable)
        ["clothing", "tops", "person wearing shirt"],
        ["clothing", "tops", "person wearing blouse"],
        ["clothing", "tops", "person wearing jacket"],
        ["clothing", "tops", "person wearing top"],
        ["clothing", "tops", "person wearing crop top"],
        ["clothing", "tops", "person wearing button up shirt"],
        
        # Clothing - Bottoms
        ["clothing", "bottoms", "person wearing pants"],
        ["clothing", "bottoms", "person wearing jeans"],
        ["clothing", "bottoms", "person wearing skirt"],
        ["clothing", "bottoms", "person wearing shorts"],
        
        # Clothing - Accessories
        ["clothing", "accessories", "person wearing glasses"],
        ["clothing", "accessories", "person wearing jewelry"],
        ["clothing", "accessories", "person wearing hat"],
        ["clothing", "accessories", "person wearing heels"],
        ["clothing", "accessories", "person wearing high heels"],
        
        # Clothing - Styles
        ["clothing", "styles", "person in casual clothing"],
        ["clothing", "styles", "person in formal attire"],
        ["clothing", "styles", "person in evening wear"],
        ["clothing", "styles", "person in swimwear"],
        ["clothing", "styles", "person in lingerie"],
        
        # Composition
        ["composition", "shots", "close up portrait"],
        ["composition", "shots", "full body shot"],
        ["composition", "shots", "three quarter portrait"],
        ["composition", "shots", "headshot photography"],
        ["composition", "style", "professional photography"],
        ["composition", "style", "artistic photography"],
        ["composition", "style", "fashion photography"],
        ["composition", "style", "glamour photography"],
        ["composition", "style", "editorial photography"],
        
        # Location
        ["location", "indoor", "indoor setting"],
        ["location", "indoor", "bedroom interior"],
        ["location", "indoor", "bathroom interior"],
        ["location", "outdoor", "outdoor setting"],
        ["location", "outdoor", "beach scene"],
        ["location", "outdoor", "park setting"],
        ["location", "venue", "restaurant setting"],
        ["location", "venue", "cafe interior"],
        ["location", "venue", "hotel room"],
        
        # NSFW/Artistic content
        ["artistic", "nudity", "artistic nude photography"],
        ["artistic", "nudity", "topless artistic portrait"],
        ["artistic", "nudity", "artistic partial nudity"],
        ["artistic", "nudity", "nude figure study"],
        ["artistic", "sensual", "sensual portrait"],
        ["artistic", "sensual", "intimate photography"],
        ["artistic", "sensual", "boudoir photography"],
        ["artistic", "sensual", "romantic portrait"],
        
        # Examples for simple tags (no subcategory needed - will use "general")
        ["vehicles", "", "car"],
        ["vehicles", "", "motorcycle"],
        ["vehicles", "", "bicycle"],
        ["nature", "", "flowers"],
        ["nature", "", "trees"],
        ["nature", "", "sunset"],
        
        # Examples showing nesting possibilities through subcategory naming
        ["clothing", "tops/crop", "person wearing crop top"],
        ["clothing", "tops/crop", "person wearing white crop top"],
        ["clothing", "dresses/evening", "person wearing black evening gown"],
        ["clothing", "dresses/casual", "person wearing summer dress"],
    ]
    
    try:
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['category', 'subcategory', 'query'])  # Header
            writer.writerows(template_data)
        print(f"\033[32m✅ Created CSV template:\033[0m {csv_path}")
    except Exception as e:
        print(f"\033[31m❌ Error creating CSV template:\033[0m {e}")

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

def export_xmp_sidecar_files(db_path: str, merge_mode: bool, logger):
    """Export XMP sidecar files with proper DigiKam tag structure."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all images and their tags - but format them properly for DigiKam
    cursor.execute('''
        SELECT i.file_path, i.file_name, t.category, t.subcategory, t.tag_name, t.confidence_score
        FROM images i
        LEFT JOIN tags t ON i.id = t.image_id
        WHERE t.tag_name IS NOT NULL
        ORDER BY i.file_path, t.confidence_score DESC
    ''')
    
    results = cursor.fetchall()
    images_dict = {}
    
    # Group tags by image
    for file_path, file_name, category, subcategory, tag_name, confidence in results:
        if file_path not in images_dict:
            images_dict[file_path] = []
        
        # Create DigiKam-friendly tag format
        if subcategory:
            digikam_tag = f"{category.title()}/{subcategory.title()}"
        else:
            digikam_tag = f"{category.title()}/{tag_name}"
            
        # Avoid duplicates
        if digikam_tag not in images_dict[file_path]:
            images_dict[file_path].append(digikam_tag)
    
    xmp_files_created = 0
    
    for file_path, tags in images_dict.items():
        if tags:
            xmp_path = f"{file_path}.xmp"
            
            # Handle merge mode
            if merge_mode:
                existing_tags = read_existing_xmp_tags(xmp_path)
                # Combine and deduplicate
                all_tags = list(set(existing_tags + tags))
            else:
                all_tags = tags
            
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
    conn.close()
    return xmp_files_created    
    
    for file_path, file_name, tags in results:
        if tags:
            xmp_path = f"{file_path}.xmp"
            new_tag_list = [tag.strip() for tag in tags.split(';') if tag.strip()]
            
            # Handle merge mode
            if merge_mode:
                existing_tags = read_existing_xmp_tags(xmp_path)
                # Combine and deduplicate
                all_tags = list(set(existing_tags + new_tag_list))
            else:
                all_tags = new_tag_list
            
            # Create XMP content
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
    conn.close()
    return xmp_files_created

def export_digikam_tags(db_path: str, output_path: str, logger):
    """Export tags in DigiKam-compatible format."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all images and format tags properly for DigiKam import
    cursor.execute('''
        SELECT i.file_path, i.file_name, t.category, t.subcategory, t.tag_name, t.confidence_score
        FROM images i
        LEFT JOIN tags t ON i.id = t.image_id
        ORDER BY i.file_path, t.confidence_score DESC
    ''')
    
    results = cursor.fetchall()
    images_dict = {}
    
    # Group and format tags by image
    for file_path, file_name, category, subcategory, tag_name, confidence in results:
        if file_path not in images_dict:
            images_dict[file_path] = []
        
        # Create proper DigiKam hierarchical tag
        if subcategory:
            digikam_tag = f"{category.title()}/{subcategory.title()}"
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

def main():
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mImage Auto Tagger (AI)\033[0m")
        print("Batch tag images for poses, clothing & style")
        print("\033[92m==================================================\033[0m")
        print()

        # Initialize CLIP model
        model, processor, model_name = initialize_clip_model()
        if model is None:
            print("\033[31m❌ Cannot proceed without CLIP model.\033[0m")
            break
        print()

        # CSV Dataset selection - NEW
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
        print()
        if not images:
            print("❌ \033[93mNo valid image files found. Try again.\033[0m\n")
            continue
            
        print(f"✅ \033[93m{len(images)} images found\033[0m")
        print()
        # Export options
        export_xmp = djj.prompt_choice(
            "\033[93mCreate XMP sidecar files?\033[0m\n1. Yes (recommended)\n2. No, CSV only\n",
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
            batch_size = min(int(batch_input), 100)  # Max 100 for M2 MBA
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
        print("\n\033[1;33mProcessing images...\033[0m")
        print("\n" * 2)
        # Initialize database
        conn = setup_database(db_path)
        
        # Process images in batches
        total_batches = (len(images) + batch_size - 1) // batch_size
        processed_count = 0
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(images))
            batch_images = images[start_idx:end_idx]
            
            # Process batch
            results = process_image_batch(batch_images, model, processor, tag_queries, confidence_threshold, logger)
            
            # Save to database
            save_results_to_db(results, conn, model_name, logger)
            
            processed_count += len(batch_images)
            progress = int((processed_count / len(images)) * 100)
            
            sys.stdout.write(f"\r\033[93mProcessing batch\033[0m {batch_idx + 1}\033[93m/\033[0m{total_batches} ({progress}%) - {processed_count}\033[93m/\033[0m{len(images)} \033[93mimages...\033[0m")
            print()
            sys.stdout.flush()

        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()

        # Export results
        print("\033[93mExporting results...\033[0m")
        
        # Always create CSV for backup
        csv_path = export_digikam_tags(db_path, output_dir, logger)
        
        # Create XMP sidecar files if requested
        xmp_count = 0
        if export_xmp:
            print("\033[93mCreating XMP sidecar files...\033[0m")
            xmp_count = export_xmp_sidecar_files(db_path, merge_existing, logger)
        
        conn.close()
        
        print()
        print("\033[93mProcessing Complete!\033[0m")
        print("--------------------")
        print(f"\033[93mImages processed:\033[0m {len(images)}")
        print(f"\033[93mDatabase:\033[0m {db_path}")
        print(f"\033[93mDigiKam CSV:\033[0m {csv_path}")
        if export_xmp and xmp_count > 0:
            print(f"\033[93mXMP files created:\033[0m {xmp_count}")
            print(f"\033[93mDisk usage estimate:\033[0m ~{(xmp_count * 1.5):.1f} KB")
        print(f"\033[93mOutput folder:\033[0m {output_dir}")
        print()
        
        logger.info(f"Processing complete: {len(images)} images")
        
        djj.prompt_open_folder(output_dir)
        
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == '__main__':
    main()