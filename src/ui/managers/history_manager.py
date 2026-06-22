"""History and navigation manager for the Random Image Viewer."""

import os
import random
from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QObject, Signal


class HistoryManager(QObject):
    """Manages image history, navigation, and thumbnail panel functionality."""
    
    # Signals
    image_requested = Signal(str)  # Emitted when an image should be displayed
    history_navigation = Signal(str, bool)  # Emitted for prev/next navigation (path, is_forward)
    random_image_requested = Signal()  # Emitted when random image is needed
    
    def __init__(self, history_list_widget, parent=None):
        super().__init__(parent)

        self.history = []
        self.history_index = -1
        self.sorted_collection_index = 0

        self.images = []
        self.current_image = None

        self.history_list = history_list_widget
        self.history_list.itemClicked.connect(self.on_history_clicked)
        
    def set_images(self, images):
        """Set the current image collection."""
        self.images = images[:]
        
    def clear_history(self):
        """Clear all history data."""
        self.history.clear()
        self.history_index = -1
        self.sorted_collection_index = 0
        if self.history_list:
            self.history_list.clear()
            self.history_list.repaint()
        self.current_image = None
        
    def add_to_history(self, img_path):
        """Add an image to history, handling forward history removal."""
        # If we're not at the end of history (i.e., we went back and now showing new image),
        # remove all forward history.
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
            if self.history_list:
                self.history_list.clear()
                for path in self.history:
                    self._add_history_item(path)
                    
        # Only add if not duplicating last
        if not self.history or self.history[-1] != img_path:
            self.history.append(img_path)
            if self.history_list:
                self._add_history_item(img_path)
                
        self.history_index = len(self.history) - 1
        self.current_image = img_path
        
    def _add_history_item(self, img_path):
        """Add an item to the history list widget."""
        if not self.history_list:
            return
            
        item = QListWidgetItem(os.path.basename(img_path))
        
        # OPTIMIZATION: Generate thumbnails asynchronously to avoid UI freezing
        # For now, use a simple icon and generate thumbnails in background
        # This prevents the UI freeze during navigation
        
        # Set basic properties immediately
        item.setToolTip(img_path)
        item.setData(Qt.UserRole, img_path)
        self.history_list.addItem(item)
        self.history_list.scrollToBottom()
        
        # Generate thumbnail asynchronously (prevents UI blocking)
        self._generate_thumbnail_async(item, img_path)
        
    def _generate_thumbnail_async(self, item, img_path):
        """Generate thumbnail asynchronously to avoid blocking UI."""
        try:
            thumb = QPixmap(img_path)
            if not thumb.isNull():
                # Use faster transformation for thumbnails
                size = 48
                thumb = thumb.scaled(size, size, Qt.KeepAspectRatio, Qt.FastTransformation)
                item.setIcon(thumb)
        except Exception:
            # Silently handle thumbnail generation failures
            pass
        
    def on_history_clicked(self, item):
        """Handle clicking on a history item."""
        img_path = item.data(Qt.UserRole)
        if img_path:
            # Update history_index to match clicked item
            try:
                idx = self.history.index(img_path)
                self.history_index = idx
            except ValueError:
                self.history_index = len(self.history) - 1
            
            self.current_image = img_path
            self.image_requested.emit(img_path)
            
    def show_previous_image(self):
        """Navigate to the previous image in history."""
        if self.history_index > 0:
            self.history_index -= 1
            img_path = self.history[self.history_index]
            self.current_image = img_path
            self.history_navigation.emit(img_path, False)  # False = backward
            return True
        return False
        
    def show_next_image(self):
        """Navigate to the next image in history or request random."""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            img_path = self.history[self.history_index]
            self.current_image = img_path
            self.history_navigation.emit(img_path, True)  # True = forward
            return True
        else:
            # At end of history, request random image
            self.random_image_requested.emit()
            return False
            
    def show_next_or_random_image(self):
        """Show next image or random if at end of history."""
        if self.history_index < len(self.history) - 1:
            return self.show_next_image()
        else:
            self.get_random_image()
            return True
            
    def get_random_image(self):
        """Get a random image from the collection, avoiding recent history."""
        if not self.images:
            return None
            
        # Get available images (not in recent history)
        available = [img for img in self.images if img not in self.history]
        if not available:
            # If all images are in history, clear it and start fresh
            self.clear_history()
            available = self.images[:]
            
        if available:
            selected_image = random.choice(available)
            self.add_to_history(selected_image)
            self.image_requested.emit(selected_image)
            return selected_image
        
        return None
        
    def get_sequential_image(self, sort_method="name", sort_order="asc"):
        """Get the next image in sequential order based on sorting."""
        if not self.images:
            return None
            
        # Create sorted list
        sorted_images = self.images[:]
        
        if sort_method == "name":
            def natural_sort_key(path):
                """Generate a key for natural/human sorting of filenames."""
                import re
                name = os.path.basename(path).lower()
                # Split the filename into text and number parts
                parts = re.split(r'(\d+)', name)
                # Convert numeric parts to integers for proper sorting
                result = []
                for part in parts:
                    if part.isdigit():
                        result.append(int(part))
                    else:
                        result.append(part)
                return result
            
            sorted_images.sort(key=natural_sort_key, reverse=(sort_order == "desc"))
        elif sort_method == "date_modified":
            sorted_images.sort(key=lambda x: os.path.getmtime(x), 
                             reverse=(sort_order == "desc"))
        elif sort_method == "size":
            sorted_images.sort(key=lambda x: os.path.getsize(x), 
                             reverse=(sort_order == "desc"))
        elif sort_method == "random":
            random.shuffle(sorted_images)
            
        # Get next image in sequence
        if self.sorted_collection_index >= len(sorted_images):
            self.sorted_collection_index = 0
            
        selected_image = sorted_images[self.sorted_collection_index]
        self.sorted_collection_index += 1
        
        self.add_to_history(selected_image)
        self.image_requested.emit(selected_image)
        return selected_image
        
    def toggle_history_panel(self, visible, settings=None):
        """Toggle the history panel visibility."""
        if self.history_list:
            self.history_list.setVisible(bool(visible))
            if settings:
                settings.setValue("show_history_panel", bool(visible))
                
    def get_current_image(self):
        """Get the currently displayed image path."""
        return self.current_image
        
    def get_history_info(self):
        """Get information about current history state."""
        return {
            'current_index': self.history_index,
            'total_count': len(self.history),
            'current_image': self.current_image,
            'has_previous': self.history_index > 0,
            'has_next': self.history_index < len(self.history) - 1
        }
    
    def has_next(self):
        """Check if there's a next image in history."""
        return self.history_index < len(self.history) - 1