#!/usr/bin/env python3
"""
Enhanced AI Watermark Remover for DJJTB - V2 with Inpainting Options
Multi-Detection: Shapes + Text + Semi-transparent + Original pink detection
Added: Telea, Navier-Stokes, Hybrid inpainting options
Version: 2.1 - Inpainting Selection + Improved Detection
"""

import os
import sys
import gc
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
import time
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import re
import tempfile


# Fix the import path - go up to project root, then import
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import djjtb.utils as djj
    print("✅ \033[33mDJJTB utils loaded successfully\033[0m")
except ImportError as e:
    print(f"❌ \033[33mFailed to import djjtb.utils:\033[0m {e}")
    print(f"Project root: {project_root}")
    sys.exit(1)

# Environment and model paths
VENV_PATH = "/Users/home/Documents/ai_models/watermark_remover/wmrmvenv"
MODEL_CACHE_DIR = "/Users/home/Documents/ai_models/watermark_remover/models"
VENV_PYTHON = os.path.join(VENV_PATH, "bin", "python")

# Supported extensions
SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')

# Global OCR availability check
OCR_AVAILABLE = None
try:
    import easyocr
    OCR_AVAILABLE = "easyocr"
except ImportError:
    try:
        import pytesseract
        OCR_AVAILABLE = "pytesseract"
    except ImportError:
        OCR_AVAILABLE = None

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
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root)
        os.execve(VENV_PYTHON, [VENV_PYTHON] + sys.argv, env)
    else:
        print(f"❌ \033[33mPython executable not found in venv:\033[0m {VENV_PYTHON}")
        return False

def check_dependencies():
    """Check if required packages are installed - enhanced version"""
    required_packages = {
        'torch': 'torch',
        'transformers': 'transformers',
        'PIL': 'Pillow',
        'cv2': 'opencv-python',
        'numpy': 'numpy'
    }
    
    missing = []
    
    for import_name, package_name in required_packages.items():
        try:
            if import_name == 'PIL':
                import PIL
            elif import_name == 'cv2':
                import cv2
            else:
                __import__(import_name)
        except ImportError:
            missing.append(package_name)
    
    # Check LaMa packages
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
            print("⚠️  \033[33mNo LaMa libraries found - will use OpenCV inpainting\033[0m")
    
    if OCR_AVAILABLE:
        print(f"✅ \033[33mOCR available: {OCR_AVAILABLE}\033[0m")
    else:
        print("⚠️  \033[33mNo OCR library found - text watermark detection disabled\033[0m")
    
    if missing:
        print(f"❌ \033[33mMissing packages:\033[0m {', '.join(missing)}")
        print("\033[33mInstalling missing packages...\033[0m")
        
        try:
            for package in missing:
                print(f"Installing {package}...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print("✅ \033[33mPackages installed successfully\033[0m")
        except subprocess.CalledProcessError as e:
            print(f"❌ \033[33mFailed to install packages:\033[0m {e}")
    return True

def process_images_batch(input_paths, input_mode, src_path, suffix, detection_mode, inpaint_method):
    """Process images with enhanced detection methods and selected inpainting"""
    print("\n" * 2)
    print(f"\n\033[1;33m🧠 Processing\033[0m {len(input_paths)} \033[1;33mimage(s):\033[0m")
    print("=" * 50)
    print(f"\033[33m🔠 Suffix:\033[0m {suffix}")
    print(f"\033[33m🎯 Detection Mode:\033[0m {detection_mode}")
    print(f"\033[33m🎨 Inpaint Method:\033[0m {inpaint_method}")
    if input_mode == '1':
        print(f"\033[33m📥 Input folder:\033[0m {src_path}")
    print("\033[33m⚡ Memory-Safe Mode:\033[0m Enabled for M2 MacBook Air")
    print("=" * 50)
    print()
    print("\033[1;33m🤖 Enhanced AI Watermark Remover (Multi-Detection) 🤖 \033[0m\033[33mactivating...\033[0m")
    print()
    
    remover = EnhancedWatermarkRemover()
    success_count = 0
    error_count = 0
    error_messages = []
    output_paths = set()
    
    # Adjust batch size based on inpainting method
    if inpaint_method == "lama_ai":
        batch_size = 2  # Smaller batches for AI method
    elif detection_mode in ["text_watermarks", "combo_aggressive"]:
        batch_size = 3
    else:
        batch_size = 5
    
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
            output_dir = input_dir / "Output" / "NoWM"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_paths.add(output_dir)
            
            # Generate output filename
            input_stem = Path(input_path).stem
            output_name = f"{input_stem}_{suffix}.png"
            output_path = output_dir / output_name
            
            try:
                if remover.process_image(str(input_path), str(output_path),
                                       detection_mode, inpaint_method):
                    success_count += 1
                else:
                    error_count += 1
                    print(f"⚠️  \033[33mProcessing returned False for:\033[0m {file_name}")
                    error_messages.append(f"{file_name}: Processing returned False")
                    
            except Exception as e:
                print(f"❌ \033[33mException:\033[0m {file_name} - {str(e)}")
                error_count += 1
                error_messages.append(f"{file_name}: {str(e)}")
            
            print()
        
        # Memory cleanup between batches
        print(f"\033[33m🧹 Cleaning memory after batch {batch_idx + 1}...\033[0m")
        try:
            import torch
            gc.collect()
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
        except:
            pass
        print()
    
    # Final cleanup
    if hasattr(remover, 'ocr_reader') and remover.ocr_reader is not None:
        if OCR_AVAILABLE == "easyocr":
            del remover.ocr_reader
            remover.ocr_reader = None
    
    print("=" * 50)
    print(f"\033[1;33m🏁 Enhanced Batch Processing Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {success_count} \033[33mimage(s)\033[0m")
    print(f"❌ \033[33mFailed:\033[0m {error_count} \033[33mimage(s)\033[0m")
    
    if error_messages:
        print(f"\n\033[33mFirst few errors:\033[0m")
        for error in error_messages[:3]:
            print(f"  • {error}")
        if len(error_messages) > 3:
            print(f"  • ... and {len(error_messages) - 3} more")
    
    print("=" * 50)
    
    # Handle opening output folders
    if len(output_paths) == 1:
        output_path = list(output_paths)[0]
        djj.prompt_open_folder(output_path)
    elif len(output_paths) > 1:
        print(f"\033[33m📁 Created files in {len(output_paths)} different output folders.\033[0m")
        open_choice = djj.prompt_choice(
            "\033[33mOpen output folders?\033[0m\n1. Yes, open all\n2. Yes, open first one only\n3. No",
            ['1', '2', '3'],
            default='3'
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
    return

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
    src_path = None
    
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
    
    return valid_paths, input_mode, src_path

def get_detection_mode():
    """Get detection mode from user"""
    print("\033[1;33m🎯 Detection Mode Selection\033[0m")
    print()
    
    modes = {
        '1': ('pink_rectangles', 'Pink Rectangles (Original - Fast)', 'Your original pink rectangle detector'),
        '2': ('color_shapes', 'Multi-Color Shapes (Enhanced)', 'Rectangles, squares, circles, ovals, triangles - any color'),
        '3': ('text_watermarks', 'Text Watermarks', 'Detects text-based watermarks using OCR'),
        '4': ('semi_transparent', 'Semi-Transparent Watermarks (Social Media)', 'Logo+text overlays, optimized for social media'),
        '5': ('combo_smart', 'Smart Combo (Conservative)', 'Tries shapes first, then text if needed'),
        '6': ('combo_aggressive', 'Aggressive Combo', 'All detection methods combined')
    }
    
    # Check OCR availability for text modes
    if OCR_AVAILABLE is None:
        print("⚠️  \033[33mNote: Text detection unavailable (no OCR library)\033[0m")
        available_modes = ['1', '2', '4']
    else:
        available_modes = ['1', '2', '3', '4', '5', '6']
    
    print("\033[33mAvailable detection modes:\033[0m")
    for key in available_modes:
        mode_key, mode_name, mode_desc = modes[key]
        print(f"{key}. {mode_name}")
        print(f"   {mode_desc}")
    print()
    
    choice = djj.prompt_choice(
        "\033[33mSelect detection mode:\033[0m",
        available_modes,
        default='3'
    )
    
    selected_mode = modes[choice]
    print(f"✅ \033[33mSelected:\033[0m {selected_mode[1]}")
    print()
    
    return selected_mode[0]

def get_inpainting_method():
    """Get inpainting method selection from user"""
    print("\033[1;33m🎨 Inpainting Method Selection\033[0m")
    print()
    
    # Check LaMa availability
    lama_available = False
    lama_method = "opencv_inpaint"
    try:
        import lama_cleaner
        lama_available = True
        lama_method = "lama_cleaner"
    except ImportError:
        try:
            import simple_lama_inpainting
            lama_available = True
            lama_method = "simple_lama"
        except ImportError:
            pass
    
    print(f"🖥️  \033[33mAvailable methods:\033[0m")
    print("1. Telea (Fast, good for text)")
    print("2. Navier-Stokes (Slower, good for textures)")
    print("3. Hybrid (Combines Telea + Navier-Stokes)")
    
    if lama_available:
        print("4. LaMa AI (Highest quality - Slower, memory intensive)")
        available_choices = ['1', '2', '3', '4']
        default_choice = '3'
    else:
        print("4. LaMa AI (Not available)")
        available_choices = ['1', '2', '3']
        default_choice = '3'
    
    print()
    choice = djj.prompt_choice(
        "\033[33mSelect inpainting method:\033[0m",
        available_choices,
        default=default_choice
    )
    
    method_map = {
        '1': 'telea',
        '2': 'navier_stokes',
        '3': 'hybrid',
        '4': 'lama_ai'
    }
    
    selected_method = method_map[choice]
    print(f"✅ \033[33mSelected:\033[0m {selected_method}")
    print()
    
    return selected_method

class EnhancedWatermarkRemover:
    """Enhanced AI-powered watermark removal with multiple detection methods"""
    
    def __init__(self):
        self.lama_model = None
        self.device = "mps" if self._check_mps() else "cpu"
        self.lama_method = self._detect_lama_method()
        self.ocr_reader = None
        print(f"🖥️  \033[33mUsing device:\033[0m {self.device}")
        print(f"🎯 \033[33mInpainting method:\033[0m {self.lama_method}")
        if OCR_AVAILABLE:
            print(f"🔤 \033[33mOCR method:\033[0m {OCR_AVAILABLE}")
    
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
                return "opencv_inpaint"
    
    def _init_ocr(self):
        """Initialize OCR reader (lightweight, on-demand)"""
        if self.ocr_reader is not None or OCR_AVAILABLE is None:
            return
        
        try:
            if OCR_AVAILABLE == "easyocr":
                import easyocr
                self.ocr_reader = easyocr.Reader(['en'], gpu=False)
                print("✅ \033[33mEasyOCR initialized\033[0m")
            elif OCR_AVAILABLE == "pytesseract":
                import pytesseract
                self.ocr_reader = "pytesseract"
                print("✅ \033[33mPytesseract initialized\033[0m")
        except Exception as e:
            print(f"⚠️  \033[33mOCR initialization failed:\033[0m {e}")
            self.ocr_reader = None
    
    def load_lama_model(self):
        """Load LaMa inpainting model"""
        if self.lama_model is not None:
            return
            
        try:
            print("📥 \033[33mLoading LaMa inpainting model...\033[0m")
            
            if self.lama_method == "lama_cleaner":
                from lama_cleaner.model_manager import ModelManager
                
                self.lama_model = ModelManager(
                    name="lama",
                    device=self.device if self.device != "mps" else "cpu",
                    no_half=True
                )
                
            elif self.lama_method == "simple_lama":
                from simple_lama_inpainting import SimpleLama
                self.lama_model = SimpleLama()
                
            print(f"✅ \033[33mLaMa model loaded ({self.lama_method})\033[0m")
            
        except Exception as e:
            print(f"⚠️  \033[33mLaMa loading failed, using OpenCV fallback:\033[0m {str(e)}")
            self.lama_method = "opencv_inpaint"
            self.lama_model = "opencv"
    
    def unload_lama_model(self):
        """Unload LaMa model to free memory"""
        if self.lama_model is not None and self.lama_model != "opencv":
            del self.lama_model
            self.lama_model = None
            
            try:
                import torch
                gc.collect()
                if self.device == "mps":
                    torch.mps.empty_cache()
                elif torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
    
    @staticmethod
    def detect_pink_rectangles(image_path: str) -> List[List[int]]:
        """Original pink rectangle detector - with improved tolerance"""
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ Failed to load image: {image_path}")
            return []

        height, width = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Slightly narrower range to reduce false positives
        lower_pink = np.array([165, 110, 110])  # Increased from [160, 100, 100]
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
                # Increased minimum area to reduce false positives
                if area > 300:  # Was 200
                    print(f"🎯 Pink rectangle in {label} ({bw}x{bh})")
                    bboxes.append([abs_x1, abs_y1, abs_x2, abs_y2])

        return bboxes
    
    @staticmethod
    def detect_color_shapes(image_path: str) -> List[List[int]]:
        """Enhanced shape detector - with improved thresholds"""
        image = cv2.imread(image_path)
        if image is None:
            return []

        height, width = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        corner_regions = {
            "top-left": (0, 0, int(width * 0.35), int(height * 0.35)),
            "top-right": (int(width * 0.65), 0, width, int(height * 0.35)),
            "bottom-left": (0, int(height * 0.65), int(width * 0.35), height),
            "bottom-right": (int(width * 0.65), int(height * 0.65), width, height),
        }

        bboxes = []
        
        for label, (x1, y1, x2, y2) in corner_regions.items():
            corner_gray = gray[y1:y2, x1:x2]
            corner_color = image[y1:y2, x1:x2]
            
            # Adjusted edge detection thresholds for better precision
            edges = cv2.Canny(corner_gray, 60, 160, apertureSize=3)  # Was 50, 150
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for cnt in contours:
                area = cv2.contourArea(cnt)
                # Stricter area filtering
                if area < 300 or area > (width * height * 0.08):  # Was 200 and 0.1
                    continue
                
                bx, by, bw, bh = cv2.boundingRect(cnt)
                aspect_ratio = float(bw) / bh
                
                # Detect rectangles with narrower aspect ratio range
                if 0.4 <= aspect_ratio <= 2.5:  # Was 0.3 to 3.0
                    abs_x1, abs_y1 = x1 + bx, y1 + by
                    abs_x2, abs_y2 = abs_x1 + bw, abs_y1 + bh
                    print(f"🔷 Rectangle in {label} ({bw}x{bh})")
                    bboxes.append([abs_x1, abs_y1, abs_x2, abs_y2])
                    continue
                
                # Detect triangles
                epsilon = 0.02 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                
                if len(approx) == 3:
                    abs_x1, abs_y1 = x1 + bx, y1 + by
                    abs_x2, abs_y2 = abs_x1 + bw, abs_y1 + bh
                    print(f"🔺 Triangle in {label} ({bw}x{bh})")
                    bboxes.append([abs_x1, abs_y1, abs_x2, abs_y2])
        
        return EnhancedWatermarkRemover._remove_overlapping_bboxes(bboxes)
    
    def detect_text_watermarks(self, image_path: str) -> List[List[int]]:
        """Detect text-based watermarks using OCR - with higher confidence threshold"""
        if OCR_AVAILABLE is None:
            print("⚠️  OCR not available - skipping text detection")
            return []
        
        self._init_ocr()
        if self.ocr_reader is None:
            return []
        
        image = cv2.imread(image_path)
        if image is None:
            return []
        
        height, width = image.shape[:2]
        
        corner_regions = {
            "top-left": (0, 0, int(width * 0.4), int(height * 0.4)),
            "top-right": (int(width * 0.4), 0, width, int(height * 0.4)),
            "bottom-left": (0, int(height * 0.4), int(width * 0.4), height),
            "bottom-right": (int(width * 0.4), int(height * 0.4), width, height),
        }
        
        bboxes = []
        
        for label, (x1, y1, x2, y2) in corner_regions.items():
            corner = image[y1:y2, x1:x2]
            corner_pil = Image.fromarray(cv2.cvtColor(corner, cv2.COLOR_BGR2RGB))
            
            try:
                if OCR_AVAILABLE == "easyocr":
                    results = self.ocr_reader.readtext(np.array(corner_pil))
                    
                    for (bbox_coords, text, confidence) in results:
                        # Increased confidence threshold significantly
                        if confidence > 0.25:  # Was 0.3, now much stricter
                            points = np.array(bbox_coords, dtype=int)
                            # Increased padding for OCR detections
                            bx = max(0, np.min(points[:, 0]) - 5)  # Was 5
                            by = max(0, np.min(points[:, 1]) - 5)  # Was 5
                            bw = min(corner.shape[1] - bx, np.max(points[:, 0]) - bx + 40)  # Was 10
                            bh = min(corner.shape[0] - by, np.max(points[:, 1]) - by + 16)  # Was 10
                            
                            abs_x1, abs_y1 = x1 + bx, y1 + by
                            abs_x2, abs_y2 = abs_x1 + bw, abs_y1 + bh
                            
                            print(f"📝 Text \033[96m'{text.strip()}'\033[0m in {label} (conf: {confidence:.2f})")
                            bboxes.append([abs_x1, abs_y1, abs_x2, abs_y2])
                
                elif OCR_AVAILABLE == "pytesseract":
                    import pytesseract
                    
                    data = pytesseract.image_to_data(corner_pil, output_type=pytesseract.Output.DICT)
                    
                    for i in range(len(data['text'])):
                        confidence = int(data['conf'][i])
                        text = data['text'][i].strip()
                        
                        # Increased confidence threshold
                        if confidence > 30 and text:  # Was 30
                            # Increased padding
                            bx = max(0, data['left'][i] - 5)  # Was 5
                            by = max(0, data['top'][i] - 5)  # Was 5
                            bw = min(corner.shape[1] - bx, data['width'][i] + 40)  # Was 10
                            bh = min(corner.shape[0] - by, data['height'][i] + 16)  # Was 10
                            
                            abs_x1, abs_y1 = x1 + bx, y1 + by
                            abs_x2, abs_y2 = abs_x1 + bw, abs_y1 + bh
                            
                            print(f"📝 Text '{text}' in {label} (conf: {confidence})")
                            bboxes.append([abs_x1, abs_y1, abs_x2, abs_y2])
                            
            except Exception as e:
                print(f"⚠️  OCR failed for {label}: {e}")
                continue
        
        return self._remove_overlapping_bboxes(bboxes)
    
    @staticmethod
    def detect_semi_transparent(image_path: str) -> List[List[int]]:
        """Simple detection for semi-transparent watermarks - improved thresholds"""
        image = cv2.imread(image_path)
        if image is None:
            return []
        
        height, width = image.shape[:2]
        
        # Focus on bottom-right corner
        x1 = int(width * 0.7)
        y1 = int(height * 0.7)
        x2 = width
        y2 = height
        
        corner = image[y1:y2, x1:x2]
        corner_gray = cv2.cvtColor(corner, cv2.COLOR_BGR2GRAY)
        
        print(f"   🔍 Scanning bottom-right corner: {x2-x1}x{y2-y1} pixels")
        
        bboxes = []
        
        # Adjusted thresholds for better accuracy
        bright_mask = cv2.inRange(corner_gray, 185, 255)  # Was 180
        edges = cv2.Canny(corner_gray, 40, 110)  # Was 30, 100
        
        combined = cv2.bitwise_or(bright_mask, edges)
        
        # Slightly larger kernel for better text grouping
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))  # Was (2, 2)
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        print(f"   🔍 Found {len(contours)} potential regions")
        
        for i, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            bx, by, bw, bh = cv2.boundingRect(cnt)
            
            # More selective filtering
            if area > 80:  # Was 50, slightly higher threshold
                aspect_ratio = float(bw) / bh
                
                print(f"   📊 Region {i+1}: {bw}x{bh} (area: {area:.0f}, ratio: {aspect_ratio:.1f})")
                
                abs_x1, abs_y1 = x1 + bx, y1 + by
                abs_x2, abs_y2 = abs_x1 + bw, abs_y1 + bh
                
                bboxes.append([abs_x1, abs_y1, abs_x2, abs_y2])
        
        print(f"   ✅ Detected {len(bboxes)} regions total")
        
        if not bboxes:
            return []
        
        # Filter for likely watermarks
        filtered_bboxes = []
        for bbox in bboxes:
            x1_b, y1_b, x2_b, y2_b = bbox
            w, h = x2_b - x1_b, y2_b - y1_b
            area = w * h
            ratio = w / h if h > 0 else 0
            
            # More precise filtering
            if (ratio > 1.5 and area > 120 and area < 4500) or (ratio > 3.0 and area > 80):  # Was 100/5000 and 50
                filtered_bboxes.append(bbox)
                print(f"   🎯 Selected watermark candidate: {w}x{h} (ratio: {ratio:.1f})")
        
        return filtered_bboxes if filtered_bboxes else bboxes
        
    @staticmethod
    def _remove_overlapping_bboxes(bboxes: List[List[int]], overlap_threshold: float = 0.5) -> List[List[int]]:
        """Remove overlapping bounding boxes using simple IoU"""
        if len(bboxes) <= 1:
            return bboxes
        
        def calculate_iou(box1, box2):
            x1 = max(box1[0], box2[0])
            y1 = max(box1[1], box2[1])
            x2 = min(box1[2], box2[2])
            y2 = min(box1[3], box2[3])
            
            if x2 <= x1 or y2 <= y1:
                return 0.0
            
            intersection = (x2 - x1) * (y2 - y1)
            area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
            area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
            union = area1 + area2 - intersection
            
            return intersection / union if union > 0 else 0.0
        
        # Sort by area (largest first)
        bboxes = sorted(bboxes, key=lambda box: (box[2]-box[0])*(box[3]-box[1]), reverse=True)
        
        filtered_bboxes = []
        for box1 in bboxes:
            keep = True
            for box2 in filtered_bboxes:
                if calculate_iou(box1, box2) > overlap_threshold:
                    keep = False
                    break
            if keep:
                filtered_bboxes.append(box1)
        
        return filtered_bboxes
    
    def detect_watermarks(self, image_path: str, mode: str) -> List[List[int]]:
        """Main detection method - routes to appropriate detector(s)"""
        print(f"   🔍 Detection mode: {mode}")
        
        if mode == "pink_rectangles":
            return self.detect_pink_rectangles(image_path)
        
        elif mode == "color_shapes":
            return self.detect_color_shapes(image_path)
        
        elif mode == "text_watermarks":
            return self.detect_text_watermarks(image_path)
        
        elif mode == "semi_transparent":
            return self.detect_semi_transparent(image_path)
        
        elif mode == "combo_smart":
            # Try semi-transparent first, then shapes, then text
            print("   🎯 Phase 1: Semi-transparent detection...")
            bboxes = self.detect_semi_transparent(image_path)
            
            if len(bboxes) == 0:
                print("   🎯 Phase 2: Shape detection...")
                bboxes = self.detect_color_shapes(image_path)
                
                if len(bboxes) == 0:
                    print("   🎯 Phase 3: Text detection...")
                    bboxes = self.detect_text_watermarks(image_path)
                else:
                    print(f"   ✅ Found {len(bboxes)} shapes, skipping text detection")
            else:
                print(f"   ✅ Found {len(bboxes)} semi-transparent regions, skipping other methods")
            
            return bboxes
        
        elif mode == "combo_aggressive":
            # Run all detectors and combine results
            print("   🎯 Phase 1: Semi-transparent detection...")
            semi_bboxes = self.detect_semi_transparent(image_path)
            
            print("   🎯 Phase 2: Shape detection...")
            shape_bboxes = self.detect_color_shapes(image_path)
            
            print("   🎯 Phase 3: Text detection...")
            text_bboxes = self.detect_text_watermarks(image_path)
            
            # Combine and deduplicate
            all_bboxes = semi_bboxes + shape_bboxes + text_bboxes
            if all_bboxes:
                all_bboxes = self._remove_overlapping_bboxes(all_bboxes)
            
            return all_bboxes
        
        else:
            print(f"❌ Unknown detection mode: {mode}")
            return []
    
    @staticmethod
    def create_mask_from_bboxes(image_path: str, bboxes: List[List[int]]) -> Optional[str]:
        """Create mask from detected bounding boxes"""
        image = Image.open(image_path)
        width, height = image.size
        mask = np.zeros((height, width), dtype=np.uint8)

        if not bboxes:
            print("⚠️  No watermark detected. Skipping.")
            return None

        for i, bbox in enumerate(bboxes):
            x1, y1, x2, y2 = bbox
            pad = 10  # Increased padding from 8 for better coverage
            x1 = max(0, x1 - pad)
            y1 = max(0, y1 - pad)
            x2 = min(width, x2 + pad)
            y2 = min(height, y2 + pad)
            mask[y1:y2, x1:x2] = 255
            print(f"   🎯 Watermark region {i+1}: {x2-x1}px x {y2-y1}px")

        # Save mask to temp file
        mask_path = os.path.join(tempfile.gettempdir(), f"mask_{int(time.time())}.png")
        cv2.imwrite(mask_path, mask)
        print(f"   📊 Mask created: {os.path.basename(mask_path)}")
        return mask_path
    
    def remove_watermark(self, image_path: str, mask_path: str, output_path: str,
                        inpaint_method: str = "telea") -> bool:
        """Remove watermark using selected inpainting method"""
        try:
            print(f"   🎨 Using {inpaint_method} inpainting...")
            
            # Load images
            if inpaint_method == "lama_ai":
                image = Image.open(image_path).convert("RGB")
                mask = Image.open(mask_path).convert("L")
            else:
                image = cv2.imread(image_path)
                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            
            if image is None or mask is None:
                print("   ❌ Failed to load image or mask")
                return False
            
            # Apply inpainting based on method
            if inpaint_method == "lama_ai":
                # AI-powered LaMa inpainting
                self.load_lama_model()
                
                if self.lama_method in ["lama_cleaner"]:
                    image_np = np.array(image)
                    mask_np = np.array(mask)
                    mask_np = (mask_np > 128).astype(np.uint8) * 255
                    
                    result_np = self.lama_model(image_np, mask_np)
                    result = Image.fromarray(result_np.astype(np.uint8))
                    
                elif self.lama_method == "simple_lama":
                    result = self.lama_model(image, mask)
                    
                else:  # opencv fallback
                    print("   ⚠️  LaMa unavailable, using Telea")
                    return self.remove_watermark(image_path, mask_path, output_path, "telea")
                
                result.save(output_path, quality=95, optimize=True)
                self.unload_lama_model()
                
            elif inpaint_method == "telea":
                mask = (mask > 128).astype(np.uint8) * 255
                result = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
                cv2.imwrite(output_path, result, [cv2.IMWRITE_PNG_COMPRESSION, 9])
                
            elif inpaint_method == "navier_stokes":
                mask = (mask > 128).astype(np.uint8) * 255
                result = cv2.inpaint(image, mask, 3, cv2.INPAINT_NS)
                cv2.imwrite(output_path, result, [cv2.IMWRITE_PNG_COMPRESSION, 9])
                
            elif inpaint_method == "hybrid":
                mask = (mask > 128).astype(np.uint8) * 255
                result1 = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
                result2 = cv2.inpaint(image, mask, 3, cv2.INPAINT_NS)
                result = cv2.addWeighted(result1, 0.6, result2, 0.4, 0)
                cv2.imwrite(output_path, result, [cv2.IMWRITE_PNG_COMPRESSION, 9])
                
            else:
                print(f"   ⚠️  Unknown method '{inpaint_method}', using Telea")
                mask = (mask > 128).astype(np.uint8) * 255
                result = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
                cv2.imwrite(output_path, result, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            
            return True
            
        except Exception as e:
            print(f"   ❌ Inpainting failed: {e}")
            return False
    
    def process_image(self, input_path: str, output_path: str, detection_mode: str,
                     inpaint_method: str = "telea") -> bool:
        """Process a single image for watermark removal"""
        try:
            file_name = os.path.basename(input_path)
            print(f"🖼️  \033[33mProcessing:\033[0m {file_name}")
            
            # Step 1: Detect watermarks
            print("   Step 1: Detecting watermark regions...")
            bboxes = self.detect_watermarks(input_path, detection_mode)
            
            if not bboxes:
                print("   ⚠️  No watermarks detected - copying original")
                import shutil
                shutil.copy2(input_path, output_path)
                return True
            
            # Step 2: Create mask
            print("   Step 2: Creating precise masks...")
            mask_path = self.create_mask_from_bboxes(input_path, bboxes)
            if not mask_path:
                return False
            
            # Step 3: Remove watermark
            print("   Step 3: Removing watermark with inpainting...")
            success = self.remove_watermark(input_path, mask_path, output_path, inpaint_method)
            
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
        print("\033[1;33mEnhanced AI Watermark Remover V2 (Multi-Detection + Inpainting)\033[0m")
        print("🔹 Pink Rectangles (Original)")
        print("🔷 Multi-Color Shapes (Rectangles + Triangles)")
        print("📝 Text Watermarks (OCR-based)")
        print("🌫️  Semi-Transparent Overlays (Social Media)")
        print("🎨 Telea | Navier-Stokes | Hybrid | LaMa AI")
        print("⚡ Optimized for M2 MacBook Air 8GB")
        print("\033[92m" + "=" * 50 + "\033[0m")
        print()
        
        try:
            # Get input files
            input_files, input_mode, src_path = get_valid_inputs()
            
            # Get detection mode
            detection_mode = get_detection_mode()
            
            # Get inpainting method
            inpaint_method = get_inpainting_method()
            
            # Get suffix
            suffix = djj.get_string_input(
                "\033[33mEnter suffix (default 'NoWM'):\033[0m\n > ",
                default="NoWM"
            )
            
            os.system('clear')
            
            # Process all images
            process_images_batch(input_files, input_mode, src_path, suffix,
                               detection_mode, inpaint_method)
            
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
    