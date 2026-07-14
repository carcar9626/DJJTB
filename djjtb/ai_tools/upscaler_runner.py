import os
import sys
import subprocess
import pathlib
import time
import djjtb.utils as djj

# ─── Config ───────────────────────────────────────────────────────────────────

SUPPORTED_EXTS  = ('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp')  # webp excluded — convert first

MODEL_DIR       = "/Users/home/Documents/ai_models/upscalers"
MODEL_PATH      = f"{MODEL_DIR}/4x-UltraSharp.pth"
VENV_PYTHON     = f"{MODEL_DIR}/upsvenv/bin/python3"
TAG_PATH        = "/opt/homebrew/bin/tag"
TAG_NAME        = "UPS"
SCALE_FACTOR    = 4

# ─── Inline inference — pure PyTorch, original ESRGAN arch ───────────────────
#
# 4x-UltraSharp uses the original ESRGAN weight format:
#   model.0          → first conv
#   model.1.sub.N    → 23 RRDB blocks
#   model.3/6/8/10   → upsample + output convs
#
# All params passed via env vars — no quoting/escaping issues.

INFERENCE_SCRIPT = r"""
import os, sys, pathlib
import torch
import torch.nn as nn
import numpy as np
import cv2
from PIL import Image

model_path   = os.environ["UPS_MODEL_PATH"]
input_path   = os.environ["UPS_INPUT"]
output_path  = os.environ["UPS_OUTPUT"]
suffix       = os.environ["UPS_SUFFIX"]
tile_size    = int(os.environ.get("UPS_TILE", "0"))
tile_pad     = int(os.environ.get("UPS_TILE_PAD", "10"))
scale        = int(os.environ.get("UPS_SCALE", "4"))
resize_edge    = int(os.environ.get("UPS_RESIZE_EDGE", "0"))     # 0 = no resize
blend_strength = float(os.environ.get("UPS_BLEND", "1.0"))      # 1.0 = full AI upscale
post_mode      = os.environ.get("UPS_POST", "none")              # none / natural / custom
grain_strength = float(os.environ.get("UPS_GRAIN", "0.03"))     # 0.0-1.0
edge_sharpen   = float(os.environ.get("UPS_SHARPEN", "0.5"))    # 0.0-1.0

# ── Original ESRGAN architecture (matches 4x-UltraSharp key names) ────────────
#
# Key pattern: model.0, model.1.sub.0..22, model.3, model.6, model.8, model.10

class ResidualDenseBlock_5C(nn.Module):
    def __init__(self, nf=64, gc=32, bias=True):
        super().__init__()
        # Wrapped in Sequential so keys match conv1.0, conv2.0 etc in checkpoint
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
        out = self.RDB1(x)
        out = self.RDB2(out)
        out = self.RDB3(out)
        return out * 0.2 + x

class _Trunk(nn.Module):
    # Sits at model.1 — contains sub.0..sub.22 (RRDB blocks) + sub.23 (trunk conv)
    def __init__(self, nf, nb, gc):
        super().__init__()
        self.sub = nn.Sequential(
            *[RRDB(nf, gc) for _ in range(nb)],
            nn.Conv2d(nf, nf, 3, 1, 1, bias=True)   # sub.23
        )
    def forward(self, x):
        return self.sub(x)

class RRDBNet(nn.Module):
    # Explicit layer names to match checkpoint keys exactly:
    #   model.0   → conv_first
    #   model.1   → trunk (_Trunk with sub.0..sub.23)
    #   model.3   → upconv1
    #   model.6   → upconv2
    #   model.8   → conv_hr
    #   model.10  → conv_last
    # Indices 2,4,5,7,9 are LeakyReLU (no weights, not in checkpoint)
    def __init__(self, in_nc=3, out_nc=3, nf=64, nb=23, gc=32):
        super().__init__()
        self.model = nn.ModuleList([
            nn.Conv2d(in_nc, nf, 3, 1, 1, bias=True),   # 0  model.0
            _Trunk(nf, nb, gc),                           # 1  model.1
            nn.LeakyReLU(0.2, inplace=True),              # 2  (no weights)
            nn.Conv2d(nf, nf, 3, 1, 1, bias=True),        # 3  model.3
            nn.LeakyReLU(0.2, inplace=True),              # 4  (no weights)
            nn.LeakyReLU(0.2, inplace=True),              # 5  (no weights)
            nn.Conv2d(nf, nf, 3, 1, 1, bias=True),        # 6  model.6
            nn.LeakyReLU(0.2, inplace=True),              # 7  (no weights)
            nn.Conv2d(nf, nf, 3, 1, 1, bias=True),        # 8  model.8
            nn.LeakyReLU(0.2, inplace=True),              # 9  (no weights)
            nn.Conv2d(nf, out_nc, 3, 1, 1, bias=True),    # 10 model.10
        ])
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x):
        fea   = self.model[0](x)
        trunk = self.model[1](fea)
        fea   = fea + trunk
        fea   = self.lrelu(self.model[3](fea))
        fea   = nn.functional.interpolate(fea, scale_factor=2, mode='nearest')
        fea   = self.lrelu(self.model[6](fea))
        fea   = nn.functional.interpolate(fea, scale_factor=2, mode='nearest')
        fea   = self.lrelu(self.model[8](fea))
        out   = self.model[10](fea)
        return out

# ── Load model ────────────────────────────────────────────────────────────────

device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
print(f"Device: {device}")

ckpt = torch.load(model_path, map_location="cpu", weights_only=True)

# 4x-UltraSharp is a raw state_dict — no params_ema wrapper
if isinstance(ckpt, dict) and "params_ema" in ckpt:
    state_dict = ckpt["params_ema"]
elif isinstance(ckpt, dict) and "params" in ckpt:
    state_dict = ckpt["params"]
else:
    state_dict = ckpt

model = RRDBNet(in_nc=3, out_nc=3, nf=64, nb=23, gc=32)
model.load_state_dict(state_dict, strict=True)
model.eval()
model = model.to(device)

# ── Upscale helpers ───────────────────────────────────────────────────────────

def upscale_chunk(img_t, model, device):
    with torch.no_grad():
        return model(img_t.to(device)).cpu()

def process_image(img_bgr, tile_size, tile_pad, scale, model, device):
    img_t = torch.from_numpy(
        img_bgr.astype(np.float32) / 255.0
    ).permute(2, 0, 1).unsqueeze(0)

    if tile_size == 0:
        out_t = upscale_chunk(img_t, model, device)
    else:
        _, c, h_t, w_t = img_t.shape
        out_h, out_w = h_t * scale, w_t * scale
        out_t = torch.zeros(1, c, out_h, out_w)
        tiles_x = (w_t + tile_size - 1) // tile_size
        tiles_y = (h_t + tile_size - 1) // tile_size

        for ty in range(tiles_y):
            for tx in range(tiles_x):
                x0 = max(tx * tile_size - tile_pad, 0)
                y0 = max(ty * tile_size - tile_pad, 0)
                x1 = min((tx + 1) * tile_size + tile_pad, w_t)
                y1 = min((ty + 1) * tile_size + tile_pad, h_t)

                tile_in  = img_t[:, :, y0:y1, x0:x1]
                tile_out = upscale_chunk(tile_in, model, device)

                ox0 = (x0 - tx * tile_size + tile_pad if tx > 0 else 0) * scale
                oy0 = (y0 - ty * tile_size + tile_pad if ty > 0 else 0) * scale
                ox1 = tile_out.shape[3] - (tile_pad * scale if x1 < w_t else 0)
                oy1 = tile_out.shape[2] - (tile_pad * scale if y1 < h_t else 0)

                dst_x0 = tx * tile_size * scale
                dst_y0 = ty * tile_size * scale
                dst_x1 = dst_x0 + (ox1 - ox0)
                dst_y1 = dst_y0 + (oy1 - oy0)

                out_t[:, :, dst_y0:dst_y1, dst_x0:dst_x1] = tile_out[:, :, oy0:oy1, ox0:ox1]

    out_np = out_t.squeeze(0).permute(1, 2, 0).clamp(0, 1).numpy()
    return (out_np * 255.0).astype(np.uint8)

# ── Resize to longest edge (Lanczos, only if image exceeds target) ────────────

def resize_to_longest_edge(img_bgr, longest_edge):
    h, w = img_bgr.shape[:2]
    current_longest = max(h, w)
    if current_longest <= longest_edge:
        return img_bgr  # already smaller — bypass silently
    ratio = longest_edge / current_longest
    new_w = int(round(w * ratio))
    new_h = int(round(h * ratio))
    # cv2.INTER_LANCZOS4 = Lanczos resampling
    return cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

# ── Load, upscale, optional resize, save as PNG ───────────────────────────────

input_p  = pathlib.Path(input_path)
output_p = pathlib.Path(output_path)
output_p.mkdir(parents=True, exist_ok=True)

# Always save as PNG
out_file = output_p / f"{input_p.stem}{suffix}.png"

img_bgr = cv2.imread(str(input_p), cv2.IMREAD_COLOR)
if img_bgr is None:
    print(f"ERROR: Could not read image: {input_p}")
    sys.exit(1)

# Upscale
result_bgr = process_image(img_bgr, tile_size, tile_pad, scale, model, device)

# Blend AI upscale against plain bicubic if strength < 1.0
if blend_strength < 1.0:
    h_out, w_out = result_bgr.shape[:2]
    bicubic = cv2.resize(img_bgr, (w_out, h_out), interpolation=cv2.INTER_CUBIC)
    result_bgr = cv2.addWeighted(result_bgr, blend_strength, bicubic, 1.0 - blend_strength, 0)

# ── Post-processing ───────────────────────────────────────────────────────────

def apply_edge_sharpen(img, strength):
    # Unsharp mask — sharpens edges only, leaves flat areas (skin) smooth
    blur = cv2.GaussianBlur(img, (0, 0), sigmaX=2.0)
    sharp = cv2.addWeighted(img, 1.0 + strength, blur, -strength, 0)
    return sharp

def apply_grain(img, strength):
    # Luminance-weighted grain — more grain in midtones, less in shadows/highlights
    # Mimics natural film/sensor noise
    h, w = img.shape[:2]
    noise = np.random.normal(0, strength * 255, (h, w)).astype(np.float32)
    img_f = img.astype(np.float32)
    # Weight grain by luminance curve (less grain at extremes)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    weight = 1.0 - (2.0 * gray - 1.0) ** 2   # peaks at midtone (0.5), zero at 0 and 1
    for c in range(3):
        img_f[:, :, c] += noise * weight
    return np.clip(img_f, 0, 255).astype(np.uint8)

if post_mode == 'natural':
    result_bgr = apply_edge_sharpen(result_bgr, edge_sharpen)
    result_bgr = apply_grain(result_bgr, grain_strength)
elif post_mode == 'custom':
    if edge_sharpen > 0:
        result_bgr = apply_edge_sharpen(result_bgr, edge_sharpen)
    if grain_strength > 0:
        result_bgr = apply_grain(result_bgr, grain_strength)

# Resize to longest edge if requested
if resize_edge > 0:
    result_bgr = resize_to_longest_edge(result_bgr, resize_edge)

cv2.imwrite(str(out_file), result_bgr)
print(f"SAVED:{out_file}")
"""

# ─── Helpers ──────────────────────────────────────────────────────────────────

def format_elapsed_time(seconds):
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.1f}s"


def verify_environment():
    """Check venv python, model, torch + cv2 — no basicsr/realesrgan needed"""
    ok = True

    if not pathlib.Path(VENV_PYTHON).exists():
        print(f"\033[93m⚠️  venv python not found:\033[0m {VENV_PYTHON}")
        ok = False

    if not pathlib.Path(MODEL_PATH).exists():
        print(f"\033[93m⚠️  Model not found:\033[0m {MODEL_PATH}")
        ok = False

    if not ok:
        return False

    check = subprocess.run(
        [VENV_PYTHON, "-c",
         "import torch, cv2, numpy; "
         "print('MPS:', torch.backends.mps.is_available())"],
        capture_output=True, text=True
    )
    if check.returncode != 0:
        print("\033[93m⚠️  Missing packages in upsvenv:\033[0m")
        print(check.stderr[-300:])
        return False

    print(f"✅ \033[93mEnvironment verified —\033[0m {check.stdout.strip()}")
    return True


def tag_source_files(file_paths, tag_name=TAG_NAME):
    tagged_count = 0
    for file_path in file_paths:
        try:
            subprocess.run(
                [TAG_PATH, "-a", tag_name, str(file_path)],
                check=True, capture_output=True
            )
            tagged_count += 1
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to tag {os.path.basename(file_path)}: {e}")
    if tagged_count > 0:
        print(f"\033[93m🏷️  Tagged\033[0m {tagged_count} \033[93mfile(s) with\033[0m '\033[92m{tag_name}\033[0m'")


def clean_path(path_str):
    return path_str.strip().strip('\'"')


def collect_files_from_folder(input_path, subfolders=False):
    input_path_obj = pathlib.Path(input_path)
    files = []
    if input_path_obj.is_dir():
        if subfolders:
            for root, _, filenames in os.walk(input_path):
                files.extend(
                    pathlib.Path(root) / f for f in filenames
                    if pathlib.Path(f).suffix.lower() in SUPPORTED_EXTS
                )
        else:
            files = [
                f for f in input_path_obj.glob('*')
                if f.suffix.lower() in SUPPORTED_EXTS and f.is_file()
            ]
    return sorted([str(f) for f in files], key=str.lower)


def collect_files_from_paths(raw_input):
    files = []
    for path_str in raw_input.strip().split():
        path_obj = pathlib.Path(clean_path(path_str))
        if path_obj.is_file() and path_obj.suffix.lower() in SUPPORTED_EXTS:
            files.append(str(path_obj))
        elif path_obj.is_dir():
            files.extend(collect_files_from_folder(path_obj))
    return sorted(files, key=str.lower)


# ─── Input ────────────────────────────────────────────────────────────────────

def get_valid_inputs():
    print("\033[1;33m🔍 Select images to upscale\033[0m")

    input_mode = djj.prompt_choice(
        "\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
        ['1', '2'],
        default='1'
    )
    print()

    valid_paths = []
    src_path = None

    if input_mode == '1':
        src_path = djj.get_path_input("Enter folder path")
        print()
        include_sub = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        valid_paths = collect_files_from_folder(src_path, include_sub)
        valid_paths = djj.apply_skip_list(valid_paths, root=src_path)
    else:
        raw = input("📁 \033[93mEnter file paths (space-separated):\033[0m\n -> ").strip()
        if not raw:
            print("\033[1;33m❌ No file paths provided.\033[0m")
            sys.exit(1)
        valid_paths = collect_files_from_paths(raw)
        valid_paths = djj.apply_skip_list(valid_paths)
        print()

    if not valid_paths:
        print("❌ \033[1;33mNo valid image files found.\033[0m")
        sys.exit(1)

    os.system('clear')
    print("\n" * 2)
    print("🔍 Detecting files...")
    print()
    print(f"\033[93m✅ Found\033[0m {len(valid_paths)} \033[93msupported image(s)\033[0m")
    print()
    print("Choose Your Options:")

    return valid_paths, input_mode, src_path


# ─── Processing ───────────────────────────────────────────────────────────────

def process_single_file(input_path, output_path, suffix, tile_size, resize_edge, blend_strength, post_mode, grain_strength, edge_sharpen, timeout=600):
    file_start = time.time()

    env = os.environ.copy()
    env.update({
        "UPS_MODEL_PATH":  MODEL_PATH,
        "UPS_INPUT":       str(input_path),
        "UPS_OUTPUT":      str(output_path),
        "UPS_SUFFIX":      suffix,
        "UPS_TILE":        str(tile_size),
        "UPS_TILE_PAD":    "10",
        "UPS_SCALE":       str(SCALE_FACTOR),
        "UPS_RESIZE_EDGE": str(resize_edge),
        "UPS_BLEND":       f"{blend_strength:.2f}",
        "UPS_POST":        post_mode,
        "UPS_GRAIN":       f"{grain_strength:.3f}",
        "UPS_SHARPEN":     f"{edge_sharpen:.3f}",
    })

    try:
        result = subprocess.run(
            [VENV_PYTHON, "-c", INFERENCE_SCRIPT],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout
        )
        elapsed = time.time() - file_start
        return result.returncode == 0, result.stdout, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.time() - file_start
        return False, "Processing timeout", elapsed
    except Exception as e:
        elapsed = time.time() - file_start
        return False, str(e), elapsed


def process_files_batch(input_paths, suffix, tile_size, resize_edge, blend_strength, post_mode, grain_strength, edge_sharpen, tag_source):
    overall_start = time.time()

    blend_label = "100% — full AI upscale" if blend_strength >= 1.0 else f"{int(blend_strength*100)}% AI / {int((1-blend_strength)*100)}% bicubic"

    print("\n" * 2)
    print(f"\n\033[1;33m🔼 Upscaling\033[0m {len(input_paths)} \033[1;33mimage(s):\033[0m")
    print("---------------")
    print(f"\033[93m🧠 Model:\033[0m 4x-UltraSharp")
    print(f"\033[93m🔠 Suffix:\033[0m {suffix}")
    print(f"\033[93m🔼 Scale:\033[0m {SCALE_FACTOR}x → PNG")
    print(f"\033[93m💪 Strength:\033[0m {blend_label}")
    post_label = {'none': 'Off', 'natural': 'Natural (grain + edge sharpen)', 'custom': f'Custom — grain {int(grain_strength*100)}% / sharpen {int(edge_sharpen*100)}%'}[post_mode]
    print(f"\033[93m✨ Post-process:\033[0m {post_label}")
    print(f"\033[93m📐 Resize:\033[0m {'longest edge → ' + str(resize_edge) + 'px' if resize_edge > 0 else 'No resize'}")
    print(f"\033[93m🪟 Tile size:\033[0m {'No tiling' if tile_size == 0 else tile_size}")
    print("---------------")
    print()
    print("\033[1;33m🚀 Upscaler\033[0m \033[93mactivating...\033[0m")
    print()

    success_count = 0
    error_count   = 0
    output_paths  = set()

    for i, input_path in enumerate(input_paths):
        file_name   = os.path.basename(input_path)
        output_path = pathlib.Path(input_path).parent / "UPS"
        output_path.mkdir(parents=True, exist_ok=True)
        output_paths.add(output_path)

        print(f"\033[93mProcessing [{i+1}/{len(input_paths)}]:\033[0m {file_name}")

        success, output_msg, file_elapsed = process_single_file(
            input_path, output_path, suffix, tile_size, resize_edge, blend_strength, post_mode, grain_strength, edge_sharpen
        )
        total_elapsed = time.time() - overall_start

        if success:
            print(f"\033[92m✅ Success:\033[0m {file_name}")
            print(f"  \033[36mFile time:\033[0m {format_elapsed_time(file_elapsed)}")
            print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
            success_count += 1
        else:
            print(f"\033[93m❌ Failed:\033[0m {file_name}")
            print(f"  \033[36mFile time:\033[0m {format_elapsed_time(file_elapsed)}")
            print(f"  \033[36mTotal time:\033[0m {format_elapsed_time(total_elapsed)}")
            if "timeout" in output_msg.lower():
                print(f"   \033[93mTimeout:\033[0m Processing took too long")
            else:
                error_preview = output_msg[-400:] if output_msg else "No output"
                print(f"   \033[93mError:\033[0m {error_preview}")
            error_count += 1
        print()

    # ── Summary ──
    final_elapsed = time.time() - overall_start
    print("=" * 50)
    print(f"\033[1;33m🏁 Upscaling Complete!\033[0m")
    print(f"✅ \033[92mSuccessful:\033[0m {success_count} \033[93mimage(s)\033[0m")
    print(f"❌ \033[93mFailed:\033[0m {error_count} \033[93mimage(s)\033[0m")
    print(f"⏱️  \033[36mTotal processing time:\033[0m {format_elapsed_time(final_elapsed)}")
    print("=" * 50)

    if tag_source and success_count > 0:
        tag_source_files(input_paths)

    if len(output_paths) == 1:
        djj.prompt_open_folder(list(output_paths)[0])
    elif len(output_paths) > 1:
        print(f"\033[93m📁 Output spread across {len(output_paths)} folder(s).\033[0m")
        open_choice = djj.prompt_choice(
            "\033[93mOpen output folders?\033[0m\n1. Yes, open all\n2. Yes, open first one only\n3. No",
            ['1', '2', '3'],
            default='2'
        )
        if open_choice == '1':
            folders_opened = 0
            for folder in sorted(output_paths):
                if folders_opened < 5:
                    subprocess.run(['open', str(folder)])
                    folders_opened += 1
            if len(output_paths) > 5:
                print(f"\033[93mNote: Opened first 5 folders. Total: {len(output_paths)}\033[0m")
        elif open_choice == '2':
            first_folder = sorted(output_paths)[0]
            subprocess.run(['open', str(first_folder)])
            print(f"\033[92m✓ Opened: {first_folder}\033[0m")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    os.system('clear')

    if not verify_environment():
        print("\n\033[93mSetup issue — check messages above.\033[0m")
        sys.exit(1)

    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mUpscaler\033[0m")
        print("Batch Image Upscale — 4x-UltraSharp")
        print("\033[92m==================================================\033[0m")
        print()

        input_files, input_mode, src_path = get_valid_inputs()

        # ── Suffix ──
        suffix = djj.get_string_input(
            "\033[93mEnter suffix (default '_UT'):\033[0m\n > ",
            default="_UT"
        )

        # ── Tiling ──
        tile_choice = djj.prompt_choice(
            "\033[93mTiling mode?\033[0m\n1. No tiling — full image (recommended, 64GB)\n2. Tile size 512\n3. Tile size 256\n",
            ['1', '2', '3'],
            default='1'
        )
        tile_size = {'1': 0, '2': 512, '3': 256}[tile_choice]

        # ── Blend / output strength ──
        blend_choice = djj.prompt_choice(
            "\033[93mUpscale strength?\033[0m\n1. 100% — full AI upscale (default)\n2. 80% — subtle softening\n3. 60% — moderate blend\n4. Custom %\n",
            ['1', '2', '3', '4'],
            default='1'
        )
        if blend_choice == '1':
            blend_strength = 1.0
        elif blend_choice == '2':
            blend_strength = 0.8
        elif blend_choice == '3':
            blend_strength = 0.6
        else:
            pct_input = input("\033[93mEnter strength % (1–100, default 100):\033[0m\n > ").strip()
            try:
                pct = int(pct_input) if pct_input else 100
                pct = max(1, min(100, pct))
                blend_strength = pct / 100.0
            except ValueError:
                print("⚠️  \033[93mInvalid input, using 100%\033[0m")
                blend_strength = 1.0
        # ── Post-processing ──
        post_choice = djj.prompt_choice(
            "\033[93mPost-processing?\033[0m\n1. None\n2. Natural — grain + edge sharpen (recommended)\n3. Custom — choose strength\n",
            ['1', '2', '3'],
            default='2'
        )
        grain_strength = 0.0
        edge_sharpen   = 0.0
        if post_choice == '1':
            post_mode = 'none'
        elif post_choice == '2':
            post_mode = 'natural'
            grain_strength = 0.03
            edge_sharpen   = 0.5
        else:
            post_mode = 'custom'
            grain_input = input("\033[93mGrain strength (0–100, default 30):\033[0m\n > ").strip()
            try:
                grain_strength = (int(grain_input) if grain_input else 30) / 100.0
            except ValueError:
                grain_strength = 0.03
            sharpen_input = input("\033[93mEdge sharpen strength (0–100, default 50):\033[0m\n > ").strip()
            try:
                edge_sharpen = (int(sharpen_input) if sharpen_input else 50) / 100.0
            except ValueError:
                edge_sharpen = 0.5

        do_resize = djj.prompt_choice(
            "\033[93mResize output to longest edge?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='1'
        ) == '1'

        resize_edge = 0
        if do_resize:
            edge_input = input("\033[93mLongest edge in pixels (default 1920):\033[0m\n > ").strip()
            try:
                resize_edge = int(edge_input) if edge_input else 1920
                if resize_edge < 100:
                    print("⚠️  \033[93mValue too small, using 1920\033[0m")
                    resize_edge = 1920
            except ValueError:
                print("⚠️  \033[93mInvalid input, using 1920\033[0m")
                resize_edge = 1920

        # ── Tag source ──
        tag_source = djj.prompt_choice(
            "\033[93mTag source files with 'UPS'?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='1'
        ) == '1'

        os.system('clear')

        process_files_batch(input_files, suffix, tile_size, resize_edge, blend_strength, post_mode, grain_strength, edge_sharpen, tag_source)

        print()
        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()


# ─── Package requirements for upsvenv ────────────────────────────────────────
#
#   pip install torch torchvision
#   pip install opencv-python-headless Pillow numpy
#
#   Verify:
#   ~/Documents/ai_models/upscalers/upsvenv/bin/python3 -c \
#     "import torch, cv2, numpy; print('MPS:', torch.backends.mps.is_available())"
#
# ─────────────────────────────────────────────────────────────────────────────
