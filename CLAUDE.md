You are a highly advanced local software refactoring engine built for a workflow designer.
Your primary objective is to modify existing Python scripts cleanly and accurately, organize, enhance and manage the DJJTB repo.

# DJJTB (DJ's Toolbox) — Agent Notes

A personal macOS Python toolbox. ~70 interactive CLI scripts for media (video/image) processing, AI tools (Codeformer, FaceFusion, ComfyUI, JoyTag, RealESRGAN, watermark removal, etc.), and file utilities.

## Layout

- `djjtb.py` — interactive main launcher. ANSI-colored menus; each tool launches in a new Terminal.app tab via AppleScript (`djj.run_script_in_tab`).
- `djjtb/utils.py` — shared utility module imported by **every** script as `import djjtb.utils as djj`. Contains `PathManager`, `get_centralized_media_input`, `get_path_input`, `prompt_choice`, `wait_with_skip`, `what_next`, `apply_skip_list`, and terminal-tab helpers. Also re-exports everything from `djjtb/media_utils.py` (FFmpeg/ffmpeg-python dimension helpers, slideshow/collage builders, XMP helpers) — so `djj.*` works for both.
- `djjtb/media_tools/` — `video_tools/` and `image_tools/` subdirs hold the user-facing scripts.
  - `image_slideshow_maker.py` — **known gap, not yet fixed, found during djjtb-suite's web conversion (2026-07-30):** the CLI's "create separate slideshows per parent folder?" prompt is only ever asked when input mode is multi-path or txt-file (modes 2/3) — folder-path input (mode 1) always produces one combined slideshow, even when "include subfolders?" is answered yes, with no per-folder option offered at all. This is a real usability gap: someone who points the tool at a parent folder with subfolders and wants one slideshow per subfolder currently has no way to get that from folder-path mode, only by manually re-running per subfolder or switching to multi-path mode. The underlying `group_images_by_parent_folder()` helper already exists and needs no change — this is purely a missing prompt in `main()`'s folder-path branch (mirror the same "per-folder?" question already asked for modes 2/3, gated behind "include subfolders? yes"). Not fixed yet since this was flagged from the djjtb-suite side, not requested as DJJTB work in this session — pick up next time DJJTB itself is being worked on.
  - `image_webp_to_mp4.py` consolidates what used to be 3 near-duplicate scripts: itself (naive first-frame-only FPS detection), `image_webp_to_mp4_auto_30fps.py` (multi-frame FPS averaging + detects fake 100ms-placeholder "metadata" from browser-resaved WebPs), and `webp_anim_to_mp4.py` (hardcoded 25fps, external `anim_dump` binary, no djj conventions). The current file merges in the better averaged-FPS detection, adds even-dimension padding before the `yuv420p` ffmpeg encode (previously hard-failed on odd-dimension sources), and mirrors subfolder structure in output (previously same-named files from different subfolders could overwrite each other). The other two are archived in `djjtb/old_versions/`.
  - `video_slideshow_watermark.bak20260420.py` archived to `djjtb/old_versions/` — dated backup of `video_slideshow_watermark.py` predating the `get_join_dimensions`/`join_image_video` extraction into `media_utils.py`; fully subsumed by the current file, confirmed via diff before archiving.
  - `video_processor.py` consolidates 3 single-operation scripts that shared the same collect→prompt→batch-ffmpeg→summary shape: `video_re-encoder.py` (codec change), `video_speed_changer.py` (playback speed via setpts/atempo), `video_cropper.py` (auto-detect border trim or manual 16:9/9:16 crop-to-fit) — same pattern as `image_processor.py` for images. Top-level mode menu dispatches to the three; shared video collection, audio-option prompt, and per-mode logging (`djjtb/logs/video_processor_<mode>_log.txt`, append mode, run-start marker — the new target logging convention, not the old overwrite-beside-output style the originals used). Fixed a latent bug in the process: `video_cropper.py`'s "add silent track" audio option placed `-an` before an `anullsrc` input with no `-map`, which silently produced no audio at all; the merged version uses the already-correct `djj.get_audio_options()` (already used by `video_re-encoder.py`) instead, verified with a real test file that the silent track is now actually present. `video_speed_changer.py` also wasn't following DJJTB conventions (hand-rolled `prompt_choice`/`setup_logging`/path cleaning instead of `djj.*`) — fixed by folding into the shared script. All three originals archived to `djjtb/old_versions/`. `djjtb.py`'s Video Tools menu renumbered (10 entries → 8) to match. Follow-up (2026-07-27, for djjtb-suite's web conversion): unlike `video_reverse_merge.py`'s `reverse_and_merge()`, this file's three modes never had a standalone pure per-video function — the ffmpeg command-building lived inline inside each `run_*`'s for-loop, interleaved with prompts/progress-printing/logging. Extracted `reencode_one()`, `speed_change_one()`, and `crop_one()` (plus a new `CropDetectionError` for the border-autodetect-failed case) so djjtb-suite's backend can import and call the same per-video logic instead of duplicating it, matching the `reverse_and_merge()` precedent. Pure extraction, zero behavior change — `run_reencode`/`run_speed_change`/`run_crop` now just call these and keep all prompting/looping/printing/CSV-logging themselves. Verified via direct smoke test (synthetic ffmpeg-generated test video, all 3 modes) before/after, plus `py_compile`. In passing, found a pre-existing (not introduced here, not fixed here) bug in `build_crop_filter()`'s "2.1"/"2.2" (Crop to Fit) math: when the source is already narrower than the target aspect (e.g. a 4:3 source under 16:9 mode), `target_w` comes out larger than the source width, producing a negative offset and an ffmpeg failure — spawned as a separate follow-up task, not addressed in this pass.
  - `video_frame_bridge.py` (placeholder name, easy to rename later) pairs `video_frame_extractor.py` (video → frames, interval or evenly-spread-count extraction) and `image_video_compiler.py` (frames → video, with per-subfolder batch compiling and 3 audio modes) under one mode menu — these are inverse operations of the same video↔image-sequence bridge, not a code-shape match like `video_processor.py`'s merge, so each mode keeps its own input-collection/processing logic verbatim; only the menu, header, and per-mode append-mode logging (`djjtb/logs/video_frame_bridge_<extract|compile>_log.txt`) are shared. Added logging to the compile side, which previously had none. Both modes (including subfolder-batch compile and both extraction sub-modes) verified against real ffmpeg-generated test video/images before archiving the two originals to `djjtb/old_versions/`. `djjtb.py`'s Video Tools menu now 7 entries. Follow-up (2026-07-28, djjtb-suite conversion): unlike `image_video_compiler.py`'s side, which was already a clean pure `compile_images_to_video()` (imported unchanged, no djjtb-suite touch needed), the extraction side's `extract_frames_interval()`/`extract_frames_count()` had the same problem `video_processor.py`'s three modes had — per-video ffmpeg logic inline in the loop, no standalone function. Extracted `extract_frames_interval_one()`/`extract_frames_count_one()` the same way (pure, additive, `logger` optional). The interval mode's one interactive branch (confirm before extracting 3000+ images from a single video) became an `allow_large` param — the pure function returns `status="skipped_large"` without touching ffmpeg when the estimate exceeds 3000 and `allow_large` is False, and the CLI wrapper still prompts and retries with `allow_large=True` exactly as before, zero behavior change. Verified via direct smoke test (real test video, both extraction modes, the large-batch skip path, and `compile_images_to_video()` unchanged) plus `py_compile`. Caught and fixed one real slip during the extraction itself: an early `nb_frames == 0` guard in `extract_frames_count()`'s wrapper had dropped the original's `logger.error(...)` call — restored before verifying, but a reminder to diff every extraction this carefully, not just the happy path.
  - `video_group_merger.py` (kept, not merged — a "proud of" custom workflow, so this was an in-place trim, not a consolidation) — removed dead `collect_videos_recursive()` (defined, never called) and an unused `import logging`; hoisted a 3×-duplicated video-extensions tuple to one module constant; extracted 3 pairs of byte-identical ffmpeg command blocks inside `process_video_for_sizing()` (bg+overlay compositing, crop+scale, scale+pad) into shared helpers, roughly halving that function with zero behavior change — verified against real test clips across all 4 sizing paths (crop, crop-fallback, `_blur`, `_pad`) before and after. Also fixed a real bug: the "2. Copy streams (faster, may freeze)" merge option never worked — `needs_processing` (from a `sizing_method == 'simple'` check that's never actually reachable) forced the final concat to always re-encode regardless of the user's choice. Fixed so `use_reencode` alone controls the final concat step; confirmed working via file-size/determinism check (stream-copy output is now byte-identical across runs, distinct from the differently-sized re-encoded output). A black-frame/freeze issue in this script's merges was separately investigated (couldn't reproduce with synthetic test clips across several pipeline variants — plain concat, with audio, with the blur/overlay compositing; leading hypothesis is VFR source footage being forced to CFR, unconfirmed) — parked until it recurs with real source files to test against.
  - `video_reverse_merge.py` (kept, not merged — also "proud of," in-place trim only) — removed dead `collect_videos_from_paths()` (never called; `main()`'s multi-path input mode uses `djj.get_multifile_input()` instead) and the now-dead `clean_path()` that only that dead function referenced; hoisted a 3×-duplicated video-extensions tuple to one module constant. `reverse_and_merge()` itself untouched (explicitly protected workflow logic) — verified with real test clips via both input modes before/after. Follow-up: user confirmed the audio-desync fix — ported `get_atempo_chain()` in from `video_processor.py` (now duplicated across the two files; a future consolidation candidate) and swapped it in for the old single-`atempo` string, scoped strictly to the `audio_choice == '1'` branch — `vf_filter`/the rest of `reverse_and_merge()`'s video path is untouched. For in-range speeds (0.5–2.0) the chain collapses to the exact same single `atempo=<speed>` string as before, so no behavior change there; for out-of-range speeds (up to the 10.0 max `ask_speed_factor()` allows) audio now actually tracks the sped-up video instead of silently staying at 1x. Verified with real test clips at both an out-of-range speed (3.0x — confirmed audio/video durations now match) and an in-range speed (1.5x — confirmed unchanged).
  - `video_slideshow_watermark.py` (1015 lines, the largest script in the toolbox, kept as-is — "proud of," in-place trim only) — removed dead `get_video_dimensions()` compatibility shim (nothing references it anywhere in the repo) and hoisted two video/image-extension tuples, each copy-pasted identically **10 times** across the ten `process_*_folder`/`process_*_flat` functions, into module constants `VIDEO_EXTS`/`IMAGE_EXTS`. Also fixed a confirmed real bug: `process_flat_mode()` (Mode 1, Slideshow + Watermark, flat-folder path) referenced an undefined `temp_dir` in a stray `shutil.rmtree()` call — a copy-paste leftover from the Collage+Join processors that doesn't apply here (this pipeline never creates a temp dir). Reproduced the crash directly: it fired right after successfully creating each watermarked video, which meant in a multi-video flat-mode batch **only the first video ever got processed** — the crash killed the script before it could loop to video 2. Confirmed fix with a real 2-video batch: both videos now complete instead of the run dying after the first. All of the above (including the pre-existing subfolder mode, unaffected by the bug) verified against real ffmpeg renders. The other 9 processing functions (`process_folder`, all Slideshow-Only/Join/Slideshow+Join/Collage+Join variants) were left untouched beyond the constant hoist.
  - `video_splitter.py` (deprioritized script — user has planned enhancements for later, this pass was dedupe/bugfix only) — removed unused `import time`/`import logging` (djj.setup_logging is used instead of the raw module) and hoisted a 2×-duplicated video-extensions tuple to `VIDEO_EXTENSIONS`. Extracted the near-identical ffmpeg-command-building block from both `split_video_by_duration()` and `split_video_by_portions()` into one shared `build_split_cmd()` helper — same audio-choice branching, just no longer copy-pasted. Fixed two real bugs: (1) the end-of-run `djj.prompt_open_folder(output_dir)` call relied on `output_dir` leaking out of a `for output_dir in sorted(output_dirs):` loop a few lines above — if `output_dirs` ended up empty (all videos failing before producing output), this crashed with `NameError`; moved the call inside the `if output_dirs:` branch so it's only ever reached when the variable is guaranteed to exist, with identical folder-selection behavior in the working case. (2) `split_video_by_portions()`'s outer exception handler called `logger.error(...)`, but `logger` is only assigned partway through the `try` block — a failure before that point (e.g. `mkdir`) would crash the crash-handler itself, masking the real error; guarded with `logger = None` initialized before the `try` and an `if logger:` check. Verified both split modes (duration-based and portion-based, including the silent-audio-track path) end-to-end against a real test video before/after.
  - `video_splitter.py` Mode 3 "By Scene Detection (auto)" added — the enhancement idea behind deprioritizing this script in the first place. Origin: the user's actual first-ever script (`~/Documents/Scripts/process_video_with_progress_final17.py`, outside the repo, untouched, kept as-is for sentimental reasons) auto-split videos at PySceneDetect scene boundaries but never worked reliably (wrong/misaligned segments, black stretches). Diagnosed properly before writing anything: the ffmpeg splitting mechanism itself is accurate (verified with a synthetic 3-color test video — exact requested time range extracted correctly); the real problem is `ContentDetector`'s naive frame-difference algorithm exploding fast-cut montage footage (e.g. a "GRWM quick outfit-change" Instagram clip) into dozens of sub-second fragments, confirmed by pulling actual frames from a real merged-Instagram-clips test file the user provided. Swapping to PySceneDetect's modern `AdaptiveDetector` alone didn't fix it (nearly identical output on the pathological stretch) — the fix that actually worked is a post-detection merge pass: any detected scene shorter than a user-set minimum (default/tested at 2.0s) gets folded into its neighbor, which took a 19-scene result (15 of them under 1.5s, crammed into 11 seconds) down to 8 usable scenes without disturbing the two legitimate long segments. `detect_scenes()` and `split_video_by_scenes()` reuse the existing `build_split_cmd()` helper from the dedupe pass, so this added only ~100 lines (314 → 427) rather than duplicating ffmpeg logic — not a rewrite of the ancient script, a fresh implementation matching this file's existing two-mode pattern. `scenedetect`/`numpy` were already pinned in `requirements.txt`. Verified end-to-end through the actual wired script (not just a standalone prototype) against the user's real test video: 8 clips, correct durations, zero black frames (checked via `blackdetect` on every clip), audio preserved.
- `djjtb/ai_tools/` — AI runners. Many of these shell out to external CLIs (ComfyUI, Kohya, FaceFusion, iopaint, etc.) via `*.command` files; some are Python-only.
  - `djjtb/ai_tools/smart_crop_runner.py` (new, 2026-07-31) — subject-aware batch crop, built to close the gap Photomator's "ML Crop" left for the user's single-subject fashion/influencer-style AI generations (mostly 3:4 source, most-used target 8:9 — "half of 16:9"). Detection is YOLOX-l (COCO person class; weights copied from an existing ComfyUI model cache, no re-download needed) run via one batched subprocess call into a new dedicated venv, `ai_models/smart_crop/scvenv` — kept separate rather than reusing DJJTB's own venv because that venv's `onnxruntime-silicon` pin is already broken against its numpy 2.x (confirmed broken, not assumed; likely dead weight from an earlier setup). Same two-venv split as `cf_ups_runner.py`: the 216MB model + onnxruntime stay isolated in `scvenv`, everything else (crop math, batching, presets, I/O, logging) runs in DJJTB's own venv. `retinaface_10g.onnx`/`yoloface_8n.onnx` were also found already present (`ai_models/facefusion/.assets/models/`) as a possible future face-anchored headroom refinement, not used in v1. Crop math: largest window of the target AR that fits the source image, centered on the detected person bbox + 15% margin, falling back to plain center-crop when nothing's detected — deliberately centroid-based, not head/foot-anchored: a head/foot-anchoring variant was built and tested but reverted same-session after real-batch user review showed the simpler centroid approach framed the actual dataset better (full-body standing/kneeling shots are a known, accepted edge case the user handles manually rather than something worth the tool chasing). Validated end-to-end against a real 93-image non-recursive folder batch: 93/93 succeeded, 0 failures, 0 center-crop fallbacks (YOLOX found a person in every image), confidence 0.77–0.97. Optional post-crop resize asks for a single longest-edge pixel value rather than a general width/height/stretch/pad menu — since the crop is already locked to the chosen AR, one number determines both exact target dimensions with no distortion risk (verified: AR 8:9 + longest edge 1080 → exactly 960×1080).
  - `djjtb/ai_tools/hermes/` — Nous Research's Hermes Agent (separate install at `~/.hermes`, not part of the `ai_models` symlink tree; setup/config reference lives in the sibling `DJJIF` project's `HERMES_SETUP.md`, not in this repo — deliberate code/infra split). `hermes_core.py` holds all shared, non-interactive logic (gateway process control, `docker_volumes` mount editing, log parsing/dedup, pipeline-phase detection, real-file-count completion verification) — nothing in it prompts or prints. `hermes_helper.py` (moved here 2026-07-25 from a flat `djjtb/ai_tools/hermes_helper.py`) is the menu-dispatched status/control submenu plus the standalone Add/Remove Working Folders flow, both thin CLI wrappers over `hermes_core`. `hermes_watchdog.py` (new 2026-07-25, `djjtb.py` Hermes Helper entry 11) is an unattended stall/crash monitor for the inventory→dedupe→categorize sort pipeline: polls every 30s for crash signatures in Hermes/Ollama logs, gateway death, or 5+ min of no log growth, and auto-relaunches (stop → force-remove sandbox containers → relaunch → POST a phase-appropriate resume prompt) up to 5 attempts before giving up and alerting. Only dry-run (read-only) verified so far against a real live job, not yet through an actual crash cycle. **Non-obvious gotcha for any future code hitting Hermes's `/v1/chat/completions`:** the session ID it derives is `sha256(system_prompt + first_user_message)`, not random per call — two calls with identical first-message text collide onto the same session. `hermes_watchdog.py` works around this with a unique per-call marker; anything else calling that endpoint expecting a fresh session every time needs to do the same, or pass an explicit `X-Hermes-Session-Id`.
- `djjtb/quick_tools/`, `djjtb/file_tools/` — standalone utilities.
- `djjtb/helpers/` — one-off dev/migration scripts (Florence fixes, XMP mergers, vlc renamer, kohya guide, push scripts). Not part of the menu.
- `djjtb/archived/` — a third tier distinct from `old_versions/`: tools that still work and are worth keeping runnable, just rarely used, so they'd otherwise be forgotten. Wired into their own "🗄️ ARCHIVED" submenu off the **main** menu (shortcut `AC`), via `handle_archived_tools()`/`show_archived_menu()` in `djjtb.py`. Contrast with `old_versions/`, which stays reserved for genuinely superseded/broken code with no menu entry at all. Currently holds `video_gif_converter.py` (moved out of Video Tools' main list — "what good is GIF nowadays"), `image_collage_creator.py` (moved here from `old_versions/` — it's superseded by `image_processor.py`'s Pairing/Collage mode for the common case, but the standalone workflow is still occasionally wanted), and `image_caption_generator.py` + `image_tagger.py` (moved here from `old_versions/` during the bak/old_versions cleanup — outdated but still occasionally useful, same reasoning). Add future rarely-used-but-not-dead tools here rather than letting them vanish into `old_versions/` un-discoverable.
- **App Launcher — removed from the main menu (2026-07-25).** The `A` App Launcher entry and its handler in `djjtb.py` were deleted; `djjtb/app_launcher.py` (the actual menu-wired script — confirmed syntactically valid, just unused) archived to `djjtb/old_versions/app_launcher.py`. While removing it, found a second, completely unrelated, unreferenced-anywhere duplicate at the old `djjtb/quick_tools/app_launcher.py` (249 lines, had a real `IndentationError` — broken and dead, unlike the menu-wired one) — archived alongside it as `djjtb/old_versions/app_launcher_quicktools_orphan.py`. User confirmed they don't use App Launcher; no replacement planned.
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
| CodeFormer + Upscaler (combo) | `ai_models/CodeFormer/cfvenv/bin/python3` + `ai_models/upscalers/upsvenv/bin/python3` | `ai_models/CodeFormer/inference_codeformer.py` + an inline upscale script run via `upsvenv` | `cf_ups_runner.py` (menu: AI Tools → "Upscaler AI") |
| ComfyUI (server) | `ai_models/ComfyUI_App/ComfyUI/cfuivenv/bin/python3` | `ai_models/ComfyUI_App/ComfyUI/main.py` | `comfyui_runner.command` |
| JoyTag | `ai_models/joytag/jtvenv/bin/python` | in-process ONNX inference, no separate script invoked | `joytag_tagger.py` |
| JoyCaption | `ai_models/joycaption/jcvenv/bin/python3` | runs in-process inside jcvenv | `joycaption_runner.py` |
| Image Finder | — runs in DJJTB's own venv, no separate `ai_models` venv | self | `image_finder.py` |
| Open WebUI | — no venv, Docker container (`docker start open-webui`) | — | `open_webui_runner.command` |
| Smart Crop (AI) | `ai_models/smart_crop/scvenv/bin/python3` (detection only — orchestration/crop runs in DJJTB's own venv) | `ai_models/smart_crop/models/yolox_l.onnx` via an inline detection script run through `scvenv` | `smart_crop_runner.py` (menu: AI Tools → 14) |

Standalone `codeformer_runner.py` and `upscaler_runner.py` no longer exist — both fully retired during the `djjtb/bak`/`old_versions` cleanup, superseded by the combined `cf_ups_runner.py` row above (confirmed intentional, not an accident: the two were already redundant with the combo runner). Unlike the Watermark Remover retirement below, these weren't parked in `old_versions/` — they're gone from disk, recoverable only via git history if ever needed again.

### Present, not on the active list — cleanup candidates

Paths resolve on disk, but not in daily use — decide keep/delete per tool, don't assume either way:

- **Watermark Remover — retired.** All 4 variants (`watermark_remover_auto.py`, `watermark_remover_ref.py`, `watermark_remover_pkfpl.py`, `watermark_remover_unified.py`) plus `watermark_remover_settings.txt.py` moved to `djjtb/old_versions/` — slow, imprecise (brush-style, not true inpainting), and superseded by batch inpainting via Qwen Edit. Not wired into `djjtb.py`'s menu. Their shared venv, `ai_models/watermark_remover/wmrmvenv` (**1.08GB**), is now orphaned — flagged for a future disk-space cleanup pass, not deleted yet.
- **codeformer_runner_liveprompt.py** — same `cfvenv` as the combo runner above, resolves; not wired into `djjtb.py`'s menu.
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

**TODO, found 2026-08-03 while debugging a sibling project's ComfyUI client (stories-with-DJJ,
not this repo)**: ComfyUI's own `POST /free` endpoint (`{"unload_models": true, "free_memory":
true}`, confirmed by reading `main.py`'s queue loop directly — it calls
`comfy.model_management.unload_all_models()`, resets the execution cache, then `gc.collect()` +
`soft_empty_cache()`, the real MPS cache-clear) is a lightweight way to periodically reset
ComfyUI's memory state mid-batch, without restarting the whole server (no custom-node reload, no
downtime) — at the cost of the next job after a free having to reload the model stack from disk.
Real motivating case: a long run of many sequential Qwen Image Edit generations in one
ComfyUI process showed real per-generation slowdown (`/it` time climbing, one generation
eventually taking 5+ minutes) that a periodic `/free` call (every ~4 generations) measurably
bounded — noisy afterward but no longer runaway-compounding. **Worth adding to
`comfyui_batch.py`'s batch loops** (`process_single_input`, `process_dual_input`,
`generate_missing_icons`) as an optional periodic call every N submissions, same idea as this
repo's existing `QUEUE_DELAY` convention. Not yet implemented here — this is a note to come back
to, not a completed change. See stories-with-DJJ's `animation/spike/comfyui_client.py`
(`free_memory()`) and `CLAUDE.md`'s 2026-08-03 entries for the fuller investigation if useful
context is needed before implementing.

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

- Per-script/per-operation logs: target convention is `djjtb/logs/<script_or_operation>_log.txt` (lowercase `logs`), one continuous append-mode file per meaningfully distinct operation (not one per whole script — e.g. `image_processor_pad_log.txt`, `image_processor_convert_log.txt`). Applied opportunistically whenever a script is created or substantively revised, not retrofitted in bulk. See the `djjtb-conventions` skill for the full design. Currently mid-migration: `djj.setup_logging(output_path, script_name)` in `djjtb/utils.py` still writes beside the output folder in `mode='w'` (overwritten per run) at ~11 existing call sites — update a call site to the new convention only when you're already touching that script.
- **Exception — comfyui_batch logs**: `djjtb/logs/comfyui_batch_logs/` (moved here from `DJJTB_output/comfyui_batch_logs/`) keeps its own subfolder with one file per day (`YYYY-MM-DD.log`) plus `job_counter.txt`, set by `LOG_FOLDER` in `djjtb/ai_tools/comfyui/comfyui_batch.py`. Migrated ahead of the opportunistic schedule above because these are actually read regularly, unlike most other tools' logs — don't collapse this into the one-file-per-operation default.
- Tool-specific output dirs under `~/Documents/Scripts/DJJTB_output/` include `link_grabber/`, `path_grabber/`, `link_scraper/`, `media_info_extractor/`, `image_tagger/`, `watermark_remover/`, `facefusion_test_targets/`, `auto_subfolder/`, `for_PLAYLIST/`, plus `*link.txt` files written by the grabbers.

## djjtb-suite (web UI built on this repo)

`/Users/home/Documents/Scripts/DJJPS/djjtb-suite` is a web conversion of some of these tools
(currently: all of Video Tools, all of Image Tools, plus Playlist Generator), built by importing
pure logic functions from this repo unchanged — never duplicating them. See its own CLAUDE.md's
"Conversion convention" section for the exact interactive-vs-pure split it expects, and its
"Long-term direction" section for which parts of DJJTB are actually in scope (narrower than
everything — AI Tools, most of Quick Tools, and several Media Tools entries are permanently or
provisionally CLI-only).

- **New scripts**: separate pure per-item logic (explicit args, no `djj.prompt_*`/`input()`
  calls, returns a real value/status) from `main()`'s prompting/orchestration/progress-printing,
  as this repo's own standard practice now — not speculatively for djjtb-suite's sake, just
  cleaner structure (easier to test, easier to reuse from a REPL). This happens to make
  conversion free later if a tool's ever in scope, but that's a side effect, not the goal — don't
  build a web-facing shape for a tool that's unlikely to ever be converted.
- **Changing an existing function**: before changing the signature or behavior of any function,
  check djjtb-suite's own CLAUDE.md for whether it's one djjtb-suite already imports unchanged
  (e.g. `reencode_one`, `speed_change_one`, `crop_one`, `reverse_and_merge`,
  `collect_media_files`, `write_playlist`, `build_groups_for_images`,
  `create_collage_from_groups`, and others — the exact current list lives there, not here, since
  duplicating it here would go stale). A behavior change to one of these silently affects the web
  UI with zero signal from this side, since a DJJTB session has no visibility into djjtb-suite by
  default.
- **Wired into `djjtb.py`'s main menu (2026-07-31)**: QUICK TOOLS → new "DJJPS (GUI)" sub-heading,
  choice `12`. Launched via `djj.open_path()` on `run_djjtb_suite_desktop.command` — deliberately
  *not* `run_command_in_tab`/`run_script_in_tab` (which `source` DJJTB's own venv into the
  launcher's Terminal tab): the four DJJPS GUI apps each have their own venv, and the user wants
  zero risk of them getting tangled with DJJTB's. `open_path()` just shells out to macOS `open`,
  identical to double-clicking the `.command` file — it opens its own Terminal window at that
  window's default profile, fully independent of DJJTB's tab session, and closes itself when the
  pywebview app quits.

## facefusion-desktop-djjtb (desktop GUI built on this repo)

`/Users/home/Documents/Scripts/DJJPS/facefusion-desktop-djjtb` is a standalone pywebview +
React desktop GUI wrapping `djjtb/ai_tools/facefusion_runner.py` specifically — not a
djjtb-suite feature (djjtb-suite's scope permanently excludes AI Tools) and not a general
"AI Tools framework," just the first single-tool conversion of this kind. See its own
CLAUDE.md for the full architecture (no FastAPI/HTTP — pywebview's `js_api` bridge instead,
since it's single-user/single-tool, a deliberately different stack from djjtb-suite's).

- Installed as an editable dependency into *its own* venv (`pip install -e
  /Users/home/Documents/Scripts/DJJTB`), same pattern djjtb-suite uses — never installed into
  this repo's own venv or into its frontend.
- Imports these functions from `facefusion_runner.py` unchanged, as pure functions:
  `build_facefusion_args`, `process_single_headless`, `generate_output_filename`,
  `collect_files_from_folder`, `get_target_ff_dir`, `copy_source_files`,
  `handle_target_files`, `tag_source_files`, `verify_facefusion_exists`. Never the interactive
  ones (`get_swap_mode`, `get_source_input`, `get_target_input`,
  `get_output_path_and_suffix`, `main`) — those are replaced by GUI form state.
- **Changing `facefusion_runner.py`**: before changing the signature or behavior of any
  function in the list above, check facefusion-desktop-djjtb's own CLAUDE.md — a behavior
  change there silently affects the desktop GUI with zero signal from this side, same
  blind spot djjtb-suite has. One extra wrinkle specific to this consumer:
  `build_facefusion_args()` reads `FACE_MASK_PADDING`/`FACE_MASK_BLUR`/detector &
  landmarker scores/`FACE_DETECTOR_MODEL` as **module-level globals**, not parameters — the
  GUI's "Advanced" panel overrides these on the imported module object at run time
  (`backend/jobs.py`'s `_apply_advanced()`) rather than passing them as args. If these ever
  become real parameters instead of globals, that override mechanism needs updating too.
- **Wired into `djjtb.py`'s main menu (2026-07-31)**: QUICK TOOLS → "DJJPS (GUI)" sub-heading,
  choice `14`, via `djj.open_path()` on `run_facefusion_desktop.command` — see the equivalent
  note under djjtb-suite above for why `open_path()` (double-click equivalent) was used instead
  of the venv-sourcing tab launchers.

## joycaption-desktop-ollama-djjtb (desktop GUI built on this repo)

`/Users/home/Documents/Scripts/DJJPS/joycaption-desktop-ollama-djjtb` is a standalone pywebview +
React desktop GUI wrapping `djjtb/ai_tools/joycaption_runner_ollama.py` — same pattern as
facefusion-desktop-djjtb (pywebview `js_api` bridge, no HTTP/FastAPI), not a djjtb-suite feature.
Captions images via JoyCaption Beta One served locally through Ollama. See its own CLAUDE.md for
full architecture; pushed to GitHub, private, `main` branch.

- Installed as an editable dependency into *its own* venv (`pip install -e
  /Users/home/Documents/Scripts/DJJTB`), same pattern as the other two. Confirmed lightweight —
  backend venv is just `djjtb` + `pywebview` + `requests`, nothing from this repo's heavy
  `requirements.txt`.
- Imports unchanged, as pure functions/classes/constants: `CAPTION_STYLES`, `SUPPORTED_EXTS`,
  `OLLAMA_URL`, `OLLAMA_MODEL`, `JoyCaptionModel` (load/caption/unload). Never `main()` or the
  raw `input()`/`djj.prompt_*` calls inside it.
- **Two functions that look pure but aren't imported**: `process_images()` prints progress
  directly instead of returning status, so the GUI's `backend/jobs.py` reimplements its per-image
  loop, pushing progress via `window.state.job` instead (same reason facefusion-desktop-djjtb
  doesn't import `process_face_swap()`). `collect_images_from_txt()` internally calls
  `djj.get_path_input()` (interactive) to ask for the txt path, so it can't run unchanged either —
  the GUI gets that path via a native file dialog and reimplements just the file-parsing body.
- **Changing `joycaption_runner_ollama.py`**: before changing the signature or behavior of
  anything in the "imported unchanged" list above, check joycaption-desktop-ollama-djjtb's own
  CLAUDE.md — same blind-spot rule as the other two conversions. Also worth knowing: importing
  this module runs `os.system('clear')` unconditionally at module level, which now also fires
  once whenever the desktop app's backend process starts (clears whichever terminal launched it) —
  not fixed, just flagged, per that app's own "preserve CLI quirks" convention.
- **Wired into `djjtb.py`'s main menu (2026-07-31)**: QUICK TOOLS → "DJJPS (GUI)" sub-heading,
  choice `15`, via `djj.open_path()` on `run_joycaption_desktop.command` — see the equivalent
  note under djjtb-suite above for why `open_path()` (double-click equivalent) was used instead
  of the venv-sourcing tab launchers.

## smart-crop-djjtb (desktop GUI built on this repo)

`/Users/home/Documents/Scripts/DJJPS/smart-crop-djjtb` is a standalone pywebview + React desktop
GUI wrapping `djjtb/ai_tools/smart_crop_runner.py` — same pattern as facefusion-desktop-djjtb and
joycaption-desktop-ollama-djjtb (pywebview `js_api` bridge, no HTTP/FastAPI), not a djjtb-suite
feature. Subject-aware batch crop: YOLOX-l person detection + largest-window crop to a target
aspect ratio, optional resize to a longest-edge value. See its own CLAUDE.md for full
architecture; verified end-to-end (2 real test photos, both correctly person-detected and
cropped) before being called done.

- Installed as an editable dependency into *its own* venv (`pip install -e
  /Users/home/Documents/Scripts/DJJTB`), same pattern as the other two. Confirmed lightweight —
  backend venv is just `djjtb` + `pywebview` + `Pillow`, nothing from this repo's heavy
  `requirements.txt`. The actual heavy lifting (`onnxruntime`, `opencv`, `numpy`, the 216MB
  YOLOX-l model) stays fully isolated behind `smart_crop_runner.py`'s own `scvenv` subprocess
  boundary — never touches this GUI's venv at all.
- Imports unchanged, as pure functions/constants: `detect_subjects()`, `compute_crop_box()`,
  `AR_PRESETS`, `SC_PYTHON`, `SC_MODEL_PATH`, `SC_CONF_DEFAULT`, `get_op_logger()`. Never `main()`,
  `get_target_ar()`, `get_output_resolution()`, or the raw `djj.prompt_choice`/`djj.get_int_input`
  calls inside `main()`'s loop — those are replaced by GUI form state.
- **Two wrinkles this conversion has that the other two don't**: (1) `smart_crop_images()` prints
  progress directly instead of returning status, so the GUI's `backend/jobs.py` reimplements its
  per-image loop (same reason facefusion-desktop-djjtb doesn't import `process_face_swap()`) —
  but detection itself is *also* one opaque batched subprocess call for the whole image set (no
  per-image signal during that phase), so the GUI's job state has an extra `phase`
  (`"detecting"`/`"cropping"`) field neither sibling app needed. (2) There's no
  `check_dependencies()`-style function in the source script to reuse for a "model not found"
  setup-required card — the CLI just shells out and prints a warning on failure — so
  `sc_api.py`'s `check_dependencies()` (verifies `SC_PYTHON`/`SC_MODEL_PATH` exist on disk) is new
  logic, not a reuse of existing CLI reasoning.
- `get_paths_from_txt()` calls `input()` directly (interactive), so it can't run unchanged either —
  the GUI gets the txt path via a native file dialog and reimplements just the file-parsing body
  (skip blank/`#`-comment lines, strip quotes, unescape `\ ` spaces, resolve, check existence).
- **Changing `smart_crop_runner.py`**: before changing the signature or behavior of anything in
  the "imported unchanged" list above, check smart-crop-djjtb's own CLAUDE.md — same blind-spot
  rule as the other two conversions.
- **Wired into `djjtb.py`'s main menu (2026-07-31)**: QUICK TOOLS → "DJJPS (GUI)" sub-heading,
  choice `13`, via `djj.open_path()` on `run_smart_crop_desktop.command` — see the equivalent
  note under djjtb-suite above for why `open_path()` (double-click equivalent) was used instead
  of the venv-sourcing tab launchers.

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

**Status (2026-07-25):** the modularization/dedup half is done — see `djjtb/admin_tools/UTILS_DEDUP_REFACTOR_PLAN.md` (all 7 phases complete, merged to `main`). The actual cross-tool chaining half is in progress on its own fully-isolated branch, `worktree-centralized-io-chaining` (pushed to GitHub, not merged to `main` — deliberately kept separate until thoroughly tested, since it's expected to be fragile and workflow-critical). See `djjtb/admin_tools/CENTRALIZED_IO_CHAINING_PLAN.md` on that branch for exact status before continuing this work.

## Long Term goal
Make DJJTB a full-on shippable, bankable APP, step by step.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
