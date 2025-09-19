#!/usr/bin/env python3
"""
DJJTB Python Launcher
Updated: Sep 14, 2025
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
        print("               \033[1;93m🧰 DJJ TOOLBOX 💻\033[0m")
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mMAIN MENU\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 1.🎞️  MEDIA TOOLS 🎑")
        print(" 2.🤖 AI TOOLS 🦾")
        print(" 3.📁 FILE TOOLS 🗂️")
        print(" A.📱 APP LAUNCHER 🚀")
        print()
        print("\033[1;93mQUICK TOOLS\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 4.🌠 Reverse Image Search 🔎")
        print(" 5.🔗 Link Grabber ✊🏼")
        print(" 6.🚏 Path Grabber ✊🏼")
        print(" 7.🔢 Multi XMP Viewer 👀")
        print(" 8.📺 Media Info Viewer ℹ️")
        print(" 9.⚙️  Auto Scroller ⏬")
        print("10.🔗 Link Scraper 🪏")
        print("\033[92m--------------------------------------------------\033[0m")
        print("✈️ E\033[91mx\033[0mit    🗂️ \033[1;32mC\033[0mlean Tabs")
        print("\033[92m==================================================\033[0m")
    
    def show_media_tools_menu(self):
        """Display media tools menu"""
        os.system('clear')
        print()
        print()
        print("\033[1;93m🎇 MEDIA TOOLS 📽️\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 1. VIDEOS 📺")
        print(" 2. IMAGES 📸")
        print(" 3. Media Sorter 🔢")
        print(" 4. Metadata Stripper + Identifier 🔖 🔪")
        print(" 5. Playlist Generator 📋 🍿")
        print(" 6. Media Info Extractor 📼 🌅 ℹ️")
        print()
        print("\033[1;93m📱 APPS 💻\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" P. Photomator")
        print("PX. Pixelmator")
        print(" D. DaVinci Resolve")
        print(" W. Wondershare Uniconverter")
        print(" H. Handbrake")
        print(" C. CollageIt 3")
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 0. ⏪ Back")
        print("00. ⏮️  MAIN MENU")
        print("\033[92m--------------------------------------------------\033[0m")
    
    def show_video_tools_menu(self):
        """Display video tools menu"""
        os.system('clear')
        print()
        print()
        print("\033[93m🎬 VIDEO TOOLS 🎬\033[0m")
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
        print("\033[93m🖼️  IMAGES TOOLS 🖼️\033[0m")
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
        print("\033[93m🤖 AI TOOLS 🛠️\033[0m")
        print("\033[92m--------------------------------------------------\033[0m")
        #print(" 1. Prompt Randomizer 📝 🔀")
        #print(" 2. ComfyUI ☀️ 💻")
        #print(" 3. Merge Loras 👫➡︎🧍🏼‍♂️")
        print(" 1. Codeformer 😶‍🌫️➡︎😝")
        print(" 2. JoyTag Tagger (AI) 🏷️")
        print(" 3. Image Tagger (AI) 🔖")
        print(" 4. FaceFusion (NSFW Patched) 👿➡︎😇")
        print(" 5. FaceFusion WebUI 🌐 👿➡︎😇")
        print(" 6. Watermark Remover (AI) 💋 🧼")
        print(" 7. Watermark Remover PKFPL (AI) 🎀 🧼")
        print(" 8. IOPaint - lama cleaner (WebUI) 🦙 🧼")
        print(" 9. Image Upscaler (Real-Esrgan4x) 💓 💗 🩷")
        print("10. Image Upscaler (RealSR 4x) 👶🏼 👦🏻 🤦🏽‍♂️")
        print("11. Image Finder (AI) 🔎")
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
        print("1. Rsync Helper 👯‍♀️")
        print("2. Add Root Folder Prefix 🗂️")
        print("3. File Identifier 🆔")
        print("4. README Generator 📖")
        print()
        print("\033[92m--------------------------------------------------\033[0m")
        print(" 0. ⏪ Back")
        print("00. ⏮️  MAIN MENU")
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
                                     ['1', '2', '3', '4', '5', '6', 'p', 'px', 'd', 'w', 'h', 'c', '0', '00'])
            
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
            elif choice in ["0", "00"]:
                break
    
    def handle_ai_tools(self):
        """Handle AI tools submenu"""
        while True:
            self.show_ai_tools_menu()
            choice = djj.prompt_choice("\033[93mChoose an AI tool\033[0m",
                                     ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10','11', '0', '00'])
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
            elif choice == "2":  # Joytag
                command = f"cd {self.project_path}/; python3 -m djjtb.ai_tools.joytag_tagger"
                djj.open_terminal_with_settings(command, "tagger", "525, 120, 1460, 700")
            elif choice == "3":  # Image Tagger (AI)
                command = (f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.ai_tools.image_tagger")
                djj.open_terminal_with_settings(command, "tagger", "525, 120, 1460, 700")
            elif choice == "4":  # FaceFusion
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.ai_tools.facefusion_runner")
            elif choice == "5":  # FaceFusion webUI
                command = (f"{self.project_path}/djjtb/ai_tools/run_facefusion.command")
                djj.open_terminal_with_settings(command, "tagger", "525, 120, 1225, 700")
            elif choice == "6":  # Watermark Remover
                djj.run_command_in_tab(f"cd {self.project_path}/; python3 -m djjtb.ai_tools.watermark_remover")
            elif choice == "7":  # Watermark Remover
                djj.run_command_in_tab(f"cd {self.project_path}/; python3 -m djjtb.ai_tools.watermark_remover_pkfpl")
            elif choice == "8":  # IOPaint
                command = (f"{self.project_path}/djjtb/ai_tools/run_iopaint.command")
                djj.open_terminal_with_settings(command, "tagger", "525, 120, 1225, 700")
            elif choice == "9":  # Image Upscaler - realesrgan_runner.py
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.ai_tools.realesrgan_runner")
            elif choice == "10":  # Image Upscaler - realsr_runner.py
                djj.run_command_in_tab(f"cd {self.project_path}/; python3 -m djjtb.ai_tools.realsr_runner")
            elif choice == "11":  # Image Finder
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.ai_tools.image_finder")
            elif choice in ["0", "00"]:
                break
    
    def handle_file_tools(self):
        """Handle file tools submenu"""
        while True:
            self.show_file_tools_menu()
            choice = djj.prompt_choice("\033[93mChoose a file tool\033[0m",
                                     ['1', '2', '3', '4', '0', '00'])
            
            if choice == "1":  # Rsync
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.quick_tools.rsync_helper")
            elif choice == "2":  # Add Root Folder Prefix
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.file_tools.add_root_dir_prefix")
            elif choice == "3":  # File Identifier
                djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.file_tools.file_identifier")
            elif choice == "4":  # README Generator
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