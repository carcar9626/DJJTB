#!/bin/bash
# Media Processor: Run Video or Image Processor
# Updated: July 11, 2025

osascript -e 'tell application "Terminal" to set bounds of front window to {663, 200, 1010, 760}' 2> /tmp/osascript_error.log
osascript -e 'tell application "Terminal" to set current settings of front window to settings set "djjtb"'

clear
cleanup_tabs() {
    echo "\033[33mClosing extra tabs...\033[0m"
    osascript -e '
    tell application "Terminal"
        activate
        delay 0.2
        tell window 1
            set tabCount to count of tabs
            repeat with i from tabCount to 2 by -1
                try
                    close tab i
                end try
            end repeat
        end tell
    end tell' 2>/dev/null
}
if [ -s /tmp/osascript_error.log ]; then
    echo "\033[33mError setting menu window bounds or profile:\033[0m"
    cat /tmp/osascript_error.log
fi
skip_countdown=false
function return_to_menu_delay() {
    echo
    echo "\033[33mReturning to previous menu in 8 seconds... (press any key to skip)\033[0m"
    for i in {8..1}; do
        read -t 1 -n 1 key && break
        echo -ne "$i...\r"
    done
    clear
}

clear
while true; do
    clear
    echo
    echo -e "\033[92m===================================\033[0m"
    printf "        \e[1;33m🧰 DJJ TOOLBOX 💻\n"
    echo -e "\033[92m===================================\033[0m"
    printf "\e[1;33mMAIN MENU\n"
    echo -e "\033[92m-----------------------------------\033[0m"
    echo "1.🎞️  MEDIA TOOLS 🎑"
    echo "2.🤖 AI TOOLS 🦾"
    echo
    printf "\e[1;33mQUICK TOOLS\n"
    echo -e "\033[92m-----------------------------------\033[0m"
    echo "3.🌠 Reverse Image Search 🔎"
    echo "4.🔗 Linkgrabber ✊🏼"
    echo "5.📺 Media Info Viewer ℹ️"
    echo "6.📱 APP LAUNCHER 🚀"
    echo -e "\033[92m-----------------------------------\033[0m"
    echo -e "✈️ E\033[91mx\033[0mit    🗂️ \033[1;32mC\033[0mlean Tabs"
    echo -e "\033[92m===================================\033[0m"
    read -p $'\033[33mChoose a category: \033[0m' main_choice

    case "$main_choice" in
        1)  # Media Tools
            while true; do
                clear
                echo
                echo
                printf "\e[1;33m🎇 MEDIA TOOLS 📽️ \n"
                echo -e "\033[92m-------------------------------\033[0m"
                echo " 1. VIDEOS"
                echo " 2. IMAGES"
                echo " 3. Media Sorter"
                echo " 4. Playlist Generator"
                echo
                printf "\e[1;33m📱 APPS 💻 \n"
                echo -e "\033[92m-------------------------------\033[0m"
                echo " 5. Photomator"
                echo " 6. Pixelmator"
                echo " 7. DaVinci Resolve"
                echo " 8. Wondershare Uniconverter"
                echo " 9. Handbrake"
                echo "10. CollageIt 3"
                echo
                echo -e "\033[92m-------------------------------\033[0m"
                echo " 0. ⏪ Back"
                echo "00. ⏮️  MAIN MENU"
                echo -e "\033[92m-------------------------------\033[0m"
                read -p $'\033[33mChoose a Tool: \033[0m' media_choice

                case "$media_choice" in
                    1)  # Videos
                        first_entry=true
                        while true; do
                            clear
                            echo
                            echo
                            echo "🎬 VIDEO TOOLS 🎬"
                            echo -e "\033[92m-------------------------------\033[0m"
                            echo "1. Video Re-encoder 📼➡︎📀"
                            echo "2. Reverse Merge ↪️ ⇔↩️"
                            echo "3. Slideshow Watermark 📹 🆔"
                            echo "4. Cropper 👖➡︎🩳"
                            echo "5. Group Merger 📹 🧲 "
                            echo "6. Video Splitter 📹 ✂️  ⏱️"
                            echo "7. Speed Changer 🐇⬌🐢"
                            echo "8. Frame Extractor 📹➡︎🌃🌆🎆🎇"
                            echo
                            echo -e "\033[92m-------------------------------\033[0m"
                            echo " 0. ⏪ Back to MEDIA TOOLS"
                            echo "00. ⏮️  MAIN MENU"
                            echo -e "\033[92m-------------------------------\033[0m"
    
                            if [ "$first_entry" = true ]; then
                                read -p $'\033[33mChoose a Tool: \033[0m' video_tool
                                first_entry=false
                            else
                                echo
                                echo -e "\033[33mPress any key to choose another option, or wait 8 seconds to return to Media Tools...\033[0m"
                                skip_countdown=false
                                for i in {8..1}; do
                                    read -t 1 -n 1 key
                                    if [ $? -eq 0 ]; then
                                        skip_countdown=true
                                    fi
                                    echo -ne "$i...\r"
                                done
                    
                                if [ "$skip_countdown" = false ]; then
                                    break  # ✅ Exit the VIDEO submenu, return to MEDIA TOOLS
                                fi
                                read -p $'\033[33mChoose another option: \033[0m' video_tool
                            fi
                            case "$video_tool" in
                                1)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.video_tools.video_re-encoder" in selected tab of the front window
end tell
EOF
                                    ;;
                                2)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.video_tools.video_reverse_merge" in selected tab of the front window
end tell
EOF
                                    ;;
                                3)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.video_tools.video_slideshow_watermark" in selected tab of the front window
end tell
EOF
                                    ;;
                                4)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.video_tools.video_cropper" in selected tab of the front window
end tell
EOF
                                    ;;
                                5)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.video_tools.video_group_merger" in selected tab of the front window
end tell
EOF
                                    ;;
                                6)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.video_tools.video_splitter" in selected tab of the front window
end tell
EOF
                                    ;;
                                7)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.video_tools.video_speed_changer" in selected tab of the front window
end tell
EOF
                                    ;;
                                8)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.video_tools.video_frame_extractor" in selected tab of the front window
end tell
EOF
                                    ;;
                                0)
                                    skip_countdown=true
                                    break ;;
                                00)
                                    osascript -e 'tell application "Terminal" to tell application "System Events" to keystroke "1" using command down' 2>> /tmp/osascript_error.log
                                    skip_countdown=true
                                    break 2 ;; # Break out of both Video Tools and Media Tools loops to return to Main Menu
                                *)
                                    echo "Invalid input"
                                    first_entry=false
                                    ;;
                            esac
                            if [ -n "$video_tool" ] && [ "$video_tool" != "6" ] && [ "$video_tool" != "7" ]; then
                                echo
                                echo "Press any key to choose another option, or wait to return to Media Tools..."
                                for i in {8..1}; do
                                    read -t 1 -n 1 key && break
                                    echo -ne "$i...\r"
                                done
                                if [ -z "$key" ]; then
                                    skip_countdown=true
                                    break
                                fi
                            fi
                        done
                        ;;
                    2)  # Images
                        first_entry=true
                        while true; do
                            clear
                            echo
                            echo
                            echo "🖼️  IMAGES TOOLS 🖼️"
                            echo -e "\033[92m-------------------------------\033[0m"
                            echo "1. Image Converter 🎞️ ➡︎🌠"
                            echo "2. Strip Padding 🔲➡︎⬜️"
                            echo "3. Flip or Rotate ↔️  🔄"
                            echo "4. Collage Creation 🧩 🎇"
                            echo "5. Resize Images 🩷⬌💓"
                            echo "6. Slideshow Maker 🎑➡︎📽️"
                            echo "7. Image Pairing ✋🏼 🤲🏼"
                            echo "8. Image Padding ◼️➡︎🔳"
                            echo
                            echo -e "\033[92m-------------------------------\033[0m"
                            echo " 0. ⏪ Back to MEDIA TOOLS"
                            echo "00. ⏮️  MAIN MENU"
                            echo -e "\033[92m-------------------------------\033[0m"
                            if [ "$first_entry" = true ]; then
                                read -p $'\033[33mChoose a Tool: \033[0m' img_tool
                                first_entry=false
                            else
                                read -t 8 -p $'\033[33mChoose another option, back to Media Tools in 8s: \033[0m' img_tool || {
                                    skip_countdown=true
                                    break
                                }
                            fi
                            case "$img_tool" in
                                1)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.image_tools.image_converter" in selected tab of the front window
end tell
EOF
                                    ;;
                                2)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.image_tools.image_strip_padding" in selected tab of the front window
end tell
EOF
                                    ;;
                                3)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.image_tools.image_flip_rotate" in selected tab of the front window
end tell
EOF
                                    ;;
                                4)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.image_tools.image_collage_creator" in selected tab of the front window
end tell
EOF
                                    ;;
                                5)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "cd ~/Documents/Scripts/DJJTB; source djjvenv/bin/activate; export PYTHONPATH=.; python3 -m djjtb.media_tools.image_tools.image_resizer" in selected tab of the front window
end tell
EOF
                                    ;;
                                6)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.image_tools.image_slideshow_maker" in selected tab of the front window
end tell
EOF
                                    ;;
                                7)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.image_tools.image_pairing" in selected tab of the front window
end tell
EOF
                                    ;;
                                8)
                                    osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.image_tools.image_padder" in selected tab of the front window
end tell
EOF
                                    ;;

                                0)
                                    skip_countdown=true
                                    break ;;
                                00)
                                    osascript -e 'tell application "Terminal" to tell application "System Events" to keystroke "1" using command down' 2>> /tmp/osascript_error.log
                                    skip_countdown=true
                                    break 2 ;; # Break out of both Images Tools and Media Tools loops to return to Main Menu
                                *)
                                    echo "\033[33mInvalid input\033[0m"
                                    first_entry=false
                                    ;;
                            esac
                            if [ -n "$img_tool" ] && [ "$img_tool" != "4" ] && [ "$img_tool" != "5" ]; then
                                
                                echo
                                echo -e "\033[33mPress any key to choose another option, or wait to return to Media Tools...\033[0m"
                                for i in {8..1}; do
                                    read -t 1 -n 1 key && break
                                    echo -ne "\033[33m$i\r\033[0m"
                                done
                                if [ -z "$key" ]; then
                                    skip_countdown=true
                                    break
                                fi
                            fi
                        done
                        ;;
                    3)  # Media Sorter
                        osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.media_sorter" in selected tab of the front window
end tell
EOF
                        ;;
                    4)  # Media Sorter
                        osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.media_tools.playlist_generator" in selected tab of the front window
end tell
EOF
                        ;;
                    5)
                        open "/Applications/Photomator.app"
                        ;;
                    6)
                        open "/Applications/Pixelmator Pro.app"
                        ;;
                    7)
                        open "/Applications/DaVinci Resolve/DaVinci Resolve.app"
                        ;;
                    8)
                        open "/Applications/Wondershare UniConverter 15.app"
                        ;;
                    9)
                        open "/Applications/HandBrake.app"
                        ;;
                    10)
                        open "/Applications/CollageIt 3.app"
                        ;;
                    0|00) skip_countdown=true
                       break ;;
                    *) echo "\033[33mInvalid input\033[0m";;
                esac
                if [ "$choice_made" = true ]; then
                    return_to_menu_delay
                fi
            done
            ;;

        2)  # AI Tools
            while true; do
                clear
                echo
                echo "🤖 AI TOOLS 🛠️"
                echo -e "\033[92m-------------------------------\033[0m"
                echo "1. Prompt Randomizer 📝 🔀"
                echo "2. ComfyUI ☀️ 💻"
                echo "3. Merge Loras 👫➡︎🧍🏼‍♂️"
                echo "4. Codeformer 😶‍🌫️➡︎😝"
                echo
                echo -e "\033[92m-------------------------------\033[0m"
                echo " 0. ⏪ Back"
                echo "00. ⏮️  MAIN MENU"
                echo -e "\033[92m-------------------------------\033[0m"
                read -p $'\033[33mChoose an AI tool: \033[0m' ai_choice
                case "$ai_choice" in
                    1)
                        osascript <<EOF
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB/djjtb/ai_tools/; python3 -m djjtb.media_tools.ai_tools.prompt_randomizer" in selected tab of the front window
end tell
EOF
                        ;;
                    2)
                        osascript <<EOF
tell application "Terminal"
    activate
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "/Users/home/Documents/Scripts/DJJTB/djjtb/ai_tools/comfyui_media_processor.command" in selected tab of front window
end tell
EOF
                        ;;
                    3)
                        source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate
                        cd /Users/home/Documents/Scripts/DJJTB/djjtb/ai_tools
                        python3 -m djjtb.media_tools.merge_loras.py
                        deactivate
                        ;;
                    4)
                        osascript <<EOF
tell application "Terminal"
    activate
    tell application "System Events" to keystroke "t" using command down
    delay 0.2
    do script "/Users/home/Documents/Scripts/DJJTB/djjtb/ai_tools/run_codeformer.command" in selected tab of front window
end tell
EOF
                        ;;
                    0|00) skip_countdown=true
                       break ;;
                    *) echo "Invalid input";;
                esac
            done
            ;;
        3)
            osascript <<EOF
tell application "Terminal"
    activate
    set newWindow to (do script "")
    set current settings of front window to settings set "LinkGrabber"
    
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.quick_tools.reverse_image_search" in selected tab of the front window
    delay 0.2
    set bounds of front window to {50, 282, 250, 482}
end tell
EOF
            ;;
        4)
            osascript <<EOF
tell application "Terminal"
    activate
    set newWindow to (do script "")
    set current settings of front window to settings set "LinkGrabber"
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB; python3 -m djjtb.quick_tools.link_grabber" in front window
    delay 0.3
    set bounds of front window to {50, 700, 600, 930}
end tell
EOF
            ;;
        5)
            osascript <<EOF
tell application "Terminal"
    activate
    set newWindow to (do script "")
    set current settings of front window to settings set "LinkGrabber"
    do script "source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate; cd /Users/home/Documents/Scripts/DJJTB/; python3 -m djjtb.quick_tools.media_info_viewer" in front window
    delay 0.3
    set bounds of front window to {50, 80, 250, 280}
end tell
EOF
            ;;
        6)
            source ~/Documents/Scripts/DJJTB/djjvenv/bin/activate
            bash /Users/home/Documents/Scripts/DJJTB/djjtb/quick_tools/app_launcher.command
            deactivate
            ;;
            
        c)
            cleanup_tabs
            ;;
        x)
            echo "\033[33mExiting...\033[0m"
            break
            ;;
        *)
            echo "\033[33mInvalid choice. Try again.\033[0m"
            ;;
    esac

    echo
    clear

    echo
done