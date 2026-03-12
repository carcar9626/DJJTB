#!/usr/bin/env python3
"""
Comprehensive Florence-2 MPS Fix
Finds and fixes ALL instances of the past_key_values bug
"""

import re
from pathlib import Path

FLORENCE_DIR = Path("/Users/home/Documents/ai_models/Florence/modules/transformers_modules/microsoft")

print("🔧 Comprehensive Florence-2 MPS Bug Fixer")
print("=" * 60)
print()

# Find all modeling files
florence_files = list(FLORENCE_DIR.rglob("modeling_florence2.py"))

if not florence_files:
    print("❌ No Florence-2 model files found")
    exit(1)

print(f"Found {len(florence_files)} file(s) to patch")
print()

for model_file in florence_files:
    print(f"📄 {model_file.parent.name}/modeling_florence2.py")
    
    with open(model_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern 1: past_key_values[0][0].shape[2] if past_key_values is not None
    # This checks if past_key_values is not None, but doesn't check if the nested values are None
    pattern1 = re.compile(
        r'past_key_values\[0\]\[0\]\.shape\[2\]\s+if\s+past_key_values is not None'
    )
    
    def fix_pattern1(match):
        return 'past_key_values[0][0].shape[2] if (past_key_values is not None and past_key_values[0] is not None and past_key_values[0][0] is not None)'
    
    content = pattern1.sub(fix_pattern1, content)
    
    # Pattern 2: if past_key_values is not None:
    #               past_length = past_key_values[0][0].shape[2]
    # Need to add nested None checks
    pattern2_lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(pattern2_lines):
        line = pattern2_lines[i]
        
        # Check if this line has "if past_key_values is not None:"
        if 'if past_key_values is not None:' in line and 'past_key_values[0]' not in line:
            # Look ahead to see if next line accesses past_key_values[0][0]
            if i + 1 < len(pattern2_lines):
                next_line = pattern2_lines[i + 1]
                if 'past_key_values[0][0]' in next_line and 'shape' in next_line:
                    # Replace the condition with comprehensive check
                    line = line.replace(
                        'if past_key_values is not None:',
                        'if past_key_values is not None and past_key_values[0] is not None and past_key_values[0][0] is not None:'
                    )
        
        new_lines.append(line)
        i += 1
    
    content = '\n'.join(new_lines)
    
    # Check if anything changed
    if content == original_content:
        print("   ✅ Already patched or no patterns found")
        print()
        continue
    
    # Count changes
    changes = sum(1 for a, b in zip(original_content.split('\n'), content.split('\n')) if a != b)
    
    # Backup
    backup_path = model_file.with_suffix('.py.backup')
    if not backup_path.exists():
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"   💾 Backup created: {backup_path.name}")
    
    # Write patched version
    with open(model_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"   ✅ Patched {changes} line(s)!")
    print()

print("=" * 60)
print("✅ All Florence-2 files patched!")
print("=" * 60)
print()

print("Next step:")
print("Run: python3 image_caption_generator.py")
print()
print("This should FINALLY work! 🎉")
