#!/usr/bin/env python3
"""
Category Sorter for DJJTB
Zero-shot image categorization using CLIP — dedupes near-identical images via
perceptual hashing, classifies the rest against a user-supplied category set,
then renames sorted files sequentially per category.

General-purpose: this script has no hardcoded notion of what it's sorting.
Drop your own *.json files into category_sets/ to add new category sets.
Format: {"categories": ["Label One", "Label Two", ...]}
"""

import os
import sys
import json
import shutil
import re
from pathlib import Path

VENV_PATH = "/Users/home/Documents/ai_models/joytag/jtvenv"
VENV_PYTHON = os.path.join(VENV_PATH, "bin", "python")

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def ensure_venv_and_run():
    if not os.path.exists(VENV_PATH):
        print("❌ \033[93mVirtual environment not found at\033[0m", VENV_PATH)
        return False

    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        current_venv = sys.prefix
        if VENV_PATH in current_venv:
            return True

    if os.path.exists(VENV_PYTHON):
        print("\033[93m🔄 Activating JoyTag environment (CLIP classification)...\033[0m")
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root)
        os.execve(VENV_PYTHON, [VENV_PYTHON] + sys.argv, env)
    else:
        print(f"❌ \033[93mPython executable not found in venv:\033[0m {VENV_PYTHON}")
        return False

try:
    import djjtb.utils as djj
except ImportError as e:
    print(f"❌ \033[93mFailed to import djjtb.utils:\033[0m {e}")
    sys.exit(1)

SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff')
DEFAULT_CATEGORY_SETS_FOLDER = Path(__file__).parent / "category_sets"
HAMMING_THRESHOLD = 5  # phash distance <= this = considered duplicates
CLIP_MODEL_NAME = "openai/clip-vit-large-patch14"

DEVICE = None


def check_dependencies():
    global DEVICE
    print("\033[93m🔍 Checking dependencies...\033[0m")
    try:
        import torch
        import transformers
        import imagehash
        from PIL import Image
    except ImportError as e:
        print(f"❌ \033[93mMissing dependency:\033[0m {e}")
        return False

    DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"✅ \033[93mDevice:\033[0m {DEVICE}")
    print()
    return True


def collect_images(folder, include_subfolders):
    folder = Path(folder)
    images = []
    if include_subfolders:
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if d.lower() != 'categorized']
            for f in files:
                if Path(f).suffix.lower() in SUPPORTED_EXTS:
                    images.append(Path(root) / f)
    else:
        images = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS]
    return sorted(images, key=lambda p: p.name.lower())


def load_categories_from_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ \033[93mFailed to parse JSON:\033[0m {path} ({e})")
        return []
    categories = data.get('categories', [])
    if not isinstance(categories, list) or not categories:
        print(f"❌ \033[93mNo valid 'categories' list in:\033[0m {path}")
        return []
    return [str(c) for c in categories]


def merge_category_sets(json_paths):
    """Merge 'categories' arrays from multiple JSON files, dedupe by exact string, first-occurrence order."""
    merged = []
    seen = set()
    contributions = {}  # filename -> categories it actually contributed (post-dedupe)
    for path in json_paths:
        cats = load_categories_from_json(path)
        added_here = []
        for c in cats:
            if c not in seen:
                seen.add(c)
                merged.append(c)
                added_here.append(c)
        contributions[path.name] = added_here
    return merged, contributions


def get_category_input(logger):
    print("\033[1;93m🏷️  Category Set Selection\033[0m")
    mode = djj.prompt_choice(
        "\033[93mCategory set input mode:\033[0m\n1. Enter JSON file path directly\n2. Pick from default category_sets folder\n",
        ['1', '2'], default='2'
    )
    print()

    if mode == '1':
        json_path = djj.get_path_input("Enter JSON file path")
        categories, contributions = merge_category_sets([Path(json_path)])
    else:
        selected_files = djj.pick_multiple_from_folder(DEFAULT_CATEGORY_SETS_FOLDER, ('.json',), label="category set")
        if not selected_files:
            print("\033[93m❌ No category sets selected.\033[0m")
            sys.exit(1)
        categories, contributions = merge_category_sets(selected_files)

    if not categories:
        print("\033[93m❌ Merged category list is empty — nothing to sort against. Exiting.\033[0m")
        sys.exit(1)

    print(f"✅ \033[92mLoaded {len(categories)} categories from {len(contributions)} file(s):\033[0m")
    logger.info(f"Category set(s) loaded: {len(categories)} total categories from {len(contributions)} file(s)")
    for fname, cats in contributions.items():
        summary = ', '.join(cats) if cats else '(no new categories — all duplicates)'
        print(f"   \033[93m{fname}:\033[0m {summary}")
        logger.info(f"  {fname}: {summary}")
    print()

    return categories


def slugify(label):
    return re.sub(r'\s+', '_', label.strip())


def compute_phash(path):
    from PIL import Image
    import imagehash
    with Image.open(path) as img:
        return imagehash.phash(img.convert('RGB'))


def image_pixel_count(path):
    from PIL import Image
    with Image.open(path) as img:
        w, h = img.size
    return w * h


def dedupe_images(images, output_path, logger):
    print("\033[1;93m🔍 Deduping (perceptual hash)...\033[0m")
    hashes = {}
    for img_path in images:
        try:
            hashes[img_path] = compute_phash(img_path)
        except Exception as e:
            print(f"   ⚠️  \033[93mHash failed for\033[0m {img_path.name}: {e}")
            logger.info(f"HASH_ERROR: {img_path.name} ({e})")

    hashed = list(hashes.keys())
    groups = []
    assigned = set()

    for i, img_a in enumerate(hashed):
        if img_a in assigned:
            continue
        group = [img_a]
        assigned.add(img_a)
        for img_b in hashed[i + 1:]:
            if img_b in assigned:
                continue
            if hashes[img_a] - hashes[img_b] <= HAMMING_THRESHOLD:
                group.append(img_b)
                assigned.add(img_b)
        groups.append(group)

    duplicates_dir = output_path / "_duplicates"
    kept = []

    for group in groups:
        if len(group) == 1:
            kept.append(group[0])
            continue

        def sort_key(p):
            try:
                return (-image_pixel_count(p), p.name.lower())
            except Exception:
                return (0, p.name.lower())

        group_sorted = sorted(group, key=sort_key)
        keeper = group_sorted[0]
        kept.append(keeper)

        duplicates_dir.mkdir(parents=True, exist_ok=True)
        for dup in group_sorted[1:]:
            dist = hashes[keeper] - hashes[dup]
            dest = duplicates_dir / dup.name
            if dest.exists():
                stem, ext = dup.stem, dup.suffix
                n = 1
                while dest.exists():
                    dest = duplicates_dir / f"{stem}_{n}{ext}"
                    n += 1
            shutil.move(str(dup), str(dest))
            msg = f"KEPT: {keeper.name} | DUPLICATE: {dup.name} (hamming distance: {dist})"
            print(f"   \033[93m{msg}\033[0m")
            logger.info(msg)

    print(f"✅ \033[92mDedupe complete:\033[0m {len(kept)} kept, {len(images) - len(kept)} duplicate(s) moved")
    print()
    return kept


def build_category_embeddings(model, processor, categories, device):
    import torch
    prompts = [f"a photo of a {c}" for c in categories]
    inputs = processor(text=prompts, return_tensors="pt", padding=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        text_outputs = model.get_text_features(**inputs)
    # transformers 5.x returns BaseModelOutputWithPooling; .pooler_output holds the projected embedding
    text_features = text_outputs.pooler_output if hasattr(text_outputs, 'pooler_output') else text_outputs
    return text_features / text_features.norm(dim=-1, keepdim=True)


def classify_images(images, categories, output_path, logger):
    if not images:
        print("\033[93m⚠️  No images left to categorize.\033[0m")
        return

    print("\033[1;93m🧠 Loading CLIP model...\033[0m")
    import torch
    from transformers import CLIPModel, CLIPProcessor
    from PIL import Image

    model = CLIPModel.from_pretrained(CLIP_MODEL_NAME)
    processor = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME)
    model = model.to(DEVICE).eval()

    print(f"✅ \033[92mCLIP loaded\033[0m ({CLIP_MODEL_NAME.split('/')[-1]}, device: {DEVICE})")
    print()

    text_features = build_category_embeddings(model, processor, categories, DEVICE)
    logit_scale = model.logit_scale.exp()

    log_entries = []  # (confidence, message) — sorted ascending before writing to log

    for idx, img_path in enumerate(images, 1):
        try:
            image = Image.open(img_path).convert("RGB")
            inputs = processor(images=image, return_tensors="pt")
            inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
            with torch.no_grad():
                image_outputs = model.get_image_features(**inputs)
            image_features = image_outputs.pooler_output if hasattr(image_outputs, 'pooler_output') else image_outputs
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            similarity = (image_features @ text_features.T).squeeze(0)
            probs = torch.softmax(similarity * logit_scale, dim=-1)
            best_idx = int(torch.argmax(probs).item())
            confidence = float(probs[best_idx].item())
            label = categories[best_idx]
            slug = slugify(label)

            dest_dir = output_path / slug
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / img_path.name
            if dest.exists():
                stem, ext = img_path.stem, img_path.suffix
                n = 1
                while dest.exists():
                    dest = dest_dir / f"{stem}_{n}{ext}"
                    n += 1
            shutil.move(str(img_path), str(dest))

            msg = f"{img_path.name} → {label} (confidence: {confidence:.2f})"
            print(f"\033[93m[{idx}/{len(images)}]\033[0m {msg}")
            log_entries.append((confidence, msg))
        except Exception as e:
            print(f"   ❌ \033[93mFailed:\033[0m {img_path.name} ({e})")
            logger.info(f"CLASSIFY_ERROR: {img_path.name} ({e})")

    log_entries.sort(key=lambda x: x[0])
    for _, msg in log_entries:
        logger.info(msg)

    del model, processor
    import gc
    gc.collect()
    if DEVICE == "mps":
        torch.mps.empty_cache()

    print()
    print(f"✅ \033[92mCategorization complete:\033[0m {len(log_entries)} image(s) sorted")
    print()


def rename_categorized_files(output_path, categories):
    print("\033[1;93m🔤 Renaming categorized files...\033[0m")
    slugs = sorted(set(slugify(c) for c in categories))

    for slug in slugs:
        folder = output_path / slug
        if not folder.is_dir():
            continue
        files = sorted(
            [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS],
            key=lambda f: f.name.lower()
        )
        if not files:
            continue

        width = max(3, len(str(len(files))))

        # Two-pass rename (via temp names) avoids collisions between original and final names
        temp_files = []
        for i, f in enumerate(files, 1):
            temp_dest = folder / f".tmp_{i}{f.suffix}"
            f.rename(temp_dest)
            temp_files.append(temp_dest)

        for i, temp_path in enumerate(temp_files, 1):
            final_name = f"{slug}-{str(i).zfill(width)}{temp_path.suffix}"
            temp_path.rename(folder / final_name)

    print("✅ \033[92mRename complete\033[0m")
    print()


def main():
    os.system('clear')

    if not ensure_venv_and_run():
        return

    if not check_dependencies():
        print("\n\033[93mSetup failed\033[0m")
        return

    while True:
        print()
        print("\033[92m" + "=" * 50 + "\033[0m")
        print("\033[1;93mCategory Sorter\033[0m")
        print("🔹 Dedupe (phash) → Categorize (CLIP zero-shot) → Rename")
        print("\033[92m" + "=" * 50 + "\033[0m")
        print()

        try:
            input_folder = djj.get_path_input("Enter folder path")
            print()
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No", ['1', '2'], default='2'
            ) == '1'
            print()

            images = collect_images(input_folder, include_sub)
            if not images:
                print("\033[93m❌ No supported images found.\033[0m")
                action = djj.what_next()
                if action == 'exit':
                    break
                continue

            print(f"✅ \033[92mFound {len(images)} image(s)\033[0m")
            print()

            output_path = Path(input_folder) / "Categorized"
            if output_path.exists() and any(output_path.iterdir()):
                print(f"\033[93m⚠️  Categorized/ already has content from a previous run:\033[0m {output_path}")
                print("\033[93m   Continuing will merge this run's results into it (category folders, _duplicates, and the log will combine).\033[0m")
                proceed = djj.prompt_choice(
                    "\033[93mContinue anyway?\033[0m\n1. Yes, merge into existing Categorized/\n2. No, cancel this run",
                    ['1', '2'], default='2'
                )
                print()
                if proceed == '2':
                    print("\033[93mCancelled.\033[0m")
                    action = djj.what_next()
                    if action == 'exit':
                        break
                    continue

            output_path.mkdir(parents=True, exist_ok=True)
            logger = djj.setup_logging(str(output_path), "category_sorter")

            categories = get_category_input(logger)

            os.system('clear')
            print(f"\033[1;93m🧠 Processing {len(images)} image(s) against {len(categories)} categories\033[0m")
            print("=" * 50)
            print()

            remaining = dedupe_images(images, output_path, logger)
            classify_images(remaining, categories, output_path, logger)
            rename_categorized_files(output_path, categories)

            print("=" * 50)
            print(f"\033[1;93m🏁 Complete!\033[0m")
            print("=" * 50)
            print()

            djj.prompt_open_folder(str(output_path))

            action = djj.what_next()
            if action == 'exit':
                break
        except KeyboardInterrupt:
            print("\n\033[93mCancelled\033[0m")
            break
        except Exception as e:
            print(f"\n❌ {e}")
            import traceback
            traceback.print_exc()
            break


if __name__ == "__main__":
    main()
