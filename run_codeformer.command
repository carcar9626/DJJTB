#!/bin/bash

# Clear the terminal for a clean interface
clear
echo
echo -e "\033[92m===================================\033[0m"
echo -e "           \033[1;33mCodeformer\033[0m"
echo -e "   Face Restore & UpScale Tool"
echo -e "\033[92m===================================\033[0m"

function what_next() {
    echo
    echo -e "\033[33mWhat Next?\033[0m"
    echo "1. Again"
    echo "2. Return to DJJTB"
    echo "3. Exit"
    echo
    read -p "> " choice
    case "$choice" in
        1)
            clear
            return 0  # continue loop
            ;;
        2)
            echo "🔁 Returning to DJJTB..."
            # Replace this with actual return call if needed
            exit 0
            ;;
        3)
            echo "👋 Exiting."
            exit 0
            ;;
        *)
            echo "Invalid choice. Defaulting to Return to DJJTB."
            exit 0
            ;;
    esac
}
# Activate virtual environment
source /Volumes/Desmond_SSD_2TB/Codeformer/cfvenv/bin/activate
cd /Volumes/Desmond_SSD_2TB/Codeformer

while true; do
    # Prompt for input path
        echo "Enter path:"
        read -p " -> " input_path
    if [ -z "$input_path" ]; then
        echo -e "\033[91mError: Input path cannot be empty.\033[0m"
        echo "Press Enter to try again..."
        read
        continue
    fi

    # Check if input is a directory, single image, or single video
    if [ -d "$input_path" ]; then
        # Check if directory contains at least one image or video file
        if ! find "$input_path" -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.mp4" -o -iname "*.mov" -o -iname "*.avi" \) | grep -q .; then
            echo -e "\033[91mError: Directory '$input_path' contains no supported files (.jpg, .jpeg, .png, .mp4, .mov, .avi).\033[0m"
            echo "Press Enter to try again..."
            read
            continue
        fi
    elif [ -f "$input_path" ]; then
        # Check if the file is an image or video
        if ! [[ "$input_path" =~ \.(jpg|jpeg|png|mp4|mov|avi)$ ]]; then
            echo -e "\033[91mError: File '$input_path' is not a supported image (.jpg, .jpeg, .png) or video (.mp4, .mov, .avi).\033[0m"
            echo "Press Enter to try again..."
            read
            continue
        fi
    else
        echo -e "\033[91mError: Path '$input_path' does not exist or is not a file/directory.\033[0m"
        echo "Press Enter to try again..."
        read
        continue
    fi

    # Create output path
    output_path="$(dirname "$input_path")/Output/CF"
    mkdir -p "$output_path"
    if [ $? -ne 0 ]; then
        echo -e "\033[91mError: Could not create output directory '$output_path'. Please check permissions.\033[0m"
        echo "Press Enter to try again..."
        read
        continue
    fi

    # Prompt for weight with default and validation
    echo "Enter weight (default 0.7, range 0.0-1.0):"
    read weight
    weight=${weight:-0.7}
    if ! [[ "$weight" =~ ^[0-1](\.[0-9]+)?$ ]] || (( $(echo "$weight < 0 || $weight > 1" | bc -l) )); then
        echo -e "\033[91mError: Weight must be a number between 0.0 and 1.0. Using default 0.7.\033[0m"
        weight=0.7
    fi

    # Prompt for suffix with default and validation
    echo "Enter suffix (default _CF):"
    read suffix
    suffix=${suffix:-_CF}
    if [ -z "$suffix" ]; then
        echo -e "\033[91mError: Suffix cannot be empty. Using default _CF.\033[0m"
        suffix="_CF"
    fi

    # Prompt for upscale with default and validation
    echo "Enter upscale factor (default 2, integer >= 1):"
    read upscale
    upscale=${upscale:-2}
    if ! [[ "$upscale" =~ ^[1-9][0-9]*$ ]]; then
        echo -e "\033[91mError: Upscale factor must be an integer >= 1. Using default 2.\033[0m"
        upscale=2
    fi

    # Display parameters
    echo
    echo -e "\033[92mPrcocess Summary:\033[0m"
    echo
    echo "Input Path: $input_path"
    echo "Output Path: $output_path"
    echo "Weight: $weight"
    echo "Suffix: $suffix"
    echo "Upscale: $upscale"
    echo
    echo -e "\033[92mCodeformer starting...\033[0m"
    echo

    # Run CodeFormer
    PYTHONPATH=. python3 inference_codeformer.py \
        -i "$input_path" \
        -o "$output_path" \
        -w "$weight" \
        --suffix "$suffix" \
        --upscale "$upscale"

    # Check if command was successful
    if [ $? -eq 0 ]; then
        echo -e "\033[92mCodeFormer processing completed successfully!\033[0m"
    else
        echo -e "\033[91mError: CodeFormer processing failed.\033[0m"
    fi
    what_next
   
    clear
    echo
    echo -e "\033[92m===================================\033[0m"
    echo -e "           \033[1;33mCodeformer\033[0m"
    echo -e "   Face Restore & UpScale Tool"
    echo -e "\033[92m===================================\033[0m"

    
# Deactivate virtual environment
deactivate
done
echo "Press Enter to close..."
read