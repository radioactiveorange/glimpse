"""Menu and keyboard shortcut manager for the Random Image Viewer."""

from PySide6.QtWidgets import QMenu, QInputDialog
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QObject, Signal, QTimer


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
    
    # Navigation completion signals
    navigation_completed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = None
        
        # Navigation queue for rapid key handling (including key repeat)
        self.navigation_queue = []
        self.navigation_timer = QTimer()
        self.navigation_timer.setSingleShot(True)
        self.navigation_timer.timeout.connect(self._process_navigation_queue)
        self.navigation_delay = 1  # ms - minimal delay for maximum speed
        self.is_navigating = False  # Prevent navigation queue buildup
        
    def set_settings(self, settings):
        """Set the settings object for accessing configuration."""
        self.settings = settings
                
    def handle_key_press(self, event):
        """Handle keyboard shortcuts with key repeat throttling."""
        if event.key() == Qt.Key_Left:
            self._handle_navigation_key('left', event.isAutoRepeat())
            return True
        elif event.key() == Qt.Key_Right:
            self._handle_navigation_key('right', event.isAutoRepeat())
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
        
        return False
    
    def _handle_navigation_key(self, direction, is_auto_repeat):
        """Handle navigation keys with smart queuing for rapid navigation."""
        # Queue navigation for both first press and auto-repeat (holding key)
        self._queue_navigation(direction)
    
    def _queue_navigation(self, direction):
        """Queue navigation for continuous cycling like a normal image viewer."""
        # Add to queue without consolidation - process each keypress
        self.navigation_queue.append(direction)

        # Process immediately if not already navigating
        if not self.is_navigating and not self.navigation_timer.isActive():
            self._process_navigation_queue()
    
    def _process_navigation_queue(self):
        """Process the navigation queue with throttling."""
        if not self.navigation_queue or self.is_navigating:
            return
        
        self.is_navigating = True
        
        # Process one navigation at a time
        direction = self.navigation_queue.pop(0)
        
        if direction == 'left':
            self.previous_image_requested.emit()
        else:  # right
            self.next_or_random_requested.emit()
        
        # Emit completion signal to reset flag
        self.navigation_completed.emit()
        
        # Schedule next processing if queue not empty
        if self.navigation_queue:
            self.navigation_timer.start(self.navigation_delay)
        else:
            self.is_navigating = False
    
    def on_navigation_completed(self):
        """Called when navigation is actually completed."""
        self.is_navigating = False
        
        # Continue processing queue if there are pending navigations
        if self.navigation_queue and not self.navigation_timer.isActive():
            self.navigation_timer.start(self.navigation_delay)
    
    def handle_key_release(self, event):
        """Handle key release events."""
        # No special handling needed - navigation happens on key press/repeat
        return False
        
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
        
    def show_context_menu(self, global_pos, parent_widget, state):
        """Show the right-click context menu.

        Args:
            global_pos: QPoint in global screen coordinates.
            parent_widget: QWidget to parent menus/actions against.
            state: dict with keys history_index, history_length, timer_interval,
                   auto_advance_active, timer_paused, zoom_factor, current_image.
        """
        if not self.settings:
            return

        history_index = state.get('history_index', 0)
        auto_advance_active = state.get('auto_advance_active', False)
        timer_paused = state.get('timer_paused', False)
        timer_interval = state.get('timer_interval', 60)
        zoom_factor = state.get('zoom_factor', 1.0)
        current_image = state.get('current_image', None)

        menu = QMenu(parent_widget)

        # --- Navigation ---
        prev_action = QAction("Previous", parent_widget)
        prev_action.triggered.connect(lambda: self.previous_image_requested.emit())
        prev_action.setEnabled(history_index > 0)
        menu.addAction(prev_action)

        next_action = QAction("Next", parent_widget)
        next_action.triggered.connect(lambda: self.next_or_random_requested.emit())
        menu.addAction(next_action)
        menu.addSeparator()

        random_action = QAction("Random", parent_widget)
        random_action.triggered.connect(lambda: self.random_image_requested.emit())
        menu.addAction(random_action)
        menu.addSeparator()

        # --- Timer Controls ---
        if auto_advance_active:
            if timer_paused:
                play_action = QAction("Play Timer", parent_widget)
                play_action.triggered.connect(lambda: self.timer_pause_requested.emit())
                menu.addAction(play_action)
            else:
                pause_action = QAction("Pause Timer", parent_widget)
                pause_action.triggered.connect(lambda: self.timer_pause_requested.emit())
                menu.addAction(pause_action)
        else:
            start_action = QAction("Start Timer", parent_widget)
            start_action.triggered.connect(lambda: self.timer_start_requested.emit())
            menu.addAction(start_action)

        stop_action = QAction("Stop Timer", parent_widget)
        stop_action.triggered.connect(lambda: self.timer_stop_requested.emit())
        stop_action.setEnabled(auto_advance_active)
        menu.addAction(stop_action)

        # Timer interval submenu
        timer_menu = QMenu("Timer Interval", parent_widget)
        for label, value in [("30s", 30), ("1m", 60), ("2m", 120), ("5m", 300), ("10m", 600)]:
            act = QAction(label, parent_widget)
            act.setCheckable(True)
            act.setChecked(timer_interval == value)
            act.triggered.connect(lambda checked, v=value: self.timer_interval_changed.emit(v))
            timer_menu.addAction(act)

        timer_menu.addSeparator()
        custom_act = QAction("Custom...", parent_widget)
        custom_act.triggered.connect(lambda: self._show_custom_timer_dialog(parent_widget, timer_interval))
        timer_menu.addAction(custom_act)
        menu.addMenu(timer_menu)
        menu.addSeparator()

        # --- View Controls ---
        zoom_menu = QMenu("Zoom", parent_widget)

        zoom_in_action = QAction("Zoom In", parent_widget)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(lambda: self.zoom_in_requested.emit())
        zoom_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", parent_widget)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(lambda: self.zoom_out_requested.emit())
        zoom_menu.addAction(zoom_out_action)

        reset_zoom_action = QAction("Reset Zoom", parent_widget)
        reset_zoom_action.setShortcut("Ctrl+0")
        reset_zoom_action.triggered.connect(lambda: self.reset_zoom_requested.emit())
        zoom_menu.addAction(reset_zoom_action)

        reset_pan_action = QAction("Reset Pan Position", parent_widget)
        reset_pan_action.triggered.connect(lambda: self.reset_pan_requested.emit())
        reset_pan_action.setEnabled(zoom_factor > 1.0)
        zoom_menu.addAction(reset_pan_action)
        menu.addMenu(zoom_menu)

        # Background color submenu
        bg_menu = QMenu("Background Color", parent_widget)
        current_bg = self.settings.value("bg_mode", "Black")
        for mode in ["Black", "Gray", "Adaptive Color"]:
            act = QAction(mode, parent_widget)
            act.setCheckable(True)
            act.setChecked(current_bg == mode)
            act.triggered.connect(lambda checked, m=mode: self.background_mode_changed.emit(m))
            bg_menu.addAction(act)
        menu.addMenu(bg_menu)

        history_action = QAction("Show History Panel", parent_widget)
        history_action.setCheckable(True)
        history_action.setChecked(self.settings.value("show_history_panel", False, type=bool))
        history_action.toggled.connect(lambda checked: self.history_panel_toggled.emit(checked))
        menu.addAction(history_action)
        menu.addSeparator()

        # --- Image Transform ---
        transform_menu = QMenu("Transform", parent_widget)

        grayscale_action = QAction("Grayscale", parent_widget)
        grayscale_action.setCheckable(True)
        grayscale_action.setChecked(self.settings.value("grayscale_enabled", False, type=bool))
        grayscale_action.toggled.connect(lambda checked: self.grayscale_toggled.emit(checked))
        transform_menu.addAction(grayscale_action)

        flip_h_action = QAction("Flip Horizontal", parent_widget)
        flip_h_action.triggered.connect(lambda: self.flip_horizontal_requested.emit())
        transform_menu.addAction(flip_h_action)

        flip_v_action = QAction("Flip Vertical", parent_widget)
        flip_v_action.triggered.connect(lambda: self.flip_vertical_requested.emit())
        transform_menu.addAction(flip_v_action)
        menu.addMenu(transform_menu)
        menu.addSeparator()

        # --- File Actions ---
        open_explorer_action = QAction("Open in File Explorer", parent_widget)
        open_explorer_action.triggered.connect(lambda: self.open_in_explorer_requested.emit())
        open_explorer_action.setEnabled(current_image is not None)
        menu.addAction(open_explorer_action)

        welcome_action = QAction("Switch Collection/Folder...", parent_widget)
        welcome_action.triggered.connect(lambda: self.switch_collection_requested.emit())
        menu.addAction(welcome_action)

        menu.addSeparator()

        shortcuts_action = QAction("Keyboard Shortcuts...", parent_widget)
        shortcuts_action.triggered.connect(lambda: self.keyboard_shortcuts_requested.emit())
        menu.addAction(shortcuts_action)

        menu.exec(global_pos)

    def _show_custom_timer_dialog(self, parent_widget, current_interval):
        value, ok = QInputDialog.getInt(
            parent_widget,
            "Custom Timer Interval",
            "Enter interval in seconds:",
            current_interval, 5, 3600, 5
        )
        if ok:
            self.timer_interval_changed.emit(value)