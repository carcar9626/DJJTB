import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QLabel, QListWidget, QTextEdit,
                             QFileDialog, QScrollArea, QSplitter, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont

class FileLoader(QThread):
    files_loaded = pyqtSignal(list)
    
    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        
    def run(self):
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif'}
        files = []
        if os.path.exists(self.folder_path):
            for file in os.listdir(self.folder_path):
                file_ext = Path(file).suffix.lower()
                if file_ext in image_extensions and not file.lower().endswith('.xmp'):
                    files.append(file)
        files.sort()
        self.files_loaded.emit(files)

class XMPViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_folder = ""
        self.txt_folder = ""
        self.xmp_folders = []
        self.image_files = []
        self.current_image_index = -1
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("XMP/TXT Comparison Viewer")
        self.setGeometry(100, 100, 1600, 1000)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Top buttons
        control_layout = QHBoxLayout()
        self.select_image_folder_btn = QPushButton("📁 Image")
        self.select_image_folder_btn.clicked.connect(self.select_image_folder)
        control_layout.addWidget(self.select_image_folder_btn)
        
        self.select_txt_folder_btn = QPushButton("📝 TXT")
        self.select_txt_folder_btn.clicked.connect(self.select_txt_folder)
        control_layout.addWidget(self.select_txt_folder_btn)
        
        self.select_xmp_folders_btn = QPushButton("⚙️ XMP")
        self.select_xmp_folders_btn.clicked.connect(self.select_xmp_folders)
        control_layout.addWidget(self.select_xmp_folders_btn)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.load_images)
        control_layout.addWidget(self.refresh_btn)
        control_layout.addStretch()
        main_layout.addLayout(control_layout)
        
        self.status_label = QLabel("Select folders: Image → TXT → XMP")
        self.status_label.setMaximumHeight(30)
        main_layout.addWidget(self.status_label)
        
        # Main content
        content_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(content_splitter, 10)
        
        # Left: vertical splitter (image preview + list)
        left_splitter = QSplitter(Qt.Vertical)
        content_splitter.addWidget(left_splitter)
        
        self.image_preview_widget = QWidget()
        self.image_preview_layout = QVBoxLayout(self.image_preview_widget)
        left_splitter.addWidget(self.image_preview_widget)
        
        self.image_list = QListWidget()
        self.image_list.itemClicked.connect(self.on_image_clicked)
        left_splitter.addWidget(self.image_list)
        
        # Right: metadata
        self.viewer_widget = QWidget()
        self.viewer_layout = None
        content_splitter.addWidget(self.viewer_widget)
        
        left_splitter.setSizes([400, 600])
        content_splitter.setSizes([200, 1400])
        
        self.init_image_preview()
        
    def init_image_preview(self):
        for i in reversed(range(self.image_preview_layout.count())):
            item = self.image_preview_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        self.image_title_label = QLabel("Image Preview")
        self.image_title_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.image_title_label.setAlignment(Qt.AlignCenter)
        self.image_preview_layout.addWidget(self.image_title_label)
        
        self.image_scroll_area = QScrollArea()
        self.image_label = QLabel("Select an image")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 2px dashed #aaa; color: #666;")
        self.image_scroll_area.setWidget(self.image_label)
        self.image_scroll_area.setWidgetResizable(True)
        self.image_preview_layout.addWidget(self.image_scroll_area)
        
    def select_image_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.image_folder = folder
            self.update_status()
            self.load_images()
    
    def select_txt_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select TXT Folder")
        if folder:
            self.txt_folder = folder
            self.update_status()
            if self.image_folder:
                self.load_images()
    
    def select_xmp_folders(self):
        folders = []
        while True:
            folder = QFileDialog.getExistingDirectory(
                self, f"Select XMP Folder #{len(folders) + 1} (Cancel when done)")
            if not folder:
                break
            folders.append(folder)
        if folders:
            self.xmp_folders = folders
            self.update_status()
            if self.image_folder:
                self.load_images()
    
    def update_status(self):
        parts = []
        if self.image_folder:
            parts.append(f"Images: {Path(self.image_folder).name}")
        if self.txt_folder:
            parts.append(f"TXT: {Path(self.txt_folder).name}")
        if self.xmp_folders:
            parts.append(f"XMP: {', '.join([Path(f).name for f in self.xmp_folders])}")
        self.status_label.setText(" | ".join(parts) if parts else "Select folders: Image → TXT → XMP")
    
    def load_images(self):
        if not self.image_folder:
            QMessageBox.warning(self, "Warning", "Please select an image folder first")
            return
        self.file_loader = FileLoader(self.image_folder)
        self.file_loader.files_loaded.connect(self.on_images_loaded)
        self.file_loader.start()
    
    def on_images_loaded(self, files):
        self.image_files = files
        self.current_image_index = -1
        self.image_list.clear()
        for file in files:
            self.image_list.addItem(file)
        if files:
            self.current_image_index = 0
            self.display_current_image()
            self.image_list.setCurrentRow(0)
    
    def on_image_clicked(self, item):
        if not item:
            return
        filename = item.text()
        try:
            index = self.image_files.index(filename)
            if index != self.current_image_index:
                self.current_image_index = index
                self.display_current_image()
        except ValueError:
            pass
    
    def keyPressEvent(self, event):
        if not self.image_files:
            return
        if event.key() == Qt.Key_Down:
            if self.current_image_index < len(self.image_files) - 1:
                self.current_image_index += 1
                self.image_list.setCurrentRow(self.current_image_index)
                self.display_current_image()
        elif event.key() == Qt.Key_Up:
            if self.current_image_index > 0:
                self.current_image_index -= 1
                self.image_list.setCurrentRow(self.current_image_index)
                self.display_current_image()
    
    def display_current_image(self):
        if not self.image_files or self.current_image_index < 0:
            return
        current_file = self.image_files[self.current_image_index]
        self.update_image_preview(current_file)
        
        if self.viewer_layout:
            self.clear_layout(self.viewer_layout)
            self.viewer_layout.deleteLater()
        self.viewer_layout = QHBoxLayout()
        self.viewer_widget.setLayout(self.viewer_layout)
        
        panels_created = 0
        if self.txt_folder:
            self.viewer_layout.addWidget(self.create_txt_panel(current_file))
            panels_created += 1
        for i, xmp_folder in enumerate(self.xmp_folders):
            self.viewer_layout.addWidget(self.create_xmp_panel(current_file, xmp_folder, i + 1))
            panels_created += 1
        if panels_created == 0:
            msg_label = QLabel("Select TXT and/or XMP folders to view metadata")
            msg_label.setAlignment(Qt.AlignCenter)
            self.viewer_layout.addWidget(msg_label)
    
    def update_image_preview(self, filename):
        image_path = os.path.join(self.image_folder, filename)
        self.image_title_label.setText(filename)
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            w = self.image_scroll_area.width() - 20
            h = self.image_scroll_area.height() - 20
            scaled_pixmap = pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setStyleSheet("")
        else:
            self.image_label.setText("Failed to load image")
            self.image_label.setStyleSheet("border: 2px dashed red; color: red;")
    
    def create_txt_panel(self, filename):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        title = QLabel("📝 TXT (JoyTag Output)")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("background-color: #2d2d2d; color: white; padding: 8px; border-radius: 4px;")
        layout.addWidget(title)
        text_edit = QTextEdit()
        text_edit.setPlainText(self.load_txt_content(filename))
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Consolas", 10))
        layout.addWidget(text_edit)
        return panel
    
    def create_xmp_panel(self, filename, xmp_folder, panel_number):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        folder_name = Path(xmp_folder).name
        title = QLabel(f"⚙️ XMP {panel_number}: {folder_name}")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("background-color: #2d2d2d; color: white; padding: 8px; border-radius: 4px;")
        layout.addWidget(title)
        text_edit = QTextEdit()
        text_edit.setPlainText(self.load_xmp_content(filename, xmp_folder))
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Consolas", 10))
        layout.addWidget(text_edit)
        return panel
    
    def load_txt_content(self, image_filename):
        if not self.txt_folder:
            return "No TXT folder selected"
        base_name = Path(image_filename).stem
        txt_patterns = [f"{base_name}.txt", f"{image_filename}.txt", f"{base_name}.TXT"]
        for pattern in txt_patterns:
            txt_path = os.path.join(self.txt_folder, pattern)
            if os.path.exists(txt_path):
                try:
                    with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().strip()
                    if content:
                        lines = content.split('\n')
                        formatted_lines = []
                        for line in lines:
                            line = line.strip()
                            if line and ':' in line:
                                parts = line.split(':', 1)
                                if len(parts) == 2:
                                    tag = parts[0].strip()
                                    conf = parts[1].strip()
                                    formatted_lines.append(f"{tag:<30} {conf}")
                                else:
                                    formatted_lines.append(line)
                            elif line:
                                formatted_lines.append(line)
                        return '\n'.join(formatted_lines) if formatted_lines else content
                    else:
                        return "TXT file is empty"
                except Exception as e:
                    return f"Error reading TXT file: {str(e)}"
        return f"No TXT file found for {image_filename}"
    
    def load_xmp_content(self, image_filename, xmp_folder):
        base_name = Path(image_filename).stem
        xmp_patterns = [f"{image_filename}.xmp", f"{base_name}.xmp", f"{image_filename}.XMP", f"{base_name}.XMP"]
        for pattern in xmp_patterns:
            xmp_path = os.path.join(xmp_folder, pattern)
            if os.path.exists(xmp_path):
                try:
                    with open(xmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    try:
                        import xml.dom.minidom as minidom
                        dom = minidom.parseString(content)
                        return dom.toprettyxml(indent="  ")
                    except:
                        return content
                except Exception as e:
                    return f"Error reading XMP file: {str(e)}"
        return f"No XMP file found for {image_filename}"
    
    def clear_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())

def main():
    app = QApplication(sys.argv)
    viewer = XMPViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()