"""Image display management - handles zoom, pan, transformations, and image processing."""

import os
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QPixmap, QImage, QTransform, QPainter, QColor
from PySide6.QtCore import Qt, QObject, Signal

from ...core.image_utils import set_adaptive_bg


class ImageDisplayManager(QObject):
    """Manages image display functionality including zoom, pan, transformations, and processing."""
    
    # Signals
    image_changed = Signal(str)  # Emitted when image changes
    zoom_changed = Signal(float)  # Emitted when zoom level changes
    transform_changed = Signal()  # Emitted when image transforms change
    
    def __init__(self, image_label, settings):
        super().__init__()
        self.image_label = image_label
        self.settings = settings
        
        # Image state
        self.current_image = None
        self._cached_pixmap = None
        
        # Zoom and pan state
        self.zoom_factor = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        
        # Transform state - initialize from settings
        self.is_flipped_h = False
        self.is_flipped_v = False
        self.is_grayscale = settings.value("grayscale_enabled", False, type=bool)
        
        # Image processing constants
        self.MIN_ZOOM = 0.1
        self.MAX_ZOOM = 10.0
        self.ZOOM_STEP = 0.1
    
    def display_image(self, img_path, fast_mode=False):
        """Display an image with current zoom, pan, and transform settings."""
        if not img_path or not os.path.exists(img_path):
            self.image_label.clear()
            self.image_label.setText("Image not found")
            return False
        
        # Check if image is too large for Qt
        if self._is_image_too_large(img_path):
            self.image_label.clear()
            self.image_label.setText("Image too large to display")
            return False
        
        self.current_image = img_path
        
        # Set background according to settings (skip in fast mode if no transforms)
        if not fast_mode or self.is_grayscale or self.is_flipped_h or self.is_flipped_v:
            mode = self.settings.value("bg_mode", "Black")
            if mode == "Adaptive Color":
                set_adaptive_bg(self.image_label, img_path)
            elif mode == "Gray":
                self.image_label.parentWidget().setStyleSheet("background-color: #444444;")
            else:
                self.image_label.parentWidget().setStyleSheet("background-color: #000000;")
        
        # Load and process the image
        success = self._load_and_process_image(img_path, fast_mode)
        
        if success:
            self.image_changed.emit(img_path)
        
        return success
    
    def _is_image_too_large(self, img_path):
        """Check if an image file is likely too large for Qt to handle."""
        try:
            file_size = os.path.getsize(img_path)
            # Skip files larger than 500MB - likely to cause Qt issues
            return file_size > 500 * 1024 * 1024
        except OSError:
            return False
    
    def _load_and_process_image(self, img_path, fast_mode=False):
        """Load image and apply current transforms and zoom."""
        try:
            pixmap = QPixmap(img_path)
            if pixmap.isNull():
                self.image_label.clear()
                self.image_label.setText("Failed to load image")
                return False
            
            return self._process_image_immediately(pixmap, img_path, fast_mode)
            
        except Exception as e:
            print(f"Error loading image: {e}")
            self.image_label.clear() 
            self.image_label.setText("Error loading image")
            return False
    
    def _process_image_immediately(self, pixmap, img_path, fast_mode=False):
        """Process image with transforms and display immediately."""
        try:
            # OPTIMIZATION: Use reference instead of expensive copy for caching
            # Only copy if we need to modify the pixmap
            self._cached_pixmap = pixmap
            
            # Fast mode: Skip transforms if none are active (for rapid navigation)
            if fast_mode and not (self.is_flipped_h or self.is_flipped_v or self.is_grayscale):
                # Direct display for speed
                self._update_zoom_display()
                return True
            
            # Apply transforms to cached pixmap
            transform = QTransform()
            
            if self.is_flipped_h:
                transform = transform.scale(-1, 1)
            if self.is_flipped_v:
                transform = transform.scale(1, -1)
            
            if self.is_flipped_h or self.is_flipped_v:
                self._cached_pixmap = self._cached_pixmap.transformed(transform, Qt.SmoothTransformation)
            
            # Apply grayscale if enabled
            if self.is_grayscale:
                image = self._cached_pixmap.toImage()
                image = self._apply_improved_grayscale(image)
                self._cached_pixmap = QPixmap.fromImage(image)
            
            # Update display with zoom
            self._update_zoom_display()
            return True
            
        except Exception as e:
            print(f"Error processing image: {e}")
            self.image_label.clear()
            self.image_label.setText("Error processing image")
            return False
    
    def _apply_improved_grayscale(self, image):
        """Apply improved grayscale conversion."""
        return image.convertToFormat(QImage.Format_Grayscale8)
    
    def _update_zoom_display(self):
        """Update the image display with current zoom and pan settings."""
        if not self._cached_pixmap:
            return
        
        # Get container size (label size)
        container_size = self.image_label.size()
        original_size = self._cached_pixmap.size()
        
        # Calculate target size based on zoom
        if self.zoom_factor == 1.0:
            # For zoom level 1.0, fit image to container
            target_size = original_size.scaled(container_size, Qt.KeepAspectRatio)
        else:
            # Calculate zoom from the fit-to-container size
            if original_size.width() <= container_size.width() and original_size.height() <= container_size.height():
                # Scale from original size for small images
                target_size = original_size * self.zoom_factor
            else:
                # Scale from fit-to-container size for large images
                fit_size = original_size.scaled(container_size, Qt.KeepAspectRatio)
                target_size = fit_size * self.zoom_factor
        
        # Scale the cached pixmap
        scaled = self._cached_pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Apply panning - always use canvas when there's any pan offset
        if self.pan_offset_x != 0 or self.pan_offset_y != 0:
            # Create a canvas the size of the label
            canvas = QPixmap(self.image_label.size())
            
            # Get the appropriate background color based on current mode
            bg_color = self._get_current_background_color()
            canvas.fill(bg_color)
            
            # Paint the scaled image with offset
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            
            # Calculate position to center the image with pan offset
            x = (self.image_label.width() - scaled.width()) // 2 + self.pan_offset_x
            y = (self.image_label.height() - scaled.height()) // 2 + self.pan_offset_y
            
            # Draw the scaled image at offset position
            painter.drawPixmap(x, y, scaled)
            painter.end()
            
            self.image_label.setPixmap(canvas)
        else:
            self.image_label.setPixmap(scaled)
    
    def _get_current_background_color(self):
        """Get the current background color as QColor based on the active mode."""
        mode = self.settings.value("bg_mode", "Black")
        
        if mode == "Gray":
            return QColor(0x44, 0x44, 0x44)  # #444444
        elif mode == "Adaptive Color":
            # Try to extract the current background color from the parent widget
            parent = self.image_label.parentWidget()
            if parent:
                style = parent.styleSheet()
                # Look for rgb() or background-color in the stylesheet
                import re
                rgb_match = re.search(r'rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)', style)
                if rgb_match:
                    r, g, b = map(int, rgb_match.groups())
                    return QColor(r, g, b)
            
            # Fallback to dark gray if we can't extract the adaptive color
            return QColor(40, 40, 40)
        else:
            # Default to black
            return QColor(0, 0, 0)
    
    # Zoom Methods
    def zoom_in(self):
        """Zoom in on the image."""
        if self.zoom_factor < self.MAX_ZOOM:
            self.zoom_factor = min(self.zoom_factor + self.ZOOM_STEP, self.MAX_ZOOM)
            self._update_zoom_display()
            self.zoom_changed.emit(self.zoom_factor)
    
    def zoom_out(self):
        """Zoom out on the image."""
        if self.zoom_factor > self.MIN_ZOOM:
            self.zoom_factor = max(self.zoom_factor - self.ZOOM_STEP, self.MIN_ZOOM)
            self._update_zoom_display()
            self.zoom_changed.emit(self.zoom_factor)
    
    def handle_wheel_zoom(self, angle):
        """Handle mouse wheel zoom."""
        if angle > 0:
            self.zoom_in()
        else:
            self.zoom_out()
    
    def reset_zoom(self):
        """Reset zoom to fit-to-container and center image."""
        self.zoom_factor = 1.0
        self.reset_pan()
        self._update_zoom_display()
        self.zoom_changed.emit(self.zoom_factor)
    
    # Pan Methods
    def start_panning(self, pos):
        """Start panning operation."""
        pass  # Just for signal connection, actual panning handled in handle_panning
    
    def handle_panning(self, delta):
        """Handle panning movement with improved logic."""
        if not self._cached_pixmap:
            return
        
        # Get image and container dimensions for calculations
        container_size = self.image_label.size()
        
        # Always allow panning if there's currently a pan offset (to reset position)
        new_offset_x = self.pan_offset_x + delta.x()
        new_offset_y = self.pan_offset_y + delta.y()
        
        if self.zoom_factor > 1.0:
            # Apply panning with constraints
            # Get current displayed image size
            original_size = self._cached_pixmap.size()
            if original_size.width() <= container_size.width() and original_size.height() <= container_size.height():
                # Constrain panning so image doesn't go too far off screen
                target_size = original_size * self.zoom_factor
            else:
                fit_size = original_size.scaled(container_size, Qt.KeepAspectRatio)
                # Constrain panning so image doesn't go too far off screen  
                target_size = fit_size * self.zoom_factor
            
            max_offset_x = max(0, (target_size.width() - container_size.width()) // 2 + 50)
            max_offset_y = max(0, (target_size.height() - container_size.height()) // 2 + 50)
            
            self.pan_offset_x = max(-max_offset_x, min(max_offset_x, new_offset_x))
            self.pan_offset_y = max(-max_offset_y, min(max_offset_y, new_offset_y))
        else:
            # Allow small movements even when zoomed out to help repositioning
            max_movement = min(container_size.width(), container_size.height()) // 4
            self.pan_offset_x = max(-max_movement, min(max_movement, new_offset_x))
            self.pan_offset_y = max(-max_movement, min(max_movement, new_offset_y))
        
        self._update_zoom_display()
    
    def end_panning(self):
        """End panning operation."""
        pass  # Panning state is maintained until next pan or reset
    
    def reset_pan(self):
        """Reset pan offset to center."""
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        if self.current_image:
            self._update_zoom_display()
    
    # Transform Methods
    def flip_horizontal(self):
        """Toggle horizontal flip of the image."""
        self.is_flipped_h = not self.is_flipped_h
        if self.current_image:
            self.display_image(self.current_image)
        self.transform_changed.emit()
    
    def flip_vertical(self):
        """Toggle vertical flip of the image."""
        self.is_flipped_v = not self.is_flipped_v
        if self.current_image:
            self.display_image(self.current_image)
        self.transform_changed.emit()
    
    def toggle_grayscale(self):
        """Toggle grayscale mode."""
        self.is_grayscale = not self.is_grayscale
        if self.current_image:
            self.display_image(self.current_image)
        self.transform_changed.emit()
    
    # Background Methods
    def cycle_background_mode(self):
        """Cycle through background modes: Black -> Gray -> Adaptive Color -> Black."""
        current_mode = self.settings.value("bg_mode", "Black")
        modes = ["Black", "Gray", "Adaptive Color"]
        
        try:
            current_index = modes.index(current_mode)
            next_index = (current_index + 1) % len(modes)
            next_mode = modes[next_index]
        except ValueError:
            # If current mode is not in list, default to first mode
            next_mode = modes[0]
        
        self.change_bg_mode(next_mode)
    
    def change_bg_mode(self, mode):
        """Change the background color mode."""
        self.settings.setValue("bg_mode", mode)
        if self.current_image:
            self.display_image(self.current_image)
    
    # State Methods
    def get_zoom_info(self):
        """Get current zoom information."""
        return {
            'zoom_factor': self.zoom_factor,
            'pan_offset_x': self.pan_offset_x,
            'pan_offset_y': self.pan_offset_y
        }
    
    def get_transform_info(self):
        """Get current transform information."""
        return {
            'is_flipped_h': self.is_flipped_h,
            'is_flipped_v': self.is_flipped_v,
            'is_grayscale': self.is_grayscale
        }
    
    def reset_all_transforms(self):
        """Reset all image transforms to default state."""
        self.is_flipped_h = False
        self.is_flipped_v = False
        self.is_grayscale = False
        self.zoom_factor = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        
        if self.current_image:
            self.display_image(self.current_image)
        
        self.zoom_changed.emit(self.zoom_factor)
        self.transform_changed.emit()
    
    def reset_all_transforms_without_display(self):
        """Reset all image transforms to default state without re-displaying image."""
        self.is_flipped_h = False
        self.is_flipped_v = False
        self.is_grayscale = False
        self.zoom_factor = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        
        self.zoom_changed.emit(self.zoom_factor)
        self.transform_changed.emit()
    
    def reset_positional_transforms_without_display(self):
        """Reset zoom/pan and flips but preserve user preferences like grayscale."""
        self.is_flipped_h = False
        self.is_flipped_v = False
        # Preserve grayscale - it's a user preference that should persist across collections
        self.zoom_factor = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        
        self.zoom_changed.emit(self.zoom_factor)
        self.transform_changed.emit()