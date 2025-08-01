#!/bin/bash

cd /Users/home/Documents/Scripts/DJJTB || exit 1

echo "🛑 This will force push and overwrite the remote repository!"

# Ensure djjvenv is ignored
if ! grep -q '^djjvenv/$' .gitignore; then
    echo "Adding 'djjvenv/' to .gitignore..."
    echo "djjvenv/" >> .gitignore
else
    echo "'djjvenv/' is already in .gitignore."
fi

# Remove djjvenv from git tracking if already added before
if git ls-files --error-unmatch djjvenv/ >/dev/null 2>&1; then
    echo "Removing 'djjvenv/' from Git tracking..."
    git rm -r --cached djjvenv/
fi
echo
echo "Do you want to flush __pycache__ directories before pushing?"
echo "1. Yes"
echo "2. No"
read -p "Enter your choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    echo "Removing __pycache__ directories..."
    find . -name '__pycache__' -type d -exec rm -rf {} +
    echo "__pycache__ directories removed."
    read -p "✅ Cache flushed. Continue with git add + push?\n1. Yes, 2. No: " confirm
    echo
    if [[ "$confirm" != "1" ]]; then
        echo "❌ Aborting push."
        exit 1
    fi
else
    echo "Skipping __pycache__ cleanup."
fi
echo
echo "Adding all changes..."
git add .
echo
echo "Enter commit message:"
read -r commit_msg
echo
if [ -z "$commit_msg" ]; then
    commit_msg="Auto commit"
fi

git commit -m "$commit_msg"

echo "Force pushing to origin main (overwriting remote)..."
git push origin main --force
echo
echo "Done."