#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

clear
echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}              Stop ComfyUI                     ${NC}"
echo -e "${BLUE}===============================================${NC}\n"

PID=$(lsof -tiTCP:8188 -sTCP:LISTEN 2>/dev/null)

if [ -z "$PID" ]; then
    echo -e "${YELLOW}ComfyUI isn't running (nothing on port 8188).${NC}"
else
    echo -e "${BLUE}Stopping ComfyUI (pid $PID)...${NC}"
    kill "$PID"

    for i in $(seq 1 10); do
        if ! kill -0 "$PID" 2>/dev/null; then
            echo -e "${GREEN}✓ ComfyUI stopped.${NC}"
            break
        fi
        sleep 1
    done

    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${YELLOW}Still running, forcing it closed...${NC}"
        kill -9 "$PID" 2>/dev/null
        echo -e "${GREEN}✓ ComfyUI stopped.${NC}"
    fi
fi

echo ""
read -p "Press [Enter] to close this window..." exit_prompt
