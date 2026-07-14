    #!/usr/bin/env python3
"""
ComfyUI Batch Processor - DJJTB Edition
Processes images through ComfyUI workflows using symlinks
Supports single-input and dual-input (e.g. pose transfer) workflows
"""

import os
import json
import copy
import requests
import time
from pathlib import Path
from datetime import datetime
import djjtb.utils as djj

# ComfyUI server address
COMFYUI_URL = "http://127.0.0.1:8188"

# ComfyUI input folder
COMFYUI_INPUT_FOLDER = "/Users/home/Documents/ai_models/ComfyUI_App/ComfyUI/input"

# Default workflow folders
DEFAULT_WORKFLOW_FOLDER      = "/Volumes/Movies_2SSD/ComfyUI.bak/user/default/workflows/API"
DEFAULT_WORKFLOW_FOLDER_QWEN = "/Volumes/Movies_2SSD/ComfyUI.bak/user/default/workflows/API/Qwen_CN"

# Log file location
LOG_FOLDER       = Path("/Users/home/Documents/Scripts/DJJTB_output/comfyui_batch_logs")
JOB_COUNTER_FILE = LOG_FOLDER / "job_counter.txt"

# Supported image formats
IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.bmp']

# Wait time between submissions (seconds)
QUEUE_DELAY = 1

# Default node IDs for the Qwen pose-transfer workflow
QWEN_SOURCE_NODE_ID = "151"   # LoadImageReturnFilename — subject (OG)
QWEN_POSE_NODE_ID   = "162"   # LoadImageReturnFilename — pose reference

# KSampler node ID and steps config
KSAMPLER_NODE_ID    = "3"
KSAMPLER_STEPS_IDX  = 2       # index of 'steps' in widgets_values
DEFAULT_STEPS       = 4


# ─────────────────────────────────────────────────────────────────────────────
#  Job ID / logging
# ─────────────────────────────────────────────────────────────────────────────

def get_next_job_id():
    LOG_FOLDER.mkdir(parents=True, exist_ok=True)
    if JOB_COUNTER_FILE.exists():
        try:
            with open(JOB_COUNTER_FILE, 'r') as f:
                current_id = int(f.read().strip())
        except Exception:
            current_id = 0
    else:
        current_id = 0
    next_id = current_id + 1
    with open(JOB_COUNTER_FILE, 'w') as f:
        f.write(str(next_id))
    return f"{next_id:05d}"


def get_todays_log_file():
    LOG_FOLDER.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    return LOG_FOLDER / f"{today}.log"


def log_job(job_id, workflow_path, mode_label, pairs, steps_override=None):
    """Log job info to today's log file.
    pairs = list of (src, ref) tuples  OR  plain Path objects (single-input).
    """
    log_file  = get_todays_log_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry  = f"\n{'=' * 70}\n"
    log_entry += f"JOB ID:        {job_id}\n"
    log_entry += f"TIME:          {timestamp}\n"
    log_entry += f"WORKFLOW:      {Path(workflow_path).name}\n"
    log_entry += f"WORKFLOW PATH: {workflow_path}\n"
    log_entry += f"MODE:          {mode_label}\n"
    if steps_override is not None:
        log_entry += f"STEPS:         {steps_override} (overridden)\n"
    log_entry += f"TOTAL JOBS:    {len(pairs)}\n"
    log_entry += "PAIRS:\n"

    for i, pair in enumerate(pairs, 1):
        if isinstance(pair, tuple):
            src, ref = pair
            log_entry += f"  {i:3}. SOURCE: {Path(src).name}  |  POSE REF: {Path(ref).name}\n"
        else:
            log_entry += f"  {i:3}. {Path(pair).name}\n"

    log_entry += f"{'=' * 70}\n"

    with open(log_file, 'a') as f:
        f.write(log_entry)

    return log_file


# ─────────────────────────────────────────────────────────────────────────────
#  Image / path input helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_images_from_folder(folder_path, include_subfolders=False):
    """Return a sorted list of image Paths from a folder."""
    folder = Path(folder_path)
    images = []
    if not folder.exists():
        print(f"❌ \033[93mFolder not found:\033[0m {folder_path}")
        return images
    if include_subfolders:
        for root, _, files in os.walk(folder):
            for f in files:
                if any(f.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                    images.append(Path(root) / f)
    else:
        for f in folder.iterdir():
            if f.is_file() and any(f.name.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                images.append(f)
    return sorted(images)


def get_image_list_input(label):
    """
    Ask user: folder OR individual files.
    Returns a sorted list of Path objects.
    """
    print()
    mode = djj.prompt_choice(
        f"\033[93m{label} — input method:\033[0m\n1. Folder\n2. Individual files",
        ['1', '2'],
        default='1'
    )
    print()

    if mode == '1':
        folder = djj.get_path_input(f"📁 Folder path for {label}")
        print()
        include_sub = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        images = get_images_from_folder(folder, include_sub)
        if not images:
            print(f"❌ \033[93mNo images found in folder.\033[0m")
        return images
    else:
        print(f"\033[93mEnter file paths for {label}, one per line.\033[0m")
        print("\033[93mPress Enter on an empty line when done.\033[0m")
        paths = []
        while True:
            raw = input(" > ").strip().strip("'\"")
            if not raw:
                break
            p = Path(raw)
            if p.exists() and p.is_file():
                paths.append(p)
                print(f"  ✅ \033[92mAdded:\033[0m {p.name}")
            else:
                print(f"  ⚠️  \033[93mNot found, skipped:\033[0m {raw}")
        return sorted(paths)


def get_single_image_input(label):
    """Ask for one image path. Returns Path or None."""
    print()
    raw = djj.get_path_input(f"🖼️  {label} image path")
    print()
    p = Path(raw)
    if not p.exists() or not p.is_file():
        print(f"❌ \033[93mFile not found:\033[0m {raw}")
        return None
    return p


def prompt_steps_override():
    """
    Ask user if they want to override KSampler steps.
    Returns an int if overriding, or None to leave workflow as-is.
    """
    print()
    override = djj.prompt_choice(
        f"\033[93m⚡ Override KSampler steps?\033[0m (node {KSAMPLER_NODE_ID})\n1. Yes\n2. No (use workflow default)",
        ['1', '2'],
        default='2'
    )
    print()
    if override == '2':
        return None

    raw = djj.get_string_input(
        f"\033[93m🔢 Steps\033[0m (default: {DEFAULT_STEPS}):\n > ",
        default=str(DEFAULT_STEPS)
    )
    print()
    try:
        steps = int(raw)
        print(f"✅ \033[92mSteps set to:\033[0m {steps}")
        return steps
    except (ValueError, TypeError):
        print(f"⚠️  \033[93mInvalid input, using default:\033[0m {DEFAULT_STEPS}")
        return DEFAULT_STEPS


# ─────────────────────────────────────────────────────────────────────────────
#  Workflow file selector
# ─────────────────────────────────────────────────────────────────────────────

def get_workflow_files(folder_path):
    folder = Path(folder_path)
    if not folder.exists():
        return []
    return sorted([f for f in folder.glob('*.json') if f.is_file()])


def select_workflow_from_folder(folder_path):
    workflows = get_workflow_files(folder_path)
    if not workflows:
        print(f"❌ \033[93mNo workflow JSON files found in:\033[0m {folder_path}")
        return None
    print()
    print(f"\033[93m📂 Workflows in:\033[0m {Path(folder_path).name}")
    print("\033[93m" + "-" * 50 + "\033[0m")
    for i, wf in enumerate(workflows, 1):
        print(f"{i:2}. {wf.name}")
    print("\033[93m" + "-" * 50 + "\033[0m")
    print()
    valid  = [str(i) for i in range(1, len(workflows) + 1)]
    choice = djj.prompt_choice("\033[93mSelect workflow number\033[0m", valid, default='1')
    selected = workflows[int(choice) - 1]
    print(f"✅ \033[92mSelected:\033[0m {selected.name}")
    print()
    return str(selected)


# ─────────────────────────────────────────────────────────────────────────────
#  Dual-input pair builders  (5 modes)
# ─────────────────────────────────────────────────────────────────────────────

def build_pairs_mode1():
    """1 source → many pose refs"""
    source = get_single_image_input("source subject")
    if not source:
        return None, None
    refs = get_image_list_input("pose references (targets)")
    if not refs:
        return None, None
    return [(source, ref) for ref in refs], f"1 source → {len(refs)} targets"


def build_pairs_mode2():
    """1 source → 1 pose ref"""
    source = get_single_image_input("source subject")
    if not source:
        return None, None
    ref = get_single_image_input("pose reference (target)")
    if not ref:
        return None, None
    return [(source, ref)], "1 source → 1 target"


def build_pairs_mode3():
    """Many sources → 1 pose ref"""
    sources = get_image_list_input("sources (subjects)")
    if not sources:
        return None, None
    ref = get_single_image_input("pose reference (target)")
    if not ref:
        return None, None
    return [(src, ref) for src in sources], f"{len(sources)} sources → 1 target"


def build_pairs_mode4():
    """Many sources → many pose refs (paired by sort order)"""
    print()
    print("\033[93m⚠️  Many-to-many mode: files are paired by sorted filename order.\033[0m")
    print("\033[93m   Make sure both sets have matching counts and are named accordingly.\033[0m")
    sources = get_image_list_input("sources (subjects)")
    if not sources:
        return None, None
    refs = get_image_list_input("pose references (targets)")
    if not refs:
        return None, None
    if len(sources) != len(refs):
        count = min(len(sources), len(refs))
        print(f"\n⚠️  \033[93mCount mismatch: {len(sources)} sources vs {len(refs)} refs. "
              f"Pairing the first {count} from each.\033[0m")
        sources = sources[:count]
        refs    = refs[:count]
    pairs = list(zip(sources, refs))
    return pairs, f"{len(pairs)} sources → {len(pairs)} targets (paired)"


def build_pairs_mode5():
    """Full matrix: every source × every pose ref (itertools.product)"""
    from itertools import product
    print()
    print("\033[93m⚠️  Full matrix mode: every source will be paired with every pose ref.\033[0m")
    print("\033[93m   e.g. 4 sources × 6 refs = 24 jobs.\033[0m")
    sources = get_image_list_input("sources (subjects)")
    if not sources:
        return None, None
    refs = get_image_list_input("pose references (targets)")
    if not refs:
        return None, None
    pairs = list(product(sources, refs))
    return pairs, f"{len(sources)} sources × {len(refs)} targets = {len(pairs)} jobs (full matrix)"


# ─────────────────────────────────────────────────────────────────────────────
#  Core processor
# ─────────────────────────────────────────────────────────────────────────────

class ComfyUIBatchProcessor:
    def __init__(self, workflow_path, comfyui_input_folder, job_id=None):
        self.workflow_path        = workflow_path
        self.comfyui_input_folder = Path(comfyui_input_folder)
        self.server_url           = COMFYUI_URL
        self.client_id            = "djjtb_batch_processor"
        self.created_symlinks     = []
        self.job_id               = job_id

    # ── Workflow ──────────────────────────────────────────────────────────

    def load_workflow(self):
        try:
            with open(self.workflow_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ \033[93mWorkflow not found:\033[0m {self.workflow_path}")
            return None
        except json.JSONDecodeError:
            print(f"❌ \033[93mInvalid JSON in workflow file\033[0m")
            return None

    def update_node_image(self, workflow, node_id, filename):
        node_id = str(node_id)
        if node_id in workflow:
            node = workflow[node_id]
            if 'inputs' in node and 'image' in node['inputs']:
                node['inputs']['image'] = filename
            elif 'widgets_values' in node:
                node['widgets_values'][0] = filename
        return workflow

    def update_ksampler_steps(self, workflow, steps):
        """Override the steps value in the KSampler node (widgets_values index 2)."""
        node_id = KSAMPLER_NODE_ID
        if node_id in workflow:
            node = workflow[node_id]
            # Try inputs dict first (API format)
            if 'inputs' in node and 'steps' in node['inputs']:
                node['inputs']['steps'] = steps
            # Fall back to widgets_values
            elif 'widgets_values' in node and len(node['widgets_values']) > KSAMPLER_STEPS_IDX:
                node['widgets_values'][KSAMPLER_STEPS_IDX] = steps
        return workflow

    # ── Symlinks ──────────────────────────────────────────────────────────

    def create_symlink(self, image_path):
        image_path = Path(image_path)
        dest_path  = self.comfyui_input_folder / image_path.name
        try:
            self.comfyui_input_folder.mkdir(parents=True, exist_ok=True)
            if not image_path.exists():
                return False, f"Source not found: {image_path}"
            if dest_path.exists() or dest_path.is_symlink():
                dest_path.unlink()
            dest_path.symlink_to(image_path)
            self.created_symlinks.append(dest_path)
            return True, None
        except Exception as e:
            return False, str(e)

    def cleanup_symlinks(self):
        if not self.created_symlinks:
            return
        print()
        print("🧹 \033[93mCleaning up symlinks...\033[0m")
        cleaned = 0
        for sp in self.created_symlinks:
            try:
                if sp.is_symlink():
                    sp.unlink()
                    cleaned += 1
            except Exception as e:
                print(f"   ⚠️  \033[93mCould not remove\033[0m {sp.name}: {e}")
        if cleaned > 0:
            print(f"✅ \033[92mRemoved {cleaned} symlinks\033[0m")

    # ── ComfyUI API ───────────────────────────────────────────────────────

    def submit_workflow(self, workflow):
        try:
            r = requests.post(
                f"{self.server_url}/prompt",
                json={"prompt": workflow, "client_id": self.client_id},
                timeout=10
            )
            if r.status_code == 200:
                return True, r.json().get('prompt_id')
            return False, f"HTTP {r.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to ComfyUI"
        except Exception as e:
            return False, str(e)

    def check_comfyui_running(self):
        try:
            return requests.get(f"{self.server_url}/system_stats", timeout=5).status_code == 200
        except Exception:
            return False

    def get_queue_status(self):
        try:
            r = requests.get(f"{self.server_url}/queue", timeout=5)
            if r.status_code == 200:
                d = r.json()
                return len(d.get('queue_running', [])), len(d.get('queue_pending', []))
        except Exception:
            pass
        return 0, 0

    # ── Single-input batch ────────────────────────────────────────────────

    def process_single_input(self, images, node_id, steps_override=None, cleanup_after=False):
        self._print_header()
        if not self.check_comfyui_running():
            print(f"❌ \033[93mCannot connect to ComfyUI at\033[0m {self.server_url}")
            return False
        print(f"✅ \033[92mConnected to ComfyUI\033[0m\n")

        base_workflow = self.load_workflow()
        if not base_workflow:
            return False
        print(f"✅ \033[92mLoaded workflow\033[0m\n")
        print(f"✅ \033[92mFound {len(images)} images\033[0m")
        if steps_override is not None:
            print(f"⚡ \033[92mSteps override:\033[0m {steps_override}")
        self._show_sample(images)

        successful, failed, symlinked = 0, 0, 0
        self._section("Processing Images")

        for idx, image_path in enumerate(images, 1):
            print(f"\n\033[93m[{idx}/{len(images)}]\033[0m {image_path.name}")

            ok, err = self.create_symlink(image_path)
            if not ok:
                print(f"    ❌ \033[93mSymlink failed:\033[0m {err}")
                failed += 1
                continue
            symlinked += 1
            print(f"    ✅ \033[92mSymlinked\033[0m")

            wf = copy.deepcopy(base_workflow)
            wf = self.update_node_image(wf, node_id, image_path.name)
            if steps_override is not None:
                wf = self.update_ksampler_steps(wf, steps_override)

            print(f"    📤 \033[93mSubmitting...\033[0m")
            ok, result = self.submit_workflow(wf)
            if ok:
                print(f"    ✅ \033[92mQueued\033[0m (ID: {result})")
                successful += 1
            else:
                print(f"    ❌ \033[93mQueue failed:\033[0m {result}")
                failed += 1

            if idx < len(images):
                time.sleep(QUEUE_DELAY)

        print()
        self._section("Summary")
        print(f"📁 \033[93mInput folder:\033[0m {images[0].parent if images else '-'}")
        print(f"⚙️  \033[93mWorkflow:\033[0m {Path(self.workflow_path).name}")
        if steps_override is not None:
            print(f"⚡ \033[93mSteps:\033[0m {steps_override} (overridden)")
        print(f"🔗 \033[93mSymlinks created:\033[0m {symlinked}")
        print(f"✅ \033[92mSuccessfully queued:\033[0m {successful}")
        if failed > 0:
            print(f"❌ \033[93mFailed:\033[0m {failed}")
        self._footer(cleanup_after)
        return True

    # ── Dual-input batch ──────────────────────────────────────────────────

    def process_dual_input(self, pairs, source_node_id, ref_node_id, mode_label,
                           steps_override=None, cleanup_after=False):
        self._print_header()
        if not self.check_comfyui_running():
            print(f"❌ \033[93mCannot connect to ComfyUI at\033[0m {self.server_url}")
            return False
        print(f"✅ \033[92mConnected to ComfyUI\033[0m\n")

        base_workflow = self.load_workflow()
        if not base_workflow:
            return False
        print(f"✅ \033[92mLoaded workflow\033[0m")
        print(f"✅ \033[92mMode: {mode_label}\033[0m")
        if steps_override is not None:
            print(f"⚡ \033[92mSteps override:\033[0m {steps_override}")
        print(f"✅ \033[92m{len(pairs)} job(s) to submit\033[0m\n")

        successful, failed = 0, 0
        self._section("Processing Pairs")

        for idx, (source_path, ref_path) in enumerate(pairs, 1):
            source_path = Path(source_path)
            ref_path    = Path(ref_path)
            print(f"\n\033[93m[{idx}/{len(pairs)}]\033[0m")
            print(f"    📸 \033[93mSource:\033[0m   {source_path.name}")
            print(f"    🕺 \033[93mPose ref:\033[0m {ref_path.name}")

            ok, err = self.create_symlink(source_path)
            if not ok:
                print(f"    ❌ \033[93mSource symlink failed:\033[0m {err}")
                failed += 1
                continue

            if ref_path.resolve() != source_path.resolve():
                ok, err = self.create_symlink(ref_path)
                if not ok:
                    print(f"    ❌ \033[93mRef symlink failed:\033[0m {err}")
                    failed += 1
                    continue

            print(f"    ✅ \033[92mSymlinks created\033[0m")

            wf = copy.deepcopy(base_workflow)
            wf = self.update_node_image(wf, source_node_id, source_path.name)
            wf = self.update_node_image(wf, ref_node_id,    ref_path.name)
            if steps_override is not None:
                wf = self.update_ksampler_steps(wf, steps_override)

            print(f"    📤 \033[93mSubmitting...\033[0m")
            ok, result = self.submit_workflow(wf)
            if ok:
                print(f"    ✅ \033[92mQueued\033[0m (ID: {result})")
                successful += 1
            else:
                print(f"    ❌ \033[93mQueue failed:\033[0m {result}")
                failed += 1

            if idx < len(pairs):
                time.sleep(QUEUE_DELAY)

        print()
        self._section("Summary")
        print(f"⚙️  \033[93mWorkflow:\033[0m {Path(self.workflow_path).name}")
        print(f"🔀 \033[93mMode:\033[0m {mode_label}")
        if steps_override is not None:
            print(f"⚡ \033[93mSteps:\033[0m {steps_override} (overridden)")
        print(f"✅ \033[92mSuccessfully queued:\033[0m {successful}")
        if failed > 0:
            print(f"❌ \033[93mFailed:\033[0m {failed}")
        self._footer(cleanup_after)
        return True

    # ── Print helpers ─────────────────────────────────────────────────────

    def _print_header(self):
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mComfyUI Batch Processor\033[0m")
        if self.job_id:
            print(f"\033[93mJob ID:\033[0m {self.job_id}")
        print("\033[92m==================================================\033[0m")
        print()
        print("🔍 \033[93mChecking ComfyUI connection...\033[0m")

    def _section(self, title):
        print("\033[93m" + "=" * 50 + "\033[0m")
        print(f"\033[1;33m{title}\033[0m")
        print("\033[93m" + "=" * 50 + "\033[0m")

    def _show_sample(self, images, n=5):
        print()
        print("\033[93mSample of images:\033[0m")
        for i, img in enumerate(images[:n], 1):
            print(f"  {i}. {img.name}")
        if len(images) > n:
            print(f"  ... and {len(images) - n} more")
        print()

    def _footer(self, cleanup_after):
        running, pending = self.get_queue_status()
        print(f"📊 \033[93mQueue status:\033[0m {running} running, {pending} pending")
        print()
        print("💡 \033[93mComfyUI will process these images one by one.\033[0m")
        print("   \033[93mMonitor progress in the ComfyUI interface.\033[0m")
        if cleanup_after:
            self.cleanup_symlinks()
        else:
            print()
            print("📌 \033[93mNote: Symlinks remain in ComfyUI input folder\033[0m")
            print(f"   \033[93mLocation:\033[0m {self.comfyui_input_folder}")
        print("\033[93m" + "=" * 50 + "\033[0m")
        print()


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    while True:
        os.system('clear')
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mComfyUI Batch Processor\033[0m")
        print("Process images through ComfyUI workflows")
        print("\033[92m==================================================\033[0m")
        print()

        # ── Step 1: workflow type ──────────────────────────────────────────
        workflow_type = djj.prompt_choice(
            "\033[93mWorkflow type:\033[0m\n"
            "1. Single input  (one Load Image node)\n"
            "2. Dual input    (two Load Image nodes — e.g. pose transfer)",
            ['1', '2'],
            default='1'
        )
        print()

        # ── Step 2: workflow file ──────────────────────────────────────────
        if workflow_type == '2':
            workflow_mode = djj.prompt_choice(
                "\033[93mWorkflow selection:\033[0m\n"
                "1. Load from Qwen_CN folder (default)\n"
                "2. Load from API folder\n"
                "3. Custom path",
                ['1', '2', '3'],
                default='1'
            )
            print()
            if workflow_mode == '1':
                workflow_path = select_workflow_from_folder(DEFAULT_WORKFLOW_FOLDER_QWEN)
            elif workflow_mode == '2':
                workflow_path = select_workflow_from_folder(DEFAULT_WORKFLOW_FOLDER)
            else:
                workflow_path = djj.get_path_input("📄 Enter workflow JSON path (API format)")
                print()
        else:
            workflow_mode = djj.prompt_choice(
                "\033[93mWorkflow selection:\033[0m\n"
                "1. Load from default folder\n"
                "2. Custom path",
                ['1', '2'],
                default='1'
            )
            print()
            if workflow_mode == '1':
                workflow_path = select_workflow_from_folder(DEFAULT_WORKFLOW_FOLDER)
            else:
                workflow_path = djj.get_path_input("📄 Enter workflow JSON path (API format)")
                print()

        if not workflow_path:
            print("❌ \033[93mNo workflow selected.\033[0m")
            action = djj.what_next()
            if action == 'exit':
                break
            continue

        # ── Step 3: steps override ─────────────────────────────────────────
        steps_override = prompt_steps_override()

        # ── Step 4: cleanup preference ─────────────────────────────────────
        cleanup_after = djj.prompt_choice(
            "\033[93mCleanup symlinks after processing?\033[0m\n1. Yes\n2. No (leave for review)",
            ['1', '2'],
            default='2'
        ) == '1'
        print()

        # ── Step 5: job ID ─────────────────────────────────────────────────
        job_id = get_next_job_id()
        print(f"🆔 \033[93mJob ID:\033[0m {job_id}")
        print()

        processor = ComfyUIBatchProcessor(
            workflow_path=workflow_path,
            comfyui_input_folder=COMFYUI_INPUT_FOLDER,
            job_id=job_id
        )

        # ══════════════════════════════════════════════════════════════════
        #  SINGLE-INPUT FLOW
        # ══════════════════════════════════════════════════════════════════
        if workflow_type == '1':
            source_folder = djj.get_path_input("📁 Enter source folder path")
            print()

            include_subfolders = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
                ['1', '2'],
                default='2'
            ) == '1'
            print()

            load_image_node = djj.get_string_input(
                "\033[93m🔢 Enter Load Image node ID (default: 232):\033[0m\n > ",
                default='232'
            )
            print()

            images = get_images_from_folder(source_folder, include_subfolders)
            if not images:
                print("❌ \033[93mNo images found. Skipping.\033[0m")
                action = djj.what_next()
                if action == 'exit':
                    break
                continue

            log_file = log_job(
                job_id=job_id,
                workflow_path=workflow_path,
                mode_label="Single input",
                pairs=images,
                steps_override=steps_override
            )
            print(f"📝 \033[93mLogged to:\033[0m {log_file}\n")
            print("\033[1;33m🚀 Starting batch process...\033[0m\n")

            processor.process_single_input(
                images=images,
                node_id=load_image_node,
                steps_override=steps_override,
                cleanup_after=cleanup_after
            )

        # ══════════════════════════════════════════════════════════════════
        #  DUAL-INPUT FLOW
        # ══════════════════════════════════════════════════════════════════
        else:
            print(f"\033[93m🔢 Source node ID\033[0m (default: {QWEN_SOURCE_NODE_ID} — Qwen OG subject):")
            source_node_raw = djj.get_string_input(" > ", default=QWEN_SOURCE_NODE_ID)
            source_node = source_node_raw if source_node_raw else QWEN_SOURCE_NODE_ID
            print()

            print(f"\033[93m🔢 Pose ref node ID\033[0m (default: {QWEN_POSE_NODE_ID} — Qwen POSE):")
            ref_node_raw = djj.get_string_input(" > ", default=QWEN_POSE_NODE_ID)
            ref_node = ref_node_raw if ref_node_raw else QWEN_POSE_NODE_ID
            print()

            print("\033[93mPairing mode:\033[0m")
            print("1. Single source   → multiple targets  (one subject, many pose refs)")
            print("2. Single source   → single target     (one subject, one pose ref)")
            print("3. Multiple sources → single target    (many subjects, one pose ref)")
            print("4. Multiple sources → multiple targets (paired by filename order)")
            print("5. Full matrix     → every source × every target (N×M jobs)")
            print()
            pair_mode = djj.prompt_choice(
                "\033[93mSelect pairing mode\033[0m",
                ['1', '2', '3', '4', '5'],
                default='1'
            )
            print()

            pairs, mode_label = {
                '1': build_pairs_mode1,
                '2': build_pairs_mode2,
                '3': build_pairs_mode3,
                '4': build_pairs_mode4,
                '5': build_pairs_mode5,
            }[pair_mode]()

            if not pairs:
                print("❌ \033[93mNo pairs built. Skipping.\033[0m")
                action = djj.what_next()
                if action == 'exit':
                    break
                continue

            # Preview pairs before confirming
            print()
            print(f"\033[93m📋 {mode_label} — preview (first 5):\033[0m")
            for i, (src, ref) in enumerate(pairs[:5], 1):
                print(f"  {i}. \033[92m{Path(src).name}\033[0m  →  \033[94m{Path(ref).name}\033[0m")
            if len(pairs) > 5:
                print(f"  ... and {len(pairs) - 5} more")
            print()
            print(f"\033[93m📊 Total jobs to queue:\033[0m {len(pairs)}")

            confirm = djj.prompt_choice(
                "\033[93mProceed with these pairs?\033[0m\n1. Yes\n2. No, go back",
                ['1', '2'],
                default='1'
            )
            print()
            if confirm == '2':
                continue

            log_file = log_job(
                job_id=job_id,
                workflow_path=workflow_path,
                mode_label=mode_label,
                pairs=pairs,
                steps_override=steps_override
            )
            print(f"📝 \033[93mLogged to:\033[0m {log_file}\n")
            print("\033[1;33m🚀 Starting batch process...\033[0m\n")

            processor.process_dual_input(
                pairs=pairs,
                source_node_id=source_node,
                ref_node_id=ref_node,
                mode_label=mode_label,
                steps_override=steps_override,
                cleanup_after=cleanup_after
            )

        # ── What next? ─────────────────────────────────────────────────────
        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()
