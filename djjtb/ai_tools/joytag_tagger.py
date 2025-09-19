#!/usr/bin/env python3
"""
JoyTag Image Tagger for DJJTB - WITH XMP DETECTION
Uses JoyTag model for comprehensive image tagging with Danbooru schema
Optimized for M2 MacBook Air 8GB RAM
FIXED: ONNX data type mismatch (double -> float)
NEW: Skip images that already have XMP sidecar files
"""

import os
import sys
import sqlite3
import pathlib
import time
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import subprocess
import gc

# Fix the import path - go up to project root, then import
project_root = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import djjtb.utils as djj
    print("✅ \033[33mDJJTB utils loaded successfully\033[0m")
except ImportError as e:
    print(f"❌ \033[33mFailed to import djjtb.utils:\033[0m {e}")
    sys.exit(1)

# Environment and model paths
AI_MODELS_DIR = "/Users/home/Documents/ai_models"
JOYTAG_MODEL_DIR = os.path.join(AI_MODELS_DIR, "joytag")
VENV_PATH = os.path.join(JOYTAG_MODEL_DIR, "jtvenv")
VENV_PYTHON = os.path.join(VENV_PATH, "bin", "python")

# Clear screen
os.system('clear')

# Supported image formats
SUPPORTED_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff")

# Optimized batch size for M2 MBA 8GB RAM
BATCH_SIZE = 8

def format_elapsed_time(seconds):
    """Format elapsed time in a readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def check_environment():
    """Check if JoyTag environment exists, create if needed"""
    print("\033[93m🔍 Checking JoyTag environment...\033[0m")
    
    # Check if model directory exists
    if not os.path.exists(JOYTAG_MODEL_DIR):
        print(f"\033[33m📁 Creating model directory:\033[0m {JOYTAG_MODEL_DIR}")
        os.makedirs(JOYTAG_MODEL_DIR, exist_ok=True)
    
    # Check if virtual environment exists
    if not os.path.exists(VENV_PATH):
        print("\033[33m🐍 Creating virtual environment for JoyTag...\033[0m")
        try:
            subprocess.run([sys.executable, "-m", "venv", VENV_PATH], check=True)
            print("✅ \033[33mVirtual environment created\033[0m")
        except subprocess.CalledProcessError as e:
            print(f"❌ \033[33mFailed to create venv:\033[0m {e}")
            return False
    
    # Skip automatic environment switching - let user handle manually
    print("✅ \033[33mEnvironment ready (manual activation required)\033[0m")
    print(f"\033[33m💡 To activate: source {VENV_PATH}/bin/activate\033[0m")
    return True

def install_dependencies():
    """Install required packages for JoyTag"""
    print("\033[93m📦 Installing JoyTag dependencies...\033[0m")
    
    required_packages = [
        "torch",
        "torchvision",
        "transformers",
        "huggingface-hub",
        "pillow",
        "numpy",
        "onnxruntime"  # For ONNX model
    ]
    
    try:
        for package in required_packages:
            print(f"   Installing {package}...")
            subprocess.run([
                sys.executable, "-m", "pip", "install", package, "--upgrade"
            ], check=True, capture_output=True)
        
        print("✅ \033[33mDependencies installed\033[0m")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ \033[33mFailed to install dependencies:\033[0m {e}")
        return False

def download_joytag_model():
    """Download JoyTag model from HuggingFace"""
    print("\033[93m⬇️  Downloading JoyTag model...\033[0m")
    
    try:
        # Use huggingface-cli to download the model
        cmd = [
            "huggingface-cli", "download", "fancyfeast/joytag",
            "--local-dir", JOYTAG_MODEL_DIR,
            "--local-dir-use-symlinks", "False"
        ]
        
        subprocess.run(cmd, check=True, cwd=JOYTAG_MODEL_DIR)
        print("✅ \033[33mJoyTag model downloaded\033[0m")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ \033[33mFailed to download model:\033[0m {e}")
        print("\033[33m💡 Try running:\033[0m pip install huggingface_hub[cli]")
        return False

def setup_joytag_environment():
    """Complete setup of JoyTag environment"""
    print()
    print("\033[92m======================================================================\033[0m")
    print("\033[1;33m🚀 JoyTag Environment Setup\033[0m")
    print("\033[92m======================================================================\033[0m")
    
    # Step 1: Check/create environment
    if not check_environment():
        return False
    
    # Step 2: Install dependencies
    if not install_dependencies():
        return False
    
    # Step 3: Download model
    model_exists = os.path.exists(os.path.join(JOYTAG_MODEL_DIR, "model.safetensors"))
    if not model_exists:
        if not download_joytag_model():
            return False
    else:
        print("✅ \033[33mJoyTag model already exists\033[0m")
    
    print()
    print("✅ \033[33m🎉 JoyTag environment ready!\033[0m")
    return True

def setup_logging(output_path, prefix="joytag"):
    """Set up logging to a file in the output folder."""
    logger = djj.setup_logging(output_path, f"{prefix}_tagger")
    return logger

class JoyTagProcessor:
    """JoyTag image processor using the fancyfeast/joytag model"""
    
    def __init__(self):
        self.model = None
        self.device = "mps" if self._check_mps() else "cpu"
        print(f"🖥️  \033[33mUsing device:\033[0m {self.device}")
        
    def _check_mps(self):
        """Check if MPS is available on M1/M2 Macs"""
        try:
            import torch
            return torch.backends.mps.is_available()
        except:
            return False
    
    def load_model(self):
        """Load JoyTag model - pure ONNX approach"""
        if self.model is not None:
            return True
            
        print("\033[93m📥 Loading JoyTag model...\033[0m")
        
        try:
            import onnxruntime as ort
            import numpy as np
            
            # Look for ONNX model file
            onnx_path = os.path.join(JOYTAG_MODEL_DIR, "model.onnx")
            if not os.path.exists(onnx_path):
                print(f"❌ \033[33mONNX model not found at:\033[0m {onnx_path}")
                return False
                
            print("\033[33m🏃 Loading ONNX model for JoyTag\033[0m")
            
            # Set up ONNX Runtime providers
            providers = ["CPUExecutionProvider"]  # JoyTag works fine on CPU
            
            self.model = ort.InferenceSession(onnx_path, providers=providers)
            self.model_type = "onnx"
            
            # Get input shape from model
            input_shape = self.model.get_inputs()[0].shape
            self.input_size = input_shape[2] if len(input_shape) > 2 else 448  # Default JoyTag size
            
            print(f"\033[33m📐 Model input size:\033[0m {self.input_size}x{self.input_size}")
            
            # Load labels/tags
            self._load_labels()
            
            print("✅ \033[33mJoyTag model loaded successfully\033[0m")
            return True
            
        except Exception as e:
            print(f"❌ \033[33mFailed to load JoyTag model:\033[0m {e}")
            return False
    
    def _load_labels(self):
        """Load the tag labels for JoyTag"""
        try:
            # JoyTag typically has a top_tags.txt file with the labels
            possible_label_files = [
                "top_tags.txt",
                "tags.txt",
                "labels.txt",
                "tag_names.txt"
            ]
            
            labels_loaded = False
            
            for filename in possible_label_files:
                labels_file = os.path.join(JOYTAG_MODEL_DIR, filename)
                if os.path.exists(labels_file):
                    print(f"\033[33m📋 Loading labels from:\033[0m {filename}")
                    with open(labels_file, 'r', encoding='utf-8') as f:
                        self.labels = [line.strip() for line in f if line.strip()]
                    labels_loaded = True
                    break
            
            if not labels_loaded:
                print("⚠️  \033[33mNo label files found, checking downloaded files...\033[0m")
                # List what files we actually have
                files = os.listdir(JOYTAG_MODEL_DIR)
                print(f"Available files: {files}")
                self.labels = None
            else:
                print(f"\033[32m✅ Loaded {len(self.labels)} labels\033[0m")
                    
        except Exception as e:
            print(f"⚠️  \033[33mFailed to load labels:\033[0m {e}")
            self.labels = None
    
    def unload_model(self):
        """Unload model to free memory"""
        if self.model is not None:
            del self.model
            self.model = None
            
            import torch
            gc.collect()
            if self.device == "mps":
                torch.mps.empty_cache()
    
    def process_image(self, image_path: str, confidence_threshold: float = 0.5) -> List[Dict]:
        """Process a single image and return tags with confidence scores"""
        try:
            from PIL import Image
            import numpy as np
            
            # Load and preprocess image
            image = Image.open(image_path).convert("RGB")
            
            # Manual preprocessing for JoyTag ONNX model
            # Resize and normalize like JoyTag expects
            image = image.resize((self.input_size, self.input_size), Image.LANCZOS)
            
            # Convert to numpy array and ensure float32 throughout
            img_array = np.array(image, dtype=np.float32) / 255.0
            
            # Normalize with ImageNet stats (common for vision models)
            # CRITICAL FIX: Ensure all operations maintain float32 precision
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            img_array = (img_array - mean) / std
            
            # Add batch dimension and transpose to NCHW format
            img_array = img_array.transpose(2, 0, 1)  # HWC -> CHW
            img_array = np.expand_dims(img_array, axis=0)  # Add batch dim
            
            # CRITICAL FIX: Ensure final array is float32 before ONNX inference
            img_array = img_array.astype(np.float32)
            
            # Run ONNX inference
            input_name = self.model.get_inputs()[0].name
            outputs = self.model.run(None, {input_name: img_array})
            logits = outputs[0][0]  # Remove batch dimension
            
            # Apply sigmoid for multi-label classification
            probs = 1 / (1 + np.exp(-logits))  # Sigmoid
            
            # Extract high-confidence tags
            tags = []
            for i, confidence in enumerate(probs):
                if confidence > confidence_threshold:
                    tag_name = self.labels[i] if self.labels and i < len(self.labels) else f"tag_{i}"
                    tags.append({
                        'tag': tag_name,
                        'confidence': float(confidence),
                        'category': self._categorize_tag(tag_name)
                    })
            
            # Sort by confidence
            tags.sort(key=lambda x: x['confidence'], reverse=True)
            return tags
            
        except Exception as e:
            print(f"❌ \033[33mFailed to process {os.path.basename(image_path)}:\033[0m {e}")
            return []
    
    def _categorize_tag(self, tag: str) -> str:
        """Categorize tags based on Danbooru schema patterns"""
        tag_lower = tag.lower()
        
        # Basic categorization based on common Danbooru patterns
        if any(word in tag_lower for word in ['hair', 'eyes', 'face']):
            return 'character'
        elif any(word in tag_lower for word in ['shirt', 'dress', 'clothing', 'outfit']):
            return 'clothing'
        elif any(word in tag_lower for word in ['standing', 'sitting', 'lying', 'pose']):
            return 'pose'
        elif any(word in tag_lower for word in ['indoor', 'outdoor', 'background']):
            return 'setting'
        elif any(word in tag_lower for word in ['nsfw', 'nude', 'explicit']):
            return 'nsfw'
        else:
            return 'general'

def setup_database(db_path):
    """Create SQLite database for storing JoyTag results"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Images table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            file_name TEXT NOT NULL,
            processed_date TEXT NOT NULL,
            model_used TEXT NOT NULL,
            tag_count INTEGER DEFAULT 0,
            max_confidence REAL DEFAULT 0.0
        )
    ''')
    
    # Tags table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER,
            tag_name TEXT NOT NULL,
            category TEXT,
            confidence_score REAL NOT NULL,
            FOREIGN KEY (image_id) REFERENCES images (id)
        )
    ''')
    
    # Add indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_path ON images(file_path)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tag_image ON tags(image_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tag_name ON tags(tag_name)')
    
    conn.commit()
    return conn

def collect_images_from_folder(input_path, include_subfolders=False):
    """Collect images from folder(s) - following DJJTB pattern."""
    input_path_obj = pathlib.Path(input_path)
    
    images = []
    if input_path_obj.is_dir():
        if include_subfolders:
            for root, _, files in os.walk(input_path):
                images.extend(pathlib.Path(root) / f for f in files
                            if pathlib.Path(f).suffix.lower() in SUPPORTED_EXTS)
        else:
            images = [f for f in input_path_obj.glob('*')
                     if f.suffix.lower() in SUPPORTED_EXTS and f.is_file()]
    
    return sorted([str(v) for v in images], key=str.lower)

def process_image_batch(image_paths: List[str], processor: JoyTagProcessor,
                       confidence_threshold: float, logger) -> List[Dict]:
    """Process a batch of images and return results"""
    results = []
    
    for img_path in image_paths:
        try:
            tags = processor.process_image(img_path, confidence_threshold)
            
            if tags:
                results.append({
                    'image_path': img_path,
                    'tags': tags,
                    'tag_count': len(tags),
                    'max_confidence': max(tag['confidence'] for tag in tags)
                })
                
        except Exception as e:
            logger.error(f"Failed to process {img_path}: {e}")
            
    return results

def save_results_to_db(results: List[Dict], conn, model_name: str, logger):
    """Save JoyTag results to database"""
    cursor = conn.cursor()
    
    for result in results:
        img_path = result['image_path']
        img_name = pathlib.Path(img_path).name
        
        try:
            # Insert image record
            cursor.execute('''
                INSERT OR REPLACE INTO images
                (file_path, file_name, processed_date, model_used, tag_count, max_confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (img_path, img_name, datetime.now().isoformat(), model_name,
                  result['tag_count'], result['max_confidence']))
            
            image_id = cursor.lastrowid
            
            # Delete existing tags for this image
            cursor.execute('DELETE FROM tags WHERE image_id = ?', (image_id,))
            
            # Insert new tags
            for tag in result['tags']:
                cursor.execute('''
                    INSERT INTO tags (image_id, tag_name, category, confidence_score)
                    VALUES (?, ?, ?, ?)
                ''', (image_id, tag['tag'], tag['category'], tag['confidence']))
            
        except Exception as e:
            logger.error(f"Database error for {img_path}: {e}")
    
    conn.commit()

def export_xmp_sidecar_files(db_path: str, merge_mode: bool, logger):
    """Export XMP sidecar files for DigiKam"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT i.file_path, t.tag_name, t.category, t.confidence_score
        FROM images i
        LEFT JOIN tags t ON i.id = t.image_id
        WHERE t.tag_name IS NOT NULL
        ORDER BY i.file_path, t.confidence_score DESC
    ''')
    
    results = cursor.fetchall()
    images_dict = {}
    
    # Group tags by image
    for file_path, tag_name, category, confidence in results:
        if file_path not in images_dict:
            images_dict[file_path] = []
        
        # Format tag for DigiKam (hierarchical)
        if category and category != 'general':
            digikam_tag = f"JoyTag/{category.title()}/{tag_name}"
        else:
            digikam_tag = f"JoyTag/{tag_name}"
        
        images_dict[file_path].append(digikam_tag)
    
    xmp_files_created = 0
    
    for file_path, tags in images_dict.items():
        if tags:
            xmp_path = f"{file_path}.xmp"
            
            # Handle merge mode
            if merge_mode and os.path.exists(xmp_path):
                existing_tags = djj.read_existing_xmp_tags(xmp_path) if hasattr(djj, 'read_existing_xmp_tags') else []
                all_tags = list(set(existing_tags + tags))
            else:
                all_tags = tags
            
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
    
    logger.info(f"Created {xmp_files_created} XMP sidecar files")
    conn.close()
    return xmp_files_created
    
def export_txt_per_image(db_path: str, logger):
    """Export a plain .txt file per image with tags and confidence"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT i.file_path, t.tag_name, t.confidence_score
        FROM images i
        LEFT JOIN tags t ON i.id = t.image_id
        WHERE t.tag_name IS NOT NULL
        ORDER BY i.file_path, t.confidence_score DESC
    ''')

    results = cursor.fetchall()
    images_dict = {}

    # Group tags by image
    for file_path, tag_name, confidence in results:
        if file_path not in images_dict:
            images_dict[file_path] = []
        images_dict[file_path].append((tag_name, confidence))

    txt_files_created = 0

    for file_path, tag_list in images_dict.items():
        if not tag_list:
            continue
        txt_path = f"{file_path}.txt"
        try:
            with open(txt_path, 'w', encoding='utf-8') as f:
                for tag, conf in tag_list:
                    f.write(f"{tag} {int(conf * 100)}%\n")
            txt_files_created += 1
        except Exception as e:
            logger.error(f"Failed to write TXT for {file_path}: {e}")

    conn.close()
    logger.info(f"Created {txt_files_created} TXT tag files")
    return txt_files_created

def export_csv_results(db_path: str, output_path: str, logger):
    """Export results to CSV"""
    import csv
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT i.file_path, i.file_name, t.tag_name, t.category,
               t.confidence_score, i.processed_date
        FROM images i
        LEFT JOIN tags t ON i.id = t.image_id
        ORDER BY i.file_path, t.confidence_score DESC
    ''')
    
    results = cursor.fetchall()
    csv_path = os.path.join(output_path, "joytag_results.csv")
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['file_path', 'file_name', 'tag_name', 'category',
                        'confidence_score', 'processed_date'])
        writer.writerows(results)
    
    logger.info(f"Results exported to CSV: {csv_path}")
    conn.close()
    return csv_path

def main():
    while True:
        print()
        print("\033[92m======================================================================\033[0m")
        print("\033[1;33mJoyTag Image Tagger for DJJTB - WITH XMP DETECTION\033[0m")
        print("Comprehensive image tagging using Danbooru schema")
        print("Optimized for M2 MacBook Air 8GB RAM")
        print("\033[92m======================================================================\033[0m")
        print()
        
        # Check if setup is needed - look for any model files
        model_files = ['model.safetensors', 'pytorch_model.bin', 'model.onnx', 'config.json']
        model_exists = any(os.path.exists(os.path.join(JOYTAG_MODEL_DIR, f)) for f in model_files)
        if not model_exists:
            print("\033[93m⚡ First time setup required\033[0m")
            setup_choice = djj.prompt_choice(
                "\033[33mSet up JoyTag environment?\033[0m\n1. Yes, set up now\n2. Exit\n",
                ['1', '2'],
                default='1'
            )
            
            if setup_choice == '2':
                print("👋 Setup cancelled. Exiting.")
                break
                
            if not setup_joytag_environment():
                print("❌ \033[33mSetup failed. Please check your installation.\033[0m")
                break
            
            print()
            continue
        
        # Initialize JoyTag processor
        processor = JoyTagProcessor()
        if not processor.load_model():
            print("❌ \033[33mFailed to load JoyTag model.\033[0m")
            break
        print()
        
        # Get input path
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
        all_images = collect_images_from_folder(folder_path, include_sub)
        print()
        
        if not all_images:
            print("❌ \033[93mNo valid image files found. Try again.\033[0m\n")
            continue
            
        print(f"✅ \033[93m{len(all_images)} images found\033[0m")
        print()
        
        # NEW: Get XMP handling configuration
        xmp_config = djj.prompt_xmp_handling_mode()
        
        # NEW: Filter images based on XMP handling mode
        if xmp_config['skip_existing']:
            images_to_process, images_with_xmp, xmp_stats = djj.filter_images_without_xmp(all_images, show_stats=True)
            
            if not images_to_process:
                print("🎉 \033[92mAll images already have XMP files! Nothing to process.\033[0m")
                
                # Offer to continue anyway
                continue_anyway = djj.prompt_choice(
                    "Process all images anyway (overwrite XMP files)?\n1. Yes, process all\n2. No, skip this folder\n",
                    ['1', '2'],
                    default='2'
                )
                
                if continue_anyway == '2':
                    continue
                else:
                    images_to_process = all_images
                    xmp_config['skip_existing'] = False
                    xmp_config['overwrite_existing'] = True
            
        else:
            images_to_process = all_images
            # Still show stats for user awareness
            djj.filter_images_without_xmp(all_images, show_stats=True)
        
        # Get confidence threshold
        confidence_input = input("\033[93mConfidence threshold [0.1-0.9, default: 0.4]:\n\033[0m -> ").strip()
        try:
            confidence_threshold = float(confidence_input) if confidence_input else 0.4
            confidence_threshold = max(0.1, min(0.9, confidence_threshold))
        except ValueError:
            confidence_threshold = 0.4
        print()
        
        # Export options
        export_xmp = djj.prompt_choice(
            "\033[93mCreate XMP sidecar files?\033[0m\n1. Yes (recommended for DigiKam)\n2. No, CSV only\n",
            ['1', '2'],
            default='1'
        ) == '1'
        print()
        
        export_txt = djj.prompt_choice(
            "\033[93mAlso export TXT file per image?\033[0m\n1. Yes,  2. No\n",
            ['1', '2'],
            default='1'
        ) == '1'
        print()
        
        # Processing options
        batch_size = BATCH_SIZE
        batch_input = input(f"\033[93mBatch size [default: {BATCH_SIZE}]:\n\033[0m -> ").strip()
        if batch_input.isdigit():
            batch_size = min(int(batch_input), 20)
        print()
        
        # Setup output directory
        output_dir = os.path.join(folder_path, "Output", "JoyTag")
        os.makedirs(output_dir, exist_ok=True)
        logger = setup_logging(output_dir, "joytag")
        
        os.system('clear')
        print("\n" * 3)
        
        # Start processing
        processing_start_time = time.time()
        
        print("\n\033[1;33mProcessing images with JoyTag...\033[0m")
        if xmp_config['skip_existing'] and len(images_to_process) < len(all_images):
            skipped_count = len(all_images) - len(images_to_process)
            print(f"\033[92m⏭️  Skipping {skipped_count} images that already have XMP files\033[0m")
        print("\n" * 2)
        
        # Setup database
        db_path = os.path.join(output_dir, "joytag_results.db")
        conn = setup_database(db_path)
        
        # Process images in batches
        total_batches = (len(images_to_process) + batch_size - 1) // batch_size
        processed_count = 0
        total_tags = 0
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(images_to_process))
            batch_images = images_to_process[start_idx:end_idx]
            
            # Process batch
            results = process_image_batch(batch_images, processor, confidence_threshold, logger)
            
            # Count tags
            batch_tags = sum(result['tag_count'] for result in results)
            total_tags += batch_tags
            
            # Save to database
            save_results_to_db(results, conn, "JoyTag", logger)
            
            processed_count += len(batch_images)
            progress = int((processed_count / len(images_to_process)) * 100)
            
            # Calculate elapsed time
            current_elapsed = time.time() - processing_start_time
            sys.stdout.write(f"\r\033[93mProcessing batch\033[0m {batch_idx + 1}\033[93m/\033[0m{total_batches} ({progress}%) - {processed_count}\033[93m/\033[0m{len(images_to_process)} \033[93mimages...\033[0m \033[36m[Elapsed: {format_elapsed_time(current_elapsed)}]\033[0m")
            
            if batch_tags > 0:
                sys.stdout.write(f" [\033[32m{batch_tags} tags\033[0m]")
            sys.stdout.flush()

        sys.stdout.write("\r" + " " * 98 + "\r")
        
        conn.close()
        processor.unload_model()
        
        # Calculate processing time
        processing_time = time.time() - processing_start_time
        
        # Export results
        export_start_time = time.time()
        print("\033[93mExporting results...\033[0m")
        
        # Always create CSV
        csv_path = export_csv_results(db_path, output_dir, logger)
        
        # Create XMP sidecar files if requested
        xmp_count = 0
        if export_xmp:
            print("\033[93mCreating XMP sidecar files...\033[0m")
            # Use the merge setting from xmp_config
            xmp_count = export_xmp_sidecar_files(db_path, xmp_config['merge_existing'], logger)

        export_time = time.time() - export_start_time
        total_time = time.time() - processing_start_time
        
        # Create TXT files if requested
        txt_count = 0
        if export_txt:
            print("\033[93mCreating TXT tag files...\033[0m")
            txt_count = export_txt_per_image(db_path, logger)
        
        print()
        print("\033[1;93m 🚀 JoyTag Processing Complete! 💥\033[0m")
        print("\033[92m--------------------\033[0m")
        print(f"\033[93mTotal images found:\033[0m {len(all_images)}")
        if xmp_config['skip_existing'] and len(images_to_process) < len(all_images):
            print(f"\033[93mImages skipped (had XMP):\033[0m {len(all_images) - len(images_to_process)}")
        print(f"\033[93mImages processed:\033[0m {len(images_to_process)}")
        print(f"\033[93mTotal tags found:\033[0m {total_tags}")
        if images_to_process:
            print(f"\033[93mAvg tags per image:\033[0m {total_tags/len(images_to_process):.1f}")
        print(f"\033[93mConfidence threshold:\033[0m {confidence_threshold}")
        print(f"\033[93mXMP handling:\033[0m {xmp_config['mode_description']}")
        print(f"\033[93mProcessing time:\033[0m {format_elapsed_time(processing_time)}")
        print(f"\033[93mExport time:\033[0m {format_elapsed_time(export_time)}")
        print(f"\033[93mTotal time:\033[0m {format_elapsed_time(total_time)}")
        print(f"\033[93mDatabase:\033[0m {db_path}")
        print(f"\033[93mResults CSV:\033[0m {csv_path}")
        if export_xmp and xmp_count > 0:
            print(f"\033[93mXMP files created:\033[0m {xmp_count}")
        if export_txt and txt_count > 0:
            print(f"\033[93mTXT files created:\033[0m {txt_count}")
        print(f"\033[93mOutput folder:\033[0m {output_dir}")
        print()
        
        # Log the session
        log_message = f"JoyTag processing complete: {len(all_images)} total images"
        if xmp_config['skip_existing'] and len(images_to_process) < len(all_images):
            log_message += f", {len(all_images) - len(images_to_process)} skipped (had XMP)"
        log_message += f", {len(images_to_process)} processed, {total_tags} total tags"
        if images_to_process:
            log_message += f", avg {total_tags/len(images_to_process):.1f} tags/image"
        log_message += f", {xmp_config['mode_description']}, total time: {format_elapsed_time(total_time)}"
        
        logger.info(log_message)
        
        djj.prompt_open_folder(output_dir)
        
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == '__main__':
    main()