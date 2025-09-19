#!/usr/bin/env python3
"""
AI Watermark Remover for DJJTB
Uses Florence-2 for watermark detection and LaMa for inpainting removal
Optimized for M2 MacBook Air 8GB RAM - FIXED VERSION WITH PRECISE CORNER DETECTION
"""

import os
import sys
import gc
import subprocess
from pathlib import Path
from typing import List, Optional
import time
import cv2
import numpy as np
from PIL import Image

import numpy as np

try:
    from ultralytics import YOLO
except ImportError:
    print("⚠️  ultralytics (YOLOv8) not installed. Installing now...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ultralytics"])
    from ultralytics import YOLO

# Fix the import path - go up to project root, then import
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import djjtb.utils as djj
    print("✅ \033[33mDJJTB utils loaded successfully\033[0m")
except ImportError as e:
    print(f"❌ \033[33mFailed to import djjtb.utils:\033[0m {e}")
    print(f"Project root: {project_root}")
    print(f"Current path: {sys.path}")
    sys.exit(1)

# Environment and model paths
VENV_PATH = "/Users/home/Documents/ai_models/watermark_remover/wmrmvenv"
MODEL_CACHE_DIR = "/Users/home/Documents/ai_models/watermark_remover/models"
VENV_PYTHON = os.path.join(VENV_PATH, "bin", "python")

# Supported extensions
SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')

def ensure_venv_and_run():
    """Ensure we're running in the correct virtual environment"""
    if not os.path.exists(VENV_PATH):
        print("❌ \033[33mVirtual environment not found at\033[0m", VENV_PATH)
        print("\033[33mPlease run the setup instructions first\033[0m")
        return False
    
    # Check if we're already in the correct venv
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        current_venv = sys.prefix
        if VENV_PATH in current_venv:
            return True
    
    # Re-run this script with the correct venv
    if os.path.exists(VENV_PYTHON):
        print("\033[33mActivating watermark removal environment...\033[0m")
        # Preserve the sys.path modifications when re-executing
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root)
        os.execve(VENV_PYTHON, [VENV_PYTHON] + sys.argv, env)
    else:
        print(f"❌ \033[33mPython executable not found in venv:\033[0m {VENV_PYTHON}")
        return False

def check_dependencies():
    """Check if required packages are installed - LaMa focused"""
    required_packages = {
        'torch': 'torch',
        'transformers': 'transformers',
        'PIL': 'Pillow',
        'cv2': 'opencv-python',
        'numpy': 'numpy',
        'lama_cleaner': 'lama-cleaner',  # This is the key package
        'simple_lama_inpainting': 'simple-lama-inpainting'  # Alternative lightweight LaMa
    }
    
    missing = []
    optional_missing = []
    
    # Check core requirements first
    core_packages = ['torch', 'transformers', 'PIL', 'cv2', 'numpy']
    
    for import_name in core_packages:
        try:
            if import_name == 'PIL':
                import PIL
            elif import_name == 'cv2':
                import cv2
            else:
                __import__(import_name)
        except ImportError:
            missing.append(required_packages[import_name])
    
    # Check LaMa packages (try to use what's available)
    lama_available = False
    try:
        import lama_cleaner
        lama_available = True
        print("✅ \033[33mLaMa Cleaner found\033[0m")
    except ImportError:
        try:
            import simple_lama_inpainting
            lama_available = True
            print("✅ \033[33mSimple LaMa Inpainting found\033[0m")
        except ImportError:
            optional_missing.extend(['lama-cleaner', 'simple-lama-inpainting'])
    
    if missing:
        print(f"❌ \033[33mMissing core packages:\033[0m {', '.join(missing)}")
        print("\033[33mInstalling missing core packages...\033[0m")
        
        try:
            for package in missing:
                print(f"Installing {package}...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print("✅ \033[33mCore packages installed successfully\033[0m")
        except subprocess.CalledProcessError as e:
            print(f"❌ \033[33mFailed to install packages:\033[0m {e}")
            return False
    
    if not lama_available and optional_missing:
        print(f"⚠️  \033[33mLaMa packages not found. Installing simple-lama-inpainting...\033[0m")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'simple-lama-inpainting'])
            print("✅ \033[33mLaMa inpainting installed\033[0m")
        except subprocess.CalledProcessError as e:
            print(f"❌ \033[33mFailed to install LaMa:\033[0m {e}")
            print("⚠️  \033[33mContinuing without LaMa - will use basic inpainting\033[0m")
    
    print("✅ \033[33mDependency check complete\033[0m")
    return True

def setup_model_cache():
    """Ensure model cache directory exists"""
    os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
    os.environ['HF_HOME'] = MODEL_CACHE_DIR
    os.environ['TRANSFORMERS_CACHE'] = os.path.join(MODEL_CACHE_DIR, 'transformers')

def clean_path(path_str):
    """Clean path string by removing quotes and whitespace"""
    return path_str.strip().strip('\'"')

def collect_images_from_folder(input_path, subfolders=False):
    """Collect supported images from folder(s)"""
    input_path_obj = Path(input_path)
    
    images = []
    if input_path_obj.is_dir():
        if subfolders:
            for root, _, filenames in os.walk(input_path):
                images.extend(Path(root) / f for f in filenames
                           if Path(f).suffix.lower() in SUPPORTED_EXTS)
        else:
            images = [f for f in input_path_obj.glob('*')
                    if f.suffix.lower() in SUPPORTED_EXTS and f.is_file()]
    
    return sorted([str(f) for f in images], key=str.lower)

def collect_images_from_paths(file_paths):
    """Collect images from space-separated file paths"""
    images = []
    paths = file_paths.strip().split()
    
    for path in paths:
        path = clean_path(path)
        path_obj = Path(path)
        
        if path_obj.is_file() and path_obj.suffix.lower() in SUPPORTED_EXTS:
            images.append(str(path_obj))
        elif path_obj.is_dir():
            dir_images = collect_images_from_folder(path)
            images.extend(dir_images)
    
    return sorted(images, key=str.lower)

def get_valid_inputs():
    """Get and validate input files using your established patterns"""
    print("\033[1;33m🖼️  Select images to process\033[0m")
    
    input_mode = djj.prompt_choice(
        "\033[33mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
        ['1', '2'],
        default='1'
    )
    print()
    
    valid_paths = []
    
    if input_mode == '1':
        src_path = djj.get_path_input("Enter folder path")
        print()
        
        include_sub = djj.prompt_choice(
            "\033[33mInclude subfolders?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        
        valid_paths = collect_images_from_folder(src_path, include_sub)
        
    else:
        file_paths = input("📁 \033[33mEnter image paths (space-separated):\033[0m\n -> ").strip()
        
        if not file_paths:
            print("❌ \033[33mNo file paths provided.\033[0m")
            sys.exit(1)
        
        valid_paths = collect_images_from_paths(file_paths)
        print()
    
    if not valid_paths:
        print("❌ \033[33mNo valid image files found.\033[0m")
        sys.exit(1)
    
    os.system('clear')
    print("\n" * 2)
    print("🔍 Detecting images...")
    print()
    print(f"\033[33m✅ Found\033[0m {len(valid_paths)} \033[33msupported image(s)\033[0m")
    print()
    print("Choose Your Options:")
    
    return valid_paths, input_mode, src_path if input_mode == '1' else None

class WatermarkRemover:
    """AI-powered watermark removal using Florence-2 + LaMa Inpainting"""
    
    def __init__(self):
        self.florence_model = None
        self.florence_processor = None
        self.lama_model = None
        self.device = "mps" if self._check_mps() else "cpu"
        self.lama_method = self._detect_lama_method()
        print(f"🖥️  \033[33mUsing device:\033[0m {self.device}")
        print(f"🎯 \033[33mInpainting method:\033[0m {self.lama_method}")
    
    def _check_mps(self):
        """Check if MPS is available on M1/M2 Macs"""
        try:
            import torch
            return torch.backends.mps.is_available()
        except:
            return False
    
    def _detect_lama_method(self):
        """Detect which LaMa implementation is available"""
        try:
            import lama_cleaner
            return "lama_cleaner"
        except ImportError:
            try:
                import simple_lama_inpainting
                return "simple_lama"
            except ImportError:
                return "opencv_inpaint"  # Fallback to OpenCV
                
    def load_yolo_model(self):
        """Load YOLOv8 model for watermark detection"""
        if hasattr(self, "yolo_model") and self.yolo_model is not None:
            return
        try:
            print("📥 \033[33mLoading YOLOv8 model for watermark detection...\033[0m")
            # Use pretrained nano model; can fine-tune later for watermark
            self.yolo_model = YOLO("yolov8n.pt")
            print("✅ \033[33mYOLOv8 model loaded\033[0m")
        except Exception as e:
            print(f"❌ \033[33mFailed to load YOLO model:\033[0m {e}")
            self.yolo_model = None
    
    def load_florence_model(self):
        """Load Florence-2 model for watermark detection"""
        if self.florence_model is not None:
            return
        
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoProcessor
            
            print("📥 \033[33mLoading Florence-2 detection model...\033[0m")
            model_name = "microsoft/Florence-2-base"
            
            self.florence_processor = AutoProcessor.from_pretrained(
                model_name,
                cache_dir=MODEL_CACHE_DIR,
                trust_remote_code=True
            )
            
            self.florence_model = AutoModelForCausalLM.from_pretrained(
                model_name,
                cache_dir=MODEL_CACHE_DIR,
                torch_dtype=torch.float32,  # Force float32 for MPS compatibility
                trust_remote_code=True
            ).to(self.device)
            
            print("✅ \033[33mFlorence-2 model loaded\033[0m")
            
        except Exception as e:
            print(f"❌ \033[33mFailed to load Florence-2 model:\033[0m {str(e)}")
            raise
    
    def unload_florence_model(self):
        """Unload Florence-2 model to free memory"""
        if self.florence_model is not None:
            del self.florence_model
            del self.florence_processor
            self.florence_model = None
            self.florence_processor = None
            
            import torch
            gc.collect()
            if self.device == "mps":
                torch.mps.empty_cache()
            elif torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    def load_lama_model(self):
        """Load LaMa inpainting model"""
        if self.lama_model is not None:
            return
            
        try:
            print("📥 \033[33mLoading LaMa inpainting model...\033[0m")
            
            if self.lama_method == "lama_cleaner":
                from lama_cleaner.model_manager import ModelManager
                from lama_cleaner.schema import Config
                
                # Initialize LaMa through lama_cleaner
                self.lama_model = ModelManager(
                    name="lama",
                    device=self.device if self.device != "mps" else "cpu",  # LaMa may not support MPS
                    no_half=True  # For stability on Mac
                )
                
            elif self.lama_method == "simple_lama":
                from simple_lama_inpainting import SimpleLama
                
                self.lama_model = SimpleLama()
                
            print(f"✅ \033[33mLaMa model loaded ({self.lama_method})\033[0m")
            
        except Exception as e:
            print(f"⚠️  \033[33mLaMa loading failed, using OpenCV fallback:\033[0m {str(e)}")
            self.lama_method = "opencv_inpaint"
            self.lama_model = "opencv"  # Placeholder
    
    def unload_lama_model(self):
        """Unload LaMa model to free memory"""
        if self.lama_model is not None and self.lama_model != "opencv":
            del self.lama_model
            self.lama_model = None
            
            import torch
            gc.collect()
            if self.device == "mps":
                torch.mps.empty_cache()
            elif torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    @staticmethod
    def detect_watermark_color_based(image_path: str) -> List[List[int]]:
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ Failed to load image: {image_path}")
            return []

        height, width = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Define pink range in HSV
        lower_pink = np.array([160, 100, 100])
        upper_pink = np.array([180, 255, 255])

        # Define corner regions
        corner_regions = {
            "top-left": (0, 0, int(width * 0.35), int(height * 0.35)),
            "top-right": (int(width * 0.65), 0, width, int(height * 0.35)),
            "bottom-left": (0, int(height * 0.65), int(width * 0.35), height),
            "bottom-right": (int(width * 0.65), int(height * 0.65), width, height),
        }

        bboxes = []
        for label, (x1, y1, x2, y2) in corner_regions.items():
            corner = hsv[y1:y2, x1:x2]
            mask = cv2.inRange(corner, lower_pink, upper_pink)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                bx, by, bw, bh = cv2.boundingRect(cnt)
                abs_x1 = x1 + bx
                abs_y1 = y1 + by
                abs_x2 = abs_x1 + bw
                abs_y2 = abs_y1 + bh
                area = bw * bh
                if area > 200:
                    print(f"🎯 Detected watermark in {label} ({bw}x{bh})")
                    bboxes.append([abs_x1, abs_y1, abs_x2, abs_y2])

        print(f"✅ Found {len(bboxes)} watermark region(s)")
        return bboxes

    @staticmethod
    def create_mask_from_bboxes(image_path: str, bboxes: List[List[int]]) -> Optional[str]:
        image = Image.open(image_path)
        width, height = image.size
        mask = np.zeros((height, width), dtype=np.uint8)

        if not bboxes:
            print("⚠️  No watermark detected. Skipping.")
            return None

        for i, bbox in enumerate(bboxes):
            x1, y1, x2, y2 = bbox
            pad = 8
            x1 = max(0, x1 - pad)
            y1 = max(0, y1 - pad)
            x2 = min(width, x2 + pad)
            y2 = min(height, y2 + pad)
            mask[y1:y2, x1:x2] = 255
            print(f"   🎯 Watermark region {i+1}: {x2-x1}px x {y2-y1}px")

        mask_path = image_path.replace(Path(image_path).suffix, '_mask.png')
        cv2.imwrite(mask_path, mask)
        print(f"   📊 Mask saved: {mask_path}")
        return mask_path
    
    def remove_watermark(self, image_path: str, mask_path: str, output_path: str) -> bool:
        """Remove watermark using LaMa inpainting with your existing installation"""
        try:
            from PIL import Image
            import numpy as np
            
            print(f"   🎨 Using {self.lama_method} for inpainting...")
            
            # Load images
            image = Image.open(image_path).convert("RGB")
            mask = Image.open(mask_path).convert("L")
            
            if self.lama_method in ["lama_cleaner", "iopaint"]:
                self.load_lama_model()
                
                # Convert PIL to numpy arrays (lama_cleaner format)
                image_np = np.array(image)
                mask_np = np.array(mask)
                
                # Ensure mask is binary
                mask_np = (mask_np > 128).astype(np.uint8) * 255
                
                # Process with your existing lama_cleaner
                # The ModelManager expects the image and mask in a specific format
                result_np = self.lama_model(image_np, mask_np)
                result = Image.fromarray(result_np.astype(np.uint8))
                
            elif self.lama_method == "simple_lama":
                self.load_lama_model()
                
                # Use simple_lama_inpainting
                result = self.lama_model(image, mask)
                
            else:  # opencv_inpaint fallback
                import cv2
                
                print("   ⚠️  Using OpenCV inpainting (basic method)")
                
                # Convert to OpenCV format
                image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                mask_cv = np.array(mask)
                
                # Ensure mask is binary
                mask_cv = (mask_cv > 128).astype(np.uint8) * 255
                
                # Apply OpenCV inpainting (two methods for better results)
                result1 = cv2.inpaint(image_cv, mask_cv, 3, cv2.INPAINT_TELEA)
                result2 = cv2.inpaint(image_cv, mask_cv, 3, cv2.INPAINT_NS)
                
                # Blend results for better quality
                result_cv = cv2.addWeighted(result1, 0.6, result2, 0.4, 0)
                result_rgb = cv2.cvtColor(result_cv, cv2.COLOR_BGR2RGB)
                result = Image.fromarray(result_rgb)
            
            # Save result with high quality
            result.save(output_path, quality=95, optimize=True)
            return True
            
        except Exception as e:
            print(f"❌ \033[33mInpainting failed:\033[0m {str(e)}")
            import traceback
            traceback.print_exc()  # For debugging
            return False
        finally:
            if self.lama_method not in ["opencv_inpaint"]:
                self.unload_lama_model()
    
    def process_image(self, input_path: str, output_path: str) -> bool:
        """Process a single image for watermark removal"""
        try:
            file_name = os.path.basename(input_path)
            print(f"🖼️  \033[33mProcessing:\033[0m {file_name}")
            
            # Step 1: Detect watermarks
            print("   Step 1: Detecting watermark regions...")
            bboxes = self.detect_watermark_color_based(input_path)
            
            # Step 2: Create mask
            print("   Step 2: Creating precise corner masks...")
            mask_path = self.create_mask_from_bboxes(input_path, bboxes)
            if not mask_path:
                return False
            
            # Step 3: Remove watermark
            print("   Step 3: Removing watermark with LaMa AI inpainting...")
            success = self.remove_watermark(input_path, mask_path, output_path)
            
            # Cleanup temporary mask
            if os.path.exists(mask_path):
                os.remove(mask_path)
            
            if success:
                print(f"✅ \033[33mCompleted:\033[0m {file_name}")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ \033[33mFailed processing\033[0m {os.path.basename(input_path)}: {str(e)}")
            return False

def process_images_batch(input_paths, input_mode, src_path, suffix):
    """Process images following your established batch processing pattern with memory safety"""
    print("\n" * 2)
    print(f"\n\033[1;33m🧠 Processing\033[0m {len(input_paths)} \033[1;33mimage(s):\033[0m")
    print("=" * 50)
    print(f"\033[33m🔠 Suffix:\033[0m {suffix}")
    if input_mode == '1':
        print(f"\033[33m📥 Input folder:\033[0m {src_path}")
    print("\033[33m⚡ Memory-Safe Mode:\033[0m Enabled for M2 MacBook Air")
    print("=" * 50)
    print()
    print("\033[1;33m🤖 AI Watermark Remover (LaMa Edition - Fixed) 🤖 \033[0m\033[33mactivating...\033[0m")
    print()
    
    remover = WatermarkRemover()
    success_count = 0
    error_count = 0
    error_messages = []
    output_paths = set()
    
    # Process smaller batches to avoid memory issues
    batch_size = 5  # Process 5 images at a time
    total_batches = (len(input_paths) + batch_size - 1) // batch_size
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, len(input_paths))
        batch_paths = input_paths[start_idx:end_idx]
        
        print(f"\033[1;33m📦 Batch {batch_idx + 1}/{total_batches}\033[0m ({len(batch_paths)} images)")
        print()
        
        for i, input_path in enumerate(batch_paths):
            file_name = os.path.basename(input_path)
            overall_idx = start_idx + i + 1
            print(f"\033[33m[{overall_idx}/{len(input_paths)}]\033[0m")
            
            # Create output path
            input_dir = Path(input_path).parent
            output_dir = input_dir / "Output"/ "NoWM"  # Watermark Removed
            output_dir.mkdir(parents=True, exist_ok=True)
            output_paths.add(output_dir)
            
            # Generate output filename
            input_stem = Path(input_path).stem
            output_name = f"{input_stem}_{suffix}.png"  # Always save as PNG for quality
            output_path = output_dir / output_name
            
            try:
                if remover.process_image(str(input_path), str(output_path)):
                    success_count += 1
                else:
                    error_count += 1
                    error_messages.append(f"{file_name}: Processing failed")
                    
            except Exception as e:
                print(f"❌ \033[33mException:\033[0m {file_name} - {str(e)}")
                error_count += 1
                error_messages.append(f"{file_name}: {str(e)}")
            
            print()  # Add spacing between files
        
        # Memory cleanup between batches
        print(f"\033[33m🧹 Cleaning memory after batch {batch_idx + 1}...\033[0m")
        import torch
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        print()
    
    print("=" * 50)
    print(f"\033[1;33m🏁 Batch Processing Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {success_count} \033[33mimage(s)\033[0m")
    print(f"❌ \033[33mFailed:\033[0m {error_count} \033[33mimage(s)\033[0m")
    
    # Show first few errors if any
    if error_messages:
        print(f"\n\033[33mFirst few errors:\033[0m")
        for error in error_messages[:3]:
            print(f"  • {error}")
        if len(error_messages) > 3:
            print(f"  • ... and {len(error_messages) - 3} more")
    
    print("=" * 50)
    
    # Handle opening output folders (following your pattern)
    if len(output_paths) == 1:
        output_path = list(output_paths)[0]
        djj.prompt_open_folder(output_path)
    elif len(output_paths) > 1:
        print(f"\033[33m📁 Created files in {len(output_paths)} different output folders.\033[0m")
        open_choice = djj.prompt_choice(
            "\033[33mOpen output folders?\033[0m\n1. Yes, open all\n2. Yes, open first one only\n3. No",
            ['1', '2', '3'],
            default='2'
        )
        
        if open_choice == '1':
            folders_opened = 0
            for output_path in sorted(output_paths):
                if folders_opened < 5:
                    subprocess.run(['open', str(output_path)])
                    folders_opened += 1
                else:
                    break
            if len(output_paths) > 5:
                print(f"\033[33mNote: Opened first 5 folders. Total: {len(output_paths)}\033[0m")
        elif open_choice == '2':
            first_folder = sorted(output_paths)[0]
            subprocess.run(['open', str(first_folder)])
            print(f"✅ \033[33mOpened:\033[0m {first_folder}")

def main():
    os.system('clear')
    
    # Ensure we're in the right environment first
    if not ensure_venv_and_run():
        return
    
    # Check dependencies and install if missing
    if not check_dependencies():
        print("\n\033[33mFailed to install required dependencies\033[0m")
        return
    
    # Setup model cache
    setup_model_cache()
    
    while True:
        print()
        print("\033[92m" + "=" * 50 + "\033[0m")
        print("\033[1   ;33mAI Watermark Remover (LaMa Edition - Fixed)\033[0m")
        print("Florence-2 Detection + LaMa Inpainting")
        print("Optimized for M2 MacBook Air 8GB RAM")
        print("🎯 FIXED: Precise corner watermark detection")
        print("\033[92m" + "=" * 50 + "\033[0m")
        print()
        
        try:
            input_files, input_mode, src_path = get_valid_inputs()
            
            # Get suffix
            suffix = djj.get_string_input(
                "\033[33mEnter suffix (default 'NoWM'):\033[0m\n > ",
                default="NoWM"
            )
            
            os.system('clear')
            
            # Process all images
            process_images_batch(input_files, input_mode, src_path, suffix)
            
            print()
            action = djj.what_next()
            if action == 'exit':
                break
                
        except KeyboardInterrupt:
            print("\n\033[33mOperation cancelled by user\033[0m")
            break
        except Exception as e:
            print(f"\n❌ \033[33mUnexpected error:\033[0m {str(e)}")
            print("Please check your setup and try again")
            break

if __name__ == "__main__":
    main()