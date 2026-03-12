# Kohya_ss LoRA Training Setup Guide for Mac M4 Max

## What is Kohya_ss?

Kohya_ss is the industry-standard tool for training LoRAs. It has a user-friendly GUI and is more reliable than ComfyUI training nodes. Most professional LoRAs on Civitai are trained with this.

---

## Installation on Mac

### Prerequisites
- Python 3.10 or 3.11 (you have 3.11.9 ✅)
- Git
- 64GB RAM (you have this ✅)

### Step 1: Install Dependencies

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required packages
brew install cmake protobuf rust python-tk@3.11
```

### Step 2: Clone Kohya_ss

```bash
# Navigate to where you want to install
cd ~/Documents/ai_models/

# Clone the repository
git clone https://github.com/bmaltais/kohya_ss.git
cd kohya_ss

# Check out stable version (optional but recommended)
git checkout v24.1.7
```

### Step 3: Setup Virtual Environment

```bash
# Create venv using your Python 3.11.9
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m venv venv

# Activate venv
source venv/bin/activate

# Verify Python version
python --version  # Should show 3.11.9
```

### Step 4: Install PyTorch for Mac

```bash
# Install PyTorch with MPS support
pip install torch torchvision torchaudio
```

### Step 5: Install Kohya Requirements

```bash
# Upgrade pip first
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Install specific packages for Mac
pip install -U -I --no-deps \
  https://github.com/C43H66N12O12S2/stable-fast/releases/download/v1.0.5/stable_fast-1.0.5+torch211cu121-cp311-cp311-manylinux2014_x86_64.whl
```

**Note:** The last command might fail on Mac - that's okay, it's a CUDA-specific optimization.

### Step 6: Fix Mac-Specific Issues

```bash
# Install additional Mac dependencies
pip install tensorflow-macos tensorflow-metal

# If you get errors about missing modules, install them:
pip install accelerate transformers diffusers dadaptation prodigyopt lycoris-lora
```

### Step 7: Launch Kohya_ss

```bash
# Make sure venv is activated
source venv/bin/activate

# Launch the GUI
python gui.py

# Or use the convenience script
./gui.sh
```

This will open a web interface at `http://127.0.0.1:7860`

---

## First Time Setup in GUI

### 1. Install Models

Kohya needs SDXL models in specific folders:

```bash
# Create model directories
mkdir -p ~/Documents/ai_models/kohya_ss/models/Stable-diffusion
mkdir -p ~/Documents/ai_models/kohya_ss/models/VAE

# Copy or symlink your SDXL models
# From ComfyUI:
ln -s ~/Documents/ai_models/ComfyUI_App/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors \
  ~/Documents/ai_models/kohya_ss/models/Stable-diffusion/

ln -s ~/Documents/ai_models/ComfyUI_App/ComfyUI/models/vae/sdxl_vae.safetensors \
  ~/Documents/ai_models/kohya_ss/models/VAE/
```

### 2. Configure Settings

In the GUI (http://127.0.0.1:7860):

**Go to "Configuration" tab:**
- Pretrained model: `sd_xl_base_1.0.safetensors`
- Output directory: `./output`
- Logging directory: `./logs`

---

## Training Your First SDXL LoRA

### Step 1: Prepare Your Dataset

```bash
# Create training folder structure
mkdir -p ~/Documents/ai_models/kohya_ss/training_data/my_first_lora/20_ohwx
```

**Folder naming convention:**
`NUMBER_TRIGGER/`
- **NUMBER** = number of repeats per epoch (10-50)
- **TRIGGER** = your trigger word (ohwx, sks, etc.)

**Example:**
- `20_ohwx/` = repeat each image 20 times, trigger word is "ohwx"
- `30_mychar/` = repeat 30 times, trigger is "mychar"

### Step 2: Add Your Images

```bash
# Copy your training images
cp /path/to/your/images/*.jpg ~/Documents/ai_models/kohya_ss/training_data/my_first_lora/20_ohwx/
```

**Image requirements:**
- 10-30 images (20 is ideal)
- 1024x1024 or higher
- Good variety
- Clear, high quality

### Step 3: Generate Captions

**Option A: Manual Captions**
Create `.txt` files for each image:

```
image_001.jpg → image_001.txt
Content: "a photo of ohwx woman, blonde hair, smiling, red dress"
```

**Option B: Auto-Caption in Kohya**
1. Go to "Utilities" tab
2. Select "Captioning"
3. Choose "BLIP" or "WD14 Tagger"
4. Point to your image folder
5. Click "Caption images"

**Option C: Use WD14 Tagger (Best for anime/illustrations)**
```bash
# Install WD14 tagger
pip install wd14-tagger

# Run captioning
python utilities/caption_images_wd14.py \
  --model_dir ./models/wd14_tagger \
  --image_dir ./training_data/my_first_lora/20_ohwx \
  --caption_extension .txt \
  --batch_size 4
```

### Step 4: Configure Training Settings

In Kohya GUI, go to **"LoRA" tab**:

#### **Source Model**
- Model: `sd_xl_base_1.0.safetensors`
- Model type: `SDXL`
- V2: ☐ (unchecked)
- V-parameterization: ☐ (unchecked)

#### **Folders**
- Image folder: `./training_data/my_first_lora`
- Output folder: `./output/my_first_lora`
- Logging folder: `./logs`
- Model output name: `my_first_lora`

#### **Training Parameters**
```
Training epochs: 10
Save every N epochs: 1
Mixed precision: fp16
Save precision: fp16
Number of CPU threads: 8
Seed: 42
Cache latents: ☑ (checked)
Cache latents to disk: ☑ (checked)
```

#### **Learning Rate**
```
Learning rate: 0.0001
LR Scheduler: cosine_with_restarts
LR warmup (% of steps): 10
Optimizer: AdamW8bit
```

#### **LoRA Settings**
```
Network Rank (dimension): 32
Network Alpha: 32
LoRA type: Standard
```

#### **Advanced Settings**
```
Resolution: 1024,1024
Batch size: 2
Gradient accumulation steps: 1
Max train steps: Leave empty (will calculate from epochs)
Enable buckets: ☑
Min bucket resolution: 256
Max bucket resolution: 2048
Caption extension: .txt
Shuffle caption: ☑
Keep tokens: 1
```

#### **Sample Images (Optional but Recommended)**
```
Sample every N epochs: 1
Sample prompts:
  a photo of ohwx woman, portrait, studio lighting
  ohwx woman wearing casual clothes, outdoors
  ohwx woman, professional photography
Sample sampler: euler_a
Sample steps: 30
```

### Step 5: Start Training

1. Review all settings
2. Click **"Train model"** button at the bottom
3. Monitor progress in the terminal/console
4. Training will take 1-3 hours depending on settings

**Progress indicators:**
- Loss values (should decrease over time)
- Sample images (if enabled)
- ETA remaining

### Step 6: Find Your Trained LoRAs

After training completes, find your LoRAs:

```bash
cd ~/Documents/ai_models/kohya_ss/output/my_first_lora
ls -lh
```

You'll see files like:
- `my_first_lora-000001.safetensors` (epoch 1)
- `my_first_lora-000005.safetensors` (epoch 5)
- `my_first_lora-000010.safetensors` (epoch 10)

---

## Testing Your LoRA in ComfyUI

### Copy LoRA to ComfyUI

```bash
# Copy to ComfyUI
cp ~/Documents/ai_models/kohya_ss/output/my_first_lora/*.safetensors \
  ~/Documents/ai_models/ComfyUI_App/ComfyUI/models/loras/
```

### Test Workflow

Use this simple test in ComfyUI:

```
CheckpointLoaderSimple (SDXL base)
  ↓
LoraLoader (your LoRA, strength 0.8-1.0)
  ↓
CLIPTextEncode (+): "a photo of ohwx woman, portrait"
CLIPTextEncode (-): "blurry, low quality"
  ↓
EmptyLatentImage (1024x1024)
  ↓
KSampler (steps 30, cfg 7.0, euler_a)
  ↓
VAEDecode
  ↓
SaveImage
```

**Test different epochs** (001, 005, 010) to find the best one!

---

## Recommended Settings for Different LoRA Types

### Character/Person LoRA
```
Rank: 32
Alpha: 32
Learning Rate: 0.0001
Epochs: 10-15
Images: 20-30
Repeats: 20
```

### Style LoRA
```
Rank: 64
Alpha: 64
Learning Rate: 0.0001
Epochs: 15-20
Images: 50-100
Repeats: 10
```

### Concept LoRA
```
Rank: 32
Alpha: 32
Learning Rate: 0.0001
Epochs: 10-15
Images: 30-50
Repeats: 15
```

---

## Troubleshooting

### "Out of memory" error
```bash
# Reduce batch size to 1
# Enable gradient checkpointing
# Cache latents to disk
```

### "Module not found" errors
```bash
pip install [missing_module_name]
```

### Training is too slow
```bash
# Lower resolution to 768x768
# Reduce batch size
# Use fewer training images for testing
```

### Mac MPS errors
```bash
# Some operations fall back to CPU - this is normal
# Set environment variable:
export PYTORCH_ENABLE_MPS_FALLBACK=1
python gui.py
```

### LoRA doesn't work in ComfyUI
- Check trigger word is correct
- Try different strengths (0.6, 0.8, 1.0, 1.2)
- Test different epoch checkpoints
- Verify LoRA file isn't corrupted

---

## Quick Start Checklist

- [ ] Install Kohya_ss
- [ ] Download SDXL base model
- [ ] Prepare 20-30 images
- [ ] Create folder: `20_ohwx/`
- [ ] Generate/write captions
- [ ] Configure training settings
- [ ] Start training
- [ ] Test epochs 5, 8, 10
- [ ] Copy best LoRA to ComfyUI
- [ ] Celebrate! 🎉

---

## Advanced Tips

### 1. Regularization Images
Prevent overfitting by adding "reg" images:
```
training_data/
├── 20_ohwx/          # Your subject
└── 1_person/         # Generic people photos (for regularization)
```

### 2. Tag Ordering
For anime/character LoRAs, order tags by importance:
```
ohwx, 1girl, blue eyes, blonde hair, smiling, red dress, studio
```

### 3. Aspect Ratio Bucketing
Enable buckets to train on various aspect ratios:
- Portrait: 768x1344
- Landscape: 1344x768
- Square: 1024x1024

### 4. Resume Training
If training crashes, resume from last checkpoint:
- Point to the last saved LoRA
- Reduce remaining epochs

---

## Resources

- **Kohya GitHub**: https://github.com/bmaltais/kohya_ss
- **Documentation**: https://github.com/bmaltais/kohya_ss/wiki
- **SDXL Training Guide**: https://rentry.org/sdxl_lora_training_guide_kohya
- **Discord**: Kohya-ss Discord for support
- **Reddit**: r/StableDiffusion

---

## For Next Chat

If we continue in a new chat, send me:

1. "Continuing Kohya_ss SDXL training from previous conversation"
2. Your training settings (copy/paste from GUI)
3. Any errors you're getting
4. What worked/didn't work

Good luck with your training! 🚀

---

## Summary Command Reference

```bash
# Start Kohya GUI
cd ~/Documents/ai_models/kohya_ss
source venv/bin/activate
python gui.py

# Caption images
python utilities/caption_images_wd14.py \
  --image_dir ./training_data/my_lora/20_trigger \
  --batch_size 4

# Copy trained LoRA to ComfyUI
cp output/my_lora/*.safetensors \
  ~/Documents/ai_models/ComfyUI_App/ComfyUI/models/loras/
```

Start with a small test (5 images, 5 epochs) to verify everything works!
