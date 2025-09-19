#!/usr/bin/env python3
"""
DJJTB Python Launcher (Tkinter GUI Version)
Media Processor: Run Video or Image Processor with Clickable Buttons
Updated: July 21, 2025
"""

import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import threading
import time

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))
import djjtb.utils as djj

class DJJTBLauncherGUI:
    def __init__(self):
        self.venv_path = "~/Documents/Scripts/DJJTB/djjvenv/bin/activate"
        self.project_path = "/Users/home/Documents/Scripts/DJJTB"
        self.root = tk.Tk()
        self.root.title("DJJ Toolbox")
        self.root.geometry("400x600")  # Set window size
        self.timer = None  # For countdown in submenus

    def clear_window(self):
        """Clear all widgets from the window"""
        for widget in self.root.winfo_children():
            widget.destroy()
        if self.timer:
            self.timer.cancel()  # Cancel any active timer

    def start_timer(self, seconds, callback):
        """Start a timer that calls the callback function after seconds"""
        self.timer = threading.Timer(seconds, lambda: self.root.after(0, callback))
        self.timer.start()

    def show_main_menu(self):
        """Display main menu with clickable buttons"""
        self.clear_window()
        tk.Label(self.root, text="🧰 DJJ TOOLBOX 💻", font=("Arial", 16, "bold"), fg="darkorange").pack(pady=10)
        tk.Label(self.root, text="MAIN MENU", font=("Arial", 12, "bold"), fg="darkorange").pack()
        tk.Label(self.root, text="-----------------------------------", fg="green").pack()
        tk.Button(self.root, text="🎞️ MEDIA TOOLS 🎑", command=self.handle_media_tools, width=30).pack(pady=5)
        tk.Button(self.root, text="🤖 AI TOOLS 🦾", command=self.handle_ai_tools, width=30).pack(pady=5)
        tk.Label(self.root, text="QUICK TOOLS", font=("Arial", 12, "bold"), fg="darkorange").pack(pady=5)
        tk.Label(self.root, text="-----------------------------------", fg="green").pack()
        tk.Button(self.root, text="🌠 Reverse Image Search 🔎", command=lambda: self.handle_quick_tools("3"), width=30).pack(pady=5)
        tk.Button(self.root, text="🔗 Linkgrabber ✊🏼", command=lambda: self.handle_quick_tools("4"), width=30).pack(pady=5)
        tk.Button(self.root, text="📺 Media Info Viewer ℹ️", command=lambda: self.handle_quick_tools("5"), width=30).pack(pady=5)
        tk.Button(self.root, text="📱 APP LAUNCHER 🚀", command=lambda: self.handle_quick_tools("6"), width=30).pack(pady=5)
        tk.Label(self.root, text="-----------------------------------", fg="green").pack()
        tk.Button(self.root, text="🗂️ Clean Tabs", command=djj.cleanup_tabs, width=30).pack(pady=5)
        tk.Button(self.root, text="✈️ Exit", command=self.exit, width=30).pack(pady=5)

    def show_media_tools_menu(self):
        """Display media tools menu"""
        self.clear_window()
        tk.Label(self.root, text="🎇 MEDIA TOOLS 📽️", font=("Arial", 14, "bold"), fg="darkorange").pack(pady=10)
        tk.Label(self.root, text="-----------------------------------", fg="green").pack()
        tk.Button(self.root, text="VIDEOS", command=self.show_video_tools_menu, width=30).pack(pady=5)
        tk.Button(self.root, text="IMAGES", command=self.show_image_tools_menu, width=30).pack(pady=5)
        tk.Button(self.root, text="Media Sorter", command=lambda: djj.run_script_in_tab("djjtb.media_tools.media_sorter", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Button(self.root, text="Playlist Generator", command=lambda: djj.run_script_in_tab("djjtb.media_tools.playlist_generator", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Label(self.root, text="APPS", font=("Arial", 12, "bold"), fg="darkorange").pack(pady=5)
        tk.Label(self.root, text="-----------------------------------", fg="green").pack()
        tk.Button(self.root, text="Photomator", command=lambda: djj.open_app("/Applications/Photomator.app"), width=30).pack(pady=5)
        tk.Button(self.root, text="Pixelmator", command=lambda: djj.open_app("/Applications/Pixelmator Pro.app"), width=30).pack(pady=5)
        tk.Button(self.root, text="DaVinci Resolve", command=lambda: djj.open_app("/Applications/DaVinci Resolve/DaVinci Resolve.app"), width=30).pack(pady=5)
        tk.Button(self.root, text="Wondershare Uniconverter", command=lambda: djj.open_app("/Applications/Wondershare UniConverter 15.app"), width=30).pack(pady=5)
        tk.Button(self.root, text="Handbrake", command=lambda: djj.open_app("/Applications/HandBrake.app"), width=30).pack(pady=5)
        tk.Button(self.root, text="CollageIt 3", command=lambda: djj.open_app("/Applications/CollageIt 3.app"), width=30).pack(pady=5)
        tk.Label(self.root, text="-----------------------------------", fg="green").pack()
        tk.Button(self.root, text="⏪ Back", command=self.show_main_menu, width=30).pack(pady=5)
        tk.Button(self.root, text="⏮️ MAIN MENU", command=self.show_main_menu, width=30).pack(pady=5)

    def show_video_tools_menu(self):
        """Display video tools menu"""
        self.clear_window()
        tk.Label(self.root, text="🎬 VIDEO TOOLS 🎬", font=("Arial", 14, "bold"), fg="darkorange").pack(pady=10)
        tk.Label(self.root, text="-----------------------------------", fg="green").pack()
        tk.Button(self.root, text="Video Re-encoder 📼➡︎📀", command=lambda: djj.run_script_in_tab("djjtb.media_tools.video_tools.video_re-encoder", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Button(self.root, text="Reverse Merge ↪️ ⇔↩️", command=lambda: djj.run_script_in_tab("djjtb.media_tools.video_tools.video_reverse_merge", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Button(self.root, text="Slideshow Watermark 📹 🆔", command=lambda: djj.run_script_in_tab("djjtb.media_tools.video_tools.video_slideshow_watermark", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Button(self.root, text="Cropper 👖➡︎🩳", command=lambda: djj.run_script_in_tab("djjtb.media_tools.video_tools.video_cropper", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Button(self.root, text="Group Merger 📹 🧲", command=lambda: djj.run_script_in_tab("djjtb.media_tools.video_tools.video_group_merger", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Button(self.root, text="Video Splitter 📹 ✂️ ⏱️", command=lambda: djj.run_script_in_tab("djjtb.media_tools.video_tools.video_splitter", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Button(self.root, text="Speed Changer 🐇⬌🐢", command=lambda: djj.run_script_in_tab("djjtb.media_tools.video_tools.video_speed_changer", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Button(self.root, text="Frame Extractor 📹➡︎🌃🌆🎆🎇", command=lambda: djj.run_script_in_tab("djjtb.media_tools.video_tools.video_frame_extractor", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Label(self.root, text="-----------------------------------", fg="green").pack()
        tk.Button(self.root, text="⏪ Back to MEDIA TOOLS", command=self.show_media_tools_menu, width=30).pack(pady=5)
        tk.Button(self.root, text="⏮️ MAIN MENU", command=self.show_main_menu, width=30).pack(pady=5)
        # Start 8-second timer to return to media tools menu
        self.start_timer(8, self.show_media_tools_menu)

    def show_image_tools_menu(self):
        """Display image tools menu"""
        self.clear_window()
        tk.Label(self.root, text="🖼️ IMAGES TOOLS 🖼️", font=("Arial", 14, "bold"), fg="darkorange").pack(pady=10)
        tk.Label(self.root, text="-----------------------------------", fg="green").pack()
        tk.Button(self.root, text="Image Converter 🎞️ ➡︎🌠", command=lambda: djj.run_script_in_tab("djjtb.media_tools.image_tools.image_converter", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Button(self.root, text="Strip Padding 🔲➡︎⬜️", command=lambda: djj.run_script_in_tab("djjtb.media_tools.image_tools.image_strip_padding", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Button(self.root, text="Flip or Rotate ↔️ 🔄", command=lambda: djj.run_script_in_tab("djjtb.media_tools.image_tools.image_flip_rotate", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Button(self.root, text="Collage Creation 🧩 🎇", command=lambda: djj.run_script_in_tab("djjtb.media_tools.image_tools.image_collage_creator", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Button(self.root, text="Resize Images 🩷⬌💓", command=lambda: djj.run_command_in_tab(f"cd {self.project_path}; source djjvenv/bin/activate; export PYTHONPATH=.; python3 -m djjtb.media_tools.image_tools.image_resizer"), width=30).pack(pady=5)
        tk.Button(self.root, text="Slideshow Maker 🎑➡︎📽️", command=lambda: djj.run_script_in_tab("djjtb.media_tools.image_tools.image_slideshow_maker", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Button(self.root, text="Image Pairing ✋🏼 🤲🏼", command=lambda: djj.run_script_in_tab("djjtb.media_tools.image_tools.image_pairing", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Button(self.root, text="Image Padding ◼️➡︎🔳", command=lambda: djj.run_script_in_tab("djjtb.media_tools.image_tools.image_padder", self.venv_path, self.project_path), width=30).pack(pady=5)
        tk.Label(self.root, text="-----------------------------------", fg="green").pack()
        tk.Button(self.root, text="⏪ Back to MEDIA TOOLS", command=self.show_media_tools_menu, width=30).pack(pady=5)
        tk.Button(self.root, text="⏮️ MAIN MENU", command=self.show_main_menu, width=30).pack(pady=5)
        # Start 8-second timer to return to media tools menu
        self.start_timer(8, self.show_media_tools_menu)

    def show_ai_tools_menu(self):
        """Display AI tools menu"""
        self.clear_window()
        tk.Label(self.root, text="🤖 AI TOOLS 🛠️", font=("Arial", 14, "bold"), fg="darkorange").pack(pady=10)
        tk.Label(self.root, text="-----------------------------------", fg="green").pack()
        tk.Button(self.root, text="Prompt Randomizer 📝 🔀", command=lambda: djj.run_command_in_tab(f"source {self.venv_path}; cd {self.project_path}/djjtb/ai_tools/; python3 -m djjtb.media_tools.ai_tools.prompt_randomizer"), width=30).pack(pady=5)
        tk.Button(self.root, text="ComfyUI ☀️ 💻", command=lambda: djj.run_command_in_tab(f"{self.project_path}/djjtb/ai_tools/comfyui_media_processor.command"), width=30).pack(pady=5)
        tk.Button(self.root, text="Merge Loras 👫➡︎🧍🏼‍♂️", command=lambda: os.system(f"source {self.venv_path}; cd {self.project_path}/djjtb/ai_tools; python3 -m djjtb.media_tools.merge_loras.py"), width=30).pack(pady=5)
        tk.Button(self.root, text="Codeformer 😶‍🌫️➡︎😝", command=lambda: djj.run_command_in_tab(f"{self.project_path}/djjtb/ai_tools/run_codeformer.command"), width=30).pack(pady=5)
        tk.Label(self.root, text="-----------------------------------", fg="green").pack()
        tk.Button(self.root, text="⏪ Back", command=self.show_main_menu, width=30).pack(pady=5)
        tk.Button(self.root, text="⏮️ MAIN MENU", command=self.show_main_menu, width=30).pack(pady=5)

    def handle_media_tools(self):
        """Handle media tools submenu"""
        self.show_media_tools_menu()

    def handle_ai_tools(self):
        """Handle AI tools submenu"""
        self.show_ai_tools_menu()

    def handle_quick_tools(self, choice):
        """Handle quick tools"""
        if choice == "3":  # Reverse Image Search
            command = f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.quick_tools.reverse_image_search"
            djj.open_terminal_with_settings(command, "LinkGrabber", "50, 282, 250, 482")
        elif choice == "4":  # Link Grabber
            command = f"source {self.venv_path}; cd {self.project_path}; python3 -m djjtb.quick_tools.link_grabber"
            djj.open_terminal_with_settings(command, "LinkGrabber", "50, 700, 600, 930")
        elif choice == "5":  # Media Info Viewer
            command = f"source {self.venv_path}; cd {self.project_path}/; python3 -m djjtb.quick_tools.media_info_viewer"
            djj.open_terminal_with_settings(command, "LinkGrabber", "50, 80, 250, 280")
        elif choice == "6":  # App Launcher
            os.system(f"source {self.venv_path}; bash {self.project_path}/djjtb/quick_tools/app_launcher.command")
        self.show_main_menu()

    def exit(self):
        """Exit the application"""
        self.clear_window()
        messagebox.showinfo("DJJ Toolbox", "Exiting...")
        self.root.quit()

    def run(self):
        """Main launcher loop"""
        djj.setup_terminal()
        self.show_main_menu()
        self.root.mainloop()

def main():
    launcher = DJJTBLauncherGUI()
    launcher.run()

if __name__ == "__main__":
    main()