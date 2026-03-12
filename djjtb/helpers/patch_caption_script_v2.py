#!/usr/bin/env python3
"""
PATCH 2: Fix image processing on MPS
Adds error handling and ensures processor works correctly
"""

import sys
from pathlib import Path

SCRIPT_PATH = Path("/Users/home/Documents/Scripts/DJJTB/djjtb/ai_tools/image_caption_generator.py")

print("🔧 Image Caption Generator Patcher v2")
print("=" * 60)
print()

if not SCRIPT_PATH.exists():
    print(f"❌ Script not found: {SCRIPT_PATH}")
    sys.exit(1)

print(f"📄 Found script: {SCRIPT_PATH}")
print()

# Read the current file
with open(SCRIPT_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the generate_caption method
old_method = '''    def generate_caption(self, image_path: str, task: str = "<MORE_DETAILED_CAPTION>") -> str:
        try:
            from PIL import Image
            import torch
            
            image = Image.open(image_path).convert("RGB")
            inputs = self.processor(text=task, images=image, return_tensors="pt")
            
            if self.device == "mps":
                inputs = {k: v.to("mps") for k, v in inputs.items()}
            
            with torch.no_grad():
                generated_ids = self.model.generate(input_ids=inputs["input_ids"], pixel_values=inputs["pixel_values"], max_new_tokens=1024, num_beams=3, do_sample=False)
            
            generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
            caption = generated_text.replace(task, "").replace("</s>", "").strip()
            return caption
        except Exception as e:
            print(f"   ❌ Caption failed: {e}")
            return ""'''

new_method = '''    def generate_caption(self, image_path: str, task: str = "<MORE_DETAILED_CAPTION>") -> str:
        try:
            from PIL import Image
            import torch
            
            image = Image.open(image_path).convert("RGB")
            
            # Process inputs - ensure we get valid tensors
            inputs = self.processor(text=task, images=image, return_tensors="pt")
            
            # Debug: Check if pixel_values exists
            if "pixel_values" not in inputs or inputs["pixel_values"] is None:
                print(f"   ⚠️  Processor didn't create pixel_values - retrying with explicit image")
                inputs = self.processor(text=task, images=[image], return_tensors="pt")
            
            # Move to device (MPS or CPU)
            if self.device == "mps":
                inputs = {k: v.to("mps") if v is not None else None for k, v in inputs.items()}
            
            # Ensure pixel_values exists before generation
            if "pixel_values" not in inputs or inputs["pixel_values"] is None:
                print(f"   ❌ Failed to create pixel_values from image")
                return ""
            
            with torch.no_grad():
                generated_ids = self.model.generate(
                    input_ids=inputs["input_ids"], 
                    pixel_values=inputs["pixel_values"], 
                    max_new_tokens=1024, 
                    num_beams=3, 
                    do_sample=False
                )
            
            generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
            caption = generated_text.replace(task, "").replace("</s>", "").strip()
            return caption
        except Exception as e:
            import traceback
            print(f"   ❌ Caption failed: {e}")
            print(f"   Stack trace:")
            traceback.print_exc()
            return ""'''

if old_method not in content:
    print("⚠️  Could not find exact method to patch")
    print()
    print("The script may have already been modified or is different than expected.")
    print()
    print("Try this manual fix:")
    print("1. Open image_caption_generator.py")
    print("2. Find the generate_caption method")
    print("3. Add debug print before the processor line:")
    print('   print(f"   Debug: Processing {image_path}")')
    print("4. Check if image is loading correctly")
    sys.exit(1)

# Apply the patch
new_content = content.replace(old_method, new_method)

# Check if anything changed
if new_content == content:
    print("❌ No changes made - method might already be patched")
    sys.exit(1)

# Backup if not already backed up
backup_path = SCRIPT_PATH.parent / "image_caption_generator.py.backup"
if not backup_path.exists():
    print(f"💾 Creating backup: {backup_path.name}")
    with open(backup_path, 'w', encoding='utf-8') as f:
        with open(SCRIPT_PATH, 'r', encoding='utf-8') as orig:
            f.write(orig.read())

# Write patched version
print(f"✍️  Writing patched version...")
with open(SCRIPT_PATH, 'w', encoding='utf-8') as f:
    f.write(new_content)

print()
print("=" * 60)
print("✅ Patch 2 applied successfully!")
print("=" * 60)
print()

print("What changed:")
print("• Added better error handling for pixel_values")
print("• Added debug checks for processor output")
print("• Added retry logic if processor fails first time")
print("• Added stack trace on errors for debugging")
print()

print("Next step:")
print("Run: python3 image_caption_generator.py")
print()
print("If still failing, the debug output will show what's wrong")
