#!/usr/bin/env python3
"""
CF + UPS Runner — DJJTB
Combined CodeFormer face restore + 4x-UltraSharp upscaler

Modes:
  1. Codeformer Only   → input/CF/          suffix _CF
  2. Upscale Only      → input/UPS/         suffix _UT
  3. CF → UPS          → input/Output/CFUP/ suffix _CU  (intermediate → Output/CF/ _CF)
  4. UPS → CF          → input/Output/UPCF/ suffix _UC  (intermediate → Output/UPS/ _UT)

Finalize step (sharpen + grain + optional resize) applies to every saved output.
For chain modes, if the user opts to save the intermediate it is finalized before saving.
"""

import os
import sys
import subprocess
import pathlib
import time
import shutil
import djjtb.utils as djj

# ─── Config ───────────────────────────────────────────────────────────────────

SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp')

# CodeFormer
CF_SCRIPT  = "/Users/home/Documents/ai_models/CodeFormer/inference_codeformer.py"
CF_PYTHON  = "/Users/home/Documents/ai_models/CodeFormer/cfvenv/bin/python3"
CF_DIR     = "/Users/home/Documents/ai_models/CodeFormer"
CF_TAG     = "CF"

# Upscaler
UPS_MODEL  = "/Users/home/Documents/ai_models/upscalers/4x-UltraSharp.pth"
UPS_PYTHON = "/Users/home/Documents/ai_models/upscalers/upsvenv/bin/python3"
UPS_SCALE  = 4
UPS_TAG    = "UPS"

TAG_PATH   = "/opt/homebrew/bin/tag"

# ─── UPS Inline Inference Script ─────────────────────────────────────────────
# Passed to upsvenv python via -c so no file needed on disk.
# All params come in via env vars — no shell quoting issues.

UPS_INFERENCE = r"""
import os, sys, pathlib
import torch
import torch.nn as nn
import numpy as np
import cv2

model_path     = os.environ["UPS_MODEL_PATH"]
input_path     = os.environ["UPS_INPUT"]
output_path    = os.environ["UPS_OUTPUT"]
suffix         = os.environ["UPS_SUFFIX"]
tile_size      = int(os.environ.get("UPS_TILE", "0"))
tile_pad       = int(os.environ.get("UPS_TILE_PAD", "10"))
scale          = int(os.environ.get("UPS_SCALE", "4"))
resize_edge    = int(os.environ.get("UPS_RESIZE_EDGE", "0"))
blend_strength = float(os.environ.get("UPS_BLEND", "1.0"))
post_mode      = os.environ.get("UPS_POST", "none")
grain_strength = float(os.environ.get("UPS_GRAIN", "0.03"))
edge_sharpen   = float(os.environ.get("UPS_SHARPEN", "0.5"))

class ResidualDenseBlock_5C(nn.Module):
    def __init__(self, nf=64, gc=32, bias=True):
        super().__init__()
        self.conv1 = nn.Sequential(nn.Conv2d(nf,      gc, 3, 1, 1, bias=bias))
        self.conv2 = nn.Sequential(nn.Conv2d(nf+gc,   gc, 3, 1, 1, bias=bias))
        self.conv3 = nn.Sequential(nn.Conv2d(nf+gc*2, gc, 3, 1, 1, bias=bias))
        self.conv4 = nn.Sequential(nn.Conv2d(nf+gc*3, gc, 3, 1, 1, bias=bias))
        self.conv5 = nn.Sequential(nn.Conv2d(nf+gc*4, nf, 3, 1, 1, bias=bias))
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)
    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x

class RRDB(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.RDB1 = ResidualDenseBlock_5C(nf, gc)
        self.RDB2 = ResidualDenseBlock_5C(nf, gc)
        self.RDB3 = ResidualDenseBlock_5C(nf, gc)
    def forward(self, x):
        out = self.RDB1(x); out = self.RDB2(out); out = self.RDB3(out)
        return out * 0.2 + x

class _Trunk(nn.Module):
    def __init__(self, nf, nb, gc):
        super().__init__()
        self.sub = nn.Sequential(
            *[RRDB(nf, gc) for _ in range(nb)],
            nn.Conv2d(nf, nf, 3, 1, 1, bias=True)
        )
    def forward(self, x): return self.sub(x)

class RRDBNet(nn.Module):
    def __init__(self, in_nc=3, out_nc=3, nf=64, nb=23, gc=32):
        super().__init__()
        self.model = nn.ModuleList([
            nn.Conv2d(in_nc, nf, 3, 1, 1, bias=True),
            _Trunk(nf, nb, gc),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(nf, nf, 3, 1, 1, bias=True),
            nn.LeakyReLU(0.2, inplace=True),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(nf, nf, 3, 1, 1, bias=True),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(nf, nf, 3, 1, 1, bias=True),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(nf, out_nc, 3, 1, 1, bias=True),
        ])
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)
    def forward(self, x):
        fea = self.model[0](x); trunk = self.model[1](fea); fea = fea + trunk
        fea = self.lrelu(self.model[3](fea))
        fea = nn.functional.interpolate(fea, scale_factor=2, mode='nearest')
        fea = self.lrelu(self.model[6](fea))
        fea = nn.functional.interpolate(fea, scale_factor=2, mode='nearest')
        fea = self.lrelu(self.model[8](fea))
        return self.model[10](fea)

device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
print(f"Device: {device}")

ckpt = torch.load(model_path, map_location="cpu", weights_only=True)
if isinstance(ckpt, dict) and "params_ema" in ckpt:
    state_dict = ckpt["params_ema"]
elif isinstance(ckpt, dict) and "params" in ckpt:
    state_dict = ckpt["params"]
else:
    state_dict = ckpt

model = RRDBNet(); model.load_state_dict(state_dict, strict=True)
model.eval(); model = model.to(device)

def upscale_chunk(img_t, model, device):
    with torch.no_grad(): return model(img_t.to(device)).cpu()

def process_image(img_bgr, tile_size, tile_pad, scale, model, device):
    img_t = torch.from_numpy(img_bgr.astype(np.float32)/255.0).permute(2,0,1).unsqueeze(0)
    if tile_size == 0:
        out_t = upscale_chunk(img_t, model, device)
    else:
        _, c, h_t, w_t = img_t.shape
        out_h, out_w = h_t*scale, w_t*scale
        out_t = torch.zeros(1, c, out_h, out_w)
        tiles_x = (w_t+tile_size-1)//tile_size
        tiles_y = (h_t+tile_size-1)//tile_size
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                x0=max(tx*tile_size-tile_pad,0); y0=max(ty*tile_size-tile_pad,0)
                x1=min((tx+1)*tile_size+tile_pad,w_t); y1=min((ty+1)*tile_size+tile_pad,h_t)
                tile_in=img_t[:,:,y0:y1,x0:x1]; tile_out=upscale_chunk(tile_in,model,device)
                ox0=(x0-tx*tile_size+tile_pad if tx>0 else 0)*scale
                oy0=(y0-ty*tile_size+tile_pad if ty>0 else 0)*scale
                ox1=tile_out.shape[3]-(tile_pad*scale if x1<w_t else 0)
                oy1=tile_out.shape[2]-(tile_pad*scale if y1<h_t else 0)
                dst_x0=tx*tile_size*scale; dst_y0=ty*tile_size*scale
                out_t[:,:,dst_y0:dst_y0+(oy1-oy0),dst_x0:dst_x0+(ox1-ox0)]=tile_out[:,:,oy0:oy1,ox0:ox1]
    out_np = out_t.squeeze(0).permute(1,2,0).clamp(0,1).numpy()
    return (out_np*255.0).astype(np.uint8)

def apply_edge_sharpen(img, strength):
    blur = cv2.GaussianBlur(img, (0,0), sigmaX=2.0)
    return cv2.addWeighted(img, 1.0+strength, blur, -strength, 0)

def apply_grain(img, strength):
    h, w = img.shape[:2]
    noise = np.random.normal(0, strength*255, (h,w)).astype(np.float32)
    img_f = img.astype(np.float32)
    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)/255.0
    weight = 1.0-(2.0*gray-1.0)**2
    for c in range(3): img_f[:,:,c] += noise*weight
    return np.clip(img_f, 0, 255).astype(np.uint8)

def resize_to_longest_edge(img_bgr, longest_edge):
    h, w = img_bgr.shape[:2]
    if max(h,w) <= longest_edge: return img_bgr
    ratio = longest_edge/max(h,w)
    return cv2.resize(img_bgr, (int(round(w*ratio)), int(round(h*ratio))), interpolation=cv2.INTER_LANCZOS4)

input_p  = pathlib.Path(input_path)
output_p = pathlib.Path(output_path)
output_p.mkdir(parents=True, exist_ok=True)
out_file = output_p / f"{input_p.stem}{suffix}.png"

img_bgr = cv2.imread(str(input_p), cv2.IMREAD_COLOR)
if img_bgr is None:
    print(f"ERROR: Could not read image: {input_p}"); sys.exit(1)

result_bgr = process_image(img_bgr, tile_size, tile_pad, scale, model, device)

if blend_strength < 1.0:
    h_out, w_out = result_bgr.shape[:2]
    bicubic = cv2.resize(img_bgr, (w_out, h_out), interpolation=cv2.INTER_CUBIC)
    result_bgr = cv2.addWeighted(result_bgr, blend_strength, bicubic, 1.0-blend_strength, 0)

if post_mode == 'natural':
    result_bgr = apply_edge_sharpen(result_bgr, edge_sharpen)
    result_bgr = apply_grain(result_bgr, grain_strength)
elif post_mode == 'custom':
    if edge_sharpen > 0: result_bgr = apply_edge_sharpen(result_bgr, edge_sharpen)
    if grain_strength > 0: result_bgr = apply_grain(result_bgr, grain_strength)

if resize_edge > 0:
    result_bgr = resize_to_longest_edge(result_bgr, resize_edge)

cv2.imwrite(str(out_file), result_bgr)
print(f"SAVED:{out_file}")
"""

# ─── CF-side post-processing (finalize without upscaling) ────────────────────
# The UPS engine handles its own finalize inside the subprocess.
# For CF-only output (which stays in the main venv), we do the post-pass here
# using cv2 directly — no subprocess needed because cv2 is in the main venv
# via the upsvenv... actually CF uses its own venv and we can't guarantee cv2
# there. So we do CF finalize as a second cv2 subprocess under UPS_PYTHON,
# using a lightweight finalize-only script (no model load, just post-processing).

CF_FINALIZE_SCRIPT = r"""
import os, sys, pathlib
import numpy as np
import cv2

input_path     = os.environ["FIN_INPUT"]
output_path    = os.environ["FIN_OUTPUT"]
suffix         = os.environ["FIN_SUFFIX"]
post_mode      = os.environ.get("FIN_POST", "none")
grain_strength = float(os.environ.get("FIN_GRAIN", "0.03"))
edge_sharpen   = float(os.environ.get("FIN_SHARPEN", "0.5"))
resize_edge    = int(os.environ.get("FIN_RESIZE", "0"))

def apply_edge_sharpen(img, strength):
    blur = cv2.GaussianBlur(img, (0,0), sigmaX=2.0)
    return cv2.addWeighted(img, 1.0+strength, blur, -strength, 0)

def apply_grain(img, strength):
    h, w = img.shape[:2]
    noise = np.random.normal(0, strength*255, (h,w)).astype(np.float32)
    img_f = img.astype(np.float32)
    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)/255.0
    weight = 1.0-(2.0*gray-1.0)**2
    for c in range(3): img_f[:,:,c] += noise*weight
    return np.clip(img_f, 0, 255).astype(np.uint8)

def resize_to_longest_edge(img_bgr, longest_edge):
    h, w = img_bgr.shape[:2]
    if max(h,w) <= longest_edge: return img_bgr
    ratio = longest_edge/max(h,w)
    return cv2.resize(img_bgr, (int(round(w*ratio)), int(round(h*ratio))), interpolation=cv2.INTER_LANCZOS4)

input_p  = pathlib.Path(input_path)
output_p = pathlib.Path(output_path)
output_p.mkdir(parents=True, exist_ok=True)

img = cv2.imread(str(input_p), cv2.IMREAD_COLOR)
if img is None:
    print(f"ERROR: Could not read: {input_p}"); sys.exit(1)

if post_mode == 'natural':
    img = apply_edge_sharpen(img, edge_sharpen)
    img = apply_grain(img, grain_strength)
elif post_mode == 'custom':
    if edge_sharpen > 0: img = apply_edge_sharpen(img, edge_sharpen)
    if grain_strength > 0: img = apply_grain(img, grain_strength)

if resize_edge > 0:
    img = resize_to_longest_edge(img, resize_edge)

# Keep original extension if possible, fall back to PNG
ext = input_p.suffix.lower()
if ext not in ('.jpg', '.jpeg', '.png', '.tiff', '.bmp'):
    ext = '.png'
out_file = output_p / f"{input_p.stem}{suffix}{ext}"
cv2.imwrite(str(out_file), img)
print(f"SAVED:{out_file}")
"""


# ─── Shared Helpers ───────────────────────────────────────────────────────────

def fmt_time(seconds):
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{int(seconds//60)}m {seconds%60:.1f}s"
    else:
        return f"{int(seconds//3600)}h {int((seconds%3600)//60)}m {seconds%60:.1f}s"


def tag_files(file_paths, tag_name):
    tagged = 0
    for fp in file_paths:
        try:
            subprocess.run([TAG_PATH, "-a", tag_name, str(fp)], check=True, capture_output=True)
            tagged += 1
        except Exception:
            pass
    if tagged:
        print(f"\033[93m🏷️  Tagged\033[0m {tagged} \033[93mfile(s) with '\033[92m{tag_name}\033[0m'")


def collect_files_from_folder(input_path, subfolders=False):
    p = pathlib.Path(input_path)
    files = []
    if p.is_dir():
        walk = os.walk(input_path) if subfolders else [(input_path, [], os.listdir(input_path))]
        for root, _, filenames in walk:
            files.extend(
                pathlib.Path(root) / f for f in filenames
                if pathlib.Path(f).suffix.lower() in SUPPORTED_EXTS
            )
    return sorted([str(f) for f in files], key=str.lower)


def collect_files_from_paths(raw):
    files = []
    for path_str in raw.strip().split():
        p = pathlib.Path(path_str.strip('\'"'))
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
            files.append(str(p))
        elif p.is_dir():
            files.extend(collect_files_from_folder(p))
    return sorted(files, key=str.lower)


def cleanup_cf_extras(output_path):
    """Remove cropped_faces and restored_faces subdirs CF creates."""
    for sub in ('cropped_faces', 'restored_faces'):
        d = pathlib.Path(output_path) / sub
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)


def find_cf_output(cf_output_dir, original_stem, cf_suffix):
    """
    Recursively scan cf_output_dir for CF output matching original_stem.

    CF naming is unpredictable:
      - Single file: may write {stem}.png (ignores --suffix) into final_results/
      - Single file: may write {stem}_{suffix}.png with one underscore
      - Single file: may write {stem}__{suffix}.png with double underscore
      - Folder mode: writes {stem}_{suffix}.png directly

    Strategy: find any image file whose stem STARTS WITH original_stem
    (case-insensitive). Among those, prefer the one whose stem is longest
    (most specific match). Return None only if nothing starts with the stem.
    """
    base = pathlib.Path(cf_output_dir)
    original_lower = original_stem.lower()
    image_exts = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp'}

    candidates = []
    for path in base.rglob("*"):
        if path.is_file() and path.suffix.lower() in image_exts:
            if path.stem.lower().startswith(original_lower):
                candidates.append(path)

    if candidates:
        # Prefer longest stem (most specific — has the suffix appended)
        return max(candidates, key=lambda p: len(p.stem))

    # Nothing found — print diagnostic
    image_files = [p for p in base.rglob("*")
                   if p.is_file() and p.suffix.lower() in image_exts]
    if image_files:
        print(f"  \033[93m⚠️  CF lookup miss for '{original_stem}'\033[0m")
        print(f"     Files in {cf_output_dir}:")
        for f in image_files[:5]:
            print(f"       {f.relative_to(base)}")
        if len(image_files) > 5:
            print(f"       ... and {len(image_files)-5} more")
    else:
        print(f"  \033[93m⚠️  CF output dir is empty: {cf_output_dir}\033[0m")
    return None


# ─── CF Engine ────────────────────────────────────────────────────────────────

def run_cf_single(input_path, output_dir, weight, suffix, upscale_factor=1, timeout=600):
    """
    Run CodeFormer on one file. CF's --upscale here means its internal
    bicubic pre-scale (we default 1 — let UPS handle real upscaling).
    Returns (success, stdout_text, elapsed_seconds)
    """
    t0 = time.time()
    cmd = [
        CF_PYTHON, CF_SCRIPT,
        "-i", str(input_path),
        "-o", str(output_dir),
        "-w", str(weight),
        "--suffix", suffix,
        "--upscale", str(upscale_factor),
        "--no-open"
    ]
    try:
        r = subprocess.run(cmd, cwd=CF_DIR, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout, time.time() - t0
    except subprocess.TimeoutExpired:
        return False, "Timeout", time.time() - t0
    except Exception as e:
        return False, str(e), time.time() - t0


def run_cf_folder(input_dir, output_dir, weight, suffix, upscale_factor=1):
    """
    Run CodeFormer on a whole folder (efficient for Mode 1 CF Only).
    Chain modes (3 & 4) always use run_cf_single for exact per-file tracking.
    """
    t0 = time.time()
    cmd = [
        CF_PYTHON, CF_SCRIPT,
        "-i", str(input_dir),
        "-o", str(output_dir),
        "-w", str(weight),
        "--suffix", suffix,
        "--upscale", str(upscale_factor),
        "--no-open"
    ]
    r = subprocess.run(cmd, cwd=CF_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        print(f"\033[93m\u26a0\ufe0f  CF folder mode output tail:\033[0m\n{r.stdout[-400:]}")
    return r.returncode == 0, time.time() - t0


# ─── UPS Engine ───────────────────────────────────────────────────────────────

def run_ups_single(input_path, output_dir, suffix, tile_size, resize_edge,
                   blend_strength, post_mode, grain_strength, edge_sharpen, timeout=600):
    """Run 4x-UltraSharp on one file via inline inference script."""
    t0 = time.time()
    env = os.environ.copy()
    env.update({
        "UPS_MODEL_PATH":  UPS_MODEL,
        "UPS_INPUT":       str(input_path),
        "UPS_OUTPUT":      str(output_dir),
        "UPS_SUFFIX":      suffix,
        "UPS_TILE":        str(tile_size),
        "UPS_TILE_PAD":    "10",
        "UPS_SCALE":       str(UPS_SCALE),
        "UPS_RESIZE_EDGE": str(resize_edge),
        "UPS_BLEND":       f"{blend_strength:.2f}",
        "UPS_POST":        post_mode,
        "UPS_GRAIN":       f"{grain_strength:.3f}",
        "UPS_SHARPEN":     f"{edge_sharpen:.3f}",
    })
    try:
        r = subprocess.run([UPS_PYTHON, "-c", UPS_INFERENCE], env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=timeout)
        return r.returncode == 0, r.stdout, time.time() - t0
    except subprocess.TimeoutExpired:
        return False, "Timeout", time.time() - t0
    except Exception as e:
        return False, str(e), time.time() - t0


# ─── Finalize Engine (CF output post-pass) ───────────────────────────────────

def run_finalize(input_path, output_dir, suffix, post_mode, grain_strength,
                 edge_sharpen, resize_edge, timeout=120):
    """
    Apply sharpen + grain + resize to a CF output (or any image).
    Uses UPS_PYTHON (has cv2/numpy) but doesn't load the model — fast.
    If post_mode is 'none' and resize_edge is 0 we just copy the file.
    """
    if post_mode == 'none' and resize_edge == 0:
        # Nothing to do — copy straight to destination
        out_path = pathlib.Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        src = pathlib.Path(input_path)
        dst = out_path / f"{src.stem}{suffix}{src.suffix}"
        shutil.copy2(src, dst)
        return True, "", 0.0

    t0 = time.time()
    env = os.environ.copy()
    env.update({
        "FIN_INPUT":   str(input_path),
        "FIN_OUTPUT":  str(output_dir),
        "FIN_SUFFIX":  suffix,
        "FIN_POST":    post_mode,
        "FIN_GRAIN":   f"{grain_strength:.3f}",
        "FIN_SHARPEN": f"{edge_sharpen:.3f}",
        "FIN_RESIZE":  str(resize_edge),
    })
    try:
        r = subprocess.run([UPS_PYTHON, "-c", CF_FINALIZE_SCRIPT], env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=timeout)
        return r.returncode == 0, r.stdout, time.time() - t0
    except subprocess.TimeoutExpired:
        return False, "Timeout", time.time() - t0
    except Exception as e:
        return False, str(e), time.time() - t0


# ─── Verification ────────────────────────────────────────────────────────────

def verify_all():
    ok = True
    checks = [
        (CF_PYTHON,  "CF venv python"),
        (CF_SCRIPT,  "CF inference script"),
        (pathlib.Path(CF_DIR) / "weights/facelib/detection_Resnet50_Final.pth", "CF detection model"),
        (pathlib.Path(CF_DIR) / "weights/CodeFormer/codeformer.pth",            "CF model weights"),
        (UPS_PYTHON, "UPS venv python"),
        (UPS_MODEL,  "4x-UltraSharp model"),
    ]
    for path, label in checks:
        if not pathlib.Path(path).exists():
            print(f"\033[93m⚠️  Missing:\033[0m {label}")
            print(f"   {path}")
            ok = False
    if ok:
        # Quick torch check via upsvenv
        r = subprocess.run(
            [UPS_PYTHON, "-c", "import torch, cv2, numpy; print('MPS:', torch.backends.mps.is_available())"],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            print("\033[93m⚠️  UPS venv missing packages (torch/cv2/numpy):\033[0m")
            print(r.stderr[-300:])
            ok = False
        else:
            print(f"✅ \033[93mAll engines ready —\033[0m {r.stdout.strip()}")
    return ok


# ─── Input Collection ─────────────────────────────────────────────────────────

def get_inputs():
    input_mode = djj.prompt_choice(
        "\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
        ['1', '2'], default='1'
    )
    print()

    src_path = None
    if input_mode == '1':
        src_path = djj.get_path_input("Enter folder path")
        print()
        include_sub = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
            ['1', '2'], default='2'
        ) == '1'
        print()
        files = collect_files_from_folder(src_path, include_sub)
        files = djj.apply_skip_list(files, root=src_path)
    else:
        raw = input("📁 \033[93mEnter file paths (space-separated):\033[0m\n -> ").strip()
        if not raw:
            print("❌ No file paths provided.")
            sys.exit(1)
        files = collect_files_from_paths(raw)
        files = djj.apply_skip_list(files)
        if files:
            src_path = str(pathlib.Path(files[0]).parent)
        print()

    if not files:
        print("❌ No valid image files found.")
        sys.exit(1)

    os.system('clear')
    print("\n\n🔍 Detecting files...")
    print()
    print(f"\033[93m✅ Found\033[0m {len(files)} \033[93mimage(s)\033[0m")
    print()
    return files, input_mode, src_path


# ─── Prompt Blocks ────────────────────────────────────────────────────────────

def prompt_cf_options():
    """Collect all CodeFormer parameters."""
    print("\033[1;93m🤖 CodeFormer Options\033[0m")
    weight_raw = input("\033[93mWeight (0.0–1.0, default 0.7):\033[0m\n > ").strip()
    try:
        weight = float(weight_raw) if weight_raw else 0.7
        if not 0.0 <= weight <= 1.0:
            raise ValueError()
    except ValueError:
        print("⚠️  Using 0.7")
        weight = 0.7

    save_faces = djj.prompt_choice(
        "\033[93mSave cropped faces?\033[0m\n1. Yes\n2. No", ['1', '2'], default='2'
    ) == '1'
    save_restored = djj.prompt_choice(
        "\033[93mSave restored faces?\033[0m\n1. Yes\n2. No", ['1', '2'], default='2'
    ) == '1'
    print()
    return weight, save_faces, save_restored


def prompt_ups_options():
    """Collect all UPS parameters."""
    print("\033[1;93m🔼 Upscaler Options\033[0m")

    tile_choice = djj.prompt_choice(
        "\033[93mTiling mode?\033[0m\n1. No tiling (recommended, 64GB)\n2. Tile 512\n3. Tile 256",
        ['1', '2', '3'], default='1'
    )
    tile_size = {'1': 0, '2': 512, '3': 256}[tile_choice]

    blend_choice = djj.prompt_choice(
        "\033[93mUpscale strength?\033[0m\n1. 100% — full AI\n2. 80%\n3. 60%\n4. Custom %",
        ['1', '2', '3', '4'], default='1'
    )
    if blend_choice == '4':
        pct_raw = input("\033[93mStrength % (1–100):\033[0m\n > ").strip()
        try:
            blend = max(1, min(100, int(pct_raw) if pct_raw else 100)) / 100.0
        except ValueError:
            blend = 1.0
    else:
        blend = {'1': 1.0, '2': 0.8, '3': 0.6}[blend_choice]
    print()
    return tile_size, blend


def prompt_finalize_options(label=""):
    """
    Full finalize: grain + sharpen + resize. Used for saved outputs and modes 1/2.
    Natural defaults: grain=0.015 (subtle), no sharpening — matches chaiNNer workflow.
    Returns (post_mode, grain_strength, edge_sharpen, resize_edge).
    """
    header = f"\033[1;93m✨ Finalize{' — ' + label if label else ''}\033[0m"
    print(header)

    post_choice = djj.prompt_choice(
        "\033[93mPost-processing?\033[0m\n"
        "1. None\n"
        "2. Natural — blend + grain (recommended)\n"
        "3. Custom — choose strength",
        ['1', '2', '3'], default='2'
    )
    grain = 0.0
    sharpen = 0.0
    if post_choice == '1':
        post_mode = 'none'
    elif post_choice == '2':
        post_mode = 'natural'
        grain = 0.015   # subtle — matches chaiNNer grain level
        sharpen = 0.0   # no sharpening by default
    else:
        post_mode = 'custom'
        g_raw = input("\033[93mGrain strength (0–100, default 15):\033[0m\n > ").strip()
        try:
            grain = (int(g_raw) if g_raw else 15) / 100.0
        except ValueError:
            grain = 0.015
        s_raw = input("\033[93mEdge sharpen (0–100, default 0):\033[0m\n > ").strip()
        try:
            sharpen = (int(s_raw) if s_raw else 0) / 100.0
        except ValueError:
            sharpen = 0.0

    do_resize = djj.prompt_choice(
        "\033[93mResize to longest edge?\033[0m\n1. Yes\n2. No",
        ['1', '2'], default='1'
    ) == '1'
    resize_edge = 0
    if do_resize:
        e_raw = input("\033[93mLongest edge px (default 1920):\033[0m\n > ").strip()
        try:
            resize_edge = int(e_raw) if e_raw else 1920
            if resize_edge < 100:
                resize_edge = 1920
        except ValueError:
            resize_edge = 1920
    print()
    return post_mode, grain, sharpen, resize_edge


def prompt_passthrough_options(label=""):
    """
    Pass-through post: sharpen + optional resize, NO grain.
    Used for images handed to the next processing step in chain modes.
    Grain added here would stack with final-step grain = static TV effect.
    Returns (post_mode, grain_strength=0.0, edge_sharpen, resize_edge).
    """
    header = f"\033[1;93m⚙️  Pass-through post{' — ' + label if label else ''}\033[0m"
    print(header)
    print("\033[93m  (No grain — grain applied only at final saved output)\033[0m")

    post_choice = djj.prompt_choice(
        "\033[93mPost-processing before next step?\033[0m\n"
        "1. None (recommended — cleanest input for next step)\n"
        "2. Edge sharpen only\n"
        "3. Custom sharpen strength",
        ['1', '2', '3'], default='1'
    )
    sharpen = 0.0
    if post_choice == '1':
        post_mode = 'none'
    elif post_choice == '2':
        post_mode = 'custom'
        sharpen = 0.3
    else:
        post_mode = 'custom'
        s_raw = input("\033[93mEdge sharpen (0–100, default 30):\033[0m\n > ").strip()
        try:
            sharpen = (int(s_raw) if s_raw else 30) / 100.0
        except ValueError:
            sharpen = 0.3

    do_resize = djj.prompt_choice(
        "\033[93mResize before next step?\033[0m\n1. Yes\n2. No",
        ['1', '2'], default='2'
    ) == '1'
    resize_edge = 0
    if do_resize:
        e_raw = input("\033[93mLongest edge px (default 1920):\033[0m\n > ").strip()
        try:
            resize_edge = int(e_raw) if e_raw else 1920
            if resize_edge < 100:
                resize_edge = 1920
        except ValueError:
            resize_edge = 1920
    print()
    return post_mode, 0.0, sharpen, resize_edge


def resolve_output_dirs(src_path, mode):
    """
    Return the output directories for a given mode and source folder.

    Modes 1 & 2 — flat beside input (matching originals):
      CF Only  → src/CF/
      UPS Only → src/UPS/

    Modes 3 & 4 — under Output/:
      CF → UPS: intermediate → src/Output/CF/   final → src/Output/CFUP/
      UPS → CF: intermediate → src/Output/UPS/  final → src/Output/UPCF/
    """
    base = pathlib.Path(src_path)
    if mode == '1':
        return {'final': base / 'CF'}
    elif mode == '2':
        return {'final': base / 'UPS'}
    elif mode == '3':
        return {
            'intermediate': base / 'Output' / 'CF',
            'final':        base / 'Output' / 'CFUP',
        }
    else:  # mode == '4'
        return {
            'intermediate': base / 'Output' / 'UPS',
            'final':        base / 'Output' / 'UPCF',
        }


# ─── Per-file Pipeline Runners ────────────────────────────────────────────────

def run_pipeline_mode1(files, src_path, input_mode,
                       cf_weight, save_faces, save_restored,
                       post_mode, grain, sharpen, resize_edge,
                       tag_source):
    """CF Only → finalize → src/CF/"""
    dirs = resolve_output_dirs(src_path, '1')
    final_dir = dirs['final']
    final_dir.mkdir(parents=True, exist_ok=True)

    # CF uses a temp dir for its raw output, then we finalize into final_dir
    # This keeps the pipeline consistent — finalize always has a source to read.
    tmp_dir = final_dir / ".cf_raw"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    overall_start = time.time()
    print("\n\n\033[1;93m🤖 CodeFormer activating...\033[0m\n")

    # Check if folder mode is possible (all images, single folder)
    images_only = all(pathlib.Path(f).suffix.lower() in ('.jpg','.jpeg','.png','.tiff','.tif','.bmp') for f in files)
    use_folder_mode = (input_mode == '1' and images_only)

    success_count = error_count = 0

    if use_folder_mode:
        print(f"\033[93m📁 Folder mode — {len(files)} image(s)\033[0m")
        ok, elapsed = run_cf_folder(src_path, tmp_dir, cf_weight, "_CF")
        if ok:
            success_count = len(files)
        else:
            error_count = len(files)
        if not save_faces or not save_restored:
            cleanup_cf_extras(tmp_dir)
    else:
        for i, fp in enumerate(files):
            fname = os.path.basename(fp)
            print(f"\033[93m[{i+1}/{len(files)}]\033[0m {fname}")
            ok, out, elapsed = run_cf_single(fp, tmp_dir, cf_weight, "_CF")
            total = time.time() - overall_start
            if ok:
                print(f"  ✅ \033[92mCF done\033[0m  {fmt_time(elapsed)}  (total {fmt_time(total)})")
                success_count += 1
            else:
                print(f"  ❌ \033[93mCF failed\033[0m  {fmt_time(elapsed)}")
                error_count += 1
            print()
        if not save_faces or not save_restored:
            cleanup_cf_extras(tmp_dir)

    # Finalize every CF output
    print("\033[93m✨ Finalizing...\033[0m\n")
    fin_success = fin_error = 0
    for fp in files:
        stem = pathlib.Path(fp).stem
        cf_out = find_cf_output(tmp_dir, stem, "_CF")
        if cf_out is None:
            fin_error += 1
            continue
        ok, _, _ = run_finalize(cf_out, final_dir, "", post_mode, grain, sharpen, resize_edge)
        # suffix="" because CF already appended _CF; finalize just copies/tweaks in place
        if ok:
            fin_success += 1
        else:
            fin_error += 1

    # Clean up temp raw CF outputs
    shutil.rmtree(tmp_dir, ignore_errors=True)

    _print_summary(success_count, error_count, fmt_time(time.time() - overall_start), final_dir)
    if tag_source and success_count:
        tag_files(files, CF_TAG)
    djj.prompt_open_folder(final_dir)


def run_pipeline_mode2(files, src_path,
                       tile_size, blend, post_mode, grain, sharpen, resize_edge,
                       tag_source):
    """UPS Only → finalize (inside UPS engine) → src/UPS/"""
    dirs = resolve_output_dirs(src_path, '2')
    final_dir = dirs['final']
    final_dir.mkdir(parents=True, exist_ok=True)

    overall_start = time.time()
    blend_label = "100% AI" if blend >= 1.0 else f"{int(blend*100)}% AI / {int((1-blend)*100)}% bicubic"
    post_label = {'none':'Off','natural':'Natural','custom':'Custom'}[post_mode]

    print("\n\n\033[1;93m🔼 Upscaler activating...\033[0m")
    print(f"\033[93m  Strength:\033[0m {blend_label}  \033[93mPost:\033[0m {post_label}\n")

    success_count = error_count = 0
    for i, fp in enumerate(files):
        fname = os.path.basename(fp)
        print(f"\033[93m[{i+1}/{len(files)}]\033[0m {fname}")
        # UPS engine handles finalize internally
        ok, out, elapsed = run_ups_single(fp, final_dir, "_UT", tile_size, resize_edge,
                                          blend, post_mode, grain, sharpen)
        total = time.time() - overall_start
        if ok:
            print(f"  ✅ \033[92mDone\033[0m  {fmt_time(elapsed)}  (total {fmt_time(total)})")
            success_count += 1
        else:
            print(f"  ❌ \033[93mFailed\033[0m  {fmt_time(elapsed)}")
            print(f"     {out[-200:]}")
            error_count += 1
        print()

    _print_summary(success_count, error_count, fmt_time(time.time() - overall_start), final_dir)
    if tag_source and success_count:
        tag_files(files, UPS_TAG)
    djj.prompt_open_folder(final_dir)


def run_pipeline_mode3(files, src_path,
                       cf_weight, save_faces, save_restored,
                       cf_save_post, cf_save_grain, cf_save_sharpen, cf_save_resize,
                       cf_pass_post, cf_pass_grain, cf_pass_sharpen, cf_pass_resize,
                       save_intermediate,
                       tile_size, blend,
                       final_post, final_grain, final_sharpen, final_resize,
                       tag_source):
    """
    CF → UPS
    1. CF raw output → temp dir
    2a. If save_intermediate: finalize WITH grain → Output/CF/ (saved version)
    2b. Finalize WITHOUT grain (pass-through) → handed to UPS
    3. UPS on the pass-through CF output → final CFUP dir (UPS handles its finalize)
    """
    dirs = resolve_output_dirs(src_path, '3')
    inter_dir = dirs['intermediate']   # Output/CF/
    final_dir = dirs['final']          # Output/CFUP/
    tmp_dir   = pathlib.Path(src_path) / "Output" / ".cf_raw"

    for d in (inter_dir, final_dir, tmp_dir):
        d.mkdir(parents=True, exist_ok=True)

    overall_start = time.time()

    # ── Step 1: CodeFormer (always per-file in chain modes) ─────────────────────
    print("\n\n\033[1;93m🤖 Step 1 — CodeFormer...\033[0m\n")
    cf_success = []
    cf_fail    = []

    for i, fp in enumerate(files):
        fname = os.path.basename(fp)
        print(f"\033[93m[{i+1}/{len(files)}]\033[0m {fname}")
        ok, stdout_text, elapsed = run_cf_single(fp, tmp_dir, cf_weight, "_CF")
        total = time.time() - overall_start
        if ok:
            print(f"  ✅ \033[92mCF done\033[0m  {fmt_time(elapsed)}  (total {fmt_time(total)})")
            # Print last 3 lines of CF output so we can see where it saved
            cf_lines = [l for l in stdout_text.strip().splitlines() if l.strip()]
            for l in cf_lines[-3:]:
                print(f"     {l}")
            cf_success.append(fp)
        else:
            print(f"  ❌ CF failed  {fmt_time(elapsed)}")
            if stdout_text:
                print(f"     {stdout_text[-300:]}")
            cf_fail.append(fp)
        print()
    cleanup_cf_extras(tmp_dir)

    # ── Step 2: Finalize CF outputs ──────────────────────────────────────────
    # Two separate passes:
    #   2a. Save copy (with grain) → Output/CF/  [only if save_intermediate]
    #   2b. Pass-through (no grain) → temp holding area → fed to UPS

    cf_passthrough_dir = pathlib.Path(src_path) / "Output" / ".cf_passthrough"
    cf_passthrough_dir.mkdir(parents=True, exist_ok=True)

    ups_inputs = []

    for fp in cf_success:
        stem   = pathlib.Path(fp).stem
        cf_out = find_cf_output(tmp_dir, stem, "_CF")
        if cf_out is None:
            print(f"  ⚠️  Skipping {stem} — CF output not found in temp dir")
            continue

        # 2a: Save copy with full finalize (grain included) if requested
        if save_intermediate:
            run_finalize(cf_out, inter_dir, "", cf_save_post, cf_save_grain, cf_save_sharpen, cf_save_resize)

        # 2b: Pass-through copy — no grain, clean input for UPS
        ok, _, _ = run_finalize(cf_out, cf_passthrough_dir, "", cf_pass_post, cf_pass_grain, cf_pass_sharpen, cf_pass_resize)
        if ok:
            target_lower = cf_out.stem.lower()
            found = None
            for p in cf_passthrough_dir.iterdir():
                if p.is_file() and p.stem.lower().startswith(target_lower):
                    found = p
                    break
            if found:
                ups_inputs.append(str(found))
            else:
                print(f"  ⚠️  Pass-through output not found for {cf_out.stem}, using raw CF output")
                ups_inputs.append(str(cf_out))
        else:
            print(f"  ❌ Pass-through finalize failed for {stem}")

    # Clean up raw CF temp — done reading it
    shutil.rmtree(tmp_dir, ignore_errors=True)

    if save_intermediate:
        print(f"  [92m✅ CF saved versions → {inter_dir}[0m")

    if not ups_inputs:
        print("❌ No CF outputs available for upscaling. Stopping.")
        return

    # ── Step 3: Upscale ───────────────────────────────────────────────────────
    blend_label = "100% AI" if blend >= 1.0 else f"{int(blend*100)}% AI"
    print(f"\n\033[1;93m🔼 Step 2 — Upscaling {len(ups_inputs)} file(s)...\033[0m")
    print(f"\033[93m  Strength:\033[0m {blend_label}\n")

    ups_success = ups_fail = 0
    for i, fp in enumerate(ups_inputs):
        fname = os.path.basename(fp)
        print(f"\033[93m[{i+1}/{len(ups_inputs)}]\033[0m {fname}")
        ok, out, elapsed = run_ups_single(fp, final_dir, "_CU", tile_size, final_resize,
                                          blend, final_post, final_grain, final_sharpen)
        total = time.time() - overall_start
        if ok:
            print(f"  ✅ \033[92mDone\033[0m  {fmt_time(elapsed)}  (total {fmt_time(total)})")
            ups_success += 1
        else:
            print(f"  ❌ Failed  {fmt_time(elapsed)}")
            print(f"     {out[-200:]}")
            ups_fail += 1
        print()

    # Clean up pass-through temp
    shutil.rmtree(cf_passthrough_dir, ignore_errors=True)

    print(f"\033[93mCF step:\033[0m {len(cf_success)} ok / {len(cf_fail)} failed")
    _print_summary(ups_success, ups_fail, fmt_time(time.time() - overall_start), final_dir)

    if save_intermediate:
        print(f"\033[93m📁 CF intermediate saved →\033[0m {inter_dir}")

    if tag_source and ups_success:
        tag_files(files, CF_TAG)
        tag_files(files, UPS_TAG)

    djj.prompt_open_folder(final_dir)


def run_pipeline_mode4(files, src_path,
                       tile_size, blend,
                       ups_save_post, ups_save_grain, ups_save_sharpen, ups_save_resize,
                       ups_pass_post, ups_pass_grain, ups_pass_sharpen, ups_pass_resize,
                       save_intermediate,
                       cf_weight, save_faces, save_restored,
                       cf_post, cf_grain, cf_sharpen, cf_resize,
                       tag_source):
    """
    UPS → CF
    1a. UPS → save copy with grain to Output/UPS/ (if save_intermediate)
    1b. UPS → pass-through (no grain) → fed to CF
    2. CF on the pass-through UPS output → temp raw
    3. Finalize CF output with grain → final UPCF dir
    """
    dirs = resolve_output_dirs(src_path, '4')
    inter_dir = dirs['intermediate']   # Output/UPS/
    final_dir = dirs['final']          # Output/UPCF/
    tmp_cf    = pathlib.Path(src_path) / "Output" / ".cf_raw"

    for d in (inter_dir, final_dir, tmp_cf):
        d.mkdir(parents=True, exist_ok=True)

    overall_start = time.time()

    # ── Step 1: Upscale ───────────────────────────────────────────────────────
    blend_label = "100% AI" if blend >= 1.0 else f"{int(blend*100)}% AI"
    print(f"\n\n\033[1;93m🔼 Step 1 — Upscaling {len(files)} file(s)...\033[0m")
    print(f"\033[93m  Strength:\033[0m {blend_label}\n")

    # Pass-through dir: UPS output without grain, fed to CF
    ups_passthrough_dir = pathlib.Path(src_path) / "Output" / ".ups_passthrough"
    ups_passthrough_dir.mkdir(parents=True, exist_ok=True)

    ups_outputs = []
    ups_fail    = []

    for i, fp in enumerate(files):
        fname = os.path.basename(fp)
        print(f"\033[93m[{i+1}/{len(files)}]\033[0m {fname}")

        # Always run UPS into passthrough dir first (no grain)
        ok, out, elapsed = run_ups_single(fp, ups_passthrough_dir, "_UT", tile_size,
                                          ups_pass_resize, blend, ups_pass_post,
                                          ups_pass_grain, ups_pass_sharpen)
        total = time.time() - overall_start
        if ok:
            print(f"  ✅ \033[92mUPS done\033[0m  {fmt_time(elapsed)}  (total {fmt_time(total)})")
            stem = pathlib.Path(fp).stem
            target_stem = f"{stem}_UT".lower()
            found = None
            for p in ups_passthrough_dir.iterdir():
                if p.is_file() and p.stem.lower() == target_stem:
                    found = p
                    break
            if found:
                # Save copy with grain to inter_dir if requested
                if save_intermediate:
                    run_ups_single(fp, inter_dir, "_UT", tile_size,
                                   ups_save_resize, blend, ups_save_post,
                                   ups_save_grain, ups_save_sharpen)
                ups_outputs.append(str(found))
            else:
                print(f"  ⚠️  UPS passthrough output not found for {stem}, skipping")
                ups_fail.append(fp)
        else:
            print(f"  ❌ UPS failed  {fmt_time(elapsed)}")
            if out:
                print(f"     {out[-200:]}")
            ups_fail.append(fp)
        print()

    if not ups_outputs:
        print("❌ No UPS outputs to pass to CF. Stopping.")
        return

    # ── Step 2: CodeFormer on upscaled images ─────────────────────────────────
    print(f"\033[1;93m🤖 Step 2 — CodeFormer on {len(ups_outputs)} upscaled image(s)...\033[0m\n")

    cf_success = []
    cf_fail    = []

    for i, fp in enumerate(ups_outputs):
        fname = os.path.basename(fp)
        print(f"\033[93m[{i+1}/{len(ups_outputs)}]\033[0m {fname}")
        ok, _, elapsed = run_cf_single(fp, tmp_cf, cf_weight, "_CF")
        if ok:
            print(f"  ✅ \033[92mCF done\033[0m  {fmt_time(elapsed)}")
            cf_success.append(fp)
        else:
            print(f"  ❌ CF failed")
            cf_fail.append(fp)
        print()
    cleanup_cf_extras(tmp_cf)

    # ── Step 3: Finalize CF output → final UPCF dir ───────────────────────────
    print("\033[93m✨ Finalizing...\033[0m\n")
    fin_ok = fin_fail = 0
    for fp in cf_success:
        stem   = pathlib.Path(fp).stem
        cf_out = find_cf_output(tmp_cf, stem, "_CF")
        if cf_out is None:
            fin_fail += 1
            continue
        ok, _, _ = run_finalize(cf_out, final_dir, "_UC", cf_post, cf_grain, cf_sharpen, cf_resize)
        if ok:
            fin_ok += 1
        else:
            fin_fail += 1

    shutil.rmtree(tmp_cf, ignore_errors=True)
    shutil.rmtree(ups_passthrough_dir, ignore_errors=True)

    print(f"\033[93mUPS step:\033[0m {len(ups_outputs)} ok / {len(ups_fail)} failed")
    print(f"\033[93mCF step:\033[0m  {len(cf_success)} ok / {len(cf_fail)} failed")
    _print_summary(fin_ok, fin_fail, fmt_time(time.time() - overall_start), final_dir)

    if save_intermediate:
        print(f"\033[93m📁 UPS intermediate saved →\033[0m {inter_dir}")

    if tag_source and fin_ok:
        tag_files(files, UPS_TAG)
        tag_files(files, CF_TAG)

    djj.prompt_open_folder(final_dir)


def _print_summary(success, error, elapsed, output_dir):
    print("=" * 50)
    print("\033[1;93m🏁 Complete!\033[0m")
    print(f"✅ \033[92mSuccess:\033[0m {success}")
    if error:
        print(f"❌ \033[93mFailed:\033[0m  {error}")
    print(f"⏱️  \033[36mTotal time:\033[0m {elapsed}")
    print(f"📁 \033[93mOutput:\033[0m {output_dir}")
    print("=" * 50)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    os.system('clear')

    if not verify_all():
        print("\n\033[93mFix the issues above then run again.\033[0m")
        sys.exit(1)

    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mCF + UPS Runner\033[0m")
        print("CodeFormer face restore  ·  4x-UltraSharp upscale")
        print("\033[92m==================================================\033[0m")
        print()

        # ── Mode selection ────────────────────────────────────────────────────
        mode = djj.prompt_choice(
            "\033[93mMode:\033[0m\n"
            "1. Codeformer Only   (→ CF/    suffix _CF)\n"
            "2. Upscale Only      (→ UPS/   suffix _UT)\n"
            "3. CF → UPS          (→ CFUP/  suffix _CU)\n"
            "4. UPS → CF          (→ UPCF/  suffix _UC)\n",
            ['1', '2', '3', '4'], default='1'
        )
        print()

        # ── Input ─────────────────────────────────────────────────────────────
        files, input_mode, src_path = get_inputs()
        print("Choose Your Options:\n")

        # ── Collect options depending on mode ─────────────────────────────────

        if mode == '1':
            # CF options + finalize
            cf_weight, save_faces, save_restored = prompt_cf_options()
            post_mode, grain, sharpen, resize_edge = prompt_finalize_options("CF output")
            tag_source = djj.prompt_choice(
                "\033[93mTag source files with 'CF'?\033[0m\n1. Yes\n2. No",
                ['1', '2'], default='1'
            ) == '1'
            os.system('clear')
            run_pipeline_mode1(files, src_path, input_mode,
                               cf_weight, save_faces, save_restored,
                               post_mode, grain, sharpen, resize_edge,
                               tag_source)

        elif mode == '2':
            # UPS options (finalize is inside UPS engine)
            tile_size, blend = prompt_ups_options()
            post_mode, grain, sharpen, resize_edge = prompt_finalize_options("UPS output")
            tag_source = djj.prompt_choice(
                "\033[93mTag source files with 'UPS'?\033[0m\n1. Yes\n2. No",
                ['1', '2'], default='1'
            ) == '1'
            os.system('clear')
            run_pipeline_mode2(files, src_path,
                               tile_size, blend, post_mode, grain, sharpen, resize_edge,
                               tag_source)

        elif mode == '3':
            # CF options
            cf_weight, save_faces, save_restored = prompt_cf_options()
            # Save intermediate CF version?
            save_inter = djj.prompt_choice(
                "\033[93mSave finalized CF version to Output/CF/?\033[0m\n1. Yes\n2. No",
                ['1', '2'], default='2'
            ) == '1'
            print()
            if save_inter:
                # Full finalize for the saved CF copy (grain included)
                cf_save_post, cf_save_grain, cf_save_sharpen, cf_save_resize = prompt_finalize_options("saved CF output")
            else:
                cf_save_post, cf_save_grain, cf_save_sharpen, cf_save_resize = 'none', 0.0, 0.0, 0
            # Pass-through post for CF→UPS handoff (no grain)
            cf_pass_post, cf_pass_grain, cf_pass_sharpen, cf_pass_resize = prompt_passthrough_options("CF → UPS handoff")
            # UPS options
            tile_size, blend = prompt_ups_options()
            # Final finalize for CFUP output (grain included)
            final_post, final_grain, final_sharpen, final_resize = prompt_finalize_options("final CFUP output")
            tag_source = djj.prompt_choice(
                "\033[93mTag source files?\033[0m\n1. Yes (CF + UPS tags)\n2. No",
                ['1', '2'], default='1'
            ) == '1'
            os.system('clear')
            run_pipeline_mode3(files, src_path,
                               cf_weight, save_faces, save_restored,
                               cf_save_post, cf_save_grain, cf_save_sharpen, cf_save_resize,
                               cf_pass_post, cf_pass_grain, cf_pass_sharpen, cf_pass_resize,
                               save_inter,
                               tile_size, blend,
                               final_post, final_grain, final_sharpen, final_resize,
                               tag_source)

        else:  # mode == '4'
            # UPS options first
            tile_size, blend = prompt_ups_options()
            # Save intermediate UPS version?
            save_inter = djj.prompt_choice(
                "\033[93mSave finalized UPS version to Output/UPS/?\033[0m\n1. Yes\n2. No",
                ['1', '2'], default='2'
            ) == '1'
            print()
            if save_inter:
                # Full finalize for the saved UPS copy (grain included)
                ups_save_post, ups_save_grain, ups_save_sharpen, ups_save_resize = prompt_finalize_options("saved UPS output")
            else:
                ups_save_post, ups_save_grain, ups_save_sharpen, ups_save_resize = 'none', 0.0, 0.0, 0
            # Pass-through post for UPS→CF handoff (no grain)
            ups_pass_post, ups_pass_grain, ups_pass_sharpen, ups_pass_resize = prompt_passthrough_options("UPS → CF handoff")
            # CF options
            cf_weight, save_faces, save_restored = prompt_cf_options()
            # Final finalize for UPCF output (grain included)
            cf_post, cf_grain, cf_sharpen, cf_resize = prompt_finalize_options("final UPCF output")
            tag_source = djj.prompt_choice(
                "\033[93mTag source files?\033[0m\n1. Yes (UPS + CF tags)\n2. No",
                ['1', '2'], default='1'
            ) == '1'
            os.system('clear')
            run_pipeline_mode4(files, src_path,
                               tile_size, blend,
                               ups_save_post, ups_save_grain, ups_save_sharpen, ups_save_resize,
                               ups_pass_post, ups_pass_grain, ups_pass_sharpen, ups_pass_resize,
                               save_inter,
                               cf_weight, save_faces, save_restored,
                               cf_post, cf_grain, cf_sharpen, cf_resize,
                               tag_source)

        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()
