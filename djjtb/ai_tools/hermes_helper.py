#!/usr/bin/env python3
"""
Hermes Helper — status/control utilities for Nous Research's Hermes Agent CLI,
plus a standalone Add/Remove Working Folders flow (run as __main__ in its own tab).

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


# ── Standalone Add/Remove Working Folders flow ────────────────────────────────

def _select_indices_to_remove(volumes):
    selected = set()
    while True:
        print("\033[93mMounted folders:\033[0m")
        print("\033[93m" + "-" * 60 + "\033[0m")
        for i, v in enumerate(volumes, 1):
            host, _, container = v.partition(':')
            marker = " ✅" if (i - 1) in selected else ""
            print(f"  {i:2}. {host}  →  {container}{marker}")
        print("\033[93m" + "-" * 60 + "\033[0m")
        if selected:
            print(f"\033[92mSelected for removal ({len(selected)}):\033[0m "
                  f"{', '.join(str(i + 1) for i in sorted(selected))}")
        raw = input("\033[93mEnter a number to toggle, or press Enter to confirm:\033[0m ").strip()
        if raw == '':
            return selected
        try:
            n = int(raw)
            if 1 <= n <= len(volumes):
                idx = n - 1
                if idx in selected:
                    selected.remove(idx)
                else:
                    selected.add(idx)
            else:
                print(f"\033[93mPlease enter a number between 1 and {len(volumes)}.\033[0m\n")
        except ValueError:
            print("\033[93mInvalid input.\033[0m\n")


def _collect_new_folders():
    paths = []
    print("\033[93mEnter host folder paths one at a time. Press Enter on a blank line to finish.\033[0m")
    while True:
        raw = input(" 📁 > ").strip().strip('\'"')
        if raw == '':
            break
        p = Path(raw).expanduser().resolve()
        if not p.is_dir():
            print(f"\033[93m⚠️  '{p}' isn't a folder — try again.\033[0m")
            continue
        paths.append(p)
        print(f"\033[92m➕ Added:\033[0m {p}")
    return paths


def _apply_and_restart(new_volumes):
    write_docker_volumes(new_volumes)
    print("\033[92m✅ config.yaml updated.\033[0m")
    ok, msg = stop_gateway()
    print(f"\033[93m{msg}\033[0m" if ok else f"\033[93m{msg}\033[0m")
    removed = remove_sandbox_containers()
    if removed:
        print(f"\033[93m🗑  Removed {removed} sandbox container(s) so new mounts take effect.\033[0m")
    launch_gateway_window()
    print("\033[92m🚀 Relaunching gateway in a new window...\033[0m")
    time.sleep(2)


def main():
    os.system('clear')
    print("\033[1;93m🪽 Hermes Helper — Add/Remove Working Folders 🪽\033[0m")
    print("\033[92m" + "-" * 60 + "\033[0m")

    volumes = read_docker_volumes()
    action = djj.prompt_choice(
        "\033[93mWhat do you want to do?\033[0m\n1. Add folders\n2. Remove folders\n",
        ['1', '2'], default='1'
    )

    if action == '2':
        if not volumes:
            print("\033[93mNo mounted folders to remove.\033[0m")
            djj.wait_with_skip(3, "Closing")
            return
        to_remove = _select_indices_to_remove(volumes)
        if not to_remove:
            print("\033[93mNothing selected — no changes made.\033[0m")
            djj.wait_with_skip(3, "Closing")
            return
        new_volumes = [v for i, v in enumerate(volumes) if i not in to_remove]
        print(f"\033[93mRemoving {len(to_remove)} mount(s):\033[0m")
        for i in sorted(to_remove):
            print(f"  - {volumes[i]}")
        confirm = djj.prompt_choice("\033[93mApply?\033[0m\n1. Yes\n2. Cancel\n", ['1', '2'], default='1')
        if confirm != '1':
            print("\033[93mCancelled — no changes made.\033[0m")
            djj.wait_with_skip(3, "Closing")
            return
        _apply_and_restart(new_volumes)
        return

    # action == '1': Add
    new_paths = _collect_new_folders()
    if not new_paths:
        print("\033[93mNo folders entered — no changes made.\033[0m")
        djj.wait_with_skip(3, "Closing")
        return

    existing_container_paths = [v.split(':', 1)[1] for v in volumes if ':' in v]
    additions = []
    for p in new_paths:
        cpath = _derive_container_path(
            str(p), existing_container_paths + [a.split(':', 1)[1] for a in additions]
        )
        additions.append(f"{p}:{cpath}")

    print(f"\033[93mAdding {len(additions)} mount(s):\033[0m")
    for a in additions:
        host, _, container = a.partition(':')
        print(f"  {host}  →  {container}")
    confirm = djj.prompt_choice("\033[93mApply?\033[0m\n1. Yes\n2. Cancel\n", ['1', '2'], default='1')
    if confirm != '1':
        print("\033[93mCancelled — no changes made.\033[0m")
        djj.wait_with_skip(3, "Closing")
        return

    _apply_and_restart(volumes + additions)


if __name__ == "__main__":
    main()
