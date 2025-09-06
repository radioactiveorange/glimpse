"""Reusable sorting panel widget for collections and viewing settings."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from PySide6.QtCore import Qt, Signal


class SortingPanel(QWidget):
    """Reusable sorting panel with method and order selection.
    
    Eliminates duplicate sorting UI code across collection_dialog.py and timer_dialog.py.
    """
    
    # Signals
    sort_method_changed = Signal(str)  # Emits sort method string
    sort_order_changed = Signal(bool)  # Emits True for descending, False for ascending
    
    def __init__(self, parent=None, show_current_info=False, current_info_text=""):
        super().__init__(parent)
        self.show_current_info = show_current_info
        
        # Sort method mapping
        self.sort_methods = ["random", "name", "path", "size", "date"]
        self.sort_method_labels = [
            "Random (shuffle)",
            "Name (alphabetical)", 
            "Full path",
            "File size",
            "Date modified"
        ]
        
        self.init_ui()
        if show_current_info and current_info_text:
            self.set_current_info(current_info_text)
    
    def init_ui(self):
        """Initialize the sorting panel UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Show current collection settings if requested
        if self.show_current_info:
            self.current_info_label = QLabel()
            self.current_info_label.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 5px;")
            layout.addWidget(self.current_info_label)
        
        # Sort method row
        sort_method_layout = QHBoxLayout()
        sort_method_layout.setSpacing(10)
        
        sort_by_label = QLabel("Sort by:")
        sort_by_label.setMinimumWidth(60)
        sort_method_layout.addWidget(sort_by_label)
        
        self.sort_method_combo = QComboBox()
        self.sort_method_combo.addItems(self.sort_method_labels)
        self.sort_method_combo.setMinimumWidth(160)
        sort_method_layout.addWidget(self.sort_method_combo)
        
        sort_method_layout.addStretch()
        layout.addLayout(sort_method_layout)
        
        # Sort order row
        sort_order_layout = QHBoxLayout()
        sort_order_layout.setSpacing(10)
        
        sort_order_label = QLabel("Order:")
        sort_order_label.setMinimumWidth(60)
        self.sort_order_label = sort_order_label  # Store reference for updating text
        sort_order_layout.addWidget(sort_order_label)
        
        self.sort_order_combo = QComboBox()
        self.sort_order_combo.addItems(["Ascending", "Descending"])
        self.sort_order_combo.setMinimumWidth(160)
        
        # Set custom styling for disabled state
        disabled_style = """
            QComboBox:disabled {
                background-color: #1e1e1e;
                color: #666666;
                border: 1px solid #333333;
            }
        """
        self.sort_order_combo.setStyleSheet(disabled_style)
        sort_order_layout.addWidget(self.sort_order_combo)
        
        sort_order_layout.addStretch()
        layout.addLayout(sort_order_layout)
        
        # Connect signals
        self.sort_method_combo.currentIndexChanged.connect(self._on_sort_method_changed)
        self.sort_order_combo.currentIndexChanged.connect(self._on_sort_order_changed)
        
        # Initialize state
        self._on_sort_method_changed()
    
    def _on_sort_method_changed(self):
        """Handle sort method change."""
        # Disable sort order combo for random sort
        is_random = self.sort_method_combo.currentIndex() == 0
        self.sort_order_combo.setEnabled(not is_random)
        
        if is_random:
            self.sort_order_combo.setCurrentIndex(0)  # Reset to ascending
            # Also update the label to show it's not applicable
            self.sort_order_label.setText("Order: (N/A)")
        else:
            self.sort_order_label.setText("Order:")
        
        # Emit signal
        sort_method = self.sort_methods[self.sort_method_combo.currentIndex()]
        self.sort_method_changed.emit(sort_method)
    
    def _on_sort_order_changed(self):
        """Handle sort order change."""
        is_descending = self.sort_order_combo.currentIndex() == 1
        self.sort_order_changed.emit(is_descending)
    
    # Public API methods
    def set_sort_method(self, sort_method):
        """Set the current sort method."""
        if sort_method in self.sort_methods:
            index = self.sort_methods.index(sort_method)
            self.sort_method_combo.setCurrentIndex(index)
    
    def set_sort_order(self, descending):
        """Set the sort order. True for descending, False for ascending."""
        self.sort_order_combo.setCurrentIndex(1 if descending else 0)
    
    def get_sort_method(self):
        """Get the currently selected sort method."""
        return self.sort_methods[self.sort_method_combo.currentIndex()]
    
    def get_sort_order(self):
        """Get the current sort order. Returns True for descending, False for ascending."""
        return self.sort_order_combo.currentIndex() == 1
    
    def get_sorting_settings(self):
        """Get both sort method and order as a tuple (method, descending)."""
        return self.get_sort_method(), self.get_sort_order()
    
    def set_sorting_settings(self, sort_method, sort_descending):
        """Set both sort method and order."""
        self.set_sort_method(sort_method)
        self.set_sort_order(sort_descending)
    
    def set_current_info(self, info_text):
        """Set the current collection info text (if show_current_info is True)."""
        if self.show_current_info and hasattr(self, 'current_info_label'):
            self.current_info_label.setText(info_text)
    
    def reset_to_random(self):
        """Reset to random sorting (useful for new collections)."""
        self.sort_method_combo.setCurrentIndex(0)  # Random
        self.sort_order_combo.setCurrentIndex(0)   # Ascending (disabled anyway)