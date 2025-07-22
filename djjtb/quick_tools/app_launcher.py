import os
import subprocess
import sys
import djjtb.utils as djj

def launch_app(app_name):
    """Launch an application using macOS 'open' command"""
    try:
        subprocess.run(["open", "-a", app_name], check=True)
        print(f"\033[92m✓ Launched {app_name}\033[0m")
    except subprocess.CalledProcessError:
        print(f"\033[33m⚠️  Could not launch {app_name} - app may not be installed\033[0m")
    except Exception as e:
        print(f"\033[33m⚠️  Error launching {app_name}: {e}\033[0m")

def daily_apps_menu():
    """Daily Apps submenu"""
    while True:
        os.system('clear')
        print()
        print("\033[1;33m📱 DAILY APPS 🌟\033[0m")
        print("\033[92m-------------------------------\033[0m")
        print("1. Telegram")
        print("2. Orion")
        print("3. JDownloader2")
        print("4. CotEditor")
        print("5. ChatGPT")
        print("6. Grok")
        print("7. IINA")
        print()
        print("\033[92m-------------------------------\033[0m")
        print(" 0. ⏪ Back to App Categories")
        print("00. ⏮️  Back to DJJTB")
        print("\033[92m-------------------------------\033[0m")
        
        choice = djj.prompt_choice(
            "\033[33mChoose app\033[0m",
            ['1', '2', '3', '4', '5', '6', '7', '0', '00']
        )
        
        app_map = {
            '1': 'Telegram Lite',
            '2': 'Orion',
            '3': 'JDownloader2',
            '4': 'CotEditor',
            '5': 'ChatGPT',
            '6': 'Grok',
            '7': 'VLC'
        }
        
        if choice in app_map:
            launch_app(app_map[choice])
            djj.wait_with_skip(3, "Continuing")
        elif choice == '0':
            break
        elif choice == '00':
            os.system('clear')
            return 'exit'

def tools_utilities_menu():
    """Tools & Utilities submenu"""
    while True:
        os.system('clear')
        print()
        print("\033[1;33m🔧 TOOLS & UTILITIES 🛠️\033[0m")
        print("\033[92m-------------------------------\033[0m")
        print("1. A Better Finder Rename 12")
        print("2. dupeguru")
        print("3. Keka")
        print("4. BetterZip")
        print("5. Gray")
        print()
        print("\033[92m-------------------------------\033[0m")
        print(" 0. ⏪ Back to App Categories")
        print("00. ⏮️  Back to DJJTB")
        print("\033[92m-------------------------------\033[0m")
        
        choice = djj.prompt_choice(
            "\033[33mChoose a tool\033[0m",
            ['1', '2', '3', '4', '5', '0', '00']
        )
        
        app_map = {
            '1': 'A Better Finder Rename 12',
            '2': 'dupeguru',
            '3': 'Keka',
            '4': 'BetterZip',
            '5': 'Gray'
        }
        
        if choice in app_map:
            launch_app(app_map[choice])
            djj.wait_with_skip(3, "Continuing")
        elif choice == '0':
            break
        elif choice == '00':
            os.system('clear')
            return 'exit'

def web_tools_menu():
    """Web Tools submenu"""
    while True:
        os.system('clear')
        print()
        print("\033[1;33m🌐 WEB TOOLS 🌍\033[0m")
        print("\033[92m-------------------------------\033[0m")
        print("1. NordVPN")
        print("2. Transmit")
        print("3. Motrix")
        print("4. Thunder (迅雷)")
        print("5. BaiduNetdisk")
        print()
        print("\033[92m-------------------------------\033[0m")
        print(" 0. ⏪ Back to App Categories")
        print("00. ⏮️  Back to DJJTB")
        print("\033[92m-------------------------------\033[0m")
        
        choice = djj.prompt_choice(
            "\033[33mChoose a tool\033[0m",
            ['1', '2', '3', '4', '5', '0', '00']
        )
        
        app_map = {
            '1': 'NordVPN',
            '2': 'Transmit',
            '3': 'Motrix',
            '4': '迅雷',
            '5': 'BaiduNetdisk'
        }
        
        if choice in app_map:
            launch_app(app_map[choice])
            djj.wait_with_skip(3, "Continuing")
        elif choice == '0':
            break
        elif choice == '00':
            os.system('clear')
            return 'exit'

def system_utilities_menu():
    """System Utilities submenu"""
    while True:
        os.system('clear')
        print()
        print("\033[1;33m⚙️  SYSTEM UTILITIES 🖥️\033[0m")
        print("\033[92m-------------------------------\033[0m")
        print("1. System Settings")
        print("2. Disk Utility")
        print("3. Activity Monitor")
        print("4. Automator")
        print("5. NordPass")
        print("6. DriveDx")
        print("7. Logitech Options+")
        print()
        print("\033[92m-------------------------------\033[0m")
        print(" 0. ⏪ Back to App Categories")
        print("00. ⏮️  Back to DJJTB")
        print("\033[92m-------------------------------\033[0m")
        
        choice = djj.prompt_choice(
            "\033[33mChoose a system utility\033[0m",
            ['1', '2', '3', '4', '5', '6', '7', '0', '00']
        )
        
        app_map = {
            '1': 'System Settings',
            '2': 'Disk Utility',
            '3': 'Activity Monitor',
            '4': 'Automator',
            '5': 'NordPass',
            '6': 'DriveDx',
            '7': 'Logi Options+'
        }
        
        if choice in app_map:
            launch_app(app_map[choice])
            djj.wait_with_skip(3, "Continuing")
        elif choice == '0':
            break
        elif choice == '00':
            os.system('clear')
            return 'exit'

def app_launcher_main():
    """Main app launcher function"""
    while True:
        os.system('clear')
        print()
        print("\033[92m===================================\033[0m")
        print("        \033[1;33m📱 APP LAUNCHER 🚀\033[0m")
        print("\033[92m===================================\033[0m")
        print("\033[1;33mAPP CATEGORIES\033[0m")
        print("\033[92m-----------------------------------\033[0m")
        print("1.📱 Daily Apps 🌟")
        print("2.🔧 Tools & Utilities 🛠️")
        print("3.🌐 Web Tools 🌍")
        print("4.⚙️  System Utilities 🖥️")
        print()
        print("\033[1;33mQUICK LAUNCH\033[0m")
        print("\033[92m-----------------------------------\033[0m")
        print("5. Orion")
        print("6. VLC")
        print("7. JDownloader2")
        print("8. Photomator")
        print()
        print("\033[92m-----------------------------------\033[0m")
        print(" 0|00. ⏪ Back to DJJTB")
        print("\033[92m===================================\033[0m")
        
        choice = djj.prompt_choice(
            "\033[33mChoose an option\033[0m",
            ['1', '2', '3', '4', '5', '6', '7', '8', '0', '00']
        )
        
        if choice == '1':
            result = daily_apps_menu()
            if result == 'exit':
                break
        elif choice == '2':
            result = tools_utilities_menu()
            if result == 'exit':
                break
        elif choice == '3':
            result = web_tools_menu()
            if result == 'exit':
                break
        elif choice == '4':
            result = system_utilities_menu()
            if result == 'exit':
                break
        elif choice == '5':
            launch_app("Orion")
            djj.wait_with_skip(3, "Continuing")
        elif choice == '6':
            launch_app("VLC")
            djj.wait_with_skip(3, "Continuing")
        elif choice == '7':
            launch_app("JDownloader2")
            djj.wait_with_skip(3, "Continuing")
        elif choice == '8':
            launch_app("Photomator")
            djj.wait_with_skip(3, "Continuing")
        elif choice in ['0', '00']:
            os.system('clear')
            djj.return_to_djjtb()
            break

if __name__ == "__main__":
    # Set up terminal if needed
