#!/bin/bash
# Double-click this to launch IndexTTS-2.5's webui (zero-shot voice cloning
# with independent emotion control), opened as a chromeless Chrome app window
# rather than a normal tab. Fully standalone install — own uv-managed .venv,
# not part of DJJTB's venv or the ai_models symlink tree. See
# DJJIF/ai_stack_port_registry.md for the port reservation and install notes.
#
# Unlike gptsovits_runner.command, no manual env activation is needed here —
# `uv run` handles that itself.

REPO="/Users/home/Documents/ai_models/IndexTTS-2"
WATCHER="/Users/home/Documents/Scripts/DJJTB/djjtb/ai_tools/indextts2_output_watcher.sh"
PORT=7861
URL="http://localhost:$PORT"

cd "$REPO" || { echo "Could not find $REPO"; read -n 1; exit 1; }

# Auto-copies every generated result out of Gradio's ephemeral temp folder
# into a permanent output dir — no separate step to remember each launch.
# Detached (nohup + disown) on purpose: it should keep running and de-dupe
# across launches regardless of whether this terminal window stays open, and
# it no-ops immediately if a copy from an earlier launch is still alive.
nohup bash "$WATCHER" >/dev/null 2>&1 &
disown

# Reuse an existing server on this port if one's already running
if ! lsof -i :$PORT >/dev/null 2>&1; then
    ~/.local/bin/uv run webui.py --port $PORT &

    echo "Waiting for IndexTTS-2.5 to finish loading models..."
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
