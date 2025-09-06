"""Base class for dialogs that automatically center themselves on screen."""

from PySide6.QtWidgets import QDialog, QApplication
from PySide6.QtCore import QTimer


class CenteredDialog(QDialog):
    """Base dialog class that automatically centers itself on screen.
    
    Eliminates the need for duplicate centering logic across all dialogs.
    Simply inherit from this class instead of QDialog.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
    
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
        # Use QTimer.singleShot to center after dialog is fully rendered
        QTimer.singleShot(0, self.center_on_screen)


class CenteredMainWindow(QDialog):
    """Base class for main windows that need centering functionality.
    
    For windows that need centering but aren't modal dialogs.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(False)
        self._centered = False
    
    def center_on_screen(self):
        """Center the window on the screen."""
        screen = QApplication.primaryScreen().availableGeometry()
        window = self.frameGeometry()
        x = (screen.width() - window.width()) // 2 + screen.x()
        y = (screen.height() - window.height()) // 2 + screen.y()
        self.move(x, y)
    
    def showEvent(self, event):
        """Override showEvent to center window when first shown."""
        super().showEvent(event)
        if not self._centered:
            # Use QTimer to center after window is fully shown
            QTimer.singleShot(0, self._delayed_center)
            self._centered = True
    
    def _delayed_center(self):
        """Delayed centering to ensure window is fully rendered."""
        self.center_on_screen()