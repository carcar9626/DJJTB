import os
import sys
import webbrowser
import time
import tempfile
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QMessageBox, QFileDialog, QPushButton, QHBoxLayout
from PyQt5.QtGui import QPixmap, QClipboard
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
        self.setGeometry(50, 520, 375, 470)  # Made slightly taller for new button
        self.setAcceptDrops(True)
        
        # Main layout
        layout = QVBoxLayout()
        
        # Drop/click area
        self.label = QLabel("Click, drag, or use buttons below", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("border: 2px dashed #aaa; font-size: 16px; padding: 20px;")
        self.label.mousePressEvent = self.openFileDialog
        layout.addWidget(self.label)
        
        # Buttons layout
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
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Enable keyboard shortcuts
        self.setFocusPolicy(Qt.StrongFocus)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
            # Ctrl+V (Cmd+V on Mac)
            self.paste_from_clipboard()
        else:
            super().keyPressEvent(event)

    def paste_from_clipboard(self):
        """Get image from clipboard and process it"""
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        print("DEBUG: Clipboard formats available:", mime_data.formats())  # Debug line
        
        # First, check if clipboard has actual image data
        if mime_data.hasImage():
            pixmap = clipboard.pixmap()
            if not pixmap.isNull():
                print("DEBUG: Found image data in clipboard")
                # Save the clipboard image to a temporary file for processing
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_path = temp_file.name
                temp_file.close()
                
                # Save pixmap to temp file
                pixmap.save(temp_path, 'PNG')
                
                # Process the image
                self.process_image_from_clipboard(temp_path, pixmap)
                return
        
        # Try to get file URLs from clipboard (main way Finder copies files)
        if mime_data.hasUrls():
            urls = mime_data.urls()
            print(f"DEBUG: Found URLs in clipboard: {[url.toString() for url in urls]}")
            if urls:
                file_path = urls[0].toLocalFile()
                print(f"DEBUG: Local file path: {file_path}")
                if file_path and os.path.exists(file_path) and file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                    # Load the actual image file
                    pixmap = QPixmap(file_path)
                    if not pixmap.isNull():
                        print(f"DEBUG: Successfully loaded image from: {file_path}")
                        self.process_image_from_clipboard(file_path, pixmap)
                        return
                    else:
                        print(f"DEBUG: Failed to load pixmap from: {file_path}")
        
        # Check if clipboard has file paths as text (backup method)
        if mime_data.hasText():
            clipboard_text = clipboard.text().strip()
            print(f"DEBUG: Clipboard text: {clipboard_text}")
            if clipboard_text and os.path.exists(clipboard_text):
                if clipboard_text.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                    # Load the actual image file (not just the path)
                    pixmap = QPixmap(clipboard_text)
                    if not pixmap.isNull():
                        print(f"DEBUG: Successfully loaded image from text path: {clipboard_text}")
                        self.process_image_from_clipboard(clipboard_text, pixmap)
                        return
        
        # No valid image found
        print("DEBUG: No valid image found in clipboard")
        QMessageBox.warning(self, "No Image",
                          "No image found in clipboard.\n\n"
                          "Try copying an image first:\n"
                          "• Right-click image in browser → Copy Image\n"
                          "• Or copy image file from Finder (Cmd+C)")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def openFileDialog(self, event):
        """Open file dialog - now works as both click handler and direct call"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image File",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if file_path:
            self.process_image(file_path)

    def process_image(self, file_path):
        """Process image from file path"""
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
                self.label.setText("Search canceled. Click, drag, or paste another image.")
        else:
            self.label.setText("Invalid image file")

    def paste_file_path(self):
        """Allow user to paste or type a file path"""
        from PyQt5.QtWidgets import QInputDialog
        
        # Get clipboard text as default value
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text().strip().strip('"\'')  # Remove quotes if present
        
        # Show input dialog with clipboard content as default
        file_path, ok = QInputDialog.getText(
            self,
            'File Path',
            'Paste or enter the full path to your image file:',
            text=clipboard_text
        )
        
        if ok and file_path:
            file_path = file_path.strip().strip('"\'')  # Remove quotes if present
            if os.path.exists(file_path) and file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                self.process_image(file_path)
            else:
                QMessageBox.warning(self, "Invalid File",
                                  "File not found or not a valid image file.\n\n"
                                  f"Path tried: {file_path}")

    def process_image_from_clipboard(self, temp_path, pixmap):
        """Process image that was pasted from clipboard - removed since we're using file paths now"""
        pass

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                self.process_image(file_path)
            else:
                self.label.setText("Please drop an image file")

    def perform_search(self, file_path, pixmap):
        self.label.setText("Opening Google in your default browser...")
        QApplication.processEvents()  # Update UI immediately
        
        # IMPORTANT: Copy the actual image data to clipboard, not file reference
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(pixmap)  # This puts actual image data on clipboard
        
        # Give clipboard a moment to update
        QApplication.processEvents()
        
        # Open your preferred Google URL
        webbrowser.open("https://www.google.com/?olud")
        
        # Show instructions
        info_dialog = QMessageBox(self)
        info_dialog.setWindowFlags(info_dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        info_dialog.setWindowTitle("Ready to Search")
        info_dialog.setText("Image data copied to clipboard!\n\nIn Google:\n1. Click the camera/search icon\n2. Paste with Cmd+V\n\nNote: You should see the actual image, not a file icon.")
        info_dialog.setIcon(QMessageBox.Information)
        info_dialog.exec_()
        
        self.label.setText("Image data in clipboard. Ready to paste in browser.")
        
        # Clean up temp file if it exists
        if file_path.startswith(tempfile.gettempdir()):
            try:
                os.unlink(file_path)
            except:
                pass

def main():
    app = QApplication(sys.argv)
    window = DropZone()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()