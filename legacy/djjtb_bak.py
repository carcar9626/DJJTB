#!/usr/bin/env python3
"""
DJJTB Python Launcher

"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))
import djjtb.utils as djj

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
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰\033[4;91mX\033[0m  Exit 👋🏻✈️")
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
        print(" 💰 \033[4;93m1\033[0m  Image Converter 🎞️ ➡︎🌠")
        print(" 💰 \033[4;93m2\033[0m  Strip Padding 🔲➡︎⬜️")
        print(" 💰 \033[4;93m3\033[0m  Flip or Rotate ↔️  🔄")
        print(" 💰 \033[4;93m4\033[0m  Collage Creation 🧩 🎇")
        print(" 💰 \033[4;93m5\033[0m  Resize Images 🩷⬌💓")
        print(" 💰 \033[4;93m6\033[0m  Slideshow Maker 🎑➡︎📽️")
        print(" 💰 \033[4;93m7\033[0m  Image Pairing ✋🏼 🤲🏼")
        print(" 💰 \033[4;93m8\033[0m  Image Padding ◼️➡︎🔳")
        print(" 💰 \033[4;93m9\033[0m  Webp to MP4 Converter 👾➡︎📹")
        print(" 💰\033[4;93m10\033[0m  Images to Video Compiler 🌃🌆🎆🎇➡︎📹")
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
        print(" 💰 \033[4;93m7\033[0m  Image Upscaler (4x_UltraSharp 💓 💗 🩷")
        # print(" 💰 \033[4;93m6\033[0m  WM Remover Auto-Detect(AI) 🤖 💋 🧼")
        # print(" 💰 \033[4;93m7\033[0m  WM Remover from Reference (AI) 👷🏻‍♂️ 💋 🧼")
        print(" 💰 \033[4;93m8\033[0m  IOPaint - lama cleaner (WebUI) 🦙 🧼")
#        print(" 💰\033[4;93m9\033[0m  Image Upscaler (Real-Esrgan4x) 💓 💗 🩷")
#        print("💰\033[4;93m10\033[0m  Image Upscaler (RealSR 4x) 👶🏼 👦🏻 🤦🏽‍♂️")
        print(" 💰 \033[4;93m9\033[0m  Image Finder (AI) 🔎")
        print(" 💰\033[4;93m10\033[0m  Image Caption Generator (AI)(Florence) 🩻📜")
        print(" 💰\033[4;93m11\033[0m  Kohya_SS (AI)(SD Lora Trainer) 🏋🏻")
        print(" 💰\033[4;93m12\033[0m  Comfyui Batch Process ▶️")
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
        print(" 💰\033[4;93mCU\033[0m  ComfyUI")
        print(" 💰\033[4;93mCH\033[0m  chaiNNer")
        print(" 💰\033[4;93mCJ\033[0m  Prompt Lib CSV to JSON")
        print(" 💰\033[4;93mJC\033[0m  Prompt Lib JSON to CSV")
        
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
        print()
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 💰 \033[4;93m0\033[0m  ⏪ Back")
        print(" 💰\033[4;93m00\033[0m ⏮️  MAIN MENU")
        print("\033[92m--------------------------------------------------\033[0m")
        
#    def show_admin_tools_menu(self):
#    """Display Admin Tools menu (password-protected)"""
#    os.system("clear && printf '\033c'")
#    print()
#    print("\033[91m🔐 ADMIN TOOLS 🔐\033[0m")
#    print("\033[92m--------------------------------------------------\033[0m")
#    print("1. Backup DB Files 💾")
#    print("2. Delete Cache 🗑️")
#    print("3. Run Integrity Check 🧪")
#    print("4. Sync Tag Databases 🔁")
#    print("\033[92m--------------------------------------------------\033[0m")
#    print(" 0. ⏪ Back")
#    print("00. ⏮️  MAIN MENU")
#    print("\033[92m--------------------------------------------------\033[0m")
    
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
                                     ['1', '2', '3', '4', '5', '6', '7', '8','9', '10','11', '0', '00'])
            first_entry = False
            
            if choice == "1":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_converter", self.venv_path, self.project_path)
            elif choice == "2":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_strip_padding", self.venv_path, self.project_path)
            elif choice == "3":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_flip_rotate", self.venv_path, self.project_path)
            elif choice == "4":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_collage_creator", self.venv_path, self.project_path)
            elif choice == "5":
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path};    python3 -m djjtb.media_tools.image_tools.image_resizer")
            elif choice == "6":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_slideshow_maker", self.venv_path, self.project_path)
            elif choice == "7":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_pairing", self.venv_path, self.project_path)
            elif choice == "8":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_padder", self.venv_path, self.project_path)
            elif choice == "9":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_webp_to_mp4", self.venv_path, self.project_path)
            elif choice == "10":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_video_compiler", self.venv_path, self.project_path)
            # elif choice == "11":
            #     djj.run_script_in_tab("djjtb.media_tools.image_tools.image_stack", self.venv_path, self.project_path)
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
                                     ['1','1b', '2', '3', '4', '5', '6', '7', '8', '9','10','11','12','c0','c1' ,'c2' , 'c3', 'c4','c5','c6', 'c7', 'c8','cu','ch','cj', 'jc', '0', '00'])
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
            elif choice == "7":  # Watermark Remover from Reference
                djj.run_command_in_tab(f"source /Users/home/Documents/ai_models/upscalers/upsvenv/bin/activate; cd {self.project_path}/; python3 -m djjtb.ai_tools.upscaler_runner")
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
            elif choice == "11":  # Kohya_ss webUI
                command = (f"{self.project_path}/djjtb/ai_tools/run_kohya_ss.command")
                djj.open_terminal_with_settings(command, "tagger", "525, 120, 1225, 700")
            elif choice == "12":  # ComfyUI batch
                djj.run_script_in_tab("djjtb.ai_tools.comfyui.comfyui_batch", self.venv_path, self.project_path)
            elif choice == "cu":
                command = (f"{self.project_path}/djjtb/ai_tools/comfyui_runner.command")
                djj.open_terminal_with_settings(command, "comfyui", "1000, 120, 1700, 700")
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
                                     ['1', '2', '3', '4', '5', '6', '0', '00'])
            
            if choice == "1":  # Rsync
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.quick_tools.rsync_helper")
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

                
#        def handle_admin_tools(self):
#            """Handle Admin Tools submenu (requires password)"""
#            PASSWORD = "supersecret"  # 🔒 Change this to your desired password
#
#            os.system("clear && printf '\033c'")
#            print("\n\033[91m⚠️  Restricted Access\033[0m")
#            attempt = input("Enter Admin Password: ")
#
#            if attempt != PASSWORD:
#                print("\n\033[91m❌ Incorrect password. Returning to main menu...\033[0m")
#                djj.wait_with_skip(3)
#                return
#
#            while True:
#                self.show_admin_tools_menu()
#                choice = djj.prompt_choice("\033[91mChoose an admin tool\033[0m", ['1', '2', '3', '4', '0'])
#
#                if choice == "1":
#                    djj.run_script_in_tab("djjtb.admin_tools.backup_db", self.venv_path, self.project_path)
#                elif choice == "2":
#                    djj.run_script_in_tab("djjtb.admin_tools.clear_cache", self.venv_path, self.project_path)
#                elif choice == "3":
#                    djj.run_script_in_tab("djjtb.admin_tools.check_integrity", self.venv_path, self.project_path)
#                elif choice == "4":
#                    djj.run_script_in_tab("djjtb.admin_tools.sync_tag_dbs", self.venv_path, self.project_path)
#                elif choice == "0":
#                    break
            
  
    def run(self):
        """Main launcher loop"""
        djj.setup_terminal()
        os.system('clear')
        
        while True:
            self.show_main_menu()
            choice = djj.prompt_choice("\033[93mChoose a category\033[0m",
                                     ['1', '2', '3', '4', '5', '6', '7', '8', '9','10', 'a' , 'c', 'x'])
            
            if choice == "1":
                self.handle_media_tools()
            elif choice == "2":
                self.handle_ai_tools()
            elif choice == "3":
                self.handle_file_tools()
            elif choice in ["4", "5", "6", "7", "8", "9","10"]:
                self.handle_quick_tools(choice)
            elif choice == "a":  # App Launcher
                command = f"cd {self.project_path}; python3 -m djjtb.app_launcher"
                djj.open_terminal_with_settings(command, "djjtb", "738, 200, 1314, 958")
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