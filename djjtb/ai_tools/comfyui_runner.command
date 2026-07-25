#!/bin/bash

source /Users/home/Documents/ai_models/ComfyUI_App/ComfyUI/cfuivenv/bin/activate  || exit 1

cd /Users/home/Documents/ai_models/ComfyUI_App/ComfyUI || exit 1
open -g -a "/Users/home/Applications/ComfyUI.app"

LOG_FILE="user/comfyui_launch_$(date +%Y%m%d_%H%M%S).log"
echo "Full startup log (tracebacks, fetch spam, etc): $LOG_FILE"

# Filters startup noise only (custom-node import tracebacks + their one-line
# "Cannot import..." reason, ComfyUI-Manager's registry fetch spam, frontend
# deprecation warnings). The node success/fail list itself always shows.
# Everything from "Starting server" onward (real usage: progress, errors,
# sampling) is passed through untouched, live, unfiltered.
PYTHONUNBUFFERED=1 python3 main.py --listen 0.0.0.0 --port 8188 2>&1 | tee "$LOG_FILE" | awk '
    {
        line = $0
        if (line ~ /^Starting server$/) { startup = 0 }

        if (startup) {
            if (skip_tb) {
                if (line ~ /^[ \t]/) { next }
                skip_tb = 0
                next
            }
            if (line ~ /^Traceback \(most recent call last\):$/) { skip_tb = 1; next }
            if (line ~ /^Cannot import .* module for custom nodes:/) { next }
        }

        if (line ~ /^FETCH ComfyRegistry Data:/) { next }
        if (line ~ /^\[DEPRECATION WARNING\]/) { next }

        print line
        fflush()
    }
    BEGIN { startup = 1 }
'

echo "Press any key to close this window..."
read -n 1
