# DJJTB - DJ's Toolbox

## Overview

DJJTB (DJ's Toolbox) is a comprehensive Python-based media processing suite with an interactive terminal interface. This repository contains 70 scripts for video processing, image manipulation, AI tools, and automation utilities.

## 🚀 Quick Start

```bash
# Clone and setup
cd /Users/home/Documents/Scripts/DJJTB
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Launch main interface
python3 djjtb.py
```

## 📁 Project Structure

```
DJJTB/
├── djjtb.py              # Main launcher script
├── djjtb/
│   ├── utils.py          # Core utility functions
│   ├── media_tools/      # Video & image processing
│   ├── ai_tools/         # AI-powered utilities
│   └── quick_tools/      # Standalone tools
└── venv/                 # Python virtual environment
```

## 🎛️ Main Components

### djjtb.py
Main DJJTB launcher with interactive menu system for media and AI tools

**Features:**
- Interactive menu system with color-coded interface
- Terminal tab management for parallel processing
- Integrated app launcher for media applications
- Centralized path and session management

### app_launcher.py
Python script: app_launcher

**Features:**
- Interactive menu system with color-coded interface
- Terminal tab management for parallel processing
- Integrated app launcher for media applications
- Centralized path and session management

### app_launcher.command
App Launcher: Launch applications with organized submenus Updated: July 20, 2025

**Features:**
- Interactive menu system with color-coded interface
- Terminal tab management for parallel processing
- Integrated app launcher for media applications
- Centralized path and session management

### utils.py
DJJTB utility functions for UI, file handling, terminal management, and common operations

**Key Functions:**
- **UI/Input:** get_int_input, get_centralized_media_input, get_path_input, subfolder_from_input, prompt_choice
- **File Handling:** get_centralized_media_input, save_paths, load_paths, collect_media_files, get_path_input
- **Terminal Management:** setup_terminal, run_script_in_tab, switch_to_terminal_tab, open_terminal_with_settings, cleanup_tabs

## 🎬 Video Tools

| Tool | Description | Key Features |
|------|-------------|-------------|
| **Reverse Merge** | Video processing tool with FFmpeg integration | Video merging |
| **Splitter Copy** | Video processing tool with FFmpeg integration | Media processing |
| **Re-Encoder** | Video processing tool with FFmpeg integration | Media processing |
| **Cropper Beta** | Video cropping tool with custom dimensions | Media processing |
| **Cropper** | Video cropping tool with custom dimensions | Media processing |
| **  Init  ** | Video processing tool with FFmpeg integration | Media processing |
| **Frame Extractor** | Video processing tool with FFmpeg integration | Media processing |
| **Slideshow Watermark** | Video processing tool with FFmpeg integration | Media processing |
| **Group Merger** | Video merging tool with group processing capabilities | Batch processing, Video merging |
| **Splitter** | Video processing tool with FFmpeg integration | Media processing |
| **Speed Changer** | Video processing tool with FFmpeg integration | Interactive UI |
| **Gif Converter** | Video format conversion tool with batch processing | Media processing |

## 🖼️ Image Tools

| Tool | Description | Key Features |
|------|-------------|-------------|
| **Converter** | Image format conversion tool with batch processing | PIL/Pillow |
| **Resizer** | Image resizing tool with aspect ratio preservation | PIL/Pillow |
| **Slideshow Maker** | Image processing tool with FFmpeg integration | PIL/Pillow |
| **Pairing** | Image processing tool with FFmpeg integration | PIL/Pillow |
| ** Init  ** | Image processing tool with FFmpeg integration | Image processing |
| **Collage Creator** | Image processing tool with FFmpeg integration | PIL/Pillow |
| **Padder** | Image processing tool with FFmpeg integration | PIL/Pillow |
| **Flip Rotate** | Image processing tool with FFmpeg integration | PIL/Pillow |
| **Strip Padding** | Image processing tool with FFmpeg integration | PIL/Pillow |

## 🤖 AI Tools

| Tool | Description | Technology |
|------|-------------|------------|
| **  Init  ** | Python script: __init__ | AI/ML |
| **Comfyui Media Processor** | ComfyUI Launcher: Run ComfyUI in a new Terminal tab Created: July 12, 2025 | ComfyUI |
| **Codeformer Runner** | Python script: codeformer_runner | AI/ML |
| **Merge Loras** | Python script: merge_loras | PyTorch, LoRA |
| **Prompt Randomizer** | Python script: prompt_randomizer | AI/ML |
| **Codeformer Runner Copy** | Python script: codeformer_runner copy | AI/ML |
| **Randomize Prompts** | Shell script: randomize_prompts | AI/ML |
| **Generate Attribute Files** | Python script: generate_attribute_files | AI/ML |
| **Prompt Randomizer** | Python script: prompt_randomizer | AI/ML |

## ⚡ Quick Tools

| Tool | Description | Usage |
|------|-------------|-------|
| **Reverse Image Search** | Image processing tool with FFmpeg integration | `python3 -m djjtb.quick_tools.reverse_image_search` |
| **App Launcher** | Python script: app_launcher | `python3 -m djjtb.quick_tools.app_launcher` |
| **Link Grabber Copy** | Python script: link_grabber copy | `python3 -m djjtb.quick_tools.link_grabber copy` |
| **Image Finder** | Image processing tool with FFmpeg integration | `python3 -m djjtb.quick_tools.image_finder` |
| **App Launcher** | App Launcher: Launch applications with organized submenus Updated: July 20, 2025 | `python3 -m djjtb.quick_tools.app_launcher.command` |
| **Media Info Viewer** | Media processing tool with FFmpeg integration | `python3 -m djjtb.quick_tools.media_info_viewer` |
| **Link Grabber** | Python script: link_grabber | `python3 -m djjtb.quick_tools.link_grabber` |
| **  Init  ** | Python script: __init__ | `python3 -m djjtb.quick_tools.__init__` |
| **Plist Converter** | Python script: plist_converter | `python3 -m djjtb.quick_tools.plist_converter` |
| **File Identifier** | Enhanced File Identifier Tool | `python3 -m djjtb.quick_tools.file_identifier` |
| **Add Root Dir Prefix** | Python script: add_root_dir_prefix | `python3 -m djjtb.quick_tools.add_root_dir_prefix` |
| **Link Grabber** | Python script: link_grabber | `python3 -m djjtb.quick_tools.Linkgrabber.Scripts.link_grabber` |
| **Link Grabber Grokmod** | Python script: link_grabber_GrokMod | `python3 -m djjtb.quick_tools.Linkgrabber.Scripts.link_grabber_GrokMod` |

## 📦 Installation & Dependencies

### System Requirements
- macOS (optimized for Terminal.app integration)
- Python 3.8+
- FFmpeg (for video processing tools)

### Python Dependencies
```bash
pip install ( AutoModelForCausalLM AutoTokenizer BeautifulSoup By DND_FILES Dict Image ImageChops ImageFilter List Optional Options PIL Path PathManager PngImagePlugin PyQt5 QApplication QClipboard QFileDialog QHBoxLayout QInputDialog QLabel QMessageBox QPalette QPixmap QPushButton QUrl QVBoxLayout QWidget Qt TkinterDnD Tuple WebDriverWait arch argparse asdict bash break bs4 case cat cd close collections csv cv2 dataclass dataclasses datetime defaultdict delay echo elif end eval exit expected_conditions as EC export filedialog find function git glob load_file magic messagebox mimetypes mkdir open osascript pandas pandas as pd pipeline print_error printf pyenv pyperclip python3 random read repeat requests return safetensors save_file selenium set shlex shutil simpledialog sleep source subprocess  # For window resizing tell threading tkinter tkinter as tk tkinterdnd2 torch traceback transformers typing urllib urlparse utils as djj webbrowser webdriver
```

### FFmpeg Installation
```bash
# Using Homebrew
brew install ffmpeg
```

## 🎯 Usage

### Main Interface
```bash
# Launch the main DJJTB interface
cd /Users/home/Documents/Scripts/DJJTB
source venv/bin/activate
python3 djjtb.py
```

### Direct Tool Access
```bash
# Run individual tools directly
python3 -m djjtb.media_tools.video_tools.video_group_merger
python3 -m djjtb.quick_tools.reverse_image_search
```

### Integration with Utils
All DJJTB scripts use the centralized utils module:
```python
import djjtb.utils as djj

# Common patterns
choice = djj.prompt_choice("Select option", ['1', '2', '3'])
media_files = djj.get_centralized_media_input("script_name")
output_path = djj.get_centralized_output_path("script_name")
```

## ✨ Key Features

- **🖥️ Terminal Integration**: Optimized for macOS Terminal.app with tab management
- **🎨 Color-coded Interface**: Enhanced UX with consistent color schemes
- **📁 Smart Path Management**: Centralized input/output handling with session persistence
- **⚡ Parallel Processing**: Multi-tab execution for batch operations
- **🔄 Session Management**: Automatic cleanup and tab organization
- **🎛️ Interactive Menus**: Intuitive navigation with skip options
- **📱 App Integration**: Launch external media apps from within DJJTB

## 📜 Additional Scripts

| Script | Type | Description |
|--------|------|-------------|
| `__init__.py` | Python | Python script: __init__ |
| `readme_generator.py` | Python | Main DJJTB launcher with interactive menu system for media and AI tools |
| `run_djjtb_py.command` | Shell | Shell script: run_djjtb_py |
| `djjtb_c.py` | Python | Python script: djjtb_c |
| `djjtb_input_handling.py` | Python | Python script: djjtb_input_handling |
| `djjtb_gui.py` | Python | Main DJJTB launcher with interactive menu system for media and AI tools |
| `djjtb_cd_beta1.py` | Python | Main DJJTB launcher with interactive menu system for media and AI tools |
| `reverse_image_search_tkd.py` | Python | Image processing tool with FFmpeg integration |
| `djjtb.command.bak` | Shell | Media Processor: Run Video or Image Processor Updated: July 11, 2025 |
| `run_codeformer.command` | Shell | Clear the terminal for a clean interface |
| `djjtb.command` | Shell | Media Processor: Run Video or Image Processor Updated: July 11, 2025 |
| `utils_new.py` | Python | DJJTB utility functions for UI, file handling, terminal management, and common operations |
| `__init__.py` | Python | Python script: __init__ |
| `utils copy.py` | Python | DJJTB utility functions for UI, file handling, terminal management, and common operations |
| `metadata_injector.py` | Python | Media processing tool with FFmpeg integration |
| `media_sorter.py` | Python | Media processing tool with FFmpeg integration |
| `__init__.py` | Python | Media processing tool with FFmpeg integration |
| `metadata_tool.py` | Python | Media processing tool with FFmpeg integration |
| `playlist_generator.py` | Python | Media processing tool with FFmpeg integration |
| `update_tools.py` | Python | Python script: update_tools |
| `push_djjtb_force.command` | Shell | Ensure djjvenv is ignored Remove djjvenv from git tracking if already added before |
| `push_djjtb.command` | Shell | Shell script: push_djjtb |
| `replace_decor_lines.py` | Python | Python script: replace_decor_lines |
| `scan_djj_usage.py` | Python | Python script: scan_djj_usage |
| `Help_ChatTemplate.py` | Python | Python script: Help_ChatTemplate |

## 🛠️ Development

### Project Structure Guidelines
- All media tools import `djjtb.utils as djj`
- Use centralized input/output functions from utils
- Follow consistent UI patterns with color coding
- Implement proper error handling and logging
- Support both single and batch processing modes

### Adding New Tools
1. Create script in appropriate category folder
2. Import and use `djjtb.utils` for UI consistency
3. Add menu entry in main launcher
4. Follow naming convention: `category_toolname.py`

---
*Generated with DJJTB README Generator*
