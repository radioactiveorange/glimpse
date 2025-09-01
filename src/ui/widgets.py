"""Custom UI widgets for the image viewer."""

import time
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient, QIcon, QPixmap
from PySide6.QtCore import Qt, QTimer, QSize, Signal, QRect


class CircularCountdown(QWidget):
    """A circular countdown timer widget with smooth animation."""
    
    def __init__(self, total_time=0, parent=None):
        super().__init__(parent)
        self.total_time = 0
        self.remaining_time = 0      # The actual time left
        self.displayed_time = 0      # The smooth UI value
        self.setFixedSize(QSize(24, 24))
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        # Don't start timer immediately - start only when needed

        self._last_update = time.monotonic()

    def set_total_time(self, seconds):
        """Set the total countdown time."""
        self.total_time = float(max(1, seconds))
        self.update()

    def set_remaining_time(self, seconds):
        """Set the remaining countdown time."""
        self.remaining_time = float(max(0, min(self.total_time, seconds)))
        # Start timer for smooth animation
        if not self._timer.isActive():
            self._timer.start(16)  # 60 FPS for smooth animation
        self.update()

    def _on_tick(self):
        """Smooth animation tick handler."""
        # Interpolate displayed_time toward remaining_time
        alpha = 0.18  # Smoothing factor (smaller = smoother/slower)
        self.displayed_time += (self.remaining_time - self.displayed_time) * alpha
        if abs(self.displayed_time - self.remaining_time) < 0.01:
            self.displayed_time = self.remaining_time
        self.update()

    def paintEvent(self, event):
        """Paint the circular countdown progress."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(4, 4, -4, -4)
        # Draw subtle background ring
        painter.setPen(QPen(QColor("#3d3e40"), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(rect)
        # Draw smooth progress arc
        if self.total_time > 0 and self.displayed_time > 0:
            fraction = self.displayed_time / self.total_time
            angle = int(360 * 16 * fraction)
            painter.setPen(QPen(QColor("#80b2ff"), 3))
            painter.drawArc(rect, 90 * 16, -angle)


class ClickableLabel(QLabel):
    """A QLabel that emits signals for various mouse interactions."""
    
    clicked = Signal()
    mouse_nav = True  # Always enabled
    back = Signal()
    forward = Signal()
    wheel_zoom = Signal(float)  # Signal for zooming, emits delta
    pan_start = Signal(object)  # Signal for starting pan (QPoint)
    pan_move = Signal(object)   # Signal for pan movement (QPoint)
    pan_end = Signal()          # Signal for ending pan
    mouse_moved = Signal()      # Signal for mouse movement to show controls
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_panning = False
        self._last_pan_point = None
        # Enable mouse tracking to receive move events during drag
        self.setMouseTracking(True)
    
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.LeftButton:
            # Use left button for panning
            self._is_panning = True
            self._last_pan_point = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            self.pan_start.emit(event.pos())
        elif self.mouse_nav:
            if event.button() == Qt.BackButton:
                self.back.emit()
            elif event.button() == Qt.ForwardButton:
                self.forward.emit()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events for panning and show controls."""
        # Emit signal for showing controls on mouse movement
        self.mouse_moved.emit()
        
        if self._is_panning and self._last_pan_point:
            delta = event.pos() - self._last_pan_point
            self.pan_move.emit(delta)
            self._last_pan_point = event.pos()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.LeftButton and self._is_panning:
            self._is_panning = False
            self._last_pan_point = None
            self.setCursor(Qt.ArrowCursor)
            self.pan_end.emit()
        super().mouseReleaseEvent(event)
    
    def wheelEvent(self, event):
        """Handle mouse wheel events for zooming."""
        angle = event.angleDelta().y()
        if angle != 0:
            self.wheel_zoom.emit(angle)
        super().wheelEvent(event)


class MinimalProgressBar(QWidget):
    """A minimal semi-transparent progress bar for the bottom of the window."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_time = 0
        self.remaining_time = 0
        self.displayed_time = 0
        self.setFixedHeight(4)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # Smooth animation timer - don't start immediately
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
    
    def set_total_time(self, seconds):
        """Set the total countdown time."""
        self.total_time = float(max(1, seconds))
        self.update()
    
    def set_remaining_time(self, seconds):
        """Set the remaining countdown time."""
        self.remaining_time = float(max(0, min(self.total_time, seconds)))
        # Start timer for smooth animation
        if not self._timer.isActive():
            self._timer.start(16)  # 60 FPS for smooth animation
        self.update()
    
    def _on_tick(self):
        """Smooth animation tick handler."""
        alpha = 0.18  # Smoothing factor
        self.displayed_time += (self.remaining_time - self.displayed_time) * alpha
        if abs(self.displayed_time - self.remaining_time) < 0.01:
            self.displayed_time = self.remaining_time
        self.update()
    
    def paintEvent(self, event):
        """Paint the minimal progress bar."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        
        # Draw very subtle semi-transparent background
        bg_color = QColor("#000000")
        bg_color.setAlphaF(0.1)  # Much more subtle
        painter.fillRect(rect, bg_color)
        
        # Draw progress
        if self.total_time > 0 and self.displayed_time > 0:
            fraction = self.displayed_time / self.total_time
            progress_width = int(rect.width() * fraction)
            progress_rect = QRect(0, 0, progress_width, rect.height())
            
            # Create more subtle gradient for progress bar
            gradient = QLinearGradient(0, 0, progress_width, 0)
            progress_color_1 = QColor("#80b2ff")
            progress_color_1.setAlphaF(0.6)  # Reduced opacity
            progress_color_2 = QColor("#4a90e2") 
            progress_color_2.setAlphaF(0.4)  # Reduced opacity
            gradient.setColorAt(0, progress_color_1)
            gradient.setColorAt(1, progress_color_2)
            
            painter.fillRect(progress_rect, gradient)


def create_simple_icon(symbol, size=24, color="#ffffff"):
    """Create a simple icon from a text symbol."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QColor(color))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, symbol)
    painter.end()
    return QIcon(pixmap)


class ButtonOverlay(QWidget):
    """Semi-transparent button overlay for bottom middle of the image viewer."""
    
    previous_clicked = Signal()
    pause_clicked = Signal() 
    stop_clicked = Signal()
    next_clicked = Signal()
    zoom_in_clicked = Signal()
    zoom_out_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground)
        self.setFixedSize(280, 50)  # Wider to accommodate zoom buttons
        
        # Auto-hide functionality
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._auto_hide)
        self._hide_delay = 3000  # 3 seconds
        self._is_auto_hiding = False
        self._manually_hidden = False  # Track if user manually hid controls
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
        # Initially semi-transparent
        self.base_opacity = 0.3
        self.hover_opacity = 0.8
        self.icon_base_opacity = 0.5  # Icons start more transparent
        self.icon_hover_opacity = 1.0  # Icons become fully opaque on hover
        self.setStyleSheet(f"""
            ButtonOverlay {{
                background-color: rgba(0, 0, 0, {int(self.base_opacity * 255)});
                border-radius: 25px;
            }}
            ButtonOverlay:hover {{
                background-color: rgba(0, 0, 0, {int(self.hover_opacity * 255)});
            }}
            QPushButton {{
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, {int(self.icon_base_opacity * 255)});
                font-size: 16px;
                padding: 0px;
                border-radius: 20px;
                min-width: 40px;
                min-height: 40px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 30);
                color: rgba(255, 255, 255, {int(self.icon_hover_opacity * 255)});
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 50);
                color: rgba(255, 255, 255, {int(self.icon_hover_opacity * 255)});
            }}
        """)
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Import the icon function
        from ..core.image_utils import create_professional_icon
        
        # Create buttons with professional geometric icons (all same size)
        icon_size = 18  # Consistent size for all icons
        # Use semi-transparent icons to match button opacity
        icon_color = f"rgba(255, 255, 255, {int(self.icon_base_opacity * 255)})"
        
        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(create_professional_icon("skip_previous", icon_size, icon_color))
        
        self.pause_btn = QPushButton()
        self.pause_btn.setIcon(create_professional_icon("pause", icon_size, icon_color))
        
        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(create_professional_icon("stop", icon_size, icon_color))
        
        self.next_btn = QPushButton()
        self.next_btn.setIcon(create_professional_icon("skip_next", icon_size, icon_color))
        
        self.zoom_out_btn = QPushButton()
        self.zoom_out_btn.setIcon(create_professional_icon("zoom_out", icon_size, icon_color))
        
        self.zoom_in_btn = QPushButton()
        self.zoom_in_btn.setIcon(create_professional_icon("zoom_in", icon_size, icon_color))
        
        # Connect signals
        self.prev_btn.clicked.connect(self.previous_clicked.emit)
        self.pause_btn.clicked.connect(self.pause_clicked.emit)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        self.next_btn.clicked.connect(self.next_clicked.emit)
        self.zoom_out_btn.clicked.connect(self.zoom_out_clicked.emit)
        self.zoom_in_btn.clicked.connect(self.zoom_in_clicked.emit)
        
        # Add buttons to layout (zoom buttons on the sides)
        layout.addWidget(self.zoom_out_btn)
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.pause_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.next_btn)
        layout.addWidget(self.zoom_in_btn)
    
    def set_pause_state(self, is_paused, timer_active=True):
        """Update pause button based on timer state."""
        from ..core.image_utils import create_professional_icon
        # If timer is not active, show play button regardless of pause state
        # If timer is active, show play when paused, pause when running
        icon_type = "play" if (not timer_active or is_paused) else "pause"
        icon_size = 18  # Match the consistent icon size
        # Use same opacity as other icons
        icon_color = f"rgba(255, 255, 255, {int(self.icon_base_opacity * 255)})"
        self.pause_btn.setIcon(create_professional_icon(icon_type, icon_size, icon_color))
    
    def show(self):
        """Override show to start auto-hide timer."""
        super().show()
        self._start_auto_hide_timer()
    
    def enterEvent(self, event):
        """Show controls when mouse enters the overlay."""
        super().enterEvent(event)
        self._show_controls()
        
    def leaveEvent(self, event):
        """Start auto-hide timer when mouse leaves the overlay."""
        super().leaveEvent(event)
        self._start_auto_hide_timer()
    
    def _show_controls(self):
        """Show the controls and cancel auto-hide."""
        self._hide_timer.stop()
        self._is_auto_hiding = False
        self._manually_hidden = False  # Reset manual hide when mouse moves
        if self.isHidden():
            super().show()  # Use super().show() to avoid triggering auto-hide timer
        # Restart the auto-hide timer
        self._start_auto_hide_timer()
    
    def _start_auto_hide_timer(self):
        """Start or restart the auto-hide timer."""
        if not self._is_auto_hiding:
            self._hide_timer.stop()
            self._hide_timer.start(self._hide_delay)
    
    def _auto_hide(self):
        """Hide the controls automatically."""
        self._is_auto_hiding = True
        # Don't set _manually_hidden for auto-hide, only for explicit hiding
        self.hide()
    
    def show_for_new_image(self):
        """Show controls explicitly for new image loading (resets manual hide state)."""
        self._manually_hidden = False  # Reset manual hide state
        self._show_controls()