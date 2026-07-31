#!/usr/bin/env python3
"""
Hermes Helper — DJJTB main-menu entry points for Nous Research's Hermes
Agent CLI (status/control, dispatched from djjtb.py's Hermes Helper submenu),
plus a standalone Add/Remove Working Folders flow (run as __main__ in its
own tab). Shared, non-interactive logic lives in hermes_core.py.
"""

import os
import time
from pathlib import Path

import djjtb.utils as djj
from . import hermes_core as hc


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
    hc.write_docker_volumes(new_volumes)
    print("\033[92m✅ config.yaml updated.\033[0m")
    ok, msg = hc.stop_gateway()
    print(f"\033[93m{msg}\033[0m" if ok else f"\033[93m{msg}\033[0m")
    removed = hc.remove_sandbox_containers()
    if removed:
        print(f"\033[93m🗑  Removed {removed} sandbox container(s) so new mounts take effect.\033[0m")
    hc.launch_gateway_window()
    print("\033[92m🚀 Relaunching gateway in a new window...\033[0m")
    time.sleep(2)


def main():
    os.system('clear')
    print("\033[1;93m🪽 Hermes Helper — Add/Remove Working Folders 🪽\033[0m")
    print("\033[92m" + "-" * 60 + "\033[0m")

    volumes = hc.read_docker_volumes()
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
        cpath = hc._derive_container_path(
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
