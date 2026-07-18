#!/usr/bin/env python3
"""
Fix Florence-2 model cache for M4 Mac Studio
Removes old cached model to allow fresh download with correct transformers version
"""

import os
import shutil
from pathlib import Path

# Your model cache directory
FLORENCE_CACHE = Path("/Users/home/Documents/ai_models/Florence")

print("🔧 Florence-2 Cache Fixer")
print("=" * 50)
print()

if not FLORENCE_CACHE.exists():
    print("✅ No Florence cache found - nothing to fix!")
    exit(0)

print(f"📁 Cache location: {FLORENCE_CACHE}")
print()

# Look for Florence model folders
florence_folders = []
for item in FLORENCE_CACHE.iterdir():
    if item.is_dir() and ('florence' in item.name.lower() or 'models--microsoft' in item.name.lower()):
        florence_folders.append(item)

if not florence_folders:
    print("⚠️  No Florence model folders found in cache")
    print("   Cache might already be clean")
    exit(0)

print("Found these Florence-2 folders:")
for folder in florence_folders:
    size_mb = sum(f.stat().st_size for f in folder.rglob('*') if f.is_file()) / 1024 / 1024
    print(f"   • {folder.name} ({size_mb:.1f} MB)")
print()

response = input("🗑️  Delete these folders? [y/N]: ").strip().lower()

if response == 'y':
    print()
    for folder in florence_folders:
        try:
            print(f"   Removing {folder.name}...")
            shutil.rmtree(folder)
            print(f"   ✅ Deleted")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    print()
    print("=" * 50)
    print("✅ Cache cleaned!")
    print()
    print("Next steps:")
    print("1. Run your image_caption_generator.py again")
    print("2. It will download Florence-2 fresh (~500-1000 MB)")
    print("3. This time it will be compatible with your transformers version")
else:
    print("❌ Cancelled - no changes made")
