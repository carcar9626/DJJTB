#!/usr/bin/env python3
"""
M4 Mac Studio - Fix NumPy Conflict
Resolves the numpy version conflict in wmrmvenv
"""

import subprocess
import sys
from pathlib import Path

VENV_PATH = Path("/Users/home/Documents/ai_models/watermark_remover/wmrmvenv")
PIP = VENV_PATH / "bin" / "pip"
PYTHON = VENV_PATH / "bin" / "python"

print("🔧 M4 Mac Studio - NumPy Conflict Fixer")
print("=" * 60)
print()

if not VENV_PATH.exists():
    print("❌ Virtual environment not found at:", VENV_PATH)
    sys.exit(1)

print(f"✅ Found venv: {VENV_PATH}")
print()

print("📊 Analyzing the conflict:")
print("-" * 60)
print("• opencv-python-headless 4.12.0.88 requires NumPy >= 2.0")
print("• Most other packages work with NumPy 1.x or 2.x")
print("• Your old requirements.txt pinned NumPy to 1.25.2")
print("• Solution: Downgrade opencv-python-headless to 4.10.x")
print()

print("=" * 60)
print("🔧 Fixing packages...")
print("=" * 60)
print()

# Step 1: Uninstall the problematic opencv version
print("1️⃣  Removing opencv-python-headless 4.12.x...")
try:
    subprocess.run([str(PIP), "uninstall", "-y", "opencv-python-headless"], 
                   check=True, capture_output=True)
    print("   ✅ Removed")
except:
    print("   ⚠️  Not installed (OK)")
print()

# Step 2: Install compatible opencv version
print("2️⃣  Installing opencv-python-headless 4.10.x (compatible with NumPy 1.x)...")
try:
    subprocess.run([str(PIP), "install", "opencv-python-headless==4.10.0.84"], 
                   check=True)
    print("   ✅ Installed")
except subprocess.CalledProcessError as e:
    print(f"   ❌ Failed: {e}")
print()

# Step 3: Upgrade Pillow (for PyTorch 2.8 compatibility)
print("3️⃣  Upgrading Pillow (current: 9.5.0 → target: 10.x)...")
try:
    subprocess.run([str(PIP), "install", "--upgrade", "Pillow>=10.0.0"], 
                   check=True)
    print("   ✅ Upgraded")
except subprocess.CalledProcessError as e:
    print(f"   ❌ Failed: {e}")
print()

# Step 4: Ensure NumPy is at good version
print("4️⃣  Ensuring NumPy 1.26.x (compatible with everything)...")
try:
    subprocess.run([str(PIP), "install", "numpy>=1.26.0,<2.0"], 
                   check=True)
    print("   ✅ Installed")
except subprocess.CalledProcessError as e:
    print(f"   ❌ Failed: {e}")
print()

# Step 5: Verify transformers version
print("5️⃣  Checking transformers version...")
try:
    result = subprocess.run([str(PYTHON), "-c", 
                            "import transformers; print(transformers.__version__)"],
                           capture_output=True, text=True)
    version = result.stdout.strip()
    print(f"   Current: {version}")
    
    # Parse version
    major, minor = map(int, version.split('.')[:2])
    if major < 4 or (major == 4 and minor < 46):
        print("   ⬆️  Upgrading to 4.46+...")
        subprocess.run([str(PIP), "install", "--upgrade", "transformers>=4.46.0"], 
                      check=True)
        print("   ✅ Upgraded")
    else:
        print("   ✅ Version OK")
except Exception as e:
    print(f"   ⚠️  Could not check: {e}")
print()

print("=" * 60)
print("📊 Final package versions:")
print("-" * 60)
try:
    result = subprocess.run([str(PYTHON), "-c", 
        "import torch, transformers, PIL, numpy, cv2; "
        "print(f'PyTorch: {torch.__version__}'); "
        "print(f'Transformers: {transformers.__version__}'); "
        "print(f'Pillow: {PIL.__version__}'); "
        "print(f'NumPy: {numpy.__version__}'); "
        "print(f'OpenCV: {cv2.__version__}'); "
        "print(f'MPS available: {torch.backends.mps.is_available()}')"],
        capture_output=True, text=True)
    print(result.stdout)
except Exception as e:
    print(f"⚠️  Could not check versions: {e}")
    print()

print("=" * 60)
print("✅ Package conflicts resolved!")
print("=" * 60)
print()

print("Next steps:")
print("1. Run fix_florence_cache.py to clean old model cache")
print("2. Test your image_caption_generator.py")
print("3. Test your watermark_remover script")
print()

# Offer to save clean requirements
print("💾 Save new clean requirements.txt? [y/N]: ", end="")
response = input().strip().lower()
if response == 'y':
    req_path = Path("/Users/home/Documents/ai_models/watermark_remover/requirements_clean.txt")
    with open(req_path, 'w') as f:
        subprocess.run([str(PIP), "freeze"], stdout=f)
    print(f"✅ Saved to: {req_path}")
    print(f"   Use this for fresh installs instead of the old requirements.txt")
