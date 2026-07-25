#!/usr/bin/env python3
"""
ComfyUI Batch Processor - DJJTB Edition
Processes images through ComfyUI workflows by staging copies in ComfyUI's input folder
Supports single-input and dual-input (e.g. pose transfer) workflows,
plus an icon-batch + IG carousel compositor mode.
"""

import os
import re
import csv
import math
import shutil
import hashlib
import argparse
import json
import copy
import requests
import time
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import djjtb.utils as djj

# ComfyUI server address
COMFYUI_URL = "http://127.0.0.1:8188"

# ComfyUI input folder
COMFYUI_INPUT_FOLDER = "/Users/home/Documents/ai_models/ComfyUI_App/ComfyUI/input"

# Default workflow folders
DEFAULT_WORKFLOW_FOLDER      = "/Volumes/Movies_2SSD/ComfyUI.bak/user/default/workflows/API"
DEFAULT_WORKFLOW_FOLDER_QWEN = "/Volumes/Movies_2SSD/ComfyUI.bak/user/default/workflows/API/Qwen_CN"

# Log file location
LOG_FOLDER       = Path("/Users/home/Documents/Scripts/DJJTB/djjtb/logs/comfyui_batch_logs")
JOB_COUNTER_FILE = LOG_FOLDER / "job_counter.txt"

# Supported image formats
IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.bmp']

# Wait time between submissions (seconds)
QUEUE_DELAY = 1

# Default node IDs for the Qwen pose-transfer workflow
QWEN_SOURCE_NODE_ID = "151"   # LoadImageReturnFilename — subject (OG)
QWEN_POSE_NODE_ID   = "162"   # LoadImageReturnFilename — pose reference

# KSampler node ID and steps config
KSAMPLER_NODE_ID    = "3"
KSAMPLER_STEPS_IDX  = 2       # index of 'steps' in widgets_values
DEFAULT_STEPS       = 4

# ─────────────────────────────────────────────────────────────────────────────
#  Icon-Batch + Carousel Compositor config
# ─────────────────────────────────────────────────────────────────────────────

# ComfyUI writes finished renders here — assumed sibling of COMFYUI_INPUT_FOLDER.
# Confirm this matches your actual ComfyUI output dir if things don't line up.
COMFYUI_OUTPUT_FOLDER = "/Users/home/Documents/ai_models/ComfyUI_App/ComfyUI/output"

ICON_CACHE_DIR        = Path("/Users/home/Documents/Scripts/DJJTB_output/comfyui_icon_cache")
ICON_CACHE_IMAGES_DIR = ICON_CACHE_DIR / "icons"
ICON_CACHE_MANIFEST   = ICON_CACHE_DIR / "manifest.json"

ICON_GEN_RESOLUTION  = 768
ICON_DEFAULT_STEPS   = 8
ICON_DEFAULT_CFG     = 3.5
ICON_FIXED_SEED      = 42          # same seed every icon — consistency over variety
ICON_GEN_TIMEOUT     = 180         # seconds to wait for a batch of pending icons
ICON_POLL_INTERVAL   = 2

ICON_CANVAS_SIZE     = 1080        # square, matches current IG carousel format
ICON_CANVAS_BG       = (255, 255, 255)  # must match the background named in the prompt below
ICON_DEFAULT_COLUMNS = 6

ICON_POSITIVE_TEMPLATE = (
    "a simple flat icon illustration of {label}, minimalist, clean lines, "
    "centered composition, plain solid white background, vector art style"
)
ICON_NEGATIVE_PROMPT = (
    "photo, photorealistic, text, watermark, signature, blurry, "
    "complex background, gradient background, shadow, 3d render, cluttered"
)

# Node IDs inside the workflow this script builds itself (see build_icon_workflow) —
# hardcoded because we own the graph, unlike the Qwen node IDs above which belong
# to a pre-made workflow file.
ICON_NODE_IDS = {"positive": "2", "save": "7"}

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/NotoSansSC-Regular.otf",
    "/Library/Fonts/NotoSansSC-Regular.otf",
    str(Path.home() / "Library/Fonts/NotoSansSC-Regular.otf"),
    "/System/Library/Fonts/Supplemental/SourceHanSansSC-Regular.otf",
    "/Library/Fonts/SourceHanSansSC-Regular.otf",
    str(Path.home() / "Library/Fonts/SourceHanSansSC-Regular.otf"),
]


# ─────────────────────────────────────────────────────────────────────────────
#  Job ID / logging
# ─────────────────────────────────────────────────────────────────────────────

def get_next_job_id():
    LOG_FOLDER.mkdir(parents=True, exist_ok=True)
    if JOB_COUNTER_FILE.exists():
        try:
            with open(JOB_COUNTER_FILE, 'r') as f:
                current_id = int(f.read().strip())
        except Exception:
            current_id = 0
    else:
        current_id = 0
    next_id = current_id + 1
    with open(JOB_COUNTER_FILE, 'w') as f:
        f.write(str(next_id))
    return f"{next_id:05d}"


def get_todays_log_file():
    LOG_FOLDER.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    return LOG_FOLDER / f"{today}.log"


def log_job(job_id, workflow_path, mode_label, pairs, steps_override=None):
    """Log job info to today's log file.
    pairs = list of (src, ref) tuples  OR  plain strings/Path objects (single-input,
    or descriptive labels like "Category (18 items)" for icon-batch mode).
    """
    log_file  = get_todays_log_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry  = f"\n{'=' * 70}\n"
    log_entry += f"JOB ID:        {job_id}\n"
    log_entry += f"TIME:          {timestamp}\n"
    log_entry += f"WORKFLOW:      {Path(workflow_path).name}\n"
    log_entry += f"WORKFLOW PATH: {workflow_path}\n"
    log_entry += f"MODE:          {mode_label}\n"
    if steps_override is not None:
        log_entry += f"STEPS:         {steps_override} (overridden)\n"
    log_entry += f"TOTAL JOBS:    {len(pairs)}\n"
    log_entry += "PAIRS:\n"

    for i, pair in enumerate(pairs, 1):
        if isinstance(pair, tuple):
            src, ref = pair
            log_entry += f"  {i:3}. SOURCE: {Path(src).name}  |  POSE REF: {Path(ref).name}\n"
        else:
            log_entry += f"  {i:3}. {pair}\n"

    log_entry += f"{'=' * 70}\n"

    with open(log_file, 'a') as f:
        f.write(log_entry)

    return log_file


# ─────────────────────────────────────────────────────────────────────────────
#  Image / path input helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_images_from_folder(folder_path, include_subfolders=False):
    """Return a sorted list of image Paths from a folder."""
    folder = Path(folder_path)
    images = []
    if not folder.exists():
        print(f"❌ \033[93mFolder not found:\033[0m {folder_path}")
        return images
    if include_subfolders:
        for root, _, files in os.walk(folder):
            for f in files:
                if any(f.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                    images.append(Path(root) / f)
    else:
        for f in folder.iterdir():
            if f.is_file() and any(f.name.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                images.append(f)
    return sorted(images)


def get_image_list_input(label):
    """
    Ask user: folder OR individual files.
    Returns a sorted list of Path objects.
    """
    print()
    mode = djj.prompt_choice(
        f"\033[93m{label} — input method:\033[0m\n1. Folder\n2. Individual files",
        ['1', '2'],
        default='1'
    )
    print()

    if mode == '1':
        folder = djj.get_path_input(f"📁 Folder path for {label}")
        print()
        include_sub = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        images = get_images_from_folder(folder, include_sub)
        if not images:
            print(f"❌ \033[93mNo images found in folder.\033[0m")
        return images
    else:
        print(f"\033[93mEnter file paths for {label}, one per line.\033[0m")
        print("\033[93mPress Enter on an empty line when done.\033[0m")
        paths = []
        while True:
            raw = input(" > ").strip().strip("'\"")
            if not raw:
                break
            p = Path(raw)
            if p.exists() and p.is_file():
                paths.append(p)
                print(f"  ✅ \033[92mAdded:\033[0m {p.name}")
            else:
                print(f"  ⚠️  \033[93mNot found, skipped:\033[0m {raw}")
        return sorted(paths)


def get_single_image_input(label):
    """Ask for one image path. Returns Path or None."""
    print()
    raw = djj.get_path_input(f"🖼️  {label} image path")
    print()
    p = Path(raw)
    if not p.exists() or not p.is_file():
        print(f"❌ \033[93mFile not found:\033[0m {raw}")
        return None
    return p


def prompt_steps_override():
    """
    Ask user if they want to override KSampler steps.
    Returns an int if overriding, or None to leave workflow as-is.
    """
    print()
    override = djj.prompt_choice(
        f"\033[93m⚡ Override KSampler steps?\033[0m (node {KSAMPLER_NODE_ID})\n1. Yes\n2. No (use workflow default)",
        ['1', '2'],
        default='2'
    )
    print()
    if override == '2':
        return None

    raw = djj.get_string_input(
        f"\033[93m🔢 Steps\033[0m (default: {DEFAULT_STEPS}):\n > ",
        default=str(DEFAULT_STEPS)
    )
    print()
    try:
        steps = int(raw)
        print(f"✅ \033[92mSteps set to:\033[0m {steps}")
        return steps
    except (ValueError, TypeError):
        print(f"⚠️  \033[93mInvalid input, using default:\033[0m {DEFAULT_STEPS}")
        return DEFAULT_STEPS


# ─────────────────────────────────────────────────────────────────────────────
#  Workflow file selector
# ─────────────────────────────────────────────────────────────────────────────

def select_workflow_from_folder(folder_path):
    selected = djj.pick_single_from_folder(folder_path, ('.json',), label="workflow")
    return str(selected) if selected else None


# ─────────────────────────────────────────────────────────────────────────────
#  Dual-input pair builders  (5 modes)
# ─────────────────────────────────────────────────────────────────────────────

def build_pairs_mode1():
    """1 source → many pose refs"""
    source = get_single_image_input("source subject")
    if not source:
        return None, None
    refs = get_image_list_input("pose references (targets)")
    if not refs:
        return None, None
    return [(source, ref) for ref in refs], f"1 source → {len(refs)} targets"


def build_pairs_mode2():
    """1 source → 1 pose ref"""
    source = get_single_image_input("source subject")
    if not source:
        return None, None
    ref = get_single_image_input("pose reference (target)")
    if not ref:
        return None, None
    return [(source, ref)], "1 source → 1 target"


def build_pairs_mode3():
    """Many sources → 1 pose ref"""
    sources = get_image_list_input("sources (subjects)")
    if not sources:
        return None, None
    ref = get_single_image_input("pose reference (target)")
    if not ref:
        return None, None
    return [(src, ref) for src in sources], f"{len(sources)} sources → 1 target"


def build_pairs_mode4():
    """Many sources → many pose refs (paired by sort order)"""
    print()
    print("\033[93m⚠️  Many-to-many mode: files are paired by sorted filename order.\033[0m")
    print("\033[93m   Make sure both sets have matching counts and are named accordingly.\033[0m")
    sources = get_image_list_input("sources (subjects)")
    if not sources:
        return None, None
    refs = get_image_list_input("pose references (targets)")
    if not refs:
        return None, None
    if len(sources) != len(refs):
        count = min(len(sources), len(refs))
        print(f"\n⚠️  \033[93mCount mismatch: {len(sources)} sources vs {len(refs)} refs. "
              f"Pairing the first {count} from each.\033[0m")
        sources = sources[:count]
        refs    = refs[:count]
    pairs = list(zip(sources, refs))
    return pairs, f"{len(pairs)} sources → {len(pairs)} targets (paired)"


def build_pairs_mode5():
    """Full matrix: every source × every pose ref (itertools.product)"""
    from itertools import product
    print()
    print("\033[93m⚠️  Full matrix mode: every source will be paired with every pose ref.\033[0m")
    print("\033[93m   e.g. 4 sources × 6 refs = 24 jobs.\033[0m")
    sources = get_image_list_input("sources (subjects)")
    if not sources:
        return None, None
    refs = get_image_list_input("pose references (targets)")
    if not refs:
        return None, None
    pairs = list(product(sources, refs))
    return pairs, f"{len(sources)} sources × {len(refs)} targets = {len(pairs)} jobs (full matrix)"


# ─────────────────────────────────────────────────────────────────────────────
#  ICON BATCH + CAROUSEL COMPOSITOR — helpers
# ─────────────────────────────────────────────────────────────────────────────

def slugify_label(label_en):
    """Deterministic filesystem-safe cache key for an English label."""
    slug = re.sub(r"[^a-z0-9]+", "_", label_en.lower()).strip("_")
    h = hashlib.md5(label_en.encode("utf-8")).hexdigest()[:6]
    return f"{slug}_{h}"[:80]


def load_icon_manifest():
    if ICON_CACHE_MANIFEST.exists():
        try:
            with open(ICON_CACHE_MANIFEST, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_icon_manifest(manifest):
    ICON_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(ICON_CACHE_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def _split_combined_category(value):
    """'Desserts / 甜点' -> ('Desserts', '甜点'). Falls back to using the same
    string for both if there's no ' / ' separator."""
    if "/" in value:
        parts = [p.strip() for p in value.split("/", 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            return parts[0], parts[1]
    return value, value


def load_content_data(data_path):
    """
    Parse a .csv or .json content file into:
      [{"category_en": str, "category_zh": str,
        "items": [{"label_en": str, "label_zh": str}, ...]}, ...]
    """
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    if path.suffix.lower() == ".json":
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        posts = []
        for entry in raw:
            if "category_en" in entry:
                cat_en = entry.get("category_en", "").strip()
                cat_zh = entry.get("category_zh", "").strip()
            else:
                cat_en, cat_zh = _split_combined_category(entry.get("category", ""))
            items = [
                {"label_en": it["label_en"].strip(), "label_zh": it["label_zh"].strip()}
                for it in entry.get("items", [])
            ]
            posts.append({"category_en": cat_en, "category_zh": cat_zh, "items": items})
        return posts

    elif path.suffix.lower() == ".csv":
        grouped = {}
        order = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("category_en"):
                    cat_en = row["category_en"].strip()
                    cat_zh = row.get("category_zh", "").strip()
                else:
                    cat_en, cat_zh = _split_combined_category(row.get("category", ""))
                key = cat_en
                if key not in grouped:
                    grouped[key] = {"category_en": cat_en, "category_zh": cat_zh, "items": []}
                    order.append(key)
                grouped[key]["items"].append({
                    "label_en": row["label_en"].strip(),
                    "label_zh": row["label_zh"].strip(),
                })
        return [grouped[k] for k in order]

    else:
        raise ValueError(f"Unsupported data file type: {path.suffix} (use .csv or .json)")


def build_icon_workflow(checkpoint_name, lora_name=None,
                        steps=ICON_DEFAULT_STEPS, cfg=ICON_DEFAULT_CFG,
                        resolution=ICON_GEN_RESOLUTION, seed=ICON_FIXED_SEED):
    """Build a minimal headless txt2img API-format ComfyUI graph in Python.
    No workflow JSON file needed on disk — this dict goes straight to /prompt.
    """
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": checkpoint_name}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": resolution, "height": resolution, "batch_size": 1}},
    }

    if lora_name:
        wf["8"] = {"class_type": "LoraLoader",
                   "inputs": {"lora_name": lora_name, "strength_model": 1.0, "strength_clip": 1.0,
                              "model": ["1", 0], "clip": ["1", 1]}}
        model_ref = ["8", 0]
        clip_ref  = ["8", 1]
    else:
        model_ref = ["1", 0]
        clip_ref  = ["1", 1]

    wf["2"] = {"class_type": "CLIPTextEncode",
               "inputs": {"text": "", "clip": clip_ref}}   # positive — filled in per icon
    wf["3"] = {"class_type": "CLIPTextEncode",
               "inputs": {"text": ICON_NEGATIVE_PROMPT, "clip": clip_ref}}
    wf["5"] = {"class_type": "KSampler",
               "inputs": {"seed": seed, "steps": steps, "cfg": cfg,
                          "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0,
                          "model": model_ref, "positive": ["2", 0], "negative": ["3", 0],
                          "latent_image": ["4", 0]}}
    wf["6"] = {"class_type": "VAEDecode",
               "inputs": {"samples": ["5", 0], "vae": ["1", 2]}}
    wf["7"] = {"class_type": "SaveImage",
               "inputs": {"images": ["6", 0], "filename_prefix": "djjtb_icon"}}
    return wf


def check_comfyui_connection():
    try:
        return requests.get(f"{COMFYUI_URL}/system_stats", timeout=5).status_code == 200
    except Exception:
        return False


def submit_icon_workflow(workflow_dict):
    try:
        r = requests.post(
            f"{COMFYUI_URL}/prompt",
            json={"prompt": workflow_dict, "client_id": "djjtb_icon_batch"},
            timeout=10
        )
        if r.status_code == 200:
            return True, r.json().get("prompt_id")
        return False, f"HTTP {r.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to ComfyUI"
    except Exception as e:
        return False, str(e)


def get_history_entry(prompt_id):
    try:
        r = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
        if r.status_code == 200:
            return r.json().get(prompt_id)
    except Exception:
        pass
    return None


def save_icon_from_history(history_entry, label, manifest):
    outputs = history_entry.get("outputs", {})
    node_out = outputs.get(ICON_NODE_IDS["save"], {})
    images = node_out.get("images", [])
    if not images:
        return False
    info = images[0]
    src = Path(COMFYUI_OUTPUT_FOLDER) / info.get("subfolder", "") / info["filename"]
    if not src.exists():
        return False
    ICON_CACHE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    slug = slugify_label(label)
    dest = ICON_CACHE_IMAGES_DIR / f"{slug}.png"
    shutil.copy2(src, dest)
    manifest[slug] = {
        "label_en": label,
        "path": str(dest),
        "generated": datetime.now().isoformat(timespec="seconds"),
    }
    return True


def generate_missing_icons(all_labels, checkpoint_name, lora_name, steps, cfg):
    """
    Two-phase batch: submit every cache-miss icon to the ComfyUI queue back-to-back,
    then poll /history for each until it resolves. This lets ComfyUI's own queue do
    the work instead of us waiting on one icon at a time.
    """
    manifest = load_icon_manifest()
    to_generate = [l for l in all_labels if slugify_label(l) not in manifest]

    print(f"\033[93m📦 Icon cache:\033[0m {len(all_labels) - len(to_generate)} hit(s), "
          f"{len(to_generate)} to generate")
    if not to_generate:
        return manifest

    base_workflow = build_icon_workflow(checkpoint_name, lora_name, steps, cfg)

    print(f"\033[93m📤 Submitting {len(to_generate)} icon job(s)...\033[0m")
    pending = {}
    for label in to_generate:
        wf = copy.deepcopy(base_workflow)
        wf[ICON_NODE_IDS["positive"]]["inputs"]["text"] = ICON_POSITIVE_TEMPLATE.format(label=label)
        ok, result = submit_icon_workflow(wf)
        if ok:
            pending[result] = label
        else:
            print(f"  ❌ \033[93mSubmit failed for\033[0m '{label}': {result}")
        time.sleep(QUEUE_DELAY)

    print(f"\033[93m⏳ Waiting for ComfyUI to render {len(pending)} icon(s)...\033[0m")
    start = time.time()
    remaining = dict(pending)
    completed = 0
    while remaining and (time.time() - start) < ICON_GEN_TIMEOUT:
        for prompt_id in list(remaining.keys()):
            entry = get_history_entry(prompt_id)
            if entry is not None:
                label = remaining.pop(prompt_id)
                if save_icon_from_history(entry, label, manifest):
                    completed += 1
                    print(f"  ✅ {label}")
                else:
                    print(f"  ⚠️  \033[93mCouldn't locate output for\033[0m '{label}'")
        if remaining:
            time.sleep(ICON_POLL_INTERVAL)

    if remaining:
        print(f"  ⏰ \033[93m{len(remaining)} icon(s) timed out:\033[0m "
              f"{', '.join(list(remaining.values())[:5])}")

    save_icon_manifest(manifest)
    print(f"\033[92m✅ Icon generation done — {completed}/{len(to_generate)} new icon(s)\033[0m\n")
    return manifest


_font_cache = {}


def get_cjk_font(size):
    """Find a Simplified-Chinese-capable font, asking once if none of the usual
    spots have one, then reusing that answer for the rest of the run."""
    if size in _font_cache:
        return _font_cache[size]

    if "_resolved_path" not in _font_cache:
        found = None
        for candidate in FONT_CANDIDATES:
            if Path(candidate).exists():
                found = candidate
                break
        if not found:
            print("\033[93m⚠️  No Noto Sans SC / Source Han Sans found in the usual spots.\033[0m")
            found = djj.get_path_input("Enter path to a .ttf/.otf font that supports Simplified Chinese")
        _font_cache["_resolved_path"] = found

    font = ImageFont.truetype(_font_cache["_resolved_path"], size)
    _font_cache[size] = font
    return font


def composite_carousel_pages(category_en, category_zh, items, manifest, output_dir, columns=6):
    """Render one or more square carousel pages for a category. Auto-paginates
    if the item count won't fit at a reasonable row height for the given columns."""
    canvas_size = ICON_CANVAS_SIZE
    margin = 40
    banner_h = 140
    grid_top = banner_h + margin
    available_h = canvas_size - grid_top - margin
    max_rows = 5
    per_page = columns * max_rows

    pages = [items[i:i + per_page] for i in range(0, len(items), per_page)] or [[]]

    title_font = get_cjk_font(58)
    label_font = get_cjk_font(26)
    page_font  = get_cjk_font(22)

    output_paths = []
    for page_idx, page_items in enumerate(pages, 1):
        canvas = Image.new("RGB", (canvas_size, canvas_size), ICON_CANVAS_BG)
        draw = ImageDraw.Draw(canvas)

        title_text = category_zh or category_en
        bbox = draw.textbbox((0, 0), title_text, font=title_font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((canvas_size - tw) / 2, (banner_h - th) / 2 - bbox[1]), title_text,
                  font=title_font, fill=(30, 30, 30))

        if len(pages) > 1:
            page_label = f"{page_idx}/{len(pages)}"
            draw.text((canvas_size - margin - 50, margin // 2), page_label,
                      font=page_font, fill=(140, 140, 140))

        rows_needed = max(1, math.ceil(len(page_items) / columns)) if page_items else 1
        cell_w = (canvas_size - 2 * margin) / columns
        cell_h = available_h / rows_needed
        icon_size = int(min(cell_w, cell_h) * 0.55)

        for idx, it in enumerate(page_items):
            row, col = divmod(idx, columns)
            cx = margin + col * cell_w + cell_w / 2
            cy = grid_top + row * cell_h + cell_h * 0.38

            slug = slugify_label(it["label_en"])
            entry = manifest.get(slug)
            if entry and Path(entry["path"]).exists():
                icon_img = Image.open(entry["path"]).convert("RGB")
                icon_img = icon_img.resize((icon_size, icon_size), Image.LANCZOS)
                canvas.paste(icon_img, (int(cx - icon_size / 2), int(cy - icon_size / 2)))
            else:
                draw.rectangle(
                    [cx - icon_size / 2, cy - icon_size / 2, cx + icon_size / 2, cy + icon_size / 2],
                    outline=(200, 200, 200), width=2
                )

            label_text = it["label_zh"]
            lbbox = draw.textbbox((0, 0), label_text, font=label_font)
            lw = lbbox[2] - lbbox[0]
            draw.text((cx - lw / 2, cy + icon_size / 2 + 10), label_text,
                      font=label_font, fill=(50, 50, 50))

        out_name = f"{slugify_label(category_en)}_{page_idx}.png"
        out_path = Path(output_dir) / out_name
        canvas.save(out_path, "PNG", quality=95)
        output_paths.append(out_path)

    return output_paths


def run_icon_batch_mode(cli_data_path=None):
    print()
    print("\033[92m" + "=" * 50 + "\033[0m")
    print("\033[1;33mIcon Batch + Carousel Compositor\033[0m")
    print("\033[92m" + "=" * 50 + "\033[0m")
    print()

    if cli_data_path:
        data_path = cli_data_path
        print(f"📄 \033[93mData file (from --data):\033[0m {data_path}")
    else:
        data_path = djj.get_path_input("📄 Enter content data file path (.csv or .json)")
    print()

    try:
        posts = load_content_data(data_path)
    except Exception as e:
        print(f"❌ \033[93mFailed to parse data file:\033[0m {e}")
        return

    if not posts:
        print("❌ \033[93mNo posts found in data file.\033[0m")
        return

    total_items = sum(len(p["items"]) for p in posts)
    print(f"✅ \033[92mLoaded\033[0m {len(posts)} categor{'y' if len(posts) == 1 else 'ies'}, "
          f"{total_items} item(s) total")
    for p in posts[:5]:
        print(f"   • {p['category_en']} ({len(p['items'])} items)")
    if len(posts) > 5:
        print(f"   ... and {len(posts) - 5} more")
    print()

    print("🔍 \033[93mChecking ComfyUI connection...\033[0m")
    if not check_comfyui_connection():
        print(f"❌ \033[93mCannot connect to ComfyUI at\033[0m {COMFYUI_URL}")
        return
    print("✅ \033[92mConnected\033[0m\n")

    checkpoint_name = djj.get_string_input(
        "\033[93m🧠 Checkpoint filename (in models/checkpoints/):\033[0m\n > "
    )
    lora_name = djj.get_string_input(
        "\033[93m🎨 LoRA filename, blank for none (in models/loras/):\033[0m\n > ",
        default=""
    )
    lora_name = lora_name if lora_name else None
    print()

    param_choice = djj.prompt_choice(
        f"\033[93m⚡ Steps/CFG:\033[0m\n"
        f"1. Use defaults ({ICON_DEFAULT_STEPS} steps, cfg {ICON_DEFAULT_CFG})\n"
        f"2. Custom\n",
        ['1', '2'], default='1'
    )
    if param_choice == '2':
        steps = djj.get_int_input("Steps", min_val=1, max_val=150)
        cfg = djj.get_float_input("CFG", min_val=0.5, max_val=30.0)
    else:
        steps, cfg = ICON_DEFAULT_STEPS, ICON_DEFAULT_CFG
    print()

    col_choice = djj.prompt_choice(
        "\033[93m📐 Grid columns:\033[0m\n1. 4\n2. 5\n3. 6 (default)\n4. Custom\n",
        ['1', '2', '3', '4'], default='3'
    )
    col_map = {'1': 4, '2': 5, '3': 6}
    if col_choice == '4':
        columns = djj.get_int_input("Columns", min_val=2, max_val=10)
    else:
        columns = col_map[col_choice]
    print()

    all_labels = sorted({it["label_en"] for p in posts for it in p["items"]})
    print(f"\033[93m🖼️  {len(all_labels)} unique icon(s) needed across all posts\033[0m")
    print()

    manifest = generate_missing_icons(all_labels, checkpoint_name, lora_name, steps, cfg)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("/Users/home/Documents/Scripts/DJJTB_output/ig_carousels") / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    job_id = get_next_job_id()
    log_job(
        job_id=job_id,
        workflow_path="(generated icon workflow — no file on disk)",
        mode_label="Icon batch + carousel composite",
        pairs=[f"{p['category_en']} ({len(p['items'])} items)" for p in posts]
    )

    print("\033[1;33m🖼️  Compositing carousels...\033[0m\n")
    all_outputs = []
    for post in posts:
        pages = composite_carousel_pages(
            post["category_en"], post["category_zh"], post["items"],
            manifest, output_dir, columns=columns
        )
        all_outputs.extend(pages)
        print(f"  ✅ {post['category_en']}: {len(pages)} page(s)")

    print()
    print("=" * 50)
    print(f"🏁 \033[1;33mDone —\033[0m {len(all_outputs)} image(s)")
    print(f"📁 \033[93mOutput:\033[0m {output_dir}")
    print("=" * 50)
    djj.prompt_open_folder(output_dir)


def parse_cli_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--mode', choices=['icon-batch'])
    parser.add_argument('--data')
    args, _ = parser.parse_known_args()
    return args


# ─────────────────────────────────────────────────────────────────────────────
#  Core processor
# ─────────────────────────────────────────────────────────────────────────────

class ComfyUIBatchProcessor:
    def __init__(self, workflow_path, comfyui_input_folder, job_id=None):
        self.workflow_path        = workflow_path
        self.comfyui_input_folder = Path(comfyui_input_folder)
        self.server_url           = COMFYUI_URL
        self.client_id            = "djjtb_batch_processor"
        self.staged_inputs        = []
        self.job_id               = job_id

    # ── Workflow ──────────────────────────────────────────────────────────

    def load_workflow(self):
        try:
            with open(self.workflow_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ \033[93mWorkflow not found:\033[0m {self.workflow_path}")
            return None
        except json.JSONDecodeError:
            print(f"❌ \033[93mInvalid JSON in workflow file\033[0m")
            return None

    def update_node_image(self, workflow, node_id, filename):
        node_id = str(node_id)
        if node_id in workflow:
            node = workflow[node_id]
            if 'inputs' in node and 'image' in node['inputs']:
                node['inputs']['image'] = filename
            elif 'widgets_values' in node:
                node['widgets_values'][0] = filename
        return workflow

    def update_ksampler_steps(self, workflow, steps):
        """Override the steps value in the KSampler node (widgets_values index 2)."""
        node_id = KSAMPLER_NODE_ID
        if node_id in workflow:
            node = workflow[node_id]
            # Try inputs dict first (API format)
            if 'inputs' in node and 'steps' in node['inputs']:
                node['inputs']['steps'] = steps
            # Fall back to widgets_values
            elif 'widgets_values' in node and len(node['widgets_values']) > KSAMPLER_STEPS_IDX:
                node['widgets_values'][KSAMPLER_STEPS_IDX] = steps
        return workflow

    # ── Staged input copies ──────────────────────────────────────────────
    # ComfyUI 0.28.2 added a symlink-escape containment check (GHSA-779p) on
    # anything resolved via folder_paths.get_annotated_filepath/exists_annotated_filepath —
    # it realpath()s the target and rejects anything that resolves outside
    # the input folder. That's exactly what a symlink into /Volumes/... does,
    # so plain symlinking here now gets rejected at prompt-validation time.
    # Hard links aren't an option either (source lives on a different volume).
    # Copying is the only thing that satisfies the new check.

    def create_symlink(self, image_path):
        image_path = Path(image_path)
        dest_path  = self.comfyui_input_folder / image_path.name
        try:
            self.comfyui_input_folder.mkdir(parents=True, exist_ok=True)
            if not image_path.exists():
                return False, f"Source not found: {image_path}"
            if dest_path.exists() or dest_path.is_symlink():
                dest_path.unlink()
            shutil.copy2(image_path, dest_path)
            self.staged_inputs.append(dest_path)
            return True, None
        except Exception as e:
            return False, str(e)

    def cleanup_symlinks(self):
        if not self.staged_inputs:
            return
        print()
        print("🧹 \033[93mCleaning up staged copies...\033[0m")
        cleaned = 0
        for sp in self.staged_inputs:
            try:
                if sp.exists() and not sp.is_symlink():
                    sp.unlink()
                    cleaned += 1
            except Exception as e:
                print(f"   ⚠️  \033[93mCould not remove\033[0m {sp.name}: {e}")
        if cleaned > 0:
            print(f"✅ \033[92mRemoved {cleaned} staged copies\033[0m")

    # ── ComfyUI API ───────────────────────────────────────────────────────

    def submit_workflow(self, workflow):
        try:
            r = requests.post(
                f"{self.server_url}/prompt",
                json={"prompt": workflow, "client_id": self.client_id},
                timeout=10
            )
            if r.status_code == 200:
                return True, r.json().get('prompt_id')
            return False, f"HTTP {r.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to ComfyUI"
        except Exception as e:
            return False, str(e)

    def check_comfyui_running(self):
        try:
            return requests.get(f"{self.server_url}/system_stats", timeout=5).status_code == 200
        except Exception:
            return False

    def get_queue_status(self):
        try:
            r = requests.get(f"{self.server_url}/queue", timeout=5)
            if r.status_code == 200:
                d = r.json()
                return len(d.get('queue_running', [])), len(d.get('queue_pending', []))
        except Exception:
            pass
        return 0, 0

    # ── Single-input batch ────────────────────────────────────────────────

    def process_single_input(self, images, node_id, steps_override=None, cleanup_after=False):
        self._print_header()
        if not self.check_comfyui_running():
            print(f"❌ \033[93mCannot connect to ComfyUI at\033[0m {self.server_url}")
            return False
        print(f"✅ \033[92mConnected to ComfyUI\033[0m\n")

        base_workflow = self.load_workflow()
        if not base_workflow:
            return False
        print(f"✅ \033[92mLoaded workflow\033[0m\n")
        print(f"✅ \033[92mFound {len(images)} images\033[0m")
        if steps_override is not None:
            print(f"⚡ \033[92mSteps override:\033[0m {steps_override}")
        self._show_sample(images)

        successful, failed, staged = 0, 0, 0
        self._section("Processing Images")

        for idx, image_path in enumerate(images, 1):
            print(f"\n\033[93m[{idx}/{len(images)}]\033[0m {image_path.name}")

            ok, err = self.create_symlink(image_path)
            if not ok:
                print(f"    ❌ \033[93mCopy failed:\033[0m {err}")
                failed += 1
                continue
            staged += 1
            print(f"    ✅ \033[92mCopied\033[0m")

            wf = copy.deepcopy(base_workflow)
            wf = self.update_node_image(wf, node_id, image_path.name)
            if steps_override is not None:
                wf = self.update_ksampler_steps(wf, steps_override)

            print(f"    📤 \033[93mSubmitting...\033[0m")
            ok, result = self.submit_workflow(wf)
            if ok:
                print(f"    ✅ \033[92mQueued\033[0m (ID: {result})")
                successful += 1
            else:
                print(f"    ❌ \033[93mQueue failed:\033[0m {result}")
                failed += 1

            if idx < len(images):
                time.sleep(QUEUE_DELAY)

        print()
        self._section("Summary")
        print(f"📁 \033[93mInput folder:\033[0m {images[0].parent if images else '-'}")
        print(f"⚙️  \033[93mWorkflow:\033[0m {Path(self.workflow_path).name}")
        if steps_override is not None:
            print(f"⚡ \033[93mSteps:\033[0m {steps_override} (overridden)")
        print(f"🔗 \033[93mCopies staged:\033[0m {staged}")
        print(f"✅ \033[92mSuccessfully queued:\033[0m {successful}")
        if failed > 0:
            print(f"❌ \033[93mFailed:\033[0m {failed}")
        self._footer(cleanup_after)
        return True

    # ── Dual-input batch ──────────────────────────────────────────────────

    def process_dual_input(self, pairs, source_node_id, ref_node_id, mode_label,
                           steps_override=None, cleanup_after=False):
        self._print_header()
        if not self.check_comfyui_running():
            print(f"❌ \033[93mCannot connect to ComfyUI at\033[0m {self.server_url}")
            return False
        print(f"✅ \033[92mConnected to ComfyUI\033[0m\n")

        base_workflow = self.load_workflow()
        if not base_workflow:
            return False
        print(f"✅ \033[92mLoaded workflow\033[0m")
        print(f"✅ \033[92mMode: {mode_label}\033[0m")
        if steps_override is not None:
            print(f"⚡ \033[92mSteps override:\033[0m {steps_override}")
        print(f"✅ \033[92m{len(pairs)} job(s) to submit\033[0m\n")

        successful, failed = 0, 0
        self._section("Processing Pairs")

        for idx, (source_path, ref_path) in enumerate(pairs, 1):
            source_path = Path(source_path)
            ref_path    = Path(ref_path)
            print(f"\n\033[93m[{idx}/{len(pairs)}]\033[0m")
            print(f"    📸 \033[93mSource:\033[0m   {source_path.name}")
            print(f"    🕺 \033[93mPose ref:\033[0m {ref_path.name}")

            ok, err = self.create_symlink(source_path)
            if not ok:
                print(f"    ❌ \033[93mSource copy failed:\033[0m {err}")
                failed += 1
                continue

            if ref_path.resolve() != source_path.resolve():
                ok, err = self.create_symlink(ref_path)
                if not ok:
                    print(f"    ❌ \033[93mRef copy failed:\033[0m {err}")
                    failed += 1
                    continue

            print(f"    ✅ \033[92mCopies staged\033[0m")

            wf = copy.deepcopy(base_workflow)
            wf = self.update_node_image(wf, source_node_id, source_path.name)
            wf = self.update_node_image(wf, ref_node_id,    ref_path.name)
            if steps_override is not None:
                wf = self.update_ksampler_steps(wf, steps_override)

            print(f"    📤 \033[93mSubmitting...\033[0m")
            ok, result = self.submit_workflow(wf)
            if ok:
                print(f"    ✅ \033[92mQueued\033[0m (ID: {result})")
                successful += 1
            else:
                print(f"    ❌ \033[93mQueue failed:\033[0m {result}")
                failed += 1

            if idx < len(pairs):
                time.sleep(QUEUE_DELAY)

        print()
        self._section("Summary")
        print(f"⚙️  \033[93mWorkflow:\033[0m {Path(self.workflow_path).name}")
        print(f"🔀 \033[93mMode:\033[0m {mode_label}")
        if steps_override is not None:
            print(f"⚡ \033[93mSteps:\033[0m {steps_override} (overridden)")
        print(f"✅ \033[92mSuccessfully queued:\033[0m {successful}")
        if failed > 0:
            print(f"❌ \033[93mFailed:\033[0m {failed}")
        self._footer(cleanup_after)
        return True

    # ── Print helpers ─────────────────────────────────────────────────────

    def _print_header(self):
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mComfyUI Batch Processor\033[0m")
        if self.job_id:
            print(f"\033[93mJob ID:\033[0m {self.job_id}")
        print("\033[92m==================================================\033[0m")
        print()
        print("🔍 \033[93mChecking ComfyUI connection...\033[0m")

    def _section(self, title):
        print("\033[93m" + "=" * 50 + "\033[0m")
        print(f"\033[1;33m{title}\033[0m")
        print("\033[93m" + "=" * 50 + "\033[0m")

    def _show_sample(self, images, n=5):
        print()
        print("\033[93mSample of images:\033[0m")
        for i, img in enumerate(images[:n], 1):
            print(f"  {i}. {img.name}")
        if len(images) > n:
            print(f"  ... and {len(images) - n} more")
        print()

    def _footer(self, cleanup_after):
        running, pending = self.get_queue_status()
        print(f"📊 \033[93mQueue status:\033[0m {running} running, {pending} pending")
        print()
        print("💡 \033[93mComfyUI will process these images one by one.\033[0m")
        print("   \033[93mMonitor progress in the ComfyUI interface.\033[0m")
        if cleanup_after:
            # Submitting is fast (seconds) but ComfyUI processes the queue one job
            # at a time and each job can take minutes — cleaning up right after the
            # submit loop (the old behavior) deletes staged inputs for jobs still
            # waiting in the queue, not yet processed, causing "No such file or
            # directory" mid-run. Wait for the whole queue to actually drain first.
            print()
            print("⏳ \033[93mWaiting for ComfyUI to finish processing before cleanup...\033[0m")
            waited = 0
            while True:
                running, pending = self.get_queue_status()
                if running == 0 and pending == 0:
                    break
                if waited > 0 and waited % 60 == 0:
                    print(f"   \033[93m...still processing\033[0m ({running} running, {pending} pending, "
                          f"{waited}s elapsed)")
                time.sleep(5)
                waited += 5
            print("✅ \033[92mQueue drained.\033[0m")
            self.cleanup_symlinks()
        else:
            print()
            print("📌 \033[93mNote: Staged copies remain in ComfyUI input folder\033[0m")
            print(f"   \033[93mLocation:\033[0m {self.comfyui_input_folder}")
        print("\033[93m" + "=" * 50 + "\033[0m")
        print()


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    cli_args = parse_cli_args()

    while True:
        os.system('clear')
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mComfyUI Batch Processor\033[0m")
        print("Process images through ComfyUI workflows")
        print("\033[92m==================================================\033[0m")
        print()

        # ── Step 1: workflow type ──────────────────────────────────────────
        default_wf_type = '3' if cli_args.mode == 'icon-batch' else '1'
        workflow_type = djj.prompt_choice(
            "\033[93mWorkflow type:\033[0m\n"
            "1. Single input  (one Load Image node)\n"
            "2. Dual input    (two Load Image nodes — e.g. pose transfer)\n"
            "3. Icon batch + carousel composite (content data file → IG carousel)",
            ['1', '2', '3'],
            default=default_wf_type
        )
        print()

        if workflow_type == '3':
            run_icon_batch_mode(cli_data_path=cli_args.data if cli_args.mode == 'icon-batch' else None)
            action = djj.what_next()
            if action == 'exit':
                break
            continue

        # ── Step 2: workflow file ──────────────────────────────────────────
        if workflow_type == '2':
            workflow_mode = djj.prompt_choice(
                "\033[93mWorkflow selection:\033[0m\n"
                "1. Load from Qwen_CN folder (default)\n"
                "2. Load from API folder\n"
                "3. Custom path",
                ['1', '2', '3'],
                default='1'
            )
            print()
            if workflow_mode == '1':
                workflow_path = select_workflow_from_folder(DEFAULT_WORKFLOW_FOLDER_QWEN)
            elif workflow_mode == '2':
                workflow_path = select_workflow_from_folder(DEFAULT_WORKFLOW_FOLDER)
            else:
                workflow_path = djj.get_path_input("📄 Enter workflow JSON path (API format)")
                print()
        else:
            workflow_mode = djj.prompt_choice(
                "\033[93mWorkflow selection:\033[0m\n"
                "1. Load from default folder\n"
                "2. Custom path",
                ['1', '2'],
                default='1'
            )
            print()
            if workflow_mode == '1':
                workflow_path = select_workflow_from_folder(DEFAULT_WORKFLOW_FOLDER)
            else:
                workflow_path = djj.get_path_input("📄 Enter workflow JSON path (API format)")
                print()

        if not workflow_path:
            print("❌ \033[93mNo workflow selected.\033[0m")
            action = djj.what_next()
            if action == 'exit':
                break
            continue

        # ── Step 3: steps override ─────────────────────────────────────────
        steps_override = prompt_steps_override()

        # ── Step 4: cleanup preference ─────────────────────────────────────
        cleanup_after = djj.prompt_choice(
            "\033[93mCleanup staged copies after processing?\033[0m\n1. Yes\n2. No (leave for review)",
            ['1', '2'],
            default='2'
        ) == '1'
        print()

        # ── Step 5: job ID ─────────────────────────────────────────────────
        job_id = get_next_job_id()
        print(f"🆔 \033[93mJob ID:\033[0m {job_id}")
        print()

        processor = ComfyUIBatchProcessor(
            workflow_path=workflow_path,
            comfyui_input_folder=COMFYUI_INPUT_FOLDER,
            job_id=job_id
        )

        # ══════════════════════════════════════════════════════════════════
        #  SINGLE-INPUT FLOW
        # ══════════════════════════════════════════════════════════════════
        if workflow_type == '1':
            source_folder = djj.get_path_input("📁 Enter source folder path")
            print()

            include_subfolders = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
                ['1', '2'],
                default='2'
            ) == '1'
            print()

            load_image_node = djj.get_string_input(
                "\033[93m🔢 Enter Load Image node ID (default: 232):\033[0m\n > ",
                default='232'
            )
            print()

            images = get_images_from_folder(source_folder, include_subfolders)
            if not images:
                print("❌ \033[93mNo images found. Skipping.\033[0m")
                action = djj.what_next()
                if action == 'exit':
                    break
                continue

            log_file = log_job(
                job_id=job_id,
                workflow_path=workflow_path,
                mode_label="Single input",
                pairs=images,
                steps_override=steps_override
            )
            print(f"📝 \033[93mLogged to:\033[0m {log_file}\n")
            print("\033[1;33m🚀 Starting batch process...\033[0m\n")

            processor.process_single_input(
                images=images,
                node_id=load_image_node,
                steps_override=steps_override,
                cleanup_after=cleanup_after
            )

        # ══════════════════════════════════════════════════════════════════
        #  DUAL-INPUT FLOW
        # ══════════════════════════════════════════════════════════════════
        else:
            print(f"\033[93m🔢 Source node ID\033[0m (default: {QWEN_SOURCE_NODE_ID} — Qwen OG subject):")
            source_node_raw = djj.get_string_input(" > ", default=QWEN_SOURCE_NODE_ID)
            source_node = source_node_raw if source_node_raw else QWEN_SOURCE_NODE_ID
            print()

            print(f"\033[93m🔢 Pose ref node ID\033[0m (default: {QWEN_POSE_NODE_ID} — Qwen POSE):")
            ref_node_raw = djj.get_string_input(" > ", default=QWEN_POSE_NODE_ID)
            ref_node = ref_node_raw if ref_node_raw else QWEN_POSE_NODE_ID
            print()

            print("\033[93mPairing mode:\033[0m")
            print("1. Single source   → multiple targets  (one subject, many pose refs)")
            print("2. Single source   → single target     (one subject, one pose ref)")
            print("3. Multiple sources → single target    (many subjects, one pose ref)")
            print("4. Multiple sources → multiple targets (paired by filename order)")
            print("5. Full matrix     → every source × every target (N×M jobs)")
            print()
            pair_mode = djj.prompt_choice(
                "\033[93mSelect pairing mode\033[0m",
                ['1', '2', '3', '4', '5'],
                default='1'
            )
            print()

            pairs, mode_label = {
                '1': build_pairs_mode1,
                '2': build_pairs_mode2,
                '3': build_pairs_mode3,
                '4': build_pairs_mode4,
                '5': build_pairs_mode5,
            }[pair_mode]()

            if not pairs:
                print("❌ \033[93mNo pairs built. Skipping.\033[0m")
                action = djj.what_next()
                if action == 'exit':
                    break
                continue

            # Preview pairs before confirming
            print()
            print(f"\033[93m📋 {mode_label} — preview (first 5):\033[0m")
            for i, (src, ref) in enumerate(pairs[:5], 1):
                print(f"  {i}. \033[92m{Path(src).name}\033[0m  →  \033[94m{Path(ref).name}\033[0m")
            if len(pairs) > 5:
                print(f"  ... and {len(pairs) - 5} more")
            print()
            print(f"\033[93m📊 Total jobs to queue:\033[0m {len(pairs)}")

            confirm = djj.prompt_choice(
                "\033[93mProceed with these pairs?\033[0m\n1. Yes\n2. No, go back",
                ['1', '2'],
                default='1'
            )
            print()
            if confirm == '2':
                continue

            log_file = log_job(
                job_id=job_id,
                workflow_path=workflow_path,
                mode_label=mode_label,
                pairs=pairs,
                steps_override=steps_override
            )
            print(f"📝 \033[93mLogged to:\033[0m {log_file}\n")
            print("\033[1;33m🚀 Starting batch process...\033[0m\n")

            processor.process_dual_input(
                pairs=pairs,
                source_node_id=source_node,
                ref_node_id=ref_node,
                mode_label=mode_label,
                steps_override=steps_override,
                cleanup_after=cleanup_after
            )

        # ── What next? ─────────────────────────────────────────────────────
        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()