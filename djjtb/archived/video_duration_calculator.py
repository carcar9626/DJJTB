import os
import json
import logging
import subprocess
from pathlib import Path

import webview
from webview.dom import DOMEventHandler

import djjtb.utils as djj

os.system('clear')
print()
print("Video Duration Calculator running... (close the window to quit)")

LOG_DIR = Path("~/Documents/Scripts/DJJTB/djjtb/logs").expanduser()
LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_logger():
    log_file = LOG_DIR / "video_duration_calculator_log.txt"
    logger = logging.getLogger('djjtb.video_duration_calculator')
    logger.setLevel(logging.INFO)
    logger.handlers = []
    logger.propagate = False
    handler = logging.FileHandler(log_file, mode='a')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)
    logger.info("===== RUN START =====")
    return logger


def get_duration(video_path):
    """Return duration in seconds via ffprobe, or None on failure."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return None


def format_duration(seconds):
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def collect_videos(paths, include_subfolders=False):
    videos = []
    for p in paths:
        try:
            path = Path(p)
            if path.is_dir():
                videos.extend(djj.collect_videos_from_folder(str(path), include_subfolders=include_subfolders))
            elif path.is_file() and path.suffix.lower() in djj.VIDEO_EXTENSIONS:
                videos.append(str(path))
        except OSError:
            continue
    return sorted(set(videos), key=str.lower)


def build_summary(video_paths, logger):
    total_seconds = 0.0
    entries = []
    error_count = 0

    for video_path in video_paths:
        duration = get_duration(video_path)
        name = os.path.basename(video_path)
        if duration is None:
            logger.error(f"Failed to read duration: {video_path}")
            error_count += 1
            continue
        total_seconds += duration
        entries.append({"name": name, "seconds": duration, "formatted": format_duration(duration)})

    logger.info(
        f"Videos: {len(entries)}, errors: {error_count}, "
        f"total: {format_duration(total_seconds)} ({total_seconds:.1f}s)"
    )

    return {
        "count": len(entries),
        "errorCount": error_count,
        "totalSeconds": total_seconds,
        "totalFormatted": format_duration(total_seconds),
        "videos": entries,
    }


class Api:
    def __init__(self, logger):
        self.logger = logger
        self.include_subfolders = False

    def browse_files(self):
        result = webview.windows[0].create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True)
        return list(result) if result else []

    def browse_folder(self):
        result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        return result[0] if result else None

    def set_include_subfolders(self, value):
        self.include_subfolders = bool(value)

    def calculate(self, paths, include_subfolders=False):
        videos = collect_videos(paths, include_subfolders)
        return build_summary(videos, self.logger)


def bind(window, logger, api):
    def on_drop(e):
        files = e.get('dataTransfer', {}).get('files', [])
        paths = [f.get('pywebviewFullPath') for f in files if f.get('pywebviewFullPath')]
        if not paths:
            return
        videos = collect_videos(paths, api.include_subfolders)
        summary = build_summary(videos, logger)
        # Non-blocking: a DOM event handler runs on the webview's own thread, so a
        # synchronous evaluate_js() call here (waiting on its own thread) would deadlock.
        window.evaluate_js(f'renderResults({json.dumps(summary)})', lambda r: None)

    window.dom.document.events.drop += DOMEventHandler(on_drop, True, True)


HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 16px;
    background: #1a1a1e; color: #e8e8ea;
    font: 13px -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
    -webkit-user-select: none; user-select: none;
    height: 100vh; display: flex; flex-direction: column; gap: 12px;
  }
  h1 {
    margin: 0; font-size: 15px; font-weight: 600; color: #f5f5f7;
  }
  #dropzone {
    border: 2px dashed #45454c; border-radius: 10px;
    padding: 22px 12px; text-align: center; color: #9a9aa2;
    transition: border-color .15s, background .15s, color .15s;
    flex-shrink: 0;
  }
  #dropzone.drag { border-color: #5e9eff; background: #202538; color: #cfe0ff; }
  .buttons { display: flex; gap: 8px; margin-top: 10px; justify-content: center; }
  button {
    background: #2c2c33; color: #e8e8ea; border: 1px solid #3d3d45;
    border-radius: 6px; padding: 6px 12px; font-size: 12px; cursor: pointer;
  }
  button:hover { background: #37373f; }
  button:active { background: #26262c; }
  label.check {
    display: flex; align-items: center; gap: 6px; color: #9a9aa2; font-size: 12px;
    justify-content: center; margin-top: 10px;
  }
  #summary {
    flex-shrink: 0; padding: 10px 12px; background: #202024; border-radius: 8px;
    display: none;
  }
  #summary.show { display: block; }
  #totalLine { font-size: 20px; font-weight: 700; color: #6fd88a; }
  #countLine { color: #9a9aa2; font-size: 12px; margin-top: 2px; }
  #errorLine { color: #ff8a8a; font-size: 12px; margin-top: 2px; display: none; }
  #list {
    flex: 1; overflow-y: auto; background: #202024; border-radius: 8px;
    padding: 4px 0; display: none;
  }
  #list.show { display: block; }
  .row {
    display: flex; justify-content: space-between; gap: 10px;
    padding: 4px 12px; font-size: 12px; border-bottom: 1px solid #29292f;
  }
  .row:last-child { border-bottom: none; }
  .row .dur { color: #9a9aa2; font-variant-numeric: tabular-nums; flex-shrink: 0; }
  .row .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  #clearBtn { align-self: center; display: none; }
  #clearBtn.show { display: inline-block; }
</style>
</head>
<body>
  <h1>Video Duration Calculator</h1>

  <div id="dropzone">
    Drop video files or a folder here
    <div class="buttons">
      <button onclick="browseFiles()">Browse Files</button>
      <button onclick="browseFolder()">Browse Folder</button>
    </div>
    <label class="check"><input type="checkbox" id="subfolders" onchange="pywebview.api.set_include_subfolders(this.checked)"> Include subfolders</label>
  </div>

  <div id="summary">
    <div id="totalLine">0:00</div>
    <div id="countLine">0 videos</div>
    <div id="errorLine"></div>
  </div>

  <div id="list"></div>
  <button id="clearBtn" onclick="clearResults()">Clear</button>

<script>
  const dropzone = document.getElementById('dropzone');

  ['dragenter', 'dragover'].forEach(evt =>
    dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.add('drag'); })
  );
  ['dragleave', 'drop'].forEach(evt =>
    dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.remove('drag'); })
  );

  async function browseFiles() {
    const paths = await pywebview.api.browse_files();
    if (paths && paths.length) runCalculate(paths);
  }

  async function browseFolder() {
    const path = await pywebview.api.browse_folder();
    if (path) runCalculate([path]);
  }

  async function runCalculate(paths) {
    const includeSub = document.getElementById('subfolders').checked;
    const data = await pywebview.api.calculate(paths, includeSub);
    renderResults(data);
  }

  function renderResults(data) {
    const summary = document.getElementById('summary');
    const list = document.getElementById('list');
    const clearBtn = document.getElementById('clearBtn');

    document.getElementById('totalLine').textContent = data.totalFormatted;
    document.getElementById('countLine').textContent =
      data.count + (data.count === 1 ? ' video' : ' videos');

    const errorLine = document.getElementById('errorLine');
    if (data.errorCount > 0) {
      errorLine.textContent = data.errorCount + ' file(s) could not be read';
      errorLine.style.display = 'block';
    } else {
      errorLine.style.display = 'none';
    }

    list.innerHTML = data.videos.map(v =>
      `<div class="row"><span class="name">${escapeHtml(v.name)}</span><span class="dur">${v.formatted}</span></div>`
    ).join('');

    summary.classList.add('show');
    list.classList.toggle('show', data.videos.length > 0);
    clearBtn.classList.add('show');
  }

  function clearResults() {
    document.getElementById('summary').classList.remove('show');
    document.getElementById('list').classList.remove('show');
    document.getElementById('list').innerHTML = '';
    document.getElementById('clearBtn').classList.remove('show');
  }

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }
</script>
</body>
</html>
"""


def main():
    logger = get_logger()
    api = Api(logger)
    window = webview.create_window(
        "Video Duration Calculator", html=HTML, js_api=api,
        width=460, height=620, resizable=True
    )
    webview.start(lambda: bind(window, logger, api), debug=False)


if __name__ == "__main__":
    main()
