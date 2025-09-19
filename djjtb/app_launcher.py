#!/usr/bin/env python3
import os
import pathlib
from djjtb import utils as djj

# -------------------------------
# App Launcher Function
# -------------------------------
def run_app_launcher():
    """
    Integrated app launcher function that runs the full app launcher
    This replaces the external script call
    """
    # Daily Apps
    daily_apps = {
        '1': 'Telegram Lite',
        '2': 'Orion',
        '3': 'JDownloader2',
        '4': 'CotEditor',
        '5': 'ChatGPT',
        '6': 'Grok',
        '7': 'VLC'
    }
    
    # Tools & Utilities
    tools_utilities = {
        '1': 'A Better Finder Rename 12',
        '2': 'dupeguru',
        '3': 'Keka',
        '4': 'BetterZip',
        '5': 'Gray'
    }
    
    # Web Tools
    web_tools = {
        '1': 'NordVPN',
        '2': 'Transmit',
        '3': 'Motrix',
        '4': '迅雷',
        '5': 'BaiduNetdisk'
    }
    
    # System Utilities
    system_utilities = {
        '1': 'System Settings',
        '2': 'Disk Utility',
        '3': 'Activity Monitor',
        '4': 'Automator',
        '5': 'NordPass',
        '6': 'DriveDx',
        '7': 'Logi Options+'
    }
    
    # Quick Launch apps
    quick_launch = {
        '5': 'Orion',
        '6': 'VLC',
        '7': 'JDownloader2',
        '8': 'Photomator'
    }
    
    back_options = {'0': 'Back to App Launcher', '00': 'Back to DJJTB'}
    
    while True:
        os.system('clear')
        print("\033[92m==================================================\033[0m")
        print("\033[1;93m📱 APP LAUNCHER 🚀\033[0m")
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mAPP CATEGORIES\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print("1.📱 Daily Apps 🌟")
        print("2.🔧 Tools & Utilities 🛠️")
        print("3.🌐 Web Tools 🌍")
        print("4.⚙️  System Utilities 🖥️")
        print()
        print("\033[1;93mQUICK LAUNCH\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print("5. Orion")
        print("6. VLC")
        print("7. JDownloader2")
        print("8. Photomator")
        print()
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 0|00 ✈️ E\033[91mx\033[0mit")
        print("\033[92m==================================================\033[0m")
        
        choice = djj.prompt_choice(
            "\033[93mChoose an option: \033[0m",
            ['1', '2', '3', '4', '5', '6', '7', '8', '0', '00','x']
        )
        
        if choice == '1':
            result = djj.handle_app_menu("📱 DAILY APPS 🌟", daily_apps, back_options)
            if result == 'exit':
                break
        elif choice == '2':
            result = djj.handle_app_menu("🔧 TOOLS & UTILITIES 🛠️", tools_utilities, back_options)
            if result == 'exit':
                break
        elif choice == '3':
            result = djj.handle_app_menu("🌐 WEB TOOLS 🌍", web_tools, back_options)
            if result == 'exit':
                break
        elif choice == '4':
            result = djj.handle_app_menu("⚙️  SYSTEM UTILITIES 🖥️", system_utilities, back_options)
            if result == 'exit':
                break
        elif choice in quick_launch:
            djj.launch_app(quick_launch[choice])
            djj.wait_with_skip(3, "Continuing")
        elif choice in ['0', '00','x']:
            print("\033[93mExiting...\033[0m")
            break

# -------------------------------
# Optional helper class (from your snippet)
# -------------------------------
class PathHelper:
    def __init__(self, base_input=None):
        self.base_input = pathlib.Path(base_input) if base_input else None

    def subfolder_from_input(self, tool_name):
        output = self.base_input.parent / "Output" / tool_name
        output.mkdir(parents=True, exist_ok=True)
        return str(output.resolve())

# -------------------------------
# Main Execution
# -------------------------------
if __name__ == "__main__":
    run_app_launcher()