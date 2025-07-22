import os
import sys
import webbrowser
import time
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QMessageBox, QFileDialog
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Selenium not installed. Falling back to clipboard method.")

os.system('clear')
print()
print()
print("Reverse Image Search Activating...(press Ctrl+C to stop)")

class DropZone(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Reverse Image Search")
        self.setGeometry(50, 520, 375, 420)
        self.setAcceptDrops(True)
        
        self.label = QLabel("Click or drag image files here", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("border: 2px dashed #aaa; font-size: 16px; padding: 20px;")
        self.label.mousePressEvent = self.openFileDialog
        
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def openFileDialog(self, event):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image File",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if file_path:
            self.process_image(file_path)

    def process_image(self, file_path):
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            # Show preview
            self.label.setPixmap(pixmap.scaled(350, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
            # Prompt to proceed
            dialog = QMessageBox(self)
            dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
            dialog.setWindowTitle("Proceed with Search")
            dialog.setText("Proceed with reverse image search on Google Lens?")
            dialog.addButton("OK", QMessageBox.AcceptRole)
            dialog.addButton("Cancel", QMessageBox.RejectRole)
            
            if dialog.exec_() == QMessageBox.AcceptRole:
                self.perform_search(file_path, pixmap)
            else:
                self.label.setText("Search canceled. Click or drop another image.")
        else:
            self.label.setText("Invalid image file")

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                self.process_image(file_path)
            else:
                self.label.setText("Please drop an image file")

    def perform_search(self, file_path, pixmap):
        self.label.setText("Opening Google Lens in your default browser...")
        QApplication.processEvents()  # Update UI immediately
        
        # Copy image to clipboard first
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(pixmap)
        
        # Open Lens directly in default browser (Orion)
        webbrowser.open("https://lens.google.com/")
        
        # Show instructions
        info_dialog = QMessageBox(self)
        info_dialog.setWindowFlags(info_dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        info_dialog.setWindowTitle("Ready to Search")
        info_dialog.setText("Image copied to clipboard!\n\nIn Google Lens:\n1. Click the upload/paste area\n2. Paste with Cmd+V (Mac) or Ctrl+V (Windows)")
        info_dialog.setIcon(QMessageBox.Information)
        info_dialog.exec_()
        
        self.label.setText("Image in clipboard. Follow browser instructions.")

def main():
    app = QApplication(sys.argv)
    window = DropZone()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()