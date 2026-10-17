"""Launch (or focus) the standalone DJJPS desktop apps from the DJJTB menu.

Same behaviour as the "Launch" button in djjtb-suite's AI Tools page: start the app's own venv
python on its entry script in a new session — no Terminal window, no frontend rebuild — using the
frontend `dist/` it already has. If the app is already running, bring its window to the front
instead of opening a second copy. Python code is read fresh on every launch; only the React/TS
frontend needs `npm run build` (run the app's `run_*_desktop.command` once after changing it).

stdlib + AppKit only (AppKit comes with pywebview's pyobjc), so DJJTB's venv needs nothing new.
Never imports the apps' code. Output of a launched app goes to
DJJTB_output/launcher_logs/<id>.log.
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

DJJPS = Path("/Users/home/Documents/Scripts/DJJPS")
LOG_DIR = Path("/Users/home/Documents/Scripts/DJJTB_output/launcher_logs")


@dataclass(frozen=True)
class DesktopApp:
    id: str
    label: str
    repo: str       # folder under DJJPS
    script: str     # entry script, relative to the repo folder
    command: str    # the app's rebuild-and-launch .command, relative to the repo folder

    @property
    def root(self) -> Path:
        return DJJPS / self.repo

    @property
    def entry(self) -> Path:
        return self.root / self.script

    @property
    def python(self) -> Path:
        return self.root / "backend" / "venv" / "bin" / "python3"


APPS = {
    a.id: a
    for a in [
        DesktopApp("djjtb-suite", "DJJTB Suite", "djjtb-suite", "backend/desktop_app.py", "run_djjtb_suite_desktop.command"),
        DesktopApp("smart-crop", "Smart Crop", "smart-crop-djjtb", "backend/main.py", "run_smart_crop_desktop.command"),
        DesktopApp("facefusion", "FaceFusion", "facefusion-desktop-djjtb", "backend/main.py", "run_facefusion_desktop.command"),
        DesktopApp("joycaption", "JoyCaption", "joycaption-desktop-ollama-djjtb", "backend/main.py", "run_joycaption_desktop.command"),
        DesktopApp("upscaler-ai", "Upscaler AI", "upscaler-ai-desktop-djjtb", "backend/main.py", "run_upscaler_ai_desktop.command"),
        DesktopApp("comfyui-batch", "ComfyUI Batch", "comfyui-batch-desktop-djjtb", "backend/main.py", "run_comfyui_batch_desktop.command"),
    ]
}


def _cwd_of(pid: int) -> Path | None:
    """Working directory of a process (needs lsof; only called for the few candidates)."""
    try:
        out = subprocess.run(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in out.splitlines():
        if line.startswith("n"):
            return Path(line[1:]).resolve()
    return None


def find_pids(app: DesktopApp) -> list[int]:
    """Running instances. Matches the entry script by absolute path (how this launcher starts it) or,
    for apps started by their .command — which runs `python main.py` from backend/ — by a relative
    script name plus the process's working directory."""
    out = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout
    script_name = app.entry.name
    pids = []
    for line in out.splitlines():
        parts = line.split(None, 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        pid, command = int(parts[0]), parts[1]
        last = command.rsplit(None, 1)[-1]
        if pid == os.getpid() or not last.endswith(script_name) or "python" not in command.lower():
            continue
        script = Path(last)
        if script.is_absolute():
            hit = script == app.entry
        else:
            hit = _cwd_of(pid) == app.entry.parent.resolve()
        if hit:
            pids.append(pid)
    return pids


def focus(pid: int) -> bool:
    """Raise a running app's window (no accessibility permission needed, unlike System Events)."""
    try:
        import AppKit
        running = AppKit.NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        return bool(running and running.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps))
    except Exception:
        return False


def rebuild_and_launch(app_id: str) -> tuple[str, str]:
    """Open the app's run_*_desktop.command in Terminal (what double-clicking it does): rebuilds the
    frontend (`npm run build`), then runs the app in that window. Use after changing the app's
    React/TS source. Refused while the app is already running — it would open a second copy.
    Returns (status, message); status is "rebuilding" or "error"."""
    app = APPS[app_id]
    if find_pids(app):
        return "error", f"{app.label} is running — close it first, then rebuild & launch."
    command = app.root / app.command
    if not command.exists():
        return "error", f"{app.label}'s rebuild launcher is missing: {command}"
    subprocess.Popen(["open", str(command)])
    return "rebuilding", f"{app.label}: rebuilding in a Terminal window, then it opens."


def launch(app_id: str) -> tuple[str, str]:
    """Start the app, or raise it if it's already open.
    Returns (status, message); status is "launched", "focused" or "error"."""
    app = APPS[app_id]

    pids = find_pids(app)
    if pids:
        raised = focus(pids[0])
        return "focused", f"{app.label} is already running" + (" — brought to the front." if raised else " — switch to it with Cmd+Tab.")

    if not app.python.exists():
        return "error", f"{app.label}'s venv isn't set up: {app.python}"
    if not app.entry.exists():
        return "error", f"{app.label}'s entry script is missing: {app.entry}"
    if not (app.root / "frontend" / "dist" / "index.html").exists():
        return "error", f"{app.label}'s frontend isn't built yet — run {app.root / app.command} once."

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / f"{app.id}.log", "ab") as log:
        subprocess.Popen(
            [str(app.python), str(app.entry)], cwd=app.entry.parent,
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True,   # own session: outlives this menu, no shared terminal
        )
    return "launched", f"{app.label} launching — its window will appear in a moment."
