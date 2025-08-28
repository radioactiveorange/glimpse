"""Random Image Viewer - Main application entry point."""

import sys
from PySide6.QtWidgets import QApplication

from src.ui.styles import DARK_STYLESHEET
from src.ui.main_window import RandomImageViewer
from src.core.image_utils import emoji_icon

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    app.setWindowIcon(emoji_icon("🎲", 128))
    viewer = RandomImageViewer()
    viewer.show()
    sys.exit(app.exec())
