"""Image processing utilities and helpers."""

import os
from PySide6.QtGui import QPixmap, QPainter, QFont, QIcon, QColor, QPen, QBrush, QPolygon
from PySide6.QtCore import Qt, QPoint

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


def create_professional_icon(icon_type, size=24, color="#ffffff"):
    """Create crisp, recognizable geometric icons using QPainter."""
    # Use higher DPI for crisp rendering
    scale_factor = 2
    actual_size = size * scale_factor
    pixmap = QPixmap(actual_size, actual_size)
    pixmap.setDevicePixelRatio(scale_factor)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    
    # Use thicker strokes for better visibility
    pen_width = max(2, size // 8)
    pen = QPen(QColor(color), pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    brush = QBrush(QColor(color))
    
    center = size // 2
    margin = size // 5  # Larger margin for clearer shapes
    
    if icon_type == "previous":
        # Clear left-pointing triangle
        points = [
            QPoint(center + margin, margin),
            QPoint(center + margin, size - margin), 
            QPoint(margin, center)
        ]
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(QPolygon(points))
        
    elif icon_type == "next":
        # Clear right-pointing triangle
        points = [
            QPoint(center - margin, margin),
            QPoint(center - margin, size - margin),
            QPoint(size - margin, center)
        ]
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(QPolygon(points))
        
    elif icon_type == "pause":
        # Two thick vertical bars
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        bar_width = size // 6
        bar_height = size - 2 * margin
        gap = size // 10
        painter.drawRoundedRect(center - bar_width - gap//2, margin, bar_width, bar_height, 1, 1)
        painter.drawRoundedRect(center + gap//2, margin, bar_width, bar_height, 1, 1)
        
    elif icon_type == "play":
        # Slightly smaller play triangle
        play_margin = margin + 2
        points = [
            QPoint(play_margin, play_margin),
            QPoint(play_margin, size - play_margin),
            QPoint(size - play_margin, center)
        ]
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(QPolygon(points))
        
    elif icon_type == "stop":
        # Rounded square
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        square_size = size - 2 * margin
        painter.drawRoundedRect(margin, margin, square_size, square_size, 2, 2)
        
    elif icon_type == "zoom_in":
        # Simple plus sign in circle
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        # Circle
        circle_radius = (size - 2 * margin) // 2
        painter.drawEllipse(center - circle_radius, center - circle_radius, 
                          circle_radius * 2, circle_radius * 2)
        
        # Plus sign - thicker lines
        plus_size = circle_radius // 2
        plus_pen = QPen(QColor(color), pen_width + 1, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(plus_pen)
        painter.drawLine(center - plus_size, center, center + plus_size, center)
        painter.drawLine(center, center - plus_size, center, center + plus_size)
        
    elif icon_type == "zoom_out":
        # Simple minus sign in circle
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        # Circle
        circle_radius = (size - 2 * margin) // 2
        painter.drawEllipse(center - circle_radius, center - circle_radius, 
                          circle_radius * 2, circle_radius * 2)
        
        # Minus sign - thicker line
        minus_size = circle_radius // 2
        minus_pen = QPen(QColor(color), pen_width + 1, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(minus_pen)
        painter.drawLine(center - minus_size, center, center + minus_size, center)
    
    painter.end()
    return QIcon(pixmap)