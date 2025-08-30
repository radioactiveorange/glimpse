"""UI styling constants and themes."""

from PySide6.QtWidgets import QPushButton
from ..core.image_utils import create_professional_icon


def create_standard_button(text: str, icon_name: str = None, large: bool = False) -> QPushButton:
    """Create a standard button with consistent styling."""
    button = QPushButton(text)
    
    # Set consistent size
    if large:
        button.setMinimumHeight(40)
        button.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                font-weight: 500;
                padding: 8px 16px;
                border-radius: 6px;
            }
        """)
    else:
        button.setMinimumHeight(32)
        button.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                padding: 6px 12px;
                border-radius: 4px;
            }
        """)
    
    # Add icon if specified
    if icon_name:
        button.setIcon(create_professional_icon(icon_name, 16))
        # Add consistent spacing between icon and text
        button.setStyleSheet(button.styleSheet() + "text-align: left; padding-left: 8px;")
    
    return button


def create_dialog_action_button(text: str, primary: bool = False, icon_name: str = None) -> QPushButton:
    """Create a dialog action button (OK, Cancel, etc.) with consistent styling."""
    button = QPushButton(text)
    button.setMinimumHeight(32)
    button.setMinimumWidth(80)
    
    # Add icon if specified
    if icon_name:
        button.setIcon(create_professional_icon(icon_name, 16))
    
    if primary:
        button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                font-size: 12px;
                font-weight: 500;
                padding: 6px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
    else:
        button.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                padding: 6px 16px;
                border-radius: 4px;
            }
        """)
    
    return button


DARK_STYLESHEET = """
QWidget { background-color: #232629; color: #b7bcc1; font-size: 11px; }
QLabel, QCheckBox, QSpinBox, QListWidget, QToolButton { font-size: 11px; color: #b7bcc1; }
QStatusBar { font-size: 10px; color: #888; }
QSplitter::handle { background: #232629; border: none; height: 1px; }
QPushButton, QToolButton {
    background: transparent;
    color: #c7ccd1;
    border: none;
    border-radius: 4px;
    min-width: 24px;
    min-height: 24px;
    font-size: 13px;
    padding: 0 2px;
}
QPushButton:hover, QToolButton:hover { background: #2e3034; }
QListWidget::item:selected { background: #354e6e; color: #fff; }
QCheckBox:checked { color: #3b7dd8; }
QToolBar::separator {
    background: #35383b;
    width: 1px;
    margin: 0 4px;
}
QToolBar {
    border: none;
    background: #232629; /* or your preferred color */
}
"""