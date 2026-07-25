#!/usr/bin/env python3
"""
Vocab + Mask Generator for DJJTB
Detects text regions (word/phrase + bounding box) in vocab grid images using
Tesseract OCR, optionally saves the results as JSON, optionally generates
B&W inpainting masks from those regions. No translation, no API, no model
loading — pure local detection.
Category: ai_tools

Setup (one-time):
    brew install tesseract
    source ~/Documents/Scripts/DJJTB/venv/bin/activate
    pip install pytesseract
"""

import os
import sys
import shutil
import json
from pathlib import Path
from PIL import Image, ImageDraw
import djjtb.utils as djj

os.system('clear')

SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')

# Words/lines below this confidence (0-100) are dropped as noise
TESS_MIN_CONFIDENCE = 40

# --psm 11 = sparse text, no assumed layout order — fits a grid of scattered
# labels much better than Tesseract's default paragraph-flow assumption.
# Try --psm 6 instead if a particular layout gives poor results.
TESS_CONFIG = "--psm 11"

# Grid layouts often have icon artwork with text baked into it, sitting above
# each label. PSM can't tell "decorative icon text" apart from "caption text"
# — both just look like text to Tesseract. So instead we filter by position
# after detection: each grid row is treated as a vertical band, and only text
# whose center falls in the bottom portion of that band survives.
# 0.55 = bottom 45% of each cell counts as the label zone.
# Raise it if labels are still getting cut, lower it if icon text still slips through.
LABEL_ZONE_START = 0.55


# ─── Tesseract availability check ─────────────────────────────────────────────

def verify_tesseract():
    if shutil.which("tesseract") is None:
        print("❌ \033[93mTesseract binary not found on PATH.\033[0m")
        print("   Install it with: \033[92mbrew install tesseract\033[0m")
        return False
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        print("❌ \033[93mpytesseract not installed in this venv.\033[0m")
        print("   Install it with: \033[92mpip install pytesseract\033[0m")
        return False
    return True


# ─── OCR + Bounding Box Extraction ────────────────────────────────────────────

def extract_text_regions(image_path):
    """
    Run Tesseract OCR, group words into lines, return the shared data shape:
    {"items": [{"text": str, "bbox": [ymin, xmin, ymax, xmax] (0-1000 normalized)}]}
    """
    import pytesseract
    from pytesseract import Output

    image = Image.open(image_path).convert("RGB")
    width, height = image.size

    data = pytesseract.image_to_data(image, config=TESS_CONFIG, output_type=Output.DICT)

    lines = {}  # (block_num, par_num, line_num) -> accumulated box + words
    n = len(data['text'])

    for i in range(n):
        text = data['text'][i].strip()
        try:
            conf = int(float(data['conf'][i]))
        except (ValueError, TypeError):
            conf = -1
        if not text or conf < TESS_MIN_CONFIDENCE:
            continue

        key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
        left, top = data['left'][i], data['top'][i]
        right, bottom = left + data['width'][i], top + data['height'][i]

        if key not in lines:
            lines[key] = {"words": [], "left": left, "top": top, "right": right, "bottom": bottom}

        entry = lines[key]
        entry["words"].append(text)
        entry["left"] = min(entry["left"], left)
        entry["top"] = min(entry["top"], top)
        entry["right"] = max(entry["right"], right)
        entry["bottom"] = max(entry["bottom"], bottom)

    items = []
    for entry in lines.values():
        norm_bbox = [
            int(entry["top"] / height * 1000),
            int(entry["left"] / width * 1000),
            int(entry["bottom"] / height * 1000),
            int(entry["right"] / width * 1000)
        ]
        items.append({"text": " ".join(entry["words"]), "bbox": norm_bbox})

    return {"items": items}


def filter_label_items(items, rows, label_zone_start=LABEL_ZONE_START):
    """
    Keep only items whose vertical center falls in the label zone (bottom
    portion) of their grid row's band. Discards text detected inside icon
    artwork. Only row count matters here — columns don't affect vertical
    banding, so a 5x5 or 5x3 grid is filtered identically.
    """
    if rows < 1:
        return items

    cell_height = 1000 / rows
    filtered = []

    for item in items:
        ymin, xmin, ymax, xmax = item["bbox"]
        y_center = (ymin + ymax) / 2
        row_index = min(int(y_center // cell_height), rows - 1)
        row_top = row_index * cell_height
        relative_y = (y_center - row_top) / cell_height

        if relative_y >= label_zone_start:
            filtered.append(item)

    return filtered


# Row spacing tolerance (0-1000 normalized units) for grouping detections into
# rows by y-proximity. Real label rows in your samples vary ~15-20 units within
# a row, vs ~180 units between rows — 20 gives comfortable separation.
ROW_CLUSTER_TOLERANCE = 20


def group_items_into_rows(items, row_tolerance=ROW_CLUSTER_TOLERANCE):
    """Groups detections into rows by y-center proximity. Returns list of row lists."""
    if not items:
        return []

    def y_center(it):
        return (it["bbox"][0] + it["bbox"][2]) / 2

    sorted_items = sorted(items, key=y_center)
    rows = [[sorted_items[0]]]
    row_y = y_center(sorted_items[0])

    for it in sorted_items[1:]:
        yc = y_center(it)
        if abs(yc - row_y) <= row_tolerance:
            rows[-1].append(it)
            row_y = sum(y_center(i) for i in rows[-1]) / len(rows[-1])  # running mean
        else:
            rows.append([it])
            row_y = yc

    return rows


def filter_sparse_rows(items, min_row_size, row_tolerance=ROW_CLUSTER_TOLERANCE):
    """
    Discards detections that don't belong to a "full" row of aligned items.
    Targets scattered false-positive OCR blobs — Tesseract hallucinating
    text-like shapes out of busy icon artwork (feathers, textures, etc.)
    even when there's no real text there. A genuine label row has ~N items
    (N = column count) all at nearly the same y; noise shows up as isolated
    singles with no row-mates.
    """
    rows = group_items_into_rows(items, row_tolerance)
    kept = []
    for row in rows:
        if len(row) >= min_row_size:
            kept.extend(row)
    return kept


# ─── Mask Generation ──────────────────────────────────────────────────────────

def generate_mask_from_data(data, source_img_path, output_dir):
    """Build a B&W inpainting mask directly from detected text regions."""
    with Image.open(source_img_path) as img:
        width, height = img.size

    mask_canvas = Image.new("L", (width, height), 0)  # solid black canvas
    draw = ImageDraw.Draw(mask_canvas)

    # Header clearance — top ~12% typically houses a category title, if present
    header_clearance_height = int(120 * (height / 1000))
    draw.rectangle([0, 0, width, header_clearance_height], fill=255)

    for item in data.get("items", []):
        ymin, xmin, ymax, xmax = item["bbox"]

        t_left = int(xmin * (width / 1000))
        t_right = int(xmax * (width / 1000))
        t_top = int(ymin * (height / 1000))
        t_bottom = int(ymax * (height / 1000))

        padding_x = 12
        padding_y = 6

        wipe_left = max(0, t_left - padding_x)
        wipe_right = min(width, t_right + padding_x)
        wipe_top = max(0, t_top - padding_y)
        wipe_bottom = min(height, t_bottom + padding_y)

        draw.rectangle([wipe_left, wipe_top, wipe_right, wipe_bottom], fill=255)

    output_path = Path(output_dir) / f"{Path(source_img_path).stem}_mask.png"
    mask_canvas.save(output_path, "PNG")
    return output_path


def create_hidden_symlink(link_path, target_path):
    """
    Create a hidden symlink at link_path pointing to target_path, replacing
    any existing file/symlink there. Used to drop a pointer to Output/Vocab
    and Output/Masks results right beside the source image — useful for
    later pipeline stages that just want to look next to the source rather
    than know the Output/ folder structure.
    """
    link_path = Path(link_path)
    target_path = Path(target_path).resolve()
    try:
        if link_path.is_symlink() or link_path.exists():
            link_path.unlink()
        link_path.symlink_to(target_path)
        return True
    except Exception as e:
        print(f"   ⚠️  \033[93mSymlink failed for\033[0m {link_path.name}: {e}")
        return False


# ─── Input Collection (standard DJJTB pattern) ────────────────────────────────

def collect_images_from_txt():
    paths = djj.get_paths_from_txt("Enter txt file path")
    if not paths:
        return []
    images = []
    for path in paths:
        path_obj = Path(path)
        if path_obj.is_file() and path_obj.suffix.lower() in SUPPORTED_EXTS:
            images.append(str(path_obj))
        elif path_obj.is_dir():
            images.extend(djj.collect_images_from_folder(str(path_obj), include_subfolders=False, extensions=SUPPORTED_EXTS))
    return sorted(set(images), key=str.lower)


def get_valid_inputs():
    print("\033[1;93m🔤 Select vocab grid images\033[0m")
    input_mode = djj.prompt_choice(
        "\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n3. Path list from txt file\n",
        ['1', '2', '3'],
        default='1'
    )
    print()

    valid_paths = []

    if input_mode == '1':
        src_path = djj.get_path_input("Enter folder path")
        print()
        include_sub = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        valid_paths = djj.collect_images_from_folder(src_path, include_sub, extensions=SUPPORTED_EXTS)
    elif input_mode == '2':
        file_paths = input("📁 \033[93mEnter image paths (space-separated):\033[0m\n -> ").strip()
        if not file_paths:
            print("❌ \033[93mNo file paths provided.\033[0m")
            sys.exit(1)
        valid_paths = djj.collect_images_from_paths(file_paths, extensions=SUPPORTED_EXTS)
        print()
    else:
        valid_paths = collect_images_from_txt()
        print()

    if not valid_paths:
        print("❌ \033[93mNo valid image files found.\033[0m")
        sys.exit(1)

    os.system('clear')
    print("\n" * 2)
    print(f"✅ \033[93mFound\033[0m {len(valid_paths)} \033[93mvocab image(s)\033[0m")
    print()
    return valid_paths


# ─── Batch Processing ─────────────────────────────────────────────────────────

def process_images_batch(image_paths, save_json, do_masks,
                          filter_sparse=False, min_row_size=None,
                          filter_icon_text=False, grid_rows=None):
    print(f"\n\033[1;93m🧠 Processing\033[0m {len(image_paths)} \033[1;93mimage(s)\033[0m")
    print("=" * 50)
    print(f"\033[93m💾 Save JSON:\033[0m {'Yes' if save_json else 'No'}")
    print(f"\033[93m🎭 Generate masks:\033[0m {'Yes' if do_masks else 'No'}")
    if filter_sparse:
        print(f"\033[93m🧹 Sparse-row filter:\033[0m Yes (min {min_row_size} item(s)/row)")
    if filter_icon_text:
        print(f"\033[93m🧹 Icon-text filter:\033[0m Yes ({grid_rows} row(s))")
    print("=" * 50)
    print()

    success = 0
    error = 0
    output_folders = set()

    for idx, img_path in enumerate(image_paths, 1):
        fname = os.path.basename(img_path)
        print(f"\033[93m[{idx}/{len(image_paths)}]\033[0m {fname}")

        try:
            print(f"   🔎 Detecting text regions...")
            data = extract_text_regions(img_path)

            if filter_sparse and min_row_size:
                before_count = len(data["items"])
                data["items"] = filter_sparse_rows(data["items"], min_row_size)
                removed = before_count - len(data["items"])
                if removed:
                    print(f"   🧹 \033[93mFiltered\033[0m {removed} isolated/false detection(s)")

            if filter_icon_text and grid_rows:
                before_count = len(data["items"])
                data["items"] = filter_label_items(data["items"], grid_rows)
                removed = before_count - len(data["items"])
                if removed:
                    print(f"   🧹 \033[93mFiltered\033[0m {removed} icon-embedded region(s)")

            with Image.open(img_path) as im:
                w, h = im.size

            data["meta"] = {
                "source_image_path": str(Path(img_path).resolve()),
                "original_width": w,
                "original_height": h
            }

            n_items = len(data.get("items", []))
            print(f"   ✅ \033[92m{n_items} text region(s) found\033[0m")

            if save_json:
                json_dir = Path(img_path).parent / "Output" / "Vocab"
                json_dir.mkdir(parents=True, exist_ok=True)
                json_path = json_dir / f"{Path(img_path).stem}.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                output_folders.add(json_dir)
                print(f"   💾 \033[93mJSON saved\033[0m")

                json_link = Path(img_path).parent / f".{Path(img_path).stem}.json"
                if create_hidden_symlink(json_link, json_path):
                    print(f"   🔗 \033[93mSymlinked\033[0m → {json_link.name}")

            if do_masks:
                mask_dir = Path(img_path).parent / "Output" / "Masks"
                mask_dir.mkdir(parents=True, exist_ok=True)
                mask_path = generate_mask_from_data(data, img_path, mask_dir)
                output_folders.add(mask_dir)
                print(f"   🎭 \033[93mMask saved\033[0m → {mask_path.name}")

                mask_link = Path(img_path).parent / f".{Path(img_path).stem}_mask.png"
                if create_hidden_symlink(mask_link, mask_path):
                    print(f"   🔗 \033[93mSymlinked\033[0m → {mask_link.name}")

            success += 1
        except Exception as e:
            print(f"   ❌ \033[93mFailed:\033[0m {e}")
            error += 1
        print()

    print("=" * 50)
    print(f"\033[1;93m🏁 Complete!\033[0m")
    print(f"✅ \033[92mSuccess:\033[0m {success}")
    print(f"❌ \033[93mFailed:\033[0m {error}")
    print("=" * 50)

    return output_folders


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    os.system('clear')

    if not verify_tesseract():
        print("\n\033[93mFix the issue above, then run this script again.\033[0m")
        sys.exit(1)

    while True:
        print()
        print("\033[92m" + "=" * 50 + "\033[0m")
        print("\033[1;93mVocab + Mask Generator\033[0m")
        print("🔹 Text region detection (Tesseract OCR)")
        print("🔹 Optional JSON export")
        print("🔹 Optional inpainting mask generation")
        print("\033[92m" + "=" * 50 + "\033[0m")
        print()

        try:
            image_paths = get_valid_inputs()

            save_json = djj.prompt_choice(
                "\033[93mSave detected regions to Output/Vocab as JSON?\033[0m\n1. Yes\n2. No",
                ['1', '2'],
                default='1'
            ) == '1'
            print()

            do_masks = djj.prompt_choice(
                "\033[93mGenerate inpainting masks from results?\033[0m\n1. Yes\n2. No",
                ['1', '2'],
                default='1'
            ) == '1'
            print()

            filter_icon_text = djj.prompt_choice(
                "\033[93mFilter out text detected inside icon artwork (keep only grid labels)?\033[0m\n1. Yes\n2. No",
                ['1', '2'],
                default='1'
            ) == '1'
            print()

            grid_rows = None
            if filter_icon_text:
                grid_rows = djj.get_int_input("\033[93mHow many rows in the grid\033[0m", min_val=1, max_val=50)
                print()

            os.system('clear')
            output_folders = process_images_batch(image_paths, save_json, do_masks, filter_icon_text, grid_rows)

            if len(output_folders) == 1:
                djj.prompt_open_folder(list(output_folders)[0])
            elif len(output_folders) > 1:
                choice = djj.prompt_choice(
                    "\033[93mOpen folders?\033[0m\n1. All\n2. First\n3. No",
                    ['1', '2', '3'],
                    default='2'
                )
                if choice == '1':
                    import subprocess
                    for f in sorted(output_folders)[:5]:
                        subprocess.run(['open', str(f)])
                elif choice == '2':
                    import subprocess
                    subprocess.run(['open', str(sorted(output_folders)[0])])

            action = djj.what_next()
            if action == 'exit':
                break

        except KeyboardInterrupt:
            print("\n\033[93mCancelled\033[0m")
            break
        except SystemExit:
            raise
        except Exception as e:
            print(f"\n❌ {e}")
            import traceback
            traceback.print_exc()
            action = djj.what_next()
            if action == 'exit':
                break


if __name__ == "__main__":
    main()