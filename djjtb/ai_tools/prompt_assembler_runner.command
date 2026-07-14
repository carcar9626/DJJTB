#!/bin/bash
# Double-click this to launch the Prompt Assembler.
# Serves the folder over http://localhost so the page can auto-fetch
# prompt_assembler.json instead of you pasting it in.

DIR="/Users/home/Documents/Scripts/FLOW_TOOLS/prompt_assembler/LOCAL"
PORT=8642
URL="http://localhost:$PORT/prompt_assembler.html"

cd "$DIR" || { echo "Could not find $DIR"; read -p "Press enter to close..."; exit 1; }

# Reuse an existing server on this port if one's already running
if ! lsof -i :$PORT >/dev/null 2>&1; then
    python3 -m http.server "$PORT" >/dev/null 2>&1 &
    sleep 0.5
fi

open -na "Google Chrome" --args --new-window "$URL"