import threading
import time
from typing import Optional, List, Dict, Callable
from PyQt6.QtCore import QObject, pyqtSignal
from enum import Enum, auto

class LoaderStyle(Enum):
    """Available loader animation styles"""
    SPINNER = auto()
    DOTS = auto()
    BAR = auto()
    PULSE = auto()

class Loader(QObject):
    """A utility class to handle loading animations and progress updates with enhanced features"""
    
    # Signals for updating the UI
    progress_updated = pyqtSignal(str)  # Signal to update progress message
    progress_percentage = pyqtSignal(int)  # Signal to update progress percentage
    loading_finished = pyqtSignal()     # Signal when loading is complete
    loading_error = pyqtSignal(str)     # Signal for error reporting
    
    # Animation frames for different styles
    ANIMATIONS: Dict[LoaderStyle, List[str]] = {
        LoaderStyle.SPINNER: ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
        LoaderStyle.DOTS: ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
        LoaderStyle.BAR: ['[□□□□□□□□□□]', '[■□□□□□□□□□]', '[■■□□□□□□□□]', '[■■■□□□□□□□]', 
                         '[■■■■□□□□□□]', '[■■■■■□□□□□]', '[■■■■■■□□□□]', '[■■■■■■■□□□]',
                         '[■■■■■■■■□□]', '[■■■■■■■■■□]', '[■■■■■■■■■■]'],
        LoaderStyle.PULSE: ['●○○○○○○○○○', '○●○○○○○○○○', '○○●○○○○○○○', '○○○●○○○○○○', 
                          '○○○○●○○○○○', '○○○○○●○○○○', '○○○○○○●○○○', '○○○○○○○●○○',
                          '○○○○○○○○●○', '○○○○○○○○○●']
    }
    
    def __init__(self, initial_message: str = "Loading...", style: LoaderStyle = LoaderStyle.SPINNER):
        super().__init__()
        self.message = initial_message
        self.style = style
        self.is_loading = False
        self.progress = 0
        self.loader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._error_handlers: List[Callable[[str], None]] = []
        
    def start(self, message: Optional[str] = None, style: Optional[LoaderStyle] = None):
        """Start the loading animation with an optional message and style"""
        if self.is_loading:
            self.stop()
            
        if message:
            self.message = message
        if style:
            self.style = style
            
        self.is_loading = True
        self.progress = 0
        self._stop_event.clear()
        
        # Emit initial progress message
        self.progress_updated.emit(self.message)
        self.progress_percentage.emit(0)
        
        # Start loader thread
        self.loader_thread = threading.Thread(target=self._run_loader)
        self.loader_thread.daemon = True
        self.loader_thread.start()
        
    def stop(self, error: Optional[str] = None):
        """Stop the loading animation with optional error message"""
        if not self.is_loading:
            return
            
        self._stop_event.set()
        if self.loader_thread:
            self.loader_thread.join(timeout=1.0)
        self.is_loading = False
        
        if error:
            self.loading_error.emit(error)
            for handler in self._error_handlers:
                try:
                    handler(error)
                except Exception as e:
                    print(f"Error in error handler: {str(e)}")
        else:
            # Clear the progress message and emit finished signal
            self.progress_updated.emit("")
            self.loading_finished.emit()
        
    def update(self, message: str, progress: Optional[int] = None):
        """Update the loading message and optionally the progress percentage"""
        self.message = message
        if progress is not None:
            self.progress = max(0, min(100, progress))
            self.progress_percentage.emit(self.progress)
        self.progress_updated.emit(message)
        
    def add_error_handler(self, handler: Callable[[str], None]):
        """Add a custom error handler"""
        self._error_handlers.append(handler)
        
    def _run_loader(self):
        """Run the loading animation in a separate thread"""
        try:
            frames = self.ANIMATIONS[self.style]
            idx = 0
            
            while not self._stop_event.is_set():
                # Update the progress message with the animation
                progress_msg = f"{frames[idx]} {self.message}"
                if self.progress > 0:
                    progress_msg += f" ({self.progress}%)"
                self.progress_updated.emit(progress_msg)
                
                # Update animation index
                idx = (idx + 1) % len(frames)
                
                # Sleep for a short duration
                time.sleep(0.1)
        except Exception as e:
            self.stop(f"Loader error: {str(e)}") 