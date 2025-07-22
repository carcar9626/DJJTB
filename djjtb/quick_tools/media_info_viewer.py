import os
import sys
import csv
import mimetypes
import datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QMessageBox,
    QFileDialog, QPushButton, QTextBrowser
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QPalette

from PIL import Image
import cv2
os.system('clear')
print ()
print ()
print ("Media Info Viewer running...(press Ctrl+C to stop)")
class DropZone(QWidget):
    def __init__(self):
        super().__init__()
        self.file_info_list = []
        self.include_subfolders = False
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Media Info Inspector")
        self.setGeometry(50, 80, 375, 420)
        self.setAcceptDrops(True)

        self.label = QLabel("Click or drag files/folders here", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFixedHeight(120)
        self.label.setStyleSheet("border: 2px dashed #aaa; font-size: 16px; padding: 12px;")
        self.label.mousePressEvent = self.openFileDialog

        self.text_area = QTextBrowser(self)
        self.text_area.setReadOnly(True)
        self.text_area.setOpenExternalLinks(False)
        self.text_area.viewport().setCursor(Qt.PointingHandCursor)
        self.text_area.mouseReleaseEvent = self.handleLinkClick

        self.export_button = QPushButton("Export to CSV", self)
        self.export_button.clicked.connect(self.exportToCSV)

        palette = self.export_button.palette()
        accent_color = palette.color(QPalette.Highlight)
        self.export_button.setStyleSheet(f"background-color: {accent_color.name()}; color: white; padding: 6px;")

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.text_area)
        layout.addWidget(self.export_button)
        self.setLayout(layout)

    def handleLinkClick(self, event):
        cursor = self.text_area.cursorForPosition(event.pos())
        url = cursor.charFormat().anchorHref()
        if url:
            qurl = QUrl(url)
            self.openLink(qurl)
        else:
            super(QTextBrowser, self.text_area).mouseReleaseEvent(event)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        self.handleUrls(event.mimeData().urls())

    def openFileDialog(self, event):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Files or Folders")
        if not paths:
            return
        if any(Path(p).is_dir() for p in paths):
            reply = QMessageBox.question(
                self, 'Include Subfolders?', 'Include files from subfolders?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            self.include_subfolders = (reply == QMessageBox.Yes)

        new_batch = []
        for path in paths:
            new_batch.extend(self.collectPaths(Path(path)))
        self.processBatch(new_batch)

    def handleUrls(self, urls):
        if any(Path(url.toLocalFile()).is_dir() for url in urls):
            reply = QMessageBox.question(
                self, 'Include Subfolders?', 'Include files from subfolders?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            self.include_subfolders = (reply == QMessageBox.Yes)

        new_batch = []
        for url in urls:
            new_batch.extend(self.collectPaths(Path(url.toLocalFile())))
        self.processBatch(new_batch)

    def collectPaths(self, path: Path):
        if path.is_file():
            return [path]
        elif path.is_dir():
            files = path.rglob("*") if self.include_subfolders else path.glob("*")
            return [f for f in files if f.is_file()]
        return []

    def processBatch(self, paths):
        new_entries = []
        for path in paths:
            info = self.extractInfo(path)
            if info:
                self.file_info_list.append(info)
                new_entries.append(info)
        if new_entries:
            self.prependDisplay(new_entries)

    def extractInfo(self, file_path: Path):
        try:
            file_info = {
                "Filename": file_path.name,
                "Parent Folder": file_path.parent.name,
                "Full Path": str(file_path),
                "Extension": file_path.suffix.lower(),
                "Size (MB)": f"{file_path.stat().st_size / (1024*1024):.2f}",
                "Date Created": datetime.datetime.fromtimestamp(file_path.stat().st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                "Date Modified": datetime.datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                "Dimensions": "",
                "Resolution": "",
                "Aspect Ratio": "",
                "Duration": ""
            }

            mime, _ = mimetypes.guess_type(file_path)
            if mime:
                if mime.startswith("image"):
                    img = Image.open(file_path)
                    w, h = img.size
                    file_info["Dimensions"] = f"{w}x{h}"
                    file_info["Aspect Ratio"] = f"{w}:{h} ({w/h:.2f})"
                    file_info["Resolution"] = self.classify_resolution(h)
                elif mime.startswith("video"):
                    cap = cv2.VideoCapture(str(file_path))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    duration = frames / fps if fps else 0
                    file_info["Duration"] = f"{duration:.2f}s"
                    file_info["Dimensions"] = f"{width}x{height}"
                    file_info["Aspect Ratio"] = f"{width}:{height} ({width/height:.2f})"
                    file_info["Resolution"] = self.classify_resolution(height)
                    cap.release()
            return file_info
        except:
            return None

    def classify_resolution(self, height):
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
        else:
            return f"{height}p"

    def prependDisplay(self, new_entries):
        html_blocks = []
    
        for i, f in enumerate(reversed(new_entries)):
            file_link = f'<a href="file://{f["Full Path"]}">{f["Filename"]}</a>'
            parent_path = str(Path(f["Full Path"]).parent)
            parent_link = f'<a href="file://{parent_path}">{f["Parent Folder"]}</a>'
    
            block = []
    
            # Divider on all but first
            if i != 0:
                block.append("<hr>")
    
            # Main display block with bolded keys
            block.append(f"<b>Filename:</b> {file_link}<br>")
            block.append(f"<b>Parent Folder:</b> {parent_link}<br>")
            block.append(f"<b>Full Path:</b> {f['Full Path']}<br>")
            block.append(f"<b>Extension:</b> {f['Extension']}<br>")
            block.append(f"<b>Size (MB):</b> {f['Size (MB)']}<br>")
            block.append(f"<b>Date Created:</b> {f['Date Created']}<br>")
            block.append(f"<b>Date Modified:</b> {f['Date Modified']}<br>")
            block.append(f"<b>Dimensions:</b> {f['Dimensions']}<br>")
            block.append(f"<b>Resolution:</b> {f['Resolution']}<br>")
            block.append(f"<b>Aspect Ratio:</b> {f['Aspect Ratio']}<br>")
            block.append(f"<b>Duration:</b> {f['Duration']}<br>")
    
            html_blocks.append(''.join(block))
    
        current_html = self.text_area.toHtml()
        self.text_area.setHtml(''.join(html_blocks) + current_html)

    def openLink(self, url: QUrl):
        path = url.toLocalFile()
        if Path(path).exists():
            os.system(f'open -R "{path}"')
        else:
            QMessageBox.warning(self, "Not Found", f"Path does not exist:\n{path}")

    def exportToCSV(self):
        if not self.file_info_list:
            QMessageBox.warning(self, "No Data", "No file info to export.")
            return
    
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", os.path.expanduser("~/media_info.csv"), "CSV Files (*.csv)"
        )
        if save_path:
            keys = list(self.file_info_list[0].keys())
            with open(save_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(self.file_info_list)
    
            msg = QMessageBox(self)
            msg.setWindowTitle("Saved")
            msg.setText(f"CSV exported to:\n{save_path}")
            msg.setIcon(QMessageBox.Information)
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Open)
            msg.setDefaultButton(QMessageBox.Ok)
    
            result = msg.exec_()
            if result == QMessageBox.Open:
                folder_path = str(Path(save_path).parent)
                os.system(f'open "{folder_path}"')

def main():
    app = QApplication(sys.argv)
    window = DropZone()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()