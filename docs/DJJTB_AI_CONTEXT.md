# DJJTB — AI Context Reference
_Generated 2026-05-01 22:57 by djjtb_scan.py_

## About DJJTB

DJJTB (DJJ Toolbox) is a personal Python CLI toolkit of ~20–30 scripts for media processing and AI tools, launched via AppleScript terminal tabs from a central `djjtb.py` launcher.

- **Project root:** `/Users/home/Documents/Scripts/DJJTB/`
- **Scripts live in:** `DJJTB/djjtb/` (nested by category)
- **Main venv:** `~/Documents/Scripts/DJJTB/venv`
- **Shared utils:** `djjtb/utils.py` — imported everywhere as `import djjtb.utils as djj`
- **Media utils:** `djjtb/media_utils.py` — re-exported via utils, callable as `djj.*`
- **AI tools** use isolated venvs (joytag: `jtvenv`, upscaler: `upsvenv`, watermark: `wmrmvenv`)
- **Template/pattern source:** `codeformer_runner.py` — canonical script structure

## Key Conventions

- All selections via `djj.prompt_choice()` — never raw `input()` for options
- All questions asked **upfront** before processing begins
- Output routed to named subfolders: `parent/Output/ToolName/`
- `what_next()` loop at end of every script
- `prompt_open_folder()` offered after processing
- `tag_source_files()` for Finder tagging of processed files
- Skip list at `/Users/home/Documents/Scripts/DJJTB_output/skip_list.txt`
- `apply_skip_list(files, root=input_folder)` — one line after file collection
- Undo manifests: `.djjtb/` hidden folder inside input folder, JSON stackable

## Environment

- Mac Studio M4 Max, 64GB unified memory, macOS Sequoia
- Python 3.11.9 (DMG install), pip venvs only (no conda)
- FFmpeg is the core media processing engine
- MPS backend for PyTorch (Apple Silicon) — CUDA ops will fail
- Known MPS blockers: `basicsr`, `realesrgan`, FP8 dtypes, CUDA-hardcoded code


## 🗂️ Root / Shared

### `djjtb/app_launcher.py`
**Purpose:** app launcher (djjtb)
**djj utils:** UI(prompt_choice, wait_with_skip) | launch_app
**Key functions:** `run_app_launcher`, `subfolder_from_input`

### `djjtb/media_utils.py`
**Purpose:** DJJTB Media Utilities
**Input:** folder + subfolders
**Ext tools:** FFmpeg, Pillow

### `djjtb/utils.py`
**Purpose:** Shared utility functions imported by all scripts as djjtb.utils (djj.*)
**Modes:**
  - 1. Single folder (all media files)
  - 2. Multiple files/folders (space-separated)
  - 3. Single file
  - 1. Desktop
  - 2. Same folder as input files
  - 3. Custom folder
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Folder path
  - 2. Space-separated file paths
**Input:** folder, multi-file drag+drop, space-separated paths, txt file
**Output:** DJJTB_output/ (centralized)
**Ext tools:** FFmpeg


## 🎞️ Media Tools

### `djjtb/media_tools/media_info_extractor.py`
**Purpose:** media info extractor (media tools)
**Modes:**
  - 1. Folder Mode
  - 2. Space-separated file paths
  - 1. Images only
  - 2. Videos only
  - 3. Both
  - 1. Yes
  - 2. No
  - 1. Default location
  - 2. Output folder near input
  - 3. Custom path
**Input:** folder
**Output:** DJJTB_output/ (centralized)
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next)
**Ext tools:** Pillow
**Key functions:** `format_duration`, `collect_media_files`, `get_media_info`, `get_output_dir`, `main`

### `djjtb/media_tools/media_sorter.py`
**Purpose:** media sorter (media tools)
**Modes:**
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes
  - 2. No
  - 1. Images only
  - 2. Videos only
  - 3. Both
  - 1. Rename with Suffix Only
  - 2. Move Subfolders and Rename
  - 3. Move to Subfolders Only
**Input:** folder, folder + subfolders, space-separated paths
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next) | SkipList(apply_skip_list, load_skip_list, should_skip)
**Ext tools:** FFmpeg, Pillow
**Key functions:** `tag_file`, `get_aspect_category`, `get_video_resolution`, `get_image_resolution`, `safe_rename_only`, `safe_move_and_rename`, `safe_move_only`, `reverse_suffix_files`

### `djjtb/media_tools/metadata_injector.py`
**Purpose:** metadata injector (media tools)
**Ext tools:** Pillow
**Key functions:** `inject_metadata`, `process_folder`

### `djjtb/media_tools/metadata_tool.py`
**Purpose:** Metadata Stripper & Injector Tool
**Modes:**
  - 1. Process all files
  - 2. Select specific files
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Videos only
  - 2. Images only
  - 3. Audio only
  - 4. All media files
  - 1. Yes, 2. No
  - 1. Yes
**Input:** folder, space-separated paths
**djj utils:** UI(get_path_input, prompt_choice, what_next) | Tabs(setup_terminal)
**Ext tools:** FFmpeg, Pillow
**Key functions:** `clean_path`, `generate_fake_metadata`, `get_file_type_by_extension`, `is_media_file`, `collect_and_select_files`, `collect_files_from_paths`, `run_ffmpeg_strip`, `run_exiftool_strip`

### `djjtb/media_tools/playlist_generator.py`
**Purpose:** playlist generator (media tools)
**Modes:**
  - 1. Yes (~/Desktop/Playlists)
  - 2. No (choose custom path)
  - 1. Folder path
  - 2. Space-separated file paths
  - 3. Path list from txt file
  - 1. Yes
  - 2. No
  - 1. Yes
  - 2. No
  - 1. Use '{default_name_suggestion}' (from input)
**Input:** folder, folder + subfolders, space-separated paths
**Output:** ~/Desktop/Playlists/
**djj utils:** UI(get_path_input, get_string_input, prompt_choice, prompt_open_folder, what_next)
**Key functions:** `collect_media_files`, `collect_media_from_txt`, `display_media_list`, `write_playlist`, `get_playlist_path`, `generate_playlist`, `main`

### `djjtb/media_tools/image_tools/_init__.py`
**Purpose:**  init   (image tools)

### `djjtb/media_tools/image_tools/image_collage_creator.py`
**Purpose:** image collage creator (image tools)
**Modes:**
  - 1. Yes
  - 2. No
  - 1. Yes
  - 2. No
**Input:** folder, folder + subfolders, space-separated paths, txt file
**Output:** Output/Collage_Joined/
**djj utils:** UI(get_path_input, get_paths_from_txt, prompt_choice, prompt_open_folder, what_next) | setup_logging
**Ext tools:** Pillow
**Key functions:** `setup_logging`, `should_exclude_image`, `load_images`, `load_images_from_list`, `load_used_images`, `save_used_images`, `get_next_collage_number`, `collect_images_from_folder`

### `djjtb/media_tools/image_tools/image_converter.py`
**Purpose:** image converter (image tools)
**Modes:**
  - 1. Yes
  - 2. No
  - 1. Yes
  - 2. No
**Input:** folder, folder + subfolders, space-separated paths
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next) | setup_logging
**Ext tools:** Pillow
**Key functions:** `setup_logging`, `collect_images_from_folder`, `collect_images_from_paths`, `collect_images_from_txt`, `convert_images`, `main`

### `djjtb/media_tools/image_tools/image_flip_rotate.py`
**Purpose:** image flip rotate (image tools)
**Modes:**
  - 1. Yes, 2. No
**Input:** folder + subfolders
**djj utils:** UI(prompt_choice, prompt_open_folder, what_next)
**Ext tools:** Pillow
**Key functions:** `clear_screen`, `setup_logging`, `clean_path`, `rotate_or_flip_images`

### `djjtb/media_tools/image_tools/image_padder.py`
**Purpose:** image padder (image tools)
**Modes:**
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes, 2. No
  - 1. Left (image on left, padding on right)
  - 2. Right (image on right, padding on left)
  - 3. Center
  - 1. Square
  - 2. Landscape
  - 3. Portrait
  - 4. Custom
**Input:** folder, space-separated paths
**djj utils:** UI(get_int_input, prompt_choice, prompt_open_folder, what_next)
**Ext tools:** Pillow
**Key functions:** `clear_screen`, `clean_path`, `setup_logging`, `is_valid_image`, `collect_images_from_folder`, `collect_images_from_paths`, `get_output_directory`, `calculate_padding_offset`

### `djjtb/media_tools/image_tools/image_pairing.py`
**Purpose:** image pairing (image tools)
**Modes:**
  - 1. Yes
  - 2. No
  - 1. Prefix
  - 2. Suffix
  - 1. Yes
  - 2. No
  - 1. Yes
  - 2. No (same as main)
  - 1. Yes
  - 2. No
**Input:** folder, folder + subfolders, space-separated paths, txt file
**Output:** Output/Comp/, Output/Comp_Joined/, Output/Joined/, Output/Paired/, input/Joined/
**djj utils:** UI(get_int_input, get_path_input, get_paths_from_txt, prompt_choice, prompt_open_folder, what_next) | Media(create_collage, join_image_video)
**Ext tools:** FFmpeg, Pillow
**Key functions:** `clear_screen`, `setup_logging`, `is_valid_image`, `collect_images_from_folder`, `collect_images_from_paths`, `collect_images_from_txt`, `group_images_by_parent_folder`, `get_match_key`

### `djjtb/media_tools/image_tools/image_resizer.py`
**Purpose:** image resizer (image tools)
**Modes:**
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes
  - 2. No
  - 1. Width (↔️)
  - 2. Height (↕️)
  - 1. PNG
  - 2. JPG
**Input:** folder, space-separated paths
**djj utils:** UI(get_int_input, get_path_input, prompt_choice, prompt_open_folder, what_next)
**Ext tools:** Pillow
**Key functions:** `setup_logging`, `collect_images_from_folder`, `collect_images_from_paths`, `get_valid_inputs`, `resize_images`

### `djjtb/media_tools/image_tools/image_slideshow_maker.py`
**Purpose:** image slideshow maker (image tools)
**Modes:**
  - 1. Yes
  - 2. No
  - 1. Yes
  - 2. No (combine all)
  - 1. Yes
  - 2. No (combine all)
  - 1. Yes
  - 2. No
  - 1. Blurred (from image)
  - 2. Solid color
**Input:** folder, folder + subfolders, space-separated paths, txt file
**Output:** Output/Slideshow_Joined/, input/Slideshows/
**djj utils:** UI(get_path_input, get_paths_from_txt, prompt_choice, prompt_open_folder, what_next)
**Ext tools:** FFmpeg, Pillow
**Key functions:** `setup_logging`, `collect_images_from_folder`, `collect_images_from_paths`, `collect_images_from_txt`, `group_images_by_parent_folder`, `get_first_image_dimensions`, `prepare_slides`

### `djjtb/media_tools/image_tools/image_stack.py`
**Purpose:** image stack (image tools)
**Modes:**
  - 1. Yes
  - 2. No
  - 1. Horizontal
  - 2. Vertical
  - 1. Prefix
  - 2. Suffix
**Input:** folder, folder + subfolders, space-separated paths, txt file
**Output:** Output/Comp/, Output/Paired/
**djj utils:** UI(get_int_input, get_path_input, get_paths_from_txt, prompt_choice, prompt_open_folder, what_next) | Media(create_collage)
**Ext tools:** FFmpeg, Pillow
**Key functions:** `clear_screen`, `setup_logging`, `is_valid_image`, `collect_images_from_folder`, `collect_images_from_paths`, `collect_images_from_txt`, `group_images_by_parent_folder`, `get_match_key`

### `djjtb/media_tools/image_tools/image_strip_padding.py`
**Purpose:** image strip padding (image tools)
**Modes:**
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes
  - 2. No
**Input:** folder, folder + subfolders, space-separated paths
**Output:** Output/Stripped/
**djj utils:** UI(prompt_choice, prompt_open_folder, what_next)
**Ext tools:** NumPy, Pillow
**Key functions:** `detect_border_color`, `trim_multiple_regions`, `collect_images_from_folder`, `collect_images_from_paths`, `process_images`, `process_folder`, `main`

### `djjtb/media_tools/image_tools/image_video_compiler.py`
**Purpose:** image video compiler (image tools)
**Input:** folder, space-separated paths, txt file
**djj utils:** UI(get_int_input, get_path_input, get_paths_from_txt, prompt_choice, prompt_open_folder, what_next)
**Ext tools:** FFmpeg, Pillow
**Key functions:** `collect_images_from_folder`, `collect_images_from_paths`, `collect_images_from_txt`, `collect_subfolders_with_images`, `get_image_dimensions`, `get_audio_duration`, `compile_images_to_video`

### `djjtb/media_tools/image_tools/image_webp_to_mp4.py`
**Purpose:** image webp to mp4 (image tools)
**Modes:**
  - 1. Yes
  - 2. No
**Input:** folder, folder + subfolders, space-separated paths
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next)
**Ext tools:** FFmpeg, Pillow
**Key functions:** `get_webp_fps`, `extract_webp_frames`, `convert_webp_to_mp4`, `collect_webp_files`, `collect_webp_from_paths`, `collect_webp_from_txt`, `batch_convert_webps`, `main`

### `djjtb/media_tools/image_tools/image_webp_to_mp4_auto_30fps.py`
**Purpose:** image webp to mp4 auto 30fps (image tools)
**Modes:**
  - 1. Yes
  - 2. No
**Input:** folder, folder + subfolders, space-separated paths
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next)
**Ext tools:** FFmpeg, Pillow
**Key functions:** `get_webp_fps`, `extract_webp_frames`, `convert_webp_to_mp4`, `collect_webp_files`, `collect_webp_from_paths`, `collect_webp_from_txt`, `batch_convert_webps`, `main`

### `djjtb/media_tools/image_tools/webp_anim_to_mp4.py`
**Purpose:** webp anim to mp4 (image tools)
**Input:** folder
**Ext tools:** FFmpeg
**Key functions:** `prompt_folder`, `extract_frames`, `convert_to_mp4`, `main`

### `djjtb/media_tools/video_tools/video_cropper.py`
**Purpose:** video cropper (video tools)
**Modes:**
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes, 2. No
**Input:** folder, space-separated paths
**djj utils:** UI(prompt_choice, prompt_open_folder, what_next) | setup_logging
**Ext tools:** FFmpeg
**Key functions:** `get_cropdetect_crop`, `get_video_resolution`, `get_audio_flag`, `build_crop_filter`, `log_to_csv`, `clean_path`, `collect_videos_from_folder`, `collect_videos_from_paths`

### `djjtb/media_tools/video_tools/video_frame_extractor.py`
**Purpose:** video frame extractor (video tools)
**Modes:**
  - 1. Yes
  - 2. Skip
  - 1. Yes
  - 2. No
  - 1. Yes
  - 2. No
  - 1. Yes
  - 2. No
  - 1. Interval  (every Nth frame)
  - 2. Target count  (N frames evenly spread)
**Input:** folder, space-separated paths, txt file
**Output:** Output/Frames/
**djj utils:** UI(get_path_input, get_paths_from_txt, prompt_choice, prompt_open_folder, what_next) | setup_logging
**Ext tools:** FFmpeg
**Key functions:** `prompt_integer`, `get_video_info`, `probe_all_videos`, `format_duration`, `display_probe_table`, `parse_finder_paths`, `collect_videos_from_folder`, `collect_videos_from_paths`

### `djjtb/media_tools/video_tools/video_gif_converter.py`
**Purpose:** video gif converter (video tools)
**Modes:**
  - 1. GIF to Video
  - 2. Video to GIF
  - 1. High (15fps, 720p)
  - 2. Medium (10fps, 480p)
  - 3. Low (8fps, 360p)
  - 1. H.264 (MP4)
  - 2. WebM
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes, 2. No
**Input:** folder, space-separated paths
**djj utils:** UI(prompt_choice, prompt_open_folder, what_next) | setup_logging
**Ext tools:** FFmpeg
**Key functions:** `clean_path`, `return_to_djjtb`, `is_valid_gif`, `is_valid_video`, `get_conversion_mode`, `get_gif_quality`, `get_video_codec`, `collect_media_from_folder`

### `djjtb/media_tools/video_tools/video_group_merger.py`
**Purpose:** video group merger (video tools)
**Modes:**
  - 1. 16:9 (horizontal)
  - 2. 9:16 (vertical)
  - 1. Blurred background (no black bars)
  - 2. Black padding (simple/fast)
**Input:** folder, space-separated paths
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next)
**Ext tools:** FFmpeg
**Key functions:** `clean_path`, `is_valid_video`, `collect_videos_from_folder`, `collect_videos_recursive`, `collect_subfolders_with_videos`, `collect_videos_from_paths`, `get_user_group_size`, `get_video_info`

### `djjtb/media_tools/video_tools/video_re-encoder.py`
**Purpose:** video re-encoder (video tools)
**Modes:**
  - 1. Yes, 2. No
  - 1. Keep Original Audio
  - 2. Strip Audio
  - 3. Add Silent Audio Track
**djj utils:** UI(prompt_choice, prompt_open_folder, what_next) | Media(get_audio_options) | setup_logging
**Ext tools:** FFmpeg
**Key functions:** `reencode_videos`, `clear_screen`, `main`

### `djjtb/media_tools/video_tools/video_reverse_merge.py`
**Purpose:** video reverse merge (video tools)
**Modes:**
  - 1. Yes
  - 2. No
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes, 2. No
**Input:** folder, space-separated paths
**djj utils:** UI(get_float_input, get_path_input, prompt_choice, prompt_open_folder, what_next)
**Ext tools:** FFmpeg
**Key functions:** `sanitize_path`, `clean_path`, `is_video_file`, `run_ffmpeg`, `get_video_fps`, `reverse_and_merge`, `collect_videos_from_folder`, `collect_videos_from_paths`

### `djjtb/media_tools/video_tools/video_slideshow_watermark.bak20260420.py`
**Purpose:** video slideshow watermark.bak20260420 (video tools)
**Modes:**
  - 1. Slideshow + Watermark
  - 2. Slideshow Only
  - 3. Image Join
  - 1. Yes (per-pair subfolders), 2. No (flat folder)
  - 1. Yes (per-video subfolders), 2. No (flat folder)
  - 1. One slideshow
  - 2. Two slideshows (images auto-split)
  - 1. Yes (per-video subfolders), 2. No (flat folder)
**Input:** folder
**Output:** input/Joined/, input/Slideshows/, input/Watermarked/
**djj utils:** UI(get_float_input, get_path_input, prompt_choice, prompt_open_folder, what_next) | Media(get_audio_options)
**Ext tools:** FFmpeg
**Key functions:** `get_video_info`, `get_video_dimensions`, `get_image_dimensions`, `build_slideshow`, `build_slideshow_native_size`, `get_overlay_position`, `overlay_watermark`, `split_images_for_two`

### `djjtb/media_tools/video_tools/video_slideshow_watermark.py`
**Purpose:** video slideshow watermark (video tools)
**Modes:**
  - 1. Slideshow + Watermark
  - 2. Slideshow Only
  - 3. Image Join
  - 4. Slideshow + Join
  - 5. Collage + Join
  - 1. Yes (per-pair subfolders), 2. No (flat folder)
  - 1. Yes (per-video subfolders), 2. No (flat folder)
  - 1. One slideshow
  - 2. Two slideshows (images auto-split)
  - 1. Yes (per-video subfolders), 2. No (flat folder)
**Input:** folder
**Output:** Output/Collage_Joined/, Output/Joined/, Output/Slideshow_Joined/, input/Joined/, input/Slideshows/, input/Watermarked/
**djj utils:** UI(get_float_input, get_path_input, prompt_choice, prompt_open_folder, what_next) | Media(build_collage_and_join, build_slideshow_and_join, get_join_dimensions, join_image_video, position_suffix)
**Ext tools:** FFmpeg
**Key functions:** `get_video_info`, `get_video_dimensions`, `get_image_dimensions`, `build_slideshow`, `build_slideshow_native_size`, `get_overlay_position`, `overlay_watermark`, `split_images_for_two`

### `djjtb/media_tools/video_tools/video_speed_changer.py`
**Purpose:** video speed changer (video tools)
**Modes:**
  - 1. Yes, 2. No
  - 1. Yes, 2. No
**Input:** space-separated paths
**djj utils:** UI(prompt_open_folder, what_next)
**Ext tools:** FFmpeg
**Key functions:** `setup_logging`, `sanitize_path`, `get_input_paths`, `prompt_choice`, `get_atempo_chain`, `change_speed`, `clear_screen`, `main`

### `djjtb/media_tools/video_tools/video_splitter.py`
**Purpose:** video splitter (video tools)
**Modes:**
  - 1. Folder path, 2. Files & Folders (space-divided)
  - 1. Yes, 2. No
  - 1. By Duration, 2. By Portions
  - 1. Keep Original Audio
  - 2. Strip Audio
  - 3. Add Silent Audio Track)
**Input:** folder, space-separated paths
**djj utils:** UI(get_float_input, get_int_input, prompt_choice, prompt_open_folder, what_next) | Media(get_audio_options) | setup_logging
**Ext tools:** FFmpeg
**Key functions:** `clean_path`, `get_video_duration`, `collect_videos_from_folder`, `collect_videos_from_paths`, `get_video_input`, `split_video_by_duration`, `split_video_by_portions`


## 🤖 AI Tools

### `djjtb/ai_tools/cf_ups_runner.py`
**Purpose:** CF + UPS Runner — DJJTB
**Type:** AI Tool — isolated venv: `cfvenv (CodeFormer)`
**Modes:**
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes
  - 2. No
  - 1. Yes
  - 2. No
  - 1. Yes
  - 2. No
  - 1. No tiling (recommended, 64GB)
  - 2. Tile 512
**Input:** folder, space-separated paths
**Output:** input/CF/, input/UPS/
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next) | SkipList(apply_skip_list)
**Ext tools:** NumPy, OpenCV, PyTorch
**Key functions:** `fmt_time`, `tag_files`, `collect_files_from_folder`, `collect_files_from_paths`, `cleanup_cf_extras`, `find_cf_output`, `run_cf_single`, `run_cf_folder`

### `djjtb/ai_tools/codeformer_runner.py`
**Purpose:** codeformer runner (ai tools)
**Type:** AI Tool — isolated venv: `cfvenv (CodeFormer)`
**Modes:**
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes
  - 2. No
  - 1. Yes, open all
  - 2. Yes, open first one only
  - 3. No
  - 1. Yes, open all
  - 2. Yes, open first one only
  - 3. No
**Input:** folder, space-separated paths
**Output:** input/CF/
**djj utils:** UI(get_path_input, get_string_input, prompt_choice, prompt_open_folder, what_next)
**Key functions:** `format_elapsed_time`, `verify_models_exist`, `clean_path`, `cleanup_cropped_faces`, `cleanup_restored_faces`, `tag_source_files`, `collect_files_from_folder`, `collect_files_from_paths`

### `djjtb/ai_tools/codeformer_runner_liveprompt.py`
**Purpose:** codeformer runner liveprompt (ai tools)
**Type:** AI Tool — isolated venv: `cfvenv (CodeFormer)`
**Modes:**
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes
  - 2. No
  - 1. Yes, open all
  - 2. Yes, open first one only
  - 3. No
  - 1. Yes, open all
  - 2. Yes, open first one only
  - 3. No
**Input:** folder, space-separated paths
**Output:** input/CF/
**djj utils:** UI(get_path_input, get_string_input, prompt_choice, prompt_open_folder, what_next)
**Key functions:** `format_elapsed_time`, `verify_models_exist`, `run_process_with_live_output`, `clean_path`, `cleanup_cropped_faces`, `cleanup_restored_faces`, `tag_source_files`, `collect_files_from_folder`

### `djjtb/ai_tools/facefusion_runner.py`
**Purpose:** facefusion runner (ai tools)
**Type:** AI Tool — isolated venv: `ffvenv (FaceFusion)`
**Modes:**
  - 1. Single source TO multiple targets (one face → many images/videos)
  - 2. Single source TO single target (one face → one image/video)
  - 3. Multiple sources TO single target (m   any faces → one image/video)
  - 4. Multiple sources TO multiple targets (many faces → many images/videos)
  - 1. Folder containing source faces
  - 2. Space-separated file paths
  - 3. Pick from default FACES folder
  - 1. Yes
  - 2. No
  - 1. Enter file path
**Input:** folder, space-separated paths
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next)
**Key functions:** `verify_facefusion_exists`, `clean_path`, `tag_source_files`, `copy_source_files`, `handle_target_files`, `collect_files_from_folder`, `collect_files_from_paths`, `build_facefusion_args`

### `djjtb/ai_tools/gfpgan_runner.py`
**Purpose:** gfpgan runner (ai tools)
**Type:** AI Tool — subprocess/venv pattern
**Modes:**
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes
  - 2. No
  - 1. Yes, open all
  - 2. Yes, open first one only
  - 3. No
  - 1. Yes
  - 2. No
  - 1. Yes
**Input:** folder, space-separated paths
**djj utils:** UI(get_path_input, get_string_input, prompt_choice, prompt_open_folder, what_next)
**Ext tools:** PyTorch
**Key functions:** `format_elapsed_time`, `verify_setup`, `clean_path`, `cleanup_cropped_faces`, `cleanup_restored_faces`, `cleanup_comparison`, `tag_source_files`, `collect_files_from_folder`

### `djjtb/ai_tools/image_caption_generator.py`
**Purpose:** Image Caption Generator for DJJTB
**Type:** AI Tool — isolated venv: `wmrmvenv (Watermark)`
**Modes:**
  - 1. Folder path
  - 2. Space-separated file paths
  - 3. Path list from txt file
  - 1. Yes
  - 2. No
  - 1. Florence-2-base (Faster, ~0.5GB)
  - 2. Florence-2-large (Better quality, ~1GB)
  - 1. All
  - 2. First
  - 3. No
**Input:** folder, folder + subfolders, space-separated paths
**Output:** Output/Captions/
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next)
**Ext tools:** HuggingFace, NumPy, Pillow, PyTorch, timm
**Key functions:** `ensure_venv_and_run`, `setup_model_cache`, `check_dependencies`, `collect_images_from_folder`, `collect_images_from_paths`, `collect_images_from_txt`, `get_valid_inputs`, `get_caption_options`

### `djjtb/ai_tools/image_finder.py`
**Purpose:** image finder (ai tools)
**Modes:**
  - 1. AND (all terms must match)
  - 2. OR (any term matches)
  - 1. Subfolder(s)
  - 2. CSV
  - 1. Yes
  - 2. No
  - 1. Yes, 2. No
  - 1. Yes, 2. No
  - 1. AND (all terms must match)
  - 2. OR (any term matches)
**Input:** folder, folder + subfolders
**djj utils:** UI(prompt_choice, prompt_open_folder)
**Key functions:** `safe_filename`, `open_folder_mac`, `search_tags_in_db`, `search_tags_in_xmp`, `xmp_only_mode`, `main`

### `djjtb/ai_tools/image_tagger.py`
**Purpose:** image tagger (ai tools)
**Modes:**
  - 1. Online (download/verify models)
  - 2. Offline (use cached models only)
  - 1. Single CSV file (original mode)
  - 2. Folder mode (process multiple CSVs)
  - 1. Optimized dataset (recommended)
  - 2. Load custom CSV file
  - 1. Default batch folder
  - 2. Choose custom folder
  - 1. Yes, create examples
  - 2. No, choose different folder
**Input:** folder, folder + subfolders
**Output:** DJJTB_output/ (centralized)
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next) | filter_images_without_xmp, prompt_xmp_handling_mode, setup_logging
**Ext tools:** HuggingFace, NumPy, Pillow, PyTorch
**Key functions:** `format_elapsed_time`, `setup_logging`, `initialize_clip_model`, `get_default_csv_path`, `get_csv_folder_path`, `prompt_processing_mode`, `prompt_csv_dataset`, `prompt_csv_folder`

### `djjtb/ai_tools/joycaption_runner.py`
**Purpose:** JoyCaption Runner for DJJTB
**Type:** AI Tool — isolated venv: `jcvenv (JoyCaption)`
**Modes:**
  - 1. Yes
  - 2. Exit
  - 1. Yes
  - 2. No
  - 1. Yes (skip)
  - 2. No (overwrite all)
  - 1. Yes
  - 2. Cancel
**Input:** folder, folder + subfolders
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next) | SkipList(apply_skip_list)
**Ext tools:** HuggingFace, Pillow, PyTorch
**Key functions:** `format_time`, `collect_images`, `txt_exists`, `check_venv`, `print_setup_instructions`, `check_dependencies`, `process_images`, `main`

### `djjtb/ai_tools/joytag_tagger.py`
**Purpose:** JoyTag Image Tagger for DJJTB - WITH XMP DETECTION
**Type:** AI Tool — isolated venv: `jtvenv (JoyTag)`
**Modes:**
  - 1. Yes, set up now
  - 2. Exit
  - 1. Yes
  - 2. No
  - 1. Yes, process all
  - 2. No, skip this folder
  - 1. Yes (recommended for DigiKam)
  - 2. No, CSV only
  - 1. Yes,  2. No
**Input:** folder, folder + subfolders
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next) | SkipList(apply_skip_list) | filter_images_without_xmp, prompt_xmp_handling_mode, setup_logging
**Ext tools:** HuggingFace, NumPy, Pillow, PyTorch
**Key functions:** `format_elapsed_time`, `check_environment`, `install_dependencies`, `download_joytag_model`, `setup_joytag_environment`, `setup_logging`, `setup_database`, `collect_images_from_folder`

### `djjtb/ai_tools/merge_loras.py`
**Purpose:** merge loras (ai tools)
**Ext tools:** PyTorch

### `djjtb/ai_tools/prompt_randomizer.py`
**Purpose:** prompt randomizer (ai tools)

### `djjtb/ai_tools/realesrgan_runner.py`
**Purpose:** realesrgan runner (ai tools)
**Modes:**
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes
  - 2. No
  - 1. Same as input
  - 2. JPG
  - 3. PNG
  - 4. WEBP
  - 1. Yes
  - 2. No
**Input:** folder, space-separated paths
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next) | open_multiple_folders
**Key functions:** `format_elapsed_time`, `verify_executable_exists`, `clean_path`, `tag_source_files`, `collect_files_from_folder`, `collect_files_from_paths`, `get_valid_inputs`, `create_output_path`

### `djjtb/ai_tools/realsr_runner.py`
**Purpose:** realsr runner (ai tools)
**Modes:**
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes
  - 2. No
  - 1. Yes
  - 2. No
**Input:** folder, space-separated paths
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next) | open_multiple_folders
**Key functions:** `format_elapsed_time`, `verify_executable_exists`, `clean_path`, `tag_source_files`, `collect_files_from_folder`, `collect_files_from_paths`, `get_valid_inputs`, `create_output_path`

### `djjtb/ai_tools/thinksound_runner.py`
**Purpose:** ThinkSound Runner — DJJTB
**Type:** AI Tool — subprocess/venv pattern
**Modes:**
  - 1. Flat (videos directly in folder)
  - 2. Subfolders (one video per subfolder)
  - 1. Output/ subfolder inside input folder
  - 2. Same folder as each video
  - 3. Custom path
  - 1. Fast (24 steps)
  - 2. Balanced (36 steps)
  - 3. Quality (50 steps)
  - 1. Yes (save merged .mp4)
  - 2. No (audio WAV only)
**Input:** folder
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next) | Tabs(run_command_in_tab)
**Ext tools:** FFmpeg
**Key functions:** `verify_installation`, `collect_videos`, `collect_videos_from_subfolders`, `run_thinksound`, `merge_audio_to_video`, `process_video`, `main`

### `djjtb/ai_tools/upscaler_runner.py`
**Purpose:** upscaler runner (ai tools)
**Type:** AI Tool — isolated venv: `upsvenv (Upscaler)`
**Modes:**
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes
  - 2. No
  - 1. Yes, open all
  - 2. Yes, open first one only
  - 3. No
  - 1. No tiling — full image (recommended, 64GB)
  - 2. Tile size 512
  - 3. Tile size 256
**Input:** folder, space-separated paths
**Output:** input/UPS/
**djj utils:** UI(get_path_input, get_string_input, prompt_choice, prompt_open_folder, what_next) | SkipList(apply_skip_list)
**Ext tools:** NumPy, OpenCV, Pillow, PyTorch
**Key functions:** `format_elapsed_time`, `verify_environment`, `tag_source_files`, `clean_path`, `collect_files_from_folder`, `collect_files_from_paths`, `get_valid_inputs`, `process_single_file`

### `djjtb/ai_tools/watermark_remover_auto.py`
**Purpose:** Enhanced AI Watermark Remover for DJJTB - V2 with Inpainting Options
**Type:** AI Tool — isolated venv: `wmrmvenv (Watermark)`
**Modes:**
  - 1. Yes, open all
  - 2. Yes, open first one only
  - 3. No
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes
  - 2. No
**Input:** folder, space-separated paths
**djj utils:** UI(get_path_input, get_string_input, prompt_choice, prompt_open_folder, what_next)
**Ext tools:** HuggingFace, NumPy, OpenCV, Pillow, PyTorch
**Key functions:** `ensure_venv_and_run`, `check_dependencies`, `process_images_batch`, `setup_model_cache`, `clean_path`, `collect_images_from_folder`, `collect_images_from_paths`, `get_valid_inputs`

### `djjtb/ai_tools/watermark_remover_pkfpl.py`
**Purpose:** AI Watermark Remover for DJJTB
**Type:** AI Tool — isolated venv: `wmrmvenv (Watermark)`
**Modes:**
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes
  - 2. No
  - 1. Yes, open all
  - 2. Yes, open first one only
  - 3. No
**Input:** folder, space-separated paths
**djj utils:** UI(get_path_input, get_string_input, prompt_choice, prompt_open_folder, what_next)
**Ext tools:** HuggingFace, NumPy, OpenCV, Pillow, PyTorch
**Key functions:** `ensure_venv_and_run`, `check_dependencies`, `setup_model_cache`, `clean_path`, `collect_images_from_folder`, `collect_images_from_paths`, `get_valid_inputs`, `process_images_batch`

### `djjtb/ai_tools/watermark_remover_ref.py`
**Purpose:** Reference-Based Watermark Remover for DJJTB - FIXED VERSION
**Type:** AI Tool — isolated venv: `wmrmvenv (Watermark)`
**Modes:**
  - 1. Yes
  - 2. No
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes
  - 2. No
  - 1. Use default (0.7)
  - 2. Custom threshold
  - 1. Yes (save to Output/Masks)
  - 2. No (temporary only)
**Input:** folder, space-separated paths
**djj utils:** UI(get_float_input, get_path_input, get_string_input, prompt_choice, prompt_open_folder, what_next)
**Ext tools:** NumPy, OpenCV, Pillow, PyTorch
**Key functions:** `ensure_venv_and_run`, `check_dependencies`, `collect_images_from_folder`, `collect_images_from_paths`, `get_reference_watermark`, `get_valid_inputs`, `get_processing_options`, `process_images_batch`

### `djjtb/ai_tools/watermark_remover_settings.txt.py`
**Purpose:** watermark remover settings.txt (ai tools)
**Ext tools:** OpenCV

### `djjtb/ai_tools/watermark_remover_unified.py`
**Purpose:** watermark remover unified (ai tools)
**Type:** AI Tool — isolated venv: `wmrmvenv (Watermark)`
**Modes:**
  - 1. Use default (0.7)
  - 2. Custom threshold
  - 1. Yes (save to Output/Masks)
  - 2. No (temporary only)
  - 1. Yes, open all
  - 2. Yes, open first one only
  - 3. No
**djj utils:** UI(get_float_input, get_string_input, prompt_choice, prompt_open_folder, what_next)
**Ext tools:** NumPy, OpenCV, Pillow

### `djjtb/ai_tools/comfyui/comfyui_batch.bak.py`
**Purpose:** ComfyUI Batch Processor - DJJTB Edition
**Modes:**
  - 1. Yes
  - 2. No
  - 1. Load from default folder
  - 2. Custom path
  - 1. Yes
  - 2. No (leave for review)
**Input:** folder, folder + subfolders
**Output:** DJJTB_output/ (centralized)
**djj utils:** UI(get_path_input, get_string_input, prompt_choice, what_next)
**Ext tools:** requests
**Key functions:** `get_next_job_id`, `get_todays_log_file`, `log_job`, `get_workflow_files`, `select_workflow_from_folder`, `main`, `load_workflow`, `get_images`

### `djjtb/ai_tools/comfyui/comfyui_batch.py`
**Purpose:** ComfyUI Batch Processor - DJJTB Edition
**Modes:**
  - 1. Folder
  - 2. Individual files
  - 1. Yes
  - 2. No
  - 1. Yes
  - 2. No (use workflow default)
  - 1. Yes
  - 2. No (leave for review)
  - 1. Yes
  - 2. No
**Input:** folder, folder + subfolders
**Output:** DJJTB_output/ (centralized)
**djj utils:** UI(get_path_input, get_string_input, prompt_choice, what_next)
**Ext tools:** requests
**Key functions:** `get_next_job_id`, `get_todays_log_file`, `log_job`, `get_images_from_folder`, `get_image_list_input`, `get_single_image_input`, `prompt_steps_override`, `get_workflow_files`

### `djjtb/ai_tools/comfyui/csv_to_prompt_library.py`
**Purpose:** CSV to Prompt Library JSON Converter
**Modes:**
  - 2. No
**djj utils:** UI(prompt_choice)
**Key functions:** `csv_to_json`, `copy_to_comfyui`, `create_example_csv`

### `djjtb/ai_tools/comfyui/json_to_prompt_csv.py`
**Purpose:** Prompt Library JSON to CSV Converter (Reverse Sync)
**Key functions:** `create_backup`, `json_to_csv`, `main`

### `djjtb/ai_tools/Prompt_Randomizer/Scripts/generate_attribute_files.py`
**Purpose:** generate attribute files (Scripts)
**Key functions:** `is_empty`

### `djjtb/ai_tools/Prompt_Randomizer/Scripts/prompt_randomizer.py`
**Purpose:** prompt randomizer (Scripts)


## 🗃️ File Tools

### `djjtb/file_tools/add_root_dir_prefix.py`
**Purpose:** add root dir prefix (file tools)
**Input:** folder
**djj utils:** UI(get_path_input, prompt_open_folder, what_next)
**Key functions:** `main`

### `djjtb/file_tools/auto_subfolder.py`
**Purpose:** auto subfolder (file tools)
**Modes:**
  - 1. Yes
  - 2. No
  - 1. Yes
  - 2. No
  - 1. Yes
  - 2. No
**Input:** folder, space-separated paths, txt file
**djj utils:** UI(get_path_input, get_paths_from_txt, prompt_choice, prompt_open_folder, what_next)
**Key functions:** `get_undo_dir`, `list_undo_manifests`, `save_undo_manifest`, `run_undo`, `collect_files_from_folder`, `collect_files_from_paths`, `collect_files_from_txt`, `sort_files_by_pattern`

### `djjtb/file_tools/file_identifier.py`
**Purpose:** Enhanced File Identifier Tool
**Modes:**
  - 1. Analyze all files
  - 2. Select specific files
  - 1. Yes, analyze all
  - 2. No, go back
  - 1. Folder path
  - 2. Space-separated file paths
  - 1. Yes, 2. No
  - 1. Yes
  - 2. No
  - 1. Yes
**Input:** folder, space-separated paths
**djj utils:** UI(get_path_input, prompt_choice, what_next) | Tabs(setup_terminal)
**Key functions:** `clean_path`, `detect_true_file_type`, `get_file_type_by_extension`, `collect_and_select_files`, `get_file_info_enhanced`, `export_to_csv`, `main`

### `djjtb/file_tools/filename_randomizer.py`
**Purpose:** filename randomizer (file tools)
**Input:** folder, folder + subfolders, space-separated paths
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next)
**Key functions:** `collect_files`, `collect_files_from_paths`, `collect_folders`, `rename_files`, `rename_folders`

### `djjtb/file_tools/plist_converter.py`
**Purpose:** plist converter (file tools)
**djj utils:** UI(prompt_choice, what_next)
**Key functions:** `header`, `prompt_conversion_mode`, `convert_plist_to_json`, `convert_json_to_plist`, `run_conversion`, `main`

### `djjtb/file_tools/readme_generator.py`
**Purpose:** Universal README Generator
**Modes:**
  - 1. Yes (requires Ollama)
  - 2. No (basic analysis)
  - 1. In the project folder
  - 2. Desktop
  - 3. Custom location
  - 1. Yes
  - 2. No
**Input:** folder
**djj utils:** UI(get_path_input, get_string_input, prompt_choice, prompt_open_folder, wait_with_skip, what_next)
**Ext tools:** HuggingFace, PyTorch, requests
**Key functions:** `main`, `analyze_python_file`, `analyze_shell_file`, `setup_ollama`, `enhance_description`, `scan_directory`, `generate_readme`, `save_readme`

### `djjtb/file_tools/symlink_randomizer.py`
**Purpose:** symlink randomizer (file tools)

### `djjtb/file_tools/x_to_w_copy.py`
**Purpose:** X-to-W Folder Broadcaster — DJJTB File Tools
**Modes:**
  - 1. Yes
  - 2. No
**Input:** folder
**djj utils:** UI(get_path_input, prompt_choice, prompt_open_folder, what_next)
**Key functions:** `x_index_to_letter`, `collect_sorted_files`, `strip_suffix_token`, `build_new_filename`, `scan_base_folder`, `preview`, `run_copy`, `main`


## ⚡ Quick Tools

### `djjtb/quick_tools/app_launcher.py`
**Purpose:** app launcher (quick tools)
**djj utils:** UI(prompt_choice, wait_with_skip)

### `djjtb/quick_tools/auto_scroller.py`
**Purpose:** auto scroller (quick tools)
**Key functions:** `scroll_loop`, `on_press`, `on_release`

### `djjtb/quick_tools/link_grabber.py`
**Purpose:** link grabber (quick tools)
**Output:** DJJTB_output/ (centralized)
**Ext tools:** BeautifulSoup, requests
**Key functions:** `get_today_filenames`, `extract_extension`, `get_page_title`, `get_domain`, `log_link`, `main`

### `djjtb/quick_tools/link_scraper.py`
**Purpose:** Enhanced Link Scraper Tool for DJJTB
**Modes:**
  - 1. Yes, add unpadded
  - 2. No, skip it
  - 1. Yes
  - 2. No
  - 1. Import from text file
  - 2. Enter custom links
  - 3. Use default slink.txt
  - 1. Standard (requests) - faster
  - 2. Browser automation (Selenium) - handles dynamic content
  - 1. No login required
**Input:** folder, space-separated paths
**Output:** DJJTB_output/ (centralized)
**djj utils:** UI(get_int_input, get_path_input, prompt_choice, prompt_open_folder)
**Ext tools:** BeautifulSoup, Selenium, requests
**Key functions:** `create_output_directories`, `get_domain_name`, `get_page_title`, `parse_keywords`, `generate_links`, `export_generated_links`, `get_links_with_keywords_requests`, `perform_login`

### `djjtb/quick_tools/media_info_viewer.py`
**Purpose:** media info viewer (quick tools)
**Input:** folder, folder + subfolders, space-separated paths
**Ext tools:** OpenCV, Pillow
**Key functions:** `main`, `initUI`, `keyPressEvent`, `paste_file_path`, `handleLinkClick`, `dragEnterEvent`, `dropEvent`, `openFileDialog`

### `djjtb/quick_tools/multi_xmp_viewer.py`
**Purpose:** multi xmp viewer (quick tools)
**Key functions:** `main`, `run`, `init_ui`, `init_image_preview`, `select_image_folder`, `select_txt_folder`, `select_xmp_folders`, `update_status`

### `djjtb/quick_tools/path_grabber.py`
**Purpose:** path grabber (quick tools)
**Output:** DJJTB_output/ (centralized)
**Key functions:** `get_today_filenames`, `get_path_info`, `is_valid_path`, `extract_paths_from_text`, `log_path`, `main`

### `djjtb/quick_tools/pdf_extractor.py`
**Purpose:** pdf extractor (quick tools)

### `djjtb/quick_tools/reverse_image_search.py`
**Purpose:** reverse image search (quick tools)
**Ext tools:** Selenium
**Key functions:** `main`, `initUI`, `keyPressEvent`, `paste_from_clipboard`, `dragEnterEvent`, `openFileDialog`, `process_image`, `paste_file_path`

### `djjtb/quick_tools/rsync_helper.py`
**Purpose:** DJJTB Rsync Helper
**Modes:**
  - 1. Folder path
  - 2. Multiple files/folders (space-separated)
  - 1. Yes
  - 2. No
  - 1. Same location as source ({default_dest})
  - 2. Custom path
  - 1. Yes
  - 2. No
**Input:** folder, folder + subfolders, multi-file drag+drop, space-separated paths
**djj utils:** UI(get_multifile_input, get_path_input, prompt_choice, prompt_open_folder, what_next)
**Key functions:** `filter_files_by_extensions`, `collect_files_from_folder`, `get_source_input`, `get_destination_path`, `perform_rsync`, `main`


## 🔧 Helpers

### `djjtb/helpers/ansi_colors.py`
**Purpose:** ansi colors (helpers)

### `djjtb/helpers/ckpt_ncnn_convert.py`
**Purpose:** ckpt ncnn convert (helpers)
**Ext tools:** PyTorch

### `djjtb/helpers/ckpt_pth_convert.py`
**Purpose:** ckpt pth convert (helpers)
**Ext tools:** PyTorch

### `djjtb/helpers/clean_florence_completely.py`
**Purpose:** Complete Florence-2 Cache Cleaner

### `djjtb/helpers/djj.readme_generator.py`
**Purpose:** Auto README Generator
**djj utils:** UI(prompt_choice) | get_centralized_media_input, get_centralized_output_path
**Ext tools:** FFmpeg, HuggingFace, Pillow, PyTorch, requests

### `djjtb/helpers/dup_line_cleaner.py`
**Purpose:** dup line cleaner (helpers)
**Output:** DJJTB_output/ (centralized)

### `djjtb/helpers/duplicate_file_with_prefix.py`
**Purpose:** duplicate file with prefix (helpers)

### `djjtb/helpers/duplicate_file_with_prefix_B.py`
**Purpose:** duplicate file with prefix B (helpers)

### `djjtb/helpers/duplicate_file_with_prefix_C.py`
**Purpose:** duplicate file with prefix C (helpers)
**Output:** Output/Comp/

### `djjtb/helpers/extract_filenames_mergeURL.py`
**Purpose:** extract filenames mergeURL (helpers)

### `djjtb/helpers/files_to_folders.py`
**Purpose:** files to folders (helpers)
**Input:** folder

### `djjtb/helpers/fix_florence_cache.py`
**Purpose:** Fix Florence-2 model cache for M4 Mac Studio
**Ext tools:** HuggingFace

### `djjtb/helpers/fix_florence_comprehensive.py`
**Purpose:** Comprehensive Florence-2 MPS Fix
**Ext tools:** HuggingFace
**Key functions:** `fix_pattern1`

### `djjtb/helpers/fix_florence_model_code.py`
**Purpose:** Fix Florence-2 model code for MPS beam search compatibility
**Ext tools:** HuggingFace

### `djjtb/helpers/fix_numpy_conflict.py`
**Purpose:** M4 Mac Studio - Fix NumPy Conflict
**Type:** AI Tool — isolated venv: `wmrmvenv (Watermark)`
**Ext tools:** HuggingFace, NumPy, OpenCV, Pillow, PyTorch

### `djjtb/helpers/joytag_summary_export.py`
**Purpose:** joytag summary export (helpers)
**Key functions:** `prompt_folder`, `collect_txt_files`, `parse_tag_file`, `analyze_tags`, `export_csv`, `main`

### `djjtb/helpers/mergetxt.py`
**Purpose:** mergetxt (helpers)

### `djjtb/helpers/mergetxt2.py`
**Purpose:** mergetxt2 (helpers)

### `djjtb/helpers/patch_caption_script.py`
**Purpose:** PATCH for image_caption_generator.py
**Ext tools:** PyTorch

### `djjtb/helpers/patch_caption_script_v2.py`
**Purpose:** PATCH 2: Fix image processing on MPS
**Ext tools:** Pillow, PyTorch

### `djjtb/helpers/patch_caption_script_v3.py`
**Purpose:** PATCH 3: Fix beam search on MPS

### `djjtb/helpers/replace_decor_lines_adaptive.py`
**Purpose:** replace decor lines adaptive (helpers)
**Key functions:** `get_terminal_width`, `replace_in_file`, `repl`

### `djjtb/helpers/replace_decor_lines_fixed.py`
**Purpose:** replace decor lines fixed (helpers)
**Key functions:** `replace_in_file`, `repl`

### `djjtb/helpers/scan_djj_usage.py`
**Purpose:** scan djj usage (helpers)

### `djjtb/helpers/transition_helper.py`
**Purpose:** Transition Helper for DJJTB - Reusable dissolve transition logic
**Ext tools:** FFmpeg
**Key functions:** `create_dissolve_slideshow`, `calculate_slideshow_duration`

### `djjtb/helpers/update_tools.py`
**Purpose:** update tools (helpers)
**djj utils:** Tabs(cleanup_tabs)
**Key functions:** `update_script`

### `djjtb/helpers/vlc_renamer.py`
**Purpose:** vlc renamer (helpers)
**Key functions:** `is_vlc_running`, `get_video_filepath`, `get_next_filename`, `wait_for_vlc`, `monitor_screenshots`, `main`

### `djjtb/helpers/vlc_renamer_manual.py`
**Purpose:** vlc renamer manual (helpers)
**Key functions:** `get_video_filepath`, `get_next_filename`, `main`

### `djjtb/helpers/xmp_face_merger.py`
**Purpose:** XMP Region Data Merger
**Key functions:** `parse_xmp_file`, `find_regions_data`, `remove_existing_regions`, `add_regions_data`, `merge_xmp_regions`, `batch_merge_regions`

### `djjtb/helpers/xmp_region_merger.py`
**Purpose:** XMP Region Data Merger
**Key functions:** `make_writable`, `patched_et_write`, `patched_copy2`, `patched_move`, `patched_open`, `parse_xmp_file`, `find_regions_data`, `remove_existing_regions`


---
## PathManager (Planned Central I/O)

`PathManager` exists in `utils.py` but is not yet widely adopted. The planned refactor is to have the launcher pass input/output paths to scripts via `PathManager` so results can chain between tools. Most scripts still handle their own I/O independently.

Scripts that have adopted `PathManager`: none yet at scale.
Scripts that are candidates for early adoption: `image_pairing.py`, `video_slideshow_watermark.py`
