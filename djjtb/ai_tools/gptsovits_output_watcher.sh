#!/bin/bash
# Watches Gradio's ephemeral temp folder for new GPT-SoVITS inference results
# and copies each one out to a permanent destination. Gradio itself never
# persists results anywhere durable — every "Start inference" click lands in
# a fresh random subfolder under $TMPDIR/gradio/, subject to macOS's own temp
# cleanup — so this just mirrors anything new out before that happens.
#
# Meant to be launched in the background by gptsovits_runner.command, not run
# standalone. Loops until killed.

DEST="/Volumes/Movies_2SSD/UD_Gens/Characters/TTS_SD/Output/GPT-SoVIT"
GRADIO_TMP="${TMPDIR%/}/gradio"
SEEN_LOG="/tmp/gptsovits_watcher_seen.txt"
PIDFILE="/tmp/gptsovits_watcher.pid"

# Idempotent: if a copy of this watcher is already running (from an earlier
# launch that's still alive), don't start a second one polling the same dirs.
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    exit 0
fi
echo $$ > "$PIDFILE"

touch "$SEEN_LOG"

while true; do
    mkdir -p "$DEST" 2>/dev/null

    if [ -d "$GRADIO_TMP" ] && [ -d "$DEST" ]; then
        find "$GRADIO_TMP" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | while read -r hashdir; do
            if [ -f "$hashdir/audio.wav" ] && ! grep -qxF "$hashdir" "$SEEN_LOG"; then
                ts=$(date +"%Y%m%d_%H%M%S")
                tag=$(basename "$hashdir" | cut -c1-8)
                if cp "$hashdir/audio.wav" "$DEST/${ts}_${tag}_gptsovits.wav" 2>/dev/null; then
                    echo "$hashdir" >> "$SEEN_LOG"
                fi
            fi
        done
    fi

    sleep 3
done
