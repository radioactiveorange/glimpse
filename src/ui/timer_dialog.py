"""Viewing settings dialog for opening collections with timer and sort override options."""

from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QRadioButton,
    QSpinBox,
    QButtonGroup,
    QGroupBox,
)
from .components import CenteredDialog, SortingPanel
from .styles import create_dialog_action_button


class ViewingSettingsDialog(CenteredDialog):
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
            ("5 minutes", 300),
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

            # Create collection default info text
            sort_display = {
                "random": "Random (shuffle)",
                "name": "Name (alphabetical)",
                "path": "Full path",
                "size": "File size",
                "date": "Date modified",
            }
            current_sort = sort_display.get(
                self.collection.sort_method, self.collection.sort_method
            )
            if (
                self.collection.sort_method != "random"
                and self.collection.sort_descending
            ):
                current_sort += " (descending)"
            current_info_text = f"Collection default: {current_sort}"

            # Use the reusable SortingPanel component
            self.sorting_panel = SortingPanel(
                show_current_info=True, current_info_text=current_info_text
            )

            # Set current collection values
            self.sorting_panel.set_sorting_settings(
                self.sort_method, self.sort_descending
            )

            sorting_layout.addWidget(self.sorting_panel)
            layout.addWidget(sorting_group)

        # Connect signals
        self.custom_radio.toggled.connect(self.custom_spinbox.setEnabled)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_button = create_dialog_action_button(
            "Start Viewing", primary=True, icon_name="ok"
        )
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

        # Use the SortingPanel to get settings
        return self.sorting_panel.get_sorting_settings()
