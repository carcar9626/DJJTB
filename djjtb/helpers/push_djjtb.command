#!/bin/bash

# Premium ANSI terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

clear
echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}            DJJTB GitHub Sync Tool             ${NC}"
echo -e "${BLUE}===============================================${NC}\n"

# Navigate to the local repository
TARGET_DIR="/Users/home/Documents/Scripts/DJJTB"
if cd "$TARGET_DIR"; then
    echo -e "${GREEN}✓ Successfully entered directory:${NC} $TARGET_DIR\n"
else
    echo -e "${RED}✗ Error: Could not find directory:${NC} $TARGET_DIR"
    echo "Please double-check your path or folder location."
    echo ""
    read -p "Press [Enter] to exit..." exit_prompt
    exit 1
fi

# Clean up temporary __pycache__ directories
echo "Do you want to flush __pycache__ directories before pushing?"
echo "1. Yes (Recommended to keep it clean)"
echo "2. No"
read -p "Enter your choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    echo -e "\n${YELLOW}Cleaning up __pycache__ directories...${NC}"
    find . -name '__pycache__' -type d -exec rm -rf {} +
    echo -e "${GREEN}✓ __pycache__ directories successfully removed.${NC}\n"
else
    echo -e "\n${YELLOW}Skipping __pycache__ cleanup.${NC}\n"
fi

# Staging changes
echo -e "${BLUE}Staging all local changes...${NC}"
git add .

# Check if there are actual changes to commit before prompting
if git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}No new changes detected since last push. Proceeding to sync...${NC}"
else
    echo -e "Enter a commit message (or press [Enter] for default 'Auto commit'):"
    read -r commit_msg

    if [ -z "$commit_msg" ]; then
        commit_msg="Auto commit"
    fi

    echo -e "${BLUE}Committing changes: \"$commit_msg\"...${NC}"
    git commit -m "$commit_msg"
fi

# Configure Mac Keychain helper automatically
if [ "$(git config --global credential.helper)" != "osxkeychain" ]; then
    echo -e "${YELLOW}Configuring Git to use macOS Keychain for secure credential storage...${NC}"
    git config --global credential.helper osxkeychain
fi

# Pushing to GitHub
echo -e "\n${BLUE}Pushing to GitHub (origin main)...${NC}"
echo -e "${YELLOW}Note: If asked for credentials, use your GitHub username (carcar9626) and your Personal Access Token (PAT) as the password.${NC}\n"

if git push origin main; then
    echo -e "\n${GREEN}===============================================${NC}"
    echo -e "${GREEN}       ✓ Sync Completed Successfully!          ${NC}"
    echo -e "${GREEN}===============================================${NC}"
else
    echo -e "\n${RED}===============================================${NC}"
    echo -e "${RED}               ✗ Sync Failed!                  ${NC}"
    echo -e "${RED}===============================================${NC}"
    echo -e "Please check your network connection or Personal Access Token."
fi

echo ""
read -p "Press [Enter] to close this window..." exit_prompt