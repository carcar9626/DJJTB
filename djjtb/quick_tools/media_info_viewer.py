import os
import sys
import csv
import mimetypes
import datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QMessageBox,
    QFileDialog, QPushButton, QTextBrowser, QHBoxLayout, QInputDialog
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QPalette

from PIL import Image
import cv2

os.system('clear')
print()
print()
print("Media Info Viewer running...(press Ctrl+C to stop)")

class DropZone(QWidget):
    def __init__(self):
        super().__init__()
        self.file_info_list = []
        self.include_subfolders = False
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Media Info Inspector")
        self.setGeometry(50, 80, 375, 470)  # Made slightly taller for new button
        self.setAcceptDrops(True)
        
        # Enable keyboard shortcuts
        self.setFocusPolicy(Qt.StrongFocus)

        # Main layout
        layout = QVBoxLayout()

        # Drop/click area
        self.label = QLabel("Click, drag, or use buttons below", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFixedHeight(120)
        self.label.setStyleSheet("border: 2px dashed #aaa; font-size: 16px; padding: 12px;")
        self.label.mousePressEvent = self.openFileDialog
        layout.addWidget(self.label)

        # Buttons layout (top row)
        button_layout = QHBoxLayout()
        
        # Paste file path button
        self.paste_btn = QPushButton("Paste File Path", self)
        self.paste_btn.clicked.connect(self.paste_file_path)
        self.paste_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(self.paste_btn)
        
        # Browse files button
        self.browse_btn = QPushButton("Browse Files", self)
        self.browse_btn.clicked.connect(lambda: self.openFileDialog(None))
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        button_layout.addWidget(self.browse_btn)
        
        # Refresh button
        self.refresh_btn = QPushButton("Clear All", self)
        self.refresh_btn.clicked.connect(self.refresh_display)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        button_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(button_layout)

        # Text area
        self.text_area = QTextBrowser(self)
        self.text_area.setReadOnly(True)
        self.text_area.setOpenExternalLinks(False)
        self.text_area.viewport().setCursor(Qt.PointingHandCursor)
        self.text_area.mouseReleaseEvent = self.handleLinkClick
        layout.addWidget(self.text_area)

        # Export button
        self.export_button = QPushButton("Export to CSV", self)
        self.export_button.clicked.connect(self.exportToCSV)

        palette = self.export_button.palette()
        accent_color = palette.color(QPalette.Highlight)
        self.export_button.setStyleSheet(f"background-color: {accent_color.name()}; color: white; padding: 6px;")
        layout.addWidget(self.export_button)

        self.setLayout(layout)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
            # Ctrl+V (Cmd+V on Mac) - opens paste file path dialog
            self.paste_file_path()
        else:
            super().keyPressEvent(event)

    def paste_file_path(self):
        """Allow user to paste or type file/folder paths (supports multiple paths)"""
        # Get clipboard text as default value
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text().strip()
        
        # Show input dialog with clipboard content as default
        input_text, ok = QInputDialog.getText(
            self,
            'File/Folder Paths',
            'Paste or enter file/folder paths:\n(Multiple paths: space-separated like Finder, or newlines)',
            text=clipboard_text
        )
        
        if ok and input_text:
            # Parse multiple paths - handle Finder's space-separated format and other formats
            raw_paths = []
            
            # First try to split by newlines (manual entry)
            if '\n' in input_text:
                lines = input_text.strip().split('\n')
                for line in lines:
                    if ';' in line:
                        # Handle semicolon separation within lines
                        raw_paths.extend(line.split(';'))
                    else:
                        raw_paths.append(line)
            else:
                # Handle space-separated paths (Finder format)
                # This is tricky because paths can contain spaces, but we'll use quotes as indicators
                import shlex
                try:
                    # Use shlex to properly parse quoted paths
                    raw_paths = shlex.split(input_text)
                except ValueError:
                    # If shlex fails, fall back to simple space split
                    # and hope paths don't have spaces or are quoted
                    raw_paths = input_text.split()
            
            # Clean up each path
            cleaned_paths = []
            for path in raw_paths:
                cleaned = path.strip().strip('"\'')  # Remove quotes and whitespace
                if cleaned:  # Only add non-empty paths
                    cleaned_paths.append(cleaned)
            
            if not cleaned_paths:
                QMessageBox.warning(self, "No Paths", "No valid paths found in input.")
                return
            
            # Check which paths exist and separate files from folders
            valid_paths = []
            invalid_paths = []
            has_folders = False
            
            for path_str in cleaned_paths:
                path_obj = Path(path_str)
                if path_obj.exists():
                    valid_paths.append(path_obj)
                    if path_obj.is_dir():
                        has_folders = True
                else:
                    invalid_paths.append(path_str)
            
            # Warn about invalid paths but continue with valid ones
            if invalid_paths:
                invalid_list = '\n'.join(invalid_paths[:5])  # Show max 5 invalid paths
                if len(invalid_paths) > 5:
                    invalid_list += f'\n... and {len(invalid_paths)-5} more'
                
                reply = QMessageBox.question(
                    self, "Some Paths Invalid",
                    f"Found {len(invalid_paths)} invalid path(s):\n\n{invalid_list}\n\n"
                    f"Continue with {len(valid_paths)} valid path(s)?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply != QMessageBox.Yes:
                    return
            
            if not valid_paths:
                QMessageBox.warning(self, "No Valid Paths", "No valid paths found.")
                return
            
            # Ask about subfolders if any folders are present
            if has_folders:
                reply = QMessageBox.question(
                    self, 'Include Subfolders?',
                    f'Found {sum(1 for p in valid_paths if p.is_dir())} folder(s).\n'
                    'Include files from subfolders?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                self.include_subfolders = (reply == QMessageBox.Yes)
            
            # Process all valid paths
            new_batch = []
            for path_obj in valid_paths:
                new_batch.extend(self.collectPaths(path_obj))
            
            if new_batch:
                self.processBatch(new_batch)
                # Show summary
                file_count = len(new_batch)
                folder_count = sum(1 for p in valid_paths if p.is_dir())
                single_file_count = len(valid_paths) - folder_count
                
                summary_parts = []
                if single_file_count > 0:
                    summary_parts.append(f"{single_file_count} file(s)")
                if folder_count > 0:
                    summary_parts.append(f"{folder_count} folder(s)")
                
                summary = f"Processed {' and '.join(summary_parts)}, found {file_count} total files."
                
                # Update the label temporarily to show summary
                original_text = self.label.text()
                self.label.setText(f"✓ {summary}")
                # Reset after 3 seconds
                QApplication.processEvents()
                import threading
                threading.Timer(3.0, lambda: self.label.setText(original_text)).start()
            else:
                QMessageBox.information(self, "No Media Files",
                                      "No media files found in the specified paths.")

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
        """Open file dialog - now works as both click handler and direct call"""
        # Use getOpenFileNames to allow multiple file selection
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Multiple Files")
        if not paths:
            # If no files selected, try folder selection
            folder = QFileDialog.getExistingDirectory(self, "Or Select a Folder")
            if folder:
                paths = [folder]
        
        if not paths:
            return
            
        # Check if any folders are selected and ask about subfolders
        path_objects = [Path(p) for p in paths]
        if any(p.is_dir() for p in path_objects):
            reply = QMessageBox.question(
                self, 'Include Subfolders?', 'Include files from subfolders?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            self.include_subfolders = (reply == QMessageBox.Yes)

        new_batch = []
        for path in path_objects:
            new_batch.extend(self.collectPaths(path))
        
        if new_batch:
            self.processBatch(new_batch)
        else:
            QMessageBox.information(self, "No Media Files",
                                  "No media files found in the selected paths.")

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

    def refresh_display(self):
        """Clear all displayed info and reset the list"""
        reply = QMessageBox.question(
            self, 'Clear All Data?',
            'This will clear all displayed file information.\nAre you sure?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.file_info_list.clear()
            self.text_area.clear()
            self.label.setText("Click, drag, or use buttons below")

    def prependDisplay(self, new_entries):
        html_blocks = []
    
        for i, f in enumerate(reversed(new_entries)):
            file_link = f'<a href="file://{f["Full Path"]}">{f["Filename"]}</a>'
            parent_path = str(Path(f["Full Path"]).parent)
            parent_link = f'<a href="file://{parent_path}">{f["Parent Folder"]}</a>'
    
            block = []
    
            # Divider between individual files (lighter separator)
            if i != 0:
                block.append('<hr style="border: none; height: 1px; background: #ddd; margin: 15px 0;">')
    
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
        
        # Get existing content
        current_html = self.text_area.toHtml()
        
        # Add batch separator BETWEEN new and old content if there's existing content
        if current_html.strip() and '<b>Filename:</b>' in current_html:
            batch_separator = ('<div style="margin: 20px 0; text-align: center;">'
                             '<hr style="border: none; height: 3px; background: linear-gradient(to right, #ff4444, #ff6666, #ff4444); margin: 10px 0;">'
                             '<div style="color: #ff4444; font-weight: bold; font-size: 14px; margin: 8px 0;">NEW BATCH</div>'
                             '<hr style="border: none; height: 3px; background: linear-gradient(to right, #ff4444, #ff6666, #ff4444); margin: 10px 0;">'
                             '</div>')
            # New content + separator + old content
            self.text_area.setHtml(''.join(html_blocks) + batch_separator + current_html)
        else:
            # No existing content, just show new content
            self.text_area.setHtml(''.join(html_blocks))

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