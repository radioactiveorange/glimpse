#!/usr/bin/env python3
"""
Proof of concept: Embed feh image viewer in Qt window for blazing fast performance.
"""

import sys
import subprocess
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt

class FehViewer(QMainWindow):
    """Qt window that embeds feh for ultra-fast image viewing."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Glimpse - Feh Integration Test")
        self.setGeometry(100, 100, 1000, 700)

        # Main widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Container for feh to render into
        self.feh_container = QWidget()
        self.feh_container.setMinimumSize(800, 600)
        self.feh_container.setStyleSheet("background-color: black;")
        layout.addWidget(self.feh_container)

        # Control buttons
        controls = QHBoxLayout()

        prev_btn = QPushButton("← Previous")
        prev_btn.clicked.connect(self.previous_image)
        controls.addWidget(prev_btn)

        next_btn = QPushButton("Next →")
        next_btn.clicked.connect(self.next_image)
        controls.addWidget(next_btn)

        layout.addLayout(controls)

        self.feh_process = None
        self.current_index = 0
        self.images = [
            "/usr/share/pixmaps/debian-logo.png",
            "/usr/share/pixmaps/gdebi.png",
        ]

    def showEvent(self, event):
        """Launch feh when window is shown."""
        super().showEvent(event)
        if not self.feh_process:
            # Get the X11 window ID of our container widget
            window_id = self.feh_container.winId()
            print(f"Container Window ID: {window_id}")

            # Launch feh embedded in our window
            self.launch_feh(window_id)

    def launch_feh(self, window_id):
        """Launch feh process embedded in the Qt window."""
        if self.feh_process:
            self.feh_process.terminate()

        if not self.images:
            return

        img_path = self.images[self.current_index]

        # Launch feh with window-id to embed it
        cmd = [
            'feh',
            '--window-id', str(window_id),
            '--scale-down',  # Fit image to window
            '--auto-zoom',   # Auto zoom
            img_path
        ]

        print(f"Launching: {' '.join(cmd)}")
        self.feh_process = subprocess.Popen(cmd)

    def previous_image(self):
        """Show previous image."""
        if self.current_index > 0:
            self.current_index -= 1
            window_id = self.feh_container.winId()
            self.launch_feh(window_id)

    def next_image(self):
        """Show next image."""
        if self.current_index < len(self.images) - 1:
            self.current_index += 1
            window_id = self.feh_container.winId()
            self.launch_feh(window_id)

    def closeEvent(self, event):
        """Clean up feh process on close."""
        if self.feh_process:
            self.feh_process.terminate()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = FehViewer()
    viewer.show()
    sys.exit(app.exec())
