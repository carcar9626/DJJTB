import os
import csv
import json
import base64
import tempfile
import mimetypes
import subprocess
from io import BytesIO
from pathlib import Path
from datetime import datetime

import webview
from webview.dom import DOMEventHandler
from PIL import Image

import djjtb.utils as djj

os.system('clear')
print()
print("Media Dashboard running... (close the window to quit)")

IMAGE_SEARCH_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')


# ─── File info (Info tab) ──────────────────────────────────────────────────

def classify_resolution(height):
    if height >= 2160:
        return "4K"
    elif height >= 1440:
        return "2K"
    elif height >= 1080:
        return "1080p"
    elif height >= 720:
        return "720p"
    elif height >= 480:
        return "480p"
    return f"{height}p"


def get_video_metadata(path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,bit_rate:format=duration,bit_rate,size",
        "-of", "json", str(path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None

    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format", {})

    width = stream.get("width")
    height = stream.get("height")

    fps = None
    r_frame_rate = stream.get("r_frame_rate")
    if r_frame_rate and "/" in r_frame_rate:
        num, den = r_frame_rate.split("/")
        try:
            den_f = float(den)
            fps = (float(num) / den_f) if den_f else None
        except ValueError:
            fps = None

    duration = fmt.get("duration")
    duration = float(duration) if duration else None

    bit_rate = stream.get("bit_rate") or fmt.get("bit_rate")
    bit_rate = float(bit_rate) if bit_rate else None
    calculated_bitrate = bit_rate is None
    if bit_rate is None and duration:
        size = fmt.get("size")
        if size:
            bit_rate = (float(size) * 8) / duration

    return {
        "width": width, "height": height, "fps": fps,
        "duration": duration, "bit_rate": bit_rate,
        "bit_rate_calculated": calculated_bitrate,
    }


def collect_paths(path, include_subfolders):
    if path.is_file():
        return [path]
    if path.is_dir():
        files = path.rglob("*") if include_subfolders else path.glob("*")
        return [f for f in files if f.is_file()]
    return []


def extract_info(file_path):
    try:
        stat = file_path.stat()
        info = {
            "filename": file_path.name,
            "parentFolder": file_path.parent.name,
            "parentPath": str(file_path.parent),
            "fullPath": str(file_path),
            "extension": file_path.suffix.lower(),
            "sizeMb": f"{stat.st_size / (1024 * 1024):.2f}",
            "dateCreated": datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
            "dateModified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            "dimensions": "", "resolution": "", "aspectRatio": "",
            "duration": "", "durationSeconds": None, "fps": "", "bitRate": "",
        }

        mime, _ = mimetypes.guess_type(file_path)
        if mime and mime.startswith("image"):
            with Image.open(file_path) as img:
                w, h = img.size
            info["dimensions"] = f"{w}x{h}"
            info["aspectRatio"] = f"{w}:{h} ({w / h:.2f})"
            info["resolution"] = classify_resolution(h)
        elif mime and mime.startswith("video"):
            meta = get_video_metadata(file_path)
            if meta and meta["width"] and meta["height"]:
                w, h = meta["width"], meta["height"]
                info["dimensions"] = f"{w}x{h}"
                info["aspectRatio"] = f"{w}:{h} ({w / h:.2f})"
                info["resolution"] = classify_resolution(h)
                if meta["duration"] is not None:
                    info["duration"] = f"{meta['duration']:.2f}s"
                    info["durationSeconds"] = meta["duration"]
                if meta["fps"]:
                    info["fps"] = f"{meta['fps']:.2f}"
                if meta["bit_rate"]:
                    suffix = " (calculated)" if meta["bit_rate_calculated"] else ""
                    info["bitRate"] = f"{meta['bit_rate'] / 1_000_000:.2f} Mbps{suffix}"
        return info
    except (OSError, ValueError):
        return None


# ─── Reverse image search (Search tab) ─────────────────────────────────────

def make_thumbnail_data_uri(path, max_size=320):
    with Image.open(path) as img:
        img = img.convert("RGB")
        img.thumbnail((max_size, max_size))
        buf = BytesIO()
        img.save(buf, "JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"


def copy_image_to_clipboard(path):
    """Copy actual image bytes (not a file reference) to the macOS clipboard."""
    tmp_path = None
    try:
        with Image.open(path) as img:
            img = img.convert("RGB")
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            tmp_path = tmp.name
            tmp.close()
            img.save(tmp_path, "JPEG", quality=95)
        script = f'set the clipboard to (read (POSIX file "{tmp_path}") as JPEG picture)'
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ─── Api ────────────────────────────────────────────────────────────────────

class Api:
    def __init__(self):
        self.active_tab = "info"
        self.include_subfolders = False
        self.pending_search_path = None

    def set_active_tab(self, name):
        self.active_tab = name

    def set_include_subfolders(self, value):
        self.include_subfolders = bool(value)

    # Info tab
    def browse_info_files(self):
        result = webview.windows[0].create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True)
        return list(result) if result else []

    def browse_info_folder(self):
        result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        return result[0] if result else None

    def get_info(self, paths):
        entries = []
        for p in paths:
            path = Path(p)
            for f in collect_paths(path, self.include_subfolders):
                info = extract_info(f)
                if info:
                    entries.append(info)
        return entries

    def reveal(self, path):
        if os.path.exists(path):
            subprocess.run(["open", "-R", path])

    def export_csv(self, rows):
        if not rows:
            return {"ok": False}
        save_path = webview.windows[0].create_file_dialog(
            webview.SAVE_DIALOG, save_filename="media_info.csv"
        )
        if not save_path:
            return {"ok": False}
        save_path = save_path if isinstance(save_path, str) else save_path[0]
        keys = list(rows[0].keys())
        with open(save_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
        subprocess.run(["open", "-R", save_path])
        return {"ok": True, "path": save_path}

    # Search tab
    def browse_search_image(self):
        result = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=("Image Files (*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp)",)
        )
        return result[0] if result else None

    def load_search_preview(self, path):
        try:
            data_uri = make_thumbnail_data_uri(path)
        except (OSError, ValueError):
            return {"ok": False}
        self.pending_search_path = path
        return {"ok": True, "thumbnail": data_uri, "filename": os.path.basename(path)}

    def do_reverse_search(self):
        if not self.pending_search_path:
            return {"ok": False, "error": "No image loaded"}
        ok = copy_image_to_clipboard(self.pending_search_path)
        if ok:
            subprocess.run(["open", "-a", "Google Chrome", "https://www.google.com/?olud"])
        return {"ok": ok}


def bind(window, api):
    def on_drop(e):
        files = e.get('dataTransfer', {}).get('files', [])
        paths = [f.get('pywebviewFullPath') for f in files if f.get('pywebviewFullPath')]
        if not paths:
            return

        if api.active_tab == "search":
            image_paths = [p for p in paths if Path(p).suffix.lower() in IMAGE_SEARCH_EXTS]
            if not image_paths:
                return
            result = api.load_search_preview(image_paths[0])
            window.evaluate_js(f'renderSearchPreview({json.dumps(result)})', lambda r: None)
        else:
            entries = api.get_info(paths)
            window.evaluate_js(f'appendInfoResults({json.dumps(entries)})', lambda r: None)

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
    margin: 0; padding: 0;
    background: #1a1a1e; color: #e8e8ea;
    font: 13px -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
    -webkit-user-select: none; user-select: none;
    height: 100vh; display: flex; flex-direction: column;
  }
  .tabbar { display: flex; border-bottom: 1px solid #2c2c33; flex-shrink: 0; }
  .tab {
    flex: 1; text-align: center; padding: 12px 8px; cursor: pointer;
    color: #9a9aa2; font-size: 13px; font-weight: 500;
    border-bottom: 2px solid transparent;
  }
  .tab.active { color: #f5f5f7; border-bottom-color: #5e9eff; }
  .panel { display: none; flex: 1; min-height: 0; flex-direction: column; gap: 10px; padding: 14px; }
  .panel.active { display: flex; }

  #dropzoneInfo, #dropzoneSearch {
    border: 2px dashed #45454c; border-radius: 10px;
    padding: 18px 12px; text-align: center; color: #9a9aa2;
    transition: border-color .15s, background .15s, color .15s;
    flex-shrink: 0;
  }
  .drag { border-color: #5e9eff !important; background: #202538; color: #cfe0ff !important; }
  .buttons { display: flex; gap: 8px; margin-top: 10px; justify-content: center; }
  button {
    background: #2c2c33; color: #e8e8ea; border: 1px solid #3d3d45;
    border-radius: 6px; padding: 6px 12px; font-size: 12px; cursor: pointer;
  }
  button:hover { background: #37373f; }
  button:active { background: #26262c; }
  button.primary { background: #3a6fd8; border-color: #3a6fd8; }
  button.primary:hover { background: #4a7ce0; }
  label.check {
    display: flex; align-items: center; gap: 6px; color: #9a9aa2; font-size: 12px;
    justify-content: center; margin-top: 10px;
  }

  #infoTotal {
    flex-shrink: 0; padding: 8px 12px; background: #202024; border-radius: 8px;
    display: none; align-items: baseline; gap: 8px;
  }
  #infoTotal.show { display: flex; }
  #infoTotal .label { color: #9a9aa2; font-size: 12px; }
  #infoTotal .value { color: #6fd88a; font-size: 18px; font-weight: 700; }
  #infoTotal .count { color: #9a9aa2; font-size: 12px; margin-left: auto; }

  #infoResults {
    flex: 1; overflow-y: auto; background: #202024; border-radius: 8px;
    padding: 4px 0; display: none;
  }
  #infoResults.show { display: block; }
  .card { padding: 10px 12px; border-bottom: 1px solid #29292f; }
  .card:last-child { border-bottom: none; }
  .card-head {
    display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 6px;
  }
  .card-head .name { font-weight: 600; color: #f5f5f7; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .card-head button { flex-shrink: 0; padding: 3px 8px; font-size: 11px; }
  .fields { display: grid; grid-template-columns: auto 1fr; gap: 2px 10px; font-size: 12px; }
  .fields .k { color: #75757e; }
  .fields .v { color: #c8c8cc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .row-actions { display: flex; gap: 10px; flex-shrink: 0; }
  .row-actions button { display: none; }

  #searchPreview { flex: 1; display: none; flex-direction: column; align-items: center; gap: 12px; overflow-y: auto; }
  #searchPreview.show { display: flex; }
  #searchPreview img { max-width: 100%; max-height: 260px; border-radius: 8px; }
  #searchFilename { color: #9a9aa2; font-size: 12px; }
  #searchStatus { color: #6fd88a; font-size: 12px; min-height: 16px; }
</style>
</head>
<body>
  <div class="tabbar">
    <div class="tab active" id="tabInfoBtn" onclick="switchTab('info')">Media Info</div>
    <div class="tab" id="tabSearchBtn" onclick="switchTab('search')">Reverse Image Search</div>
  </div>

  <div class="panel active" id="panelInfo">
    <div id="dropzoneInfo">
      Drop files or a folder here
      <div class="buttons">
        <button onclick="browseInfoFiles()">Browse Files</button>
        <button onclick="browseInfoFolder()">Browse Folder</button>
        <button onclick="exportCsv()">Export CSV</button>
        <button onclick="clearInfo()">Clear</button>
      </div>
      <label class="check"><input type="checkbox" id="subfolders" onchange="pywebview.api.set_include_subfolders(this.checked)"> Include subfolders</label>
    </div>
    <div id="infoTotal">
      <span class="label">Total Duration</span>
      <span class="value" id="infoTotalValue">0:00</span>
      <span class="count" id="infoTotalCount"></span>
    </div>
    <div id="infoResults"></div>
  </div>

  <div class="panel" id="panelSearch">
    <div id="dropzoneSearch">
      Drop an image here
      <div class="buttons">
        <button onclick="browseSearchImage()">Browse Image</button>
        <button onclick="clearSearch()">Clear</button>
      </div>
    </div>
    <div id="searchPreview">
      <img id="searchThumb" src="">
      <div id="searchFilename"></div>
      <button class="primary" onclick="runSearch()">Search on Google</button>
      <div id="searchStatus"></div>
    </div>
  </div>

<script>
  let infoRows = [];

  function switchTab(name) {
    document.getElementById('tabInfoBtn').classList.toggle('active', name === 'info');
    document.getElementById('tabSearchBtn').classList.toggle('active', name === 'search');
    document.getElementById('panelInfo').classList.toggle('active', name === 'info');
    document.getElementById('panelSearch').classList.toggle('active', name === 'search');
    pywebview.api.set_active_tab(name);
  }

  for (const id of ['dropzoneInfo', 'dropzoneSearch']) {
    const el = document.getElementById(id);
    ['dragenter', 'dragover'].forEach(evt => el.addEventListener(evt, e => { e.preventDefault(); el.classList.add('drag'); }));
    ['dragleave', 'drop'].forEach(evt => el.addEventListener(evt, e => { e.preventDefault(); el.classList.remove('drag'); }));
  }

  // ── Info tab ──
  async function browseInfoFiles() {
    const paths = await pywebview.api.browse_info_files();
    if (paths && paths.length) {
      const entries = await pywebview.api.get_info(paths);
      appendInfoResults(entries);
    }
  }

  async function browseInfoFolder() {
    const path = await pywebview.api.browse_info_folder();
    if (path) {
      const entries = await pywebview.api.get_info([path]);
      appendInfoResults(entries);
    }
  }

  function appendInfoResults(entries) {
    if (!entries || !entries.length) return;
    infoRows = entries.concat(infoRows);
    const list = document.getElementById('infoResults');
    list.innerHTML = infoRows.map(cardHtml).join('');
    list.classList.add('show');
    updateInfoTotal();
  }

  function formatDuration(seconds) {
    seconds = Math.round(seconds);
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    const mm = String(m).padStart(2, '0');
    const ss = String(s).padStart(2, '0');
    return h ? `${h}:${mm}:${ss}` : `${m}:${ss}`;
  }

  function updateInfoTotal() {
    const videos = infoRows.filter(f => f.durationSeconds != null);
    const total = document.getElementById('infoTotal');
    if (!videos.length) {
      total.classList.remove('show');
      return;
    }
    const totalSeconds = videos.reduce((sum, f) => sum + f.durationSeconds, 0);
    document.getElementById('infoTotalValue').textContent = formatDuration(totalSeconds);
    document.getElementById('infoTotalCount').textContent =
      videos.length + (videos.length === 1 ? ' video' : ' videos');
    total.classList.add('show');
  }

  function cardHtml(f) {
    const rows = [
      ['Parent', f.parentFolder], ['Extension', f.extension], ['Size', f.sizeMb + ' MB'],
      ['Created', f.dateCreated], ['Modified', f.dateModified],
    ];
    if (f.dimensions) rows.push(['Dimensions', f.dimensions], ['Resolution', f.resolution], ['Aspect', f.aspectRatio]);
    if (f.duration) rows.push(['Duration', f.duration]);
    if (f.fps) rows.push(['FPS', f.fps]);
    if (f.bitRate) rows.push(['Bit Rate', f.bitRate]);
    const fields = rows.map(([k, v]) => `<div class="k">${k}</div><div class="v">${escapeHtml(String(v))}</div>`).join('');
    return `<div class="card">
      <div class="card-head">
        <span class="name" title="${escapeHtml(f.fullPath)}">${escapeHtml(f.filename)}</span>
        <button onclick='pywebview.api.reveal(${JSON.stringify(f.fullPath)})'>Reveal</button>
      </div>
      <div class="fields">${fields}</div>
    </div>`;
  }

  function clearInfo() {
    infoRows = [];
    const list = document.getElementById('infoResults');
    list.innerHTML = '';
    list.classList.remove('show');
    document.getElementById('infoTotal').classList.remove('show');
  }

  async function exportCsv() {
    if (!infoRows.length) return;
    await pywebview.api.export_csv(infoRows);
  }

  // ── Search tab ──
  async function browseSearchImage() {
    const path = await pywebview.api.browse_search_image();
    if (path) {
      const result = await pywebview.api.load_search_preview(path);
      renderSearchPreview(result);
    }
  }

  function renderSearchPreview(result) {
    if (!result || !result.ok) return;
    document.getElementById('searchThumb').src = result.thumbnail;
    document.getElementById('searchFilename').textContent = result.filename;
    document.getElementById('searchStatus').textContent = '';
    document.getElementById('searchPreview').classList.add('show');
  }

  async function runSearch() {
    document.getElementById('searchStatus').textContent = 'Copying image and opening Google...';
    const result = await pywebview.api.do_reverse_search();
    document.getElementById('searchStatus').textContent = result.ok
      ? 'Image copied — paste with Cmd+V into the Google Lens search box.'
      : 'Could not copy the image to the clipboard.';
  }

  function clearSearch() {
    document.getElementById('searchThumb').src = '';
    document.getElementById('searchPreview').classList.remove('show');
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
    api = Api()
    window = webview.create_window(
        "Media Dashboard", html=HTML, js_api=api,
        width=560, height=720, resizable=True
    )
    webview.start(lambda: bind(window, api), debug=False)


if __name__ == "__main__":
    main()
