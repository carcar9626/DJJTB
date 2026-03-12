#!/bin/bash

ARCHIVE="/Users/home/Documents/Scripts/env_archive"
DATE=$(date +"%Y%b%d")

snapshot () {
    NAME="$1"
    PATH_IN="$2"
    OUT="$ARCHIVE/${NAME}_${DATE}.tar.gz"

    echo "📦 Archiving $NAME ..."
    tar -czf "$OUT" -C "$(dirname "$PATH_IN")" "$(basename "$PATH_IN")"
    echo "✅ Saved -> $OUT"
    echo ""
}

snapshot jtvenv "/Users/home/Documents/ai_models/joytag/jtvenv"
snapshot ffvenv "/Users/home/Documents/ai_models/facefusion/ffvenv"
snapshot cfvenv "/Users/home/Documents/ai_models/CodeFormer/cfvenv"
snapshot djjtbvenv "/Users/home/Documents/Scripts/DJJTB/venv"

echo "🎉 ALL ENV SNAPSHOTS COMPLETE"