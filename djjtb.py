#!/usr/bin/env python3
"""
DJJTB Python Launcher

"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))
import djjtb.utils as djj

# ── Boot-launch detection ─────────────────────────────────────────────────────
# Stamp file records the last time djjtb launched the grabbers.
# If the Mac booted after that stamp, it's a fresh boot → launch grabbers.
GRABBER_STAMP = Path("/Users/home/Documents/Scripts/DJJTB_output/grabber_last_launch.txt")

def get_boot_time():
    """Return system boot time as a Unix timestamp."""
    try:
        result = subprocess.run(
            ["sysctl", "-n", "kern.boottime"],
            capture_output=True, text=True
        )
        # Output looks like: { sec = 1234567890, usec = 0 } ...
        for part in result.stdout.split(","):
            if "sec" in part:
                return float(part.split("=")[1].strip().split()[0])
    except Exception:
        pass
    return 0.0

def is_boot_launch():
    """Return True if this is the first djjtb launch since last boot."""
    boot_time = get_boot_time()
    if not boot_time:
        return False  # Can't determine — play it safe, skip auto-launch

    if not GRABBER_STAMP.exists():
        return True  # Never launched before → treat as boot launch

    try:
        last_launch = float(GRABBER_STAMP.read_text().strip())
        # Boot happened AFTER our last stamp → fresh boot
        return boot_time > last_launch
    except Exception:
        return True  # Corrupt stamp → treat as boot launch

def write_grabber_stamp():
    """Record current time as the last grabber launch time."""
    try:
        GRABBER_STAMP.parent.mkdir(parents=True, exist_ok=True)
        GRABBER_STAMP.write_text(str(time.time()))
    except Exception:
        pass

class DJJTBLauncher:

    def __init__(self):
        self.venv_path = "~/Documents/Scripts/DJJTB/venv/bin/activate"
        self.project_path = "/Users/home/Documents/Scripts/DJJTB"

    def show_main_menu(self):
        """Display main menu"""
        os.system('clear')
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93m 🧰 🧲 🎞️  🤖 🩷⬌💓 DJJ TOOLBOX 💻 🔗 😶‍🌫️➡︎😝 🦙 🧼\033[0m")
        print("\033[92m==================================================\033[0m")
        print("\033[1;93m MAIN MENU\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        #
        print(" 💰 \033[4;93m1\033[0m  MEDIA TOOLS 🎞️ 🎑 ")
        #
        print(" 💰 \033[4;93m2\033[0m  AI TOOLS 🤖🦾")
        #
        print(" 💰 \033[4;93m3\033[0m  FILE TOOLS 🗄️ 🗂️   ")
        #
        print(" 💰 \033[4;93mA\033[0m  APP LAUNCHER 📱🚀")
        print()
        print("\033[1;93m QUICK TOOLS\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        #
        print(" 💰 \033[4;93m4\033[0m  Reverse Image Search 🌠🔎")
        #
        print(" 💰 \033[4;93m5\033[0m  Link Grabber 🔗✊🏼")
        #🚏✊🏼
        print(" 💰 \033[4;93m6\033[0m  Path Grabber 🚏✊🏼")
        #
        print(" 💰 \033[4;93m7\033[0m  Multi XMP Viewer 🔢👀")
        #
        print(" 💰 \033[4;93m8\033[0m  Media Info Viewer 📺ℹ️")
        #
        print(" 💰 \033[4;93m9\033[0m  Auto Scroller ⚙️ ⏬")
        #
        print(" 💰\033[4;93m10\033[0m  Link Scraper 🔗🪏")
        print(" 💰\033[4;93m11\033[0m  Mount Movies 4 & 8 💽")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰\033[4;91mX\033[0m  Exit 👋🏻✈️         💰\033[4;91mAD\033[0m  ADMIN TOOLS 🔐")
        print("\033[92m==================================================\033[0m")
    
    def show_media_tools_menu(self):
        """Display media tools menu"""
        os.system('clear')
        print()
        print()
        print("\033[1;93m🎇 MEDIA TOOLS 📽️\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰 \033[4;93m1\033[0m  VIDEOS 📺")
        print(" 💰 \033[4;93m2\033[0m  IMAGES 📸")
        print(" 💰 \033[4;93m3\033[0m  Media Sorter 🔢")
        print(" 💰 \033[4;93m4\033[0m  Metadata Stripper + Identifier 🔖 🔪")
        print(" 💰 \033[4;93m5\033[0m  Playlist Generator 📋 🍿")
        print(" 💰 \033[4;93m6\033[0m  Media Info Extractor 📼 🌅 ℹ️")
        print()
        print("\033[1;93m📱 APPS 💻\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰 \033[4;93mP\033[0m  Photomator")
        print(" 💰\033[4;93mPX\033[0m  Pixelmator")
        print(" 💰 \033[4;93mD\033[0m  DaVinci Resolve")
        print(" 💰 \033[4;93mW\033[0m  Wondershare Uniconverter")
        print(" 💰 \033[4;93mH\033[0m  Handbrake")
        print(" 💰 \033[4;93mC\033[0m  CollageIt 3")
        print(" 💰\033[4;93mFM\033[0m  Filmora (Parallels)")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰 \033[4;93m0\033[0m  ⏪ Back")
        print(" 💰\033[4;93m00\033[0m ⏮️  MAIN MENU")
        print("\033[92m--------------------------------------------------\033[0m")
    
    def show_video_tools_menu(self):
        """Display video tools menu"""
        os.system('clear')
        print()
        print()
        print("\033[1;93m🎬 VIDEO TOOLS 🎬\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰 \033[4;93m1\033[0m  Video Re-encoder 📼➡︎📀")
        print(" 💰 \033[4;93m2\033[0m  Reverse Merge ↪️ ⇔↩️")
        print(" 💰 \033[4;93m3\033[0m  Slideshow Watermark 📹 🆔")
        print(" 💰 \033[4;93m4\033[0m  Video Cropper 👖➡︎🩳")
        print(" 💰 \033[4;93m5\033[0m  Group Merger 📹 🧲")
        print(" 💰 \033[4;93m6\033[0m  Video Splitter 📹 ✂️  ⏱️")
        print(" 💰 \033[4;93m7\033[0m  Speed Changer 🐇⬌🐢")
        print(" 💰 \033[4;93m8\033[0m  Frame Extractor 📹➡︎🌃🌆🎆🎇")
        print(" 💰 \033[4;93m9\033[0m  GIFs Converter 📹⬌🌃🌆🎆🎇")
        print()
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰 \033[4;93m0\033[0m  ⏪ Back to MEDIA TOOLS")
        print(" 💰\033[4;93m00\033[0m ⏮️  MAIN MENU")
        print("\033[92m--------------------------------------------------\033[0m")
    
    def show_image_tools_menu(self):
        """Display image tools menu"""
        os.system('clear')
        print()
        print()
        print("\033[1;93m🖼️  IMAGES TOOLS 🖼️\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰 \033[4;93m1\033[0m  Image Processor 🩷⬌💓 ↔️🔄 ✋🏼🤲🏼")
        print(" 💰 \033[4;93m2\033[0m  Collage Creation 🧩 🎇")
        print(" 💰 \033[4;93m3\033[0m  Slideshow Maker 🎑➡︎📽️")
        print(" 💰 \033[4;93m4\033[0m  Webp to MP4 Converter 👾➡︎📹")
        print(" 💰 \033[4;93m5\033[0m  Images to Video Compiler 🌃🌆🎆🎇➡︎📹")
        print()
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰 \033[4;93m0\033[0m  ⏪ Back to MEDIA TOOLS")
        print(" 💰\033[4;93m00\033[0m  ⏮️  MAIN MENU")
        print("\033[92m--------------------------------------------------\033[0m")
    
    def show_ai_tools_menu(self):
        """Display AI tools menu"""
        os.system('clear')
        print()
        print("\033[1;93m 🤖 AI TOOLS 🛠️\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        #print(" 1. Prompt Randomizer 📝 🔀")
        #print(" 2. ComfyUI ☀️ 💻")
        #print(" 3. Merge Loras 👫➡︎🧍🏼‍♂️")
        print(" 💰 \033[4;93m1\033[0m  Codeformer 😶‍🌫️➡︎😝")
        print(" 💰 \033[4;93m2\033[0m  JoyTag Tagger (AI) 🏷️")
        print(" 💰 \033[4;93m3\033[0m  Image Tagger (AI) 🔖")
        print(" 💰 \033[4;93m4\033[0m  FaceFusion (NSFW Patched) 👿➡︎😇")
        print(" 💰 \033[4;93m5\033[0m  FaceFusion WebUI 🌐 👿➡︎😇")
        print(" 💰 \033[4;93m6\033[0m  JoyCaption (AI) 🏷️")
        print(" 💰\033[4;93m6a\033[0m  JoyCaption Ollama (AI) 🏷️")
        print(" 💰 \033[4;93m7\033[0m  Image Upscaler (4x_UltraSharp 💓 💗 🩷")
        print(" 💰\033[4;93m7a\033[0m  Codeformer x 4x_UltraSharp 💓 💗 🩷")
        # print(" 💰 \033[4;93m6\033[0m  WM Remover Auto-Detect(AI) 🤖 💋 🧼")
        # print(" 💰 \033[4;93m7\033[0m  WM Remover from Reference (AI) 👷🏻‍♂️ 💋 🧼")
        print(" 💰 \033[4;93m8\033[0m  IOPaint - lama cleaner (WebUI) 🦙 🧼")
#        print(" 💰\033[4;93m9\033[0m  Image Upscaler (Real-Esrgan4x) 💓 💗 🩷")
#        print("💰\033[4;93m10\033[0m  Image Upscaler (RealSR 4x) 👶🏼 👦🏻 🤦🏽‍♂️")
        print(" 💰 \033[4;93m9\033[0m  Image Finder (AI) 🔎")
        print(" 💰\033[4;93m10\033[0m  Image Caption Generator (AI)(Florence) 🩻📜")
        # print(" 💰\033[4;93m11\033[0m  Kohya_SS (AI)(SD Lora Trainer) 🏋🏻")
        print(" 💰\033[4;93m11\033[0m  Prompt Assembler 📝")
        print(" 💰\033[4;93m12\033[0m  Comfyui Batch Process ▶️")
        print(" 💰\033[4;93m13\033[0m  OpenCode (Local AI Agent) 🖥️🤖")
        print(" 💰\033[4;93m14\033[0m  Open WebUI 🌐🧠")
        print(" 💰\033[4;93m15\033[0m  Vocab + Mask Generator 🔤")
        print(" 💰\033[4;93m16\033[0m  Category Sorter (AI)(CLIP) 🗂️")
        print()
        print("\033[1;93m ⛓️  chaiNNer Workflows ⚙️\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰\033[4;93mC0\033[0m  Face Restore + Upscale")
        print(" 💰\033[4;93mC1\033[0m  Upscale + Face Restore")
        print(" 💰\033[4;93mC2\033[0m  Upscale Only")
        print(" 💰\033[4;93mC3\033[0m  Face Restore Only")
        # print(" 💰\033[4;93mC4\033[0m  Batch Crop")
        print(" 💰\033[4;93mC5\033[0m  Batch Resize")
        # print(" 💰\033[4;93mC6\033[0m  Watermark Removal with OpenCV")
        print(" 💰\033[4;93mC7\033[0m  Stack Only")
        # print(" 💰\033[4;93mC8\033[0m  Batch Background Removal")
        print()
        print("\033[1;93m ⚙️  ➡️  ⤵️  🔀 🔁 🔄 🔃 ↔️  ⚙️\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰 \033[4;93mCU\033[0m  ComfyUI")
        print(" 💰 \033[4;93mCH\033[0m  chaiNNer")
        print(" 💰\033[4;93mATK\033[0m  AI-TOOLKIT")
        print(" 💰 \033[4;93mCJ\033[0m  Prompt Lib CSV to JSON")
        print(" 💰 \033[4;93mJC\033[0m  Prompt Lib JSON to CSV")
        
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰 \033[4;93m0\033[0m  ⏪ Back")
        print(" 💰\033[4;93m00\033[0m  ⏮️  MAIN MENU")
        print("\033[92m--------------------------------------------------\033[0m")
    
    def show_file_tools_menu(self):
        """Display file tools menu"""
        os.system('clear')
        print()
        print("📁 FILE TOOLS 🗂️")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰 \033[4;93m1\033[0m  Rsync Helper 👯‍♀️")
        print(" 💰 \033[4;93m2\033[0m  Add Root Folder Prefix 🗂️")
        print(" 💰 \033[4;93m3\033[0m  Auto Subfolder by Filename 🗃️")
        print(" 💰 \033[4;93m4\033[0m  Filename Randomizer 📇 🔀")
        print(" 💰 \033[4;93m5\033[0m  File Identifier 🆔")
        print(" 💰 \033[4;93m6\033[0m  README Generator 📖")
        print(" 💰 \033[4;93m7\033[0m  X-to-W Folder Broadcaster 📤➡️📁")
        print(" 💰 \033[4;93m8\033[0m  Add Pose Prompts 🤸📝")
        print()
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰 \033[4;93m0\033[0m  ⏪ Back")
        print(" 💰\033[4;93m00\033[0m ⏮️  MAIN MENU")
        print("\033[92m--------------------------------------------------\033[0m")

    def show_admin_tools_menu(self):
        """Display Admin Tools menu (password-protected)"""
        os.system('clear')
        print()
        print("\033[91m🔐 ADMIN TOOLS 🔐\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰 \033[4;93m1\033[0m  DJJTB Usage Scan 🔍")
        print(" 💰 \033[4;93m2\033[0m  Env Backup 💾")
        print(" 💰 \033[4;93m3\033[0m  Push to GitHub 🐙")
        print(" 💰 \033[4;93m4\033[0m  List Open Ports 🌐")
        print(" 💰 \033[4;93m5\033[0m  Diskutil List 💽")
        print(" 💰 \033[4;93m6\033[0m  Command Help ❓")
        print(" 💰 \033[4;93m7\033[0m  VLC Screenshot Renamer 📸")
        print(" 💰 \033[4;93m8\033[0m  Mount Movies 4 & 8 💽")
        print(" 💰\033[4;93m8a\033[0m  Unmount Movies 4 & 8 ⏏️")
        print(" 💰 \033[4;93m9\033[0m  Stop ComfyUI 🛑")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰 \033[4;93m0\033[0m  ⏪ Back")
        print(" 💰\033[4;93m00\033[0m ⏮️  MAIN MENU")
        print("\033[92m--------------------------------------------------\033[0m")

    def handle_video_tools(self):
        """Handle video tools submenu"""
        first_entry = True
        
        while True:
            if not first_entry:
                djj.wait_with_skip(8, "Back to Media Tools")
            self.show_video_tools_menu()
            
            choice = djj.prompt_choice("\033[93mChoose a Tool\033[0m" if first_entry else "\033[93mChoose another option\033[0m",
                                     ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '0', '00'])
            first_entry = False
            
            if choice == "1":
                djj.run_script_in_tab("djjtb.media_tools.video_tools.video_re-encoder", self.venv_path, self.project_path)
            elif choice == "2":
                djj.run_script_in_tab("djjtb.media_tools.video_tools.video_reverse_merge", self.venv_path, self.project_path)
            elif choice == "3":
                djj.run_script_in_tab("djjtb.media_tools.video_tools.video_slideshow_watermark", self.venv_path, self.project_path)
            elif choice == "4":
                djj.run_script_in_tab("djjtb.media_tools.video_tools.video_cropper", self.venv_path, self.project_path)
            elif choice == "5":
                djj.run_script_in_tab("djjtb.media_tools.video_tools.video_group_merger", self.venv_path, self.project_path)
            elif choice == "6":
                djj.run_script_in_tab("djjtb.media_tools.video_tools.video_splitter", self.venv_path, self.project_path)
            elif choice == "7":
                djj.run_script_in_tab("djjtb.media_tools.video_tools.video_speed_changer", self.venv_path, self.project_path)
            elif choice == "8":
                djj.run_script_in_tab("djjtb.media_tools.video_tools.video_frame_extractor", self.venv_path, self.project_path)
            elif choice == "9":
                djj.run_script_in_tab("djjtb.media_tools.video_tools.video_gif_converter", self.venv_path, self.project_path)
            elif choice == "0":
                break
            elif choice == "00":
                djj.switch_to_terminal_tab("1")
                return "main_menu"
        
        return None
    
    def handle_image_tools(self):
        """Handle image tools submenu"""
        first_entry = True
        
        while True:
            if not first_entry:
                djj.wait_with_skip(8, "Back to Media Tools")
            self.show_image_tools_menu()
            
            choice = djj.prompt_choice("\033[93mChoose a Tool\033[0m" if first_entry else "\033[93mChoose another option\033[0m",
                                      ['1', '2', '3', '4', '5', '0', '00'])
            first_entry = False

            if choice == "1":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_processor", self.venv_path, self.project_path)
            elif choice == "2":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_collage_creator", self.venv_path, self.project_path)
            elif choice == "3":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_slideshow_maker", self.venv_path, self.project_path)
            elif choice == "4":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_webp_to_mp4", self.venv_path, self.project_path)
            elif choice == "5":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_video_compiler", self.venv_path, self.project_path)
            elif choice == "0":
                break
            elif choice == "00":
                djj.switch_to_terminal_tab("1")
                return "main_menu"
        
        return None
    
    def handle_media_tools(self):
        """Handle media tools submenu"""
        while True:
            self.show_media_tools_menu()
            choice = djj.prompt_choice("\033[93mChoose a Tool\033[0m",
                                     ['1', '2', '3', '4', '5', '6', 'p', 'px', 'd', 'w', 'h', 'c','fm', '0', '00'])
            
            if choice == "1":  # Videos
                result = self.handle_video_tools()
                if result == "main_menu":
                    return
            elif choice == "2":  # Images
                result = self.handle_image_tools()
                if result == "main_menu":
                    return
            elif choice == "3":  # Media Sorter
                djj.run_script_in_tab("djjtb.media_tools.media_sorter", self.venv_path, self.project_path)
            elif choice == "4":  # Media Metadata and Identifier
                djj.run_script_in_tab("djjtb.media_tools.metadata_tool", self.venv_path, self.project_path)
            elif choice == "5":  # Playlist Generator
                djj.run_script_in_tab("djjtb.media_tools.playlist_generator", self.venv_path, self.project_path)
            elif choice == "6":  # Media Info Extractor
                djj.run_script_in_tab("djjtb.media_tools.media_info_extractor", self.venv_path, self.project_path)
            elif choice == "p":  # Photomator
                djj.open_app("/Applications/Photomator.app")
            elif choice == "px":  # Pixelmator
                djj.open_app("/Applications/Pixelmator Pro.app")
            elif choice == "d":  # DaVinci Resolve
                djj.open_app("/Applications/DaVinci Resolve/DaVinci Resolve.app")
            elif choice == "w":  # Wondershare Uniconverter
                djj.open_app("/Applications/Wondershare UniConverter 15.app")
            elif choice == "h":  # Handbrake
                djj.open_app("/Applications/HandBrake.app")
            elif choice == "c":  # CollageIt 3
                djj.open_app("/Applications/CollageIt 3.app")
            elif choice == "fm":
                djj.open_app("/Users/home/Applications (Parallels)/{02e73adb-0fb7-45c1-888a-60680c0391ce} Applications.localized/Wondershare Filmora.app")
            elif choice in ["0", "00"]:
                break
    
    def handle_ai_tools(self):
        """Handle AI tools submenu"""
        while True:
            self.show_ai_tools_menu()
            choice = djj.prompt_choice("\033[93mChoose an AI tool\033[0m",
                                     ['1','1b', '2', '3', '4', '5', '6', '6a', '7', '7a','8','9','10','11','12','13','14','15','16','c0','c1' ,'c2' , 'c3', 'c4','c5','c6', 'c7', 'c8','cu','ch','cj', 'jc','atk', '0', '00'])
            """
            if choice == "1":  # Prompt Randomizer
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}/djjtb/ai_tools/; python3 -m djjtb.media_tools.ai_tools.prompt_randomizer")
            elif choice == "2":  # ComfyUI
                djj.run_command_in_tab(f"{self.project_path}/djjtb/ai_tools/comfyui_media_processor.command")
            elif choice == "3":  # Merge Loras
                # Run in current terminal
                os.system(f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.ai_tools.merge_loras.py")
            """
            if choice == "1":  # Codeformer
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.ai_tools.codeformer_runner")
            elif choice == "1b":  # Upscaler
                djj.run_command_in_tab(f"source /Users/home/Documents/ai_models/upscalers/upsvenv/bin/activate; cd {self.project_path}/; python3 -m djjtb.ai_tools.upscaler_runner")
            elif choice == "2":  # Joytag
                command = f"source /Users/home/Documents/ai_models/joytag/jtvenv/bin/activate; cd {self.project_path}/; python3 -m djjtb.ai_tools.joytag_tagger"
                djj.open_terminal_with_settings(command, "tagger", "525, 120, 1460, 700")
            elif choice == "3":  # Image Tagger (AI)
                command = (f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.ai_tools.image_tagger")
                djj.open_terminal_with_settings(command, "tagger", "525, 120, 1460, 700")
            elif choice == "4":  # FaceFusion
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.ai_tools.facefusion_runner")
            elif choice == "5":  # FaceFusion webUI
                command = (f"{self.project_path}/djjtb/ai_tools/run_facefusion.command")
                djj.open_terminal_with_settings(command, "tagger", "525, 120, 1225, 700")
            elif choice == "6":  # Watermark Remover Auto-Detect
                djj.run_command_in_tab(
                  f"source /Users/home/Documents/ai_models/joycaption/jcvenv/bin/activate; "
                  f"cd {self.project_path}/; python3 -m djjtb.ai_tools.joycaption_runner"
              )

                # djj.run_command_in_tab(f"source /Users/home/Documents/ai_models/watermark_remover/wmrmvenv/bin/activate; cd {self.project_path}/; python3 -m djjtb.ai_tools.watermark_remover_auto")
            elif choice == "6a":  # JoyCaption via Ollama (GGUF, no dedicated venv needed)
                djj.run_script_in_tab("djjtb.ai_tools.joycaption_runner_ollama", self.venv_path, self.project_path)
            elif choice == "7":
                djj.run_command_in_tab(f"source /Users/home/Documents/ai_models/upscalers/upsvenv/bin/activate; cd {self.project_path}/; python3 -m djjtb.ai_tools.upscaler_runner")
            elif choice == "7a":  # or whatever slot number you pick
                djj.run_command_in_tab(
                  f"source /Users/home/Documents/ai_models/upscalers/upsvenv/bin/activate; "
                  f"cd {self.project_path}/; python3 -m djjtb.ai_tools.cf_ups_runner"
              )
                # djj.run_command_in_tab(f"cd {self.project_path}/; python3 -m djjtb.ai_tools.watermark_remover_ref")
            elif choice == "8":  # IOPaint
                command = (f"{self.project_path}/djjtb/ai_tools/run_iopaint.command")
                djj.open_terminal_with_settings(command, "tagger", "525, 120, 1225, 700")
#            elif choice == "9":  # Image Upscaler - realesrgan_runner.py
#                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.ai_tools.realesrgan_runner")
#            elif choice == "10":  # Image Upscaler - realsr_runner.py
#                djj.run_command_in_tab(f"cd {self.project_path}/; python3 -m djjtb.ai_tools.realsr_runner")
            elif choice == "9":  # Image Finder
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.ai_tools.image_finder")
            elif choice == "10":  # Image Caption Generator
                command = f"source cd {self.project_path}/; python3 -m djjtb.ai_tools.image_caption_generator"
                djj.open_terminal_with_settings(command, "tagger", "525, 120, 1460, 700")
            elif choice == "11":  # Prompt Assembler
                command = ("/Users/home/Documents/Scripts/FLOW_TOOLS/prompt_assembler/LOCAL/prompt_assembler_runner.command")
                djj.open_terminal_with_settings(command, "comfyui", "1000, 120, 1700, 700")
            # elif choice == "12":  # Kohya_ss webUI
            #     command = (f"{self.project_path}/djjtb/ai_tools/run_kohya_ss.command")
            #     djj.open_terminal_with_settings(command, "tagger", "525, 120, 1225, 700")
            elif choice == "12":  # ComfyUI batch
                djj.run_script_in_tab("djjtb.ai_tools.comfyui.comfyui_batch", self.venv_path, self.project_path)
            elif choice == "13":  # OpenCode
                command = f"cd {self.project_path}; opencode"
                djj.open_terminal_with_settings(command, "home_profile", "1000, 120, 1700, 700")
            elif choice == "14":  # Open WebUI
                command = (f"{self.project_path}/djjtb/ai_tools/open_webui_runner.command")
                djj.open_terminal_with_settings(command, "home_profile", "525, 120, 1460, 700")
            elif choice == "15":  # Vocab + Mask Generator
                djj.run_script_in_tab("djjtb.ai_tools.vocab_mask_generator", self.venv_path, self.project_path)
            elif choice == "16":  # Category Sorter
                djj.run_script_in_tab("djjtb.ai_tools.category_sorter.category_sorter", self.venv_path, self.project_path)
            elif choice == "cu":
                command = (f"{self.project_path}/djjtb/ai_tools/comfyui_runner.command")
                djj.open_terminal_with_settings(command, "comfyui", "1000, 120, 1700, 700")
            elif choice == "atk":
                command = (f"{self.project_path}/djjtb/ai_tools/ostris_runner.command")
                djj.open_terminal_with_settings(command, "home_profile", "1000, 120, 1700, 700")
            elif choice == "ch":
                djj.open_path("/Applications/chaiNNer.app")
                djj.wait_with_skip(3, "Returning to AI Tools menu")
            elif choice == "cj":
                djj.run_script_in_tab("djjtb.ai_tools.comfyui.csv_to_prompt_library", self.venv_path, self.project_path)
            elif choice == "jc":
                djj.run_script_in_tab("djjtb.ai_tools.comfyui.json_to_prompt_csv", self.venv_path, self.project_path)
            elif choice == "c0":
                djj.open_path("/Users/home/Documents/ai_models/chaiNNer_workflows/facerestore_upscale_UT_stacked.chn")
                djj.wait_with_skip(3, "Returning to AI Tools menu")
            elif choice == "c1":
                djj.open_path("/Users/home/Documents/ai_models/chaiNNer_workflows/upscale_facerestore.chn")
                djj.wait_with_skip(3, "Returning to AI Tools menu")
            elif choice == "c2":
                djj.open_path("/Users/home/Documents/ai_models/chaiNNer_workflows/upscale_only.chn")
                djj.wait_with_skip(3, "Returning to AI Tools menu")
            elif choice == "c3":
                djj.open_path("/Users/home/Documents/ai_models/chaiNNer_workflows/facerestore_only.chn")
                djj.wait_with_skip(3, "Returning to AI Tools menu")
            elif choice == "c4":
                djj.open_path("/Users/home/Documents/ai_models/chaiNNer_workflows/crop.chn")
                djj.wait_with_skip(3, "Returning to AI Tools menu")
            elif choice == "c5":
                djj.open_path("/Users/home/Documents/ai_models/chaiNNer_workflows/resize.chn")
                djj.wait_with_skip(3, "Returning to AI Tools menu")
            elif choice == "c6":
                djj.open_path("/Users/home/Documents/ai_models/chaiNNer_workflows/watermark_remover.chn")
                djj.wait_with_skip(3, "Returning to AI Tools menu")
            elif choice == "c7":
                djj.open_path("/Users/home/Documents/ai_models/chaiNNer_workflows/stack.chn")
            elif choice == "c8":
                djj.open_path("/Users/home/Documents/ai_models/chaiNNer_workflows/bg_remove.chn")
                djj.wait_with_skip(3, "Returning to AI Tools menu")
            elif choice in ["0", "00"]:
                break
    
    def handle_file_tools(self):
        """Handle file tools submenu"""
        while True:
            self.show_file_tools_menu()
            choice = djj.prompt_choice("\033[93mChoose a file tool\033[0m",
                                     ['1', '2', '3', '4', '5', '6','7', '8', '0', '00'])
            
            if choice == "1":  # Rsync
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.file_tools.rsync_helper")
            elif choice == "2":  # Add Root Folder Prefix
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.file_tools.add_root_dir_prefix")
            elif choice == "3":  # Auto Subfolder
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.file_tools.auto_subfolder")
            elif choice == "4":  # Filename Randomizer
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.file_tools.filename_randomizer")
            elif choice == "5":  # File Identifier
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.file_tools.file_identifier")
            elif choice == "6":  # README Generator
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.file_tools.readme_generator")
            elif choice == "7":
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.file_tools.x_to_w_copy")
            elif choice == "8":  # Add Pose Prompts
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.file_tools.add_pose_prompts")
            elif choice in ["0", "00"]:
                break

    def handle_quick_tools(self, choice):
        """Handle quick tools"""
        if choice == "4":  # Reverse Image Search
            command = f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.quick_tools.reverse_image_search"
            djj.open_terminal_with_settings(command, "LinkGrabber", "50, 282, 250, 482")
        
        elif choice == "5":  # Link Grabber
            command = f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.quick_tools.link_grabber"
            djj.open_terminal_with_settings(command, "LinkGrabber", "850, 730, 1650, 960")
        
        elif choice == "6":  # Path Grabber
            command = f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.quick_tools.path_grabber"
            djj.open_terminal_with_settings(command, "path_grabber", "850, 450, 1650, 680")
        
        elif choice == "7":  # Multi XMP Viewer
            command = f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.quick_tools.multi_xmp_viewer"
            djj.open_terminal_with_settings(command, "LinkGrabber", "50, 490, 100, 690")
        
        elif choice == "8":  # Media Info Viewer
            command = f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.quick_tools.media_info_viewer"
            djj.open_terminal_with_settings(command, "LinkGrabber", "50, 80, 80, 280")
        
        elif choice == "9":  # Auto Scroller
            command = f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.quick_tools.auto_scroller"
            djj.open_terminal_with_settings(command, "auto_scroller", "50, 180, 380, 350")
        elif choice == "10":
                djj.run_script_in_tab("djjtb.quick_tools.link_scraper", self.venv_path, self.project_path)

        elif choice == "11":  # Mount Movies 4 & 8 — silent background mount
            print("\033[93mMounting Disks...\033[0m")
            for disk_uuid in [
                "4AF0255E-DAEE-41F8-A045-0194DB148A2F",
                "284C712E-9F72-46B8-AF7A-4FB416299AF2",
            ]:
                subprocess.Popen(
                    ["diskutil", "mount", disk_uuid],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            time.sleep(2)


    def handle_admin_tools(self):
        """Handle Admin Tools submenu (password-protected, not fancy — just a speedbump)"""
        ADMIN_PASSWORD = "555"  # 🔒 change this to whatever you like

        os.system('clear')
        print()
        print("\033[91m🔐 Restricted Access\033[0m")
        attempt = input("Enter Admin Password: \n > ").strip()

        if attempt != ADMIN_PASSWORD:
            print("\n\033[91m❌ Incorrect password. Returning to main menu...\033[0m")
            djj.wait_with_skip(3, "Returning to main menu")
            return

        while True:
            self.show_admin_tools_menu()
            choice = djj.prompt_choice("\033[91mChoose an admin tool\033[0m", ['1', '2', '3', '4', '5', '6', '7', '8', '8a', '9', '0', '00'])

            if choice == "1":  # djjtb_scan.py
                djj.run_command_in_tab(
                    f"source {self.venv_path}; cd {self.project_path}; "
                    f"python3 djjtb/admin_tools/djjtb_scan.py"
                )
            elif choice == "2":  # env_backup.sh
                djj.run_command_in_tab(
                    f"bash {self.project_path}/djjtb/admin_tools/env_backup.sh"
                )
            elif choice == "3":  # push_github.command
                djj.run_command_in_tab(
                    f"bash {self.project_path}/djjtb/admin_tools/push_github.command"
                )
            elif choice == "4":  # List Open Ports
                djj.run_command_in_tab("lsof -iTCP -sTCP:LISTEN -P")
            elif choice == "5":  # Diskutil List
                djj.run_command_in_tab("diskutil list")
            elif choice == "6":  # Command Help
                djj.run_command_in_tab("bash /Users/home/Documents/Scripts/HELP/cmd_help.sh")
            elif choice == "7":  # VLC Screenshot Renamer
                djj.run_command_in_tab(
                    f"source {self.venv_path}; cd {self.project_path}; "
                    f"python3 djjtb/helpers/vlc/vlc_renamer.py"
                )
            elif choice == "8":  # Mount Movies 4 & 8 — silent background mount
                print("\033[93mMounting Disks...\033[0m")
                for disk_uuid in [
                    "4AF0255E-DAEE-41F8-A045-0194DB148A2F",
                    "284C712E-9F72-46B8-AF7A-4FB416299AF2",
                ]:
                    subprocess.Popen(
                        ["diskutil", "mount", disk_uuid],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                time.sleep(2)
            elif choice == "8a":  # Mount Movies 4 & 8 — silent background mount
                print("\033[93mUnmounting Disks...\033[0m")
                for disk_uuid in [
                    "4AF0255E-DAEE-41F8-A045-0194DB148A2F",
                    "284C712E-9F72-46B8-AF7A-4FB416299AF2",
                ]:
                    subprocess.Popen(
                        ["diskutil", "unmount", disk_uuid],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                time.sleep(2)
            elif choice == "9":  # Stop ComfyUI
                djj.run_command_in_tab(
                    f"bash {self.project_path}/djjtb/ai_tools/comfyui_stop.command"
                )
            elif choice == "0":
                break
            elif choice == "00":
                djj.switch_to_terminal_tab("1")
                return
            
  
    def launch_grabbers_at_boot(self):
        """Fire Link Grabber and Path Grabber — only called on fresh boot launch."""
        command_link = f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.quick_tools.link_grabber"
        djj.open_terminal_with_settings(command_link, "LinkGrabber", "850, 730, 1650, 960")
        # Small pause so windows don't collide
        time.sleep(2)
        command_path = f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.quick_tools.path_grabber"
        djj.open_terminal_with_settings(command_path, "path_grabber", "850, 450, 1650, 680")

    def run(self):
        """Main launcher loop"""
        djj.setup_terminal()
        os.system('clear')

        # Auto-launch grabbers on first boot only
        if is_boot_launch():
            self.launch_grabbers_at_boot()
            write_grabber_stamp()
        
        while True:
            self.show_main_menu()
            choice = djj.prompt_choice("\033[93mChoose a category\033[0m",
                                     ['1', '2', '3', '4', '5', '6', '7', '8', '9','10', '11', 'a' , 'ad', 'c', 'x'])

            if choice == "1":
                self.handle_media_tools()
            elif choice == "2":
                self.handle_ai_tools()
            elif choice == "3":
                self.handle_file_tools()
            elif choice in ["4", "5", "6", "7", "8", "9","10", "11"]:
                self.handle_quick_tools(choice)
            elif choice == "a":  # App Launcher
                command = f"cd {self.project_path}; python3 -m djjtb.app_launcher"
                djj.open_terminal_with_settings(command, "djjtb", "738, 200, 1314, 958")
            elif choice == "ad":  # Admin Tools
                self.handle_admin_tools()
            elif choice == "c":
                djj.cleanup_tabs()
            elif choice == "x":
                print("\033[93mExiting...\033[0m")
                break
            
            os.system('clear')

def main():
    launcher = DJJTBLauncher()
    launcher.run()

if __name__ == "__main__":
    main()