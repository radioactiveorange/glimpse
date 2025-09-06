"""Menu and keyboard shortcut manager for the Random Image Viewer."""

from PySide6.QtWidgets import QMenu, QInputDialog
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QObject, Signal


class MenuManager(QObject):
    """Manages context menus and keyboard shortcuts."""
    
    # Signals for menu actions
    previous_image_requested = Signal()
    next_image_requested = Signal()
    next_or_random_requested = Signal()
    random_image_requested = Signal()
    
    # Timer control signals
    timer_toggle_requested = Signal()
    timer_start_requested = Signal()
    timer_stop_requested = Signal()
    timer_pause_requested = Signal()
    timer_interval_changed = Signal(int)
    
    # View control signals
    zoom_in_requested = Signal()
    zoom_out_requested = Signal()
    reset_zoom_requested = Signal()
    reset_pan_requested = Signal()
    background_mode_changed = Signal(str)
    history_panel_toggled = Signal(bool)
    
    # Transform signals
    grayscale_toggled = Signal(bool)
    flip_horizontal_requested = Signal()
    flip_vertical_requested = Signal()
    
    # File action signals  
    open_in_explorer_requested = Signal()
    switch_collection_requested = Signal()
    keyboard_shortcuts_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.settings = None
        
        # State tracking
        self.history_index = 0
        self.history_length = 0
        self.timer_interval = 60
        self.auto_advance_active = False
        self.timer_paused = False
        self.zoom_factor = 1.0
        self.current_image = None
        
    def set_settings(self, settings):
        """Set the settings object for accessing configuration."""
        self.settings = settings
        
    def update_state(self, **kwargs):
        """Update the internal state for menu enabling/disabling."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                
    def handle_key_press(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key_Left:
            self.previous_image_requested.emit()
            return True
        elif event.key() == Qt.Key_Right:
            self.next_or_random_requested.emit()
            return True
        elif event.key() == Qt.Key_Space:
            self.timer_pause_requested.emit()
            return True
        elif event.key() == Qt.Key_F:
            self.flip_horizontal_requested.emit()
            return True
        elif event.key() == Qt.Key_G:
            self.grayscale_toggled.emit(not self.settings.value("grayscale_enabled", False, type=bool))
            return True
        elif event.key() == Qt.Key_B:
            self._cycle_background_mode()
            return True
        elif event.key() == Qt.Key_H:
            current_visibility = self.settings.value("show_history_panel", False, type=bool)
            self.history_panel_toggled.emit(not current_visibility)
            return True
        elif event.key() == Qt.Key_Escape:
            self.switch_collection_requested.emit()
            return True
        elif event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
                self.zoom_in_requested.emit()
                return True
            elif event.key() == Qt.Key_Minus:
                self.zoom_out_requested.emit()
                return True
            elif event.key() == Qt.Key_0:
                self.reset_zoom_requested.emit()
                return True
        
        return False  # Key not handled
        
    def _cycle_background_mode(self):
        """Cycle through background modes."""
        if not self.settings:
            return
            
        modes = ["Black", "Gray", "Adaptive Color"]
        current_mode = self.settings.value("bg_mode", "Black")
        
        try:
            current_index = modes.index(current_mode)
            next_index = (current_index + 1) % len(modes)
            next_mode = modes[next_index]
        except ValueError:
            # If current mode is not in list, default to first mode
            next_mode = modes[0]
        
        self.background_mode_changed.emit(next_mode)
        
    def show_context_menu(self, pos):
        """Show the right-click context menu."""
        if not self.parent_window or not self.settings:
            return
            
        menu = QMenu(self.parent_window)
        
        # --- Navigation ---
        prev_action = QAction("Previous", self.parent_window)
        prev_action.triggered.connect(lambda: self.previous_image_requested.emit())
        prev_action.setEnabled(self.history_index > 0)
        menu.addAction(prev_action)
        
        next_action = QAction("Next", self.parent_window)
        next_action.triggered.connect(lambda: self.next_or_random_requested.emit())
        menu.addAction(next_action)
        menu.addSeparator()
        
        random_action = QAction("Random", self.parent_window)
        random_action.triggered.connect(lambda: self.random_image_requested.emit())
        menu.addAction(random_action)
        menu.addSeparator()
        
        # --- Timer Controls ---
        # Timer toggle
        if self.auto_advance_active:
            if self.timer_paused:
                play_action = QAction("Play Timer", self.parent_window)
                play_action.triggered.connect(lambda: self.timer_pause_requested.emit())
                menu.addAction(play_action)
            else:
                pause_action = QAction("Pause Timer", self.parent_window)
                pause_action.triggered.connect(lambda: self.timer_pause_requested.emit())
                menu.addAction(pause_action)
        else:
            start_action = QAction("Start Timer", self.parent_window)
            start_action.triggered.connect(lambda: self.timer_start_requested.emit())
            menu.addAction(start_action)
        
        stop_action = QAction("Stop Timer", self.parent_window)
        stop_action.triggered.connect(lambda: self.timer_stop_requested.emit())
        stop_action.setEnabled(self.auto_advance_active)
        menu.addAction(stop_action)
        
        # Timer interval submenu
        timer_menu = QMenu("Timer Interval", self.parent_window)
        for label, value in [("30s", 30), ("1m", 60), ("2m", 120), ("5m", 300), ("10m", 600)]:
            act = QAction(label, self.parent_window)
            act.setCheckable(True)
            act.setChecked(self.timer_interval == value)
            act.triggered.connect(lambda checked, v=value: self.timer_interval_changed.emit(v))
            timer_menu.addAction(act)
        
        timer_menu.addSeparator()
        custom_act = QAction("Custom...", self.parent_window)
        custom_act.triggered.connect(self._show_custom_timer_dialog)
        timer_menu.addAction(custom_act)
        menu.addMenu(timer_menu)
        menu.addSeparator()
        
        # --- View Controls ---
        zoom_menu = QMenu("Zoom", self.parent_window)
        
        zoom_in_action = QAction("Zoom In", self.parent_window)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(lambda: self.zoom_in_requested.emit())
        zoom_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom Out", self.parent_window)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(lambda: self.zoom_out_requested.emit())
        zoom_menu.addAction(zoom_out_action)
        
        reset_zoom_action = QAction("Reset Zoom", self.parent_window)
        reset_zoom_action.setShortcut("Ctrl+0")
        reset_zoom_action.triggered.connect(lambda: self.reset_zoom_requested.emit())
        zoom_menu.addAction(reset_zoom_action)
        
        reset_pan_action = QAction("Reset Pan Position", self.parent_window)
        reset_pan_action.triggered.connect(lambda: self.reset_pan_requested.emit())
        reset_pan_action.setEnabled(self.zoom_factor > 1.0)  # Only enable when zoomed
        zoom_menu.addAction(reset_pan_action)
        menu.addMenu(zoom_menu)
        
        # Background color submenu
        bg_menu = QMenu("Background Color", self.parent_window)
        current_bg = self.settings.value("bg_mode", "Black")
        for mode in ["Black", "Gray", "Adaptive Color"]:
            act = QAction(mode, self.parent_window)
            act.setCheckable(True)
            act.setChecked(current_bg == mode)
            act.triggered.connect(lambda checked, m=mode: self.background_mode_changed.emit(m))
            bg_menu.addAction(act)
        menu.addMenu(bg_menu)
        
        history_action = QAction("Show History Panel", self.parent_window)
        history_action.setCheckable(True)
        history_action.setChecked(self.settings.value("show_history_panel", False, type=bool))
        history_action.toggled.connect(lambda checked: self.history_panel_toggled.emit(checked))
        menu.addAction(history_action)
        menu.addSeparator()
        
        # --- Image Transform ---
        transform_menu = QMenu("Transform", self.parent_window)
        
        grayscale_action = QAction("Grayscale", self.parent_window)
        grayscale_action.setCheckable(True)
        grayscale_action.setChecked(self.settings.value("grayscale_enabled", False, type=bool))
        grayscale_action.toggled.connect(lambda checked: self.grayscale_toggled.emit(checked))
        transform_menu.addAction(grayscale_action)
        
        flip_h_action = QAction("Flip Horizontal", self.parent_window)
        flip_h_action.triggered.connect(lambda: self.flip_horizontal_requested.emit())
        transform_menu.addAction(flip_h_action)
        
        flip_v_action = QAction("Flip Vertical", self.parent_window)
        flip_v_action.triggered.connect(lambda: self.flip_vertical_requested.emit())
        transform_menu.addAction(flip_v_action)
        menu.addMenu(transform_menu)
        menu.addSeparator()
        
        # --- File Actions ---
        open_explorer_action = QAction("Open in File Explorer", self.parent_window)
        open_explorer_action.triggered.connect(lambda: self.open_in_explorer_requested.emit())
        open_explorer_action.setEnabled(self.current_image is not None)
        menu.addAction(open_explorer_action)
        
        welcome_action = QAction("Switch Collection/Folder...", self.parent_window)
        welcome_action.triggered.connect(lambda: self.switch_collection_requested.emit())
        menu.addAction(welcome_action)
        
        menu.addSeparator()
        
        # Keyboard shortcuts help
        shortcuts_action = QAction("Keyboard Shortcuts...", self.parent_window)
        shortcuts_action.triggered.connect(lambda: self.keyboard_shortcuts_requested.emit())
        menu.addAction(shortcuts_action)
        
        # Show the menu
        menu.exec(self.parent_window.mapToGlobal(pos))
        
    def _show_custom_timer_dialog(self):
        """Show dialog for custom timer interval."""
        if not self.parent_window:
            return
            
        value, ok = QInputDialog.getInt(
            self.parent_window,
            "Custom Timer Interval",
            "Enter interval in seconds:",
            self.timer_interval, 5, 3600, 5
        )
        
        if ok:
            self.timer_interval_changed.emit(value)