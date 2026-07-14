#!/usr/bin/env python3
"""
Splits a merged caption file (format: filename.txt on its own line,
followed by caption text, blank line, repeat) into individual .txt files.
"""
import os

input_file = "/Users/home/Documents/Lora_Training/Datasets/SACH/SACH_B2/TA_Caption/SACH-dataset-merged-OPT.txt"
output_dir = "/Users/home/Documents/Lora_Training/Datasets/SACH/SACH_B2/TA_Caption/"

with open(input_file, "r", encoding="utf-8") as f:
    content = f.read()

blocks = content.strip().split("\n\n")
count = 0

for block in blocks:
    lines = block.strip().split("\n")
    if len(lines) < 2:
        continue
    filename = lines[0].strip()
    caption = "\n".join(lines[1:]).strip()
    if not filename.endswith(".txt"):
        continue
    out_path = os.path.join(output_dir, filename)
    with open(out_path, "w", encoding="utf-8") as out:
        out.write(caption)
    count += 1
    print(f"Wrote {out_path}")

print(f"\nDone — {count} files written.")