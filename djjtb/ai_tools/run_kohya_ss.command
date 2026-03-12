#!/bin/bash

source /Users/home/Documents/ai_models/kohya_ss/kyvenv/bin/activate || exit 1

cd /Users/home/Documents/ai_models/kohya_ss || exit 1

# Start kohya_ss in the background

# Ask if you want to open WebUI
echo ""
echo "Open Kohya_SS WebUI?"
echo "1. Yes"
echo "2. No"
read -rp "Enter your choice: " choice

if [[ "$choice" == "1" ]]; then
    open -a "/Users/home/Applications/Kohya_ss.app"
    echo "Kohya_ss webUI running, Ctrl+C to stop."
    # Keep the foreground terminal tied to the background process
    wait
fi
python kohya_gui.py --server_port 7861

echo "Press any key to close this window..."
read -n 1
