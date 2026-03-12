#!/bin/bash

source /Users/home/Documents/ai_models/facefusion/ffvenv/bin/activate || exit 1

cd /Users/home/Documents/ai_models/facefusion || exit 1

# Start iopaint in the background
python facefusion.py run &

# Give it a few seconds to fully start
sleep 5
open -g -a "/Users/home/Applications/Facefusion.app"
wait
echo "Press any key to close this window..."
read -n 1

