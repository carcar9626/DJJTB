#!/bin/bash

# ============================================================
# RMBG — Finder Quick Action
# Default : transparent PNG only            -> RMBG/<name>.png
# --grey  : mid-grey background version only -> RMBG/<name>_gry.png
# ============================================================

# --- settings ---
MODEL_NAME="birefnet-general"   # lighter/faster alternative: birefnet-general-lite
PROVIDER="cpu"                  # "coreml" = try Apple GPU / Neural Engine (test first)
LOG="$HOME/Documents/Scripts/DJJTB/logs/rmbg.log"
# ----------------

VENV="$HOME/Documents/ai_models/rembg/rmbgvenv"
MODEL_DIR="$HOME/Documents/ai_models/rembg"
PYTHON="$VENV/bin/python"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
export RMBG_MODEL="$MODEL_NAME"
export RMBG_PROVIDER="$PROVIDER"

# --- collect image files only ---
FILES=()
for filepath in "$@"; do
    ext_lower=$(echo "${filepath##*.}" | tr '[:upper:]' '[:lower:]')
    case "$ext_lower" in
        jpg|jpeg|png|webp|bmp|tiff|tif) FILES+=("$filepath") ;;
    esac
done

if [ ${#FILES[@]} -eq 0 ]; then
    osascript -e 'display notification "No images in selection." with title "RMBG Tool"'
    exit 0
fi

# --- ONE python process for the whole batch (model loads once) ---
mkdir -p "$(dirname "$LOG")"
SUMMARY=$("$PYTHON" "$SCRIPT_DIR/rembg_batch.py" "$MODE" "${FILES[@]}" 2>>"$LOG" | tail -n 1)
echo "$(date '+%Y-%m-%d %H:%M:%S') [$MODE] ${#FILES[@]} selected | $SUMMARY" >> "$LOG"

osascript -e "display notification \"$SUMMARY\" with title \"RMBG Tool ($MODE)\""
