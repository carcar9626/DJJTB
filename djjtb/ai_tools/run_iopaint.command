#!/bin/bash

source /Users/home/Documents/ai_models/watermark_remover/wmrmvenv/bin/activate  || exit 1

cd /Users/home/Documents/ai_models/iopaint || exit 1

# Start iopaint in the background
iopaint start --model=lama --device=cpu --port=8060 &

# Give it a few seconds to fully start
sleep 10

# Ask if you want to open WebUI
echo ""
echo "Open IOPaint WebUI?"
echo "1. Yes"
echo "2. No"
read -rp "Enter your choice: " choice

if [[ "$choice" == "1" ]]; then
    open -a "/Applications/IOPaint.app"
    echo "IOPaint webUI is running.... Ctrl+C to stop."
    # Keep the foreground terminal tied to the background process
    wait
fi

echo "Press any key to close this window..."
read -n 1

