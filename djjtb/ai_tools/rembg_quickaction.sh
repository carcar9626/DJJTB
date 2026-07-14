#!/bin/bash

# ============================================================
# RMBG — Dual-Output Finder Quick Action
# Always saves transparent PNG + Optional _gry.png
# ============================================================

VENV="$HOME/Documents/ai_models/rembg/rmbgvenv"
MODEL_DIR="$HOME/Documents/ai_models/rembg"
PYTHON="$VENV/bin/python"

if [ ! -f "$PYTHON" ]; then
    osascript -e 'display alert "RMBG Error" message "Python not found in rmbgvenv. Check venv path." as critical'
    exit 1
fi

# --- Ask once per batch ---
USER_CHOICE=$(osascript -e 'display dialog "Create additional _gry versions for Flow/Qwen?" buttons {"No", "Yes"} default button "No" with title "RMBG Workflow"' 2>/dev/null)

if [[ "$USER_CHOICE" == *"button returned:Yes"* ]]; then
    WANT_GRAY=true
else
    WANT_GRAY=false
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

    "$PYTHON" - "$filepath" "$standard_output" "$gray_output" "$WANT_GRAY" <<'EOF'
import sys
from rembg import remove, new_session
from PIL import Image
import io
import os

input_path = sys.argv[1]
std_path = sys.argv[2]
gry_path = sys.argv[3]
want_gray = sys.argv[4].lower() == "true"

session = new_session("birefnet-general", providers=["CPUExecutionProvider"])

with open(input_path, "rb") as f:
    data = f.read()

# 1. Generate the transparent version
result_bytes = remove(data, session=session)

# Save the standard transparent PNG if it doesn't exist
if not os.path.exists(std_path):
    with open(std_path, "wb") as f:
        f.write(result_bytes)

# 2. If requested, generate and save the gray version
if want_gray and not os.path.exists(gry_path):
    img = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
    # Create the middle-gray background
    bg = Image.new("RGBA", img.size, (128, 128, 128, 255))
    # Composite subject over gray
    combined = Image.alpha_composite(bg, img)
    # Save as 3-channel RGB (ready for Flow)
    combined.convert("RGB").save(gry_path, "PNG")

EOF

done

osascript -e 'display notification "RMBG processing complete." with title "RMBG Tool"'