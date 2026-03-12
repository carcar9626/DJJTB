#!/bin/bash
# Kohya_ss SDXL LoRA Training Script for Mac
# Save this as: train_lora.sh
# Make executable: chmod +x train_lora.sh
# Run: ./train_lora.sh

# ============================================
# CONFIGURATION - EDIT THESE VALUES
# ============================================

# Paths
KOHYA_DIR="$HOME/Documents/ai_models/kohya_ss"
BASE_MODEL="$HOME/Documents/ai_models/kohya_ss/models/Stable-diffusion/sd_xl_base_1.0.safetensors"
VAE_MODEL="$HOME/Documents/ai_models/kohya_ss/models/VAE/sdxl_vae.safetensors"


# Project Settings
PROJECT_NAME="SACH_czy_SDXL"
TRIGGER_WORD="czy"  # Your trigger word
TRAINING_IMAGES="$KOHYA_DIR/training_data/$PROJECT_NAME"
OUTPUT_DIR="$KOHYA_DIR/output/$PROJECT_NAME"
LOG_DIR="$KOHYA_DIR/logs/$PROJECT_NAME"

# Training Parameters
MAX_TRAIN_EPOCHS=10
SAVE_EVERY_N_EPOCHS=2
NETWORK_DIM=32            # LoRA rank (16, 32, 64, 128)
NETWORK_ALPHA=32          # Usually same as dim
LEARNING_RATE=0.0001      # 0.0001 is safe default
LR_SCHEDULER="cosine_with_restarts"
LR_WARMUP_STEPS=100

# Image Settings
RESOLUTION="1024,1024"
BATCH_SIZE=2              # 2-4 for 64GB Mac
GRADIENT_ACCUMULATION=1

# Optimizer
OPTIMIZER="AdamW"     # AdamW8bit, Lion, Adafactor

# Sample Generation (Optional but recommended)
SAMPLE_EVERY_N_EPOCHS=2
SAMPLE_PROMPTS="$KOHYA_DIR/sample_prompts.txt"
SAMPLE_SAMPLER="euler"
SAMPLE_STEPS=30

# Advanced Settings
MIXED_PRECISION="fp16"
SAVE_PRECISION="fp16"
SEED=42
CACHE_LATENTS="--cache_latents"
CACHE_TO_DISK="--cache_latents_to_disk"

# ============================================
# DO NOT EDIT BELOW THIS LINE (unless you know what you're doing)
# ============================================

# Activate virtual environment
cd "$KOHYA_DIR"
source kyvenv/bin/activate

# Create output directories
mkdir -p "$OUTPUT_DIR"
mkdir -p "$LOG_DIR"

# Create sample prompts file if it doesn't exist
if [ ! -f "$SAMPLE_PROMPTS" ]; then
    cat > "$SAMPLE_PROMPTS" << EOF
a photo of $TRIGGER_WORD, portrait, studio lighting, high quality --n blurry, low quality --w 1024 --h 1024 --s 30
$TRIGGER_WORD wearing casual clothes, outdoors, natural lighting --n blurry --w 1024 --h 1024 --s 30
$TRIGGER_WORD, professional photography, detailed --n low quality, distorted --w 1024 --h 1024 --s 30
EOF
    echo "Created sample prompts file at: $SAMPLE_PROMPTS"
fi

# Enable MPS fallback for Mac
export PYTORCH_ENABLE_MPS_FALLBACK=1

# Display configuration
echo "============================================"
echo "Kohya_ss SDXL LoRA Training"
echo "============================================"
echo "Project: $PROJECT_NAME"
echo "Trigger: $TRIGGER_WORD"
echo "Images: $TRAINING_IMAGES"
echo "Output: $OUTPUT_DIR"
echo "Epochs: $MAX_TRAIN_EPOCHS"
echo "Rank/Alpha: $NETWORK_DIM/$NETWORK_ALPHA"
echo "Learning Rate: $LEARNING_RATE"
echo "Batch Size: $BATCH_SIZE"
echo "Resolution: $RESOLUTION"
echo "============================================"
echo ""
echo "Starting training in 5 seconds... (Ctrl+C to cancel)"
sleep 5

# Run training
python $KOHYA_DIR/sd-scripts/sdxl_train_network.py \
  --pretrained_model_name_or_path="$BASE_MODEL" \
  --vae="$VAE_MODEL" \
  --train_data_dir="$TRAINING_IMAGES" \
  --output_dir="$OUTPUT_DIR" \
  --output_name="$PROJECT_NAME" \
  --logging_dir="$LOG_DIR" \
  --resolution="$RESOLUTION" \
  --network_module="networks.lora" \
  --network_dim=$NETWORK_DIM \
  --network_alpha=$NETWORK_ALPHA \
  --learning_rate=$LEARNING_RATE \
  --lr_scheduler=$LR_SCHEDULER \
  --lr_warmup_steps=$LR_WARMUP_STEPS \
  --max_train_epochs=$MAX_TRAIN_EPOCHS \
  --save_every_n_epochs=$SAVE_EVERY_N_EPOCHS \
  --train_batch_size=$BATCH_SIZE \
  --gradient_accumulation_steps=$GRADIENT_ACCUMULATION \
  --mixed_precision=$MIXED_PRECISION \
  --save_precision=$SAVE_PRECISION \
  --seed=$SEED \
  --optimizer_type=$OPTIMIZER \
  --min_bucket_reso=256 \
  --max_bucket_reso=2048 \
  --enable_bucket \
  --bucket_reso_steps=64 \
  --bucket_no_upscale \
  $CACHE_LATENTS \
  $CACHE_TO_DISK \
  --caption_extension=".txt" \
  --shuffle_caption \
  --keep_tokens=1 \
  --max_data_loader_n_workers=2 \
  --persistent_data_loader_workers \
  --save_model_as=safetensors \
  --max_token_length=225 \
  --sdpa \
  --sample_every_n_epochs=$SAMPLE_EVERY_N_EPOCHS \
  --sample_prompts="$SAMPLE_PROMPTS" \
  --sample_sampler=$SAMPLE_SAMPLER

echo ""
echo "============================================"
echo "Training complete!"
echo "============================================"
echo "LoRAs saved to: $OUTPUT_DIR"
echo ""
echo "To test in ComfyUI, copy the LoRAs:"
echo "cp $OUTPUT_DIR/*.safetensors ~/Documents/ai_models/ComfyUI_App/ComfyUI/models/loras/"
echo ""
echo "Test different epochs to find the best one:"
echo "- ${PROJECT_NAME}-000002.safetensors (epoch 2)"
echo "- ${PROJECT_NAME}-000004.safetensors (epoch 4)"
echo "- ${PROJECT_NAME}-000006.safetensors (epoch 6)"
echo "- ${PROJECT_NAME}-000008.safetensors (epoch 8)"
echo "- ${PROJECT_NAME}-000010.safetensors (epoch 10)"
