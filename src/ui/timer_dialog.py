"""Timer configuration dialog for collections."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QRadioButton, QSpinBox, QButtonGroup, QGroupBox, QApplication
)
from PySide6.QtCore import Qt, QTimer
from .styles import create_dialog_action_button


class TimerConfigDialog(QDialog):
    """Dialog for configuring timer settings when opening a collection."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Timer Settings")
        self.setModal(True)
        self.resize(350, 250)
        
        self.timer_enabled = False
        self.timer_interval = 60  # Default 60 seconds
        
        self.init_ui()
    
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
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Timer Configuration")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Timer group
        timer_group = QGroupBox("Auto-Advance Timer")
        timer_layout = QVBoxLayout(timer_group)
        
        # Radio buttons for timer options
        self.button_group = QButtonGroup()
        
        self.no_timer_radio = QRadioButton("No timer - manual navigation only")
        self.no_timer_radio.setChecked(True)
        self.button_group.addButton(self.no_timer_radio, 0)
        timer_layout.addWidget(self.no_timer_radio)
        
        # Preset timer options
        presets = [
            ("30 seconds", 30),
            ("1 minute", 60),
            ("2 minutes", 120),
            ("5 minutes", 300)
        ]
        
        self.preset_radios = []
        for i, (label, seconds) in enumerate(presets):
            radio = QRadioButton(label)
            self.button_group.addButton(radio, i + 1)
            self.preset_radios.append((radio, seconds))
            timer_layout.addWidget(radio)
        
        # Custom timer option
        custom_layout = QHBoxLayout()
        self.custom_radio = QRadioButton("Custom:")
        self.button_group.addButton(self.custom_radio, len(presets) + 1)
        custom_layout.addWidget(self.custom_radio)
        
        self.custom_spinbox = QSpinBox()
        self.custom_spinbox.setRange(5, 3600)  # 5 seconds to 1 hour
        self.custom_spinbox.setValue(60)
        self.custom_spinbox.setSuffix(" seconds")
        self.custom_spinbox.setEnabled(False)
        custom_layout.addWidget(self.custom_spinbox)
        
        custom_layout.addStretch()
        timer_layout.addLayout(custom_layout)
        
        layout.addWidget(timer_group)
        
        # Connect signals
        self.custom_radio.toggled.connect(self.custom_spinbox.setEnabled)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = create_dialog_action_button("Start Viewing", primary=True, icon_name="ok")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        cancel_button = create_dialog_action_button("Cancel", icon_name="cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def get_timer_settings(self):
        """Get the selected timer settings."""
        checked_button = self.button_group.checkedButton()
        button_id = self.button_group.id(checked_button)
        
        if button_id == 0:  # No timer
            return False, 60
        elif button_id == len(self.preset_radios) + 1:  # Custom
            return True, self.custom_spinbox.value()
        else:  # Preset
            for i, (radio, seconds) in enumerate(self.preset_radios):
                if button_id == i + 1:
                    return True, seconds
        
        return False, 60  # Default fallback