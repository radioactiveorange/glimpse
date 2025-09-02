"""Viewing settings dialog for opening collections with timer and sort override options."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QRadioButton, QSpinBox, QButtonGroup, QGroupBox, QApplication,
    QComboBox, QCheckBox
)
from PySide6.QtCore import Qt, QTimer
from .styles import create_dialog_action_button, create_standard_button
from ..core.image_utils import create_professional_icon


class ViewingSettingsDialog(QDialog):
    """Dialog for configuring viewing settings when opening a collection."""
    
    def __init__(self, parent=None, collection=None):
        super().__init__(parent)
        self.setWindowTitle("Viewing Settings")
        self.setModal(True)
        self.resize(450, 300)
        
        self.collection = collection
        self.timer_enabled = False
        self.timer_interval = 60  # Default 60 seconds
        
        # Pre-populate with collection settings if provided
        if collection:
            self.sort_method = collection.sort_method
            self.sort_descending = collection.sort_descending
        else:
            self.sort_method = "random"
            self.sort_descending = False
        
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
        self.custom_spinbox.setMinimumHeight(32)  # Match standard button height
        custom_layout.addWidget(self.custom_spinbox)
        
        custom_layout.addStretch()
        timer_layout.addLayout(custom_layout)
        
        layout.addWidget(timer_group)
        
        # Sorting options (override collection defaults)
        if self.collection:
            sorting_group = QGroupBox("Image Sorting (Override Collection Settings)")
            sorting_layout = QVBoxLayout(sorting_group)
            
            # Show current collection settings
            sort_display = {
                "random": "Random (shuffle)",
                "name": "Name (alphabetical)",
                "path": "Full path",
                "size": "File size",
                "date": "Date modified"
            }
            current_sort = sort_display.get(self.collection.sort_method, self.collection.sort_method)
            if self.collection.sort_method != "random" and self.collection.sort_descending:
                current_sort += " (descending)"
            
            current_info = QLabel(f"Collection default: {current_sort}")
            current_info.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 5px;")
            sorting_layout.addWidget(current_info)
            
            # Sort method row
            sort_method_layout = QHBoxLayout()
            sort_method_layout.setSpacing(10)
            
            sort_by_label = QLabel("Sort by:")
            sort_by_label.setMinimumWidth(60)
            sort_method_layout.addWidget(sort_by_label)
            
            self.sort_method_combo = QComboBox()
            self.sort_method_combo.addItems([
                "Random (shuffle)",
                "Name (alphabetical)",
                "Full path",
                "File size",
                "Date modified"
            ])
            self.sort_method_combo.setCurrentIndex(0)  # Default to random
            self.sort_method_combo.setMinimumWidth(160)
            sort_method_layout.addWidget(self.sort_method_combo)
            
            sort_method_layout.addStretch()
            sorting_layout.addLayout(sort_method_layout)
            
            # Sort order row
            sort_order_layout = QHBoxLayout()
            sort_order_layout.setSpacing(10)
            
            sort_order_label = QLabel("Order:")
            # Store reference for updating text
            sort_order_label.setMinimumWidth(60)
            sort_order_layout.addWidget(sort_order_label)
            
            self.sort_order_combo = QComboBox()
            self.sort_order_combo.addItems(["Ascending", "Descending"])
            self.sort_order_combo.setMinimumWidth(160)
            # Set custom styling for disabled state
            self.sort_order_combo.setStyleSheet("""
                QComboBox:disabled {
                    background-color: #1e1e1e;
                    color: #666666;
                    border: 1px solid #333333;
                }
            """)
            sort_order_layout.addWidget(self.sort_order_combo)
            
            sort_order_layout.addStretch()
            sorting_layout.addLayout(sort_order_layout)
            
            # Connect sort method combo to enable/disable sort order combo
            def on_sort_method_changed():
                # Disable sort order combo for random sort
                is_random = self.sort_method_combo.currentIndex() == 0
                self.sort_order_combo.setEnabled(not is_random)
                if is_random:
                    self.sort_order_combo.setCurrentIndex(0)  # Reset to ascending
                    # Also update the label to show it's not applicable
                    sort_order_label.setText("Order: (N/A)")
                else:
                    sort_order_label.setText("Order:")
            
            self.sort_method_combo.currentIndexChanged.connect(on_sort_method_changed)
            
            # Set current collection values
            sort_methods = ["random", "name", "path", "size", "date"]
            if self.sort_method in sort_methods:
                self.sort_method_combo.setCurrentIndex(sort_methods.index(self.sort_method))
            self.sort_order_combo.setCurrentIndex(1 if self.sort_descending else 0)
            
            on_sort_method_changed()  # Initialize state
            
            layout.addWidget(sorting_group)
        
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
    
    
    def get_sorting_settings(self):
        """Get the selected sorting settings."""
        if not self.collection:
            return "random", False
        
        # Map combo box indices to sort method strings
        sort_methods = ["random", "name", "path", "size", "date"]
        sort_method = sort_methods[self.sort_method_combo.currentIndex()]
        sort_descending = self.sort_order_combo.currentIndex() == 1
        
        return sort_method, sort_descending