"""Main window class for the Random Image Viewer application."""

import sys
import os
import random
import subprocess
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QVBoxLayout, QWidget,
    QListWidget, QListWidgetItem, QSplitter, QSizePolicy,
    QMenu, QInputDialog
)
from PySide6.QtGui import QPixmap, QImage, QTransform, QAction
from PySide6.QtCore import Qt, QTimer, QSize, QSettings

from .widgets import ClickableLabel, MinimalProgressBar, ButtonOverlay
from ..core.image_utils import get_images_in_folder, set_adaptive_bg


class RandomImageViewer(QMainWindow):
    """Main application window for viewing random images."""
    
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setWindowTitle("Random Image Viewer")
        self.setGeometry(100, 100, 950, 650)
        
        # Initialize settings
        self.settings = QSettings("random-image-viewer", "RandomImageViewer")
        last_folder = self.settings.value("last_folder", type=str)
        if last_folder and os.path.exists(last_folder):
            self.folder = last_folder
        else:
            self.folder = os.getcwd()
        
        # Initialize state
        self.images = get_images_in_folder(self.folder)
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
        
        # Initialize timer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_timer_tick)
        
        self.init_ui()
        self.update_image_info()
        self._update_title()
        self._initial_image_shown = False

    def init_ui(self):
        """Initialize the user interface."""
        central_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(central_splitter)

        # Image display area
        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        image_layout.setContentsMargins(6, 6, 6, 6)

        self.image_label = ClickableLabel("Open a folder to start", alignment=Qt.AlignCenter)
        self.image_label.setScaledContents(False)
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setToolTip("")
        
        # Connect signals
        self.image_label.back.connect(self.show_previous_image)
        self.image_label.forward.connect(self.show_next_image)
        self.image_label.wheel_zoom.connect(self.handle_wheel_zoom)
        
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
            return
        
        self._timer_paused = not self._timer_paused
        if self._timer_paused:
            self.timer.stop()
        else:
            self.timer.start()
        
        self.button_overlay.set_pause_state(self._timer_paused)

    def stop_timer(self):
        """Stop the auto-advance timer completely."""
        self._auto_advance_active = False
        self._timer_paused = False
        self.settings.setValue("auto_advance_enabled", False)
        self._reset_timer()
        self.button_overlay.set_pause_state(False)

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
            self.folder = folder
            self.settings.setValue("last_folder", folder)
            self.images = get_images_in_folder(folder)
            self.history.clear()
            self.history_list.clear()
            self.history_list.repaint()
            self.current_image = None
            self.history_index = -1
            self.flipped_h = False
            self.flipped_v = False
            self.update_image_info()
            self._update_title()
            if self.images:
                self.show_random_image()
            else:
                self.image_label.setText("No images found in selected folder or its subfolders.")
            self._reset_timer()

    def _update_title(self, img_path=None, info=None):
        """Update the window title with current image info."""
        count = len(self.images)
        folder_name = os.path.basename(self.folder) if self.folder else ""
        if img_path and info:
            base = os.path.basename(img_path)
            self.setWindowTitle(f"Random Image Viewer - {base} ({info}) - {img_path}")
        else:
            self.setWindowTitle(f"Random Image Viewer - {folder_name} ({count} images found)")

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
        
        # Update title with image info
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            info = f"{pixmap.width()}x{pixmap.height()}"
        else:
            info = os.path.basename(img_path)
        self._update_title(img_path, info)

    def _load_and_process_image(self, img_path):
        """Load image from disk and apply transformations, caching the result."""
        pixmap = QPixmap(img_path)
        if pixmap.isNull():
            self.image_label.setText("Cannot load image.")
            self._cached_pixmap = None
            return
        
        # Apply transformations
        image = pixmap.toImage()
        if self.settings.value("grayscale_enabled", False, type=bool):
            image = image.convertToFormat(QImage.Format_Grayscale8)
        if self.flipped_h:
            transform = QTransform().scale(-1, 1)
            image = image.transformed(transform)
        if self.flipped_v:
            transform = QTransform().scale(1, -1)
            image = image.transformed(transform)
        
        # Cache the processed pixmap
        self._cached_pixmap = QPixmap.fromImage(image)
        self.current_image = img_path
        
    def _update_zoom_display(self):
        """Update the display with current zoom level using cached pixmap."""
        if not self._cached_pixmap:
            return
            
        # Calculate target size based on zoom factor
        base_size = self.image_label.size()
        target_size = base_size * self.zoom_factor
        
        # Scale the cached pixmap (this is much faster than reprocessing)
        scaled = self._cached_pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
        """Toggle the auto-advance timer."""
        self._auto_advance_active = bool(checked)
        self.settings.setValue("auto_advance_enabled", self._auto_advance_active)
        self._reset_timer()

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
            self.button_overlay.show()
            self.button_overlay.set_pause_state(False)
        else:
            self.timer.stop()
            self._timer_paused = False
            self.progress_bar.set_remaining_time(0)
            self.progress_bar.hide()
            self.button_overlay.hide()

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
        
        # --- Main actions ---
        open_action = QAction("Open Folder", self)
        open_action.triggered.connect(self.choose_folder)
        menu.addAction(open_action)
        menu.addSeparator()
        
        prev_action = QAction("Previous Image", self)
        prev_action.triggered.connect(self.show_previous_image)
        menu.addAction(prev_action)
        
        next_action = QAction("Next Random Image", self)
        next_action.triggered.connect(self.show_next_or_random_image)
        menu.addAction(next_action)
        
        open_explorer_action = QAction("Open in Explorer", self)
        open_explorer_action.triggered.connect(self.open_current_in_explorer)
        menu.addAction(open_explorer_action)
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
        menu.addSeparator()
        
        # --- Timer ---
        timer_action = QAction("Enable Timer", self)
        timer_action.setCheckable(True)
        timer_action.setChecked(self._auto_advance_active)
        timer_action.toggled.connect(self.toggle_timer)
        menu.addAction(timer_action)
        
        # Timer interval submenu
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
        self._update_zoom_display()

    def reset_zoom(self):
        """Reset zoom to 100%."""
        self.zoom_factor = 1.0
        self._update_zoom_display()