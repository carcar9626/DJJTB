#!/bin/bash
# App Launcher: Launch applications with organized submenus
# Updated: July 20, 2025

function launch_app() {
    open -a "$1"
}

function app_launcher_main() {
    while true; do
        clear
        echo
        echo -e "\033[92m===================================\033[0m"
        printf "        \e[1;33m📱 APP LAUNCHER 🚀\n"
        echo -e "\033[92m===================================\033[0m"
        printf "\e[1;33mAPP CATEGORIES\n"
        echo -e "\033[92m-----------------------------------\033[0m"
        echo "1.📱 Daily Apps 🌟"
        echo "2.🔧 Tools & Utilities 🛠️"
        echo "3.🌐 Web Tools 🌍"
        echo "4.⚙️  System Utilities 🖥️"
        echo
        printf "\e[1;33mQUICK LAUNCH\n"
        echo -e "\033[92m-----------------------------------\033[0m"
        echo "5. Orion"
        echo "6. VLC"
        echo "7. JDownloader2"
        echo "8. Photomator"
        echo
        echo -e "\033[92m-----------------------------------\033[0m"
        echo -e " 0|00. ⏪ Back to DJJTB"
        echo -e "\033[92m===================================\033[0m"
        read -p $'\033[33m\nChoose an option: \n -> \033[0m' main_choice

        case "$main_choice" in
            1)
                # DAILY APPS
                while true; do
                    clear
                    echo
                    printf "\e[1;33m📱 DAILY APPS 🌟\n"
                    echo -e "\033[92m-------------------------------\033[0m"
                    echo "1. Telegram"
                    echo "2. Orion"
                    echo "3. JDownloader2"
                    echo "4. CotEditor"
                    echo "5. ChatGPT"
                    echo "6. GROK"
                    echo "7. VLC"
                    echo
                    echo -e "\033[92m-------------------------------\033[0m"
                    echo " 0. ⏪ Back to App Categories"
                    echo "00. ⏮️  Back to DJJTB"
                    echo -e "\033[92m-------------------------------\033[0m"
                    read -p $'\033[33mChoose app: \033[0m' daily_choice

                    case "$daily_choice" in
                        1) launch_app "Telegram Lite" ;;
                        2) launch_app "Orion" ;;
                        3) launch_app "JDownloader2" ;;
                        4) launch_app "CotEditor" ;;
                        5) launch_app "ChatGPT" ;;
                        6) launch_app "Grok" ;;
                        7) launch_app "VLC" ;;
                        0) break ;;
                        00) clear; return ;;
                        *) echo -e "\033[33mInvalid choice. Try again.\033[0m"; sleep 1 ;;
                    esac
                done
                ;;
                
            2)
                # TOOLS & UTILITIES
                while true; do
                    clear
                    echo
                    printf "\e[1;33m🔧 TOOLS & UTILITIES 🛠️\n"
                    echo -e "\033[92m-------------------------------\033[0m"
                    echo "1. A Better Finder Rename 12"
                    echo "2. dupeguru"
                    echo "3. Keka"
                    echo "4. BetterZip"
                    echo "5. Gray"
                    echo
                    echo -e "\033[92m-------------------------------\033[0m"
                    echo " 0. ⏪ Back to App Categories"
                    echo "00. ⏮️  Back to DJJTB"
                    echo -e "\033[92m-------------------------------\033[0m"
                    read -p $'\033[33mChoose a tool: \n\033[0m' tool_choice

                    case "$tool_choice" in
                        1) launch_app "A Better Finder Rename 12" ;;
                        2) launch_app "dupeguru" ;;
                        3) launch_app "Keka" ;;
                        4) launch_app "BetterZip" ;;
                        5) launch_app "Gray" ;;
                        0) break ;;
                        00) clear; return ;;
                        *) echo -e "\033[33mInvalid choice. Try again.\033[0m"; sleep 1 ;;
                    esac
                    
                done
                ;;
                
            3)
                # WEB TOOLS
                while true; do
                    clear
                    echo
                    printf "\e[1;33m🌐 WEB TOOLS 🌍\n"
                    echo -e "\033[92m-------------------------------\033[0m"
                    echo "1. NordVPN"
                    echo "2. Transmit"
                    echo "3. Motrix"
                    echo "4. Thunder (迅雷)"
                    echo "5. BaiduNetdisk"
                    echo
                    echo -e "\033[92m-------------------------------\033[0m"
                    echo " 0. ⏪ Back to App Categories"
                    echo "00. ⏮️  Back to DJJTB"
                    echo -e "\033[92m-------------------------------\033[0m"
                    read -p $'\033[33mChoose a tool: \033[0m' web_choice

                    case "$web_choice" in
                        1) launch_app "NordVPN" ;;
                        2) launch_app "Transmit" ;;
                        3) launch_app "Motrix" ;;
                        4) launch_app "迅雷" ;;
                        5) launch_app "BaiduNetdisk" ;;
                        0) break ;;
                        00) clear; return ;;
                        *) echo -e "\033[33mInvalid choice. Try again.\033[0m"; sleep 1 ;;
                    esac
                    
                done
                ;;
                
            4)
                # SYSTEM UTILITIES
                while true; do
                    clear
                    echo
                    printf "\e[1;33m⚙️  SYSTEM UTILITIES 🖥️\n"
                    echo -e "\033[92m-------------------------------\033[0m"
                    echo "1. System Settings"
                    echo "2. Disk Utility"
                    echo "3. Activity Monitor"
                    echo "4. Automator"
                    echo "5. NordPass"
                    echo "6. DriveDx"
                    echo "7. Logitech Options+"
                    echo
                    echo -e "\033[92m-------------------------------\033[0m"
                    echo " 0. ⏪ Back to App Categories"
                    echo "00. ⏮️  Back to DJJTB"
                    echo -e "\033[92m-------------------------------\033[0m"
                    read -p $'\033[33mChoose a system utility: \033[0m' sys_choice

                    case "$sys_choice" in
                        1) launch_app "System Settings" ;;
                        2) launch_app "Disk Utility" ;;
                        3) launch_app "Activity Monitor" ;;
                        4) launch_app "Automator" ;;
                        5) launch_app "NordPass" ;;
                        6) launch_app "DriveDx" ;;
                        7) launch_app "Logi Options+" ;;
                        0) break ;;
                        00) clear; return ;;
                        *) echo -e "\033[33mInvalid choice. Try again.\033[0m"; sleep 1 ;;
                    esac
                done
                ;;
            5) launch_app "Orion" ;;
            6) launch_app "VLC" ;;
            7) launch_app "JDownloader2" ;;
            8) launch_app "Photomator" ;;
            0|00)
                clear
                return
                ;;
            *)
                echo -e "\033[33mInvalid choice. Try again.\033[0m"
                sleep 1
                ;;
        esac
    done
}

# If run directly, start the app launcher
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    app_launcher_main
fi