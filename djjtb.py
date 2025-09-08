#!/usr/bin/env python3
"""
DJJTB Python Launcher
Media Processor: Run Video or Image Processor
Updated: July 21, 2025
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
        print("               \033[1;33m🧰 DJJ TOOLBOX 💻\033[0m")
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mMAIN MENU\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 1.🎞️  MEDIA TOOLS 🎑")
        print(" 2.🤖 AI TOOLS 🦾")
        print(" 3.📁 FILE TOOLS 🗂️")
        print()
        print("\033[1;33mQUICK TOOLS\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 4.🌠 Reverse Image Search 🔎")
        print(" 5.🔗 Linkgrabber ✊🏼")
        print(" 6.🚏 Pathgrabber ✊🏼")
        print(" 7.🔢 Multi XMP Viewer 👀")
        print(" 8.📺 Media Info Viewer ℹ️")
        print(" 9.📱 APP LAUNCHER 🚀")
        print("10.⚙️  Auto Scroller ⏬")
        print("\033[92m--------------------------------------------------\033[0m")
        print("✈️ E\033[91mx\033[0mit    🗂️ \033[1;32mC\033[0mlean Tabs")
        print("\033[92m==================================================\033[0m")
    
    def show_media_tools_menu(self):
        """Display media tools menu"""
        os.system('clear')
        print()
        print()
        print("\033[1;33m🎇 MEDIA TOOLS 📽️\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 1. VIDEOS")
        print(" 2. IMAGES")
        print(" 3. Media Sorter")
        print(" 4. Metadata Stripper + Identifier")
        print(" 5. Playlist Generator")

        print()
        print("\033[1;33m📱 APPS 💻\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 6. Photomator")
        print(" 7. Pixelmator")
        print(" 8. DaVinci Resolve")
        print(" 9. Wondershare Uniconverter")
        print("10. Handbrake")
        print("11. CollageIt 3")
        print()
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 0. ⏪ Back")
        print("00. ⏮️  MAIN MENU")
        print("\033[92m--------------------------------------------------\033[0m")
    
    def show_video_tools_menu(self):
        """Display video tools menu"""
        os.system('clear')
        print()
        print()
        print("🎬 VIDEO TOOLS 🎬")
        print("\033[92m--------------------------------------------------\033[0m")
        print("1. Video Re-encoder 📼➡︎📀")
        print("2. Reverse Merge ↪️ ⇔↩️")
        print("3. Slideshow Watermark 📹 🆔")
        print("4. Cropper 👖➡︎🩳")
        print("5. Group Merger 📹 🧲")
        print("6. Video Splitter 📹 ✂️  ⏱️")
        print("7. Speed Changer 🐇⬌🐢")
        print("8. Frame Extractor 📹➡︎🌃🌆🎆🎇")
        print("9. GIFs Converter 📹⬌🌃🌆🎆🎇")
        print()
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 0. ⏪ Back to MEDIA TOOLS")
        print("00. ⏮️  MAIN MENU")
        print("\033[92m--------------------------------------------------\033[0m")
    
    def show_image_tools_menu(self):
        """Display image tools menu"""
        os.system('clear')
        print()
        print()
        print("🖼️  IMAGES TOOLS 🖼️")
        print("\033[92m--------------------------------------------------\033[0m")
        print("1. Image Converter 🎞️ ➡︎🌠")
        print("2. Strip Padding 🔲➡︎⬜️")
        print("3. Flip or Rotate ↔️  🔄")
        print("4. Collage Creation 🧩 🎇")
        print("5. Resize Images 🩷⬌💓")
        print("6. Slideshow Maker 🎑➡︎📽️")
        print("7. Image Pairing ✋🏼 🤲🏼")
        print("8. Image Padding ◼️➡︎🔳")
        print()
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 0. ⏪ Back to MEDIA TOOLS")
        print("00. ⏮️  MAIN MENU")
        print("\033[92m--------------------------------------------------\033[0m")
    
    def show_ai_tools_menu(self):
        """Display AI tools menu"""
        os.system('clear')
        print()
        print("🤖 AI TOOLS 🛠️")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 1. Prompt Randomizer 📝 🔀")
        print(" 2. ComfyUI ☀️ 💻")
        print(" 3. Merge Loras 👫➡︎🧍🏼‍♂️")
        print(" 4. Codeformer 😶‍🌫️➡︎😝")
        print(" 5. JoyTag Tagger (AI) 🏷️")
        print(" 6. Image Tagger (AI) 🔖")
        print(" 7. FaceFusion (NSFW Patched) 👿➡︎😇")
        print(" 8. Watermark Remover (AI) 💋 🧼")
        print(" 9. Watermark Remover PKFPL (AI) 🟪 🧼")
        #print("10. Image Finder (AI) 🔎")
        print()
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 0. ⏪ Back")
        print("00. ⏮️  MAIN MENU")
        print("\033[92m--------------------------------------------------\033[0m")
    
    def show_file_tools_menu(self):
        """Display file tools menu"""
        os.system('clear')
        print()
        print("📁 FILE TOOLS 🗂️")
        print("\033[92m--------------------------------------------------\033[0m")
        print("1. Add Root Folder Prefix 🗂️")
        print("2. File Identifier 🆔")
        print("3. README Generator 📖")
        print()
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 0. ⏪ Back")
        print("00. ⏮️  MAIN MENU")
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
                                     ['1', '2', '3', '4', '5', '6', '7', '8', '0', '00'])
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
                djj.run_command_in_tab(f"cd {self.project_path}; source djjvenv/bin/activate; export PYTHONPATH=.; python3 -m djjtb.media_tools.image_tools.image_resizer")
            elif choice == "6":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_slideshow_maker", self.venv_path, self.project_path)
            elif choice == "7":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_pairing", self.venv_path, self.project_path)
            elif choice == "8":
                djj.run_script_in_tab("djjtb.media_tools.image_tools.image_padder", self.venv_path, self.project_path)
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
                                     ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11',  '0', '00'])
            
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
            elif choice == "6":  # Photomator
                djj.open_app("/Applications/Photomator.app")
            elif choice == "7":  # Pixelmator
                djj.open_app("/Applications/Pixelmator Pro.app")
            elif choice == "8":  # DaVinci Resolve
                djj.open_app("/Applications/DaVinci Resolve/DaVinci Resolve.app")
            elif choice == "9":  # Wondershare Uniconverter
                djj.open_app("/Applications/Wondershare UniConverter 15.app")
            elif choice == "10":  # Handbrake
                djj.open_app("/Applications/HandBrake.app")
            elif choice == "11":  # CollageIt 3
                djj.open_app("/Applications/CollageIt 3.app")
            elif choice in ["0", "00"]:
                break
    
    def handle_ai_tools(self):
        """Handle AI tools submenu"""
        while True:
            self.show_ai_tools_menu()
            choice = djj.prompt_choice("\033[93mChoose an AI tool\033[0m",
                                     ['1', '2', '3', '4', '5', '6', '7', '8', '0', '9', '00'])
            
            if choice == "1":  # Prompt Randomizer
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}/djjtb/ai_tools/; python3 -m djjtb.media_tools.ai_tools.prompt_randomizer")
            elif choice == "2":  # ComfyUI
                djj.run_command_in_tab(f"{self.project_path}/djjtb/ai_tools/comfyui_media_processor.command")
            elif choice == "3":  # Merge Loras
                # Run in current terminal
                os.system(f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.ai_tools.merge_loras.py")
            elif choice == "4":  # Codeformer
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.ai_tools.codeformer_runner")
            elif choice == "5":  # Joytag
                djj.run_command_in_tab(f"cd {self.project_path}/; python3 -m djjtb.ai_tools.joytag_tagger")
            elif choice == "6":  # Image Tagger (AI)
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.ai_tools.image_tagger")
            elif choice == "7":  # FaceFusion
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.ai_tools.facefusion_runner")
            elif choice == "8":  # Watermark Remover
                djj.run_command_in_tab(f"cd {self.project_path}/; python3 -m djjtb.ai_tools.watermark_remover")
            elif choice == "9":  # Watermark Remover
                djj.run_command_in_tab(f"cd {self.project_path}/; python3 -m djjtb.ai_tools.watermark_remover_pkfpl")
            elif choice in ["0", "00"]:
                break
    
    def handle_file_tools(self):
        """Handle file tools submenu"""
        while True:
            self.show_file_tools_menu()
            choice = djj.prompt_choice("\033[93mChoose a file tool\033[0m",
                                     ['1', '2', '3', '0', '00'])
            
            if choice == "1":  # Add Root Folder Prefix
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.file_tools.add_root_dir_prefix")
            elif choice == "2":  # File Identifier
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.file_tools.file_identifier")
            elif choice == "3":  # README Generator
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
            djj.open_terminal_with_settings(command, "LinkGrabber", "50, 730, 600, 960")
        
        elif choice == "6":  # Path Grabber
            command = f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.quick_tools.path_grabber"
            djj.open_terminal_with_settings(command, "path_grabber", "50, 450, 700, 680")
        
        elif choice == "7":  # Multi XMP Viewer
            command = f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.quick_tools.multi_xmp_viewer"
            djj.open_terminal_with_settings(command, "LinkGrabber", "50, 490, 250, 690")
        
        elif choice == "8":  # Media Info Viewer
            command = f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.quick_tools.media_info_viewer"
            djj.open_terminal_with_settings(command, "LinkGrabber", "50, 80, 250, 280")
        
        elif choice == "9":  # App Launcher
            djj.run_app_launcher()
        
        elif choice == "10":  # Auto Scroller
            command = f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.quick_tools.auto_scroller"
            djj.open_terminal_with_settings(command, "auto_scroller", "50, 180, 380, 350")
    
    def run(self):
        """Main launcher loop"""
        djj.setup_terminal()
        os.system('clear')
        
        while True:
            self.show_main_menu()
            choice = djj.prompt_choice("\033[93mChoose a category\033[0m",
                                     ['1', '2', '3', '4', '5', '6', '7', '8', '9','10', 'c', 'x'])
            
            if choice == "1":
                self.handle_media_tools()
            elif choice == "2":
                self.handle_ai_tools()
            elif choice == "3":
                self.handle_file_tools()
            elif choice in ["4", "5", "6", "7", "8", "9", "10"]:
                self.handle_quick_tools(choice)
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