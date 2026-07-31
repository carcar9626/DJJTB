#!/usr/bin/env python3
"""
Hermes Core — shared, non-interactive logic for Nous Research's Hermes Agent
CLI, used by both hermes_helper.py (menu/CLI) and hermes_watchdog.py
(unattended stall/crash monitor). Nothing in this module prompts for input
or prints to the terminal.

Docker sandbox mounts (terminal.docker_volumes in config.yaml) are edited with a
surgical text-block rewrite rather than a full YAML parse/dump, so the rest of the
hand-maintained config file (comments, personality blocks, key order) is left
byte-for-byte untouched.
"""

import os
import re
import subprocess
import time
from pathlib import Path

import djjtb.utils as djj

HERMES_BIN = os.path.expanduser("~/.local/bin/hermes")
CONFIG_PATH = os.path.expanduser("~/.hermes/config.yaml")
ENV_PATH = os.path.expanduser("~/.hermes/.env")

GATEWAY_PROFILE = "djjtb"
GATEWAY_BOUNDS = "1000, 120, 1700, 700"


# ── Status / process helpers ──────────────────────────────────────────────────

def gateway_pids():
    """PIDs of any running `hermes gateway` process (foreground or `gateway run`)."""
    result = subprocess.run(["pgrep", "-f", "hermes gateway"], stdout=subprocess.PIPE, text=True)
    return [p for p in result.stdout.split() if p]


def hermes_desktop_pids():
    """PIDs of any running `hermes serve` process — the separate process
    Hermes Desktop uses, distinct from `hermes gateway`. Desktop can silently
    recreate its own sandbox container and keep working a folder in parallel
    with a gateway-side session (confirmed: duplicate processing of the same
    files, real wasted GPU load), so this is checked as a startup guard
    before anything that auto-relaunches the gateway."""
    result = subprocess.run(["pgrep", "-f", "hermes serve"], stdout=subprocess.PIPE, text=True)
    return [p for p in result.stdout.split() if p]


def docker_running():
    return subprocess.run(
        ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode == 0


def port_listening(port):
    result = subprocess.run(
        ["lsof", f"-iTCP:{port}", "-sTCP:LISTEN"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    )
    return bool(result.stdout.strip())


def read_api_port():
    """Read API_SERVER_PORT from .env, falling back to the documented default."""
    try:
        for line in Path(ENV_PATH).read_text().splitlines():
            line = line.strip()
            if line.startswith("API_SERVER_PORT="):
                return int(line.split("=", 1)[1].strip())
    except FileNotFoundError:
        pass
    return 8643


def read_api_key():
    """Read API_SERVER_KEY from .env. Returns None if not found."""
    try:
        for line in Path(ENV_PATH).read_text().splitlines():
            line = line.strip()
            if line.startswith("API_SERVER_KEY="):
                return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return None


def sandbox_containers():
    """(name, status) pairs for running Hermes sandbox containers."""
    if not docker_running():
        return []
    result = subprocess.run(
        ["docker", "ps", "--filter", "label=hermes-agent=1", "--format", "{{.Names}}\t{{.Status}}"],
        stdout=subprocess.PIPE, text=True
    )
    rows = [line.split("\t", 1) for line in result.stdout.splitlines() if line.strip()]
    return [(r[0], r[1] if len(r) > 1 else "") for r in rows]


def status_report():
    pids = gateway_pids()
    port = read_api_port()
    lines = [
        f"Gateway process : {'🟢 running (pid ' + ', '.join(pids) + ')' if pids else '🔴 not running'}",
        f"API port {port}  : {'🟢 listening' if port_listening(port) else '🔴 not listening'}",
        f"Docker Desktop  : {'🟢 running' if docker_running() else '🔴 not running'}",
    ]
    containers = sandbox_containers()
    if containers:
        lines.append("Sandbox containers:")
        lines.extend(f"  {name}  ({status})" for name, status in containers)
    elif docker_running():
        lines.append("Sandbox containers: none running")
    return "\n".join(lines)


def stop_gateway():
    """Graceful SIGTERM, escalating to SIGKILL after ~10s. Returns (changed, message)."""
    pids = gateway_pids()
    if not pids:
        return False, "Gateway wasn't running."
    for pid in pids:
        subprocess.run(["kill", pid], stderr=subprocess.DEVNULL)
    for _ in range(10):
        if not gateway_pids():
            return True, f"Gateway stopped (pid {', '.join(pids)})."
        time.sleep(1)
    remaining = gateway_pids()
    for pid in remaining:
        subprocess.run(["kill", "-9", pid], stderr=subprocess.DEVNULL)
    return True, f"Gateway force-stopped (pid {', '.join(pids)})."


def remove_sandbox_containers():
    """
    Force-remove all Hermes sandbox containers so the next gateway launch is
    guaranteed to recreate them with the current docker_volumes list, rather
    than silently reusing a container built with a stale mount set. Everything
    that matters (skills, caches, the container's /root home) is host-mounted,
    so this never loses state — it only discards the ephemeral container layer.
    """
    if not docker_running():
        return 0
    result = subprocess.run(
        ["docker", "ps", "-aq", "--filter", "label=hermes-agent=1"],
        stdout=subprocess.PIPE, text=True
    )
    ids = [i for i in result.stdout.split() if i]
    if not ids:
        return 0
    subprocess.run(["docker", "rm", "-f"] + ids, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return len(ids)


def launch_gateway_window():
    djj.open_terminal_with_settings(f"{HERMES_BIN} gateway", GATEWAY_PROFILE, GATEWAY_BOUNDS)


def restart_gateway():
    """Stop the gateway (if running) and relaunch it in a new window. Does not
    touch sandbox containers — that's only needed after a docker_volumes edit."""
    was_running, stop_msg = stop_gateway()
    launch_gateway_window()
    prefix = stop_msg if was_running else "Gateway wasn't running."
    return True, f"{prefix} Relaunching in a new window."


# ── docker_volumes block editing (surgical, not a full YAML round-trip) ──────

def _find_docker_volumes_block(lines):
    """Locate the docker_volumes: key and its list-item lines under terminal:."""
    key_idx = None
    key_indent = None
    for i, line in enumerate(lines):
        m = re.match(r'^( *)docker_volumes:\s*(\[.*\])?\s*$', line)
        if m:
            key_idx = i
            key_indent = len(m.group(1))
            break
    if key_idx is None:
        return None
    end_idx = key_idx + 1
    item_indent = None
    while end_idx < len(lines):
        m2 = re.match(r'^( *)- ', lines[end_idx])
        if not m2 or len(m2.group(1)) <= key_indent:
            break
        item_indent = len(m2.group(1))
        end_idx += 1
    return key_idx, end_idx, key_indent, item_indent or (key_indent + 2)


def read_docker_volumes():
    """Return the current docker_volumes list as ['host:container', ...]."""
    lines = Path(CONFIG_PATH).read_text().splitlines()
    block = _find_docker_volumes_block(lines)
    if block is None:
        return []
    key_idx, end_idx, _, _ = block
    volumes = []
    for line in lines[key_idx + 1:end_idx]:
        val = line.strip()[2:].strip().strip('"\'')
        if val:
            volumes.append(val)
    return volumes


def write_docker_volumes(volumes):
    """
    Rewrite only the docker_volumes list block in config.yaml, leaving every
    other line untouched. Backs up the config once before writing.
    """
    path = Path(CONFIG_PATH)
    lines = path.read_text().splitlines()
    block = _find_docker_volumes_block(lines)
    if block is None:
        raise RuntimeError(
            "docker_volumes: not found under terminal: in config.yaml — refusing to guess where to insert it."
        )
    key_idx, end_idx, key_indent, item_indent = block

    if volumes:
        new_block = [' ' * key_indent + 'docker_volumes:']
        new_block += [' ' * item_indent + f'- "{v}"' for v in volumes]
    else:
        new_block = [' ' * key_indent + 'docker_volumes: []']

    backup_path = path.with_suffix(path.suffix + ".bak")
    backup_path.write_text(path.read_text())

    new_lines = lines[:key_idx] + new_block + lines[end_idx:]
    path.write_text('\n'.join(new_lines) + '\n')


def _derive_container_path(host_path, existing_container_paths):
    base = os.path.basename(os.path.normpath(host_path)) or "mount"
    candidate = f"/workspace/{base}"
    if candidate not in existing_container_paths:
        return candidate
    n = 2
    while f"/workspace/{base}-{n}" in existing_container_paths:
        n += 1
    return f"/workspace/{base}-{n}"


def host_path_to_container_path(host_path):
    """
    Map a real Mac path to its container-side equivalent by matching it
    against the current docker_volumes mounts. Raises ValueError if no
    mounted folder covers it — the folder has to be mounted (Hermes Helper
    -> Add/Remove Working Folders) before a resume prompt can reference it.
    """
    host_path = str(Path(host_path).expanduser().resolve())
    best = None
    for v in read_docker_volumes():
        host, _, container = v.partition(':')
        host = str(Path(host).expanduser().resolve())
        if host_path == host or host_path.startswith(host + os.sep):
            if best is None or len(host) > len(best[0]):
                best = (host, container)
    if best is None:
        raise ValueError(
            f"'{host_path}' isn't under any mounted docker_volumes folder — "
            "mount it first via Hermes Helper -> Add/Remove Working Folders."
        )
    host, container = best
    suffix = host_path[len(host):].lstrip(os.sep)
    return f"{container}/{suffix}" if suffix else container


# ── Log parsing / verification (never trust a chat's own "done" claim) ───────

def count_real_log_entries(log_path):
    """
    Parse a `filename | field | field...` style DJJIF pipeline log (covers
    inventory-log.txt, duplicate-log.txt, sort-log.txt), keeping only
    genuine, first-occurrence-per-filename entries. Deliberately more
    conservative than a naive `grep -c` / `wc -l`: skips banner lines
    (`=== Phase N ===`), the column-header row, malformed/short lines, and
    duplicate re-logged entries — the exact corruption shapes confirmed in
    real log files (heredoc leaks, multi-line wraps, re-runs).

    Returns (count, set_of_filenames).
    """
    path = Path(log_path)
    if not path.exists():
        return 0, set()
    seen = set()
    for line in path.read_text(errors='replace').splitlines():
        parts = [p.strip() for p in line.split('|')]
        parts = [p for p in parts if p != '']
        if len(parts) < 2:
            continue
        filename = parts[0]
        if not filename or '.' not in filename or filename.lower() == 'filename':
            continue
        seen.add(filename)
    return len(seen), seen


def count_image_files(folder):
    """Recursive real-file count under folder, using the repo's shared
    IMAGE_EXTENSIONS check (djj.is_image_extension) rather than reimplementing it."""
    folder = Path(folder)
    if not folder.is_dir():
        return 0
    return sum(1 for p in folder.rglob('*') if p.is_file() and djj.is_image_extension(p.name))


PHASE_LOG_NAMES = {
    'phase1': 'inventory-log.txt',
    'phase2': 'duplicate-log.txt',
    'phase3': 'sort-log.txt',
}


def detect_pipeline_phase(target_folder):
    """
    Figure out which phase of the inventory -> dedupe -> categorize pipeline
    is actually in progress, by recomputing real counts from disk — never
    from a chat message. Returns a dict:
      {phase, real_file_count, inventory_count, duplicate_count, sort_count}

    Phase-2 completion can't be robustly verified from duplicate-log.txt
    content alone — real logs have sometimes been free prose rather than
    structured `filename | KEPT/FLAGGED | reason` lines (confirmed against
    real cowork-duplicate-log.txt content). Sort-log.txt gaining any real
    entries is used as proof Phase 2 concluded instead, since Phase 3 only
    ever starts after Phase 2 in the pipeline's own prompt flow.
    """
    folder = Path(target_folder)
    real_count = count_image_files(folder)
    inv_count, _ = count_real_log_entries(folder / PHASE_LOG_NAMES['phase1'])
    dup_count, _ = count_real_log_entries(folder / PHASE_LOG_NAMES['phase2'])
    sort_count, _ = count_real_log_entries(folder / PHASE_LOG_NAMES['phase3'])

    if inv_count < real_count:
        phase = 'phase1'
    elif sort_count > 0:
        phase = 'phase3'
    else:
        phase = 'phase2'

    return {
        'phase': phase,
        'real_file_count': real_count,
        'inventory_count': inv_count,
        'duplicate_count': dup_count,
        'sort_count': sort_count,
    }


def verify_job_complete(target_folder, duplicate_tolerance=0):
    """
    A job is only genuinely finished when sort-log.txt has moved/logged
    every real file (minus a small, documented tolerance for files flagged
    as duplicates) — never on a claimed "done" message. Returns
    (is_complete, detail_dict) where detail_dict is the same shape as
    detect_pipeline_phase(), for transparent per-cycle logging.
    """
    detail = detect_pipeline_phase(target_folder)
    is_complete = (
        detail['inventory_count'] >= detail['real_file_count'] > 0
        and detail['sort_count'] >= detail['real_file_count'] - duplicate_tolerance
    )
    return is_complete, detail
