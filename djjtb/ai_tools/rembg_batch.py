"""RMBG batch worker: loads the model ONCE, then processes every image.

Usage: rembg_batch.py <plain|grey> <image> [<image> ...]
Env  : RMBG_MODEL (default birefnet-general), RMBG_PROVIDER (cpu|coreml)
Prints one summary line on stdout; problems go to stderr.
"""
import io
import os
import sys
import time
from pathlib import Path

from PIL import Image
from rembg import new_session, remove

mode = sys.argv[1]
files = [Path(f) for f in sys.argv[2:]]
model = os.environ.get("RMBG_MODEL", "birefnet-general")
provider = os.environ.get("RMBG_PROVIDER", "cpu").lower()

providers = ["CPUExecutionProvider"]
if provider == "coreml":
    # onnxruntime falls back to CPU (with a warning in the log) if CoreML is unavailable
    providers = ["CoreMLExecutionProvider", "CPUExecutionProvider"]

# Work out what actually needs doing (skip outputs that already exist)
todo = []
for f in files:
    out_dir = f.parent / "RMBG"
    target = out_dir / (f.stem + ("_gry.png" if mode == "grey" else ".png"))
    if not target.exists():
        todo.append((f, target))

if not todo:
    print("Nothing to do (outputs already exist)")
    sys.exit(0)

t0 = time.time()
session = new_session(model, providers=providers)
load_s = time.time() - t0

done = failed = 0
t1 = time.time()
for f, target in todo:
    try:
        target.parent.mkdir(exist_ok=True)
        result = remove(f.read_bytes(), session=session)
        if mode == "plain":
            target.write_bytes(result)
        else:
            img = Image.open(io.BytesIO(result)).convert("RGBA")
            bg = Image.new("RGBA", img.size, (128, 128, 128, 255))
            Image.alpha_composite(bg, img).convert("RGB").save(target, "PNG")
        done += 1
    except Exception as e:
        failed += 1
        print(f"FAILED {f}: {e}", file=sys.stderr)

run_s = time.time() - t1
avg = run_s / max(done, 1)
print(f"{done} done, {failed} failed | model load {load_s:.1f}s | {avg:.1f}s/image | {model}/{provider}")
