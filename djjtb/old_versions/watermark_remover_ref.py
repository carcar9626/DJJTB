#!/usr/bin/env python3
"""
Reference-Based Watermark Remover for DJJTB - FIXED VERSION
Uses a reference watermark image to detect and remove similar watermarks from batch images
Now with proper LaMa + OpenCV mode selection
Version: 1.1 - Fixed
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
import tempfile
import shutil

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

# Environment and model paths (same as your original)
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
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root)
        os.execve(VENV_PYTHON, [VENV_PYTHON] + sys.argv, env)
    else:
        print(f"❌ \033[33mPython executable not found in venv:\033[0m {VENV_PYTHON}")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = {
        'cv2': 'opencv-python',
        'numpy': 'numpy',
        'PIL': 'Pillow'
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
            return False
    
    return True

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
        path = path.strip().strip('\'"')
        path_obj = Path(path)
        
        if path_obj.is_file() and path_obj.suffix.lower() in SUPPORTED_EXTS:
            images.append(str(path_obj))
        elif path_obj.is_dir():
            dir_images = collect_images_from_folder(path)
            images.extend(dir_images)
    
    return sorted(images, key=str.lower)

def get_reference_watermark():
    """Get the reference watermark image from user"""
    print("\033[1;33m🎯 Reference Watermark Selection\033[0m")
    print("\033[33mPlease provide the reference watermark image to remove.\033[0m")
    print("\033[33mBest format: PNG with transparent background\033[0m")
    print("\033[33m(JPG with solid background also works)\033[0m")
    print()
    
    ref_path = djj.get_path_input("Enter reference watermark image path")
    
    # Validate the reference image
    if not Path(ref_path).suffix.lower() in SUPPORTED_EXTS:
        print("❌ \033[33mUnsupported image format\033[0m")
        return None
    
    try:
        # Test if we can load the image
        test_img = cv2.imread(ref_path)
        if test_img is None:
            print("❌ \033[33mCannot load reference image\033[0m")
            return None
        
        height, width = test_img.shape[:2]
        print(f"✅ \033[33mReference image loaded:\033[0m {width}x{height}px")
        print(f"   📁 {os.path.basename(ref_path)}")
        
        # Show preview option
        preview_choice = djj.prompt_choice(
            "\033[33mPreview reference image?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        )
        
        if preview_choice == '1':
            subprocess.run(['open', ref_path])
        
        return ref_path
        
    except Exception as e:
        print(f"❌ \033[33mError loading reference image:\033[0m {e}")
        return None

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
    
    print(f"\033[33m✅ Found\033[0m {len(valid_paths)} \033[33msupported image(s)\033[0m")
    return valid_paths, input_mode, src_path

class ReferenceWatermarkRemover:
    """Reference-based watermark removal using template matching and inpainting"""
    
    def __init__(self):
        self.device = "mps" if self._check_mps() else "cpu"
        self.reference_template = None
        self.reference_alpha = None
        self.lama_model = None
        self.lama_method = self._detect_lama_method()
        self.lama_available = self.lama_method in ["lama_cleaner", "simple_lama"]
        print(f"🖥️  \033[33mUsing device:\033[0m {self.device}")
        print(f"🎯 \033[33mInpainting method available:\033[0m {self.lama_method}")
        print(f"🔍 \033[33mDebug: lama_method={self.lama_method}, lama_available={self.lama_available}\033[0m")
    
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
    
    def _check_mps(self):
        """Check if MPS is available on M1/M2 Macs"""
        try:
            import torch
            return torch.backends.mps.is_available()
        except:
            return False
    
    def load_reference_watermark(self, ref_path: str):
        """Load and prepare the reference watermark for template matching"""
        print(f"📥 \033[33mLoading reference watermark:\033[0m {os.path.basename(ref_path)}")
        
        # Load with PIL to handle transparency properly
        ref_pil = Image.open(ref_path).convert("RGBA")
        ref_rgba = np.array(ref_pil)
        
        # Separate RGB and alpha channels
        self.reference_template = cv2.cvtColor(ref_rgba[:, :, :3], cv2.COLOR_RGB2BGR)
        
        # Handle alpha channel (transparency)
        if ref_rgba.shape[2] == 4:
            self.reference_alpha = ref_rgba[:, :, 3]
            print("   ✅ \033[33mTransparency channel detected\033[0m")
        else:
            self.reference_alpha = np.full(ref_rgba.shape[:2], 255, dtype=np.uint8)
        
        height, width = self.reference_template.shape[:2]
        print(f"   📊 \033[33mReference size:\033[0m {width}x{height}px")
        
        return True
    
    def find_watermark_locations(self, image_path: str,
                                scales: List[float] = [0.5, 0.7, 0.8, 1.0, 1.2, 1.5],
                                threshold: float = 0.7) -> List[dict]:
        """
        Find watermark locations using multi-scale template matching
        Returns list of matches with their confidence, location, and scale
        """
        print(f"   🔍 Scanning for watermarks at {len(scales)} scales...")
        
        target_image = cv2.imread(image_path)
        if target_image is None:
            print(f"   ❌ Cannot load target image: {image_path}")
            return []
        
        target_gray = cv2.cvtColor(target_image, cv2.COLOR_BGR2GRAY)
        ref_gray = cv2.cvtColor(self.reference_template, cv2.COLOR_BGR2GRAY)
        
        matches = []
        
        for scale in scales:
            # Resize reference template
            scaled_width = int(self.reference_template.shape[1] * scale)
            scaled_height = int(self.reference_template.shape[0] * scale)
            
            if scaled_width <= 0 or scaled_height <= 0:
                continue
            if scaled_width >= target_image.shape[1] or scaled_height >= target_image.shape[0]:
                continue
            
            scaled_ref = cv2.resize(ref_gray, (scaled_width, scaled_height))
            scaled_alpha = cv2.resize(self.reference_alpha, (scaled_width, scaled_height))
            
            # Template matching with different methods for robustness
            methods = [
                cv2.TM_CCOEFF_NORMED,
                cv2.TM_CCORR_NORMED,
                cv2.TM_SQDIFF_NORMED
            ]
            
            for method_idx, method in enumerate(methods):
                try:
                    # Use masked template matching if alpha channel is meaningful
                    if np.mean(scaled_alpha) < 240:  # Has some transparency
                        mask = (scaled_alpha > 128).astype(np.uint8) * 255
                        result = cv2.matchTemplate(target_gray, scaled_ref, method, mask=mask)
                    else:
                        result = cv2.matchTemplate(target_gray, scaled_ref, method)
                    
                    # Find peaks in the result
                    if method == cv2.TM_SQDIFF_NORMED:
                        # For SQDIFF, lower values are better
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                        best_val = min_val
                        best_loc = min_loc
                        confidence = 1.0 - best_val  # Convert to higher-is-better
                    else:
                        # For other methods, higher values are better
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                        best_val = max_val
                        best_loc = max_loc
                        confidence = best_val
                    
                    # Apply threshold
                    if confidence >= threshold:
                        match_info = {
                            'confidence': confidence,
                            'location': best_loc,
                            'scale': scale,
                            'size': (scaled_width, scaled_height),
                            'method': method_idx,
                            'bbox': [best_loc[0], best_loc[1],
                                   best_loc[0] + scaled_width, best_loc[1] + scaled_height]
                        }
                        matches.append(match_info)
                        print(f"   🎯 Match found: scale={scale:.1f}, conf={confidence:.3f}, method={method_idx}")
                        
                except Exception as e:
                    print(f"   ⚠️  Template matching error at scale {scale}: {e}")
                    continue
        
        # Remove duplicate/overlapping matches
        matches = self._filter_overlapping_matches(matches)
        print(f"   ✅ Found {len(matches)} unique watermark location(s)")
        
        return matches
    
    def _filter_overlapping_matches(self, matches: List[dict], overlap_threshold: float = 0.5) -> List[dict]:
        """Remove overlapping matches, keeping the ones with highest confidence"""
        if len(matches) <= 1:
            return matches
        
        # Sort by confidence (descending)
        matches = sorted(matches, key=lambda x: x['confidence'], reverse=True)
        
        def calculate_iou(bbox1, bbox2):
            x1 = max(bbox1[0], bbox2[0])
            y1 = max(bbox1[1], bbox2[1])
            x2 = min(bbox1[2], bbox2[2])
            y2 = min(bbox1[3], bbox2[3])
            
            if x2 <= x1 or y2 <= y1:
                return 0.0
            
            intersection = (x2 - x1) * (y2 - y1)
            area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
            area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
            union = area1 + area2 - intersection
            
            return intersection / union if union > 0 else 0.0
        
        filtered_matches = []
        for match in matches:
            keep = True
            for existing_match in filtered_matches:
                if calculate_iou(match['bbox'], existing_match['bbox']) > overlap_threshold:
                    keep = False
                    break
            if keep:
                filtered_matches.append(match)
        
        return filtered_matches
    
    def create_precise_mask(self, image_path: str, matches: List[dict],
                          padding: int = 5, save_mask_path: str = None) -> Optional[str]:
        """Create precise mask based on detected watermark locations and reference alpha"""
        if not matches:
            print("   ⚠️  No matches provided for mask creation")
            return None
        
        target_image = cv2.imread(image_path)
        height, width = target_image.shape[:2]
        mask = np.zeros((height, width), dtype=np.uint8)
        
        print(f"   🎨 Creating precise mask with {len(matches)} region(s)...")
        
        for i, match in enumerate(matches):
            x, y = match['location']
            scale = match['scale']
            match_w, match_h = match['size']
            
            # FIXED: Ensure exact dimensions match the detection
            try:
                # Scale the alpha mask to match the detected watermark size EXACTLY
                scaled_alpha = cv2.resize(self.reference_alpha, (match_w, match_h), interpolation=cv2.INTER_NEAREST)
                
                # Verify dimensions match
                if scaled_alpha.shape != (match_h, match_w):
                    print(f"   ⚠️  Alpha resize mismatch: expected {match_h}x{match_w}, got {scaled_alpha.shape}")
                    # Fallback: create simple rectangular mask
                    scaled_alpha = np.full((match_h, match_w), 255, dtype=np.uint8)
                
                # Apply padding
                x1 = max(0, x - padding)
                y1 = max(0, y - padding)
                x2 = min(width, x + match_w + padding)
                y2 = min(height, y + match_h + padding)
                
                # SIMPLIFIED: Just fill the rectangular region
                # Calculate the actual region that fits in the image
                region_x1 = max(0, x)
                region_y1 = max(0, y)
                region_x2 = min(width, x + match_w)
                region_y2 = min(height, y + match_h)
                
                # Only proceed if we have a valid region
                if region_x2 > region_x1 and region_y2 > region_y1:
                    # Calculate corresponding alpha region
                    alpha_w = region_x2 - region_x1
                    alpha_h = region_y2 - region_y1
                    
                    # Extract the corresponding part of scaled alpha
                    alpha_x_start = region_x1 - x if region_x1 >= x else 0
                    alpha_y_start = region_y1 - y if region_y1 >= y else 0
                    alpha_x_end = alpha_x_start + alpha_w
                    alpha_y_end = alpha_y_start + alpha_h
                    
                    # Ensure we don't exceed alpha bounds
                    alpha_x_end = min(alpha_x_end, scaled_alpha.shape[1])
                    alpha_y_end = min(alpha_y_end, scaled_alpha.shape[0])
                    
                    if (alpha_x_end > alpha_x_start and alpha_y_end > alpha_y_start):
                        alpha_section = scaled_alpha[alpha_y_start:alpha_y_end, alpha_x_start:alpha_x_end]
                        
                        # Apply alpha mask (only non-transparent areas)
                        alpha_mask = (alpha_section > 128).astype(np.uint8) * 255
                        
                        # Update the main mask
                        mask_y1 = region_y1
                        mask_y2 = region_y1 + alpha_mask.shape[0]
                        mask_x1 = region_x1
                        mask_x2 = region_x1 + alpha_mask.shape[1]
                        
                        # Apply to main mask with bounds checking
                        if (mask_x2 <= width and mask_y2 <= height and
                            mask_x1 >= 0 and mask_y1 >= 0):
                            mask[mask_y1:mask_y2, mask_x1:mask_x2] = np.maximum(
                                mask[mask_y1:mask_y2, mask_x1:mask_x2], alpha_mask
                            )
                        
                        print(f"   📍 Region {i+1}: {match_w}x{match_h}px at ({x}, {y}), scale={scale:.2f} ✅")
                    else:
                        print(f"   ⚠️  Region {i+1}: Invalid alpha bounds, skipping")
                else:
                    print(f"   ⚠️  Region {i+1}: Invalid region bounds, skipping")
                    
            except Exception as e:
                print(f"   ❌ Error processing region {i+1}: {e}")
                # Fallback: create simple rectangle
                x1 = max(0, x)
                y1 = max(0, y)
                x2 = min(width, x + match_w)
                y2 = min(height, y + match_h)
                if x2 > x1 and y2 > y1:
                    mask[y1:y2, x1:x2] = 255
                    print(f"   📍 Region {i+1}: {match_w}x{match_h}px at ({x}, {y}), fallback rectangle")
        
        # Save mask
        if save_mask_path:
            mask_path = save_mask_path
        else:
            mask_path = os.path.join(tempfile.gettempdir(), f"ref_mask_{int(time.time())}.png")
        
        cv2.imwrite(mask_path, mask)
        print(f"   💾 Mask saved: {os.path.basename(mask_path)}")
        
        return mask_path
    
    def load_lama_model(self):
        """Load LaMa inpainting model (from original script)"""
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

    def apply_inpainting(self, image_path: str, mask_path: str, output_path: str,
                        method: str = "telea") -> bool:
        """Apply inpainting to remove watermark - includes both AI and OpenCV methods"""
        try:
            print(f"   🎨 Applying {method} inpainting...")
            
            # Load image and mask
            if method.startswith("lama"):
                # Use PIL for LaMa methods
                image = Image.open(image_path).convert("RGB")
                mask = Image.open(mask_path).convert("L")
            else:
                # Use OpenCV for traditional methods
                image = cv2.imread(image_path)
                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            
            if image is None or mask is None:
                print("   ❌ Failed to load image or mask")
                return False
            
            # Apply inpainting based on method choice
            if method.lower() == "lama_ai":
                # AI-powered LaMa inpainting
                self.load_lama_model()
                
                if self.lama_method in ["lama_cleaner"]:
                    # Convert PIL to numpy arrays
                    image_np = np.array(image)
                    mask_np = np.array(mask)
                    
                    # Ensure mask is binary
                    mask_np = (mask_np > 128).astype(np.uint8) * 255
                    
                    # Process with lama_cleaner
                    result_np = self.lama_model(image_np, mask_np)
                    result = Image.fromarray(result_np.astype(np.uint8))
                    
                elif self.lama_method == "simple_lama":
                    # Use simple_lama_inpainting
                    result = self.lama_model(image, mask)
                    
                else:  # opencv fallback
                    print("   ⚠️  LaMa unavailable, using OpenCV Telea")
                    return self.apply_inpainting(image_path, mask_path, output_path, "telea")
                
                # Save result with high quality
                result.save(output_path, quality=95, optimize=True)
                
                # Unload model to free memory
                self.unload_lama_model()
                
            elif method.lower() == "telea":
                # Ensure mask is binary
                mask = (mask > 128).astype(np.uint8) * 255
                result = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
                cv2.imwrite(output_path, result)
                
            elif method.lower() == "navier_stokes" or method.lower() == "ns":
                mask = (mask > 128).astype(np.uint8) * 255
                result = cv2.inpaint(image, mask, 3, cv2.INPAINT_NS)
                cv2.imwrite(output_path, result)
                
            elif method.lower() == "hybrid":
                # Combine both OpenCV methods for better results
                mask = (mask > 128).astype(np.uint8) * 255
                result1 = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
                result2 = cv2.inpaint(image, mask, 3, cv2.INPAINT_NS)
                result = cv2.addWeighted(result1, 0.6, result2, 0.4, 0)
                cv2.imwrite(output_path, result)
                
            else:
                print(f"   ⚠️  Unknown method '{method}', using Telea")
                mask = (mask > 128).astype(np.uint8) * 255
                result = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
                cv2.imwrite(output_path, result)
            
            return True
            
        except Exception as e:
            print(f"   ❌ Inpainting failed: {e}")
            return False
    
    def process_image(self, input_path: str, output_path: str, mask_output_path: str = None,
                     threshold: float = 0.7, inpaint_method: str = "telea") -> bool:
        """Process a single image for watermark removal"""
        try:
            file_name = os.path.basename(input_path)
            print(f"🖼️  \033[33mProcessing:\033[0m {file_name}")
            
            # Step 1: Find watermark locations
            print("   Step 1: Searching for watermarks...")
            try:
                matches = self.find_watermark_locations(input_path, threshold=threshold)
            except Exception as e:
                print(f"   ❌ Watermark detection failed: {e}")
                return False
            
            if not matches:
                print("   ⚠️  No watermarks detected - copying original")
                try:
                    shutil.copy2(input_path, output_path)
                    return True
                except Exception as e:
                    print(f"   ❌ Failed to copy original file: {e}")
                    return False
            
            # Step 2: Create precise mask
            print("   Step 2: Creating precise mask...")
            try:
                mask_path = self.create_precise_mask(input_path, matches,
                                                   save_mask_path=mask_output_path)
                if not mask_path:
                    print("   ❌ Mask creation failed")
                    return False
            except Exception as e:
                print(f"   ❌ Mask creation failed: {e}")
                return False
            
            # Step 3: Apply inpainting
            print("   Step 3: Removing watermark with inpainting...")
            try:
                success = self.apply_inpainting(input_path, mask_path, output_path, inpaint_method)
            except Exception as e:
                print(f"   ❌ Inpainting failed: {e}")
                success = False
            
            # Cleanup temporary mask if not requested to keep
            try:
                if mask_output_path is None and os.path.exists(mask_path):
                    os.remove(mask_path)
            except Exception as e:
                print(f"   ⚠️  Failed to cleanup temp mask: {e}")
            
            if success:
                print(f"✅ \033[33mCompleted:\033[0m {file_name}")
                return True
            else:
                print(f"❌ \033[33mInpainting failed for:\033[0m {file_name}")
                return False
                
        except Exception as e:
            print(f"❌ \033[33mUnexpected error processing\033[0m {os.path.basename(input_path)}: {str(e)}")
            return False

def get_processing_options():
    """Get processing options from user"""
    print("\033[1;33m⚙️  Processing Options\033[0m")
    
    # Template matching threshold
    threshold = djj.get_float_input(
        "\033[33mTemplate matching threshold (0.5-0.9, default 0.7):\033[0m",
        min_val=0.3, max_val=0.95
    ) if djj.prompt_choice(
        "\033[33mAdjust detection sensitivity?\033[0m\n1. Use default (0.7)\n2. Custom threshold",
        ['1', '2'], default='1'
    ) == '2' else 0.7
    
    # Check LaMa availability first
    try:
        test_remover = ReferenceWatermarkRemover()
        lama_available = test_remover.lama_available
        lama_method = test_remover.lama_method
        del test_remover  # Clean up
    except Exception as e:
        lama_available = False
        lama_method = "opencv_inpaint"
    
    print(f"🎯 \033[33mAvailable inpainting methods:\033[0m")
    print(f"🖥  \033[33mUsing device:\033[0m mps")
    print(f"🎯 \033[33mInpainting method available:\033[0m {lama_method}")
    print(f"🔍 \033[33mDebug: lama_method={lama_method}, lama_available={lama_available}\033[0m")
    
    # FIXED: First choose removal mode
    print("\033[33mRemoval Mode:\033[0m")
    print("1. OpenCV (Telea/Navier-Stokes - Fast)")
    if lama_available:
        print("2. LaMa AI (Highest quality - Slower)")
        removal_mode = djj.prompt_choice(
            "\033[33mSelect removal mode:\033[0m",
            ['1', '2'], default='2'
        )
    else:
        print("2. LaMa AI (Not available)")
        removal_mode = djj.prompt_choice(
            "\033[33mSelect removal mode:\033[0m",
            ['1'], default='1'
        )
    
    if removal_mode == '1':
        # OpenCV methods
        print("   1. Telea (fast, good for text)")
        print("   2. Navier-Stokes (slower, good for textures)")
        print("   3. Hybrid (combines both OpenCV methods)")
        
        opencv_choice = djj.prompt_choice(
            "\033[33mInpainting method:\033[0m",
            ['1', '2', '3'], default='1'
        )
        
        method_map = {'1': 'telea', '2': 'navier_stokes', '3': 'hybrid'}
        inpaint_method = method_map[opencv_choice]
        
    else:
        # LaMa AI method
        inpaint_method = "lama_ai"
    
    # Keep masks option
    keep_masks = djj.prompt_choice(
        "\033[33mSave mask files?\033[0m\n1. Yes (save to Output/Masks)\n2. No (temporary only)",
        ['1', '2'], default='2'
    ) == '1'
    
    return threshold, inpaint_method, keep_masks

def process_images_batch(input_paths, reference_path, input_mode, src_path, suffix,
                        threshold, inpaint_method, keep_masks):
    """Process images with reference-based watermark removal"""
    print("\n" * 2)
    print(f"\n\033[1;33m🧠 Processing\033[0m {len(input_paths)} \033[1;33mimage(s):\033[0m")
    print("=" * 60)
    print(f"\033[33m🎯 Reference:\033[0m {os.path.basename(reference_path)}")
    print(f"\033[33m🔠 Suffix:\033[0m {suffix}")
    print(f"\033[33m📊 Threshold:\033[0m {threshold}")
    print(f"\033[33m🎨 Method:\033[0m {inpaint_method}")
    print(f"\033[33m💾 Keep Masks:\033[0m {'Yes' if keep_masks else 'No'}")
    if input_mode == '1':
        print(f"\033[33m📥 Input folder:\033[0m {src_path}")
    print("=" * 60)
    print()
    
    # Initialize the remover
    remover = ReferenceWatermarkRemover()
    if not remover.load_reference_watermark(reference_path):
        print("❌ Failed to load reference watermark")
        return
    
    success_count = 0
    error_count = 0
    error_messages = []
    output_paths = set()
    mask_paths = set()
    
    for i, input_path in enumerate(input_paths):
        file_name = os.path.basename(input_path)
        print(f"\033[33m[{i+1}/{len(input_paths)}]\033[0m")
        
        # Create output paths
        input_dir = Path(input_path).parent
        output_dir = input_dir / "Output" / "NoWM"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_paths.add(output_dir)
        
        if keep_masks:
            mask_dir = input_dir / "Output" / "Masks"
            mask_dir.mkdir(parents=True, exist_ok=True)
            mask_paths.add(mask_dir)
        
        # Generate output filenames
        input_stem = Path(input_path).stem
        output_name = f"{input_stem}_{suffix}.png"
        output_path = output_dir / output_name
        
        mask_output_path = None
        if keep_masks:
            mask_name = f"{input_stem}_mask.png"
            mask_output_path = str(mask_dir / mask_name)
        
        try:
            if remover.process_image(str(input_path), str(output_path), mask_output_path,
                                   threshold, inpaint_method):
                success_count += 1
            else:
                error_count += 1
                print(f"⚠️  \033[33mProcessing returned False for:\033[0m {file_name}")
                error_messages.append(f"{file_name}: Processing returned False (check individual steps)")
                
        except Exception as e:
            print(f"❌ \033[33mException:\033[0m {file_name} - {str(e)}")
            error_count += 1
            error_messages.append(f"{file_name}: Exception - {str(e)}")
        
        print()  # Add spacing between files
    
    print("=" * 60)
    print(f"\033[1;33m🏁 Reference-Based Processing Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {success_count} \033[33mimage(s)\033[0m")
    print(f"❌ \033[33mFailed:\033[0m {error_count} \033[33mimage(s)\033[0m")
    
    # Show first few errors if any
    if error_messages:
        print(f"\n\033[33mFirst few errors:\033[0m")
        for error in error_messages[:3]:
            print(f"  • {error}")
        if len(error_messages) > 3:
            print(f"  • ... and {len(error_messages) - 3} more")
    
    print("=" * 60)
    
    # Handle opening output folders
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
    
    # Also mention mask folders if they were created
    if keep_masks and mask_paths:
        print(f"\033[33m🎭 Mask files saved in {len(mask_paths)} folder(s)\033[0m")

def main():
    os.system('clear')
    
    # Ensure we're in the right environment first
    if not ensure_venv_and_run():
        return
    
    # Check dependencies and install if missing
    if not check_dependencies():
        print("\n\033[33mFailed to install required dependencies\033[0m")
        return
    
    while True:
        print()
        print("\033[92m" + "=" * 70 + "\033[0m")
        print("\033[1;33mReference-Based Watermark Remover for DJJTB - FIXED\033[0m")
        print("🎯 Template Matching with Multi-Scale Detection")
        print("🔍 Handles Different Sizes, Locations & Opacities")
        print("🎨 LaMa AI + OpenCV Inpainting (Telea, Navier-Stokes, Hybrid)")
        print("💾 Optional Mask File Export for ChaiNNer Integration")
        print("⚡ Optimized for M2 MacBook Air 8GB RAM")
        print("\033[92m" + "=" * 70 + "\033[0m")
        print()
        
        try:
            # Step 1: Get reference watermark
            print("\033[1;33m📋 STEP 1: Reference Watermark\033[0m")
            reference_path = get_reference_watermark()
            if not reference_path:
                print("❌ Invalid reference watermark. Exiting.")
                break
            
            os.system('clear')
            print(f"✅ \033[33mReference loaded:\033[0m {os.path.basename(reference_path)}")
            print()
            
            # Step 2: Get input files
            print("\033[1;33m📋 STEP 2: Input Images\033[0m")
            input_files, input_mode, src_path = get_valid_inputs()
            
            os.system('clear')
            print(f"✅ \033[33mReference:\033[0m {os.path.basename(reference_path)}")
            print(f"✅ \033[33mInput files:\033[0m {len(input_files)} images")
            print()
            
            # Step 3: Get processing options
            print("\033[1;33m📋 STEP 3: Processing Options\033[0m")
            threshold, inpaint_method, keep_masks = get_processing_options()
            
            # Step 4: Get suffix
            suffix = djj.get_string_input(
                "\033[33mEnter output suffix (default 'NoWM'):\033[0m\n > ",
                default="NoWM"
            )
            
            os.system('clear')
            
            # Process all images
            process_images_batch(input_files, reference_path, input_mode, src_path,
                               suffix, threshold, inpaint_method, keep_masks)
            
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