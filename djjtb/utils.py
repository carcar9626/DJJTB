import os
import sys
import subprocess
import logging
import pathlib
import select
import time
import json
import tempfile

def prompt_open_folder(folder_path, initial_wait=60, countdown_seconds=10):
    """
    Prompt user to open folder with countdown option
    """
    import time
    import select
    import sys
    
    while True:  # Loop until we get a valid response or timeout
        print(f"\033[33mOpen output folder?\033[0m\n1. Yes\n2. No")
        
        # Initial wait period
        ready, _, _ = select.select([sys.stdin], [], [], initial_wait)
        
        if ready:
            choice = input().strip()
            if choice == '1':
                try:
                    subprocess.run(['open', str(folder_path)], check=True)
                    print(f"\033[92m✓ Opened: {folder_path}\033[0m")
                except subprocess.CalledProcessError as e:
                    print(f"\033[33m⚠️  Error opening folder: {e}\033[0m")
                break  # Exit the loop
            elif choice == '2':
                break  # Exit without opening
            # Invalid choice - loop continues
        else:
            # Start countdown
            print(f"\033[33mNo response - continuing in {countdown_seconds} seconds (press enter to choose)...\033[0m")
            countdown_broken = False
            for i in range(countdown_seconds, 0, -1):
                print(f"{i}...", end='\r', flush=True)
                if select.select([sys.stdin], [], [], 1)[0]:
                    input()  # consume input
                    countdown_broken = True
                    break
            
            if not countdown_broken:
                # Countdown completed - exit without opening
                print("\r" + " " * 20 + "\r", end='', flush=True)
                break
            else:
                # Countdown was broken - clear line and loop back to prompt
                print("\r" + " " * 50 + "\r", end='', flush=True)
                # Loop continues to show prompt again

        
#this one is for codeformer launcher
def get_string_input(prompt, default=None):
    """Get string input with optional default value."""
    user_input = input(prompt).strip()
    if user_input:
        return user_input
    if default is not None:
        # Silently return default without warning message
        return default
    print("❌ \033[33mInput cannot be empty.\033[0m")
    return get_string_input(prompt, default)  # Retry if no default

def launch_app(app_name):
    """Launch an application using macOS 'open' command"""
    try:
        subprocess.run(["open", "-a", app_name], check=True)
        print(f"\033[92m✓ Launched {app_name}\033[0m")
        return True
    except subprocess.CalledProcessError:
        print(f"\033[33m⚠️  Could not launch {app_name} - app may not be installed\033[0m")
        return False
    except Exception as e:
        print(f"\033[33m⚠️  Error launching\033[0m {app_name}: {e}")
        return False



def make_even_dimensions(width: int, height: int) -> tuple[int, int, int, int]:
    even_width = width + (width % 2)
    even_height = height + (height % 2)
    pad_x = (even_width - width) // 2
    pad_y = (even_height - height) // 2
    return even_width, even_height, pad_x, pad_y

def get_pad_filter(width: int, height: int) -> str:
    if width % 2 == 0 and height % 2 == 0:
        return "null"
    ew, eh, px, py = make_even_dimensions(width, height)
    return f"pad={ew}:{eh}:{px}:{py}:color=black"

def get_gif_dimensions(gif_path: str) -> tuple[int, int]:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0", gif_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    width, height = map(int, result.stdout.strip().split('x'))
    return width, height

def show_app_menu(title, apps_dict, back_options=None):
    """
    Generic function to display an app menu
    
    Args:
        title: Menu title string
        apps_dict: Dictionary mapping choice numbers to app names
        back_options: Dict with back navigation options like {'0': 'Back to Categories', '00': 'Back to DJJTB'}
    """
    os.system('clear')
    print()
    print(f"\033[1;33m{title}\033[0m")
    print("\033[92m-------------------------------\033[0m")
    
    # Display apps
    for key, app_name in apps_dict.items():
        print(f"{key}. {app_name}")
    
    print()
    print("\033[92m-------------------------------\033[0m")
    
    # Display back options
    if back_options:
        for key, description in back_options.items():
            if key == '0':
                print(f" {key}. ⏪ {description}")
            elif key == '00':
                print(f"{key}. ⏮️  {description}")
    
    print("\033[92m-------------------------------\033[0m")

def handle_app_menu(title, apps_dict, back_options=None):
    """
    Generic function to handle app menu interaction
    
    Returns:
        'exit' if user wants to exit to DJJTB
        'back' if user wants to go back one level
        None to continue in current menu
    """
    while True:
        show_app_menu(title, apps_dict, back_options)
        
        all_choices = list(apps_dict.keys())
        if back_options:
            all_choices.extend(back_options.keys())
            
        choice = prompt_choice(
            "\033[33mChoose an option\033[0m",
            all_choices
        )
        
        if choice in apps_dict:
            launch_app(apps_dict[choice])
            wait_with_skip(3, "Continuing")
        elif back_options and choice in back_options:
            if choice == '00':
                os.system('clear')
                return 'exit'
            elif choice == '0':
                return 'back'
        else:
            continue

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
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33m📱 APP LAUNCHER 🚀\033[0m")
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mAPP CATEGORIES\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print("1.📱 Daily Apps 🌟")
        print("2.🔧 Tools & Utilities 🛠️")
        print("3.🌐 Web Tools 🌍")
        print("4.⚙️  System Utilities 🖥️")
        print()
        print("\033[1;33mQUICK LAUNCH\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print("5. Orion")
        print("6. VLC")
        print("7. JDownloader2")
        print("8. Photomator")
        print()
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 0|00. ⏪ Back to DJJTB")
        print("\033[92m==================================================\033[0m")
        
        choice = prompt_choice(
            "\033[33mChoose an option: \033[0m",
            ['1', '2', '3', '4', '5', '6', '7', '8', '0', '00']
        )
        
        if choice == '1':
            result = handle_app_menu("📱 DAILY APPS 🌟", daily_apps, back_options)
            if result == 'exit':
                break
        elif choice == '2':
            result = handle_app_menu("🔧 TOOLS & UTILITIES 🛠️", tools_utilities, back_options)
            if result == 'exit':
                break
        elif choice == '3':
            result = handle_app_menu("🌐 WEB TOOLS 🌍", web_tools, back_options)
            if result == 'exit':
                break
        elif choice == '4':
            result = handle_app_menu("⚙️  SYSTEM UTILITIES 🖥️", system_utilities, back_options)
            if result == 'exit':
                break
        elif choice in quick_launch:
            launch_app(quick_launch[choice])
            wait_with_skip(3, "Continuing")
        elif choice in ['0', '00']:
            os.system('clear')
            return_to_djjtb()
            break
    def __init__(self, base_input=None):
        self.base_input = pathlib.Path(base_input) if base_input else None

    def subfolder_from_input(self, tool_name):
        output = self.base_input.parent / "Output" / tool_name
        output.mkdir(parents=True, exist_ok=True)
        return str(output.resolve())

class PathManager:
    """Centralized path management for DJJTB scripts"""
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.path_file = os.path.join(self.temp_dir, "djjtb_paths.json")
        self.session_data = {}
    
    def save_paths(self, script_name, paths, additional_data=None):
        """Save paths and additional data for a script"""
        try:
            # Load existing data
            if os.path.exists(self.path_file):
                with open(self.path_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {}
            
            # Update with new data
            script_data = {
                'paths': paths,
                'timestamp': time.time()
            }
            
            if additional_data:
                script_data.update(additional_data)
            
            data[script_name] = script_data
            
            # Save back to file
            with open(self.path_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving paths: {e}")
            return False
    
    def load_paths(self, script_name):
        """Load paths for a script"""
        try:
            if os.path.exists(self.path_file):
                with open(self.path_file, 'r') as f:
                    data = json.load(f)
                    return data.get(script_name, {})
            return {}
        except Exception as e:
            print(f"\033[33mError loading paths: {e}\033[0m")
            return {}
    
    def cleanup(self):
        """Clean up temporary path file"""
        try:
            if os.path.exists(self.path_file):
                os.remove(self.path_file)
        except Exception:
            pass

# Global path manager instance
path_manager = PathManager()

def get_centralized_media_input(script_name, prompt_text="📁 Select media files/folders", extensions=('.mp4', '.mkv', '.webm', '.mov')):
    """
    Centralized media input handler that can be called from any script
    Returns both the paths and saves them for the calling script
    """
    print(f"\033[92m=== {script_name.upper()} - MEDIA INPUT ===\033[0m")
    
    input_mode = prompt_choice(
        "\033[33m How do you want to select media?\033[0m\n1. Single folder (all media files)\n2. Multiple files/folders (space-separated)\n3. Single file\n",
        ['1', '2', '3'],
        default='2'
    )
    
    media_files = []
    
    if input_mode == '1':
        # Single folder - get all media files
        folder_path = get_path_input("Enter folder path")
        media_files = collect_media_files(folder_path, extensions)
        
    elif input_mode == '2':
        # Multiple files/folders
        print(f"\033[33m {prompt_text} (space-separated paths):\033[0m")
        paths_input = input(" > ").strip()
        if paths_input:
            for path_str in paths_input.split():
                path_str = path_str.strip('\'"')
                try:
                    path = pathlib.Path(path_str).expanduser().resolve()
                    if path.exists():
                        if path.is_file() and path.suffix.lower() in extensions:
                            media_files.append(str(path))
                        elif path.is_dir():
                            media_files.extend(collect_media_files(path, extensions))
                    else:
                        print(f"\033[33m Warning: Path '{path}' does not exist.\033[0m")
                except Exception as e:
                    print(f"\033[33m Error resolving path '{path_str}': {e}\033[0m")
    
    elif input_mode == '3':
        # Single file
        file_path = get_path_input("Enter file path")
        path = pathlib.Path(file_path)
        if path.suffix.lower() in extensions:
            media_files = [str(path)]
        else:
            print(f"\033[33m Warning: File doesn't have a supported extension.\033[0m")
            media_files = [str(path)]  # Include anyway, let the script decide
    
    if not media_files:
        print("\033[33m No valid media files found!\033[0m")
        return []
    
    print(f"\033[92m✓ Found {len(media_files)} media file(s)\033[0m")
    for i, file in enumerate(media_files[:5]):  # Show first 5
        print(f"  {i+1}. {os.path.basename(file)}")
    if len(media_files) > 5:
        print(f"  ... and {len(media_files) - 5} more")
    
    # Save paths for the script
    path_manager.save_paths(script_name, media_files, {
        'input_mode': input_mode,
        'extensions': extensions
    })
    
    return media_files

def get_centralized_output_path(script_name, default_name="output"):
    """
    Centralized output path handler
    Returns output directory path and saves it for the calling script
    """
    print(f"\033[92m=== {script_name.upper()} - OUTPUT LOCATION ===\033[0m")
    
    output_mode = prompt_choice(
        "\033[33m Where should output files be saved?\033[0m\n1. Desktop\n2. Same folder as input files\n3. Custom folder\n",
        ['1', '2', '3'],
        default='1'
    )
    
    if output_mode == '1':
        # Desktop
        output_path = os.path.expanduser("~/Desktop")
        
    elif output_mode == '2':
        # Same as input - get first input file's directory
        script_data = path_manager.load_paths(script_name)
        if script_data and script_data.get('paths'):
            first_file = script_data['paths'][0]
            output_path = os.path.dirname(first_file)
        else:
            print("\033[33m No input paths found, defaulting to Desktop\033[0m")
            output_path = os.path.expanduser("~/Desktop")
            
    elif output_mode == '3':
        # Custom folder
        output_path = get_path_input("Enter output folder path")
    
    # Create subfolder with script name and timestamp
    import time
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    subfolder_name = f"{script_name}_{timestamp}"
    final_output_path = os.path.join(output_path, subfolder_name)
    
    try:
        os.makedirs(final_output_path, exist_ok=True)
        print(f"\033[92m✓ Output folder created: {final_output_path}\033[0m")
    except Exception as e:
        print(f"\033[33m Error creating output folder: {e}\033[0m")
        # Fallback to desktop
        final_output_path = os.path.join(os.path.expanduser("~/Desktop"), subfolder_name)
        os.makedirs(final_output_path, exist_ok=True)
    
    # Save output path for the script
    script_data = path_manager.load_paths(script_name)
    if script_data:
        script_data['output_path'] = final_output_path
        path_manager.save_paths(script_name, script_data.get('paths', []), script_data)
    
    return final_output_path

def wait_with_skip(seconds=8, message="Returning to previous menu"):
    """Wait with option to skip by pressing any key"""
    print(f"\n\033[33m{message} in {seconds} seconds... (press any key to skip)\033[0m")
    
    for i in range(seconds, 0, -1):
        print(f"{i}...", end='\r', flush=True)
        
        # Check for input (non-blocking)
        if select.select([sys.stdin], [], [], 1)[0]:
            sys.stdin.read(1)  # consume the input
            break
        
    os.system('clear')

def setup_terminal(bounds="630, 200, 1110, 760", profile="djjtb"):
    """Setup terminal window bounds and profile"""
    try:
        subprocess.run([
            "osascript", "-e",
            f'tell application "Terminal" to set bounds of front window to {{{bounds}}}'
        ], stderr=subprocess.DEVNULL)
        
        subprocess.run([
            "osascript", "-e",
            f'tell application "Terminal" to set current settings of front window to settings set "{profile}"'
        ], stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"\033[33mError setting terminal window: {e}\033[0m")

def cleanup_tabs():
    """Close extra terminal tabs"""
    print("\033[33mClosing extra tabs...\033[0m")
    applescript = '''
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
    end tell
    '''
    subprocess.run(["osascript", "-e", applescript], stderr=subprocess.DEVNULL)

def run_script_in_tab(module_path, venv_path="~/Documents/Scripts/DJJTB/venv/bin/activate", project_path="/Users/home/Documents/Scripts/DJJTB"):
    """Run a Python script in a new terminal tab"""
    applescript = f'''
    tell application "Terminal"
        tell application "System Events" to keystroke "t" using command down
        delay 0.2
        do script "source {venv_path}; cd {project_path}; python3 -m {module_path}" in selected tab of the front window
    end tell
    '''
    subprocess.run(["osascript", "-e", applescript])

def run_command_in_tab(command):
    """Run a custom command in a new terminal tab"""
    applescript = f'''
    tell application "Terminal"
        tell application "System Events" to keystroke "t" using command down
        delay 0.2
        do script "{command}" in selected tab of the front window
    end tell
    '''
    subprocess.run(["osascript", "-e", applescript])

def open_app(app_path):
    """Open an application"""
    subprocess.run(["open", app_path])

def switch_to_terminal_tab(tab_number):
    """Switch to specific terminal tab (Command+number)"""
    subprocess.run([
        "osascript", "-e",
        f'tell application "Terminal" to tell application "System Events" to keystroke "{tab_number}" using command down'
    ])

def open_terminal_with_settings(command, profile="LinkGrabber", bounds="50, 282, 250, 482"):
    """Open a new terminal window with specific settings and command"""
    applescript = f'''
    tell application "Terminal"
        activate
        set newWindow to (do script "")
        set current settings of front window to settings set "{profile}"
        do script "{command}" in selected tab of the front window
        delay 0.2
        set bounds of front window to {{{bounds}}}
    end tell
    '''
    subprocess.run(["osascript", "-e", applescript])

def get_media_input(prompt_text="📁 Enter path", extensions=('.mp4', '.mkv', '.webm', '.mov')):
    """Universal media input handler with mode selection"""
    input_mode = prompt_choice(
        "\033[33mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
        ['1', '2'],
        default='2'
    )
    
    if input_mode == '1':
        # Single folder path
        path = get_path_input(prompt_text)
        return collect_media_files(path)
    else:
        # Multiple file paths
        print(f"\033[33m {prompt_text} (space-separated):\033[0m")
        paths_input = input(" > ").strip()
        if not paths_input:
            return []
        
        media_files = []
        for path_str in paths_input.split():
            path_str = path_str.strip('\'"')
            try:
                path = pathlib.Path(path_str).expanduser().resolve()
                if path.exists():
                    if path.is_file() and path.suffix.lower() in extensions:
                        media_files.append(str(path))
                    elif path.is_dir():
                        media_files.extend(collect_media_files(path))
                else:
                    print(f"\033[33m Warning: Path '{path}' does not exist.\033[0m")
            except Exception as e:
                print(f"\033[33m Error resolving path '{path_str}': {e}\033[0m")
        
        return media_files

def collect_media_files(input_path):
    """Helper function for get_media_input - collects media files from a directory"""
    input_path = pathlib.Path(input_path)
    extensions = ('.mp4', '.mov', '.webm', '.mkv', '.mp3', '.aac', '.flac', '.wav', '.m4a')
    
    if input_path.is_file():
        return [str(input_path)] if input_path.suffix.lower() in extensions else []
    elif input_path.is_dir():
        media_files = []
        for root, _, files in os.walk(input_path):
            for file in sorted(files):
                if file.lower().endswith(extensions):
                    media_files.append(os.path.join(root, file))
        return media_files
    return []

def get_video_input(prompt_text="📁 Enter path", extensions=('.mp4', '.mkv', '.webm', '.mov')):
    """Universal video input handler with mode selection"""
    input_mode = prompt_choice(
        "\033[33m Input mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
        ['1', '2'],
        default='1'
    )
    

def get_path_input(prompt, max_attempts=5):
    """Prompt user to enter a valid existing file or directory path."""
    attempt = 0
    while attempt < max_attempts:
        path_input = input(f"\033[33m {prompt}:\n >\033[0m ").strip().strip('\'"')
        try:
            path = pathlib.Path(path_input).expanduser().resolve()
            if path.exists():
                return str(path)
            else:
                print(f"\033[33m Error: Path '{path}' does not exist.\033[0m", file=sys.stderr)
        except Exception as e:
            print(f"\033[33m Error resolving path: {e}\033[0m", file=sys.stderr)
        attempt += 1
    print("\033[33m Too many invalid attempts. Exiting.\033[0m", file=sys.stderr)
    sys.exit(1)

def get_int_input(prompt, min_val=None, max_val=None, max_attempts=5):
    """Prompt user for an integer input, optionally with min and max constraints."""
    attempt = 0
    while attempt < max_attempts:
        val_str = input(f"\033[33m{prompt}\033[0m:\n > ").strip()
        try:
            val = int(val_str)
            if min_val is not None and val < min_val:
                print(f"Value must be >= {min_val}.", file=sys.stderr)
                attempt += 1
                continue
            if max_val is not None and val > max_val:
                print(f"\033[33mValue must be <=\033[0m {max_val}.", file=sys.stderr)
                attempt += 1
                continue
            return val
        except ValueError:
            print("\033[33mPlease enter a valid integer.\033[0m", file=sys.stderr)
        attempt += 1
    print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
    sys.exit(1)

def get_float_input(prompt, min_val=None, max_val=None, max_attempts=5):
    """Prompt user for a float input, optionally with min and max constraints."""
    attempt = 0
    while attempt < max_attempts:
        val_str = input(f"\033[33m{prompt}\033[0m").strip()
        try:
            val = float(val_str)
            if min_val is not None and val < min_val:
                print(f"\033[33mValue must be >=\033[0m {min_val}.", file=sys.stderr)
                attempt += 1
                continue
            if max_val is not None and val > max_val:
                print(f"\033[33mValue must be <= \033[0m{max_val}.", file=sys.stderr)
                attempt += 1
                continue
            return val
        except ValueError:
            print("\033[33mPlease enter a valid number.\033[0m", file=sys.stderr)
        attempt += 1
    print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
    sys.exit(1)

def setup_logging(output_path, script_name="script"):
    """Set up a clean logger for the given script."""
    log_file = os.path.join(output_path, f"{script_name}_log.txt")
    logger = logging.getLogger(f'djjtb.{script_name}')
    logger.setLevel(logging.INFO)
    logger.handlers = []  # Clear any existing handlers
    logger.propagate = False  # Prevent root logger interference
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

def prompt_choice(prompt, choices, default=None):
    """Prompt user for input with validation and default value."""
    while True:
        display_prompt = f"{prompt} [default: {default}]: " if default else f"\033[33m{prompt}:\033[0m "
        user_input = input(display_prompt).strip()
        if user_input == '' and default:
            return default
        if user_input in choices:
            return user_input
        print(f"\033[33m Please enter one of: {', '.join(choices)}\033[0m", file=sys.stderr)
        
def return_to_djjtb():
#Keystroke Cmd+1 in front Terminal Window
    """Switch back to DJJTB tab (Command+1)"""
    subprocess.run([
        "osascript", "-e",
        'tell application "Terminal" to tell application "System Events" to keystroke "1" using command down'
    ])
    
def what_next():
    """Handle the 'What Next?' prompt and return action to take"""
    print()
    print("---------------")
    print()
    again = prompt_choice("\033[33mWhat Next? 🤷🏻‍♂️ \033[0m\n1. Go Again 🔁\n2. Return to DJJTB ⏮️\n3. Exit ✋🏼\n> ", ['1', '2', '3'], default='2')
    
    if again == '3':
        print("👋 Exiting.")
        return 'exit'
    elif again == '2':
        return_to_djjtb()
        return 'exit'
    else:  # again == '1'
        os.system('clear')
        return 'continue'

def get_audio_options(audio_choice):
    """Get FFmpeg audio options based on user choice."""
    if audio_choice == '1':  # Keep Original Audio
        return ["-c:a", "aac"]
    elif audio_choice == '2':  # Strip Audio
        return ["-an"]
    elif audio_choice == '3':  # Add Silent Audio Track
        return ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000", "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-shortest"]
    else:
        return ["-c:a", "aac"]  # Default to keep original

def run_again():
    choice = prompt_choice("\033[33m Run again?\033[0m\n1. Yes, 2. No ", ['1', '2'], default='2')
    if choice == '2':
        print("👋 Exiting.")
        return False
    os.system('clear')
    return True