"""Startup dialog for collection management and quick folder access."""

import os
import sys
import subprocess
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, 
    QListWidgetItem, QFileDialog, QInputDialog, QMessageBox, QWidget,
    QSplitter, QTextEdit, QGroupBox, QSizePolicy, QApplication
)
from PySide6.QtGui import QFont, QDesktopServices
from PySide6.QtCore import Qt, Signal, QTimer, QUrl

from ..core.collections import CollectionManager, Collection
from ..core.image_utils import create_professional_icon
from .timer_dialog import TimerConfigDialog
from .loading_dialog import LoadingDialog
from .styles import create_standard_button, create_dialog_action_button
from ..version import get_version

class StartupDialog(QDialog):
    """Startup dialog for managing collections and quick folder access."""
    
    # Signals to communicate with main application
    collection_selected = Signal(object)  # Emits tuple: (Collection, timer_enabled, timer_interval)
    folder_selected = Signal(object)  # Emits tuple: (folder_path, timer_enabled, timer_interval)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.collection_manager = CollectionManager()
        self.setWindowTitle(f"Glimpse v{get_version()}")
        self.setModal(True)
        self.resize(800, 600)
        
        self.init_ui()
        self.refresh_collections()
        # Ensure no item is selected by default
        self.collections_list.clearSelection()
    
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
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Compact header section
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(4)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("Glimpse")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Get random glimpses of your image collections")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666; font-size: 11px;")
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header_widget)
        
        # Main content area - give it more space
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter, 1)  # Stretch factor of 1
        
        # Left side - Collections
        collections_widget = QWidget()
        collections_layout = QVBoxLayout(collections_widget)
        collections_layout.setContentsMargins(0, 0, 10, 0)
        
        # Custom collections group with title bar
        collections_group = QWidget()
        collections_group.setStyleSheet("""
            QWidget {
                border: 1px solid #35383b;
                border-radius: 4px;
                background-color: #232629;
            }
        """)
        collections_group_layout = QVBoxLayout(collections_group)
        collections_group_layout.setContentsMargins(8, 8, 8, 8)
        
        # Collections title bar with location button
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 8)
        
        title_label = QLabel("Collections")
        title_label.setStyleSheet("font-weight: bold; color: #b7bcc1; border: none; background: none;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        self.show_location_btn = create_standard_button("", "folder")
        self.show_location_btn.setToolTip("Show collections folder location")
        self.show_location_btn.setFixedSize(28, 28)
        self.show_location_btn.clicked.connect(self.show_collections_location)
        title_layout.addWidget(self.show_location_btn)
        
        collections_group_layout.addLayout(title_layout)
        
        # Collections list
        self.collections_list = QListWidget()
        self.collections_list.setMinimumHeight(300)  # Increased from 200 for easier selection
        self.collections_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.collections_list.itemDoubleClicked.connect(self.on_collection_double_clicked)
        self.collections_list.itemClicked.connect(self.on_collection_selected)
        
        # Improve list item spacing and appearance - fixed version
        self.collections_list.setStyleSheet("""
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
        
        collections_group_layout.addWidget(self.collections_list)
        
        # Collection buttons
        collection_buttons_layout = QHBoxLayout()
        
        self.new_collection_btn = create_standard_button("New Collection", "add")
        self.new_collection_btn.clicked.connect(self.create_new_collection)
        collection_buttons_layout.addWidget(self.new_collection_btn)
        
        self.edit_collection_btn = create_standard_button("Edit", "edit")
        self.edit_collection_btn.setEnabled(False)
        self.edit_collection_btn.clicked.connect(self.edit_selected_collection)
        collection_buttons_layout.addWidget(self.edit_collection_btn)
        
        self.delete_collection_btn = create_standard_button("Delete", "delete")
        self.delete_collection_btn.setEnabled(False)
        self.delete_collection_btn.clicked.connect(self.delete_selected_collection)
        collection_buttons_layout.addWidget(self.delete_collection_btn)
        
        collections_group_layout.addLayout(collection_buttons_layout)
        collections_layout.addWidget(collections_group)
        
        # Right side - Quick options and details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        # Quick shuffle group
        quick_group = QGroupBox("Quick Start")
        quick_layout = QVBoxLayout(quick_group)
        
        self.quick_shuffle_btn = create_standard_button("Quick Shuffle Folder", "shuffle", large=True)
        self.quick_shuffle_btn.clicked.connect(self.quick_shuffle_folder)
        quick_layout.addWidget(self.quick_shuffle_btn)
        
        quick_desc = QLabel("Quickly start viewing images from a single folder")
        quick_desc.setWordWrap(True)
        quick_desc.setStyleSheet("color: #666; font-size: 11px; margin-top: 5px;")
        quick_layout.addWidget(quick_desc)
        
        right_layout.addWidget(quick_group)
        
        # Collection details - expand to fill available space
        details_group = QGroupBox("Collection Details")
        details_layout = QVBoxLayout(details_group)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMinimumHeight(120)
        self.details_text.setPlaceholderText("Select a collection to view details")
        details_layout.addWidget(self.details_text)
        
        right_layout.addWidget(details_group, 1)  # Give it stretch factor
        
        # Set splitter proportions
        main_splitter.addWidget(collections_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([400, 400])
        
        # Bottom buttons with less spacing
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 8, 0, 0)
        bottom_layout.addStretch()
        
        self.open_collection_btn = create_dialog_action_button("Open Collection", primary=True, icon_name="play")
        self.open_collection_btn.setEnabled(False)
        self.open_collection_btn.clicked.connect(self.open_selected_collection)
        bottom_layout.addWidget(self.open_collection_btn)
        
        cancel_btn = create_dialog_action_button("Cancel", icon_name="cancel")
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)
        
        layout.addLayout(bottom_layout)
    
    def refresh_collections(self):
        """Refresh the collections list."""
        self.collections_list.clear()
        collections = self.collection_manager.get_all_collections()
        
        for collection in collections:
            item = QListWidgetItem()
            item.setText(f"{collection.name}")
            item.setData(Qt.UserRole, collection)
            
            # Add subtitle with path count and image count
            subtitle = f"{len(collection.paths)} folder{'s' if len(collection.paths) != 1 else ''}, {collection.image_count} images"
            item.setToolTip(f"{collection.name}\n{subtitle}")
            
            self.collections_list.addItem(item)
        
        # Show message if no collections
        if not collections:
            item = QListWidgetItem("No collections found. Create your first collection!")
            item.setFlags(Qt.NoItemFlags)  # Make it non-selectable
            self.collections_list.addItem(item)
    
    def on_collection_selected(self, item):
        """Handle collection selection."""
        collection = item.data(Qt.UserRole)
        if collection:
            self.open_collection_btn.setEnabled(True)
            self.edit_collection_btn.setEnabled(True)
            self.delete_collection_btn.setEnabled(True)
            
            # Update details
            details = f"<b>{collection.name}</b><br><br>"
            details += f"<b>Folders:</b> {len(collection.paths)}<br>"
            details += f"<b>Total Images:</b> {collection.image_count}<br>"
            if collection.last_used:
                from datetime import datetime
                try:
                    last_used = datetime.fromisoformat(collection.last_used)
                    details += f"<b>Last Used:</b> {last_used.strftime('%B %d, %Y at %I:%M %p')}<br>"
                except:
                    pass
            if collection.created_date:
                try:
                    created = datetime.fromisoformat(collection.created_date)
                    details += f"<b>Created:</b> {created.strftime('%B %d, %Y')}<br>"
                except:
                    pass
            
            details += "<br><b>Folders:</b><br>"
            for path in collection.paths:
                details += f"• {path}<br>"
            
            self.details_text.setHtml(details)
        else:
            self.open_collection_btn.setEnabled(False)
            self.edit_collection_btn.setEnabled(False)
            self.delete_collection_btn.setEnabled(False)
            self.details_text.clear()
    
    def on_collection_double_clicked(self, item):
        """Handle double-click on collection item."""
        collection = item.data(Qt.UserRole)
        if collection:
            self.open_selected_collection()
    
    def create_new_collection(self):
        """Create a new collection."""
        name, ok = QInputDialog.getText(self, "New Collection", "Collection name:")
        if not ok or not name.strip():
            return
        
        name = name.strip()
        if self.collection_manager.collection_exists(name):
            QMessageBox.warning(self, "Collection Exists", 
                              f"A collection named '{name}' already exists.")
            return
        
        # Select folders with better UX
        folders = []
        
        # Start with first folder
        first_folder = QFileDialog.getExistingDirectory(self, f"Select first folder for '{name}'")
        if not first_folder:
            return
        
        folders.append(first_folder)
        
        # Ask if user wants to add more folders
        while True:
            reply = QMessageBox.question(self, "Add Another Folder?", 
                                       f"Collection '{name}' currently has {len(folders)} folder(s).\n\n"
                                       f"Would you like to add another folder?",
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                additional_folder = QFileDialog.getExistingDirectory(self, f"Select additional folder for '{name}'")
                if additional_folder and additional_folder not in folders:
                    folders.append(additional_folder)
                elif additional_folder in folders:
                    QMessageBox.information(self, "Folder Already Added", 
                                          "This folder is already part of the collection.")
            else:
                break
        
        # Create collection with loading dialog for large collections
        self._create_collection_with_loading(name, folders)
    
    def _create_collection_with_loading(self, name: str, folders: list):
        """Create collection with loading dialog for progress indication."""
        # First create the collection without image count
        if self.collection_manager.collection_exists(name):
            QMessageBox.critical(self, "Error", "Collection already exists.")
            return
        
        # Show loading dialog for image counting
        loading_dialog = LoadingDialog(folders, self)
        
        if loading_dialog.exec() == QDialog.Accepted:
            # Get the loaded images and create collection
            images = loading_dialog.get_images()
            collection = Collection(name, folders)
            collection.image_count = len(images)
            
            if self.collection_manager.save_collection(collection):
                self.refresh_collections()
                # Select the new collection
                for i in range(self.collections_list.count()):
                    item = self.collections_list.item(i)
                    if item.data(Qt.UserRole) and item.data(Qt.UserRole).name == name:
                        self.collections_list.setCurrentItem(item)
                        self.on_collection_selected(item)
                        break
            else:
                QMessageBox.critical(self, "Error", "Failed to create collection.")
        # If dialog was cancelled, just return without creating collection
    
    def edit_selected_collection(self):
        """Edit the selected collection."""
        current = self.collections_list.currentItem()
        if not current:
            return
        
        collection = current.data(Qt.UserRole)
        if not collection:
            return
        
        # Edit name
        new_name, ok = QInputDialog.getText(self, "Edit Collection", 
                                          "Collection name:", text=collection.name)
        if not ok or not new_name.strip():
            return
        
        new_name = new_name.strip()
        
        # Check if name changed and if new name exists
        if new_name != collection.name and self.collection_manager.collection_exists(new_name):
            QMessageBox.warning(self, "Collection Exists", 
                              f"A collection named '{new_name}' already exists.")
            return
        
        # If name changed, delete old and create new
        old_name = collection.name
        collection.name = new_name
        
        if old_name != new_name:
            self.collection_manager.delete_collection(old_name)
        
        # Update and save
        collection.update_image_count()
        self.collection_manager.save_collection(collection)
        self.refresh_collections()
    
    def delete_selected_collection(self):
        """Delete the selected collection."""
        current = self.collections_list.currentItem()
        if not current:
            return
        
        collection = current.data(Qt.UserRole)
        if not collection:
            return
        
        reply = QMessageBox.question(self, "Delete Collection", 
                                   f"Are you sure you want to delete '{collection.name}'?\n\n"
                                   f"This will only remove the collection, not the actual image files.")
        
        if reply == QMessageBox.Yes:
            if self.collection_manager.delete_collection(collection.name):
                self.refresh_collections()
                # Clear details panel and disable buttons
                self.details_text.clear()
                self.open_collection_btn.setEnabled(False)
                self.edit_collection_btn.setEnabled(False)
                self.delete_collection_btn.setEnabled(False)
            else:
                QMessageBox.critical(self, "Error", "Failed to delete collection.")
    
    def open_selected_collection(self):
        """Open the selected collection with timer configuration."""
        current = self.collections_list.currentItem()
        if not current:
            return
        
        collection = current.data(Qt.UserRole)
        if collection:
            # Show timer configuration dialog
            timer_dialog = TimerConfigDialog(self)
            if timer_dialog.exec() == QDialog.Accepted:
                timer_enabled, timer_interval = timer_dialog.get_timer_settings()
                
                collection.mark_as_used()
                self.collection_manager.save_collection(collection)
                
                # Emit collection with timer settings
                self.collection_selected.emit((collection, timer_enabled, timer_interval))
                self.accept()
            # If timer dialog was cancelled, just return (keep startup dialog open)
    
    def show_collections_location(self):
        """Open the collections directory in the system file manager."""
        collections_dir = self.collection_manager.collections_dir
        
        # Ensure the directory exists
        if not os.path.exists(collections_dir):
            os.makedirs(collections_dir, exist_ok=True)
        
        # Try to open in file manager using cross-platform approach
        try:
            if sys.platform == "win32":
                # Windows - use explorer
                subprocess.run(["explorer", collections_dir], check=True)
            elif sys.platform == "darwin":
                # macOS - use Finder
                subprocess.run(["open", collections_dir], check=True)
            else:
                # Linux - try common file managers
                file_managers = ["xdg-open", "nautilus", "dolphin", "thunar", "pcmanfm"]
                for fm in file_managers:
                    try:
                        subprocess.run([fm, collections_dir], check=True)
                        break
                    except (subprocess.SubprocessError, FileNotFoundError):
                        continue
                else:
                    # Fallback to Qt's desktop services
                    QDesktopServices.openUrl(QUrl.fromLocalFile(collections_dir))
        except Exception as e:
            # Fallback to showing a message with the path
            QMessageBox.information(
                self, 
                "Collections Location", 
                f"Collections are stored in:\n{collections_dir}\n\n"
                f"(Could not open file manager: {str(e)})"
            )
    
    def quick_shuffle_folder(self):
        """Quick shuffle a single folder with timer configuration."""
        folder = QFileDialog.getExistingDirectory(self, "Select folder to shuffle")
        if folder:
            # Show timer configuration dialog
            timer_dialog = TimerConfigDialog(self)
            if timer_dialog.exec() == QDialog.Accepted:
                timer_enabled, timer_interval = timer_dialog.get_timer_settings()
                
                # Emit folder with timer settings
                self.folder_selected.emit((folder, timer_enabled, timer_interval))
                self.accept()
            # If timer dialog was cancelled, just return (keep startup dialog open)
        # If folder dialog was cancelled, just return (keep startup dialog open)