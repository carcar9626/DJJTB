#!/usr/bin/env python3
import os
from pathlib import Path
from pdf2image import convert_from_path

# --- CONFIG ---
input_root = "/Volumes/Movies_8/2017/Chinese_Model_2017/Tuigirl/TuiGirl_01-80_OfficialPDF"   # change this
output_root = "/Volumes/Movies_8/2017/Chinese_Model_2017/Tuigirl/TuiGirl_01-80_OfficialPDF"  # or same as input_root

# --- MAIN ---
for pdf_path in Path(input_root).rglob("*.pdf"):
    rel_dir = pdf_path.parent.relative_to(input_root)
    pdf_name = pdf_path.stem
    output_dir = Path(output_root) / rel_dir / pdf_name
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🛠️ Extracting: {pdf_path}")
    images = convert_from_path(str(pdf_path), fmt="jpg")

    for i, img in enumerate(images, start=1):
        out_name = f"{pdf_name}_{i:02d}.jpg"
        out_path = output_dir / out_name
        img.save(out_path, "JPEG")
    print(f"✅ Done: {output_dir}")

print("🎉 All PDFs processed.")