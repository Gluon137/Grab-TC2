#!/usr/bin/env python3
"""
TaskCard Downloader GUI - Grafische Benutzeroberfläche für den TaskCard Downloader
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
from taskcard_downloader import TaskCardDownloader
import logging

class TaskCardGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TaskCard Downloader")
        self.root.geometry("600x500")
        self.root.minsize(500, 400)
        
        # Variables
        self.url_var = tk.StringVar()
        self.folder_var = tk.StringVar(value=os.path.join(os.getcwd(), "taskcard_download"))
        self.is_downloading = False
        
        self.setup_ui()
        self.setup_logging()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="TaskCard Downloader", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # URL input
        ttk.Label(main_frame, text="TaskCard URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=50)
        url_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        
        # Download folder selection
        ttk.Label(main_frame, text="Download-Ordner:").grid(row=2, column=0, sticky=tk.W, pady=5)
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        folder_frame.columnconfigure(0, weight=1)
        
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, width=40)
        folder_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        browse_button = ttk.Button(folder_frame, text="Durchsuchen", 
                                 command=self.browse_folder)
        browse_button.grid(row=0, column=1, padx=(5, 0))
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Optionen", padding="5")
        options_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        options_frame.columnconfigure(1, weight=1)
        
        # Headless option
        self.headless_var = tk.BooleanVar(value=True)
        headless_check = ttk.Checkbutton(options_frame, text="Headless-Modus (Browser im Hintergrund)", 
                                       variable=self.headless_var)
        headless_check.grid(row=0, column=0, sticky=tk.W)
        
        # Download buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        self.download_button = ttk.Button(button_frame, text="Download starten", 
                                        command=self.start_download)
        self.download_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="Stoppen", 
                                    command=self.stop_download, state="disabled")
        self.stop_button.pack(side=tk.LEFT)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        # Status label
        self.status_var = tk.StringVar(value="Bereit")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=6, column=0, columnspan=2, sticky=tk.W)
        
        # Log output
        log_frame = ttk.LabelFrame(main_frame, text="Log-Ausgabe", padding="5")
        log_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear log button
        clear_log_button = ttk.Button(log_frame, text="Log löschen", 
                                    command=self.clear_log)
        clear_log_button.grid(row=1, column=0, sticky=tk.E, pady=(5, 0))
        
    def setup_logging(self):
        """Setup logging to display in the GUI"""
        # Create a custom handler that writes to the GUI
        self.log_handler = GUILogHandler(self.log_text)
        self.log_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.log_handler.setFormatter(formatter)
        
        # Add handler to the taskcard_downloader logger
        logger = logging.getLogger('taskcard_downloader')
        logger.addHandler(self.log_handler)
        logger.setLevel(logging.INFO)
        
    def browse_folder(self):
        """Browse for download folder"""
        folder = filedialog.askdirectory(
            title="Download-Ordner auswählen",
            initialdir=self.folder_var.get()
        )
        if folder:
            self.folder_var.set(folder)
    
    def clear_log(self):
        """Clear the log output"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def validate_input(self):
        """Validate user input"""
        url = self.url_var.get().strip()
        folder = self.folder_var.get().strip()
        
        if not url:
            messagebox.showerror("Fehler", "Bitte geben Sie eine TaskCard URL ein.")
            return False
        
        if not url.startswith(('http://', 'https://')):
            messagebox.showerror("Fehler", "Bitte geben Sie eine gültige URL ein (mit http:// oder https://).")
            return False
        
        if not folder:
            messagebox.showerror("Fehler", "Bitte wählen Sie einen Download-Ordner aus.")
            return False
        
        # Create folder if it doesn't exist
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Fehler", f"Kann Download-Ordner nicht erstellen: {e}")
            return False
        
        return True
    
    def start_download(self):
        """Start the download process"""
        if not self.validate_input():
            return
        
        if self.is_downloading:
            messagebox.showwarning("Warnung", "Download läuft bereits.")
            return
        
        # Start download in separate thread
        self.is_downloading = True
        self.download_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress.start()
        self.status_var.set("Download läuft...")
        
        # Clear log
        self.clear_log()
        
        # Start download thread
        self.download_thread = threading.Thread(target=self.download_worker, daemon=True)
        self.download_thread.start()
    
    def stop_download(self):
        """Stop the download process"""
        if self.is_downloading:
            self.status_var.set("Download wird gestoppt...")
            self.is_downloading = False
            # Note: This is a basic implementation. In a real scenario, 
            # you would need to properly signal the download thread to stop
    
    def download_worker(self):
        """Worker function for download (runs in separate thread)"""
        try:
            url = self.url_var.get().strip()
            folder = self.folder_var.get().strip()
            
            # Create downloader instance
            headless = self.headless_var.get()
            downloader = TaskCardDownloader(url, folder, headless)
            
            # Modify driver setup based on headless option
            original_setup = downloader.setup_driver
            def modified_setup():
                chrome_options = downloader.setup_driver.__self__.chrome_options if hasattr(downloader.setup_driver, '__self__') else None
                result = original_setup()
                return result
            
            # Run download
            success = downloader.run()
            
            # Update UI in main thread
            self.root.after(0, self.download_completed, success, folder)
            
        except Exception as e:
            self.root.after(0, self.download_error, str(e))
    
    def download_completed(self, success, folder):
        """Called when download is completed"""
        self.is_downloading = False
        self.download_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.progress.stop()
        
        if success:
            self.status_var.set("Download erfolgreich abgeschlossen!")
            messagebox.showinfo("Erfolg", 
                              f"Download erfolgreich abgeschlossen!\n\nDateien gespeichert in:\n{folder}")
        else:
            self.status_var.set("Download fehlgeschlagen")
            messagebox.showerror("Fehler", "Download fehlgeschlagen. Überprüfen Sie die Log-Ausgabe für Details.")
    
    def download_error(self, error_msg):
        """Called when download encounters an error"""
        self.is_downloading = False
        self.download_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.progress.stop()
        self.status_var.set("Download fehlgeschlagen")
        
        messagebox.showerror("Fehler", f"Download fehlgeschlagen:\n{error_msg}")

class GUILogHandler(logging.Handler):
    """Custom log handler that writes to a tkinter Text widget"""
    
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
    
    def emit(self, record):
        """Emit a log record to the text widget"""
        try:
            msg = self.format(record)
            # Schedule the update in the main thread
            self.text_widget.after(0, self.append_log, msg)
        except Exception:
            self.handleError(record)
    
    def append_log(self, msg):
        """Append log message to text widget (must be called from main thread)"""
        try:
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)  # Scroll to bottom
            self.text_widget.config(state=tk.DISABLED)
        except Exception:
            pass  # Widget might be destroyed

def main():
    """Main function"""
    root = tk.Tk()
    app = TaskCardGUI(root)
    
    # Center window on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2
    y = (root.winfo_screenheight() - root.winfo_reqheight()) // 2
    root.geometry(f"+{x}+{y}")
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()