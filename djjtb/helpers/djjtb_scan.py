#!/usr/bin/env python3
"""
DJJTB Script Scanner
Generates a compact AI-readable context file summarizing every script in the DJJTB project.
Output is designed to be dropped into a Claude project for session onboarding.
Run from: ~/Documents/Scripts/DJJTB/ with venv active
"""

import os
import re
import ast
import sys
from pathlib import Path
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────────

PROJECT_ROOT  = Path("/Users/home/Documents/Scripts/DJJTB")
SCRIPTS_ROOT  = PROJECT_ROOT / "djjtb"
OUTPUT_FILE   = PROJECT_ROOT / "DJJTB_AI_CONTEXT.md"

# Folders to skip entirely
SKIP_DIRS = {'__pycache__', 'bak', '.git', 'test', 'legacy', 'venv', 'jtvenv',
             'upsvenv', 'wmrmvenv', 'cfuivenv'}

# Files to skip
SKIP_FILES = {'__init__.py'}

# Known djj.* utility functions — used to summarize what each script pulls from utils
DJJ_UTILS = [
    'prompt_choice', 'get_path_input', 'get_int_input', 'get_float_input',
    'get_string_input', 'get_paths_from_txt', 'get_multifile_input',
    'what_next', 'prompt_open_folder', 'apply_skip_list', 'load_skip_list',
    'should_skip', 'tag_source_files', 'collect_media_files', 'get_media_input',
    'join_image_video', 'create_collage', 'create_dissolve_slideshow',
    'position_suffix', 'clamp_to_longest_edge', 'build_slideshow_and_join',
    'build_collage_and_join', 'get_join_dimensions', 'get_audio_options',
    'setup_logging', 'run_script_in_tab', 'run_command_in_tab',
    'open_terminal_with_settings', 'switch_to_terminal_tab', 'cleanup_tabs',
    'wait_with_skip', 'setup_terminal', 'PathManager', 'path_manager',
    'get_centralized_media_input', 'get_centralized_output_path',
    'open_multiple_folders', 'open_path', 'open_app', 'launch_app',
    'filter_images_without_xmp', 'prompt_xmp_handling_mode',
    'calculate_slideshow_duration',
]

# Known external tools detected via subprocess/imports
TOOL_SIGNALS = {
    'ffmpeg': 'FFmpeg',
    'ffprobe': 'FFmpeg',
    'PIL': 'Pillow',
    'cv2': 'OpenCV',
    'torch': 'PyTorch',
    'transformers': 'HuggingFace',
    'requests': 'requests',
    'selenium': 'Selenium',
    'bs4': 'BeautifulSoup',
    'numpy': 'NumPy',
    'timm': 'timm',
}

# Output folder patterns — detect where each script writes its results
OUTPUT_PATTERNS = [
    (r'Output.*?Paired',       'Output/Paired/'),
    (r'Output.*?Joined',       'Output/Joined/'),
    (r'Output.*?Comp_Joined',  'Output/Comp_Joined/'),
    (r'Output.*?Comp\b',       'Output/Comp/'),
    (r'Output.*?Slideshow',    'Output/Slideshow_Joined/'),
    (r'Output.*?Collage',      'Output/Collage_Joined/'),
    (r'Output.*?Frames',       'Output/Frames/'),
    (r'Output.*?Stripped',     'Output/Stripped/'),
    (r'Output.*?Captions',     'Output/Captions/'),
    (r'"CF"',                  'input/CF/'),
    (r'"UPS"',                 'input/UPS/'),
    (r'"CFUP"',                'input/Output/CFUP/'),
    (r'"UPCF"',                'input/Output/UPCF/'),
    (r'Watermarked',           'input/Watermarked/'),
    (r'Slideshows',            'input/Slideshows/'),
    (r'Joined\b',              'input/Joined/'),
    (r'Desktop.*?Playlists',   '~/Desktop/Playlists/'),
    (r'DJJTB_output',          'DJJTB_output/ (centralized)'),
]

# Input mode signals
INPUT_SIGNALS = {
    'folder path':         'folder',
    'get_path_input':      'folder',
    'include_subfolders':  'folder + subfolders',
    'get_paths_from_txt':  'txt file',
    'plink.txt':           'default txt (plink.txt)',
    'space-separated':     'space-separated paths',
    'get_multifile_input': 'multi-file drag+drop',
}

# Venv signals — detect AI tools that use isolated venvs
VENV_SIGNALS = {
    'cfvenv':    'cfvenv (CodeFormer)',
    'upsvenv':   'upsvenv (Upscaler)',
    'jtvenv':    'jtvenv (JoyTag)',
    'wmrmvenv':  'wmrmvenv (Watermark)',
    'jcvenv':    'jcvenv (JoyCaption)',
    'ffvenv':    'ffvenv (FaceFusion)',
}


# ─── AST Helpers ──────────────────────────────────────────────────────────────

def get_module_docstring(source: str) -> str:
    """Extract module-level docstring."""
    try:
        tree = ast.parse(source)
        ds = ast.get_docstring(tree)
        if ds:
            return ds.split('\n')[0].strip()
    except Exception:
        pass
    return ''


def get_top_functions(source: str) -> list[str]:
    """Get names of top-level functions (not nested)."""
    try:
        tree = ast.parse(source)
        return [
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and not node.name.startswith('_')
        ]
    except Exception:
        return []


def get_imports(source: str) -> list[str]:
    """Get all imported module names."""
    imports = set()
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
    except Exception:
        pass
    return sorted(imports)


# ─── Script Analysis ──────────────────────────────────────────────────────────

def analyze_script(path: Path) -> dict:
    """Analyze a single script and return a structured summary dict."""
    try:
        source = path.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        return {'error': str(e)}

    info = {
        'path':         str(path.relative_to(PROJECT_ROOT)),
        'name':         path.stem,
        'docstring':    '',
        'purpose':      '',
        'modes':        [],
        'input_modes':  [],
        'output_dirs':  [],
        'djj_utils':    [],
        'ext_tools':    [],
        'venv':         None,
        'functions':    [],
        'has_main':     False,
        'is_launcher':  False,
        'is_utils':     False,
        'uses_subprocess_venv': False,
        'ai_tool':      False,
    }

    # Docstring
    info['docstring'] = get_module_docstring(source)

    # Functions
    info['functions'] = get_top_functions(source)
    info['has_main'] = 'def main(' in source

    # Launcher / utils detection
    info['is_launcher'] = 'DJJTBLauncher' in source or 'show_main_menu' in source
    info['is_utils'] = path.name in ('utils.py', 'media_utils.py')

    # Modes — look for prompt_choice with numbered mode options
    mode_matches = re.findall(
        r'prompt_choice\s*\(\s*["\'].*?(?:mode|Mode)[^"\']*["\'].*?\[([^\]]+)\]',
        source, re.DOTALL
    )
    # Also detect top_mode / mode variable patterns
    top_mode_labels = re.findall(
        r'(?:top_mode|mode)\s*==\s*["\'](\d)["\'].*?#.*?([^\n]+)', source
    )

    # Detect named modes from prompt text blocks
    mode_blocks = re.findall(
        r'prompt_choice\s*\(\s*[f"\']{1,3}(.*?)[f"\']{1,3}\s*,\s*\[',
        source, re.DOTALL
    )
    named_modes = []
    for block in mode_blocks:
        lines = [l.strip() for l in block.split('\\n') if re.match(r'\d+\.', l.strip())]
        named_modes.extend(lines[:6])  # cap at 6 per block
    if named_modes:
        info['modes'] = named_modes[:10]  # cap total

    # Input modes
    detected_inputs = set()
    for signal, label in INPUT_SIGNALS.items():
        if signal in source:
            detected_inputs.add(label)
    info['input_modes'] = sorted(detected_inputs)

    # Output dirs
    detected_outputs = set()
    for pattern, label in OUTPUT_PATTERNS:
        if re.search(pattern, source):
            detected_outputs.add(label)
    info['output_dirs'] = sorted(detected_outputs)

    # djj.* utils used
    detected_djj = set()
    for util in DJJ_UTILS:
        if f'djj.{util}' in source or f'djj.{util}(' in source:
            detected_djj.add(util)
    info['djj_utils'] = sorted(detected_djj)

    # External tools
    detected_tools = set()
    imports = get_imports(source)
    for imp in imports:
        if imp in TOOL_SIGNALS:
            detected_tools.add(TOOL_SIGNALS[imp])
    for keyword, label in TOOL_SIGNALS.items():
        if keyword in source:
            detected_tools.add(label)
    info['ext_tools'] = sorted(detected_tools)

    # Venv detection
    for venv_key, venv_label in VENV_SIGNALS.items():
        if venv_key in source:
            info['venv'] = venv_label
            info['ai_tool'] = True
            break

    # Subprocess venv pattern (AI tools that re-exec under isolated venv)
    if 'os.execve' in source or 'VENV_PYTHON' in source:
        info['uses_subprocess_venv'] = True
        info['ai_tool'] = True

    # Purpose: prefer docstring, fallback to filename heuristic
    if info['docstring']:
        info['purpose'] = info['docstring']
    elif info['is_launcher']:
        info['purpose'] = 'Main DJJTB launcher — interactive menu system, tab management, app launching'
    elif info['is_utils']:
        info['purpose'] = 'Shared utility functions imported by all scripts as djjtb.utils (djj.*)'
    else:
        # Derive from filename
        name = path.stem.replace('_', ' ')
        category = path.parent.name.replace('_', ' ')
        info['purpose'] = f'{name} ({category})'

    return info


# ─── Collect Scripts ──────────────────────────────────────────────────────────

def collect_scripts() -> dict[str, list[Path]]:
    """Walk SCRIPTS_ROOT and return scripts grouped by category folder."""
    groups = {}

    for root, dirs, files in os.walk(SCRIPTS_ROOT):
        # Prune skip dirs in-place
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.endswith('venv')]

        root_path = Path(root)
        rel = root_path.relative_to(SCRIPTS_ROOT)
        # Category = first part of relative path, or 'root' for top level
        category = str(rel.parts[0]) if rel.parts else 'root'

        for fname in sorted(files):
            if fname in SKIP_FILES or not fname.endswith('.py'):
                continue
            fpath = root_path / fname
            groups.setdefault(category, []).append(fpath)

    return groups


# ─── Format Output ────────────────────────────────────────────────────────────

def format_script_block(info: dict) -> str:
    """Format one script's summary as a markdown block."""
    if 'error' in info:
        return f"### `{info.get('path', 'unknown')}`\n⚠️ Could not parse: {info['error']}\n\n"

    lines = []
    lines.append(f"### `{info['path']}`")

    lines.append(f"**Purpose:** {info['purpose']}")

    if info['ai_tool']:
        venv_note = f" — isolated venv: `{info['venv']}`" if info['venv'] else ' — subprocess/venv pattern'
        lines.append(f"**Type:** AI Tool{venv_note}")

    if info['modes']:
        lines.append(f"**Modes:**")
        for m in info['modes']:
            lines.append(f"  - {m}")

    if info['input_modes']:
        lines.append(f"**Input:** {', '.join(info['input_modes'])}")

    if info['output_dirs']:
        lines.append(f"**Output:** {', '.join(info['output_dirs'])}")

    if info['djj_utils']:
        # Group into meaningful clusters
        ui      = [u for u in info['djj_utils'] if u in ('prompt_choice','get_path_input','get_int_input','get_float_input','get_string_input','get_paths_from_txt','get_multifile_input','what_next','prompt_open_folder','wait_with_skip')]
        media   = [u for u in info['djj_utils'] if u in ('join_image_video','create_collage','create_dissolve_slideshow','position_suffix','clamp_to_longest_edge','build_slideshow_and_join','build_collage_and_join','get_join_dimensions','get_audio_options','collect_media_files','get_media_input')]
        skip    = [u for u in info['djj_utils'] if u in ('apply_skip_list','load_skip_list','should_skip')]
        tab     = [u for u in info['djj_utils'] if u in ('run_script_in_tab','run_command_in_tab','open_terminal_with_settings','switch_to_terminal_tab','cleanup_tabs','setup_terminal')]
        other   = [u for u in info['djj_utils'] if u not in ui+media+skip+tab]

        clusters = []
        if ui:     clusters.append(f"UI({', '.join(ui)})")
        if media:  clusters.append(f"Media({', '.join(media)})")
        if skip:   clusters.append(f"SkipList({', '.join(skip)})")
        if tab:    clusters.append(f"Tabs({', '.join(tab)})")
        if other:  clusters.append(', '.join(other))
        lines.append(f"**djj utils:** {' | '.join(clusters)}")

    if info['ext_tools']:
        lines.append(f"**Ext tools:** {', '.join(info['ext_tools'])}")

    if info['functions'] and not info['is_utils'] and not info['is_launcher']:
        # Only show meaningful public functions, cap at 8
        fns = [f for f in info['functions'] if not f.startswith('_')][:8]
        if fns:
            lines.append(f"**Key functions:** `{'`, `'.join(fns)}`")

    lines.append('')  # blank line between scripts
    return '\n'.join(lines) + '\n'


def format_category_header(category: str) -> str:
    labels = {
        'root':        '## 🗂️ Root / Shared',
        'media_tools': '## 🎞️ Media Tools',
        'ai_tools':    '## 🤖 AI Tools',
        'file_tools':  '## 🗃️ File Tools',
        'quick_tools': '## ⚡ Quick Tools',
        'helpers':     '## 🔧 Helpers',
    }
    label = labels.get(category, f'## 📁 {category.replace("_", " ").title()}')
    return f'\n{label}\n\n'


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print()
    print("\033[92m==================================================\033[0m")
    print("\033[1;93mDJJTB Script Scanner\033[0m")
    print("Generates AI context file from project scripts")
    print("\033[92m==================================================\033[0m")
    print()

    if not SCRIPTS_ROOT.exists():
        print(f"\033[93m❌ Scripts root not found:\033[0m {SCRIPTS_ROOT}")
        sys.exit(1)

    print(f"\033[93mScanning:\033[0m {SCRIPTS_ROOT}")
    groups = collect_scripts()
    total = sum(len(v) for v in groups.values())
    print(f"\033[92m✅ Found {total} scripts across {len(groups)} categories\033[0m")
    print()

    # ── Build output ──────────────────────────────────────────────────────────
    out = []

    # Header
    out.append("# DJJTB — AI Context Reference\n")
    out.append(f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} by djjtb_scan.py_\n\n")

    out.append("## About DJJTB\n\n")
    out.append(
        "DJJTB (DJJ Toolbox) is a personal Python CLI toolkit of ~20–30 scripts for media processing "
        "and AI tools, launched via AppleScript terminal tabs from a central `djjtb.py` launcher.\n\n"
        "- **Project root:** `/Users/home/Documents/Scripts/DJJTB/`\n"
        "- **Scripts live in:** `DJJTB/djjtb/` (nested by category)\n"
        "- **Main venv:** `~/Documents/Scripts/DJJTB/venv`\n"
        "- **Shared utils:** `djjtb/utils.py` — imported everywhere as `import djjtb.utils as djj`\n"
        "- **Media utils:** `djjtb/media_utils.py` — re-exported via utils, callable as `djj.*`\n"
        "- **AI tools** use isolated venvs (joytag: `jtvenv`, upscaler: `upsvenv`, watermark: `wmrmvenv`)\n"
        "- **Template/pattern source:** `codeformer_runner.py` — canonical script structure\n\n"
    )

    out.append("## Key Conventions\n\n")
    out.append(
        "- All selections via `djj.prompt_choice()` — never raw `input()` for options\n"
        "- All questions asked **upfront** before processing begins\n"
        "- Output routed to named subfolders: `parent/Output/ToolName/`\n"
        "- `what_next()` loop at end of every script\n"
        "- `prompt_open_folder()` offered after processing\n"
        "- `tag_source_files()` for Finder tagging of processed files\n"
        "- Skip list at `/Users/home/Documents/Scripts/DJJTB_output/skip_list.txt`\n"
        "- `apply_skip_list(files, root=input_folder)` — one line after file collection\n"
        "- Undo manifests: `.djjtb/` hidden folder inside input folder, JSON stackable\n\n"
    )

    out.append("## Environment\n\n")
    out.append(
        "- Mac Studio M4 Max, 64GB unified memory, macOS Sequoia\n"
        "- Python 3.11.9 (DMG install), pip venvs only (no conda)\n"
        "- FFmpeg is the core media processing engine\n"
        "- MPS backend for PyTorch (Apple Silicon) — CUDA ops will fail\n"
        "- Known MPS blockers: `basicsr`, `realesrgan`, FP8 dtypes, CUDA-hardcoded code\n\n"
    )

    # Category order preference
    cat_order = ['root', 'media_tools', 'ai_tools', 'file_tools', 'quick_tools', 'helpers']
    all_cats  = list(groups.keys())
    ordered   = [c for c in cat_order if c in all_cats]
    ordered  += [c for c in all_cats if c not in ordered]

    for category in ordered:
        scripts = groups[category]
        if not scripts:
            continue

        out.append(format_category_header(category))

        for script_path in scripts:
            print(f"  Analyzing: {script_path.relative_to(PROJECT_ROOT)}")
            info = analyze_script(script_path)
            out.append(format_script_block(info))

    # Footer
    out.append("\n---\n")
    out.append(
        "## PathManager (Planned Central I/O)\n\n"
        "`PathManager` exists in `utils.py` but is not yet widely adopted. "
        "The planned refactor is to have the launcher pass input/output paths to scripts "
        "via `PathManager` so results can chain between tools. "
        "Most scripts still handle their own I/O independently.\n\n"
        "Scripts that have adopted `PathManager`: none yet at scale.\n"
        "Scripts that are candidates for early adoption: `image_pairing.py`, `video_slideshow_watermark.py`\n"
    )

    # Write file
    content = ''.join(out)
    OUTPUT_FILE.write_text(content, encoding='utf-8')

    print()
    print(f"\033[92m✅ Context file written to:\033[0m")
    print(f"   {OUTPUT_FILE}")
    print(f"\033[93mSize:\033[0m {len(content):,} characters / ~{len(content)//4:,} tokens")
    print()
    print("\033[93mDrop DJJTB_AI_CONTEXT.md into your Claude project files\033[0m")
    print("\033[93mfor instant context in future sessions.\033[0m")
    print()


if __name__ == "__main__":
    main()