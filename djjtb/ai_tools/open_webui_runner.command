#!/bin/bash


echo "Starting Open WebUI..."

# Start existing container
docker start open-webui >/dev/null 2>&1

# Open Safari web app
open "/Users/home/Applications/Open WebUI.app"

echo "Open WebUI started."
exit 0
