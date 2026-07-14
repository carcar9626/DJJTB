from safetensors.torch import load_file, save_file
import torch
import os

# Load LoRAs
lora_30 = load_file("/Users/home/Documents/Lora_Training/Results/SACH-ZIT/EP07/lora-000007.TA_trained.safetensors")
lora_50 = load_file("/Users/home/Documents/Lora_Training/Results/SACH-ZIT/EP08/lora-000008.TA_trained.safetensors")
output_dir = "/Users/home/Documents/Lora_Training/Results/SACH-ZIT/EP07-08_MERGE/"

# Merge weights (weighted average)
merged = {}
weight_30, weight_50 = 0.5, 0.5  # Equal weights; adjust if needed (e.g., 0.6, 0.4)
for key in lora_30:
    if key in lora_50:
        merged[key] = weight_30 * lora_30[key] + weight_50 * lora_50[key]
    else:
        merged[key] = lora_30[key]
for key in lora_50:
    if key not in merged:
        merged[key] = lora_50[key]

# Save merged LoRA
save_file(merged, "/Users/home/Documents/Lora_Training/Results/SACH-ZIT/EP07-08_MERGE/merged.safetensors")

os.system(f"open {output_dir}")