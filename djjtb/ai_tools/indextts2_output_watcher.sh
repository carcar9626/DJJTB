#!/bin/bash
# Watches Gradio's ephemeral temp folder for new IndexTTS2 inference results
# and copies each one out to a permanent destination. Same underlying problem
# as gptsovits_output_watcher.sh: Gradio never persists results anywhere
# durable. Different signature here though — IndexTTS2's /gen_single results
# land as spk_<unix_timestamp>.wav, distinct from reference-audio uploads
# (which keep their original filename, e.g. sach_ref_trimmed.wav) — so this
# matches on the spk_*.wav pattern specifically to avoid archiving reference
# clips as if they were generated output.
#
# Meant to be launched in the background by indextts2_runner.command, not run
# standalone. Loops until killed.

DEST="/Volumes/Movies_2SSD/UD_Gens/Characters/TTS_SD/Output/IndexTTS"
GRADIO_TMP="${TMPDIR%/}/gradio"
SEEN_LOG="/tmp/indextts2_watcher_seen.txt"
PIDFILE="/tmp/indextts2_watcher.pid"

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
        find "$GRADIO_TMP" -mindepth 2 -maxdepth 2 -type f -name "spk_*.wav" 2>/dev/null | while read -r srcfile; do
            if ! grep -qxF "$srcfile" "$SEEN_LOG"; then
                ts=$(date +"%Y%m%d_%H%M%S")
                tag=$(basename "$(dirname "$srcfile")" | cut -c1-8)
                if cp "$srcfile" "$DEST/${ts}_${tag}_indextts2.wav" 2>/dev/null; then
                    echo "$srcfile" >> "$SEEN_LOG"
                fi
            fi
        done
    fi

    sleep 3
done
