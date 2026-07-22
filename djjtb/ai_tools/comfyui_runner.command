#!/bin/bash

source /Users/home/Documents/ai_models/ComfyUI_App/ComfyUI/cfuivenv/bin/activate  || exit 1

cd /Users/home/Documents/ai_models/ComfyUI_App/ComfyUI || exit 1

if lsof -nP -iTCP:8188 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "ComfyUI already appears to be running at http://localhost:8188"
    echo "Press any key to close this window..."
    read -n 1
    exit 0
fi

open -g -a "/Users/home/Applications/ComfyUI.app"

LOG_FILE="user/comfyui_launch_$(date +%Y%m%d_%H%M%S).log"
echo "Starting ComfyUI quietly... (full log: $LOG_FILE)"

python3 main.py --listen 0.0.0.0 --port 8188 --gpu-only > "$LOG_FILE" 2>&1 &
disown

for i in $(seq 1 60); do
    if grep -q "To see the GUI go to" "$LOG_FILE" 2>/dev/null; then
        echo "ComfyUI is ready: http://localhost:8188"
        break
    fi
    if ! kill -0 $! 2>/dev/null; then
        echo "ComfyUI stopped unexpectedly. Check the log: $LOG_FILE"
        break
    fi
    sleep 2
done

echo "You can close this window now — ComfyUI will keep running in the background."
echo "Press any key to close this window..."
read -n 1
