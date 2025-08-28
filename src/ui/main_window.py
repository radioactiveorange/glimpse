"""Main window class for the Random Image Viewer application."""

import sys
import os
import random
import subprocess
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QVBoxLayout, QWidget,
    QListWidget, QListWidgetItem, QSplitter, QSizePolicy,
    QMenu, QInputDialog, QDialog
)
from PySide6.QtGui import QPixmap, QImage, QTransform, QAction, QPainter
from PySide6.QtCore import Qt, QTimer, QSize, QSettings

from .widgets import ClickableLabel, MinimalProgressBar, ButtonOverlay
from .startup_dialog import StartupDialog
from ..core.image_utils import get_images_in_folder, set_adaptive_bg
from ..core.collections import Collection


class GlimpseViewer(QMainWindow):
    """Main application window for Glimpse - random image viewer."""
    
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setWindowTitle("Glimpse")
        self.setGeometry(100, 100, 950, 650)
        
        # Initialize settings
        self.settings = QSettings("glimpse", "Glimpse")
        
        # Initialize state
        self.folder = None
        self.current_collection = None
        self.images = []
        self.history = []
        self.current_image = None
        self.current_index = -1
        self.history_index = -1
        self.timer_interval = self.settings.value("timer_interval", 60, type=int)
        self.timer_remaining = 0
        self._auto_advance_active = self.settings.value("auto_advance_enabled", False, type=bool)
        self.show_history = self.settings.value("show_history_panel", False, type=bool)
        self.zoom_factor = 1.0
        self.flipped_h = False
        self.flipped_v = False
        self._timer_paused = False
        self._cached_pixmap = None  # Cache processed image for smooth zooming
        
        # Panning state
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        self._is_panning = False
        self._last_pan_point = None
        
        # Initialize timer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_timer_tick)
        
        self.init_ui()
        self._initial_image_shown = False

    def init_ui(self):
        """Initialize the user interface."""
        central_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(central_splitter)

        # Image display area
        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        image_layout.setContentsMargins(6, 6, 6, 6)

        self.image_label = ClickableLabel("Welcome to Glimpse", alignment=Qt.AlignCenter)
        self.image_label.setScaledContents(False)
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setToolTip("")
        
        # Connect signals
        self.image_label.back.connect(self.show_previous_image)
        self.image_label.forward.connect(self.show_next_image)
        self.image_label.wheel_zoom.connect(self.handle_wheel_zoom)
        self.image_label.pan_start.connect(self.start_panning)
        self.image_label.pan_move.connect(self.handle_panning)
        self.image_label.pan_end.connect(self.end_panning)
        
        # Set up context menu
        self.image_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.image_label.customContextMenuRequested.connect(self.show_context_menu)

        image_layout.addWidget(self.image_label)
        image_widget.setLayout(image_layout)
        central_splitter.addWidget(image_widget)

        # History panel
        self.history_list = QListWidget()
        self.history_list.setMaximumWidth(180)
        self.history_list.itemClicked.connect(self.on_history_clicked)
        self.history_list.hide()
        central_splitter.addWidget(self.history_list)
        central_splitter.setSizes([900, 100])
        self.history_list.setVisible(self.show_history)

        # Progress bar overlay at bottom
        self.progress_bar = MinimalProgressBar(self.image_label)
        self.progress_bar.hide()
        
        # Button overlay at bottom middle - always visible when image is loaded
        self.button_overlay = ButtonOverlay(self.image_label)
        self.button_overlay.hide()
        
        # Connect button signals
        self.button_overlay.previous_clicked.connect(self.show_previous_image)
        self.button_overlay.pause_clicked.connect(self.toggle_pause)
        self.button_overlay.stop_clicked.connect(self.stop_timer)
        self.button_overlay.next_clicked.connect(self.show_next_or_random_image)
        self.button_overlay.zoom_in_clicked.connect(self.zoom_in)
        self.button_overlay.zoom_out_clicked.connect(self.zoom_out)
        
        self.image_label.resizeEvent = self.overlay_resize_event(self.image_label.resizeEvent)

    def showEvent(self, event):
        """Handle show event to display initial image."""
        super().showEvent(event)
        if not self._initial_image_shown and self.images:
            self.show_random_image()
            self._initial_image_shown = True
            self._reset_timer()
        
        # Update title and image info on show
        self.update_image_info()
        self._update_title()

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key_Left:
            self.show_previous_image()
        elif event.key() == Qt.Key_Right:
            self.show_next_image()
        elif event.modifiers() & Qt.ControlModifier:
            if event.key() in (Qt.Key_Plus, Qt.Key_Equal):
                self.zoom_in()
            elif event.key() == Qt.Key_Minus:
                self.zoom_out()
            elif event.key() == Qt.Key_0:
                self.reset_zoom()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def toggle_pause(self):
        """Toggle pause state of the auto-advance timer."""
        if not self._auto_advance_active:
            # If timer is disabled, enable it instead of just pausing
            self.start_timer()
            return
        
        self._timer_paused = not self._timer_paused
        if self._timer_paused:
            self.timer.stop()
        else:
            self.timer.start()
        
        self.button_overlay.set_pause_state(self._timer_paused, self._auto_advance_active)
    
    def start_timer(self):
        """Start/enable the auto-advance timer."""
        self._auto_advance_active = True
        self._timer_paused = False
        self.settings.setValue("auto_advance_enabled", True)
        self._reset_timer()
        self.button_overlay.set_pause_state(False, self._auto_advance_active)

    def stop_timer(self):
        """Stop and disable the auto-advance timer completely."""
        self._auto_advance_active = False
        self._timer_paused = False
        self.settings.setValue("auto_advance_enabled", False)
        self._reset_timer()
        self.button_overlay.set_pause_state(False, self._auto_advance_active)

    def show_previous_image(self):
        """Show the previous image in history."""
        if self.history_index > 0:
            self.history_index -= 1
            img_path = self.history[self.history_index]
            self.flipped_h = False
            self.flipped_v = False
            self.display_image(img_path)
            self.current_image = img_path
            self.update_image_info(img_path)
            if self._auto_advance_active:
                self.timer_remaining = self.timer_interval
                self._update_progress()

    def show_next_image(self):
        """Show the next image in history or a random one."""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            img_path = self.history[self.history_index]
            self.flipped_h = False
            self.flipped_v = False
            self.display_image(img_path)
            self.current_image = img_path
            self.update_image_info(img_path)
            if self._auto_advance_active:
                self.timer_remaining = self.timer_interval
                self._update_progress()
        else:
            self.show_random_image()

    def show_next_or_random_image(self):
        """Show next image or random if at end of history."""
        if self.history_index < len(self.history) - 1:
            self.show_next_image()
        else:
            self.show_random_image()

    def choose_folder(self):
        """Open folder selection dialog."""
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.load_folder(folder, False, 60)  # Default: no timer, 60 seconds
            if self.images:
                self.show_random_image()

    def show_welcome_dialog(self):
        """Show the welcome dialog to switch collection or folder."""
        startup = StartupDialog(self)
        
        def on_collection_selected(data):
            if not data or len(data) != 3:
                return
            collection, timer_enabled, timer_interval = data
            self.load_collection(collection, timer_enabled, timer_interval)
            if self.images:
                self.show_random_image()
        
        def on_folder_selected(data):
            if not data or len(data) != 3:
                return
            folder, timer_enabled, timer_interval = data
            self.load_folder(folder, timer_enabled, timer_interval)
            if self.images:
                self.show_random_image()
        
        startup.collection_selected.connect(on_collection_selected)
        startup.folder_selected.connect(on_folder_selected)
        
        startup.exec()

    def _update_title(self, img_path=None, info=None):
        """Update the window title with current image info."""
        # Use collection title if we have one
        if self.current_collection:
            self._update_title_for_collection()
            return
            
        if img_path:
            base = os.path.basename(img_path)
            self.setWindowTitle(base)
        else:
            folder_name = os.path.basename(self.folder) if self.folder else "Random Image Viewer"
            self.setWindowTitle(f"Glimpse - {folder_name}")

    def update_image_info(self, img_path=None):
        """Update image information display."""
        if img_path is None or not os.path.exists(img_path):
            self._update_title()
            return
        base = os.path.basename(img_path)
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            info = f"{pixmap.width()}x{pixmap.height()}"
        else:
            info = base
        
        # Use appropriate title method
        if self.current_collection:
            self._update_title_for_collection()
        else:
            self._update_title(img_path, info)

    def show_random_image(self):
        """Display a random image from the current folder."""
        if not self.images:
            return
        self.flipped_h = False
        self.flipped_v = False
        available = [img for img in self.images if img not in self.history]
        if not available:
            self.history.clear()
            self.history_list.clear()
            available = self.images[:]
        
        # If timer is active, try to avoid very large files that might cause issues
        if self._auto_advance_active:
            manageable_images = [img for img in available if not self._is_image_too_large(img)]
            if manageable_images:
                available = manageable_images
        
        img_path = random.choice(available)
        self.display_image(img_path)
        self.add_to_history(img_path)
        self.current_image = img_path
        self.update_image_info(img_path)
        if self._auto_advance_active:
            self.timer_remaining = self.timer_interval
            self._update_progress()

    def display_image(self, img_path):
        """Display an image with current transformations and settings."""
        # Load and process the image (this caches the result)
        self._load_and_process_image(img_path)
        
        # Apply zoom to the cached image
        self._update_zoom_display()
        
        # Show button overlay when image is loaded
        self.button_overlay.show()
        
        # Set background according to settings
        mode = self.settings.value("bg_mode", "Black")
        if mode == "Adaptive Color":
            set_adaptive_bg(self.image_label, img_path)
        elif mode == "Gray":
            self.image_label.parentWidget().setStyleSheet("background-color: #444444;")
        else:
            self.image_label.parentWidget().setStyleSheet("background-color: #000000;")
        
        # Update title with just filename
        self._update_title(img_path)

    def _is_image_too_large(self, img_path):
        """Check if an image file is likely too large for Qt to handle."""
        try:
            import os
            file_size_mb = os.path.getsize(img_path) / (1024 * 1024)
            # Conservative estimate: files >100MB are likely to cause issues
            return file_size_mb > 100
        except:
            return False
    
    def _load_and_process_image(self, img_path):
        """Load image from disk and apply transformations, caching the result."""
        try:
            pixmap = QPixmap(img_path)
            if pixmap.isNull():
                # Check if this might be due to size limit
                import os
                from PySide6.QtGui import QImageReader
                file_size_mb = os.path.getsize(img_path) / (1024 * 1024)
                
                # Try to get image dimensions to calculate uncompressed size
                try:
                    reader = QImageReader(img_path)
                    size = reader.size()
                    if size.isValid():
                        width, height = size.width(), size.height()
                        uncompressed_mb = (width * height * 4) / (1024 * 1024)  # 4 bytes per pixel (RGBA)
                        self.image_label.setText(f"Image too large to display.\n\nFile: {os.path.basename(img_path)}\nFile size: {file_size_mb:.1f}MB\nDimensions: {width}x{height}\nUncompressed: {uncompressed_mb:.1f}MB\n\nQt limit: 256MB uncompressed.\nConsider resizing the image.")
                    else:
                        self.image_label.setText(f"Cannot load image.\n\nFile: {os.path.basename(img_path)}\nSize: {file_size_mb:.1f}MB\n\nThis may exceed Qt's 256MB memory limit.")
                except Exception:
                    # Fallback if QImageReader fails
                    self.image_label.setText(f"Cannot load image.\n\nFile: {os.path.basename(img_path)}\nSize: {file_size_mb:.1f}MB\n\nThis may exceed Qt's 256MB memory limit.")
                
                self._cached_pixmap = None
                return
        except Exception as e:
            self.image_label.setText(f"Error loading image:\n{str(e)}")
            self._cached_pixmap = None
            return
        
        # Apply transformations
        image = pixmap.toImage()
        if self.settings.value("grayscale_enabled", False, type=bool):
            image = self._apply_improved_grayscale(image)
        if self.flipped_h:
            transform = QTransform().scale(-1, 1)
            image = image.transformed(transform)
        if self.flipped_v:
            transform = QTransform().scale(1, -1)
            image = image.transformed(transform)
        
        # Cache the processed pixmap
        self._cached_pixmap = QPixmap.fromImage(image)
        self.current_image = img_path
        
        # Reset pan position when loading new image
        self.pan_offset_x = 0
        self.pan_offset_y = 0
    
    def _apply_improved_grayscale(self, image):
        """Apply improved grayscale conversion using human eye correction (ITU-R BT.709)."""
        # Convert to RGB32 format if needed
        if image.format() != QImage.Format_RGB32:
            image = image.convertToFormat(QImage.Format_RGB32)
        
        width = image.width()
        height = image.height()
        total_pixels = width * height
        
        # For large images, show a wait cursor to indicate processing
        show_wait_cursor = total_pixels > 2000000  # 2 megapixels
        if show_wait_cursor:
            self.setCursor(Qt.WaitCursor)
        
        try:
            # For very large images (>5MP), use Qt's built-in fast conversion 
            # and accept slightly less accurate color reproduction
            if total_pixels > 5000000:  # 5 megapixels
                return image.convertToFormat(QImage.Format_Grayscale8).convertToFormat(QImage.Format_RGB32)
            
            # Create grayscale copy
            grayscale_image = image.copy()
            
            # Process line by line for better performance
            for y in range(height):
                scan_line = grayscale_image.scanLine(y)
                # Convert to memoryview for faster access
                pixels = memoryview(scan_line).cast('I')  # 32-bit unsigned integers
                
                for x in range(width):
                    pixel = pixels[x]
                    # Extract RGB components (assuming little-endian BGRA format)
                    blue = pixel & 0xFF
                    green = (pixel >> 8) & 0xFF
                    red = (pixel >> 16) & 0xFF
                    alpha = (pixel >> 24) & 0xFF
                    
                    # Apply ITU-R BT.709 coefficients for perceptual luminance
                    gray_value = int(0.2126 * red + 0.7152 * green + 0.0722 * blue)
                    gray_value = min(255, max(0, gray_value))
                    
                    # Set pixel to grayscale (BGRA format)
                    pixels[x] = (alpha << 24) | (gray_value << 16) | (gray_value << 8) | gray_value
            
            return grayscale_image
        finally:
            # Always restore cursor
            if show_wait_cursor:
                self.setCursor(Qt.ArrowCursor)
        
    def _update_zoom_display(self):
        """Update the display with current zoom level and pan offset using cached pixmap."""
        if not self._cached_pixmap:
            return
            
        # For small images, scale based on natural size; for large images, fit to container
        original_size = self._cached_pixmap.size()
        container_size = self.image_label.size()
        
        # Check if image is small (smaller than container in both dimensions)
        is_small_image = (original_size.width() <= container_size.width() and 
                         original_size.height() <= container_size.height())
        
        if is_small_image and self.zoom_factor == 1.0:
            # For small images at 100% zoom, use original size
            target_size = original_size
        else:
            # For large images or when zoomed, scale based on container size
            if is_small_image:
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
            canvas.fill(Qt.black)  # Use black background instead of transparent
            
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
            
        self.image_label.setToolTip("")

    def resizeEvent(self, event):
        """Handle window resize to redisplay current image."""
        if self._cached_pixmap:
            self._update_zoom_display()
        super().resizeEvent(event)

    def add_to_history(self, img_path):
        """Add an image to the viewing history."""
        # If we've navigated back in history and now show a new random image,
        # remove all forward history.
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
            self.history_list.clear()
            for path in self.history:
                self._add_history_item(path)
        # Only add if not duplicating last
        if not self.history or (self.history and self.history[-1] != img_path):
            self.history.append(img_path)
            self._add_history_item(img_path)
        self.history_index = len(self.history) - 1

    def _add_history_item(self, img_path):
        """Add an item to the history list widget."""
        item = QListWidgetItem(os.path.basename(img_path))
        thumb = QPixmap(img_path)
        if not thumb.isNull():
            thumb = thumb.scaled(QSize(40, 40), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item.setIcon(thumb)
        item.setToolTip(img_path)
        item.setData(Qt.UserRole, img_path)
        self.history_list.addItem(item)
        self.history_list.scrollToBottom()

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
            self.display_image(img_path)
            self.current_image = img_path
            self.update_image_info(img_path)
            if self._auto_advance_active:
                self.timer_remaining = self.timer_interval
                self._update_progress()

    def toggle_history_panel(self, checked):
        """Toggle the history panel visibility."""
        self.history_list.setVisible(bool(checked))
        self.settings.setValue("show_history_panel", bool(checked))

    def toggle_timer(self, checked):
        """Toggle the auto-advance timer from context menu."""
        self._auto_advance_active = bool(checked)
        self._timer_paused = False  # Reset pause state when toggling
        self.settings.setValue("auto_advance_enabled", self._auto_advance_active)
        self._reset_timer()
        # Always show button overlay when image is loaded, regardless of timer state
        if self.current_image:
            self.button_overlay.show()
        # Update button overlay to reflect new state
        self.button_overlay.set_pause_state(False, self._auto_advance_active)

    def change_bg_mode(self, mode):
        """Change the background color mode."""
        self.settings.setValue("bg_mode", mode)
        self.display_image(self.current_image) if self.current_image else None

    def toggle_grayscale(self, checked):
        """Toggle grayscale mode."""
        self.settings.setValue("grayscale_enabled", checked)
        if checked:
            self.image_label.parentWidget().setStyleSheet("background-color: #3b7dd8; color: #fff; border-radius: 4px;")
        else:
            self.image_label.parentWidget().setStyleSheet("")
        self.display_image(self.current_image) if self.current_image else None

    def flip_horizontal(self):
        """Flip the current image horizontally."""
        self.flipped_h = not self.flipped_h
        if self.current_image:
            self._load_and_process_image(self.current_image)  # Reprocess with flip
            self._update_zoom_display()

    def flip_vertical(self):
        """Flip the current image vertically."""
        self.flipped_v = not self.flipped_v
        if self.current_image:
            self._load_and_process_image(self.current_image)  # Reprocess with flip
            self._update_zoom_display()

    def overlay_resize_event(self, original_resize_event):
        """Create a custom resize event handler for overlay positioning."""
        def new_resize_event(event):
            # Call the original resize event
            if original_resize_event:
                original_resize_event(event)
            # Position progress bar at bottom, full width
            self.progress_bar.setGeometry(0, self.image_label.height() - 4, self.image_label.width(), 4)
            # Position button overlay at bottom center
            overlay_x = (self.image_label.width() - self.button_overlay.width()) // 2
            overlay_y = self.image_label.height() - self.button_overlay.height() - 20
            self.button_overlay.move(overlay_x, overlay_y)
        return new_resize_event

    def _reset_timer(self):
        """Reset the auto-advance timer."""
        if self._auto_advance_active and self.images:
            self.timer.stop()
            self.timer_remaining = self.timer_interval
            self._timer_paused = False
            self._update_progress()
            self.timer.start()
            self.progress_bar.show()
            if self.current_image:
                self.button_overlay.show()
            self.button_overlay.set_pause_state(False, self._auto_advance_active)
        else:
            self.timer.stop()
            self._timer_paused = False
            self.progress_bar.set_remaining_time(0)
            self.progress_bar.hide()
            # Keep button overlay visible even when timer is disabled
            if self.current_image:
                self.button_overlay.show()
            self.button_overlay.set_pause_state(False, self._auto_advance_active)

    def _on_timer_tick(self):
        """Handle timer tick for auto-advance."""
        if not self._auto_advance_active or not self.images or self._timer_paused:
            if not self._auto_advance_active:
                self.timer.stop()
                self.progress_bar.set_remaining_time(0)
            return
        self.timer_remaining -= 1
        if self.timer_remaining <= 0:
            self.show_random_image()
        else:
            self._update_progress()

    def _update_progress(self):
        """Update the progress bar display."""
        self.progress_bar.set_total_time(self.timer_interval)
        self.progress_bar.set_remaining_time(self.timer_remaining)

    def show_context_menu(self, pos):
        """Show the right-click context menu."""
        menu = QMenu(self)
        
        # --- Navigation Controls ---
        prev_action = QAction("Previous", self)
        prev_action.triggered.connect(self.show_previous_image)
        prev_action.setEnabled(self.history_index > 0)
        menu.addAction(prev_action)
        
        next_action = QAction("Next", self)
        next_action.triggered.connect(self.show_next_or_random_image)
        menu.addAction(next_action)
        
        random_action = QAction("Random Image", self)
        random_action.triggered.connect(self.show_random_image)
        menu.addAction(random_action)
        menu.addSeparator()
        
        # --- Media Controls ---
        if self._auto_advance_active:
            if self._timer_paused:
                play_action = QAction("Play", self)
                play_action.triggered.connect(self.toggle_pause)
                menu.addAction(play_action)
            else:
                pause_action = QAction("Pause", self)
                pause_action.triggered.connect(self.toggle_pause)
                menu.addAction(pause_action)
        else:
            start_action = QAction("Start Timer", self)
            start_action.triggered.connect(self.start_timer)
            menu.addAction(start_action)
        
        stop_action = QAction("Stop Timer", self)
        stop_action.triggered.connect(self.stop_timer)
        stop_action.setEnabled(self._auto_advance_active)
        menu.addAction(stop_action)
        menu.addSeparator()
        
        # --- File Actions ---
        open_explorer_action = QAction("Open in Explorer", self)
        open_explorer_action.triggered.connect(self.open_current_in_explorer)
        open_explorer_action.setEnabled(self.current_image is not None)
        menu.addAction(open_explorer_action)
        
        # --- Source Selection ---
        welcome_action = QAction("Switch Collection/Folder...", self)
        welcome_action.triggered.connect(self.show_welcome_dialog)
        menu.addAction(welcome_action)
        menu.addSeparator()
        
        # --- Zoom actions ---
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.zoom_in)
        menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out)
        menu.addAction(zoom_out_action)
        
        reset_zoom_action = QAction("Reset Zoom", self)
        reset_zoom_action.setShortcut("Ctrl+0")
        reset_zoom_action.triggered.connect(self.reset_zoom)
        menu.addAction(reset_zoom_action)
        
        reset_pan_action = QAction("Reset Pan Position", self)
        reset_pan_action.triggered.connect(self.reset_pan)
        reset_pan_action.setEnabled(self.zoom_factor > 1.0)  # Only enable when zoomed
        menu.addAction(reset_pan_action)
        menu.addSeparator()
        
        # --- Timer Settings ---
        timer_menu = QMenu("Timer Interval", self)
        for label, value in [("30s", 30), ("60s", 60), ("5m", 300), ("10m", 600)]:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(self.timer_interval == value)
            act.triggered.connect(lambda checked, v=value: self.set_timer_interval(v))
            timer_menu.addAction(act)
        custom_act = QAction("Custom...", self)
        custom_act.triggered.connect(self.set_custom_timer_interval)
        timer_menu.addAction(custom_act)
        menu.addMenu(timer_menu)
        menu.addSeparator()
        
        # --- Settings ---
        grayscale_action = QAction("Grayscale", self)
        grayscale_action.setCheckable(True)
        grayscale_action.setChecked(self.settings.value("grayscale_enabled", False, type=bool))
        grayscale_action.toggled.connect(self.toggle_grayscale)
        menu.addAction(grayscale_action)
        
        flip_h_action = QAction("Flip Horizontal", self)
        flip_h_action.triggered.connect(self.flip_horizontal)
        menu.addAction(flip_h_action)
        
        flip_v_action = QAction("Flip Vertical", self)
        flip_v_action.triggered.connect(self.flip_vertical)
        menu.addAction(flip_v_action)
        
        history_action = QAction("Show History Panel", self)
        history_action.setCheckable(True)
        history_action.setChecked(self.settings.value("show_history_panel", False, type=bool))
        history_action.toggled.connect(self.toggle_history_panel)
        menu.addAction(history_action)
        
        # Background color submenu
        bg_menu = QMenu("Background Color", self)
        current_bg = self.settings.value("bg_mode", "Black")
        for mode in ["Black", "Gray", "Adaptive Color"]:
            act = QAction(mode, self)
            act.setCheckable(True)
            act.setChecked(current_bg == mode)
            act.triggered.connect(lambda checked, m=mode: self.change_bg_mode(m))
            bg_menu.addAction(act)
        menu.addMenu(bg_menu)
        
        menu.exec(self.image_label.mapToGlobal(pos))

    def set_timer_interval(self, value):
        """Set the timer interval."""
        self.timer_interval = value
        self.settings.setValue("timer_interval", value)
        self.timer_remaining = value
        self._update_progress()

    def set_custom_timer_interval(self):
        """Set a custom timer interval via dialog."""
        val, ok = QInputDialog.getInt(self, "Custom Timer Interval", "Seconds:", self.timer_interval, 1, 3600)
        if ok:
            self.set_timer_interval(val)

    def open_current_in_explorer(self):
        """Open the current image's folder in file explorer."""
        if not self.current_image:
            return
        path = os.path.abspath(self.current_image)
        folder = os.path.dirname(path)
        if os.name == "nt":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    def handle_wheel_zoom(self, angle):
        """Handle mouse wheel zoom."""
        if angle > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def zoom_in(self):
        """Zoom in on the current image."""
        self.zoom_factor = min(self.zoom_factor * 1.15, 8.0)
        self._update_zoom_display()

    def zoom_out(self):
        """Zoom out on the current image."""
        self.zoom_factor = max(self.zoom_factor / 1.15, 0.1)
        
        # Auto-reset pan when image becomes smaller than display area
        if self._cached_pixmap:
            base_size = self.image_label.size()
            target_size = base_size * self.zoom_factor
            scaled_size = self._cached_pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation).size()
            
            # Reset pan if image is now smaller than display in both dimensions
            if (scaled_size.width() <= self.image_label.width() and 
                scaled_size.height() <= self.image_label.height()):
                self.pan_offset_x = 0
                self.pan_offset_y = 0
        
        self._update_zoom_display()

    def reset_zoom(self):
        """Reset zoom to 100%."""
        self.zoom_factor = 1.0
        self.pan_offset_x = 0  # Reset pan when zooming to 100%
        self.pan_offset_y = 0
        self._update_zoom_display()

    def start_panning(self, pos):
        """Start panning operation."""
        pass  # Just for signal connection, actual panning handled in handle_panning

    def handle_panning(self, delta):
        """Handle panning movement with improved logic."""
        if not self._cached_pixmap:
            return
            
        # Calculate current image dimensions after zoom
        base_size = self.image_label.size()
        target_size = base_size * self.zoom_factor
        scaled_size = self._cached_pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation).size()
        
        # Always allow panning if there's currently a pan offset (to reset position)
        # or if image is larger than display area
        can_pan_x = (scaled_size.width() > self.image_label.width()) or (self.pan_offset_x != 0)
        can_pan_y = (scaled_size.height() > self.image_label.height()) or (self.pan_offset_y != 0)
        
        # Apply panning with constraints
        if can_pan_x:
            new_offset_x = self.pan_offset_x + delta.x()
            # Constrain panning so image doesn't go too far off screen
            max_offset_x = max(0, (scaled_size.width() - self.image_label.width()) // 2 + 50)
            self.pan_offset_x = max(-max_offset_x, min(max_offset_x, new_offset_x))
            
        if can_pan_y:
            new_offset_y = self.pan_offset_y + delta.y()
            # Constrain panning so image doesn't go too far off screen  
            max_offset_y = max(0, (scaled_size.height() - self.image_label.height()) // 2 + 50)
            self.pan_offset_y = max(-max_offset_y, min(max_offset_y, new_offset_y))
        
        self._update_zoom_display()

    def end_panning(self):
        """End panning operation."""
        pass  # Just for signal connection

    def reset_pan(self):
        """Reset pan position to center."""
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        self._update_zoom_display()
    
    def load_collection(self, collection: Collection, timer_enabled: bool = False, timer_interval: int = 60):
        """Load images from a collection with timer settings."""
        self.current_collection = collection
        self.folder = None  # Clear single folder
        
        # Configure timer settings
        self._auto_advance_active = timer_enabled
        self.timer_interval = timer_interval
        self.settings.setValue("auto_advance_enabled", self._auto_advance_active)
        self.settings.setValue("timer_interval", self.timer_interval)
        
        # Get all images from collection
        self.images = collection.get_all_images()
        
        # Clear history
        self.history.clear()
        self.history_list.clear()
        self.history_list.repaint()
        self.current_image = None
        self.history_index = -1
        
        # Reset transformations
        self.flipped_h = False
        self.flipped_v = False
        
        # Update UI
        self.update_image_info()
        self._update_title_for_collection()
        
        if self.images:
            # Don't auto-show image here, let showEvent handle it
            pass
        else:
            self.image_label.setText("No images found in selected collection.")
        
        self._reset_timer()
    
    def load_folder(self, folder_path: str, timer_enabled: bool = False, timer_interval: int = 60):
        """Load images from a single folder (quick shuffle mode) with timer settings."""
        self.folder = folder_path
        self.current_collection = None  # Clear collection
        
        # Configure timer settings
        self._auto_advance_active = timer_enabled
        self.timer_interval = timer_interval
        self.settings.setValue("auto_advance_enabled", self._auto_advance_active)
        self.settings.setValue("timer_interval", self.timer_interval)
        
        # Save as last folder for quick access
        self.settings.setValue("last_folder", folder_path)
        
        # Get images
        self.images = get_images_in_folder(folder_path)
        
        # Clear history
        self.history.clear()
        self.history_list.clear()
        self.history_list.repaint()
        self.current_image = None
        self.history_index = -1
        
        # Reset transformations
        self.flipped_h = False
        self.flipped_v = False
        
        # Update UI
        self.update_image_info()
        self._update_title()
        
        if self.images:
            # Don't auto-show image here, let showEvent handle it
            pass
        else:
            self.image_label.setText("No images found in selected folder or its subfolders.")
        
        self._reset_timer()
    
    def _update_title_for_collection(self):
        """Update window title for collection mode."""
        if self.current_collection:
            if self.current_image:
                base = os.path.basename(self.current_image)
                self.setWindowTitle(base)
            else:
                self.setWindowTitle(f"Glimpse - Collection: {self.current_collection.name}")
        else:
            self._update_title()