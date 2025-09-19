i have a small xmp viewer, let's me compare multiple versions of xmp side by side with image using pyqt5. i need to make some changes and debug a little. currently at the beginning when i scroll through the "image list" from the first image it only reads every other image, odd, if i click further away to an even image it will show then i can click back to the original even image i wanted to check, first i thought it had something to do with the number of xmp files i open, i usually open just two, so the panes are "folder|image|xmp1|xmp2" but i tried with one xmp and 3 xmps, still the same, every other one. please see if you can fix that. i understand limitations vs unnecessary codes tradeoff for simple gui like this, so this is actually not a priority.

here's the main course, i have a script using joytag model to batch tag images, and it would also generate a txt file with each just listing tags and confidence levels in %, so i want to add txt files to this as well, problem is they will be in the same folder beside the image along with the xmp, please look into that.

also now the image rarely fills the entire pane, let's move the image preview pane to the top of the file list pane, best if it can also be adjustable in size vertically like it does now between the horizontal panes.












import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QLabel, QListWidget, QTextEdit,
                             QFileDialog, QScrollArea, QSplitter, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont
import xml.etree.ElementTree as ET
from xml.parsers.expat import ExpatError

class FileLoader(QThread):
    """Thread for loading files to avoid UI freezing"""
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
                # Skip XMP files and only include image files
                if file_ext in image_extensions and not file.lower().endswith('.xmp'):
                    files.append(file)
        
        files.sort()
        self.files_loaded.emit(files)

class XMPViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_folder = ""
        self.xmp_folders = []
        self.image_files = []
        self.current_image_index = 0
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("XMP Comparison Viewer")
        self.setGeometry(100, 100, 1400, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.select_image_folder_btn = QPushButton("Select Image Folder")
        self.select_image_folder_btn.clicked.connect(self.select_image_folder)
        control_layout.addWidget(self.select_image_folder_btn)
        
        self.select_xmp_folders_btn = QPushButton("Select XMP Folders")
        self.select_xmp_folders_btn.clicked.connect(self.select_xmp_folders)
        control_layout.addWidget(self.select_xmp_folders_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_images)
        control_layout.addWidget(self.refresh_btn)
        
        control_layout.addStretch()
        main_layout.addLayout(control_layout)
        
        # Status label (compact)
        self.status_label = QLabel("Select folders to begin")
        self.status_label.setMaximumHeight(30)  # limit height
        main_layout.addWidget(self.status_label)
        
        # Main content area (give it ALL the remaining vertical space)
        content_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(content_splitter, 10)  # high stretch factor to grab all remaining space
        
        # Left panel - Image list
        self.image_list = QListWidget()
        self.image_list.currentRowChanged.connect(self.on_image_selected)
        self.image_list.setMaximumWidth(250)
        content_splitter.addWidget(self.image_list)
        
        # Right panel - Image and XMP viewers (initially empty)
        self.viewer_widget = QWidget()
        self.viewer_layout = None  # Will be created when needed
        content_splitter.addWidget(self.viewer_widget)
        
        # Set splitter proportions - give more space to the viewer
        content_splitter.setSizes([200, 1200])
        
    def select_image_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.image_folder = folder
            self.status_label.setText(f"Image folder: {folder}")
            print(f"DEBUG: Selected image folder: {folder}")
            self.load_images()
    
    def select_xmp_folders(self):
        folders = []
        while True:
            folder = QFileDialog.getExistingDirectory(
                self, f"Select XMP Folder #{len(folders) + 1} (Cancel when done)")
            if not folder:
                break
            folders.append(folder)
            print(f"DEBUG: Added XMP folder: {folder}")
        
        if folders:
            self.xmp_folders = folders
            folder_names = [Path(f).name for f in folders]
            self.status_label.setText(f"XMP folders: {', '.join(folder_names)}")
            print(f"DEBUG: Total XMP folders: {len(folders)}")
            if self.image_folder:
                self.load_images()
        else:
            print("DEBUG: No XMP folders selected")
    
    def load_images(self):
        if not self.image_folder:
            QMessageBox.warning(self, "Warning", "Please select an image folder first")
            return
            
        print("DEBUG: Starting to load images...")
        self.file_loader = FileLoader(self.image_folder)
        self.file_loader.files_loaded.connect(self.on_images_loaded)
        self.file_loader.start()
        
        self.status_label.setText("Loading images...")
    
    def on_images_loaded(self, files):
        self.image_files = files
        self.image_list.clear()
        
        print(f"DEBUG: Loaded {len(files)} image files")
        for file in files:
            self.image_list.addItem(file)
            print(f"DEBUG: Added image: {file}")
        
        if files:
            self.image_list.setCurrentRow(0)
            self.status_label.setText(f"Loaded {len(files)} images")
        else:
            self.status_label.setText("No images found in selected folder")
    
    def on_image_selected(self, index):
        print(f"DEBUG: Image selected at index: {index}")
        if index >= 0 and index < len(self.image_files):
            self.current_image_index = index
            current_file = self.image_files[index]
            print(f"DEBUG: Displaying image: {current_file}")
            self.display_current_image()
    
    def display_current_image(self):
        if not self.image_files:
            print("DEBUG: No image files to display")
            return
            
        current_file = self.image_files[self.current_image_index]
        print(f"DEBUG: Creating display for: {current_file}")
        print(f"DEBUG: Number of XMP folders: {len(self.xmp_folders)}")
        
        # Clear and recreate the viewer widget completely
        if self.viewer_layout:
            self.clear_layout(self.viewer_layout)
            self.viewer_layout.deleteLater()
        
        self.viewer_layout = QHBoxLayout()
        self.viewer_widget.setLayout(self.viewer_layout)
        
        # Calculate number of panels needed
        num_panels = 1 + len(self.xmp_folders)  # 1 for image + N for XMP folders
        print(f"DEBUG: Creating {num_panels} panels")
        
        # Create splitter for dynamic panels
        splitter = QSplitter(Qt.Horizontal)
        self.viewer_layout.addWidget(splitter)
        
        # Image panel
        print("DEBUG: Creating image panel...")
        image_panel = self.create_image_panel(current_file)
        splitter.addWidget(image_panel)
        
        # XMP panels
        for i, xmp_folder in enumerate(self.xmp_folders):
            print(f"DEBUG: Creating XMP panel {i+1} for folder: {xmp_folder}")
            xmp_panel = self.create_xmp_panel(current_file, xmp_folder, i + 1)
            splitter.addWidget(xmp_panel)
        
        # Set equal sizes for all panels
        if num_panels > 1:
            sizes = [400] * num_panels
            splitter.setSizes(sizes)
        
        print("DEBUG: Display update complete")
    
    def create_image_panel(self, filename):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("Image")
        title.setFont(QFont("Menlo", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Filename
        file_label = QLabel(filename)
        file_label.setAlignment(Qt.AlignCenter)
        file_label.setStyleSheet("color: yellow; font-weight: bold;")
        layout.addWidget(file_label)
        
        # Image display
        scroll_area = QScrollArea()
        image_label = QLabel()
        
        image_path = os.path.join(self.image_folder, filename)
        print(f"DEBUG: Loading image from: {image_path}")
        pixmap = QPixmap(image_path)
        
        if not pixmap.isNull():
            # Scale image to fit while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(350, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label.setPixmap(scaled_pixmap)
            print("DEBUG: Image loaded successfully")
        else:
            image_label.setText("Failed to load image")
            print("DEBUG: Failed to load image")
            
        image_label.setAlignment(Qt.AlignCenter)
        scroll_area.setWidget(image_label)
        layout.addWidget(scroll_area)
        
        return panel
    
    def create_xmp_panel(self, filename, xmp_folder, panel_number):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Title
        folder_name = Path(xmp_folder).name
        title = QLabel(f"XMP {panel_number}: {folder_name}")
        title.setFont(QFont("Menlo", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # XMP content
        print(f"DEBUG: Loading XMP for {filename} from {xmp_folder}")
        xmp_content = self.load_xmp_content(filename, xmp_folder)
        
        text_edit = QTextEdit()
        text_edit.setPlainText(xmp_content)
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Menlo", 15))
        layout.addWidget(text_edit)
        
        return panel
    
    def load_xmp_content(self, image_filename, xmp_folder):
        print(f"DEBUG: Looking for XMP file for {image_filename} in {xmp_folder}")
        
        # Try multiple XMP file patterns - based on your file structure
        base_name = Path(image_filename).stem
        xmp_patterns = [
            f"{image_filename}.xmp",        # filename.jpg.xmp (your pattern)
            f"{image_filename}.XMP",        # filename.jpg.XMP
            f"{base_name}.xmp",             # basename.xmp
            f"{base_name}.XMP",             # basename.XMP
        ]
        
        xmp_path = None
        for pattern in xmp_patterns:
            potential_path = os.path.join(xmp_folder, pattern)
            print(f"DEBUG: Checking for: {potential_path}")
            if os.path.exists(potential_path):
                xmp_path = potential_path
                print(f"DEBUG: Found XMP file: {xmp_path}")
                break
        
        if not xmp_path:
            # List what files ARE in the XMP folder for debugging
            try:
                actual_files = os.listdir(xmp_folder)
                xmp_files = [f for f in actual_files if f.lower().endswith('.xmp')]
                error_msg = f"XMP file not found for {image_filename}\n\nLooked for:\n"
                for pattern in xmp_patterns:
                    error_msg += f"- {pattern}\n"
                error_msg += f"\nActual XMP files in {Path(xmp_folder).name}:\n"
                for xmp_file in xmp_files[:10]:  # Show first 10 files
                    error_msg += f"- {xmp_file}\n"
                if len(xmp_files) > 10:
                    error_msg += f"... and {len(xmp_files) - 10} more\n"
                print(f"DEBUG: XMP not found. Actual XMP files: {xmp_files[:5]}")
                return error_msg
            except Exception as e:
                return f"Error listing XMP folder contents: {str(e)}"
        
        try:
            # Try to read as text first
            with open(xmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            print(f"DEBUG: Successfully read XMP file, length: {len(content)}")
            
            # Try to parse as XML for prettier formatting
            try:
                root = ET.fromstring(content)
                # If successful, return formatted XML
                return self.format_xml_content(content)
            except (ET.ParseError, ExpatError):
                # If XML parsing fails, return raw content
                return f"Raw XMP content (not valid XML):\n\n{content}"
                
        except Exception as e:
            print(f"DEBUG: Error reading XMP file: {str(e)}")
            return f"Error reading XMP file: {str(e)}"
    
    def format_xml_content(self, xml_content):
        """Format XML content for better readability"""
        try:
            import xml.dom.minidom as minidom
            dom = minidom.parseString(xml_content)
            return dom.toprettyxml(indent="  ")
        except:
            return xml_content
    
    def clear_layout(self, layout):
        """Recursively clear a layout"""
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