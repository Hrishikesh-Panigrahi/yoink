import threading
import time
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal

class Loader(QObject):
    """A utility class to handle loading animations and progress updates"""
    
    # Signals for updating the UI
    progress_updated = pyqtSignal(str)  # Signal to update progress message
    loading_finished = pyqtSignal()     # Signal when loading is complete
    
    def __init__(self, initial_message: str = "Loading..."):
        super().__init__()
        self.message = initial_message
        self.is_loading = False
        self.loader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
    def start(self, message: Optional[str] = None):
        """Start the loading animation with an optional message"""
        if self.is_loading:
            return
            
        if message:
            self.message = message
            
        self.is_loading = True
        self._stop_event.clear()
        self.loader_thread = threading.Thread(target=self._run_loader)
        self.loader_thread.daemon = True
        self.loader_thread.start()
        
    def stop(self):
        """Stop the loading animation"""
        if not self.is_loading:
            return
            
        self._stop_event.set()
        if self.loader_thread:
            self.loader_thread.join(timeout=1.0)
        self.is_loading = False
        self.loading_finished.emit()
        
    def update(self, message: str):
        """Update the loading message"""
        self.message = message
        self.progress_updated.emit(message)
        
    def _run_loader(self):
        """Run the loading animation in a separate thread"""
        spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        idx = 0
        
        while not self._stop_event.is_set():
            # Update the progress message with the spinner
            progress_msg = f"{spinner[idx]} {self.message}"
            self.progress_updated.emit(progress_msg)
            
            # Update spinner index
            idx = (idx + 1) % len(spinner)
            
            # Sleep for a short duration
            time.sleep(0.1)
            
        # Clear the progress message when done
        self.progress_updated.emit("") 