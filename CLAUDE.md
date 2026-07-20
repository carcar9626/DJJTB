You are a highly advanced local software refactoring engine built for a workflow designer.
Your primary objective is to modify existing Python scripts cleanly and accurately, organize, enhance and manage the DJJTB repo.

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

## AI Tools Infrastructure

- `djjtb/ai_tools/ai_models` is a symlink to `~/Documents/ai_models` — every `ai_models/...` path below resolves through it.
- **Diagnostics rule:** never `source activate` a tool venv when checking something ad hoc — invoke `<venv>/bin/python3` (or `.../bin/python`) directly by absolute path instead. Activation state doesn't persist across separate shell invocations, so a `source .../activate` in one command and a check in the next silently run against the wrong interpreter.
- **Cleanup status:** this infra has accumulated cruft — some venvs below no longer exist on disk, and several tools that still technically work aren't things I actually use. Confirmed-active list is below; everything else is a cleanup candidate. Work through it incrementally, not in one pass.

### Active (confirmed in current use)

| Tool | Venv python | Script / entry point | Runner in `djjtb/ai_tools/` |
|---|---|---|---|
| FaceFusion | `ai_models/facefusion/ffvenv/bin/python3` | `ai_models/facefusion/facefusion.py` | `facefusion_runner.py`, `run_facefusion.command` |
| CodeFormer | `ai_models/CodeFormer/cfvenv/bin/python3` | `ai_models/CodeFormer/inference_codeformer.py` | `codeformer_runner.py` |
| ComfyUI (server) | `ai_models/ComfyUI_App/ComfyUI/cfuivenv/bin/python3` | `ai_models/ComfyUI_App/ComfyUI/main.py` | `comfyui_runner.command` |
| JoyTag | `ai_models/joytag/jtvenv/bin/python` | in-process ONNX inference, no separate script invoked | `joytag_tagger.py` |
| JoyCaption | `ai_models/joycaption/jcvenv/bin/python3` | runs in-process inside jcvenv | `joycaption_runner.py` |
| Image Caption Generator (Florence) | `ai_models/watermark_remover/wmrmvenv/bin/python` ⚠️ see flag below | self (re-execs into the venv via `os.execve`) | `image_caption_generator.py` |
| Image Finder | — runs in DJJTB's own venv, no separate `ai_models` venv | self | `image_finder.py` |
| Image Tagger | — runs in DJJTB's own venv, no separate `ai_models` venv | self | `image_tagger.py` |
| Open WebUI | — no venv, Docker container (`docker start open-webui`) | — | `open_webui_runner.command` |

### Present, not on the active list — cleanup candidates

Paths resolve on disk, but not in daily use — decide keep/delete per tool, don't assume either way:

- **Watermark Remover — 4 variants, unclear which (if any) is the one to keep**: `watermark_remover_auto.py`, `watermark_remover_ref.py`, `watermark_remover_pkfpl.py`, `watermark_remover_unified.py`. All four point at `ai_models/watermark_remover/wmrmvenv/bin/python`, which resolves. This is the venv Image Caption Generator also borrows (flagged above) — worth resolving both at once.
- **cf_ups_runner.py** (CodeFormer+Upscaler combo) — `ai_models/CodeFormer/cfvenv` + `ai_models/upscalers/upsvenv`, both resolve.
- **codeformer_runner_liveprompt.py** — same venv as `codeformer_runner.py` (`cfvenv`), resolves.
- **upscaler_runner.py** — `ai_models/upscalers/upsvenv/bin/python3`, resolves.
- **gfpgan_runner.py** — `ai_models/GFPGAN/gfvenv/bin/python3` + `inference_gfpgan.py`, resolves.
- **iopaint** — `run_iopaint.command` (own `iovenv`) and `run_iopaint_ff_host.command` (uses `watermark_remover/wmrmvenv` instead) both resolve; unclear which is canonical.
- **AI-Toolkit / Ostris ("ATK")** — `ai_models/ai-toolkit/.venv/bin/python3` + `run_mac.zsh`, resolves.

### Confirmed broken — venv/binary missing entirely on disk

- **ThinkSound** (`thinksound_runner.py`) — `ai_models/thinksound/` doesn't exist. Not wired into `djjtb.py`'s menu.
- **Kohya_ss** (`run_kohya_ss.command`) — `ai_models/kohya_ss/` doesn't exist (only a leftover `kohya_ss_mac_guide.md` remains at `ai_models/` root). Menu entry commented out (`djjtb.py:199,444-445`).
- **RealESRGAN** (`realesrgan_runner.py`) — `ai_models/realesrgan-ncnn-vulkan-20220424-macos/` doesn't exist. Menu entry commented out (`djjtb.py:432-433`).
- **RealSR** (`realsr_runner.py`) — `ai_models/realsr-ncnn-vulkan-20220728-macos/` doesn't exist. Menu entry commented out (`djjtb.py:196`).

### Not applicable — no ai_models venv involved

`merge_loras.py`, `prompt_randomizer.py`, `mask_generator.py`, `vocab_extractor.py`, `djj_vocab_renderer.py`, `vocab_mask_generator.py`, `comfyui/comfyui_batch.py` (HTTP client to the already-running ComfyUI server at `localhost:8188`, doesn't invoke `cfuivenv` itself) — these run entirely in DJJTB's own venv.

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

## Working with me

- I'm a workflow builder, not a traditional coder. Explain the "why" behind
  implementation choices; don't over-explain basics.
- Don't run, execute, or test any script/command without asking me first and
  waiting for a yes. Exception: plain syntax checks (python3 -m py_compile)
  are fine without asking — nothing that touches a venv or executes real logic.
- Prefer surgical find-and-replace diffs over full file rewrites when editing
  existing scripts, unless I ask for a full rewrite.
- Before editing any file, confirm the line count matches what's on disk so
  we know we're both looking at the same version.
  
  
## Current goal
Find similar functions across the scripts and modularize them to utils.py to slim them and work towards refactoring scripts to use centralized I/O via PathManager so results can chain from one script to the next through the launcher and other ad hoc upgrades or adjustments.

## Long Term goal
Make DJJTB a full-on shippable, bankable APP, step by step.