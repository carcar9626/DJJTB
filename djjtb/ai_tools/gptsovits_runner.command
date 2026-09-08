#!/bin/bash
# Double-click this to launch GPT-SoVITS's inference-only WebUI (zero-shot
# voice cloning), opened as a chromeless Chrome app window rather than a
# normal tab. Fully standalone install — own conda env, not part of DJJTB's
# venv or the ai_models symlink tree. See DJJIF/ai_stack_port_registry.md
# for the port reservation and install notes.

REPO="/Users/home/Documents/ai_models/GPT-SoVITS"
WATCHER="/Users/home/Documents/Scripts/DJJTB/djjtb/ai_tools/gptsovits_output_watcher.sh"
PORT=9872
URL="http://localhost:$PORT"

source ~/miniforge3/etc/profile.d/conda.sh || { echo "Could not source conda"; read -n 1; exit 1; }
conda activate GPTSoVits || { echo "Could not activate GPTSoVits env"; read -n 1; exit 1; }

cd "$REPO" || { echo "Could not find $REPO"; read -n 1; exit 1; }

# Required: inference_webui.py imports "config" from the repo root and
# "text.*" from GPT_SoVITS/ at the same time, which only resolves if the
# repo root is explicitly on PYTHONPATH.
export PYTHONPATH="$REPO"

# Suppress Gradio's own auto-open (a plain browser tab) — we open Chrome
# ourselves below, in app mode, once the server is actually ready.
export BROWSER=true

# Auto-copies every generated result out of Gradio's ephemeral temp folder
# into a permanent output dir — no separate step to remember each launch.
# Detached (nohup + disown) on purpose: it should keep running and de-dupe
# across launches regardless of whether this terminal window stays open, and
# it no-ops immediately if a copy from an earlier launch is still alive.
nohup bash "$WATCHER" >/dev/null 2>&1 &
disown

# Reuse an existing server on this port if one's already running
if ! lsof -i :$PORT >/dev/null 2>&1; then
    python GPT_SoVITS/inference_webui.py &

    echo "Waiting for GPT-SoVITS to finish loading models..."
    for i in $(seq 1 90); do
        if curl -s -o /dev/null "$URL"; then
            break
        fi
        sleep 1
    done
fi

open -na "Google Chrome" --args --app="$URL"

wait
echo "Press any key to close this window..."
read -n 1
