#!/bin/bash

source /Users/home/Documents/ai_models/facefusion/ffvenv/bin/activate || exit 1

cd /Users/home/Documents/ai_models/facefusion || exit 1

# Start iopaint in the background
python facefusion.py run &

# Give it a few seconds to fully start
sleep 10

# Ask if you want to open WebUI
echo ""
echo "Open Facefusion WebUI?"
echo "1. Yes"
echo "2. No"
read -rp "Enter your choice: " choice

if [[ "$choice" == "1" ]]; then
    open -a "/Users/home/Applications/Facefusion.app"
    echo "Facefusion webUI running, Ctrl+C to stop."
    # Keep the foreground terminal tied to the background process
    wait
fi

echo "Press any key to close this window..."
read -n 1
