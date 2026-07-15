#!/bin/bash

cd /Users/home/Documents/Scripts/DJJTB || exit 1

echo "Do you want to flush __pycache__ directories before pushing?"
echo "1. Yes"
echo "2. No"
read -p "Enter your choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    echo "Removing __pycache__ directories..."
    find . -name '__pycache__' -type d -exec rm -rf {} +
    echo "__pycache__ directories removed."
else
    echo "Skipping __pycache__ cleanup."
fi

echo "Adding all changes..."
git add .

echo "Enter commit message:"
read -r commit_msg

if [ -z "$commit_msg" ]; then
    commit_msg="Auto commit"
fi

git commit -m "$commit_msg"

echo "Pushing to origin main..."
git push origin main

echo "Done."