# DJJ Toolbox (DJJTB)

DJJ Toolbox (DJJTB) is a Python-based command-line application for macOS, designed to streamline media processing tasks. It provides a suite of tools for video and image manipulation, AI-driven processing, and quick utilities, all accessible through an intuitive terminal-based menu interface. Whether you're re-encoding videos, resizing images, or launching related applications, DJJTB simplifies workflows for media enthusiasts and professionals.

## Features

- **Video Tools**: Re-encode, merge, crop, split, adjust speed, watermark slideshows, or extract frames from videos.
- **Image Tools**: Convert, resize, rotate, flip, pad, strip padding, create collages, pair images, or generate slideshows.
- **AI Tools**: Randomize prompts, merge LoRAs, run Codeformer, or process media with ComfyUI.
- **Quick Tools**: Perform reverse image searches, grab links, view media info, or find images using AI-driven search.
- **App Launcher**: Quickly open media-related applications like Photomator, Pixelmator, DaVinci Resolve, and more.
- **Terminal-Based Interface**: Navigate through a clean, color-coded menu system with tab management for a seamless experience.
- **Path Management**: Centralized input/output path handling with support for folders, files, and subfolders.
- **Extensibility**: Modular design allows easy addition of new tools.

## Prerequisites

- **Operating System**: macOS (due to AppleScript and `open` command usage)
- **Python**: Version 3.10 or higher
- **Terminal**: macOS Terminal.app (iTerm2 may require adjustments for AppleScript)
- **FFmpeg**: Required for video processing tools (install via Homebrew: `brew install ffmpeg`)

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/djjtb.git
   cd djjtb
   ```

2. **Set Up a Virtual Environment**:
   ```bash
   python3 -m venv djjvenv
   source djjvenv/bin/activate
   ```

3. **Install Dependencies**:
   Install the required Python packages listed in `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify FFmpeg Installation**:
   Ensure FFmpeg is installed and accessible:
   ```bash
   ffmpeg -version
   ```
   If not installed, run:
   ```bash
   brew install ffmpeg
   ```

5. **Set Project Path**:
   Update the `project_path` in `djjtb/launcher.py` if your project directory differs from `/Users/home/Documents/Scripts/DJJTB`:
   ```python
   self.project_path = "/path/to/your/djjtb"
   ```

## Usage

1. **Launch the Toolbox**:
   Activate the virtual environment and run the launcher:
   ```bash
   source djjvenv/bin/activate
   cd /path/to/djjtb
   python3 -m djjtb.launcher
   ```

2. **Navigate the Menu**:
   - Use the main menu to select categories: Media Tools, AI Tools, or Quick Tools.
   - Choose specific tools or apps within submenus (e.g., Video Re-encoder, Image Finder, Photomator).
   - Enter numbers to select options, or use `0`/`00` to go back or return to the main menu.
   - Press `c` to clean up extra terminal tabs or `x` to exit.

3. **Tool Workflow**:
   - Most tools prompt for input paths (files or folders) and output locations.
   - Follow on-screen prompts to configure options (e.g., include subfolders, copy/move files).
   - Use `Ctrl+C` to interrupt a tool and return to the main menu (closes the tool’s tab).
   - Select “What Next?” options at the end of each tool’s run: Again, Return to DJJTB, or Exit.

4. **Examples**:
   - **Image Finder**: Run an AI-driven image search:
     ```
     Main Menu > 7. Image Finder
     Enter folder path, search term, and choose to copy/move results to an output folder.
     ```
   - **Video Re-encoder**: Re-encode videos to a different format:
     ```
     Main Menu > 1. Media Tools > 1. Videos > 1. Video Re-encoder
     Select input videos and output settings.
     ```
   - **App Launcher**: Open Photomator:
     ```
     Main Menu > 1. Media Tools > 5. Photomator
     ```

## Dependencies

The following Python packages are required (see `requirements.txt` for versions):
- `beautifulsoup4`: Web scraping for link grabbing
- `certifi`, `charset-normalizer`, `idna`, `urllib3`, `requests`: HTTP requests for web tools
- `click`: Command-line interface utilities
- `decorator`, `six`, `typing_extensions`: General Python utilities
- `ffmpeg-python`, `imageio`, `imageio-ffmpeg`, `moviepy`: Video and image processing
- `numpy`, `opencv-python`, `pillow`: Image manipulation
- `pandas`, `python-dateutil`, `pytz`, `tzdata`: Data handling
- `pyperclip`: Clipboard operations
- `PyQt5`, `PyQt5-Qt5`, `PyQt5_sip`: GUI components (if used by tools)
- `scenedetect`: Video scene detection
- `tqdm`: Progress bars for processing
- `python-dotenv`: Environment variable management
- `proglog`: Logging for media processing

Install all dependencies with:
```bash
pip install -r requirements.txt
```

## Project Structure

```
djjtb/
├── djjvenv/                    # Virtual environment
├── djjtb/
│   ├── launcher.py             # Main launcher script
│   ├── utils.py               # Utility functions (path management, terminal control)
│   ├── media_tools/
│   │   ├── video_tools/       fundamentais Video processing scripts (e.g., video_re-encoder.py)
│   │   ├── image_tools/       # Image processing scripts (e.g., image_converter.py)
│   │   ├── media_sorter.py    # Media sorting utility
│   │   ├── playlist_generator.py # Playlist creation utility
│   ├── ai_tools/              # AI processing scripts (e.g., prompt_randomizer.py)
│   ├── quick_tools/           # Quick utilities (e.g., image_finder.py)
├── requirements.txt           # Python dependencies
```

## Contributing

Contributions are welcome! To add new tools or improve existing ones:
1. Fork the repository.
2. Create a new script in the appropriate directory (`media_tools`, `ai_tools`, or `quick_tools`).
3. Update `launcher.py` to include the new tool in the menu.
4. Submit a pull request with your changes.

## Notes

- **macOS-Specific**: The toolbox uses AppleScript for terminal tab management and `open` commands for app launching, making it macOS-centric. For other platforms, modify `utils.py` (e.g., replace AppleScript with platform-specific commands).
- **Path Configuration**: Ensure paths in `launcher.py` and `utils.py` match your system’s directory structure.
- **Logging**: Tools log to files in output directories (e.g., `script_name_log.txt`) for debugging.
- **Ctrl+C Handling**: Pressing `Ctrl+C` in any tool closes the tool’s tab and returns to the main menu, preserving terminal cleanliness.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details (create one if needed).

## Contact

For issues, feature requests, or questions, open an issue on the GitHub repository or contact [your contact info].