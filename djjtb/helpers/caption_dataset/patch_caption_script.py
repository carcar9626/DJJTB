#!/usr/bin/env python3
"""
PATCH for image_caption_generator.py
Adds attn_implementation='eager' to bypass _supports_sdpa error
"""

import sys
from pathlib import Path

SCRIPT_PATH = Path("/Users/home/Documents/Scripts/DJJTB/djjtb/ai_tools/image_caption_generator.py")

print("🔧 Image Caption Generator Patcher")
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

# Check if already patched
if 'attn_implementation=' in content:
    print("✅ Script already patched!")
    print()
    print("If still getting errors, try:")
    print("1. Delete Florence cache again")
    print("2. Run the script")
    sys.exit(0)

# Find the line to patch
target_line = 'self.model = AutoModelForCausalLM.from_pretrained(self.model_name, trust_remote_code=True, torch_dtype=torch.float32, cache_dir=MODEL_CACHE_DIR)'

if target_line not in content:
    print("⚠️  Could not find the exact line to patch")
    print("The script may have been modified")
    print()
    print("Manual fix needed:")
    print("In _load_florence() method, change:")
    print("  self.model = AutoModelForCausalLM.from_pretrained(...)")
    print("To:")
    print("  self.model = AutoModelForCausalLM.from_pretrained(..., attn_implementation='eager')")
    sys.exit(1)

# Apply the patch
patched_line = 'self.model = AutoModelForCausalLM.from_pretrained(self.model_name, trust_remote_code=True, torch_dtype=torch.float32, attn_implementation="eager", cache_dir=MODEL_CACHE_DIR)'

new_content = content.replace(target_line, patched_line)

# Backup original
backup_path = SCRIPT_PATH.parent / "image_caption_generator.py.backup"
print(f"💾 Creating backup: {backup_path.name}")
with open(backup_path, 'w', encoding='utf-8') as f:
    f.write(content)

# Write patched version
print(f"✍️  Writing patched version...")
with open(SCRIPT_PATH, 'w', encoding='utf-8') as f:
    f.write(new_content)

print()
print("=" * 60)
print("✅ Patch applied successfully!")
print("=" * 60)
print()

print("What changed:")
print("Added attn_implementation='eager' to force Florence-2 to use")
print("standard attention instead of SDPA (Scaled Dot Product Attention)")
print()

print("Next steps:")
print("1. Delete Florence cache: rm -rf /Users/home/Documents/ai_models/Florence/*")
print("2. Run: python3 image_caption_generator.py")
print()
print("To restore original: mv image_caption_generator.py.backup image_caption_generator.py")
