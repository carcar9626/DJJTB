#!/usr/bin/env python3
"""
Unified Watermark Remover for DJJTB - COMBINED VERSION
Combines Reference-Based + OCR Auto-Detection approaches
Mode 1: Reference-Based (solid watermarks) - Template matching + LaMa
Mode 2: OCR Auto-Detect (text watermarks) - OCR detection + LaMa/OpenCV options
Version: 2.0 - Unified
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
        return self._remove_overlapping_bboxes_ocr(bboxes)
    
def _remove_overlapping_bboxes_ocr(self, bboxes: List[List[int]], overlap_threshold: float = 0.5) -> List[List[int]]:
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
    
def create_mask_from_ocr_bboxes(self, image_path: str, bboxes: List[List[int]],
                                  save_mask_path: str = None) -> Optional[str]:
        """Create mask from detected bounding boxes"""
        image = Image.open(image_path)
        width, height = image.size
        mask = np.zeros((height, width), dtype=np.uint8)

        if not bboxes:
            print("⚠️  No watermark detected. Skipping.")
            return None

        for i, bbox in enumerate(bboxes):
            x1, y1, x2, y2 = bbox
            pad = 8  # Padding for better removal
            x1 = max(0, x1 - pad)
            y1 = max(0, y1 - pad)
            x2 = min(width, x2 + pad)
            y2 = min(height, y2 + pad)
            mask[y1:y2, x1:x2] = 255
            print(f"   🎯 Watermark region {i+1}: {x2-x1}px x {y2-y1}px")

        # Save mask to temp file
        if save_mask_path:
            mask_path = save_mask_path
        else:
            mask_path = os.path.join(tempfile.gettempdir(), f"ocr_mask_{int(time.time())}.png")
        
        cv2.imwrite(mask_path, mask)
        print(f"   📊 Mask created: {os.path.basename(mask_path)}")
        return mask_path
                
# ===== SHARED INPAINTING METHODS =====
    
    def apply_inpainting(self, image_path: str, mask_path: str, output_path: str,
                        method: str = "lama_ai") -> bool:
        """Apply inpainting to remove watermark - supports both LaMa and OpenCV methods"""
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
    
    # ===== UNIFIED PROCESSING METHODS =====
    
    def process_image_reference_mode(self, input_path: str, output_path: str, mask_output_path: str = None,
                                   threshold: float = 0.7, inpaint_method: str = "lama_ai") -> bool:
        """Process a single image using reference-based detection"""
        try:
            file_name = os.path.basename(input_path)
            print(f"🖼️  \033[33mProcessing (Reference Mode):\033[0m {file_name}")
            
            # Step 1: Find watermark locations using template matching
            print("   Step 1: Template matching...")
            try:
                matches = self.find_watermark_locations_ref(input_path, threshold=threshold)
            except Exception as e:
                print(f"   ❌ Template matching failed: {e}")
                return False
            
            if not matches:
                print("   ⚠️  No watermarks detected - copying original")
                try:
                    shutil.copy2(input_path, output_path)
                    return True
                except Exception as e:
                    print(f"   ❌ Failed to copy original file: {e}")
                    return False
            
            # Step 2: Create mask from matches
            print("   Step 2: Creating mask from template matches...")
            try:
                mask_path = self.create_mask_from_ref_matches(input_path, matches,
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
    
    def process_image_ocr_mode(self, input_path: str, output_path: str, mask_output_path: str = None,
                             inpaint_method: str = "lama_ai") -> bool:
        """Process a single image using OCR auto-detection"""
        try:
            file_name = os.path.basename(input_path)
            print(f"🖼️  \033[33mProcessing (OCR Mode):\033[0m {file_name}")
            
            # Step 1: Detect text watermarks using OCR
            print("   Step 1: OCR text detection...")
            try:
                bboxes = self.detect_text_watermarks_ocr(input_path)
            except Exception as e:
                print(f"   ❌ OCR detection failed: {e}")
                return False
            
            if not bboxes:
                print("   ⚠️  No text watermarks detected - copying original")
                try:
                    shutil.copy2(input_path, output_path)
                    return True
                except Exception as e:
                    print(f"   ❌ Failed to copy original file: {e}")
                    return False
            
            # Step 2: Create mask from bounding boxes
            print("   Step 2: Creating mask from text detections...")
            try:
                mask_path = self.create_mask_from_ocr_bboxes(input_path, bboxes,
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

def get_processing_options(mode: str):
    """Get processing options based on the selected mode"""
    print("\033[1;33m⚙️  Processing Options\033[0m")
    
    if mode == "reference":
        # Reference mode options
        threshold = djj.get_float_input(
            "\033[33mTemplate matching threshold (0.5-0.9, default 0.7):\033[0m",
            min_val=0.3, max_val=0.95
        ) if djj.prompt_choice(
            "\033[33mAdjust detection sensitivity?\033[0m\n1. Use default (0.7)\n2. Custom threshold",
            ['1', '2'], default='1'
        ) == '2' else 0.7
        
        # Inpainting method for reference mode (default to LaMa)
        inpaint_method = "lama_ai"
        print(f"🎨 \033[33mUsing LaMa AI inpainting for reference mode\033[0m")
        
    else:  # OCR mode
        threshold = 0.7  # Not used in OCR mode
        
        # Check LaMa availability
        try:
            test_remover = UnifiedWatermarkRemover()
            lama_available = test_remover.lama_available
            del test_remover
        except:
            lama_available = False
        
        print(f"🎯 \033[33mAvailable inpainting methods:\033[0m")
        methods = ["1. LaMa AI (highest quality, slower)"]
        method_choices = ['1']
        
        if lama_available:
            methods.extend([
                "2. Telea (fast, good for text)",
                "3. Navier-Stokes (good for textures)",
                "4. Hybrid (combines Telea + Navier-Stokes)"
            ])
            method_choices = ['1', '2', '3', '4']
        
        for method in methods:
            print(f"   {method}")
        
        inpaint_choice = djj.prompt_choice(
            "\033[33mInpainting method:\033[0m",
            method_choices,
            default='1' if lama_available else '2'
        )
        
        method_map = {
            '1': 'lama_ai',
            '2': 'telea',
            '3': 'navier_stokes',
            '4': 'hybrid'
        }
        inpaint_method = method_map.get(inpaint_choice, 'lama_ai')
    
    # Keep masks option
    keep_masks = djj.prompt_choice(
        "\033[33mSave mask files?\033[0m\n1. Yes (save to Output/Masks)\n2. No (temporary only)",
        ['1', '2'], default='2'
    ) == '1'
    
    return threshold, inpaint_method, keep_masks

def process_images_batch_unified(input_paths, mode, reference_path, input_mode, src_path,
                               suffix, threshold, inpaint_method, keep_masks):
    """Process images with unified watermark removal"""
    print("\n" * 2)
    print(f"\n\033[1;33m🧠 Processing\033[0m {len(input_paths)} \033[1;33mimage(s):\033[0m")
    print("=" * 60)
    print(f"\033[33m🎯 Mode:\033[0m {mode.title()} Detection")
    if reference_path:
        print(f"\033[33m📸 Reference:\033[0m {os.path.basename(reference_path)}")
    print(f"\033[33m🔠 Suffix:\033[0m {suffix}")
    if mode == "reference":
        print(f"\033[33m📊 Threshold:\033[0m {threshold}")
    print(f"\033[33m🎨 Method:\033[0m {inpaint_method}")
    print(f"\033[33m💾 Keep Masks:\033[0m {'Yes' if keep_masks else 'No'}")
    if input_mode == '1':
        print(f"\033[33m📥 Input folder:\033[0m {src_path}")
    print("=" * 60)
    print()
    
    # Initialize the unified remover
    remover = UnifiedWatermarkRemover()
    
    # Load reference watermark if in reference mode
    if mode == "reference" and reference_path:
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
            # Choose processing method based on mode
            if mode == "reference":
                success = remover.process_image_reference_mode(
                    str(input_path), str(output_path), mask_output_path,
                    threshold, inpaint_method
                )
            else:  # OCR mode
                success = remover.process_image_ocr_mode(
                    str(input_path), str(output_path), mask_output_path,
                    inpaint_method
                )
            
            if success:
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
    print(f"\033[1;33m🏁 Unified Processing Complete!\033[0m")
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
    
    # Setup model cache
    setup_model_cache()
    
    while True:
        print()
        print("\033[92m" + "=" * 50 + "\033[0m")
        print("\033[1;33mUnified Watermark Remover for DJJTB - COMBINED VERSION\033[0m")
        print("🎯 Mode 1: Reference-Based (solid watermarks)")
        print("🔤 Mode 2: OCR Auto-Detection (text watermarks)")
        print("🎨 LaMa AI + OpenCV Inpainting Options")
        print("💾 Optional Mask File Export")
        print("⚡ Optimized for M2 MacBook Air 8GB RAM")
        print("\033[92m" + "=" * 50 + "\033[0m")
        print()
        
        try:
            # Step 1: Get removal mode
            print("\033[1;33m📋 STEP 1: Removal Mode\033[0m")
            mode = get_removal_mode()
            
            reference_path = None
            if mode == "reference":
                os.system('clear')
                print(f"✅ \033[33mMode selected:\033[0m Reference-Based Detection")
                print()
                
                print("\033[1;33m📋 STEP 2: Reference Watermark\033[0m")
                reference_path = get_reference_watermark()
                if not reference_path:
                    print("❌ Invalid reference watermark. Exiting.")
                    break
            
            os.system('clear')
            if reference_path:
                print(f"✅ \033[33mMode:\033[0m Reference-Based")
                print(f"✅ \033[33mReference:\033[0m {os.path.basename(reference_path)}")
            else:
                print(f"✅ \033[33mMode:\033[0m OCR Auto-Detection")
            print()
            
            # Step 3: Get input files
            step_num = 3 if mode == "reference" else 2
            print(f"\033[1;33m📋 STEP {step_num}: Input Images\033[0m")
            input_files, input_mode, src_path = get_valid_inputs()
            
            os.system('clear')
            if reference_path:
                print(f"✅ \033[33mMode:\033[0m Reference-Based")
                print(f"✅ \033[33mReference:\033[0m {os.path.basename(reference_path)}")
            else:
                print(f"✅ \033[33mMode:\033[0m OCR Auto-Detection")
            print(f"✅ \033[33mInput files:\033[0m {len(input_files)} images")
            print()
            
            # Step 4: Get processing options
            step_num = 4 if mode == "reference" else 3
            print(f"\033[1;33m📋 STEP {step_num}: Processing Options\033[0m")
            threshold, inpaint_method, keep_masks = get_processing_options(mode)
            
            # Step 5: Get suffix
            suffix = djj.get_string_input(
                "\033[33mEnter output suffix (default 'NoWM'):\033[0m\n > ",
                default="NoWM"
            )
            
            os.system('clear')
            
            # Process all images
            process_images_batch_unified(
                input_files, mode, reference_path, input_mode, src_path,
                suffix, threshold, inpaint_method, keep_masks
            )
            
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