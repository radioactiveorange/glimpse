"""Media controls manager - handles timer functionality and playback controls."""

import os
from PySide6.QtCore import QObject, QTimer, Signal


class MediaControlsManager(QObject):
    """Manages auto-advance timer and media playback controls.
    
    Extracts all timer-related functionality from the main window to improve maintainability.
    """
    
    # Signals
    timer_tick = Signal()  # Emitted every timer tick
    timer_expired = Signal()  # Emitted when timer reaches zero
    timer_state_changed = Signal(bool, bool)  # active, paused
    progress_updated = Signal(int, int)  # remaining, total time
    
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        
        # Timer state
        self.timer_interval = self.settings.value("timer_interval", 60, type=int)
        self.timer_remaining = 0
        self._auto_advance_active = self.settings.value("auto_advance_enabled", False, type=bool)
        self._timer_paused = False
        self._has_images = False
        
        # Initialize QTimer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)  # 1 second intervals
        self.timer.timeout.connect(self._on_timer_tick)
    
    # Public API - Timer Controls
    def start_timer(self):
        """Start/enable the auto-advance timer."""
        self._auto_advance_active = True
        self._timer_paused = False
        self.settings.setValue("auto_advance_enabled", True)
        self._reset_timer()
        self.timer_state_changed.emit(self._auto_advance_active, self._timer_paused)
    
    def stop_timer(self):
        """Stop and disable the auto-advance timer completely."""
        self._auto_advance_active = False
        self._timer_paused = False
        self.settings.setValue("auto_advance_enabled", False)
        self._reset_timer()
        self.timer_state_changed.emit(self._auto_advance_active, self._timer_paused)
    
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
            if self._has_images:
                self.timer.start()
        
        self.timer_state_changed.emit(self._auto_advance_active, self._timer_paused)
    
    def reset_timer(self):
        """Public method to reset the timer (called when navigating manually)."""
        if self._auto_advance_active:
            self.timer_remaining = self.timer_interval
            self._update_progress()
    
    # Public API - Configuration
    def set_timer_interval(self, interval):
        """Set the timer interval in seconds."""
        self.timer_interval = max(1, interval)  # Ensure minimum 1 second
        self.settings.setValue("timer_interval", self.timer_interval)
        
        # If timer is active, restart with new interval
        if self._auto_advance_active:
            self._reset_timer()
    
    def set_has_images(self, has_images):
        """Update whether there are images available for auto-advance."""
        self._has_images = has_images
        if not has_images and self._auto_advance_active:
            self.timer.stop()
            self.progress_updated.emit(0, self.timer_interval)
    
    # Public API - State Getters
    def is_active(self):
        """Check if auto-advance is active."""
        return self._auto_advance_active
    
    def is_paused(self):
        """Check if timer is paused."""
        return self._timer_paused
    
    def get_timer_interval(self):
        """Get current timer interval in seconds."""
        return self.timer_interval
    
    def get_remaining_time(self):
        """Get remaining time in current cycle."""
        return self.timer_remaining
    
    def get_state_info(self):
        """Get complete timer state information."""
        return {
            'active': self._auto_advance_active,
            'paused': self._timer_paused,
            'interval': self.timer_interval,
            'remaining': self.timer_remaining,
            'has_images': self._has_images
        }
    
    # Private Methods
    def _reset_timer(self):
        """Reset the auto-advance timer."""
        if self._auto_advance_active and self._has_images:
            self.timer.stop()
            self.timer_remaining = self.timer_interval
            self._timer_paused = False
            self._update_progress()
            self.timer.start()
        else:
            self.timer.stop()
            self._timer_paused = False
            self.progress_updated.emit(0, self.timer_interval)
    
    def _on_timer_tick(self):
        """Handle timer tick for auto-advance."""
        if not self._auto_advance_active or not self._has_images or self._timer_paused:
            if not self._auto_advance_active:
                self.timer.stop()
                self.progress_updated.emit(0, self.timer_interval)
            return
        
        self.timer_remaining -= 1
        self.timer_tick.emit()
        
        if self.timer_remaining <= 0:
            # Timer expired - emit signal for main window to handle
            self.timer_expired.emit()
            # Reset for next cycle
            self.timer_remaining = self.timer_interval
        
        self._update_progress()
    
    def _update_progress(self):
        """Update the progress display."""
        self.progress_updated.emit(self.timer_remaining, self.timer_interval)
    
    # Lifecycle Methods
    def cleanup(self):
        """Clean up timer resources."""
        if self.timer.isActive():
            self.timer.stop()
    
    def load_settings(self):
        """Reload settings from QSettings."""
        self.timer_interval = self.settings.value("timer_interval", 60, type=int)
        self._auto_advance_active = self.settings.value("auto_advance_enabled", False, type=bool)
        
        # Update timer if active
        if self._auto_advance_active:
            self._reset_timer()
    
    def save_settings(self):
        """Save current state to QSettings."""
        self.settings.setValue("timer_interval", self.timer_interval)
        self.settings.setValue("auto_advance_enabled", self._auto_advance_active)