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
from PySide6.QtGui import QPixmap, QImage, QTransform, QAction, QPainter, QColor
from PySide6.QtCore import Qt, QTimer, QSize, QSettings, QThread, Signal

from .widgets import ClickableLabel, MinimalProgressBar, ButtonOverlay
from .startup_dialog import StartupDialog
from .loading_dialog import LoadingDialog
from .managers.image_display_manager import ImageDisplayManager
from .managers.media_controls_manager import MediaControlsManager
from .managers.history_manager import HistoryManager
from .managers.menu_manager import MenuManager
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
        self.current_image = None  # Still needed for compatibility
        self.timer_interval = self.settings.value("timer_interval", 60, type=int)
        self._auto_advance_active = self.settings.value("auto_advance_enabled", False, type=bool)
        self.show_history = self.settings.value("show_history_panel", False, type=bool)
        
        # Image display attributes (for compatibility - ImageDisplayManager is authoritative)
        self.zoom_factor = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        self._cached_pixmap = None
        
        
        self.init_ui()
        
        # Initialize image display manager
        self.image_display = ImageDisplayManager(self.image_label, self.settings)
        
        # Initialize history manager
        self.history_manager = HistoryManager()
        self.history_manager.setup_history_panel(self.history_list)
        
        # Initialize menu manager
        self.menu_manager = MenuManager(self)
        self.menu_manager.set_settings(self.settings)
        
        # Initialize media controls manager
        self.media_controls = MediaControlsManager(self.settings)
        self.media_controls.set_has_images(len(self.images) > 0)
        
        # Connect image display signals
        self.image_display.image_changed.connect(self._on_image_changed)
        self.image_display.zoom_changed.connect(self._on_zoom_changed)
        self.image_display.transform_changed.connect(self._on_transform_changed)
        
        # Connect history manager signals
        self.history_manager.image_requested.connect(self._on_history_image_requested)
        self.history_manager.history_navigation.connect(self._on_history_navigation)
        self.history_manager.random_image_requested.connect(self.show_random_image)
        
        # Connect menu manager signals with fast navigation for keyboard shortcuts
        self.menu_manager.previous_image_requested.connect(lambda: self.show_previous_image(fast_navigation=True))
        self.menu_manager.next_image_requested.connect(lambda: self.show_next_image(fast_navigation=True))
        self.menu_manager.next_or_random_requested.connect(lambda: self.show_next_or_random_image(fast_navigation=True))
        
        # Connect navigation completion signal
        self.menu_manager.navigation_completed.connect(self.menu_manager.on_navigation_completed)
        self.menu_manager.random_image_requested.connect(self.show_random_image)
        
        # Timer control signals
        self.menu_manager.timer_start_requested.connect(self.start_timer)
        self.menu_manager.timer_stop_requested.connect(self.stop_timer)
        self.menu_manager.timer_pause_requested.connect(self.toggle_pause)
        self.menu_manager.timer_interval_changed.connect(self.set_timer_interval)
        
        # View control signals
        self.menu_manager.zoom_in_requested.connect(self.zoom_in)
        self.menu_manager.zoom_out_requested.connect(self.zoom_out)
        self.menu_manager.reset_zoom_requested.connect(self.reset_zoom)
        self.menu_manager.reset_pan_requested.connect(self.reset_pan)
        self.menu_manager.background_mode_changed.connect(self.change_bg_mode)
        self.menu_manager.history_panel_toggled.connect(self.toggle_history_panel)
        
        # Transform signals
        self.menu_manager.grayscale_toggled.connect(self.toggle_grayscale)
        self.menu_manager.flip_horizontal_requested.connect(self.flip_horizontal)
        self.menu_manager.flip_vertical_requested.connect(self.flip_vertical)
        
        # File action signals
        self.menu_manager.open_in_explorer_requested.connect(self.open_current_in_explorer)
        self.menu_manager.switch_collection_requested.connect(self.show_welcome_dialog)
        self.menu_manager.keyboard_shortcuts_requested.connect(self.show_keyboard_shortcuts)
        
        # Connect media controls signals
        self.media_controls.timer_expired.connect(self.show_random_image)
        self.media_controls.timer_state_changed.connect(self._on_timer_state_changed)
        self.media_controls.progress_updated.connect(self._on_progress_updated)
        
        self._initial_image_shown = False
    
    # ImageDisplayManager signal handlers
    def _on_image_changed(self, img_path):
        """Handle image changed signal from ImageDisplayManager."""
        # Only add to history if this was a new image load (not navigation)
        # The HistoryManager will handle adding images via its own methods
        self.current_image = img_path
        self.update_image_info(img_path)
        self._update_title(img_path)
    
    def _on_zoom_changed(self, zoom_factor):
        """Handle zoom changed signal from ImageDisplayManager."""
        # Update any UI elements that show zoom level if needed
        pass
    
    def _on_transform_changed(self):
        """Handle transform changed signal from ImageDisplayManager."""
        # Update any UI elements that show transform state if needed
        pass
    
    # HistoryManager signal handlers
    def _on_history_image_requested(self, img_path):
        """Handle image request from HistoryManager."""
        self.image_display.display_image(img_path)
        self.update_image_info(img_path)
        if self.media_controls.is_active():
            self.media_controls.reset_timer()
    
    def _on_history_navigation(self, img_path, is_forward):
        """Handle navigation from HistoryManager."""
        # Navigate through history - preserve transforms (grayscale, flips)
        self.image_display.display_image(img_path)
        self.update_image_info(img_path)
        if self.media_controls.is_active():
            self.media_controls.reset_timer()
    
    def center_on_screen(self):
        """Center the window on the screen."""
        screen = QApplication.primaryScreen().availableGeometry()
        window = self.frameGeometry()
        x = (screen.width() - window.width()) // 2 + screen.x()
        y = (screen.height() - window.height()) // 2 + screen.y()
        self.move(x, y)
    

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
        """Handle show event to center window and display initial image."""
        super().showEvent(event)
        
        # Center window on first show
        if not hasattr(self, '_centered'):
            QTimer.singleShot(0, self.center_on_screen)
            self._centered = True
        
        # Show initial image if available
        if not self._initial_image_shown and self.images:
            # For initial image load, preserve user settings (grayscale, etc.)
            self.show_random_image(preserve_transforms=True)
            self._initial_image_shown = True
        
        # Update title and image info on show
        self.update_image_info()
        self._update_title()

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts via MenuManager."""
        # Update menu manager state for proper handling
        self._update_menu_manager_state()
        
        # Delegate to menu manager
        if self.menu_manager.handle_key_press(event):
            return  # Key was handled
        
        # Fall back to default handling
        super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        """Handle key release events via MenuManager."""
        # Delegate to menu manager for navigation key handling
        if self.menu_manager.handle_key_release(event):
            return  # Key was handled
        
        # Fall back to default handling
        super().keyReleaseEvent(event)
    
    def _update_menu_manager_state(self):
        """Update MenuManager state for accurate menu handling."""
        history_info = self.history_manager.get_history_info()
        
        self.menu_manager.update_state(
            history_index=history_info['current_index'],
            history_length=history_info['total_count'],
            timer_interval=self.media_controls.get_timer_interval(),
            auto_advance_active=self.media_controls.is_active(),
            timer_paused=self.media_controls.is_paused(),
            zoom_factor=self.zoom_factor,
            current_image=self.current_image
        )
        
    # MediaControlsManager signal handlers
    def _on_timer_state_changed(self, active, paused):
        """Handle timer state changes from MediaControlsManager."""
        # Update button overlay to reflect timer state
        if hasattr(self, 'button_overlay'):
            self.button_overlay.set_pause_state(paused, active)
        
        # Show/hide progress bar based on timer state
        if hasattr(self, 'progress_bar'):
            if active:
                self.progress_bar.show()
            else:
                self.progress_bar.hide()
    
    def _on_progress_updated(self, remaining, total):
        """Handle progress updates from MediaControlsManager."""
        # Update progress bar
        if hasattr(self, 'progress_bar'):
            self.progress_bar.set_total_time(total)
            self.progress_bar.set_remaining_time(remaining)

    def toggle_pause(self):
        """Toggle pause state of the auto-advance timer."""
        self.media_controls.toggle_pause()
    
    def start_timer(self):
        """Start/enable the auto-advance timer."""
        self.media_controls.start_timer()

    def stop_timer(self):
        """Stop and disable the auto-advance timer completely."""
        self.media_controls.stop_timer()

    def show_previous_image(self, fast_navigation=True):
        """Show the previous image in history."""
        if self.history_manager.history_index > 0:
            self.history_manager.history_index -= 1
            img_path = self.history_manager.history[self.history_manager.history_index]

            # Preload previous images for smooth navigation
            if fast_navigation and self.history_manager.history_index > 0:
                preload_paths = []
                for i in range(1, 6):  # Preload 5 previous images
                    idx = self.history_manager.history_index - i
                    if idx >= 0:
                        preload_paths.append(self.history_manager.history[idx])
                if preload_paths:
                    self.image_display.preload_images(preload_paths)

            # Navigate through history - preserve transforms (grayscale, flips)
            # Use the image display manager with fast mode for rapid navigation
            success = self.image_display.display_image(img_path, fast_mode=fast_navigation)
            if success:
                self.history_manager.current_image = img_path

                # Update UI based on navigation speed preference
                if fast_navigation:
                    self._update_title_only(img_path)
                else:
                    self.update_image_info(img_path)

                # Reset timer if active
                if self.media_controls.is_active():
                    self.media_controls.reset_timer()

    def show_next_image(self, fast_navigation=True):
        """Show the next image in history or a random one."""
        if self.history_manager.history_index < len(self.history_manager.history) - 1:
            self.history_manager.history_index += 1
            img_path = self.history_manager.history[self.history_manager.history_index]

            # Preload next images for smooth forward navigation
            if fast_navigation:
                preload_paths = []
                for i in range(1, 6):  # Preload 5 next images
                    idx = self.history_manager.history_index + i
                    if idx < len(self.history_manager.history):
                        preload_paths.append(self.history_manager.history[idx])
                if preload_paths:
                    self.image_display.preload_images(preload_paths)

            # Navigate through history - preserve transforms (grayscale, flips)
            # Use the image display manager with fast mode for rapid navigation
            success = self.image_display.display_image(img_path, fast_mode=fast_navigation)
            if success:
                self.history_manager.current_image = img_path

                # Update UI based on navigation speed preference
                if fast_navigation:
                    self._update_title_only(img_path)
                else:
                    self.update_image_info(img_path)

                # Reset timer if active
                if self.media_controls.is_active():
                    self.media_controls.reset_timer()
        else:
            self.show_random_image()

    def show_next_or_random_image(self, fast_navigation=True):
        """Show next image or random if at end of history."""
        if self.history_manager.has_next():
            self.show_next_image(fast_navigation=fast_navigation)
        else:
            # Continue navigation with preserved transforms (grayscale, flips)
            self.show_random_image(preserve_transforms=True)

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
        
        # OPTIMIZATION: Use cached pixmap if available to avoid redundant loading
        base = os.path.basename(img_path)
        cached_pixmap = self.image_display._cached_pixmap
        if cached_pixmap and not cached_pixmap.isNull():
            info = f"{cached_pixmap.width()}x{cached_pixmap.height()}"
        else:
            # Fallback to loading only if no cache available
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
    
    def _update_title_only(self, img_path=None):
        """Fast title update for rapid navigation without expensive operations."""
        if img_path and os.path.exists(img_path):
            base = os.path.basename(img_path)
            if self.current_collection:
                self._update_title_for_collection()
            else:
                self._update_title(img_path, base)  # Use filename as info during rapid nav
        else:
            self._update_title()

    def show_random_image(self, preserve_transforms=False):
        """Display a random image from the current folder."""
        if not self.images:
            return
            
        # Reset transformations only if explicitly requested (new random image)
        if not preserve_transforms:
            self.image_display.reset_all_transforms()
        
        # Check if we're using a sorted collection (not random)
        if self.current_collection and self.current_collection.sort_method != "random":
            self.history_manager.get_sequential_image(
                self.current_collection.sort_method,
                "desc" if self.current_collection.sort_descending else "asc"
            )
            return
        
        # Get random image through history manager
        self.history_manager.get_random_image()
    
    def show_next_sorted_image(self):
        """Show the next image in a sorted collection."""
        if not self.images or not self.current_collection:
            return
            
        # Reset transformations
        self.image_display.reset_all_transforms()
        
        # Get next sequential image through history manager
        self.history_manager.get_sequential_image(
            self.current_collection.sort_method,
            "desc" if self.current_collection.sort_descending else "asc"
        )

    def display_image(self, img_path):
        """Display an image with current transformations and settings."""
        # Delegate to image display manager
        success = self.image_display.display_image(img_path)
        
        if not success:
            return
        
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

    def _is_image_too_large(self, img_path):
        """Check if an image file is likely too large for Qt to handle."""
        try:
            import os
            file_size_mb = os.path.getsize(img_path) / (1024 * 1024)
            # Conservative estimate: files >100MB are likely to cause issues
            return file_size_mb > 100
        except:
            return False
    

    def resizeEvent(self, event):
        """Handle window resize to redisplay current image."""
        if self.image_display._cached_pixmap:
            self.image_display._update_zoom_display()
        super().resizeEvent(event)




    def toggle_history_panel(self, checked):
        """Toggle the history panel visibility."""
        self.history_manager.toggle_history_panel(bool(checked), self.settings)

    def toggle_timer(self, checked):
        """Toggle the auto-advance timer from context menu."""
        if checked:
            self.media_controls.start_timer()
        else:
            self.media_controls.stop_timer()
        
        # Update compatibility attributes
        self._auto_advance_active = bool(checked)

    def change_bg_mode(self, mode):
        """Change the background color mode."""
        self.settings.setValue("bg_mode", mode)
        if self.current_image:
            self.image_display.display_image(self.current_image)
    
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
                rgb_match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', style)
                if rgb_match:
                    r, g, b = map(int, rgb_match.groups())
                    return QColor(r, g, b)
            
            # Fallback to dark gray if we can't extract the adaptive color
            return QColor(40, 40, 40)
        else:
            # Default to black
            return QColor(0, 0, 0)
    
    def show_keyboard_shortcuts(self):
        """Show the keyboard shortcuts help dialog."""
        dialog = KeyboardShortcutsDialog(self)
        dialog.exec()

    def toggle_grayscale(self, checked):
        """Toggle grayscale mode."""
        self.settings.setValue("grayscale_enabled", checked)
        self.image_display.is_grayscale = checked
        if self.current_image:
            self.image_display.display_image(self.current_image)

    def flip_horizontal(self):
        """Flip the current image horizontally."""
        self.image_display.flip_horizontal()

    def flip_vertical(self):
        """Flip the current image vertically."""
        self.image_display.flip_vertical()

    def overlay_resize_event(self, original_resize_event):
        """Create a custom resize event handler for overlay positioning."""
        def new_resize_event(event):
            # Call the original resize event
            if original_resize_event:
                original_resize_event(event)
            # Position overlays immediately - no delay needed
            self._update_overlay_positions()
        return new_resize_event
    
    def _update_overlay_positions(self):
        """Update positions of progress bar and button overlay."""
        if self.image_label.width() > 0 and self.image_label.height() > 0:
            # Position progress bar at bottom, full width
            self.progress_bar.setGeometry(0, self.image_label.height() - 4, self.image_label.width(), 4)
            # Position button overlay at bottom center
            overlay_x = (self.image_label.width() - self.button_overlay.width()) // 2
            overlay_y = self.image_label.height() - self.button_overlay.height() - 20
            self.button_overlay.move(overlay_x, overlay_y)



    def show_context_menu(self, pos):
        """Show the right-click context menu via MenuManager."""
        # Update menu manager state
        self._update_menu_manager_state()
        
        # Delegate to menu manager
        self.menu_manager.show_context_menu(pos)
        return
        
        # OLD CODE BELOW - TO BE REMOVED
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
        self.media_controls.set_timer_interval(value)
        # Update local references for compatibility
        self.timer_interval = value

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
        self.image_display.handle_wheel_zoom(angle)

    def zoom_in(self):
        """Zoom in on the current image."""
        self.image_display.zoom_in()

    def zoom_out(self):
        """Zoom out on the current image."""
        self.image_display.zoom_out()

    def reset_zoom(self):
        """Reset zoom to 100%."""
        self.image_display.reset_zoom()

    def start_panning(self, pos):
        """Start panning operation."""
        self.image_display.start_panning(pos)

    def handle_panning(self, delta):
        """Handle panning movement with improved logic."""
        self.image_display.handle_panning(delta)

    def end_panning(self):
        """End panning operation."""
        self.image_display.end_panning()

    def reset_pan(self):
        """Reset pan position to center."""
        self.image_display.reset_pan()
    
    def show_controls(self):
        """Show the button overlay controls on mouse movement."""
        if self.current_image:
            self.button_overlay._show_controls()
    
    
    def load_collection(self, collection: Collection, timer_enabled: bool = False, timer_interval: int = 60):
        """Load images from a collection with timer settings."""
        self.current_collection = collection
        self.folder = None  # Clear single folder
        
        # Configure timer settings via MediaControlsManager
        self.media_controls.set_timer_interval(timer_interval)
        if timer_enabled:
            self.media_controls.start_timer()
        else:
            self.media_controls.stop_timer()
        
        # Update local references for compatibility
        self.timer_interval = timer_interval
        self._auto_advance_active = timer_enabled
        
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
        
        # Clear history and set new images in history manager
        self.history_manager.clear_history()
        self.history_manager.set_images(self.images)
        
        # Update MediaControlsManager about image availability
        self.media_controls.set_has_images(len(self.images) > 0)
        
        # Reset positional transforms but preserve user preferences (grayscale)
        self.image_display.reset_positional_transforms_without_display()
        
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
    
    def load_folder(self, folder_path: str, timer_enabled: bool = False, timer_interval: int = 60):
        """Load images from a single folder (quick shuffle mode) with timer settings."""
        self.folder = folder_path
        self.current_collection = None  # Clear collection
        
        # Configure timer settings via MediaControlsManager
        self.media_controls.set_timer_interval(timer_interval)
        if timer_enabled:
            self.media_controls.start_timer()
        else:
            self.media_controls.stop_timer()
        
        # Update local references for compatibility
        self.timer_interval = timer_interval
        self._auto_advance_active = timer_enabled
        
        # Save as last folder for quick access
        self.settings.setValue("last_folder", folder_path)
        
        # Show loading dialog for large folders
        loading_dialog = LoadingDialog([folder_path], self)
        if loading_dialog.exec() == QDialog.Accepted:
            self.images = loading_dialog.get_images()
        else:
            self.images = []  # User cancelled loading
        
        # Clear history and set new images in history manager
        self.history_manager.clear_history()
        self.history_manager.set_images(self.images)
        
        # Update MediaControlsManager about image availability
        self.media_controls.set_has_images(len(self.images) > 0)
        
        # Reset positional transforms but preserve user preferences (grayscale)
        self.image_display.reset_positional_transforms_without_display()
        
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