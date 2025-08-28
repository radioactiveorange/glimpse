"""Image processing utilities and helpers."""

import os
from PySide6.QtGui import QPixmap, QPainter, QFont, QIcon, QColor
from PySide6.QtCore import Qt

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}


def get_images_in_folder(folder):
    """Recursively find all image files in a folder."""
    image_paths = []
    for root, _, files in os.walk(folder):
        for f in files:
            if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS:
                image_paths.append(os.path.join(root, f))
    return image_paths


def emoji_icon(emoji="🎲", size=128):
    """Create a QIcon from an emoji character."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    f = QFont()
    f.setPointSize(int(size * 0.7))
    p.setFont(f)
    p.drawText(pix.rect(), Qt.AlignCenter, emoji)
    p.end()
    return QIcon(pix)


def set_adaptive_bg(image_label, img_path):
    """Set adaptive background color based on dominant color in image."""
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
        image_label.parentWidget().setStyleSheet(f"background-color: rgb({r},{g},{b});")
    except Exception:
        pass