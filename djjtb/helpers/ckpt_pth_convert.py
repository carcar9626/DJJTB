from pathlib import Path
import torch
import pytorch_lightning as pl

ckpt_path = Path("/Users/home/Documents/ai_models/LaMa_models/lama-places/lama-regular/models/best.ckpt")
output_path = Path("/Users/home/Documents/ai_models/LaMa_models/lama-places/lama-regular/models/lama-regular.pth")

# Load the checkpoint safely with Lightning
ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)

# Extract state_dict if present
if "state_dict" in ckpt:
    torch.save(ckpt["state_dict"], output_path)
else:
    torch.save(ckpt, output_path)