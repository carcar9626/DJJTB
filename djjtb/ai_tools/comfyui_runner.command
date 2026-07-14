#!/bin/bash

source /Users/home/Documents/ai_models/ComfyUI_App/ComfyUI/cfuivenv/bin/activate  || exit 1

cd /Users/home/Documents/ai_models/ComfyUI_App/ComfyUI || exit 1
open -g -a "/Users/home/Applications/ComfyUI.app"

# Start comfyui in the background

python3 main.py --listen 0.0.0.0 --port 8188
echo "Press any key to close this window..."
read -n 1

