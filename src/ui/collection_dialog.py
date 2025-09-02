"""Collection creation and editing dialog with comprehensive settings."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QRadioButton, QSpinBox, QButtonGroup, QGroupBox, QApplication,
    QComboBox, QCheckBox, QListWidget, QListWidgetItem, QLineEdit,
    QFileDialog, QMessageBox, QSplitter, QTextEdit
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QTimer
from .styles import create_dialog_action_button, create_standard_button
from ..core.collections import Collection
from ..core.image_utils import create_professional_icon


class CollectionDialog(QDialog):
    """Comprehensive dialog for creating and editing collections with all settings."""
    
    def __init__(self, parent=None, collection=None):
        super().__init__(parent)
        self.collection = collection  # If provided, we're editing
        self.is_editing = collection is not None
        
        self.setWindowTitle("Edit Collection" if self.is_editing else "New Collection")
        self.setModal(True)
        self.resize(650, 500)
        
        # Initialize values
        self.collection_name = collection.name if collection else ""
        self.folder_paths = collection.paths[:] if collection else []
        self.sort_method = collection.sort_method if collection else "random"
        self.sort_descending = collection.sort_descending if collection else False
        self.timer_enabled = False
        self.timer_interval = 60
        
        self.init_ui()
        self.populate_existing_data()
    
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
        
        # Main content in splitter
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter, 1)
        
        # Left side - Collection basics and folders
        left_widget = QGroupBox("Collection Details")
        left_layout = QVBoxLayout(left_widget)
        
        # Collection name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter collection name...")
        self.name_edit.setMinimumHeight(32)  # Match standard button height
        name_layout.addWidget(self.name_edit)
        left_layout.addLayout(name_layout)
        
        # Folders section
        folders_label = QLabel("Folders:")
        folders_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        left_layout.addWidget(folders_label)
        
        # Folders list
        self.folders_list = QListWidget()
        self.folders_list.setMinimumHeight(150)
        self.folders_list.setToolTip("List of folders in this collection")
        # Apply consistent styling to match the collections list
        self.folders_list.setStyleSheet("""
            QListWidget {
                outline: none;
                show-decoration-selected: 1;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #35383b;
                min-height: 20px;
            }
            QListWidget::item:hover {
                background-color: #2e3034;
            }
            QListWidget::item:selected {
                background-color: #354e6e;
                color: white;
            }
        """)
        left_layout.addWidget(self.folders_list)
        
        # Folder buttons
        folder_buttons_layout = QHBoxLayout()
        
        self.add_folder_btn = create_standard_button("Add Folder", "add")
        self.add_folder_btn.clicked.connect(self.add_folder)
        folder_buttons_layout.addWidget(self.add_folder_btn)
        
        self.remove_folder_btn = create_standard_button("Remove", "delete")
        self.remove_folder_btn.setEnabled(False)
        self.remove_folder_btn.clicked.connect(self.remove_folder)
        folder_buttons_layout.addWidget(self.remove_folder_btn)
        
        folder_buttons_layout.addStretch()
        left_layout.addLayout(folder_buttons_layout)
        
        main_splitter.addWidget(left_widget)
        
        # Right side - Settings
        right_widget = QGroupBox("Settings")
        right_layout = QVBoxLayout(right_widget)
        
        # Sorting options
        sorting_group = QGroupBox("Image Sorting")
        sorting_layout = QVBoxLayout(sorting_group)
        
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
        
        right_layout.addWidget(sorting_group)
        
        # Timer settings (show for both creation and editing)
        if True:  # Always show timer settings
            timer_group = QGroupBox("Default Timer Settings")
            timer_layout = QVBoxLayout(timer_group)
            
            timer_info = QLabel("Set default timer settings for this collection.\nYou can change these when opening the collection.")
            timer_info.setStyleSheet("color: #666; font-size: 11px;")
            timer_info.setWordWrap(True)
            timer_layout.addWidget(timer_info)
            
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
            
            # Connect signals
            self.custom_radio.toggled.connect(self.custom_spinbox.setEnabled)
            
            right_layout.addWidget(timer_group)
        
        right_layout.addStretch()
        main_splitter.addWidget(right_widget)
        
        # Set splitter proportions
        main_splitter.setSizes([350, 250])
        
        # Connect signals
        self.folders_list.itemSelectionChanged.connect(self.on_folder_selection_changed)
        
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
        on_sort_method_changed()  # Initialize state
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        if self.is_editing:
            save_button = create_dialog_action_button("Save Changes", primary=True, icon_name="ok")
            save_button.clicked.connect(self.accept)
        else:
            save_button = create_dialog_action_button("Create Collection", primary=True, icon_name="ok")
            save_button.clicked.connect(self.accept)
        
        button_layout.addWidget(save_button)
        
        cancel_button = create_dialog_action_button("Cancel", icon_name="cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def populate_existing_data(self):
        """Populate the dialog with existing collection data if editing."""
        if not self.is_editing:
            return
        
        # Set collection name
        self.name_edit.setText(self.collection_name)
        
        # Populate folders
        for folder_path in self.folder_paths:
            self.add_folder_to_list(folder_path)
        
        # Set sorting options
        sort_methods = ["random", "name", "path", "size", "date"]
        if self.sort_method in sort_methods:
            self.sort_method_combo.setCurrentIndex(sort_methods.index(self.sort_method))
        
        # Set sort order combo state
        self.sort_order_combo.setCurrentIndex(1 if self.sort_descending else 0)
    
    def add_folder_to_list(self, folder_path):
        """Add a folder to the list widget."""
        item = QListWidgetItem()
        item.setText(folder_path)
        item.setToolTip(folder_path)
        self.folders_list.addItem(item)
    
    def add_folder(self):
        """Add a new folder to the collection."""
        folder = QFileDialog.getExistingDirectory(self, "Select folder to add")
        if folder:
            # Check if folder already exists
            for i in range(self.folders_list.count()):
                if self.folders_list.item(i).text() == folder:
                    QMessageBox.information(self, "Folder Already Added", 
                                          "This folder is already part of the collection.")
                    return
            
            self.add_folder_to_list(folder)
            self.folder_paths.append(folder)
    
    def remove_folder(self):
        """Remove the selected folder from the collection."""
        current = self.folders_list.currentItem()
        if current:
            folder_path = current.text()
            reply = QMessageBox.question(self, "Remove Folder", 
                                       f"Remove this folder from the collection?\n\n{folder_path}")
            
            if reply == QMessageBox.Yes:
                row = self.folders_list.row(current)
                self.folders_list.takeItem(row)
                if folder_path in self.folder_paths:
                    self.folder_paths.remove(folder_path)
    
    def on_folder_selection_changed(self):
        """Handle folder list selection changes."""
        has_selection = bool(self.folders_list.currentItem())
        self.remove_folder_btn.setEnabled(has_selection)
    
    
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
        # Map combo box indices to sort method strings
        sort_methods = ["random", "name", "path", "size", "date"]
        sort_method = sort_methods[self.sort_method_combo.currentIndex()]
        sort_descending = self.sort_order_combo.currentIndex() == 1
        
        return sort_method, sort_descending
    
    def get_collection_data(self):
        """Get all collection data from the dialog."""
        name = self.name_edit.text().strip()
        if not name:
            raise ValueError("Collection name cannot be empty")
        
        if not self.folder_paths:
            raise ValueError("Collection must have at least one folder")
        
        sort_method, sort_descending = self.get_sorting_settings()
        
        return {
            'name': name,
            'paths': self.folder_paths[:],
            'sort_method': sort_method,
            'sort_descending': sort_descending
        }
    
    def accept(self):
        """Override accept to validate data."""
        try:
            self.get_collection_data()
            super().accept()
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", str(e))