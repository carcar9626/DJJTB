# DJJTB (DJ's Toolbox) — Agent Notes

A personal macOS Python toolbox. ~70 interactive CLI scripts for media (video/image) processing, AI tools (Codeformer, FaceFusion, ComfyUI, JoyTag, RealESRGAN, watermark removal, etc.), and file utilities.

## Layout

- `djjtb.py` — interactive main launcher. ANSI-colored menus; each tool launches in a new Terminal.app tab via AppleScript (`djj.run_script_in_tab`).
- `djjtb/utils.py` — shared utility module imported by **every** script as `import djjtb.utils as djj`. Contains `PathManager`, `get_centralized_media_input`, `get_path_input`, `prompt_choice`, `wait_with_skip`, `what_next`, `apply_skip_list`, and terminal-tab helpers. Also re-exports everything from `djjtb/media_utils.py` (FFmpeg/ffmpeg-python dimension helpers, slideshow/collage builders, XMP helpers) — so `djj.*` works for both.
- `djjtb/media_tools/` — `video_tools/` and `image_tools/` subdirs hold the user-facing scripts.
- `djjtb/ai_tools/` — AI runners. Many of these shell out to external CLIs (ComfyUI, Kohya, FaceFusion, iopaint, etc.) via `*.command` files; some are Python-only.
- `djjtb/quick_tools/`, `djjtb/file_tools/` — standalone utilities.
- `djjtb/helpers/` — one-off dev/migration scripts (Florence fixes, XMP mergers, vlc renamer, kohya guide, push scripts). Not part of the menu.
- Root-level: `requirements.txt` (pinned), `run_djjtb_py.command` (double-click launcher), `DJJTB.app/`, `safetensors_sources.csv`, `lora_metadata_reader.py`, `extract_safetensors_sources.py`.

## Run / Launch

```bash
cd /Users/home/Documents/Scripts/DJJTB
source venv/bin/activate
python3 djjtb.py
```

Run a single tool directly (must be from the venv):
```bash
python3 -m djjtb.media_tools.video_tools.video_group_merger
python3 -m djjtb.quick_tools.reverse_image_search
```

Or double-click `run_djjtb_py.command`.

## Hard-coded paths

- Project root: `/Users/home/Documents/Scripts/DJJTB`
- venv: `~/Documents/Scripts/DJJTB/venv/`
- Output root: `~/Desktop/<script_name>_<timestamp>/` (some tools write to `~/Documents/Scripts/DJJTB_output/<tool>/`)
- Session temp: `/tmp/djjtb_paths.json` — `PathManager` persists last-used paths per script. `path_manager.cleanup()` removes it.
- Boot-launch stamp: `/Users/home/Documents/Scripts/DJJTB_output/grabber_last_launch.txt` — `djjtb.py` auto-launches link/path grabbers on first run after a Mac reboot.
- Skip list: `/Users/home/Documents/Scripts/DJJTB_output/skip_list.txt` — absolute paths and folder-name keywords that `djj.apply_skip_list` filters out during batch walks. Format documented in `djjtb/utils.py:48` and the file's own comments.
- AppleScript terminal profile: `"djjtb"` (some scripts use `"LinkGrabber"`). Bounds default `"100, 200, 728, 1066"`.

## Conventions

- All scripts `import djjtb.utils as djj` and use `djj.prompt_choice`, `djj.get_path_input`, `djj.get_centralized_media_input`, `djj.get_centralized_output_path`, `djj.apply_skip_list`, `djj.setup_logging`, `djj.what_next`. Match this in any new tool.
- Per-script session state goes through `PathManager` (djjtb/utils.py:637), not ad-hoc globals.
- Filenames in menu categories follow `<category>_<toolname>.py`; the launcher dispatches by `djj.run_script_in_tab("djjtb.<dotted.path>.<module>", ...)`.
- No tests, no linter, no typecheck, no CI, no pre-commit. Don't add them speculatively.
- Heavy AI deps (torch, gfpgan, realesrgan, basicsr, transformers, selenium, PyQt5) are pinned in `requirements.txt` — install is slow and not always necessary; only the tool you run needs them.

## macOS / Terminal.app quirks

- `djj.run_script_in_tab` uses `osascript` + `keystroke "t" using command down` to open a new tab and inject a `source venv && cd $project && python3 -m …` command. Requires Terminal.app (not iTerm) and Accessibility permission for the controlling process.
- `djj.setup_terminal` resizes the front window and applies a Terminal profile. Don't invoke it from inside an already-launched tool unless you want to clobber the user's window.
- `djj.return_to_djjtb` / `djj.switch_to_terminal_tab` assume tab 1 is the main menu — set up that way when launching.
- Several tools require FFmpeg on PATH: `brew install ffmpeg`. ffmpeg-python is the wrapper; subprocess calls to `ffmpeg` are also used directly.

## Output / log locations

- Per-script logs: `djjtb/Logs/<script>_log.csv` (some scripts) and `<output_path>/<script>_log.txt` via `djj.setup_logging`.
- Tool-specific output dirs under `~/Documents/Scripts/DJJTB_output/` include `comfyui_batch_logs/`, `link_grabber/`, `path_grabber/`, `link_scraper/`, `media_info_extractor/`, `image_tagger/`, `watermark_remover/`, `facefusion_test_targets/`, `auto_subfolder/`, `for_PLAYLIST/`, plus `*link.txt` files written by the grabbers.