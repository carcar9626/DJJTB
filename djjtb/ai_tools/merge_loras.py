from safetensors.torch import load_file, save_file
import torch
import os

# Load LoRAs
lora_30 = load_file("/Users/home/Documents/Lora_Training/Results/Merges/Anna16_CatAug19/caitalinagustina_Flux-KYS-EP19_TrainedLoRa.safetensors")
lora_50 = load_file("/Users/home/Documents/Lora_Training/Results/Merges/Anna16_CatAug19/IG_SingaporeanAnna_En_Ann4-SCL-EP16_TrainedLoRa.safetensors")
output_dir = "/Users/home/Documents/Lora_Training/Results/Merges/Anna16_CatAug19/"

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
save_file(merged, "/Users/home/Documents/Lora_Training/Results/Merges/Anna16_CatAug19/Antalina.safetensors")

os.system(f"open {output_dir}")