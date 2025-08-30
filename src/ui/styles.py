"""UI styling constants and themes."""

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QEvent
from ..core.image_utils import create_professional_icon


def create_standard_button(text: str, icon_name: str = None, large: bool = False) -> QPushButton:
    """Create a standard button with consistent styling."""
    button = QPushButton(text)
    
    # Set consistent size and styling with clear enabled/disabled states
    if large:
        button.setMinimumHeight(40)
        button.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                font-weight: 500;
                padding: 8px 16px;
                border-radius: 6px;
                background-color: #404244;
                color: #ffffff;
                border: 1px solid #606264;
            }
            QPushButton:hover {
                background-color: #4a4c4e;
                border: 1px solid #707274;
            }
            QPushButton:pressed {
                background-color: #363638;
                border: 1px solid #505254;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #404040;
            }
        """)
    else:
        button.setMinimumHeight(32)
        button.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                padding: 6px 12px;
                border-radius: 4px;
                background-color: #404244;
                color: #ffffff;
                border: 1px solid #606264;
            }
            QPushButton:hover {
                background-color: #4a4c4e;
                border: 1px solid #707274;
            }
            QPushButton:pressed {
                background-color: #363638;
                border: 1px solid #505254;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #404040;
            }
        """)
    
    # Add icon if specified with disabled state support
    if icon_name:
        # Create both enabled and disabled icons
        enabled_icon = create_professional_icon(icon_name, 16, "#ffffff")
        disabled_icon = create_professional_icon(icon_name, 16, "#666666")
        
        # Set the enabled icon
        button.setIcon(enabled_icon)
        
        # Store disabled icon for state changes
        button._disabled_icon = disabled_icon
        button._enabled_icon = enabled_icon
        
        # Override changeEvent to handle icon state changes
        original_change_event = button.changeEvent
        def change_event_handler(event):
            if event.type() == QEvent.Type.EnabledChange:
                if button.isEnabled():
                    button.setIcon(button._enabled_icon)
                else:
                    button.setIcon(button._disabled_icon)
            original_change_event(event)
        button.changeEvent = change_event_handler
        
        # Add consistent spacing between icon and text - larger for big buttons
        spacing = "12px" if large else "10px"
        button.setStyleSheet(button.styleSheet() + f"text-align: left; padding-left: {spacing};")
    
    return button


def create_dialog_action_button(text: str, primary: bool = False, icon_name: str = None) -> QPushButton:
    """Create a dialog action button (OK, Cancel, etc.) with consistent styling."""
    button = QPushButton(text)
    button.setMinimumHeight(32)
    button.setMinimumWidth(80)
    
    # Add icon if specified with disabled state support
    if icon_name:
        # Create both enabled and disabled icons
        enabled_icon = create_professional_icon(icon_name, 16, "#ffffff")
        disabled_icon = create_professional_icon(icon_name, 16, "#666666")
        
        # Set the enabled icon
        button.setIcon(enabled_icon)
        
        # Store disabled icon for state changes
        button._disabled_icon = disabled_icon
        button._enabled_icon = enabled_icon
        
        # Override changeEvent to handle icon state changes
        original_change_event = button.changeEvent
        def change_event_handler(event):
            if event.type() == QEvent.Type.EnabledChange:
                if button.isEnabled():
                    button.setIcon(button._enabled_icon)
                else:
                    button.setIcon(button._disabled_icon)
            original_change_event(event)
        button.changeEvent = change_event_handler
    
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
            QPushButton:disabled {
                background-color: #404040;
                color: #888888;
                border: 1px solid #505050;
            }
        """)
    else:
        button.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                padding: 6px 16px;
                border-radius: 4px;
                background-color: #404244;
                color: #ffffff;
                border: 1px solid #606264;
            }
            QPushButton:hover {
                background-color: #4a4c4e;
                border: 1px solid #707274;
            }
            QPushButton:pressed {
                background-color: #363638;
                border: 1px solid #505254;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #404040;
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