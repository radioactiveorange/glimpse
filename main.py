import sys
import os
import random
import time
import subprocess
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QFileDialog, QVBoxLayout, QWidget,
    QListWidget, QListWidgetItem, QSplitter, QSpinBox, QCheckBox,
    QStatusBar, QToolBar, QToolButton, QSizePolicy, QComboBox, QMenu, QInputDialog
)
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QFont, QIcon, QImage, QTransform, QAction
from PySide6.QtCore import Qt, QTimer, QSize, QElapsedTimer, QSettings, Signal

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}

def get_images_in_folder(folder):
    image_paths = []
    for root, _, files in os.walk(folder):
        for f in files:
            if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS:
                image_paths.append(os.path.join(root, f))
    return image_paths

def emoji_icon(emoji="🎲", size=128):
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    f = QFont()
    f.setPointSize(int(size * 0.7))
    p.setFont(f)
    p.drawText(pix.rect(), Qt.AlignCenter, emoji)
    p.end()
    return QIcon(pix)

DARK_STYLESHEET = """
QWidget { background-color: #232629; color: #b7bcc1; font-size: 11px; }
QLabel, QCheckBox, QSpinBox, QListWidget, QToolButton { font-size: 11px; color: #b7bcc1; }
QStatusBar { font-size: 10px; color: #888; }
QSplitter::handle { background: #232629; border: none; height: 1px; }
QPushButton, QToolButton {
    background: transparent;
    color: #c7ccd1;
    border: none;
    border-radius: 4px;
    min-width: 24px;
    min-height: 24px;
    font-size: 13px;
    padding: 0 2px;
}
QPushButton:hover, QToolButton:hover { background: #2e3034; }
QListWidget::item:selected { background: #354e6e; color: #fff; }
QCheckBox:checked { color: #3b7dd8; }
QToolBar::separator {
    background: #35383b;
    width: 1px;
    margin: 0 4px;
}
QToolBar {
    border: none;
    background: #232629; /* or your preferred color */
}
"""

class CircularCountdown(QWidget):
    def __init__(self, total_time=0, parent=None):
        super().__init__(parent)
        self.total_time = 0
        self.remaining_time = 0      # The actual time left
        self.displayed_time = 0      # The smooth UI value
        self.setFixedSize(QSize(24, 24))
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(16)  # ~60 FPS

        self._last_update = time.monotonic()

    def set_total_time(self, seconds):
        self.total_time = float(max(1, seconds))
        self.update()

    def set_remaining_time(self, seconds):
        self.remaining_time = float(max(0, min(self.total_time, seconds)))
        self.update()

    def _on_tick(self):
        # Interpolate displayed_time toward remaining_time
        alpha = 0.18  # Smoothing factor (smaller = smoother/slower)
        self.displayed_time += (self.remaining_time - self.displayed_time) * alpha
        if abs(self.displayed_time - self.remaining_time) < 0.01:
            self.displayed_time = self.remaining_time
        self.update()

    def paintEvent(self, event):
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
    clicked = Signal()
    mouse_nav = True  # Always enabled
    back = Signal()
    forward = Signal()
    wheel_zoom = Signal(float)  # NEW: Signal for zooming, emits delta
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        elif self.mouse_nav:
            if event.button() == Qt.BackButton:
                self.back.emit()
            elif event.button() == Qt.ForwardButton:
                self.forward.emit()
        super().mousePressEvent(event)
    def wheelEvent(self, event):
        # Only emit if Ctrl is pressed or always? Let's do always for now
        angle = event.angleDelta().y()
        if angle != 0:
            self.wheel_zoom.emit(angle)
        super().wheelEvent(event)

class RandomImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setWindowTitle("Random Image Viewer")
        self.setGeometry(100, 100, 950, 650)
        self.settings = QSettings("random-image-viewer", "RandomImageViewer")
        last_folder = self.settings.value("last_folder", type=str)
        if last_folder and os.path.exists(last_folder):
            self.folder = last_folder
        else:
            self.folder = os.getcwd()
        self.images = get_images_in_folder(self.folder)
        self.history = []
        self.current_image = None
        self.current_index = -1
        self.history_index = -1  # NEW: For navigation
        self.timer_interval = self.settings.value("timer_interval", 60, type=int)
        self.timer_remaining = 0
        self._auto_advance_active = self.settings.value("auto_advance_enabled", False, type=bool)
        self.show_history = self.settings.value("show_history_panel", False, type=bool)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_timer_tick)
        self.zoom_factor = 1.0  # NEW: Track zoom
        self.init_ui()
        self.update_image_info()
        self._update_title()
        self._initial_image_shown = False

    def init_ui(self):
        # Remove toolbar and all buttons
        # self.toolbar = QToolBar("Main Toolbar")
        # self.addToolBar(self.toolbar)

        central_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(central_splitter)

        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        image_layout.setContentsMargins(6, 6, 6, 6)

        self.image_label = ClickableLabel("Open a folder to start", alignment=Qt.AlignCenter)
        self.image_label.setScaledContents(False)
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setToolTip("")
        self.image_label.clicked.connect(self.show_random_image)
        self.image_label.back.connect(self.show_previous_image)
        self.image_label.forward.connect(self.show_next_image)
        self.image_label.wheel_zoom.connect(self.handle_wheel_zoom)  # NEW: connect wheel zoom
        # Now set up context menu
        self.image_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.image_label.customContextMenuRequested.connect(self.show_context_menu)
        # Remove manual calls to toggle_xxx for settings
        # self.toggle_mouse_nav(self.mouse_nav_checkbox.checkState())
        # self.toggle_dominant_color(self.dominant_color_checkbox.checkState())
        # self.toggle_grayscale(self.grayscale_button.isChecked())

        image_layout.addWidget(self.image_label)
        image_widget.setLayout(image_layout)
        central_splitter.addWidget(image_widget)

        self.history_list = QListWidget()
        self.history_list.setMaximumWidth(180)
        self.history_list.itemClicked.connect(self.on_history_clicked)
        self.history_list.hide()
        central_splitter.addWidget(self.history_list)
        central_splitter.setSizes([900, 100])
        # Now set visibility
        self.history_list.setVisible(self.show_history)

        self.path_label = QLabel()

        self.path_label.linkActivated.connect(self.open_in_explorer)

        self.update_image_info()
        self._update_title()

        # Remove from toolbar: self.circle_timer = CircularCountdown(...)
        # Instead, add as overlay after self.image_label is created
        self.circle_timer = CircularCountdown(self.timer_interval, self.image_label)
        self.circle_timer.move(self.image_label.width() - 36, self.image_label.height() - 36)
        self.circle_timer.hide()
        self.image_label.resizeEvent = self.overlay_timer_resize_event(self.image_label.resizeEvent)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._initial_image_shown and self.images:
            self.show_random_image()
            self._initial_image_shown = True
            self._reset_timer()

    def keyPressEvent(self, event):
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

    def show_previous_image(self):
        if self.history_index > 0:
            self.history_index -= 1
            img_path = self.history[self.history_index]
            self.flipped_h = False
            self.flipped_v = False
            self.display_image(img_path)
            self.current_image = img_path
            self.update_image_info(img_path)
            self.set_status_path(img_path)
            if self._auto_advance_active:
                self.timer_remaining = self.timer_interval
                self._update_ring()

    def show_next_image(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            img_path = self.history[self.history_index]
            self.flipped_h = False
            self.flipped_v = False
            self.display_image(img_path)
            self.current_image = img_path
            self.update_image_info(img_path)
            self.set_status_path(img_path)
            if self._auto_advance_active:
                self.timer_remaining = self.timer_interval
                self._update_ring()
        else:
            self.show_random_image()

    def show_next_or_random_image(self):
        if self.history_index < len(self.history) - 1:
            self.show_next_image()
        else:
            self.show_random_image()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.folder = folder
            self.settings.setValue("last_folder", folder)
            self.images = get_images_in_folder(folder)
            self.history.clear()
            self.history_list.clear()
            self.history_list.repaint()
            self.current_image = None
            self.history_index = -1  # Reset history navigation
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
        count = len(self.images)
        folder_name = os.path.basename(self.folder) if self.folder else ""
        if img_path and info:
            base = os.path.basename(img_path)
            self.setWindowTitle(f"Random Image Viewer - {base} ({info}) - {img_path}")
        else:
            self.setWindowTitle(f"Random Image Viewer - {folder_name} ({count} images found)")

    def update_image_info(self, img_path=None):
        if img_path is None or not os.path.exists(img_path):
            self._update_title()
            return
        base = os.path.basename(img_path)
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            info = f"{pixmap.width()}x{pixmap.height()}"
        else:
            info = base
        # Update title with image info
        self._update_title(img_path, info)

    def show_random_image(self):
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
        self.set_status_path(img_path)
        if self._auto_advance_active:
            self.timer_remaining = self.timer_interval
            self._update_ring()

    def _manual_next_image(self):
        self.show_random_image()

    def display_image(self, img_path):
        pixmap = QPixmap(img_path)
        if pixmap.isNull():
            self.image_label.setText("Cannot load image.")
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
        pixmap = QPixmap.fromImage(image)
        size = self.image_label.size() * self.zoom_factor  # NEW: scale by zoom
        scaled = pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)
        self.image_label.setToolTip("")
        self.current_image = img_path
        # Set background according to dropdown
        mode = self.settings.value("bg_mode", "Black")
        if mode == "Adaptive Color":
            self.set_adaptive_bg(img_path)
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

    def resizeEvent(self, event):
        if self.current_image:
            self.display_image(self.current_image)
        super().resizeEvent(event)

    def add_to_history(self, img_path):
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
            self.set_status_path(img_path)
            if self._auto_advance_active:
                self.timer_remaining = self.timer_interval
                self._update_ring()

    def toggle_history_panel(self, checked):
        self.history_list.setVisible(bool(checked))
        self.settings.setValue("show_history_panel", bool(checked))

    def toggle_timer(self, checked):
        self._auto_advance_active = bool(checked)
        self.settings.setValue("auto_advance_enabled", self._auto_advance_active)
        self._reset_timer()

    def change_bg_mode(self, mode):
        self.settings.setValue("bg_mode", mode)
        self.display_image(self.current_image) if self.current_image else None

    def toggle_grayscale(self, checked):
        self.settings.setValue("grayscale_enabled", checked)
        if checked:
            self.image_label.parentWidget().setStyleSheet("background-color: #3b7dd8; color: #fff; border-radius: 4px;")
        else:
            self.image_label.parentWidget().setStyleSheet("")
        self.display_image(self.current_image) if self.current_image else None

    def flip_horizontal(self):
        self.flipped_h = not self.flipped_h
        self.display_image(self.current_image) if self.current_image else None

    def flip_vertical(self):
        self.flipped_v = not self.flipped_v
        self.display_image(self.current_image) if self.current_image else None

    def set_adaptive_bg(self, img_path):
        try:
            pixmap = QPixmap(img_path)
            if pixmap.isNull():
                return
            image = pixmap.toImage()
            w, h = image.width(), image.height()
            # Downsample for speed
            step = max(1, min(w, h) // 64)
            colors = {}
            for x in range(0, w, step):
                for y in range(0, h, step):
                    c = QColor(image.pixel(x, y)).rgb() & 0xFFFFFF
                    colors[c] = colors.get(c, 0) + 1
            if not colors:
                return
            dom_rgb = max(colors, key=colors.get)
            r = (dom_rgb >> 16) & 0xFF
            g = (dom_rgb >> 8) & 0xFF
            b = dom_rgb & 0xFF
            self.image_label.parentWidget().setStyleSheet(f"background-color: rgb({r},{g},{b});")
        except Exception:
            pass

    def set_status_path(self, image_path):
        # For Windows, convert slashes and prepend file:///
        url = os.path.abspath(image_path)
        # Cross-platform file URL
        file_url = 'file:///' + url.replace("\\", "/") if os.name == "nt" else 'file://' + url
        display_name = os.path.basename(url)
        color = "#b7bcc1"
        self.path_label.setText(
            f'<a href="{file_url}" style="color: {color}; text-decoration: none;">{display_name}</a>'
        )
        self.path_label.setToolTip(url)
        self.path_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.path_label.setOpenExternalLinks(False)  # We'll handle clicks

    def open_in_explorer(self, file_url):
        path = file_url.replace('file:///', '') if os.name == "nt" else file_url.replace('file://', '')
        path = os.path.abspath(path)
        folder = os.path.dirname(path)
        if os.name == "nt":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:  # linux
            subprocess.Popen(["xdg-open", folder])

    def overlay_timer_resize_event(self, original_resize_event):
        def new_resize_event(event):
            # Call the original resize event
            if original_resize_event:
                original_resize_event(event)
            # Move the timer to bottom-right
            self.circle_timer.move(self.image_label.width() - 36, self.image_label.height() - 36)
        return new_resize_event

    def _reset_timer(self):
        if self._auto_advance_active and self.images:
            self.timer.stop()
            self.timer_remaining = self.timer_interval
            self._update_ring()
            self.timer.start()
            self.circle_timer.show()
        else:
            self.timer.stop()
            self.circle_timer.set_remaining_time(0)
            self.circle_timer.hide()

    def _on_timer_tick(self):
        if not self._auto_advance_active or not self.images:
            self.timer.stop()
            self.circle_timer.set_remaining_time(0)
            return
        self.timer_remaining -= 1
        if self.timer_remaining <= 0:
            self.show_random_image()
        else:
            self._update_ring()

    def _update_ring(self):
        self.circle_timer.set_total_time(self.timer_interval)
        self.circle_timer.set_remaining_time(self.timer_remaining)

    def show_context_menu(self, pos):
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
        self.timer_interval = value
        self.settings.setValue("timer_interval", value)
        self.timer_remaining = value
        self._update_ring()

    def set_custom_timer_interval(self):
        val, ok = QInputDialog.getInt(self, "Custom Timer Interval", "Seconds:", self.timer_interval, 1, 3600)
        if ok:
            self.set_timer_interval(val)

    def open_current_in_explorer(self):
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
        # angle is in 1/8th degree steps, so 120 per notch
        if angle > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def zoom_in(self):
        self.zoom_factor = min(self.zoom_factor * 1.15, 8.0)
        if self.current_image:
            self.display_image(self.current_image)

    def zoom_out(self):
        self.zoom_factor = max(self.zoom_factor / 1.15, 0.1)
        if self.current_image:
            self.display_image(self.current_image)

    def reset_zoom(self):
        self.zoom_factor = 1.0
        if self.current_image:
            self.display_image(self.current_image)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    app.setWindowIcon(emoji_icon("🎲", 128))
    viewer = RandomImageViewer()
    viewer.show()
    sys.exit(app.exec())
