#!/usr/bin/env python3
import torch
from pathlib import Path
import subprocess

# Import the LaMa Generator class (from the repo)
from lamas.models import Generator  # adjust if your repo structure differs

# List of CKPTs to convert
ckpt_paths = [
    Path("/Users/home/Documents/ai_models/LaMa_models/lama-places/big-lama-regular/models/best.ckpt"),
    Path("/Users/home/Documents/ai_models/LaMa_models/lama-places/lama-regular/models/best.ckpt"),
]

# Output directories
output_dirs = [
    ckpt_paths[0].parent / "ncnn",
    ckpt_paths[1].parent / "ncnn",
]

# Ensure output dirs exist
for d in output_dirs:
    d.mkdir(exist_ok=True)

# Conversion loop
for ckpt_path, out_dir in zip(ckpt_paths, output_dirs):
    print(f"\nProcessing {ckpt_path.name}...")

    # Load checkpoint
    ckpt = torch.load(ckpt_path, map_location="cpu")
    state_dict = ckpt.get("state_dict", ckpt)

    # Initialize generator
    model = Generator(
        input_nc=4,
        output_nc=3,
        ngf=64,
        n_downsampling=3,
        n_blocks=18,
        add_out_act=True
    )
    model.load_state_dict(state_dict, strict=False)
    model.eval()

    # Export to ONNX
    onnx_path = out_dir / "model.onnx"
    dummy_input = torch.randn(1, 4, 512, 512)
    torch.onnx.export(model, dummy_input, onnx_path, opset_version=11)
    print(f"Exported ONNX to {onnx_path}")

    # Convert ONNX -> NCNN
    param_path = out_dir / "model.param"
    bin_path = out_dir / "model.bin"
    subprocess.run(["onnx2ncnn", str(onnx_path), str(param_path), str(bin_path)])
    print(f"NCNN model saved to {param_path} and {bin_path}")

print("\n✅ All models converted to NCNN.")