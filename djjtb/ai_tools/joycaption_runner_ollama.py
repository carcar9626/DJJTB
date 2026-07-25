#!/usr/bin/env python3
"""
JoyCaption Runner for DJJTB — Ollama backend
Batch image captioning using JoyCaption Beta One, served locally through Ollama
(GGUF, Metal-accelerated) instead of raw HuggingFace weights on CPU.
Output: .txt sidecar files in Output/JoyCaption/ alongside source images

Setup:
    ollama pull user-v4/joycaption-beta
    # (aha2025/llama-joycaption-beta-one-hf-llava returned "file not found" as
    #  of this writing — not a live option, don't waste time on it)
    # No separate venv needed — this script only needs `requests`, which your
    # main DJJTB venv already has.

Notes:
    - Runs through Ollama's REST API (http://localhost:11434) — native Mac
      process, no Docker involved, so plain localhost is correct here.
    - Ollama uses llama.cpp + Metal under the hood, so this should run
      dramatically faster than the old CPU/float32 path — test on a few
      images first to confirm timing and caption quality before trusting it
      for a big overnight batch (it's a community-quantized port, not an
      official release).
    - OLLAMA_MODEL below must exactly match whichever tag you pulled.
"""

import os
import sys
import pathlib
import subprocess
import time
import base64
import requests
from typing import List, Optional

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

# ── Ollama connection ──────────────────────────────────────────────────────────
OLLAMA_URL         = "http://localhost:11434"   # native Mac process, no Docker here
OLLAMA_MODEL       = "user-v4/joycaption-beta"  # must match whatever you `ollama pull`ed

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


def collect_images_from_txt() -> List[str]:
    """Collect images from a txt file listing paths (files and/or folders)."""
    txt_path = djj.get_path_input("Enter txt file path")
    if not os.path.exists(txt_path):
        print("❌ \033[93mFile not found\033[0m")
        return []

    with open(txt_path, "r", encoding="utf-8") as f:
        paths = [line.strip() for line in f if line.strip()]

    images = []
    for path_str in paths:
        path_obj = pathlib.Path(path_str)
        if path_obj.is_file() and path_obj.suffix.lower() in SUPPORTED_EXTS:
            images.append(str(path_obj))
        elif path_obj.is_dir():
            images.extend(djj.collect_images_from_folder(str(path_obj), extensions=SUPPORTED_EXTS))
    return sorted(set(images), key=str.lower)


def txt_exists(image_path: str, output_dir: pathlib.Path) -> bool:
    """Check if a .txt caption already exists in the output dir for this image."""
    stem = pathlib.Path(image_path).stem
    return (output_dir / f"{stem}.txt").exists()


# ── Environment / Setup ────────────────────────────────────────────────────────

def print_setup_instructions():
    print()
    print("\033[92m==================================================\033[0m")
    print("\033[1;93m⚙️  JoyCaption (Ollama) — Setup Required\033[0m")
    print("\033[92m==================================================\033[0m")
    print()
    print("\033[93mRun this in your terminal:\033[0m")
    print()
    print(f"  ollama pull {OLLAMA_MODEL}")
    print()
    print("\033[93mThen make sure Ollama is running (ollama serve, or the menu-bar app).\033[0m")
    print()


def check_dependencies() -> bool:
    """Verify requests is importable and Ollama is reachable."""
    try:
        import requests  # noqa: F401
    except ImportError:
        print("\033[93m❌ Missing package: requests\033[0m")
        print("\033[93m   Run: pip3 install requests\033[0m")
        return False

    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print(f"\033[93m❌ Could not reach Ollama at {OLLAMA_URL}: {e}\033[0m")
        print("\033[93m   Is Ollama running?\033[0m")
        return False

    return True


# ── Model ──────────────────────────────────────────────────────────────────────

class JoyCaptionModel:
    """
    Thin HTTP wrapper around JoyCaption running through Ollama, instead of raw
    HuggingFace weights on CPU. Same public interface (load/caption/unload) as
    before, so process_images() and main() below don't need any changes.
    """

    def __init__(self):
        self.loaded = False

    def load(self) -> bool:
        print("\033[93m📥 Checking Ollama connection...\033[0m")
        print(f"\033[93m   Model:  {OLLAMA_MODEL}\033[0m")
        print(f"\033[93m   Ollama: {OLLAMA_URL}\033[0m")
        print()

        try:
            resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
            resp.raise_for_status()
            available = [m.get("name", "") for m in resp.json().get("models", [])]
            # /api/tags returns "name:tag" (e.g. "user-v4/joycaption-beta:latest") while
            # OLLAMA_MODEL is untagged, so match on the part before the colon too.
            found = any(
                name == OLLAMA_MODEL or name.split(":")[0] == OLLAMA_MODEL
                for name in available
            )
            if not found:
                print(f"\033[93m❌ '{OLLAMA_MODEL}' not found in Ollama.\033[0m")
                if available:
                    print(f"\033[93m   Available models: {', '.join(available)}\033[0m")
                print(f"\033[93m   Run: ollama pull {OLLAMA_MODEL}\033[0m")
                return False
        except Exception as e:
            print(f"\033[93m❌ Could not reach Ollama: {e}\033[0m")
            return False

        print("✅ \033[92mOllama reachable, model available\033[0m")
        print()
        self.loaded = True
        return True

    def caption(
        self,
        image_path: str,
        style_prompt: str,
        character_name: Optional[str] = None,
        max_tokens: int = 300,
    ) -> Optional[str]:
        """
        Generate a caption for a single image via Ollama's /api/chat.

        character_name: if provided, appended to the system prompt so JoyCaption
        can use the subject's name in training captions (standard LoRA technique).
        """
        if not self.loaded:
            return None

        try:
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")

            # System prompt — JoyCaption Beta One uses this to frame its role.
            # Optionally inject character name for LoRA subject captioning.
            system_prompt = "You are a helpful image captioning assistant."
            if character_name:
                system_prompt += (
                    f" The person or character in the image is named {character_name}. "
                    f"Use their name when referring to them in the caption."
                )

            payload = {
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": style_prompt, "images": [image_b64]},
                ],
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.6,
                    "top_p": 0.9,
                },
            }

            resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=180)
            resp.raise_for_status()
            caption = resp.json().get("message", {}).get("content", "").strip()

            return caption if caption else None

        except Exception as e:
            print(f"\n  \033[93m❌ Caption error: {e}\033[0m")
            return None

    def unload(self):
        # Ask Ollama to free the model from memory now rather than waiting out
        # its default keep_alive window. Best-effort — a failure here shouldn't
        # fail the batch that already completed.
        try:
            requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "keep_alive": 0},
                timeout=10,
            )
        except Exception:
            pass
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
    # ── Dependency / Ollama reachability check ─────────────────────────────────
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
        input_mode = djj.prompt_choice(
            "\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n3. Path list from txt file\n",
            ["1", "2", "3"], default="1"
        )
        print()

        src_path = None
        images: List[str] = []

        if input_mode == "1":
            src_path = djj.get_path_input("📁 Enter folder path")
            print()
            include_sub = djj.prompt_choice(
                "📂 Include subfolders?\n1. Yes\n2. No",
                ["1", "2"], default="2"
            ) == "1"
            print()
            images = djj.collect_images_from_folder(src_path, include_sub, extensions=SUPPORTED_EXTS)
            images = djj.apply_skip_list(images, root=src_path)
        elif input_mode == "2":
            raw = input("📁 \033[93mEnter image paths (space-separated):\033[0m\n -> ").strip()
            if not raw:
                print("❌ \033[93mNo file paths provided.\033[0m")
                continue
            images = djj.collect_images_from_paths(raw, extensions=SUPPORTED_EXTS)
            if images:
                src_path = str(pathlib.Path(images[0]).parent)
            print()
        else:
            images = collect_images_from_txt()
            if images:
                src_path = str(pathlib.Path(images[0]).parent)
            print()

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
        djj.prompt_open_folder(str(out_folder) if out_folder.exists() else src_path)

        action = djj.what_next()
        if action == "exit":
            break


if __name__ == "__main__":
    main()
