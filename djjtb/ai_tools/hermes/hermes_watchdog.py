#!/usr/bin/env python3
"""
Hermes Watchdog — unattended stall/crash detection and auto-relaunch for a
single Hermes Agent inventory -> dedupe -> categorize sort job.

Meant to be started manually in its own terminal tab for an unattended run
(overnight, etc). No LaunchAgent / auto-start at login — that's a separate,
later decision. Never trusts the agent's own "done" claims or self-reported
counts; every check recomputes real progress from the log files on disk via
hermes_core.
"""

import os
import sys
import time
import logging
import threading
from pathlib import Path
from datetime import datetime

import requests

import djjtb.utils as djj
from . import hermes_core as hc

os.system('clear')

LOG_DIR = Path("~/Documents/Scripts/DJJTB/djjtb/logs").expanduser()
LOG_DIR.mkdir(parents=True, exist_ok=True)

STALL_TIMEOUT_SECONDS = 5 * 60
MAX_RELAUNCH_ATTEMPTS = 5
POLL_INTERVAL_SECONDS = 30
GATEWAY_READY_TIMEOUT_SECONDS = 60

# Confirmed live tonight against ~/.hermes/logs/errors.log and
# ~/.ollama/logs/server.log — covers both crash types (ffprobe/image-load,
# context overflow) plus the generic abort message Hermes itself logs.
CRASH_SIGNATURES = [
    "Failed to load image or audio file",
    "ffprobe",
    "signal: killed",
    "Context overflow",
    "exceed_context_size_error",
    "Context length exceeded",
    "Non-retryable client error",
]
CRASH_LOG_PATHS = [
    Path("~/.hermes/logs/errors.log").expanduser(),
    Path("~/.ollama/logs/server.log").expanduser(),
]


def get_logger():
    log_file = LOG_DIR / "hermes_watchdog_log.txt"
    logger = logging.getLogger('djjtb.hermes_watchdog')
    logger.setLevel(logging.INFO)
    logger.handlers = []
    logger.propagate = False
    handler = logging.FileHandler(log_file, mode='a')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)
    logger.info("===== RUN START: hermes_watchdog =====")
    return logger


# ── Job types ──────────────────────────────────────────────────────────────
# Source of truth for job-type-specific Phase 2 duplicate rules, analogous
# to add_pose_prompts.py's CATEGORY_MENU/CATEGORY_PREFIX pattern.

JOB_TYPES = {
    'outfit': {
        'label': 'Outfit / garment',
        'duplicate_rule': (
            "IMPORTANT: color variants are NOT duplicates. If two images show the "
            "same garment cut/style/silhouette in different colors, they are distinct, "
            "intentional catalog variants to KEEP — never group them as duplicates "
            "just because the cut matches. Only true near-duplicates (the same shot, "
            "or a trivial crop/re-export of the exact same shot) count."
        ),
    },
    'pose': {
        'label': 'Pose reference',
        'duplicate_rule': (
            "IMPORTANT: if the same pose appears in multiple versions (clothed vs. "
            "unclothed, or face visible vs. face masked/blurred), these ARE duplicates "
            "of each other — keep only ONE version per pose. Priority: a face-masked/"
            "blurred version beats any other version of that pose; if no masked version "
            "exists, a clothed version beats an unclothed one; only keep an unclothed, "
            "unmasked version if it's the only version of that pose available. Flag "
            "every other version of that pose as a duplicate."
        ),
    },
    'generic': {
        'label': 'Generic / unspecified',
        'duplicate_rule': (
            "Be conservative: only flag as a duplicate if it's the same exact shot, or "
            "a trivial crop/re-export of the exact same shot. When uncertain, keep both."
        ),
    },
}


# ── Resume-prompt templates ───────────────────────────────────────────────
# Adapted from the proven wording in DJJIF's HERMES_SETUP.md ("Reusable
# resume-prompt template") and the OUTFITS/FACEtemp 3-phase template — not
# invented from scratch. Each carries forward every rule confirmed necessary
# this session: terminal-only log writes, one vision_analyze at a time, the
# "Now analyzing" announcement, single-line-only log entries (no heredocs —
# a confirmed real corruption mechanism). Phase 2's duplicate rule comes from
# JOB_TYPES and additionally requires structured single-line entries (an
# improvement over the free-prose duplicate-log format that broke reliable
# parsing tonight).

def resume_prompt_phase1(container_path, categories, job_type):
    cat_line = (f"Categories to use: {categories}." if categories else
                "Use your best-guess category for each; add new categories as needed.")
    return f"""You're resuming an interrupted Phase 1 (inventory) job inside {container_path}.

STEP 0 — verify real state: before doing anything else, read {container_path}/inventory-log.txt via terminal (cat) to see exactly which files are already logged. A file still sitting in the folder does NOT mean it hasn't been processed — only a missing log entry means it needs work. Only treat a file as needing inventory if it has no line for it in inventory-log.txt.

CRITICAL RULES (violating these has caused real crashes/corruption before):
- NEVER create, write to, or move any file into any folder outside {container_path}, including sibling folders that may already exist nearby. NEVER delete any file, under any circumstances.
- Use ONLY terminal commands (echo/printf/cat with >>) to write to any log file. Never use write_file — it cannot see paths under /workspace at all.
- Analyze exactly one image, immediately write its log line via terminal, only then move to the next. Do not batch several images before logging any of them. Only what's written to the log survives a crash/restart — anything analyzed but unlogged is lost and must be redone at real cost.
- Before every single vision_analyze call, first say plainly: "Now analyzing: <exact filename>" as visible text, not just internal reasoning.
- Every log entry must be written as a SINGLE line with no embedded line breaks, even if the description feels long. One image = one line, always. Do not use heredocs (cat <<EOF ... EOF) for logging — use a single echo/printf per line instead, since heredoc terminators have previously leaked into logged content.
- If an image fails to load or analyze, skip it, log the filename and error to {container_path}/failed-log.txt via terminal, and continue immediately with the next image.
- If genuinely uncertain about a description or category, decide and move on — note the call in the log. Don't stall deliberating.

Recursively find every remaining image file under {container_path} (including nested subfolders) that isn't already logged in inventory-log.txt. For each, briefly look at it and note: (a) its current full path, (b) a short single-line visual description, (c) your best-guess category. {cat_line} Append this to {container_path}/inventory-log.txt as you go, one line per image, in the same `filename | description | category` format already in that log.

Once every image is logged, move on to Phase 2 (near-duplicate detection) automatically — don't stop and wait to be told."""


def resume_prompt_phase2(container_path, categories, job_type):
    duplicate_rule = JOB_TYPES[job_type]['duplicate_rule']
    return f"""You're resuming an interrupted Phase 2 (near-duplicate detection) job inside {container_path}. Phase 1 (inventory) is already complete — do not re-scan or re-analyze images for Phase 1.

STEP 0 — verify real state: before doing anything else, read {container_path}/inventory-log.txt via terminal (cat) for the full set of images and their descriptions, and read {container_path}/duplicate-log.txt to see which files already have a Phase 2 decision logged. A file still sitting in the root folder does NOT mean an earlier phase skipped it — it may simply not have reached a later phase yet. Only treat a file as needing a Phase 2 decision if it has no entry in duplicate-log.txt.

CRITICAL RULES:
- NEVER create, write to, or move any file into any folder outside {container_path}, including sibling folders that may already exist nearby. NEVER delete any file, under any circumstances.
- Use ONLY terminal commands to write to any log file, and to move files (mv). Never use write_file.
- Every log entry must be a SINGLE line, no embedded line breaks, no heredocs — use one echo/printf per line.
- {duplicate_rule}
- For every duplicate set, actually MOVE (via mv, not just log) every FLAGGED file into {container_path}/duplicate/ now — do not defer that move to Phase 3. Do not move the KEPT file itself; its category move still happens in Phase 3. Log the whole set as one grouped line to {container_path}/duplicate-log.txt in this exact format: `KEPT: <file> -> <category>/ | FLAGGED: <file2>[, <file3>] -> duplicate/ | reason` — using the KEPT file's Phase 1 category. Never log a set with zero or multiple KEPT files. For an image with no near-duplicates found, still log it so it's marked reviewed: `KEPT: <file> -> <category>/ | no duplicates found`.
- If genuinely uncertain whether something is a true duplicate, decide and move on — note the call in the log. Don't stall deliberating.

Using the Phase 1 descriptions, group the remaining images that appear to be true near-duplicates. For each genuine near-duplicate group: keep one representative, move the rest into {container_path}/duplicate/ per the rule above.

Once every image has a logged decision, move on to Phase 3 (categorize and move) automatically — don't stop and wait to be told."""


def resume_prompt_phase3(container_path, categories, job_type):
    cat_line = (f"Category folders: {categories}." if categories else
                "Use the categories already established in inventory-log.txt.")
    return f"""You're resuming an interrupted Phase 3 (categorize and move) job inside {container_path}. Phase 1 (inventory) and Phase 2 (duplicate detection) are already complete — do not redo them.

STEP 0 — verify real state: before doing anything else, read {container_path}/sort-log.txt via terminal (cat) to see which files are already moved, and read {container_path}/duplicate-log.txt for which files were FLAGGED (Phase 2 already moved those into {container_path}/duplicate/ — do not move them again). A file still sitting in the root folder does NOT mean an earlier phase skipped it — only treat a file as needing a Phase 3 move if it has no entry in sort-log.txt.

CRITICAL RULES:
- NEVER create, write to, or move any file into any folder outside {container_path}, including sibling folders that may already exist nearby. NEVER delete any file, under any circumstances.
- Use ONLY terminal commands to write to any log file, and to move files (mv). Never use write_file.
- Batch simple mv commands together in one terminal call where practical (e.g. several plain `mv src dst` commands in a row) — but never write or execute a single all-at-once script (a bash loop, a generated Python script, etc.) to handle the moves. Keep each move a plain, directly-issued mv command via terminal only.
- Every log entry must be a SINGLE line, no embedded line breaks, no heredocs.
- Before creating a category folder, always use `mkdir -p`, never `touch` — a prior run once created empty *files* instead of directories by mistake, which silently clobbers files on the first move into that "folder."
- If genuinely uncertain which category a file fits, decide and move on — note the call in the log. Don't stall deliberating.

For every remaining image not yet in sort-log.txt (and not already FLAGGED and moved in Phase 2): move it into the matching category folder directly under {container_path}, regardless of which messy subfolder it's currently in — flatten everything to one level. {cat_line} If something genuinely doesn't fit cleanly, put it in {container_path}/Uncategorized rather than forcing a bad fit. Append every move to {container_path}/sort-log.txt as `filename | moved to <destination>/`. If a FLAGGED file from Phase 2 is missing a sort-log.txt entry, just log its already-completed move (`filename | moved to duplicate/`) rather than moving it again.

When every remaining image has been moved and logged, give a final summary: total processed, duplicates flagged, count per category."""


RESUME_PROMPTS = {
    'phase1': resume_prompt_phase1,
    'phase2': resume_prompt_phase2,
    'phase3': resume_prompt_phase3,
}


# ── Log tailing ────────────────────────────────────────────────────────────

def read_new_lines(path, since_offset):
    """Return (new_text, new_offset). Handles truncation/rotation by resetting to 0."""
    if not path.exists():
        return "", since_offset
    size = path.stat().st_size
    if size < since_offset:
        since_offset = 0
    with open(path, 'r', errors='replace') as f:
        f.seek(since_offset)
        data = f.read()
    return data, path.stat().st_size


def scan_for_crash_signatures(offsets, logger):
    """Tail CRASH_LOG_PATHS since last check; return list of matched signatures."""
    hits = []
    for path in CRASH_LOG_PATHS:
        new_text, offsets[path] = read_new_lines(path, offsets.get(path, 0))
        for sig in CRASH_SIGNATURES:
            if sig in new_text:
                hits.append(f"{sig!r} in {path.name}")
    return hits


# ── Relaunch ───────────────────────────────────────────────────────────────

def _post_resume_prompt(port, prompt, phase, logger):
    """Runs in a background thread — a chat/completions call to an agentic
    Hermes session can run for the entire rest of the job (up to 500 tool-use
    iterations per config), so the watchdog must not block its own poll loop
    waiting for the HTTP response to finish."""
    try:
        resp = requests.post(
            f"http://localhost:{port}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {hc.read_api_key()}",
                "Content-Type": "application/json",
            },
            json={"model": "hermes-agent", "messages": [{"role": "user", "content": prompt}]},
            timeout=(10, 300),
            stream=True,
        )
        logger.info(f"Resume POST ({phase}) — HTTP {resp.status_code}")
    except requests.RequestException as e:
        logger.error(f"Resume POST ({phase}) failed: {e}")


def relaunch(reason, target_folder, container_path, categories, job_type, attempt_number, logger):
    logger.info(f"RELAUNCH triggered — reason: {reason}")

    ok, msg = hc.stop_gateway()
    logger.info(f"stop_gateway: {msg}")
    removed = hc.remove_sandbox_containers()
    logger.info(f"remove_sandbox_containers: removed {removed} container(s)")
    hc.launch_gateway_window()
    logger.info("launch_gateway_window: issued")

    port = hc.read_api_port()
    deadline = time.time() + GATEWAY_READY_TIMEOUT_SECONDS
    ready = False
    while time.time() < deadline:
        if hc.port_listening(port):
            ready = True
            break
        time.sleep(2)
    if not ready:
        logger.error(f"Gateway did not come back up within {GATEWAY_READY_TIMEOUT_SECONDS}s — resume prompt not sent.")
        return False

    detail = hc.detect_pipeline_phase(target_folder)
    phase = detail['phase']
    logger.info(f"Resuming as {phase} — counts: {detail}")
    # Hermes derives its session ID as sha256(system_prompt + first_user_message)
    # (gateway/platforms/api_server.py:_derive_chat_session_id) — deterministic,
    # not random per call. Two relaunches with byte-identical prompt text would
    # hash to the same session ID. Harmless here (each POST carries only a
    # single fresh user message, and sandbox containers are already wiped
    # above), but a unique marker keeps every relaunch individually
    # identifiable in Hermes's own session list too.
    marker = f"[DJJTB Watchdog relaunch #{attempt_number} — {datetime.now().isoformat(timespec='seconds')}]\n\n"
    prompt = marker + RESUME_PROMPTS[phase](container_path, categories, job_type)
    threading.Thread(target=_post_resume_prompt, args=(port, prompt, phase, logger), daemon=True).start()
    return True


# ── Interactive startup ─────────────────────────────────────────────────────

def check_no_dual_frontend():
    """Blocking guard: Hermes Desktop (`hermes serve`) is a separate process
    from `hermes gateway` and can silently recreate its own sandbox container
    against the same folder — confirmed tonight (docker ps showed 2
    containers after every relaunch, every file double-logged in
    inventory-log.txt). Returns True once it's safe to proceed, False if the
    user aborts instead of quitting Desktop."""
    if not hc.hermes_desktop_pids():
        return True

    print("\033[91m⚠️  Hermes Desktop appears to be running ('hermes serve' detected).\033[0m")
    print("\033[91m   Running the watchdog alongside Desktop on the same folder causes\033[0m")
    print("\033[91m   duplicate processing — confirmed: every file logged twice, real\033[0m")
    print("\033[91m   wasted GPU load.\033[0m")
    print("\033[93m   Quit Hermes Desktop now — this will continue automatically once it's gone.\033[0m")
    print("\033[93m   (Ctrl+C to abort instead.)\033[0m\n")
    try:
        while hc.hermes_desktop_pids():
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n\033[93mAborted.\033[0m")
        return False
    print("\033[92m✅ Hermes Desktop no longer running — continuing.\033[0m\n")
    return True


def main():
    print("\033[1;93m🪽 Hermes Watchdog 🐕\033[0m")
    print("\033[92m" + "-" * 60 + "\033[0m")

    if not check_no_dual_frontend():
        return

    target_folder = djj.get_path_input("📁 Target folder to watch (host path)")
    categories = input("\033[93m Categories (comma-separated, blank to let the agent decide):\n >\033[0m ").strip()

    job_type_keys = list(JOB_TYPES.keys())
    job_type_menu = "\n".join(
        f"{i}. {JOB_TYPES[key]['label']}" + (" (default)" if key == 'generic' else "")
        for i, key in enumerate(job_type_keys, 1)
    )
    job_type_choice = djj.prompt_choice(
        f"\033[93mJob type\033[0m\n{job_type_menu}\n",
        [str(i) for i in range(1, len(job_type_keys) + 1)],
        default=str(job_type_keys.index('generic') + 1)
    )
    job_type = job_type_keys[int(job_type_choice) - 1]

    max_relaunch_attempts = djj.get_int_input(
        "🔁 Max relaunch attempts (blank for default 5, max 50 — you control usage)",
        min_val=1, max_val=50, default=MAX_RELAUNCH_ATTEMPTS
    )

    try:
        container_path = hc.host_path_to_container_path(target_folder)
    except ValueError as e:
        print(f"\033[91m❌ {e}\033[0m")
        djj.wait_with_skip(5, "Closing")
        return

    logger = get_logger()
    logger.info(f"target_folder={target_folder} container_path={container_path} categories={categories!r} job_type={job_type!r}")
    logger.info(f"stall_timeout={STALL_TIMEOUT_SECONDS}s max_attempts={max_relaunch_attempts} poll={POLL_INTERVAL_SECONDS}s")

    print(f"\033[92mWatching:\033[0m {target_folder}")
    print(f"\033[92mContainer path:\033[0m {container_path}")
    print(f"\033[92mStall timeout:\033[0m {STALL_TIMEOUT_SECONDS // 60} min   \033[92mMax relaunches:\033[0m {max_relaunch_attempts}")
    print("\033[93mCtrl+C to stop.\033[0m\n")

    offsets = {path: path.stat().st_size if path.exists() else 0 for path in CRASH_LOG_PATHS}
    relaunch_count = 0
    gave_up = False
    # Progress is tracked by count deltas (inventory/duplicate/sort), not log
    # file mtime — mtime with a stale watchdog-start/last-relaunch fallback
    # made a legitimate phase transition look like a stall (confirmed: a
    # relaunch fired the instant inventory hit 136/136, before Phase 2 could
    # possibly have produced anything yet, because duplicate-log.txt didn't
    # exist and the fallback baseline was already minutes old). The clock
    # resets on any count increase, any phase change, or a fired relaunch
    # (the latter gives a freshly-resumed session its own fair window
    # instead of immediately re-tripping on the stall that just fired it).
    prev_detail = hc.detect_pipeline_phase(target_folder)
    last_progress_time = time.time()

    try:
        while True:
            time.sleep(POLL_INTERVAL_SECONDS)

            is_complete, detail = hc.verify_job_complete(target_folder)
            logger.info(f"check — phase={detail['phase']} real={detail['real_file_count']} "
                        f"inventory={detail['inventory_count']} duplicate={detail['duplicate_count']} "
                        f"sort={detail['sort_count']}")

            if is_complete:
                logger.info("Job VERIFIED complete — real sort count matches real file count.")
                djj.send_macos_notification("Hermes Watchdog", f"Job complete: {target_folder}", subtitle="Verified from real file counts")
                print("\033[92m✅ Job verified complete.\033[0m")
                break

            progressed = (
                detail['phase'] != prev_detail['phase']
                or detail['inventory_count'] > prev_detail['inventory_count']
                or detail['duplicate_count'] > prev_detail['duplicate_count']
                or detail['sort_count'] > prev_detail['sort_count']
            )
            if progressed:
                last_progress_time = time.time()
            prev_detail = detail

            if gave_up:
                continue

            reasons = []

            crash_hits = scan_for_crash_signatures(offsets, logger)
            if crash_hits:
                reasons.append(f"crash signature(s): {', '.join(crash_hits)}")

            if not hc.gateway_pids():
                reasons.append("gateway process not running")

            stalled_for = time.time() - last_progress_time
            if stalled_for > STALL_TIMEOUT_SECONDS:
                reasons.append(f"no count progress in {detail['phase']} for {int(stalled_for)}s")

            if not reasons:
                continue

            if relaunch_count >= max_relaunch_attempts:
                gave_up = True
                logger.error(f"Max relaunch attempts ({max_relaunch_attempts}) reached — giving up, needs manual attention. Last reasons: {reasons}")
                djj.send_macos_notification("Hermes Watchdog", "Giving up after repeated failures — needs manual attention", subtitle=str(target_folder))
                print("\033[91m⚠️  Giving up after repeated failures — check the log.\033[0m")
                continue

            reason_str = "; ".join(reasons)
            fired = relaunch(reason_str, target_folder, container_path, categories, job_type, relaunch_count + 1, logger)
            if fired:
                relaunch_count += 1
                last_progress_time = time.time()
                djj.send_macos_notification("Hermes Watchdog", f"Relaunched ({relaunch_count}/{max_relaunch_attempts}): {reason_str}", subtitle=str(target_folder))
                print(f"\033[93m🔄 Relaunched ({relaunch_count}/{max_relaunch_attempts}): {reason_str}\033[0m")

    except KeyboardInterrupt:
        logger.info("Stopped by user (Ctrl+C).")
        print("\n\033[93mStopped.\033[0m")


if __name__ == "__main__":
    main()
