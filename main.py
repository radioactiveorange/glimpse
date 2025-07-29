import sys
import os
import random
import time
import subprocess
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QFileDialog, QVBoxLayout, QWidget,
    QListWidget, QListWidgetItem, QSplitter, QSpinBox, QCheckBox,
    QStatusBar, QToolBar, QToolButton, QSizePolicy,
)
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QFont, QIcon
from PySide6.QtCore import Qt, QTimer, QSize, QElapsedTimer

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

class RandomImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setWindowTitle("Random Image Viewer")
        self.setGeometry(100, 100, 950, 650)
        self.folder = None
        self.images = []
        self.history = []
        self.current_image = None
        self.current_index = -1
        self.history_index = -1  # NEW: For navigation

        self.timer_interval = 60  # seconds
        self.timer_remaining = 0
        self._auto_advance_active = False

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_timer_tick)

        self.init_ui()

    def init_ui(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)
        toolbar.setMovable(False)
        toolbar.setStyleSheet("QToolBar { spacing: 4px; }")

        open_btn = QToolButton()
        open_btn.setText("📁")
        open_btn.setToolTip("Open Folder")
        open_btn.setFixedSize(24, 24)
        open_btn.clicked.connect(self.choose_folder)
        toolbar.addWidget(open_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)  # Or whatever feels best
        toolbar.addWidget(spacer)

        next_btn = QToolButton()
        next_btn.setText("🎲")
        next_btn.setToolTip("Show Next Random Image")
        next_btn.setFixedSize(24, 24)
        next_btn.clicked.connect(self._manual_next_image)
        toolbar.addWidget(next_btn)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        self.timer_button = QToolButton()
        self.timer_button.setCheckable(True)
        self.timer_button.setText("⚡")  # or "🔛"
        self.timer_button.setToolTip("Toggle Auto Advance")
        self.timer_button.setFixedSize(24, 24)
        self.timer_button.toggled.connect(self.toggle_timer)
        toolbar.addWidget(self.timer_button)

        spacer = QWidget()
        spacer.setFixedWidth(4)
        toolbar.addWidget(spacer)

        self.timer_spin = QSpinBox()
        self.timer_spin.setRange(1, 3600)
        self.timer_spin.setValue(self.timer_interval)
        self.timer_spin.setSuffix(" s")
        self.timer_spin.setFixedHeight(24)
        self.timer_spin.setFixedWidth(60)
        self.timer_spin.valueChanged.connect(self.update_timer_interval)
        toolbar.addWidget(self.timer_spin)

        spacer = QWidget()
        spacer.setFixedWidth(12)
        toolbar.addWidget(spacer)

        self.circle_timer = CircularCountdown(self.timer_spin.value())
        toolbar.addWidget(self.circle_timer)

        toolbar.addSeparator()

        self.show_history_checkbox = QCheckBox("History")
        self.show_history_checkbox.setChecked(False)
        self.show_history_checkbox.setFixedHeight(24)
        self.show_history_checkbox.stateChanged.connect(self.toggle_history_panel)
        toolbar.addWidget(self.show_history_checkbox)

        toolbar.addStretch = lambda: toolbar.addWidget(QWidget())
        toolbar.addStretch()

        central_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(central_splitter)

        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        image_layout.setContentsMargins(6, 6, 6, 6)

        self.image_label = QLabel("Open a folder to start", alignment=Qt.AlignCenter)
        self.image_label.setScaledContents(False)
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setToolTip("")

        image_layout.addWidget(self.image_label)
        image_widget.setLayout(image_layout)
        central_splitter.addWidget(image_widget)

        self.history_list = QListWidget()
        self.history_list.setMaximumWidth(180)
        self.history_list.itemClicked.connect(self.on_history_clicked)
        self.history_list.hide()
        central_splitter.addWidget(self.history_list)
        central_splitter.setSizes([900, 100])

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.path_label = QLabel()

        self.statusBar().addPermanentWidget(self.path_label)
        self.path_label.linkActivated.connect(self.open_in_explorer)

        self.update_image_info()
        self._update_title()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self.show_previous_image()
        elif event.key() == Qt.Key_Right:
            self.show_next_image()
        else:
            super().keyPressEvent(event)

    def show_previous_image(self):
        if self.history_index > 0:
            self.history_index -= 1
            img_path = self.history[self.history_index]
            self.display_image(img_path)
            self.current_image = img_path
            self.update_image_info(img_path)
            self.set_status_path(img_path)
            if self._auto_advance_active:
                self.timer_remaining = self.timer_spin.value()
                self._update_ring()

    def show_next_image(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            img_path = self.history[self.history_index]
            self.display_image(img_path)
            self.current_image = img_path
            self.update_image_info(img_path)
            self.set_status_path(img_path)
            if self._auto_advance_active:
                self.timer_remaining = self.timer_spin.value()
                self._update_ring()
        else:
            self.show_random_image()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.folder = folder
            self.images = get_images_in_folder(folder)
            self.history.clear()
            self.history_list.clear()
            self.history_list.repaint()
            self.current_image = None
            self.history_index = -1  # Reset history navigation
            self.update_image_info()
            self._update_title()
            if self.images:
                self.show_random_image()
            else:
                self.image_label.setText("No images found in selected folder or its subfolders.")
            self._reset_timer()

    def _update_title(self):
        count = len(self.images)
        folder_name = os.path.basename(self.folder) if self.folder else ""
        self.setWindowTitle(f"Random Image Viewer - {folder_name} ({count} images found)")

    def update_image_info(self, img_path=None):
        if img_path is None or not os.path.exists(img_path):
            self.status.showMessage("")
            return
        base = os.path.basename(img_path)
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            info = f"{base} – {pixmap.width()}x{pixmap.height()}"
        else:
            info = base
        self.status.showMessage(info)

    def show_random_image(self):
        if not self.images:
            return
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
            self.timer_remaining = self.timer_spin.value()
            self._update_ring()

    def _manual_next_image(self):
        self.show_random_image()

    def display_image(self, img_path):
        pixmap = QPixmap(img_path)
        if pixmap.isNull():
            self.image_label.setText("Cannot load image.")
            self.status.showMessage(os.path.basename(img_path))
            return
        size = self.image_label.size()
        scaled = pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)
        self.image_label.setToolTip("")
        self.current_image = img_path

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
                self.timer_remaining = self.timer_spin.value()
                self._update_ring()

    def toggle_history_panel(self, checked):
        self.history_list.setVisible(bool(checked))

    def update_timer_interval(self, value):
        self.timer_interval = value
        self.circle_timer.set_total_time(value)
        if self._auto_advance_active:
            self.timer_remaining = value
            self._update_ring()

    def toggle_timer(self, checked):
        self._auto_advance_active = bool(checked)
        self._reset_timer()

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

    def _reset_timer(self):
        if self._auto_advance_active and self.images:
            self.timer.stop()
            self.timer_remaining = self.timer_spin.value()
            self.circle_timer.set_total_time(self.timer_spin.value())
            self._update_ring()
            self.timer.start()
        else:
            self.timer.stop()
            self.circle_timer.set_remaining_time(0)

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
        self.circle_timer.set_total_time(self.timer_spin.value())
        self.circle_timer.set_remaining_time(self.timer_remaining)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    app.setWindowIcon(emoji_icon("🎲", 128))
    viewer = RandomImageViewer()
    viewer.show()
    sys.exit(app.exec())
