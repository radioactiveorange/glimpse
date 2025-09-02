"""Main window class for the Random Image Viewer application."""

import sys
import os
import random
import subprocess
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QVBoxLayout, QWidget,
    QListWidget, QListWidgetItem, QSplitter, QSizePolicy,
    QMenu, QInputDialog, QDialog, QApplication, QTableWidget, 
    QTableWidgetItem, QHeaderView, QDialogButtonBox, QLabel as QDialogLabel
)
from PySide6.QtGui import QPixmap, QImage, QTransform, QAction, QPainter
from PySide6.QtCore import Qt, QTimer, QSize, QSettings, QThread, Signal

from .widgets import ClickableLabel, MinimalProgressBar, ButtonOverlay
from .startup_dialog import StartupDialog
from .loading_dialog import LoadingDialog
from ..core.image_utils import get_images_in_folder, set_adaptive_bg
from ..core.collections import Collection


class KeyboardShortcutsDialog(QDialog):
    """Dialog to display keyboard shortcuts help."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setModal(True)
        self.resize(450, 400)
        
        # Center the dialog
        if parent:
            parent_geometry = parent.frameGeometry()
            dialog_geometry = self.frameGeometry()
            x = parent_geometry.center().x() - dialog_geometry.width() // 2
            y = parent_geometry.center().y() - dialog_geometry.height() // 2
            self.move(x, y)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Title
        title_label = QDialogLabel("Keyboard Shortcuts")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #b7bcc1; margin-bottom: 8px;")
        layout.addWidget(title_label)
        
        # Create table for shortcuts
        table = QTableWidget(11, 2)
        table.setHorizontalHeaderLabels(["Shortcut", "Action"])
        table.verticalHeader().hide()
        
        # Set table style
        table.setStyleSheet("""
            QTableWidget {
                background-color: #232629;
                color: #b7bcc1;
                gridline-color: #35383b;
                border: 1px solid #35383b;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #35383b;
            }
            QTableWidget::item:selected {
                background-color: #354e6e;
            }
            QHeaderView::section {
                background-color: #35383b;
                color: #b7bcc1;
                padding: 8px;
                border: 1px solid #232629;
                font-weight: bold;
            }
        """)
        
        # Add shortcuts data
        shortcuts = [
            ("←  →", "Navigate previous/next image"),
            ("Space", "Play/pause timer"),
            ("Ctrl +", "Zoom in"),
            ("Ctrl -", "Zoom out"),
            ("Ctrl 0", "Reset zoom and center image"),
            ("F", "Flip image horizontally"),
            ("G", "Toggle grayscale mode"),
            ("B", "Cycle background modes"),
            ("H", "Toggle history panel"),
            ("Esc", "Switch collection/folder"),
            ("Right-click", "Open context menu")
        ]
        
        for row, (shortcut, action) in enumerate(shortcuts):
            shortcut_item = QTableWidgetItem(shortcut)
            action_item = QTableWidgetItem(action)
            
            # Make items read-only and center shortcut column
            shortcut_item.setFlags(shortcut_item.flags() & ~Qt.ItemIsEditable)
            action_item.setFlags(action_item.flags() & ~Qt.ItemIsEditable)
            shortcut_item.setTextAlignment(Qt.AlignCenter)
            
            table.setItem(row, 0, shortcut_item)
            table.setItem(row, 1, action_item)
        
        # Resize columns
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        layout.addWidget(table)
        
        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.setStyleSheet("""
            QDialogButtonBox {
                margin-top: 8px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                font-size: 12px;
                font-weight: 500;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)


class GlimpseViewer(QMainWindow):
    """Main application window for Glimpse - random image viewer."""
    
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setWindowTitle(f"Glimpse")
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
        self.sorted_collection_index = 0  # For sequential navigation in sorted collections
        self.timer_interval = self.settings.value("timer_interval", 60, type=int)
        self.timer_remaining = 0
        self._auto_advance_active = self.settings.value("auto_advance_enabled", False, type=bool)
        self.show_history = self.settings.value("show_history_panel", False, type=bool)
        self.zoom_factor = 1.0
        self.flipped_h = False
        self.flipped_v = False
        self._timer_paused = False
        self._cached_pixmap = None  # Cache processed image for smooth zooming
        self._pending_grayscale_path = None  # Track if grayscale processing is pending
        
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
    
    
    def center_on_screen(self):
        """Center the window on the screen."""
        screen = QApplication.primaryScreen().availableGeometry()
        window = self.frameGeometry()
        x = (screen.width() - window.width()) // 2 + screen.x()
        y = (screen.height() - window.height()) // 2 + screen.y()
        self.move(x, y)
    
    def showEvent(self, event):
        """Override showEvent to center window when first shown."""
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            # Use QTimer to center after window is fully shown
            QTimer.singleShot(0, self._delayed_center)
            self._centered = True
    
    def _delayed_center(self):
        """Center window after it's fully displayed."""
        self.center_on_screen()

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
        self.image_label.mouse_moved.connect(self.show_controls)
        
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
        elif event.key() == Qt.Key_Space:
            self.toggle_pause()
        elif event.key() == Qt.Key_F:
            self.flip_horizontal()
        elif event.key() == Qt.Key_G:
            # Toggle grayscale mode
            current_grayscale = self.settings.value("grayscale_enabled", False, type=bool)
            self.toggle_grayscale(not current_grayscale)
        elif event.key() == Qt.Key_B:
            self.cycle_background_mode()
        elif event.key() == Qt.Key_H:
            # Toggle history panel
            current_visibility = self.history_list.isVisible()
            self.toggle_history_panel(not current_visibility)
        elif event.key() == Qt.Key_Escape:
            # Switch collection/folder
            self.show_welcome_dialog()
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
        
        # Check if we're using a sorted collection (not random)
        if self.current_collection and self.current_collection.sort_method != "random":
            self.show_next_sorted_image()
            return
        
        available = [img for img in self.images if img not in self.history]
        if not available:
            self.history.clear()
            self.history_list.clear()
            available = self.images[:]
        
        # Note: Removed expensive file size checking that was causing freezing with large collections
        
        img_path = random.choice(available)
        self.display_image(img_path)
        self.add_to_history(img_path)
        self.current_image = img_path
        self.update_image_info(img_path)
        if self._auto_advance_active:
            self.timer_remaining = self.timer_interval
            self._update_progress()
    
    def show_next_sorted_image(self):
        """Show the next image in a sorted collection."""
        if not self.images:
            return
        
        # Move to next image in sorted order
        if self.sorted_collection_index >= len(self.images):
            self.sorted_collection_index = 0  # Loop back to start
        
        img_path = self.images[self.sorted_collection_index]
        self.sorted_collection_index += 1
        
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
        
        # Show button overlay when image is loaded (but not on keyboard navigation)
        # Check if this display was triggered by keyboard navigation
        import inspect
        calling_methods = [frame.function for frame in inspect.stack()]
        keyboard_triggered = any(method in calling_methods for method in ['show_previous_image', 'show_next_image', 'keyPressEvent'])
        
        if not keyboard_triggered:
            # Show controls for mouse navigation, new images, etc.
            self.button_overlay.show_for_new_image()
        # Always show for first image load or new collection/folder
        elif not hasattr(self, '_first_image_shown') or not self._first_image_shown:
            self.button_overlay.show_for_new_image()
            self._first_image_shown = True
        
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
        """Load image from disk and apply all transformations immediately but non-blocking."""
        try:
            # Load image from disk
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
        
        # Process image with all transformations immediately but without blocking UI
        self.current_image = img_path
        self._pending_grayscale_path = img_path
        
        # Use QTimer.singleShot with 0ms to process immediately but yield control to UI
        QTimer.singleShot(0, lambda: self._process_image_immediately(pixmap, img_path))
        
        # Reset pan position when loading new image
        self.pan_offset_x = 0
        self.pan_offset_y = 0
    
    def _process_image_immediately(self, pixmap, img_path):
        """Process image with all transformations immediately but non-blocking."""
        # Only process if this is still the current image (user didn't navigate away)
        if img_path != self.current_image or img_path != self._pending_grayscale_path:
            return
        
        # Apply all transformations
        image = pixmap.toImage()
        
        # Apply grayscale first (if enabled)
        if self.settings.value("grayscale_enabled", False, type=bool):
            image = self._apply_improved_grayscale(image)
        
        # Apply flips
        if self.flipped_h:
            transform = QTransform().scale(-1, 1)
            image = image.transformed(transform)
        if self.flipped_v:
            transform = QTransform().scale(1, -1)
            image = image.transformed(transform)
        
        # Cache the final processed result
        self._cached_pixmap = QPixmap.fromImage(image)
        
        # Update display immediately
        self._update_zoom_display()
        
        self._pending_grayscale_path = None
    
    def _apply_improved_grayscale(self, image):
        """Apply fast grayscale conversion using Qt's optimized built-in method."""
        # Use Qt's fast built-in grayscale conversion - much faster than pixel-by-pixel
        return image.convertToFormat(QImage.Format_Grayscale8).convertToFormat(QImage.Format_RGB32)
        
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
        # Don't automatically show button overlay on timer toggle
        # Update button overlay to reflect new state
        self.button_overlay.set_pause_state(False, self._auto_advance_active)

    def change_bg_mode(self, mode):
        """Change the background color mode."""
        self.settings.setValue("bg_mode", mode)
        self.display_image(self.current_image) if self.current_image else None
    
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
    
    def show_keyboard_shortcuts(self):
        """Show the keyboard shortcuts help dialog."""
        dialog = KeyboardShortcutsDialog(self)
        dialog.exec()

    def toggle_grayscale(self, checked):
        """Toggle grayscale mode."""
        self.settings.setValue("grayscale_enabled", checked)
        if checked:
            self.image_label.parentWidget().setStyleSheet("background-color: #3b7dd8; color: #fff; border-radius: 4px;")
        else:
            self.image_label.parentWidget().setStyleSheet("")
        # Clear pending grayscale state
        self._pending_grayscale_path = None
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
            # Don't automatically show button overlay on timer reset
            self.button_overlay.set_pause_state(False, self._auto_advance_active)
        else:
            self.timer.stop()
            self._timer_paused = False
            self.progress_bar.set_remaining_time(0)
            self.progress_bar.hide()
            # Don't automatically show button overlay when timer disabled
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
            # Use QTimer.singleShot to ensure image loading happens in main thread
            QTimer.singleShot(0, self.show_random_image)
        else:
            self._update_progress()

    def _update_progress(self):
        """Update the progress bar display."""
        self.progress_bar.set_total_time(self.timer_interval)
        self.progress_bar.set_remaining_time(self.timer_remaining)

    def show_context_menu(self, pos):
        """Show the right-click context menu."""
        menu = QMenu(self)
        
        # --- Navigation ---
        prev_action = QAction("Previous", self)
        prev_action.triggered.connect(self.show_previous_image)
        prev_action.setEnabled(self.history_index > 0)
        menu.addAction(prev_action)
        
        next_action = QAction("Next", self)
        next_action.triggered.connect(self.show_next_or_random_image)
        menu.addAction(next_action)
        menu.addSeparator()
        
        # --- Timer Controls ---
        if self._auto_advance_active:
            if self._timer_paused:
                play_action = QAction("Play Timer", self)
                play_action.triggered.connect(self.toggle_pause)
                menu.addAction(play_action)
            else:
                pause_action = QAction("Pause Timer", self)
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
        
        # Timer interval submenu
        timer_menu = QMenu("Timer Interval", self)
        for label, value in [("30s", 30), ("1m", 60), ("2m", 120), ("5m", 300), ("10m", 600)]:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(self.timer_interval == value)
            act.triggered.connect(lambda checked, v=value: self.set_timer_interval(v))
            timer_menu.addAction(act)
        timer_menu.addSeparator()
        custom_act = QAction("Custom...", self)
        custom_act.triggered.connect(self.set_custom_timer_interval)
        timer_menu.addAction(custom_act)
        menu.addMenu(timer_menu)
        menu.addSeparator()
        
        # --- View Controls ---
        zoom_menu = QMenu("Zoom", self)
        
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.zoom_in)
        zoom_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out)
        zoom_menu.addAction(zoom_out_action)
        
        reset_zoom_action = QAction("Reset Zoom", self)
        reset_zoom_action.setShortcut("Ctrl+0")
        reset_zoom_action.triggered.connect(self.reset_zoom)
        zoom_menu.addAction(reset_zoom_action)
        
        reset_pan_action = QAction("Reset Pan Position", self)
        reset_pan_action.triggered.connect(self.reset_pan)
        reset_pan_action.setEnabled(self.zoom_factor > 1.0)  # Only enable when zoomed
        zoom_menu.addAction(reset_pan_action)
        menu.addMenu(zoom_menu)
        
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
        
        history_action = QAction("Show History Panel", self)
        history_action.setCheckable(True)
        history_action.setChecked(self.settings.value("show_history_panel", False, type=bool))
        history_action.toggled.connect(self.toggle_history_panel)
        menu.addAction(history_action)
        menu.addSeparator()
        
        # --- Image Transform ---
        transform_menu = QMenu("Transform", self)
        
        grayscale_action = QAction("Grayscale", self)
        grayscale_action.setCheckable(True)
        grayscale_action.setChecked(self.settings.value("grayscale_enabled", False, type=bool))
        grayscale_action.toggled.connect(self.toggle_grayscale)
        transform_menu.addAction(grayscale_action)
        
        flip_h_action = QAction("Flip Horizontal", self)
        flip_h_action.triggered.connect(self.flip_horizontal)
        transform_menu.addAction(flip_h_action)
        
        flip_v_action = QAction("Flip Vertical", self)
        flip_v_action.triggered.connect(self.flip_vertical)
        transform_menu.addAction(flip_v_action)
        menu.addMenu(transform_menu)
        menu.addSeparator()
        
        # --- File Actions ---
        open_explorer_action = QAction("Open in File Explorer", self)
        open_explorer_action.triggered.connect(self.open_current_in_explorer)
        open_explorer_action.setEnabled(self.current_image is not None)
        menu.addAction(open_explorer_action)
        
        welcome_action = QAction("Switch Collection/Folder...", self)
        welcome_action.triggered.connect(self.show_welcome_dialog)
        menu.addAction(welcome_action)
        
        # Add separator before help
        menu.addSeparator()
        
        # Keyboard shortcuts help
        shortcuts_action = QAction("Keyboard Shortcuts...", self)
        shortcuts_action.triggered.connect(self.show_keyboard_shortcuts)
        menu.addAction(shortcuts_action)
        
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
    
    def show_controls(self):
        """Show the button overlay controls on mouse movement."""
        if self.current_image:
            self.button_overlay._show_controls()
    
    def load_collection(self, collection: Collection, timer_enabled: bool = False, timer_interval: int = 60):
        """Load images from a collection with timer settings."""
        self.current_collection = collection
        self.folder = None  # Clear single folder
        
        # Configure timer settings
        self._auto_advance_active = timer_enabled
        self.timer_interval = timer_interval
        self.settings.setValue("auto_advance_enabled", self._auto_advance_active)
        self.settings.setValue("timer_interval", self.timer_interval)
        
        # For sorted collections (not random), we need to get sorted images
        if collection.sort_method == "random":
            # Show loading dialog for large collections and shuffle after loading
            loading_dialog = LoadingDialog(collection.paths, self)
            if loading_dialog.exec() == QDialog.Accepted:
                self.images = loading_dialog.get_images()
            else:
                self.images = []  # User cancelled loading
        else:
            # Get sorted images directly from collection
            self.images = collection.get_sorted_images()
        
        # Clear history
        self.history.clear()
        self.history_list.clear()
        self.history_list.repaint()
        self.current_image = None
        self.history_index = -1
        self.sorted_collection_index = 0  # Reset for new collection
        
        # Reset transformations
        self.flipped_h = False
        self.flipped_v = False
        
        # Reset first image flag to show controls for new collection
        self._first_image_shown = False
        
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
        
        # Show loading dialog for large folders
        loading_dialog = LoadingDialog([folder_path], self)
        if loading_dialog.exec() == QDialog.Accepted:
            self.images = loading_dialog.get_images()
        else:
            self.images = []  # User cancelled loading
        
        # Clear history
        self.history.clear()
        self.history_list.clear()
        self.history_list.repaint()
        self.current_image = None
        self.history_index = -1
        self.sorted_collection_index = 0  # Reset for new collection
        
        # Reset transformations
        self.flipped_h = False
        self.flipped_v = False
        
        # Reset first image flag to show controls for new folder
        self._first_image_shown = False
        
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