#!/bin/bash

cd /Users/home/Documents/ai_models/watermark_remover || exit 1
source wmrmvenv/bin/activate

cd /Users/home/Documents/ai_models/iopaint || exit 1

# Start iopaint in the background
iopaint start --model=lama --device=cpu --port=8060 &

# Give it a few seconds to fully start
sleep 10

# Ask if you want to open WebUI
echo ""
echo "Open WebUI in browser?"
echo "1. Yes"
echo "2. No"
read -rp "Enter your choice (1/2): " choice

if [[ "$choice" == "1" ]]; then
    open -na "Firefox" --args "http://localhost:8060"
fi

# Keep the foreground terminal tied to the background process
wait