#!/usr/bin/env python3
"""
Fix Florence-2 model code for MPS beam search compatibility
Patches the prepare_inputs_for_generation method to handle None past_key_values
"""

import sys
from pathlib import Path

FLORENCE_DIR = Path("/Users/home/Documents/ai_models/Florence/modules/transformers_modules/microsoft")

print("🔧 Florence-2 Model Code Fixer (MPS Beam Search)")
print("=" * 60)
print()

# Find the florence modeling files
florence_files = list(FLORENCE_DIR.rglob("modeling_florence2.py"))

if not florence_files:
    print("❌ No Florence-2 model files found in:")
    print(f"   {FLORENCE_DIR}")
    print()
    print("This might mean:")
    print("1. Florence cache was cleaned")
    print("2. Model hasn't been downloaded yet")
    print()
    print("Solution: Just use the simpler fix - change num_beams=3 to num_beams=1")
    sys.exit(1)

print(f"Found {len(florence_files)} Florence-2 model file(s):")
for f in florence_files:
    print(f"   • {f.parent.name}/modeling_florence2.py")
print()

# The problematic code
old_code = '''        # cut decoder_input_ids if past_key_values is used
        if past_key_values is not None:
            past_length = past_key_values[0][0].shape[2]'''

# Fixed code
new_code = '''        # cut decoder_input_ids if past_key_values is used
        if past_key_values is not None and past_key_values[0] is not None and past_key_values[0][0] is not None:
            past_length = past_key_values[0][0].shape[2]'''

fixed_count = 0

for model_file in florence_files:
    print(f"Patching: {model_file.parent.name}/...")
    
    with open(model_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if old_code not in content:
        print("   ⚠️  Pattern not found (already patched or different version)")
        continue
    
    # Apply patch
    new_content = content.replace(old_code, new_code)
    
    # Backup
    backup_path = model_file.with_suffix('.py.backup')
    if not backup_path.exists():
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"   💾 Backup: {backup_path.name}")
    
    # Write patched version
    with open(model_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("   ✅ Patched!")
    fixed_count += 1
    print()

print("=" * 60)
if fixed_count > 0:
    print(f"✅ Successfully patched {fixed_count} file(s)!")
    print()
    print("What changed:")
    print("Added null checks for past_key_values before accessing shape")
    print("This prevents the 'NoneType' has no attribute 'shape' error")
    print()
    print("Next step:")
    print("Run: python3 image_caption_generator.py")
    print()
    print("Beam search (num_beams=3) should now work on MPS! 🎉")
else:
    print("⚠️  No files were patched")
    print()
    print("Alternative: Use greedy decoding instead")
    print("Run: python3 patch_caption_script_v3.py")
    print("(Changes num_beams=3 to num_beams=1)")
