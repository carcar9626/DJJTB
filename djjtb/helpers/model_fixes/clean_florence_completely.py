#!/usr/bin/env python3
"""
Complete Florence-2 Cache Cleaner
Removes ALL Florence model files and cached code
"""

import os
import shutil
from pathlib import Path

FLORENCE_CACHE = Path("/Users/home/Documents/ai_models/Florence")

print("🧹 Complete Florence-2 Cache Cleaner")
print("=" * 60)
print()

if not FLORENCE_CACHE.exists():
    print("✅ No Florence cache found - nothing to clean!")
    exit(0)

print(f"📁 Cache location: {FLORENCE_CACHE}")
print()

# Find ALL Florence-related items
items_to_delete = []
total_size = 0

for item in FLORENCE_CACHE.rglob('*'):
    if item.is_file():
        total_size += item.stat().st_size

# Check what's in there
print("📊 Current cache contents:")
print("-" * 60)
for item in sorted(FLORENCE_CACHE.iterdir()):
    if item.is_dir():
        size_mb = sum(f.stat().st_size for f in item.rglob('*') if f.is_file()) / 1024 / 1024
        print(f"   📂 {item.name} ({size_mb:.1f} MB)")
    elif item.is_file():
        size_mb = item.stat().st_size / 1024 / 1024
        print(f"   📄 {item.name} ({size_mb:.1f} MB)")

total_mb = total_size / 1024 / 1024
print(f"\n   💾 Total: {total_mb:.1f} MB")
print()

# Specifically check for the problematic modules folder
modules_path = FLORENCE_CACHE / "modules"
if modules_path.exists():
    print("⚠️  Found 'modules' folder with old model code!")
    print("   This is what's causing the _supports_sdpa error")
    print()

print("=" * 60)
print("🗑️  This will DELETE the ENTIRE Florence cache folder:")
print(f"   {FLORENCE_CACHE}")
print()
print("   The model will re-download (~500-1500 MB) on next run,")
print("   but with fresh, compatible code.")
print("=" * 60)
print()

response = input("Delete entire Florence cache? [y/N]: ").strip().lower()

if response == 'y':
    print()
    print("🗑️  Deleting cache...")
    try:
        shutil.rmtree(FLORENCE_CACHE)
        print("   ✅ Deleted")
        
        # Recreate empty directory
        FLORENCE_CACHE.mkdir(parents=True, exist_ok=True)
        print("   ✅ Recreated empty cache directory")
        
        print()
        print("=" * 60)
        print("✅ Florence cache completely cleaned!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Run your image_caption_generator.py")
        print("2. Florence-2 will download fresh with compatible code")
        print("3. Should work perfectly this time!")
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        print()
        print("If you get a permission error, try:")
        print(f"   rm -rf '{FLORENCE_CACHE}'")
else:
    print("❌ Cancelled - no changes made")
    print()
    print("Alternative: Manually delete the folder:")
    print(f"   rm -rf '{FLORENCE_CACHE}'")
