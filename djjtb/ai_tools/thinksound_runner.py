#!/usr/bin/env python3
"""
ThinkSound Runner — DJJTB
Video-to-Audio generation using ThinkSound (FunAudioLLM / NeurIPS 2025)
Generates temporally-synced audio/foley from video using Chain-of-Thought reasoning.
Merges generated audio back onto source video via ffmpeg.

Installation:
    See bottom of this file for full setup instructions.

Model:
    ~/Documents/ai_models/thinksound/ckpts/   (cloned from HuggingFace)

Venv:
    ~/Documents/ai_models/thinksound/tsvenv/  (conda not used — pip venv instead)
"""

import os
import sys
import subprocess
import pathlib
from pathlib import Path
import djjtb.utils as djj

os.system('clear')

# ─── Config ───────────────────────────────────────────────────────────────────

THINKSOUND_DIR  = Path("/Users/home/Documents/ai_models/thinksound")
CKPTS_DIR       = THINKSOUND_DIR / "ckpts"
VENV_PYTHON     = THINKSOUND_DIR / "tsvenv/bin/python3"

VALID_VIDEO_EXTS = (".mp4", ".mov", ".webm", ".mkv", ".avi")

# ─── Helpers ──────────────────────────────────────────────────────────────────

def verify_installation():
    """Check ThinkSound install is present before doing anything."""
    missing = []
    if not VENV_PYTHON.exists():
        missing.append(str(VENV_PYTHON))
    if not CKPTS_DIR.exists():
        missing.append(str(CKPTS_DIR))
    if missing:
        print("\033[93m⚠️  Missing ThinkSound components:\033[0m")
        for m in missing:
            print(f"   {m}")
        print()
        print("Run the setup instructions at the bottom of this file.")
        return False
    print("\033[92m✅ ThinkSound installation found\033[0m")
    return True


def collect_videos(folder):
    """Return sorted list of video files from a flat folder."""
    return sorted([
        str(f) for f in Path(folder).iterdir()
        if f.is_file() and f.suffix.lower() in VALID_VIDEO_EXTS
    ])


def collect_videos_from_subfolders(parent):
    """Return sorted list of video files across immediate subfolders."""
    videos = []
    for sub in sorted(Path(parent).iterdir()):
        if sub.is_dir():
            videos.extend(sorted([
                str(f) for f in sub.iterdir()
                if f.is_file() and f.suffix.lower() in VALID_VIDEO_EXTS
            ]))
    return videos


def run_thinksound(video_path, output_audio_path, prompt, steps, cfg_scale, seed):
    """
    Call ThinkSound inference via its installed Python package.
    ThinkSound exposes: thinksound.inference.generate(video_path, prompt, ...)
    Falls back to subprocess call against infer.py if API import fails.
    """
    video_path = str(video_path)
    output_audio_path = str(output_audio_path)

    # Build the inline Python command — runs inside tsvenv
    # ThinkSound pip package exposes thinksound.inference.generate()
    inline = (
        f"import sys; sys.path.insert(0, '{THINKSOUND_DIR}'); "
        f"from thinksound.inference import generate; "
        f"generate("
        f"  video_path='{video_path}', "
        f"  output_path='{output_audio_path}', "
        f"  prompt='''{prompt}''', "
        f"  num_steps={steps}, "
        f"  cfg_scale={cfg_scale}, "
        f"  seed={seed}, "
        f"  ckpt_dir='{CKPTS_DIR}', "
        f"  device='cpu'"   # MPS fallback — change to 'mps' if ThinkSound adds support
        f")"
    )

    cmd = [str(VENV_PYTHON), "-c", inline]

    result = subprocess.run(
        cmd,
        cwd=str(THINKSOUND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=1800  # 30 min max per video
    )

    if result.returncode != 0:
        # Surface last 400 chars of stderr for diagnosis
        err = result.stderr.strip()[-400:] if result.stderr else "no error output"
        return False, err

    return True, None


def merge_audio_to_video(video_path, audio_path, output_path):
    """
    Use ffmpeg to merge generated audio onto the original video.
    Strips any existing audio track and replaces with ThinkSound output.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v",       # video from original
        "-map", "1:a",       # audio from ThinkSound
        "-c:v", "copy",      # no re-encode on video
        "-c:a", "aac",
        "-shortest",
        str(output_path)
    ]
    result = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True
    )
    return result.returncode == 0


def process_video(video_path, output_dir, prompt, steps, cfg_scale, seed,
                  save_audio, merge_video):
    """Process a single video — generate audio, optionally merge, optionally save audio."""
    video_path = Path(video_path)
    stem = video_path.stem
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_path = output_dir / f"{stem}_thinksound.wav"
    merged_path = output_dir / f"{stem}_withsound.mp4"

    print(f"  🎬 Video : {video_path.name}")
    print(f"  💬 Prompt: {prompt if prompt else '(visual-only, no text prompt)'}")
    print(f"  ⚙️  Steps : {steps} | CFG: {cfg_scale} | Seed: {seed}")
    print()

    # Generate audio
    print(f"  🔊 Generating audio...")
    success, err = run_thinksound(video_path, audio_path, prompt, steps, cfg_scale, seed)

    if not success:
        print(f"  \033[93m❌ Generation failed:\033[0m\n     {err}")
        return False

    if not audio_path.exists() or audio_path.stat().st_size == 0:
        print(f"  \033[93m❌ Output audio missing or empty.\033[0m")
        return False

    print(f"  \033[92m✅ Audio generated:\033[0m {audio_path.name}")

    # Merge back onto video
    if merge_video:
        print(f"  🔗 Merging audio onto video...")
        ok = merge_audio_to_video(video_path, audio_path, merged_path)
        if ok:
            print(f"  \033[92m✅ Merged video:\033[0m {merged_path.name}")
        else:
            print(f"  \033[93m⚠️  Merge failed — audio WAV still saved.\033[0m")

    # Clean up audio WAV if not keeping it
    if not save_audio and audio_path.exists():
        audio_path.unlink()
        print(f"  🗑️  Audio WAV removed (merge-only mode)")

    return True


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print()
    print("\033[92m==================================================\033[0m")
    print("\033[1;93mThinkSound Runner\033[0m")
    print("AI Video-to-Audio / Foley Generation")
    print("\033[92m==================================================\033[0m")
    print()

    if not verify_installation():
        sys.exit(1)

    while True:

        # ── Input path ────────────────────────────────────────────────────────
        parent = djj.get_path_input("📁 Enter folder path")
        print()

        # ── Folder mode ───────────────────────────────────────────────────────
        mode = djj.prompt_choice(
            "📂 Folder structure?\n1. Flat (videos directly in folder)\n2. Subfolders (one video per subfolder)",
            ['1', '2'],
            default='1'
        )
        print()

        if mode == '1':
            videos = collect_videos(parent)
        else:
            videos = collect_videos_from_subfolders(parent)

        if not videos:
            print("\033[93m⚠️  No video files found. Try again.\033[0m\n")
            action = djj.what_next()
            if action == 'exit':
                break
            continue

        print(f"\033[92m✅ {len(videos)} video(s) found\033[0m")
        for v in videos[:5]:
            print(f"   {Path(v).name}")
        if len(videos) > 5:
            print(f"   ... and {len(videos) - 5} more")
        print()

        # ── Output location ───────────────────────────────────────────────────
        out_mode = djj.prompt_choice(
            "📤 Output location?\n1. Output/ subfolder inside input folder\n2. Same folder as each video\n3. Custom path",
            ['1', '2', '3'],
            default='1'
        )
        print()

        if out_mode == '1':
            output_root = Path(parent) / "Output" / "ThinkSound"
        elif out_mode == '2':
            output_root = None  # per-video, determined at runtime
        else:
            output_root = Path(djj.get_path_input("📁 Enter custom output folder"))
        print()

        # ── Text prompt ───────────────────────────────────────────────────────
        print("\033[93m💬 Text prompt (optional — leave blank for visual-only mode):\033[0m")
        print("   Examples: 'footsteps on pavement, park ambience, birds'")
        print("             'ocean waves, seagulls, wind'")
        prompt = input(" > ").strip()
        print()

        # ── Generation settings ───────────────────────────────────────────────
        steps_str = djj.prompt_choice(
            "⚙️  Inference steps:\n1. Fast (24 steps)\n2. Balanced (36 steps)\n3. Quality (50 steps)",
            ['1', '2', '3'],
            default='1'
        )
        steps = {'1': 24, '2': 36, '3': 50}[steps_str]
        print()

        cfg_input = input("\033[93m⚙️  CFG scale (default 5.0, higher = more prompt-guided):\n\033[0m > ").strip()
        try:
            cfg_scale = float(cfg_input) if cfg_input else 5.0
        except ValueError:
            cfg_scale = 5.0
        print()

        seed_input = input("\033[93m🌱 Seed (default 0 = random):\n\033[0m > ").strip()
        try:
            seed = int(seed_input) if seed_input else 0
        except ValueError:
            seed = 0
        print()

        # ── Output options ────────────────────────────────────────────────────
        merge_video = djj.prompt_choice(
            "🔗 Merge audio back onto video?\n1. Yes (save merged .mp4)\n2. No (audio WAV only)",
            ['1', '2'],
            default='1'
        ) == '1'
        print()

        save_audio = djj.prompt_choice(
            "💾 Also keep the raw audio WAV?\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        print()

        # ── Confirm and process ───────────────────────────────────────────────
        print(f"\033[93m📋 Summary:\033[0m")
        print(f"   Videos   : {len(videos)}")
        print(f"   Prompt   : {prompt if prompt else '(visual only)'}")
        print(f"   Steps    : {steps} | CFG: {cfg_scale} | Seed: {seed}")
        print(f"   Merge    : {'Yes' if merge_video else 'No'}")
        print(f"   Keep WAV : {'Yes' if save_audio else 'No'}")
        print()

        confirm = djj.prompt_choice(
            "Proceed?\n1. Yes\n2. No",
            ['1', '2'],
            default='1'
        )
        if confirm != '1':
            print("Cancelled.\n")
            action = djj.what_next()
            if action == 'exit':
                break
            continue

        print()
        print("\033[1;93mProcessing...\033[0m")
        print()

        success_count = 0
        fail_count = 0
        total = len(videos)

        for idx, video_path in enumerate(videos, 1):
            pct = int((idx / total) * 100)
            print(f"\033[93m🔊 [{idx}/{total}] ({pct}%)\033[0m {Path(video_path).name}")

            # Determine output dir per video
            if out_mode == '2':
                out_dir = Path(video_path).parent / "ThinkSound"
            else:
                out_dir = output_root

            ok = process_video(
                video_path=video_path,
                output_dir=out_dir,
                prompt=prompt,
                steps=steps,
                cfg_scale=cfg_scale,
                seed=seed,
                save_audio=save_audio,
                merge_video=merge_video
            )

            if ok:
                success_count += 1
            else:
                fail_count += 1
            print()

        # ── Summary ───────────────────────────────────────────────────────────
        print()
        print("\033[93mSummary\033[0m")
        print("-------")
        print(f"\033[92m✅ Succeeded:\033[0m {success_count}")
        print(f"\033[93m❌ Failed   :\033[0m {fail_count}")
        print()

        final_out = output_root if output_root else Path(videos[0]).parent / "ThinkSound"
        djj.prompt_open_folder(str(final_out))

        print()
        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()


# ══════════════════════════════════════════════════════════════════════════════
# SETUP INSTRUCTIONS — Run these once before first use
# ══════════════════════════════════════════════════════════════════════════════
#
# ThinkSound uses conda for its official install, but we use a pip venv here
# to keep it consistent with the rest of DJJTB. Python 3.10 required.
#
# ── Step 1: Create venv (Python 3.10) ─────────────────────────────────────────
#
#   /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m venv \
#       /Users/home/Documents/ai_models/thinksound/tsvenv
#
#   If you don't have Python 3.10:
#       brew install python@3.10
#   Then:
#   /opt/homebrew/bin/python3.10 -m venv \
#       /Users/home/Documents/ai_models/thinksound/tsvenv
#
# ── Step 2: Activate and install ThinkSound ────────────────────────────────────
#
#   source /Users/home/Documents/ai_models/thinksound/tsvenv/bin/activate
#   pip install --upgrade pip
#   pip install thinksound
#
# ── Step 3: Install ffmpeg (if not already) ────────────────────────────────────
#
#   conda install -y -c conda-forge 'ffmpeg<7'
#   — OR —
#   brew install ffmpeg
#
#   ThinkSound requires ffmpeg < 7. Check: ffmpeg -version
#   If you have ffmpeg 7+, use conda to get the constrained version in the env.
#
# ── Step 4: Download model weights ────────────────────────────────────────────
#
#   cd /Users/home/Documents/ai_models/thinksound
#   git lfs install
#   git clone https://huggingface.co/liuhuadai/ThinkSound ckpts
#
#   The ckpts/ folder will be ~several GB. git lfs required for large files.
#   If git lfs isn't installed: brew install git-lfs
#
# ── Step 5: Verify install ────────────────────────────────────────────────────
#
#   source /Users/home/Documents/ai_models/thinksound/tsvenv/bin/activate
#   python -c "import thinksound; print('ThinkSound OK')"
#
# ── Step 6: Add to DJJTB launcher ─────────────────────────────────────────────
#
#   In djjtb.py → handle_ai_tools(), add:
#       elif choice == "13":  # ThinkSound
#           djj.run_command_in_tab(
#               f"source /Users/home/Documents/ai_models/thinksound/tsvenv/bin/activate; "
#               f"cd {self.project_path}/; python3 -m djjtb.ai_tools.thinksound_runner"
#           )
#
#   And add to show_ai_tools_menu():
#       print(" 💰\033[4;93m13\033[0m  ThinkSound (V2A Foley) 🔊🎬")
#
# ── Notes ─────────────────────────────────────────────────────────────────────
#
#   - ThinkSound runs on CPU on Mac (MPS not yet supported by the model).
#     Expect slow generation — minutes per clip, not seconds.
#     Your 64GB RAM means no OOM issues, just patience required.
#
#   - If thinksound.inference.generate() API differs from what's in the package
#     after you install, open an issue here or check:
#     https://github.com/FunAudioLLM/ThinkSound
#     The inline Python call in run_thinksound() is easy to adjust.
#
#   - For faster results, PrismAudio (same repo, branch prismaudio) is the
#     newer successor — swap the git clone branch and env if you want to try it.
#     Install: git clone -b prismaudio https://github.com/liuhuadai/ThinkSound.git
#
# ══════════════════════════════════════════════════════════════════════════════
