#!/usr/bin/env python3
"""
JoyCaption Runner for DJJTB
Batch image captioning using JoyCaption Beta One (fancyfeast/llama-joycaption-beta-one-hf-llava)
Llama 3.1 8B + LLaVA vision head — purpose-built for LoRA training dataset captioning
Output: .txt sidecar files in Output/JoyCaption/ alongside source images

Setup:
    cd /Users/home/Documents/ai_models/joycaption
    python3 -m venv jcvenv
    source jcvenv/bin/activate
    pip3 install torch torchvision torchaudio
    pip3 install transformers>=4.45.0 accelerate pillow huggingface_hub
    # Model downloads automatically on first run (~16GB)
    # Run via launcher: source jcvenv/bin/activate && cd DJJTB && python3 -m djjtb.ai_tools.joycaption_runner

Notes:
    - JoyCaption Beta One uses bfloat16 which MPS does not support
    - Script runs on CPU with PYTORCH_ENABLE_MPS_FALLBACK=1 as safety net
    - On M4 Max 64GB: expect ~20-45s per image on CPU (fine for batch overnight jobs)
    - float32 on CPU is stable and produces identical output quality to bfloat16 on CUDA
"""

import os
import sys
import pathlib
import subprocess
import time
import gc
from typing import List, Optional

# ── MPS fallback env var must be set BEFORE torch imports ──────────────────────
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

# ── Project root path fix (same pattern as joytag_tagger.py) ──────────────────
project_root = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import djjtb.utils as djj
    print("✅ \033[33mDJJTB utils loaded\033[0m")
except ImportError as e:
    print(f"❌ \033[33mFailed to import djjtb.utils:\033[0m {e}")
    sys.exit(1)

os.system('clear')

# ── Paths ──────────────────────────────────────────────────────────────────────
AI_MODELS_DIR      = "/Users/home/Documents/ai_models"
JC_DIR             = os.path.join(AI_MODELS_DIR, "joycaption")
VENV_PATH          = os.path.join(JC_DIR, "jcvenv")
VENV_PYTHON        = os.path.join(VENV_PATH, "bin", "python3")
MODEL_CACHE_DIR    = os.path.join(JC_DIR, "models")
MODEL_ID           = "fancyfeast/llama-joycaption-beta-one-hf-llava"

SUPPORTED_EXTS     = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff")

# ── Caption style prompts (JoyCaption Beta One instruction-style) ──────────────
# These are the prompts you pass as the user message — JoyCaption uses them
# to steer output style. Keep them as-is; they're tuned for the model.
CAPTION_STYLES = {
    "1": {
        "label": "Training Prompt (recommended for LoRA)",
        "prompt": "Write a stable diffusion prompt for this image.",
    },
    "2": {
        "label": "Descriptive Natural Language",
        "prompt": "Write a descriptive caption for this image in a formal tone.",
    },
    "3": {
        "label": "Descriptive (Casual / Relaxed tone)",
        "prompt": "Write a descriptive caption for this image in a casual tone.",
    },
    "4": {
        "label": "Danbooru Tag List",
        "prompt": (
            "Generate only comma-separated Danbooru tags (lowercase_underscores). "
            "Strict order: artist:, copyright:, character:, meta:, then general tags. "
            "Include counts (1girl), appearance, clothing, accessories, pose, expression, "
            "actions, background. Use precise Danbooru syntax. No extra text."
        ),
    },
    "5": {
        "label": "MidJourney Style Prompt",
        "prompt": "Write a MidJourney prompt for this image.",
    },
    "6": {
        "label": "Booru-Style General Tags (no hierarchy)",
        "prompt": (
            "Generate comma-separated booru-style tags for this image. "
            "Include all relevant tags for appearance, clothing, pose, expression, "
            "and background. Use lowercase with underscores."
        ),
    },
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    return f"{seconds/3600:.1f}h"


def collect_images(folder: str, include_subfolders: bool = False) -> List[str]:
    p = pathlib.Path(folder)
    images = []
    if include_subfolders:
        for root, _, files in os.walk(folder):
            for f in files:
                if pathlib.Path(f).suffix.lower() in SUPPORTED_EXTS:
                    images.append(os.path.join(root, f))
    else:
        images = [
            str(f) for f in p.glob("*")
            if f.suffix.lower() in SUPPORTED_EXTS and f.is_file()
        ]
    return sorted(images, key=str.lower)


def txt_exists(image_path: str, output_dir: pathlib.Path) -> bool:
    """Check if a .txt caption already exists in the output dir for this image."""
    stem = pathlib.Path(image_path).stem
    return (output_dir / f"{stem}.txt").exists()


# ── Environment / Setup ────────────────────────────────────────────────────────

def check_venv() -> bool:
    """Confirm we're running inside jcvenv."""
    current = sys.prefix
    if JC_DIR in current and "jcvenv" in current:
        return True
    return False


def print_setup_instructions():
    print()
    print("\033[92m==================================================\033[0m")
    print("\033[1;93m⚙️  JoyCaption — First-Time Setup Required\033[0m")
    print("\033[92m==================================================\033[0m")
    print()
    print("\033[93mRun these commands in your terminal:\033[0m")
    print()
    print(f"  mkdir -p {JC_DIR}")
    print(f"  cd {JC_DIR}")
    print(f"  python3 -m venv jcvenv")
    print(f"  source {VENV_PATH}/bin/activate")
    print(f"  pip3 install torch torchvision torchaudio")
    print(f"  pip3 install 'transformers>=4.45.0' accelerate pillow huggingface_hub")
    print()
    print("\033[93mThen add this to your DJJTB launcher entry:\033[0m")
    print()
    print(f"  source {VENV_PATH}/bin/activate && \\")
    print(f"  cd /Users/home/Documents/Scripts/DJJTB && \\")
    print(f"  python3 -m djjtb.ai_tools.joycaption_runner")
    print()
    print("\033[93m📦 Model (~16GB) downloads automatically on first run.\033[0m")
    print("\033[93m   Make sure you have ~20GB free on your drive.\033[0m")
    print()


def check_dependencies() -> bool:
    """Verify torch and transformers are importable."""
    missing = []
    for pkg in ["torch", "transformers", "PIL", "accelerate"]:
        try:
            __import__("PIL" if pkg == "PIL" else pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"\033[93m❌ Missing packages: {', '.join(missing)}\033[0m")
        print(f"\033[93m   Run: pip3 install {' '.join(missing)}\033[0m")
        return False
    return True


# ── Model ──────────────────────────────────────────────────────────────────────

class JoyCaptionModel:
    """
    Wrapper around JoyCaption Beta One (LLaVA-style VLM).

    Why CPU + float32:
        JoyCaption's inference code casts pixel_values to bfloat16, which MPS
        doesn't support. Running on CPU with float32 is fully stable and produces
        identical caption quality. On M4 Max 64GB this is ~20-45s per image.
        PYTORCH_ENABLE_MPS_FALLBACK=1 is set at module top as extra insurance.
    """

    def __init__(self):
        self.model = None
        self.processor = None
        self.loaded = False

    def load(self) -> bool:
        print("\033[93m📥 Loading JoyCaption Beta One...\033[0m")
        print(f"\033[93m   Model: {MODEL_ID}\033[0m")
        print(f"\033[93m   Cache: {MODEL_CACHE_DIR}\033[0m")
        print("\033[93m   Device: CPU (float32) — bfloat16 not supported on MPS\033[0m")
        print()

        os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
        os.environ["HF_HOME"] = MODEL_CACHE_DIR

        try:
            import torch
            from transformers import LlavaForConditionalGeneration, AutoProcessor

            print("\033[93m   Loading processor...\033[0m")
            self.processor = AutoProcessor.from_pretrained(
                MODEL_ID,
                cache_dir=MODEL_CACHE_DIR,
            )

            print("\033[93m   Loading model weights (~16GB, patience required)...\033[0m")
            self.model = LlavaForConditionalGeneration.from_pretrained(
                MODEL_ID,
                torch_dtype=torch.float32,   # bfloat16 fails on MPS; float32 is safe
                device_map="cpu",            # explicitly CPU — stable on all Mac configs
                cache_dir=MODEL_CACHE_DIR,
            )
            self.model.eval()

            print("✅ \033[92mJoyCaption loaded successfully\033[0m")
            print()
            self.loaded = True
            return True

        except Exception as e:
            print(f"\033[93m❌ Failed to load model: {e}\033[0m")
            return False

    def caption(
        self,
        image_path: str,
        style_prompt: str,
        character_name: Optional[str] = None,
        max_tokens: int = 300,
    ) -> Optional[str]:
        """
        Generate a caption for a single image.

        character_name: if provided, appended to the system prompt so JoyCaption
        can use the subject's name in training captions (standard LoRA technique).
        """
        if not self.loaded:
            return None

        try:
            import torch
            from PIL import Image

            image = Image.open(image_path).convert("RGB")

            # System prompt — JoyCaption Beta One uses this to frame its role.
            # Optionally inject character name for LoRA subject captioning.
            system_prompt = "You are a helpful image captioning assistant."
            if character_name:
                system_prompt += (
                    f" The person or character in the image is named {character_name}. "
                    f"Use their name when referring to them in the caption."
                )

            # Build conversation in the format LLaVA processor expects
            convo = [
                {"role": "system",  "content": system_prompt},
                {"role": "user",    "content": f"<image>\n{style_prompt}"},
            ]

            convo_string = self.processor.apply_chat_template(
                convo, tokenize=False, add_generation_prompt=True
            )

            inputs = self.processor(
                text=[convo_string],
                images=[image],
                return_tensors="pt",
            )

            # Cast to float32 — avoids any bfloat16 remnants from processor
            if "pixel_values" in inputs and inputs["pixel_values"] is not None:
                inputs["pixel_values"] = inputs["pixel_values"].to(torch.float32)

            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    do_sample=True,
                    temperature=0.6,
                    top_p=0.9,
                    top_k=None,
                    suppress_tokens=None,
                    use_cache=True,
                )[0]

            # Trim the prompt tokens off the front of the output
            output_ids = output_ids[inputs["input_ids"].shape[1]:]
            caption = self.processor.tokenizer.decode(
                output_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            ).strip()

            return caption if caption else None

        except Exception as e:
            print(f"\n  \033[93m❌ Caption error: {e}\033[0m")
            return None

    def unload(self):
        if self.model:
            del self.model
            self.model = None
        if self.processor:
            del self.processor
            self.processor = None
        gc.collect()
        self.loaded = False


# ── Processing ─────────────────────────────────────────────────────────────────

def process_images(
    images: List[str],
    model: JoyCaptionModel,
    style_key: str,
    character_name: Optional[str],
    skip_existing: bool,
    max_tokens: int,
):
    style = CAPTION_STYLES[style_key]
    style_prompt = style["prompt"]
    total = len(images)

    success = 0
    skipped = 0
    failed = 0
    batch_start = time.time()

    print()
    print(f"\033[1;93m🚀 Processing {total} image(s)\033[0m")
    print(f"\033[93m   Style: {style['label']}\033[0m")
    if character_name:
        print(f"\033[93m   Character: {character_name}\033[0m")
    print("\033[92m" + "=" * 50 + "\033[0m")
    print()

    for idx, img_path in enumerate(images, 1):
        img_path_obj = pathlib.Path(img_path)
        fname = img_path_obj.name
        stem  = img_path_obj.stem

        # Output goes to Output/JoyCaption/ inside the image's parent folder
        out_dir = img_path_obj.parent / "Output" / "JoyCaption"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_txt = out_dir / f"{stem}.txt"

        pct = int((idx / total) * 100)
        elapsed = time.time() - batch_start
        print(f"\033[93m[{idx}/{total}]\033[0m ({pct}%) {fname}  \033[36m[{format_time(elapsed)}]\033[0m")

        # Skip if .txt already exists and user chose to skip
        if skip_existing and out_txt.exists():
            print(f"  \033[92m⏭️  Skipped (caption exists)\033[0m")
            skipped += 1
            continue

        img_start = time.time()
        caption = model.caption(img_path, style_prompt, character_name, max_tokens)
        img_time = time.time() - img_start

        if caption:
            try:
                out_txt.write_text(caption, encoding="utf-8")
                # Show a short preview of the caption
                preview = caption[:80] + "..." if len(caption) > 80 else caption
                print(f"  \033[92m✅ {format_time(img_time)}\033[0m  \"{preview}\"")
                success += 1
            except Exception as e:
                print(f"  \033[93m❌ Write error: {e}\033[0m")
                failed += 1
        else:
            print(f"  \033[93m❌ Caption failed\033[0m")
            failed += 1

        print()

    total_time = time.time() - batch_start
    avg_time   = total_time / max(success, 1)

    print("\033[92m" + "=" * 50 + "\033[0m")
    print(f"\033[1;93m🏁 Complete!\033[0m")
    print(f"  \033[93mProcessed:\033[0m {success}")
    if skipped:
        print(f"  \033[93mSkipped:\033[0m  {skipped}")
    if failed:
        print(f"  \033[93mFailed:\033[0m   {failed}")
    print(f"  \033[93mTotal time:\033[0m {format_time(total_time)}")
    print(f"  \033[93mAvg/image:\033[0m  {format_time(avg_time)}")
    print()

    return success, skipped, failed


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    # ── Venv / dependency check ────────────────────────────────────────────────
    if not check_venv():
        print()
        print("\033[93m⚠️  Not running inside jcvenv.\033[0m")
        print_setup_instructions()
        cont = djj.prompt_choice(
            "Continue anyway (may fail if packages missing)?\n1. Yes\n2. Exit",
            ["1", "2"], default="2"
        )
        if cont != "1":
            sys.exit(0)
        print()

    if not check_dependencies():
        print_setup_instructions()
        sys.exit(1)

    while True:
        os.system('clear')
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mJoyCaption Runner\033[0m")
        print("Batch image captioning — JoyCaption Beta One")
        print("Purpose-built for LoRA training datasets")
        print("\033[92m==================================================\033[0m")
        print()

        # ── Input ──────────────────────────────────────────────────────────────
        folder = djj.get_path_input("📁 Enter folder path")
        print()

        include_sub = djj.prompt_choice(
            "📂 Include subfolders?\n1. Yes\n2. No",
            ["1", "2"], default="2"
        ) == "1"
        print()

        images = collect_images(folder, include_sub)
        images = djj.apply_skip_list(images, root=folder)

        if not images:
            print("\033[93m⚠️  No supported images found.\033[0m")
            action = djj.what_next()
            if action == "exit":
                break
            continue

        print(f"✅ \033[93m{len(images)} image(s) found\033[0m")
        print()

        # ── Skip existing ──────────────────────────────────────────────────────
        # Count how many already have captions
        out_dir_sample = pathlib.Path(images[0]).parent / "Output" / "JoyCaption"
        already_done = sum(
            1 for img in images
            if (pathlib.Path(img).parent / "Output" / "JoyCaption" / (pathlib.Path(img).stem + ".txt")).exists()
        )
        if already_done > 0:
            print(f"\033[93mℹ️  {already_done} image(s) already have captions in Output/JoyCaption/\033[0m")
            skip_existing = djj.prompt_choice(
                "Skip images that already have captions?\n1. Yes (skip)\n2. No (overwrite all)",
                ["1", "2"], default="1"
            ) == "1"
        else:
            skip_existing = False
        print()

        # ── Caption style ──────────────────────────────────────────────────────
        print("\033[93m🎨 Caption Style:\033[0m")
        for k, v in CAPTION_STYLES.items():
            print(f"{k}. {v['label']}")
        style_key = djj.prompt_choice(
            "\033[93mChoice\033[0m",
            list(CAPTION_STYLES.keys()), default="1"
        )
        print()

        # ── Character name (optional, great for LoRA subject naming) ──────────
        print("\033[93m👤 Character / Subject Name (optional):\033[0m")
        print("   Leave blank to skip. If set, JoyCaption will use this name")
        print("   when referring to the subject — useful for LoRA trigger words.")
        char_raw = input("   Name (or press Enter to skip): ").strip()
        character_name = char_raw if char_raw else None
        print()

        # ── Max tokens ────────────────────────────────────────────────────────
        tok_raw = input(
            "\033[93m📝 Max caption length in tokens [default 300, range 50-500]:\n\033[0m -> "
        ).strip()
        try:
            max_tokens = max(50, min(500, int(tok_raw))) if tok_raw else 300
        except ValueError:
            max_tokens = 300
        print()

        # ── Summary before load ────────────────────────────────────────────────
        to_process = [
            img for img in images
            if not (skip_existing and (
                pathlib.Path(img).parent / "Output" / "JoyCaption" / (pathlib.Path(img).stem + ".txt")
            ).exists())
        ]

        print("\033[92m==================================================\033[0m")
        print(f"  \033[93mImages total:\033[0m     {len(images)}")
        print(f"  \033[93mTo caption:\033[0m       {len(to_process)}")
        print(f"  \033[93mStyle:\033[0m            {CAPTION_STYLES[style_key]['label']}")
        if character_name:
            print(f"  \033[93mCharacter name:\033[0m   {character_name}")
        print(f"  \033[93mMax tokens:\033[0m       {max_tokens}")
        print(f"  \033[93mDevice:\033[0m           CPU (float32)")
        print(f"  \033[93mEst. time:\033[0m        ~{format_time(len(to_process) * 35)} "
              f"(~35s/img estimate, actual varies)")
        print("\033[92m==================================================\033[0m")
        print()

        if not to_process:
            print("\033[92m🎉 All images already captioned. Nothing to do.\033[0m")
            djj.prompt_open_folder(
                str(pathlib.Path(images[0]).parent / "Output" / "JoyCaption")
            )
            action = djj.what_next()
            if action == "exit":
                break
            continue

        confirm = djj.prompt_choice(
            "▶️  Ready — load model and begin?\n1. Yes\n2. Cancel",
            ["1", "2"], default="1"
        )
        print()
        if confirm != "1":
            action = djj.what_next()
            if action == "exit":
                break
            continue

        # ── Load model ─────────────────────────────────────────────────────────
        model = JoyCaptionModel()
        if not model.load():
            print("\033[93m❌ Model failed to load. Check setup instructions.\033[0m")
            print_setup_instructions()
            action = djj.what_next()
            if action == "exit":
                break
            continue

        # ── Process ────────────────────────────────────────────────────────────
        success, skipped_count, failed = process_images(
            images, model, style_key, character_name, skip_existing, max_tokens
        )

        # ── Cleanup ────────────────────────────────────────────────────────────
        print("\033[93m🧹 Unloading model...\033[0m")
        model.unload()
        print()

        # ── Open output ────────────────────────────────────────────────────────
        # Point to the Output/JoyCaption folder of the first image's parent
        out_folder = pathlib.Path(images[0]).parent / "Output" / "JoyCaption"
        djj.prompt_open_folder(str(out_folder) if out_folder.exists() else folder)

        action = djj.what_next()
        if action == "exit":
            break


if __name__ == "__main__":
    main()
