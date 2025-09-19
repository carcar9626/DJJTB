import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import webbrowser
import urllib.parse
import os
from tkinterdnd2 import DND_FILES, TkinterDnD

class ReverseImageSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Reverse Image Search")
        self.root.geometry("400x300")
        self.root.configure(bg='#f0f0f0')
        
        # Main frame
        main_frame = tk.Frame(root, bg='#f0f0f0')
        main_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text="Reverse Image Search",
                              font=('Arial', 16, 'bold'), bg='#f0f0f0')
        title_label.pack(pady=(0, 20))
        
        # Drop zone - Fixed the relief issue
        self.drop_frame = tk.Frame(main_frame, bg='white', relief='ridge', bd=2)
        self.drop_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        drop_label = tk.Label(self.drop_frame, text="Drop image here\nor",
                             font=('Arial', 12), bg='white', fg='#666')
        drop_label.pack(expand=True)
        
        # Buttons frame
        buttons_frame = tk.Frame(main_frame, bg='#f0f0f0')
        buttons_frame.pack(fill='x')
        
        # Browse button
        browse_btn = tk.Button(buttons_frame, text="Browse Files",
                              command=self.browse_file, bg='#4CAF50', fg='white',
                              font=('Arial', 10), padx=20, pady=8)
        browse_btn.pack(side='left', padx=(0, 10))
        
        # Paste path button
        paste_btn = tk.Button(buttons_frame, text="Paste File Path",
                             command=self.paste_file_path, bg='#2196F3', fg='white',
                             font=('Arial', 10), padx=20, pady=8)
        paste_btn.pack(side='left', padx=(0, 10))
        
        # Clipboard path button (for copied file paths)
        clipboard_btn = tk.Button(buttons_frame, text="From Clipboard",
                                 command=self.from_clipboard, bg='#FF9800', fg='white',
                                 font=('Arial', 10), padx=20, pady=8)
        clipboard_btn.pack(side='left')
        
        # Status label
        self.status_label = tk.Label(main_frame, text="Ready",
                                    font=('Arial', 9), bg='#f0f0f0', fg='#666')
        self.status_label.pack(pady=(10, 0))
        
        # Enable drag and drop
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.on_drop)
        
    def browse_file(self):
        """Open file dialog to select image"""
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.gif *.bmp *.webp *.tiff"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.process_image(file_path)
    
    def paste_file_path(self):
        """Allow user to paste or type a file path"""
        file_path = simpledialog.askstring(
            "File Path",
            "Enter the full path to your image file:",
            initialvalue=""
        )
        if file_path:
            file_path = file_path.strip().strip('"\'')  # Remove quotes if present
            if os.path.exists(file_path) and self.is_image_file(file_path):
                self.process_image(file_path)
            else:
                messagebox.showerror("Error", "File not found or not a valid image file.")
    
    def from_clipboard(self):
        """Try to get file path from clipboard"""
        try:
            clipboard_content = self.root.clipboard_get().strip().strip('"\'')
            if os.path.exists(clipboard_content) and self.is_image_file(clipboard_content):
                self.process_image(clipboard_content)
            else:
                messagebox.showwarning("Warning",
                    "Clipboard doesn't contain a valid image file path.\n"
                    "Copy a file path to clipboard first (Cmd+C on selected file in Finder).")
        except tk.TclError:
            messagebox.showwarning("Warning", "No text found in clipboard.")
    
    def on_drop(self, event):
        """Handle drag and drop"""
        files = self.root.tk.splitlist(event.data)
        if files:
            file_path = files[0]
            if self.is_image_file(file_path):
                self.process_image(file_path)
            else:
                messagebox.showerror("Error", "Please drop a valid image file.")
    
    def is_image_file(self, file_path):
        """Check if file is an image based on extension"""
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}
        return os.path.splitext(file_path.lower())[1] in valid_extensions
    
    def process_image(self, file_path):
        """Process the image file and open reverse search"""
        try:
            if not os.path.exists(file_path):
                messagebox.showerror("Error", f"File not found: {file_path}")
                return
            
            self.status_label.config(text=f"Processing: {os.path.basename(file_path)}")
            self.root.update()
            
            # Convert file path to file:// URL for Google Images
            file_url = f"file://{urllib.parse.quote(os.path.abspath(file_path))}"
            
            # Open Google reverse image search
            search_url = f"https://www.google.com/searchbyimage?image_url={urllib.parse.quote(file_url)}"
            webbrowser.open(search_url)
            
            self.status_label.config(text=f"Opened: {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            self.status_label.config(text="Error occurred")

def main():
    root = TkinterDnD.Tk()
    app = ReverseImageSearchApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()