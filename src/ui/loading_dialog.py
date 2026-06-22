"""Loading dialog with progress indication for large collections."""

from PySide6.QtWidgets import QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
import os
from typing import List

from ..core.image_utils import IMAGE_EXTENSIONS
from .components.centered_dialog import CenteredDialog


class ImageLoadingWorker(QThread):
    """Worker thread for loading images asynchronously."""

    progress_updated = Signal(
        int, int, str
    )  # current_images, estimated_total, current_folder
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
        found = 0
        running_max = 100  # lookahead buffer; grows as we find more

        for base_path in self.paths:
            if self._should_stop:
                return
            if not os.path.exists(base_path):
                continue

            for root, dirs, files in os.walk(base_path):
                if self._should_stop:
                    return

                folder_name = os.path.basename(root) or os.path.basename(base_path)

                for filename in files:
                    if self._should_stop:
                        return

                    if os.path.splitext(filename)[1].lower() in IMAGE_EXTENSIONS:
                        all_images.append(os.path.join(root, filename))
                        found += 1

                        if found % 50 == 0:
                            running_max = max(running_max, int(found * 1.1))
                            self.progress_updated.emit(found, running_max, folder_name)

                # emit after each folder so small collections still get updates
                running_max = max(running_max, int(found * 1.1))
                self.progress_updated.emit(found, running_max, folder_name)

        if not self._should_stop:
            self.loading_finished.emit(all_images)


class LoadingDialog(CenteredDialog):
    """Loading dialog with progress bar and folder information."""

    def __init__(self, paths: List[str], parent=None):
        super().__init__(parent)
        self.paths = paths
        self.worker = None
        self.images = []

        self.setWindowTitle("Loading Images...")
        self.setFixedSize(400, 150)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)

        self.init_ui()
        self.start_loading()

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

    def start_loading(self):
        """Start the image loading process."""
        self.worker = ImageLoadingWorker(self.paths)
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.loading_finished.connect(self.on_loading_finished)
        self.worker.start()

    def on_progress_updated(
        self, current_images: int, running_max: int, folder_name: str
    ):
        """Update progress display."""
        self.progress_bar.setMaximum(running_max)
        self.progress_bar.setValue(current_images)
        self.info_label.setText(f"Scanning: {folder_name}")
        self.count_label.setText(f"Found: {current_images} images")

    def on_loading_finished(self, images: List[str]):
        """Handle completion of image loading."""
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
