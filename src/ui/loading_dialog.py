"""Loading dialog with progress indication for large collections."""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QHBoxLayout, QApplication
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
import os
from typing import List

from ..core.image_utils import IMAGE_EXTENSIONS


class ImageLoadingWorker(QThread):
    """Worker thread for loading images asynchronously."""
    
    progress_updated = Signal(int, int, str)  # current_images, estimated_total, current_folder
    loading_finished = Signal(list)  # List of image paths
    
    def __init__(self, paths: List[str]):
        super().__init__()
        self.paths = paths if isinstance(paths, list) else [paths]
        self._should_stop = False
    
    def stop(self):
        """Signal the worker to stop loading."""
        self._should_stop = True
    
    def run(self):
        """Load images from all provided paths."""
        all_images = []
        self._current_image_count = 0
        
        # First pass: estimate total images by sampling folders
        estimated_total = self._estimate_total_images()
        if self._should_stop:
            return
        
        # Second pass: actually collect images with better progress tracking
        for base_path in self.paths:
            if self._should_stop:
                return
                
            if not os.path.exists(base_path):
                continue
                
            for root, dirs, files in os.walk(base_path):
                if self._should_stop:
                    return
                
                folder_name = os.path.basename(root) or os.path.basename(base_path)
                
                # Process files in current directory
                for filename in files:
                    if self._should_stop:
                        return
                    
                    if os.path.splitext(filename)[1].lower() in IMAGE_EXTENSIONS:
                        all_images.append(os.path.join(root, filename))
                        self._current_image_count += 1
                        
                        # Emit progress more frequently for better user feedback
                        if self._current_image_count % 50 == 0 or self._current_image_count % 100 == 1:
                            # Update estimate if we've exceeded it
                            if self._current_image_count > estimated_total:
                                estimated_total = int(self._current_image_count * 1.2)
                            self.progress_updated.emit(self._current_image_count, estimated_total, folder_name)
                
                # Update progress after each folder
                if self._current_image_count > estimated_total:
                    estimated_total = int(self._current_image_count * 1.2)
                self.progress_updated.emit(self._current_image_count, estimated_total, folder_name)
        
        if not self._should_stop:
            self.loading_finished.emit(all_images)
    
    def _estimate_total_images(self):
        """Estimate total number of images by sampling folders."""
        total_estimate = 0
        folders_sampled = 0
        max_sample_folders = 10  # Sample up to 10 folders for estimation
        
        for base_path in self.paths:
            if self._should_stop:
                return 0
            if not os.path.exists(base_path):
                continue
                
            for root, dirs, files in os.walk(base_path):
                if self._should_stop:
                    return 0
                
                # Sample folder to estimate
                image_count = sum(1 for f in files 
                                if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS)
                total_estimate += image_count
                folders_sampled += 1
                
                # If we've sampled enough, estimate the rest
                if folders_sampled >= max_sample_folders:
                    # Count remaining folders
                    remaining_folders = 0
                    for remaining_root, remaining_dirs, remaining_files in os.walk(base_path):
                        remaining_folders += 1
                    remaining_folders -= folders_sampled
                    
                    if folders_sampled > 0:
                        avg_per_folder = total_estimate / folders_sampled
                        total_estimate += int(avg_per_folder * remaining_folders)
                    break
        
        return max(total_estimate, 100)  # Ensure we have at least some estimate


class LoadingDialog(QDialog):
    """Loading dialog with progress bar and folder information."""
    
    def __init__(self, paths: List[str], parent=None):
        super().__init__(parent)
        self.paths = paths
        self.worker = None
        self.images = []
        
        self.setWindowTitle("Loading Images...")
        self.setModal(True)
        self.setFixedSize(400, 150)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        self.init_ui()
        self.start_loading()
    
    def center_on_screen(self):
        """Center the dialog on the screen."""
        screen = QApplication.primaryScreen().availableGeometry()
        dialog = self.frameGeometry()
        x = (screen.width() - dialog.width()) // 2 + screen.x()
        y = (screen.height() - dialog.height()) // 2 + screen.y()
        self.move(x, y)
    
    def showEvent(self, event):
        """Override showEvent to center dialog when shown."""
        super().showEvent(event)
        QTimer.singleShot(0, self.center_on_screen)
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("Scanning for images...")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Progress info
        self.info_label = QLabel("Initializing...")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.info_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #2b2b2b;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Image count
        self.count_label = QLabel("Found: 0 images")
        self.count_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.count_label)
        
        # Animate progress bar when indeterminate
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._animate_progress)
        self.animation_value = 0
    
    def start_loading(self):
        """Start the image loading process."""
        self.worker = ImageLoadingWorker(self.paths)
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.loading_finished.connect(self.on_loading_finished)
        self.worker.start()
        
        # Start animation
        self.animation_timer.start(50)  # 20 FPS
    
    def _animate_progress(self):
        """Animate progress bar when in indeterminate mode."""
        if self.progress_bar.maximum() == 100 and self.progress_bar.value() == 0:
            # Pulse animation
            self.animation_value = (self.animation_value + 2) % 100
            if self.animation_value > 50:
                value = 100 - self.animation_value
            else:
                value = self.animation_value
            self.progress_bar.setValue(value)
    
    def on_progress_updated(self, current_images: int, estimated_total: int, folder_name: str):
        """Update progress display."""
        if estimated_total > 0:
            # Switch to determinate progress
            self.animation_timer.stop()
            self.progress_bar.setMaximum(estimated_total)
            self.progress_bar.setValue(current_images)
            
            progress_percent = int((current_images / estimated_total) * 100)
            self.info_label.setText(f"Scanning: {folder_name}")
            
            # Update image count
            self.count_label.setText(f"Found: {current_images} images")
    
    def on_loading_finished(self, images: List[str]):
        """Handle completion of image loading."""
        self.animation_timer.stop()
        self.images = images
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.info_label.setText("Loading complete!")
        self.count_label.setText(f"Found: {len(images)} images")
        
        # Brief delay to show completion, then close
        QTimer.singleShot(500, self.accept)
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)  # Wait up to 3 seconds
        event.accept()
    
    def get_images(self) -> List[str]:
        """Get the loaded images."""
        return self.images