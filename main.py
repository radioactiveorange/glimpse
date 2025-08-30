"""Glimpse - Main application entry point."""

import sys
import os
from PySide6.QtWidgets import QApplication, QDialog

from src.ui.styles import DARK_STYLESHEET
from src.ui.main_window import GlimpseViewer
from src.ui.startup_dialog import StartupDialog
from PySide6.QtGui import QIcon

def main():
    """Main application entry point with startup dialog."""
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    # Get the directory where the script/executable is located
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        app_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    icon_path = os.path.join(app_dir, "app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Show startup dialog
    startup = StartupDialog()
    
    # Connect startup dialog signals
    viewer = None
    
    def on_collection_selected(data):
        nonlocal viewer
        if not data or len(data) != 3:
            return
        collection, timer_enabled, timer_interval = data
        viewer = GlimpseViewer()
        viewer.load_collection(collection, timer_enabled, timer_interval)
        viewer.show()
        viewer.center_on_screen()  # Explicitly center after show
    
    def on_folder_selected(data):
        nonlocal viewer
        if not data or len(data) != 3:
            return
        folder, timer_enabled, timer_interval = data
        viewer = GlimpseViewer()
        viewer.load_folder(folder, timer_enabled, timer_interval)
        viewer.show()
        viewer.center_on_screen()  # Explicitly center after show
    
    startup.collection_selected.connect(on_collection_selected)
    startup.folder_selected.connect(on_folder_selected)
    
    if startup.exec() == QDialog.Accepted and viewer:
        return app.exec()
    else:
        return 0

if __name__ == "__main__":
    sys.exit(main())
