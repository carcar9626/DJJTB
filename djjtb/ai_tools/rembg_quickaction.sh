#!/bin/bash

# ============================================================
# RMBG — Finder Quick Action
# Default : transparent PNG only            -> RMBG/<name>.png
# --grey  : mid-grey background version only -> RMBG/<name>_gry.png
# ============================================================

VENV="$HOME/Documents/ai_models/rembg/rmbgvenv"
MODEL_DIR="$HOME/Documents/ai_models/rembg"
PYTHON="$VENV/bin/python"

if [ ! -f "$PYTHON" ]; then
    osascript -e 'display alert "RMBG Error" message "Python not found in rmbgvenv. Check venv path." as critical'
    exit 1
fi

# --- Mode: first arg --grey switches to grey-only; otherwise plain ---
MODE="plain"
if [ "$1" = "--grey" ]; then
    MODE="grey"
    shift
fi

export U2NET_HOME="$MODEL_DIR"

for filepath in "$@"; do
    # Filter for images
    ext="${filepath##*.}"
    ext_lower=$(echo "$ext" | tr '[:upper:]' '[:lower:]')
    case "$ext_lower" in
        jpg|jpeg|png|webp|bmp|tiff|tif) ;;
        *) continue ;;
    esac

    parent_dir=$(dirname "$filepath")
    filename=$(basename "$filepath")
    name_no_ext="${filename%.*}"
    output_dir="$parent_dir/RMBG"
    mkdir -p "$output_dir"
    
    # Standard output is always the transparent PNG
    standard_output="$output_dir/${name_no_ext}.png"
    # Gray output is the second file
    gray_output="$output_dir/${name_no_ext}_gry.png"

    "$PYTHON" - "$filepath" "$standard_output" "$gray_output" "$MODE" <<'EOF'
import sys
from rembg import remove, new_session
from PIL import Image
import io
import os

input_path = sys.argv[1]
std_path = sys.argv[2]
gry_path = sys.argv[3]
mode = sys.argv[4]

# Skip if the one file this mode produces already exists
target = std_path if mode == "plain" else gry_path
if os.path.exists(target):
    sys.exit(0)

session = new_session("birefnet-general", providers=["CPUExecutionProvider"])

with open(input_path, "rb") as f:
    data = f.read()

result_bytes = remove(data, session=session)

if mode == "plain":
    with open(std_path, "wb") as f:
        f.write(result_bytes)
else:
    img = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
    bg = Image.new("RGBA", img.size, (128, 128, 128, 255))
    Image.alpha_composite(bg, img).convert("RGB").save(gry_path, "PNG")

EOF

done

osascript -e 'display notification "RMBG processing complete." with title "RMBG Tool"'