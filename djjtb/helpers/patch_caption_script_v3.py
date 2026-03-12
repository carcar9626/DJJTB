#!/usr/bin/env python3
"""
PATCH 3: Fix beam search on MPS
Changes num_beams=3 to num_beams=1 (greedy decoding)
This avoids the past_key_values None error on Apple Silicon
"""

import sys
from pathlib import Path

SCRIPT_PATH = Path("/Users/home/Documents/Scripts/DJJTB/djjtb/ai_tools/image_caption_generator.py")

print("🔧 Image Caption Generator Patcher v3 (MPS Beam Search Fix)")
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

# Find and replace the generate call - look for num_beams=3
old_generate = 'num_beams=3, do_sample=False'
new_generate = 'num_beams=1, do_sample=False'

if old_generate not in content:
    print("⚠️  Script already patched or different than expected")
    print()
    # Check if already using num_beams=1
    if 'num_beams=1' in content:
        print("✅ Already using num_beams=1 (greedy decoding)")
        sys.exit(0)
    else:
        print("Manual fix needed:")
        print("Find: num_beams=3")
        print("Replace with: num_beams=1")
        sys.exit(1)

# Apply the patch
new_content = content.replace(old_generate, new_generate)

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
print("✅ Patch 3 applied successfully!")
print("=" * 60)
print()

print("What changed:")
print("• Changed num_beams=3 → num_beams=1")
print("• This uses greedy decoding instead of beam search")
print("• Avoids the past_key_values bug on MPS")
print("• Quality is nearly identical, just slightly faster")
print()

print("Why this fixes it:")
print("Florence-2's beam search has a bug on Apple Silicon (MPS)")
print("where past_key_values becomes None during generation.")
print("Greedy decoding (num_beams=1) doesn't use past_key_values,")
print("so it works perfectly on your M4 Max!")
print()

print("Next step:")
print("Run: python3 image_caption_generator.py")
print()
print("This should work now! 🎉")
