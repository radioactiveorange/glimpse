"""Random Image Viewer - Main application entry point."""

import sys
from PySide6.QtWidgets import QApplication, QDialog

from src.ui.styles import DARK_STYLESHEET
from src.ui.main_window import RandomImageViewer
from src.ui.startup_dialog import StartupDialog
from src.core.image_utils import emoji_icon

def main():
    """Main application entry point with startup dialog."""
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    app.setWindowIcon(emoji_icon("🎲", 128))
    
    # Show startup dialog
    startup = StartupDialog()
    
    # Connect startup dialog signals
    viewer = None
    
    def on_collection_selected(data):
        nonlocal viewer
        if not data or len(data) != 3:
            return
        collection, timer_enabled, timer_interval = data
        viewer = RandomImageViewer()
        viewer.load_collection(collection, timer_enabled, timer_interval)
        viewer.show()
    
    def on_folder_selected(data):
        nonlocal viewer
        if not data or len(data) != 3:
            return
        folder, timer_enabled, timer_interval = data
        viewer = RandomImageViewer()
        viewer.load_folder(folder, timer_enabled, timer_interval)
        viewer.show()
    
    startup.collection_selected.connect(on_collection_selected)
    startup.folder_selected.connect(on_folder_selected)
    
    if startup.exec() == QDialog.Accepted and viewer:
        return app.exec()
    else:
        return 0

if __name__ == "__main__":
    sys.exit(main())
