#!/bin/bash
# ComfyUI Launcher: Run ComfyUI in a new Terminal tab
# Created: July 12, 2025

export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
cd /Volumes/Movies_2SSD/ComfyUI
pyenv local 3.10.17
source .venv/bin/activate
export PYTORCH_ENABLE_MPS_FALLBACK=1
arch -arm64 python main.py --listen 0.0.0.0 --port 8188