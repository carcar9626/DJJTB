#!/usr/bin/env python3

import subprocess
import csv
import os
from datetime import datetime

ROOT_FOLDER = "/Volumes/Movies_2SSD/ComfyUI.bak/models/loras"
OUTPUT_CSV = "safetensors_sources.csv"

MODEL_HINTS = {
    "SDXL": ["sdxl", "xl"],
    "SD 1.5": ["sd15", "sd1.5", "v1-5"],
    "SD 2.1": ["sd21", "2.1"],
    "Pony": ["pony"],
    "FLUX": ["flux"],
    "WAN2.1": ["wan21", "wan2.1"],
    "WAN2.2": ["wan22", "wan2.2"],
    "Qwen": ["Qwen"]
}

PREFERRED_DOMAINS = [
    "civitai.com/models",
    "seaart.ai",
    "huggingface.co"
]

def get_mdls_list(path, key):
    try:
        result = subprocess.run(
            ["mdls", "-name", key, "-raw", path],
            capture_output=True,
            text=True
        )
        raw = result.stdout.strip()
        if raw in ("(null)", ""):
            return []
        return [line.strip().strip('"') for line in raw.strip("()").split(",")]
    except Exception:
        return []

def select_primary_url(urls):
    if not urls:
        return ""

    # Prefer non-direct-download URLs
    candidates = [u for u in urls if not u.lower().endswith(".safetensors")]
    if not candidates:
        candidates = urls

    # Prefer known model hosts
    for domain in PREFERRED_DOMAINS:
        for url in candidates:
            if domain in url:
                return url

    return candidates[0]

def detect_base_model(*texts):
    combined = " ".join(t.lower() for t in texts if t)
    for model, hints in MODEL_HINTS.items():
        for hint in hints:
            if hint in combined:
                return model
    return "Unknown"

rows = []

for root, _, files in os.walk(ROOT_FOLDER):
    for file in files:
        if not file.lower().endswith(".safetensors"):
            continue

        full_path = os.path.join(root, file)

        try:
            stat = os.stat(full_path)
            size_bytes = stat.st_size
            size_mb = round(size_bytes / (1024 * 1024), 2)
            created = datetime.fromtimestamp(stat.st_birthtime)

            urls = get_mdls_list(full_path, "kMDItemWhereFroms")
            primary_url = select_primary_url(urls)

            base_model = detect_base_model(
                file,
                root,
                primary_url
            )

            rows.append([
                file,
                full_path,
                created.strftime("%Y-%m-%d %H:%M:%S"),
                size_bytes,
                size_mb,
                base_model,
                primary_url
            ])
        except Exception as e:
            print(f"Skipped {full_path}: {e}")

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "filename",
        "filepath",
        "date_created",
        "size_bytes",
        "size_mb",
        "base_model",
        "source_url"
    ])
    writer.writerows(rows)

print(f"✅ Exported {len(rows)} files to {OUTPUT_CSV}")