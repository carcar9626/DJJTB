#!/usr/bin/env python3
"""Localhost Port Manager — check / restart / stop whatever listens on a port.

Restart works by reading the listening process's command line and working
directory *before* killing it, then relaunching that same command in that same
folder, detached, with output going to djjtb/logs/port_manager_<port>.log.
"""
import os
import shlex
import signal
import subprocess
import textwrap
import time
from datetime import datetime
from pathlib import Path

import djjtb.utils as djj

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "port_manager_log.txt"
WIDTH = 46  # terminal is fixed at 50 columns; leave room for indent

# Listeners we should never kill/relaunch from here (their own manager owns them)
MANAGED_MARKERS = ("com.docker", "docker-proxy", "vpnkit", "OrbStack", "ollama")


def log(msg):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def launchd_label(pid):
    """Label of the launchd user job that owns this PID, or '' if none."""
    for line in _run(["launchctl", "list"]).splitlines()[1:]:
        cols = line.split(None, 2)
        if len(cols) == 3 and cols[0] == str(pid):
            return cols[2]
    return ""


def launchd_target(label):
    return f"gui/{os.getuid()}/{label}"


def find_listeners(port):
    """Return a list of dicts (pid, user, command, cwd) listening on TCP port."""
    pids = _run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"]).split()
    seen, found = set(), []
    for pid in pids:
        if pid in seen or not pid.isdigit():
            continue
        seen.add(pid)
        cwd = ""
        for line in _run(["lsof", "-a", "-p", pid, "-d", "cwd", "-Fn"]).splitlines():
            if line.startswith("n"):
                cwd = line[1:]
        found.append({
            "pid": int(pid),
            "user": _run(["ps", "-p", pid, "-o", "user="]),
            "command": _run(["ps", "-ww", "-p", pid, "-o", "command="]),
            "cwd": cwd,
            "label": launchd_label(pid),
        })
    return found


def is_managed(info):
    return any(m.lower() in info["command"].lower() for m in MANAGED_MARKERS)


def print_wrapped(label, text):
    lines = textwrap.wrap(text, WIDTH - len(label), break_long_words=True) or [""]
    print(f"  {label}{lines[0]}")
    for extra in lines[1:]:
        print(f"  {' ' * len(label)}{extra}")


def show_listeners(port, listeners):
    if not listeners:
        print(f"\n\033[91m🔴 Nothing is listening on :{port}\033[0m")
        return
    print(f"\n\033[92m🟢 :{port} is in use\033[0m")
    for info in listeners:
        print("\033[92m" + "-" * 50 + "\033[0m")
        print(f"  PID:  {info['pid']}  (user: {info['user']})")
        print_wrapped("Cmd:  ", info["command"])
        print_wrapped("Dir:  ", info["cwd"] or "unknown")
        if info["label"]:
            print_wrapped("launchd: ", info["label"])
        if is_managed(info):
            print("  \033[93m⚠️  Managed by another app — use its own\033[0m")
            print("  \033[93m   controls (docker / ollama) to restart.\033[0m")


def pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def wait_port_free(port, seconds):
    for _ in range(seconds * 4):
        if not find_listeners(port):
            return True
        time.sleep(0.25)
    return False


def confirm(question):
    return djj.prompt_choice(f"\033[93m{question}\033[0m (y/n)", ['y', 'n'], default='n') == 'y'


def check_killable(listeners):
    """Return an error string if we shouldn't touch these listeners, else None."""
    me = os.environ.get("USER", "")
    for info in listeners:
        if is_managed(info):
            return "Managed by another app — not touching it."
        if info["user"] and info["user"] != me:
            return f"Owned by '{info['user']}' — needs sudo, not doing that."
    return None


def stop_listeners(port, listeners):
    """SIGTERM, then offer SIGKILL if it won't die. Returns True if port freed."""
    for info in listeners:
        try:
            os.kill(info["pid"], signal.SIGTERM)
        except ProcessLookupError:
            pass
    if wait_port_free(port, 5):
        return True
    print("\n\033[93m⚠️  Still listening after 5s (ignoring SIGTERM).\033[0m")
    if not confirm("Force kill (SIGKILL)?"):
        return False
    for info in listeners:
        if pid_alive(info["pid"]):
            try:
                os.kill(info["pid"], signal.SIGKILL)
            except ProcessLookupError:
                pass
    return wait_port_free(port, 3)


def do_check(port):
    show_listeners(port, find_listeners(port))


def single_label(listeners):
    labels = {i["label"] for i in listeners}
    return labels.pop() if len(labels) == 1 and listeners[0]["label"] else ""


def do_stop(port):
    listeners = find_listeners(port)
    show_listeners(port, listeners)
    if not listeners:
        return
    err = check_killable(listeners)
    if err:
        print(f"\n\033[91m❌ {err}\033[0m")
        return
    label = single_label(listeners)
    if label:
        # A plain kill is pointless: KeepAlive jobs get respawned by launchd.
        plist = Path.home() / "Library/LaunchAgents" / f"{label}.plist"
        print("\n\033[93mlaunchd would respawn a plain kill.\033[0m")
        print("  Stop = unload the job until it's reloaded.")
        if not confirm(f"Unload {label}?"):
            print("Cancelled.")
            return
        subprocess.run(["launchctl", "bootout", launchd_target(label)],
                       capture_output=True)
        if wait_port_free(port, 8):
            print(f"\n\033[92m✅ :{port} is now free.\033[0m")
            print("  Bring it back with:")
            print(f"  launchctl bootstrap gui/{os.getuid()} {plist}")  # one line: copy-pasteable
            log(f"STOP (launchd bootout) port={port} label={label}")
        else:
            print(f"\n\033[91m❌ :{port} is still in use.\033[0m")
            log(f"STOP (launchd bootout) FAILED port={port} label={label}")
        return
    if not confirm(f"Stop what's on :{port}?"):
        print("Cancelled.")
        return
    if stop_listeners(port, listeners):
        print(f"\n\033[92m✅ :{port} is now free.\033[0m")
        log(f"STOP port={port} pids={[i['pid'] for i in listeners]} cmd={listeners[0]['command']}")
    else:
        print(f"\n\033[91m❌ :{port} is still in use.\033[0m")
        log(f"STOP FAILED port={port}")


def do_restart(port):
    listeners = find_listeners(port)
    show_listeners(port, listeners)
    if not listeners:
        print("\nNothing to restart. Start it manually first.")
        return
    err = check_killable(listeners)
    if err:
        print(f"\n\033[91m❌ {err}\033[0m")
        return
    label = single_label(listeners)
    if label:
        old_pids = {i["pid"] for i in listeners}
        print(f"\n\033[93mlaunchd job — will use launchctl kickstart.\033[0m")
        if not confirm(f"Restart {label}?"):
            print("Cancelled.")
            return
        subprocess.run(["launchctl", "kickstart", "-k", launchd_target(label)],
                       capture_output=True)
        print("\nWaiting for it to come back up...")
        for _ in range(60):  # up to ~15s (launchd ThrottleInterval can delay)
            time.sleep(0.25)
            now = find_listeners(port)
            if now and not ({i["pid"] for i in now} & old_pids):
                print(f"\n\033[92m✅ :{port} is back up (new PID {now[0]['pid']}).\033[0m")
                log(f"RESTART (launchd kickstart) OK port={port} label={label}")
                return
        print(f"\n\033[91m❌ :{port} didn't come back with a new PID.\033[0m")
        log(f"RESTART (launchd kickstart) FAILED port={port} label={label}")
        return
    if len({i["command"] for i in listeners}) > 1:
        print("\n\033[91m❌ Multiple different processes on this port;\033[0m")
        print("   restart is ambiguous. Use Stop instead.")
        return

    # Snapshot the launch command + folder BEFORE killing — it's gone after.
    command, cwd = listeners[0]["command"], listeners[0]["cwd"] or str(Path.home())
    try:
        args = shlex.split(command)
    except ValueError:
        print("\n\033[91m❌ Couldn't parse the original command safely.\033[0m")
        return

    print("\n\033[93mWill relaunch with same command + folder.\033[0m")
    print("  Env vars / venv activation are NOT carried over.")
    if not confirm(f"Restart :{port}?"):
        print("Cancelled.")
        return

    if not stop_listeners(port, listeners):
        print(f"\n\033[91m❌ Couldn't free :{port}; not relaunching.\033[0m")
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = LOG_DIR / f"port_manager_{port}.log"
    try:
        with open(out_path, "ab") as out:
            subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out,
                             stderr=subprocess.STDOUT, start_new_session=True)
    except (OSError, FileNotFoundError) as e:
        print(f"\n\033[91m❌ Relaunch failed: {e}\033[0m")
        log(f"RESTART FAILED port={port} cmd={command} err={e}")
        return

    print("\nWaiting for it to come back up...")
    for _ in range(40):  # up to ~10s
        time.sleep(0.25)
        if find_listeners(port):
            print(f"\n\033[92m✅ :{port} is back up.\033[0m")
            log(f"RESTART OK port={port} cwd={cwd} cmd={command}")
            return
    print(f"\n\033[91m❌ Relaunched but :{port} isn't listening yet.\033[0m")
    print_wrapped("Check: ", str(out_path))
    log(f"RESTART NO-LISTEN port={port} cwd={cwd} cmd={command}")


def main():
    while True:
        os.system("clear")
        print()
        print("\033[1;96m🌐 LOCALHOST PORT MANAGER 🌐\033[0m")
        print("\033[92m" + "-" * 50 + "\033[0m")
        port = djj.get_int_input("Enter a port (e.g. 8642)", min_val=1, max_val=65535)
        if port is None:
            break

        print("\n 💰 \033[4;93m1\033[0m  Check")
        print(" 💰 \033[4;93m2\033[0m  Restart")
        print(" 💰 \033[4;93m3\033[0m  Stop")
        action = djj.prompt_choice("\033[93mAction\033[0m", ['1', '2', '3'], default='1')

        {"1": do_check, "2": do_restart, "3": do_stop}[action](port)

        if djj.what_next() == 'exit':
            break


if __name__ == "__main__":
    main()
