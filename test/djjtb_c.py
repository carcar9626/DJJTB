# djjtb_c.py - Centralized Path + Utility Handler (Beta v0.1)
import os
import sys
import subprocess
import logging
import datetime
from pathlib import Path

# === BASE PATH SETUP ===
BASE = Path(__file__).resolve().parent  # Folder containing this file
PROJECT_NAME = "DJJTB"
OUTPUT_ROOT = BASE / "Output"
LOG_ROOT = OUTPUT_ROOT / "logs"

# Ensure base folders exist
for folder in [OUTPUT_ROOT, LOG_ROOT]:
    folder.mkdir(parents=True, exist_ok=True)

# === TIMESTAMP HELPERS ===
def timestamp_now(fmt="%Y-%m-%d_%H-%M-%S"):
    return datetime.datetime.now().strftime(fmt)

# === SMART OUTPUT PATH ===
def get_output_path(script: str, filename: str = None, timestamped=False, ext=None) -> Path:
    """
    Returns a centralized path for output, organized by script name
    """
    subdir = OUTPUT_ROOT / script
    subdir.mkdir(parents=True, exist_ok=True)

    if filename:
        if timestamped:
            stem = Path(filename).stem
            suffix = ext if ext else Path(filename).suffix or ".txt"
            filename = f"{stem}_{timestamp_now()}{suffix}"
        return subdir / filename
    return subdir

# === LOGGING ===
def init_logger(script: str, name="log"):
    log_path = LOG_ROOT / f"{script}_{timestamp_now()}.log"
    logging.basicConfig(
        filename=log_path,
        level=logging.DEBUG,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info("Logger initialized for %s", script)
    return log_path

# === SCRIPT RUNNER ===
def run_script(script_filename: str, args=None):
    script_path = BASE / script_filename
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args if isinstance(args, list) else [args])

    subprocess.run(cmd)

# === PROJECT INFO ===
__version__ = "0.1-beta"
__all__ = [
    "BASE", "OUTPUT_ROOT", "LOG_ROOT",
    "get_output_path", "init_logger", "run_script",
    "timestamp_now"
]