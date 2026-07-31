import os
import sys
import json
import tempfile
import logging
import pathlib
import subprocess
from pathlib import Path
from PIL import Image
import djjtb.utils as djj

os.system('clear')

LOG_DIR = Path("~/Documents/Scripts/DJJTB/djjtb/logs").expanduser()
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ─── Detection model (own venv — main DJJTB venv's onnxruntime pin is broken
# against numpy 2.x, and this keeps the 216MB model + onnxruntime out of the
# main venv entirely) ───────────────────────────────────────────────────────
SC_PYTHON = "/Users/home/Documents/ai_models/smart_crop/scvenv/bin/python3"
SC_MODEL_PATH = "/Users/home/Documents/ai_models/smart_crop/models/yolox_l.onnx"
SC_INPUT_SIZE = 640
SC_CONF_DEFAULT = 0.5
PERSON_CLASS_ID = 0  # COCO class 0

AR_PRESETS = [
    ("8:9  (half of 16:9 — default)", 8, 9),
    ("3:4", 3, 4),
    ("4:3", 4, 3),
    ("9:16", 9, 16),
    ("16:9", 16, 9),
    ("1:1", 1, 1),
]


def get_op_logger(op_name="crop"):
    log_file = LOG_DIR / f"smart_crop_{op_name}_log.txt"
    logger = logging.getLogger(f'djjtb.smart_crop.{op_name}')
    logger.setLevel(logging.INFO)
    logger.handlers = []
    logger.propagate = False
    handler = logging.FileHandler(log_file, mode='a')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)
    logger.info(f"===== RUN START: {op_name} =====")
    return logger


# ─── Detection — shells out to scvenv, one call for the whole batch ────────
# Passed to scvenv python via -c so no file needs to live on disk (matches
# cf_ups_runner.py's UPS_INFERENCE convention). Standard YOLOX letterbox
# preprocessing (pad=114, no normalization) + anchor-free grid decode over
# strides 8/16/32, filtered to the person class, single best box per image.

SC_DETECT_INFERENCE = r"""
import os, json
import numpy as np
import cv2
import onnxruntime as ort

model_path  = os.environ["SC_MODEL_PATH"]
input_list  = os.environ["SC_INPUT_LIST"]
output_path = os.environ["SC_OUTPUT_PATH"]
input_size  = int(os.environ.get("SC_INPUT_SIZE", "640"))
conf_thresh = float(os.environ.get("SC_CONF_THRESH", "0.5"))
class_id    = int(os.environ.get("SC_CLASS_ID", "0"))

with open(input_list) as f:
    paths = json.load(f)

session = ort.InferenceSession(model_path, providers=["CoreMLExecutionProvider", "CPUExecutionProvider"])
input_name = session.get_inputs()[0].name


def preprocess(img, size):
    padded = np.full((size, size, 3), 114, dtype=np.uint8)
    r = min(size / img.shape[0], size / img.shape[1])
    resized = cv2.resize(img, (int(img.shape[1] * r), int(img.shape[0] * r)), interpolation=cv2.INTER_LINEAR)
    padded[: resized.shape[0], : resized.shape[1]] = resized
    chw = padded.transpose(2, 0, 1).astype(np.float32)
    return chw[None], r


def decode(outputs, size):
    strides = [8, 16, 32]
    grids, expanded_strides = [], []
    for stride in strides:
        hs, ws = size // stride, size // stride
        xv, yv = np.meshgrid(np.arange(ws), np.arange(hs))
        grid = np.stack((xv, yv), 2).reshape(1, -1, 2)
        grids.append(grid)
        expanded_strides.append(np.full((1, grid.shape[1], 1), stride))
    grids = np.concatenate(grids, 1)
    expanded_strides = np.concatenate(expanded_strides, 1)
    outputs[..., :2] = (outputs[..., :2] + grids) * expanded_strides
    outputs[..., 2:4] = np.exp(outputs[..., 2:4]) * expanded_strides
    return outputs


def nms(boxes, scores, iou_thresh=0.45):
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter)
        order = order[1:][iou <= iou_thresh]
    return keep


results = {}
for path in paths:
    img = cv2.imread(path)
    if img is None:
        results[path] = None
        continue

    inp, ratio = preprocess(img, input_size)
    raw = session.run(None, {input_name: inp})[0]
    preds = decode(raw.copy(), input_size)[0]

    boxes_cxcywh = preds[:, :4]
    obj_conf = preds[:, 4]
    cls_conf = preds[:, 5:]
    scores = obj_conf * cls_conf[:, class_id]

    mask = scores > conf_thresh
    if not mask.any():
        results[path] = None
        continue

    boxes = boxes_cxcywh[mask]
    scores = scores[mask]
    x1 = (boxes[:, 0] - boxes[:, 2] / 2) / ratio
    y1 = (boxes[:, 1] - boxes[:, 3] / 2) / ratio
    x2 = (boxes[:, 0] + boxes[:, 2] / 2) / ratio
    y2 = (boxes[:, 1] + boxes[:, 3] / 2) / ratio
    xyxy = np.stack([x1, y1, x2, y2], axis=1)

    keep = nms(xyxy, scores)
    if not keep:
        results[path] = None
        continue
    best = keep[int(np.argmax(scores[keep]))]
    results[path] = {"box": xyxy[best].tolist(), "score": float(scores[best])}

with open(output_path, "w") as f:
    json.dump(results, f)
"""


def detect_subjects(image_paths, conf_thresh=SC_CONF_DEFAULT, logger=None):
    """
    Batch person-bbox detection via YOLOX-l, run once for the whole batch in
    the dedicated scvenv (avoids reloading the 216MB model per image).
    Returns {path: {"box": [x1,y1,x2,y2], "score": float} | None}.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as inf:
        json.dump(image_paths, inf)
        input_list_path = inf.name
    output_path = input_list_path.replace(".json", "_out.json")

    env = os.environ.copy()
    env.update({
        "SC_MODEL_PATH": SC_MODEL_PATH,
        "SC_INPUT_LIST": input_list_path,
        "SC_OUTPUT_PATH": output_path,
        "SC_INPUT_SIZE": str(SC_INPUT_SIZE),
        "SC_CONF_THRESH": str(conf_thresh),
        "SC_CLASS_ID": str(PERSON_CLASS_ID),
    })

    try:
        r = subprocess.run([SC_PYTHON, "-c", SC_DETECT_INFERENCE], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, timeout=1800)
        if r.returncode != 0:
            if logger:
                logger.error(f"Detection subprocess failed: {r.stdout}")
            print(f"\033[93m⚠️  Detection failed:\033[0m {r.stdout[-500:]}")
            return {}
        with open(output_path) as f:
            return json.load(f)
    finally:
        for p in (input_list_path, output_path):
            try:
                os.remove(p)
            except OSError:
                pass


# ─── Crop math ───────────────────────────────────────────────────────────

def compute_crop_box(img_w, img_h, ar_w, ar_h, subject_box, margin=0.15):
    """
    Largest window of the target aspect ratio that fits inside the source
    image, positioned (not resized) to center on the subject + headroom
    margin, clamped so it never leaves the image bounds. Falls back to a
    plain center crop when subject_box is None.
    """
    target_ratio = ar_w / ar_h

    if img_w / img_h > target_ratio:
        crop_h = img_h
        crop_w = crop_h * target_ratio
    else:
        crop_w = img_w
        crop_h = crop_w / target_ratio

    if subject_box is None:
        cx, cy = img_w / 2, img_h / 2
    else:
        x1, y1, x2, y2 = subject_box
        bw, bh = x2 - x1, y2 - y1
        x1p = max(0, x1 - bw * margin)
        y1p = max(0, y1 - bh * margin)
        x2p = min(img_w, x2 + bw * margin)
        y2p = min(img_h, y2 + bh * margin)
        cx, cy = (x1p + x2p) / 2, (y1p + y2p) / 2

    left = min(max(cx - crop_w / 2, 0), img_w - crop_w)
    top = min(max(cy - crop_h / 2, 0), img_h - crop_h)

    return (round(left), round(top), round(left + crop_w), round(top + crop_h))


# ─── Prompts ────────────────────────────────────────────────────────────

def get_target_ar():
    print("\033[93mTarget aspect ratio:\033[0m")
    for i, (label, w, h) in enumerate(AR_PRESETS, 1):
        print(f"  {i}. {label}")
    print(f"  {len(AR_PRESETS) + 1}. Custom")
    choice = djj.prompt_choice(
        "",
        [str(i) for i in range(1, len(AR_PRESETS) + 2)],
        default='1'
    )
    idx = int(choice) - 1
    if idx < len(AR_PRESETS):
        _, w, h = AR_PRESETS[idx]
        return w, h
    w = djj.get_int_input("Custom width ratio (e.g. 8)", min_val=1)
    h = djj.get_int_input("Custom height ratio (e.g. 9)", min_val=1)
    return w, h


def get_output_resolution(ar_w, ar_h):
    """
    Ask whether to keep each crop's native (source-derived) resolution or
    resize to an exact target. Resize is driven by a single longest-edge
    value — since every crop is already exactly ar_w:ar_h, that value alone
    determines both target dimensions with no distortion and no separate
    width/height/stretch-vs-pad choices to get wrong.
    Returns None (keep native) or (target_w, target_h).
    """
    choice = djj.prompt_choice(
        "\033[93mOutput resolution:\033[0m\n"
        "1. Keep crop's native resolution\n"
        "2. Resize to a longest-edge value\n",
        ['1', '2'],
        default='1'
    )
    print()
    if choice == '1':
        return None

    longest_edge = djj.get_int_input(f"\033[93mLongest edge in px (AR {ar_w}:{ar_h})\033[0m", min_val=1)
    print()
    if ar_w >= ar_h:
        target_w = longest_edge
        target_h = round(longest_edge * ar_h / ar_w)
    else:
        target_h = longest_edge
        target_w = round(longest_edge * ar_w / ar_h)
    return target_w, target_h


# ─── Batch crop ─────────────────────────────────────────────────────────

def smart_crop_images(images, ar_w, ar_h, conf_thresh, resize_target=None, logger=None):
    print()
    print(f"{len(images)} \033[93mimages found\033[0m")
    print(f"\033[93mDetecting subjects (YOLOX-l, batch of {len(images)})...\033[0m")

    detections = detect_subjects(images, conf_thresh=conf_thresh, logger=logger)

    print(f"\033[93mCropping to {ar_w}:{ar_h}...\033[0m")

    successful, failed, skipped, no_detection = [], [], [], []
    output_dirs_used = set()

    for i, img_path in enumerate(images, 1):
        try:
            det = detections.get(img_path)
            subject_box = det["box"] if det else None
            if det is None:
                no_detection.append(pathlib.Path(img_path).name)

            with Image.open(img_path) as img:
                img_w, img_h = img.size
                box = compute_crop_box(img_w, img_h, ar_w, ar_h, subject_box)
                cropped = img.crop(box)
                if resize_target is not None:
                    target_w, target_h = resize_target
                    cropped = cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)

                pillow_format, file_ext = djj.get_save_format(img_path)
                img_path_obj = pathlib.Path(img_path)
                img_output_dir = img_path_obj.parent / "Output" / "SmartCrop"
                img_output_dir.mkdir(parents=True, exist_ok=True)
                output_path = img_output_dir / f"{img_path_obj.stem}_smartcrop{file_ext}"

                if output_path.exists():
                    skipped.append(img_path_obj.name)
                    output_dirs_used.add(str(img_output_dir))
                    sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)...")
                    sys.stdout.flush()
                    continue

                save_kwargs = {}
                if pillow_format == 'JPEG':
                    if cropped.mode != 'RGB':
                        cropped = cropped.convert('RGB')
                    save_kwargs['quality'] = 95
                elif pillow_format == 'WEBP':
                    save_kwargs['quality'] = 95

                cropped.save(str(output_path), format=pillow_format, **save_kwargs)
                successful.append(img_path_obj.name)
                output_dirs_used.add(str(img_output_dir))

            if logger:
                score = det["score"] if det else None
                logger.info(f"{img_path_obj.name}: box={subject_box} score={score} -> {box}")

            sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)...")
            sys.stdout.flush()

        except Exception as e:
            failed.append((pathlib.Path(img_path).name, str(e)))
            if logger:
                logger.error(f"Failed to crop {img_path}: {e}")
            sys.stdout.write(f"\rProcessing {i}/{len(images)} ({i/len(images)*100:.1f}%)... ❌")
            sys.stdout.flush()

    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

    return successful, failed, skipped, no_detection, sorted(output_dirs_used)


def print_summary(successful, failed, skipped, no_detection, output_dirs_used, output_dir_fallback):
    print()
    print("\033[93mSmart Crop Summary\033[0m")
    print("-------------")
    print(f"✅ \033[93mSuccessfully cropped:\033[0m {len(successful)} images")
    if no_detection:
        print(f"🎯 \033[93mNo subject detected (center-crop fallback):\033[0m {len(no_detection)}")
    if skipped:
        print(f"⏭️  \033[93mSkipped (already exists):\033[0m {len(skipped)}")
    if failed:
        print(f"❌ \033[93mFailed:\033[0m {len(failed)}")
        for name, err in failed[:3]:
            print(f"   • {name}: {err}")
    if len(output_dirs_used) == 1:
        print(f"📁 \033[93mOutput folder:\033[0m\n{output_dirs_used[0]}")
    elif output_dirs_used:
        print(f"📁 \033[93mOutput folders:\033[0m {len(output_dirs_used)} (one per source folder)")
        for d in output_dirs_used[:4]:
            print(f"   {d}")
        if len(output_dirs_used) > 4:
            print(f"   ... and {len(output_dirs_used) - 4} more")
    print()

    open_target = output_dirs_used[0] if output_dirs_used else output_dir_fallback
    djj.prompt_open_folder(open_target)


def run_smart_crop(images, is_folder_mode, first_folder):
    ar_w, ar_h = get_target_ar()
    print()
    resize_target = get_output_resolution(ar_w, ar_h)

    logger = get_op_logger("crop")

    print("-------------")
    successful, failed, skipped, no_detection, output_dirs_used = smart_crop_images(
        images, ar_w, ar_h, SC_CONF_DEFAULT, resize_target=resize_target, logger=logger
    )

    output_dir = djj.get_output_directory(images, is_folder_mode=is_folder_mode,
                                           first_folder=first_folder, subfolder_name="SmartCrop")
    print_summary(successful, failed, skipped, no_detection, output_dirs_used, output_dir)

    return output_dir


# ─── Main ───────────────────────────────────────────────────────────────

def main():
    while True:
        os.system('clear')
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mSmart Crop (AI)\033[0m")
        print("Subject-aware batch crop — YOLOX-l person detection")
        print("\033[92m==================================================\033[0m")
        print()

        input_mode = djj.prompt_choice(
            "Input mode:\n"
            "1. Folder path\n"
            "2. Space-separated file paths\n"
            "3. Path list from txt file\n",
            ['1', '2', '3'],
            default='1'
        )
        print()

        images = []
        input_path = None

        if input_mode == '1':
            input_path = djj.get_path_input("Enter folder path")
            print()
            include_subfolders = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            images = djj.collect_images_from_folder(input_path, include_subfolders)
            if not include_subfolders:
                images = djj.apply_skip_list(images, root=input_path)

        elif input_mode == '2':
            print("📁 \033[93mEnter image paths (space-separated, drag-and-drop ok):\033[0m")
            raw = input(" -> ").strip()
            if not raw:
                print("❌ No file paths provided.")
                continue
            images = djj.collect_images_from_paths(raw)
            if images:
                input_path = str(pathlib.Path(images[0]).parent)
            print()

        else:
            paths = djj.get_paths_from_txt("Enter txt file path")
            images = djj.collect_images_from_path_list(paths) if paths else []
            if images:
                input_path = str(pathlib.Path(images[0]).parent)
            print()

        if not images:
            print("❌ \033[93mNo valid image files found.\033[0m")
            continue

        is_folder_mode = (input_mode == '1')
        run_smart_crop(images, is_folder_mode, input_path)

        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()
