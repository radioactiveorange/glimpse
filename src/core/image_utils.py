"""Image processing utilities and helpers."""

import os
from PySide6.QtGui import QPixmap, QPainter, QFont, QIcon, QColor, QPen, QBrush, QPolygon
from PySide6.QtCore import Qt, QPoint
from PySide6.QtSvg import QSvgRenderer

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
    """Set adaptive background color based on dominant color in image with better contrast."""
    try:
        pixmap = QPixmap(img_path)
        if pixmap.isNull():
            return
        image = pixmap.toImage()
        w, h = image.width(), image.height()
        
        # Sample colors from entire image, but with reasonable downsampling
        step = max(1, min(w, h) // 50)  
        colors = {}
        
        # Collect colors from entire image
        for x in range(0, w, step):
            for y in range(0, h, step):
                if x < w and y < h:
                    pixel = image.pixel(x, y)
                    color = QColor(pixel)
                    rgb = (color.red(), color.green(), color.blue())
                    colors[rgb] = colors.get(rgb, 0) + 1
        
        if not colors:
            return
            
        # Get the most common colors
        sorted_colors = sorted(colors.items(), key=lambda x: x[1], reverse=True)
        
        # Try the top 5 most common colors and pick the best one for background
        best_color = None
        best_score = -1
        
        for (r, g, b), count in sorted_colors[:5]:
            # Calculate perceptual brightness
            brightness = 0.2126 * r + 0.7152 * g + 0.0722 * b
            
            # Calculate saturation
            max_val = max(r, g, b)
            min_val = min(r, g, b)
            saturation = (max_val - min_val) / max_val if max_val > 0 else 0
            
            # Score based on how good this color is for a background
            # Prefer darker colors (good contrast with white text)
            darkness_score = (255 - brightness) / 255
            
            # Prefer moderate saturation (not too gray, not too vivid)
            saturation_score = saturation if saturation < 0.5 else (1 - saturation)
            
            # Weight frequency
            frequency_score = count / sorted_colors[0][1]  # Normalize to most common
            
            # Combined score
            score = darkness_score * 0.5 + saturation_score * 0.3 + frequency_score * 0.2
            
            if score > best_score and brightness < 200:  # Not too bright
                best_score = score
                best_color = (r, g, b)
        
        if best_color:
            r, g, b = best_color
            # Darken the color for better contrast
            r = int(r * 0.7)
            g = int(g * 0.7) 
            b = int(b * 0.7)
        else:
            # Fallback: use the most common color but darkened significantly
            r, g, b = sorted_colors[0][0]
            r = int(r * 0.4)
            g = int(g * 0.4)
            b = int(b * 0.4)
            
        image_label.parentWidget().setStyleSheet(f"background-color: rgb({r},{g},{b});")
        
    except Exception as e:
        # Fallback to dark gray on any error
        image_label.parentWidget().setStyleSheet("background-color: rgb(40,40,40);")


def create_professional_icon(icon_type, size=24, color="#ffffff"):
    """Create icons from SVG files when available, fallback to coded icons."""
    # First try to load from SVG file
    svg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "icons", f"{icon_type}.svg")
    
    if os.path.exists(svg_path):
        # Create icon from SVG
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        renderer = QSvgRenderer(svg_path)
        if renderer.isValid():
            renderer.render(painter)
            painter.end()
            
            # If color is different from white, apply color tint
            if color != "#ffffff":
                colored_pixmap = QPixmap(size, size)
                colored_pixmap.fill(Qt.transparent)
                
                colored_painter = QPainter(colored_pixmap)
                colored_painter.setRenderHint(QPainter.Antialiasing, True)
                
                # Handle rgba colors by using composition
                color_obj = QColor(color)
                if color_obj.alpha() < 255:
                    # For semi-transparent colors, use a different approach
                    colored_painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
                    colored_painter.fillRect(colored_pixmap.rect(), color_obj)
                    colored_painter.setCompositionMode(QPainter.CompositionMode_DestinationOver)
                    colored_painter.drawPixmap(0, 0, pixmap)
                else:
                    # For opaque colors, use the standard approach
                    colored_painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
                    colored_painter.fillRect(colored_pixmap.rect(), color_obj)
                    colored_painter.setCompositionMode(QPainter.CompositionMode_DestinationOver)  
                    colored_painter.drawPixmap(0, 0, pixmap)
                
                colored_painter.end()
                return QIcon(colored_pixmap)
            
            return QIcon(pixmap)
        painter.end()
    
    # Fallback to coded icons
    return _create_coded_icon(icon_type, size, color)


def _create_coded_icon(icon_type, size=24, color="#ffffff"):
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
        # Chevron pointing left (matches SVG)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        
        # Left-pointing chevron: two lines forming <
        x1, y1 = center + margin//2, margin + 2
        x2, y2 = margin + 2, center  
        x3, y3 = center + margin//2, size - margin - 2
        
        # Draw the two lines of the chevron
        painter.drawLine(x1, y1, x2, y2)
        painter.drawLine(x2, y2, x3, y3)
        
    elif icon_type == "next":
        # Chevron pointing right (matches SVG)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        
        # Right-pointing chevron: two lines forming >
        x1, y1 = center - margin//2, margin + 2
        x2, y2 = size - margin - 2, center
        x3, y3 = center - margin//2, size - margin - 2
        
        # Draw the two lines of the chevron
        painter.drawLine(x1, y1, x2, y2)
        painter.drawLine(x2, y2, x3, y3)
        
    elif icon_type == "pause":
        # Two thick vertical bars with proper spacing
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        bar_width = size // 7  # Slightly thinner bars
        bar_height = size - 2 * margin
        gap = size // 4  # Much larger gap for better visibility
        painter.drawRoundedRect(center - bar_width - gap//2, margin, bar_width, bar_height, 1, 1)
        painter.drawRoundedRect(center + gap//2, margin, bar_width, bar_height, 1, 1)
        
    elif icon_type == "play":
        # Play triangle - same size as other icons
        points = [
            QPoint(margin, margin),
            QPoint(margin, size - margin),
            QPoint(size - margin, center)
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
        
    elif icon_type == "center":
        # Crosshair for reset/center
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        
        # Draw crosshair
        cross_size = (size - 2 * margin) // 3
        painter.drawLine(center - cross_size, center, center + cross_size, center)
        painter.drawLine(center, center - cross_size, center, center + cross_size)
        
        # Small circle in center
        center_radius = pen_width
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center - center_radius, center - center_radius, 
                          center_radius * 2, center_radius * 2)
        
    elif icon_type == "skip_previous":
        # Skip previous: vertical bar + left triangle (like media controls)
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        
        # Vertical bar on the left
        bar_width = size // 8
        bar_height = size - 2 * margin
        painter.drawRoundedRect(margin, margin, bar_width, bar_height, 1, 1)
        
        # Triangle pointing left
        triangle_margin = margin + bar_width + 2
        points = [
            QPoint(size - margin, margin),
            QPoint(size - margin, size - margin),
            QPoint(triangle_margin, center)
        ]
        painter.drawPolygon(QPolygon(points))
        
    elif icon_type == "skip_next":
        # Skip next: right triangle + vertical bar (like media controls)
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        
        # Triangle pointing right
        triangle_end = size - margin - (size // 8) - 2
        points = [
            QPoint(margin, margin),
            QPoint(margin, size - margin),
            QPoint(triangle_end, center)
        ]
        painter.drawPolygon(QPolygon(points))
        
        # Vertical bar on the right
        bar_width = size // 8
        bar_height = size - 2 * margin
        painter.drawRoundedRect(size - margin - bar_width, margin, bar_width, bar_height, 1, 1)
    
    elif icon_type == "add":
        # Plus sign (for adding/creating new items)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        
        # Horizontal line
        line_size = (size - 2 * margin) // 2
        painter.drawLine(center - line_size, center, center + line_size, center)
        # Vertical line
        painter.drawLine(center, center - line_size, center, center + line_size)
        
    elif icon_type == "edit":
        # Pencil icon for editing
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        
        # Pencil body (diagonal rectangle)
        pencil_width = size // 6
        pencil_start = margin + size // 8
        pencil_end = size - margin - size // 8
        
        # Create pencil shape (diagonal line with width)
        points = [
            QPoint(pencil_start, pencil_end),
            QPoint(pencil_start + pencil_width, pencil_end - pencil_width),
            QPoint(pencil_end, pencil_start),
            QPoint(pencil_end - pencil_width, pencil_start - pencil_width)
        ]
        painter.drawPolygon(QPolygon(points))
        
        # Small square at the tip
        tip_size = size // 10
        painter.drawRect(pencil_end - tip_size, pencil_start - tip_size, tip_size, tip_size)
        
    elif icon_type == "delete":
        # Trash can icon for deleting
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        
        # Trash can body
        can_width = size - 2 * margin
        can_height = (size - 2 * margin) * 2 // 3
        can_y = margin + size // 6
        painter.drawRoundedRect(margin, can_y, can_width, can_height, 2, 2)
        
        # Trash can lid
        lid_width = can_width + size // 8
        lid_height = size // 10
        lid_x = margin - size // 16
        lid_y = can_y - lid_height // 2
        painter.drawRoundedRect(lid_x, lid_y, lid_width, lid_height, 1, 1)
        
        # Handle on lid
        handle_width = can_width // 3
        handle_height = size // 12
        handle_x = center - handle_width // 2
        handle_y = lid_y - handle_height
        painter.setPen(QPen(QColor(color), pen_width // 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(handle_x, handle_y, handle_width, handle_height, 1, 1)
        
    elif icon_type == "cancel":
        # X icon for cancel
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        
        # Draw X
        line_size = (size - 2 * margin) // 2
        painter.drawLine(center - line_size, center - line_size, center + line_size, center + line_size)
        painter.drawLine(center - line_size, center + line_size, center + line_size, center - line_size)
        
    elif icon_type == "ok":
        # Checkmark for OK/accept
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        
        # Draw checkmark
        check_size = (size - 2 * margin) // 3
        check_x = center - check_size
        check_y = center
        painter.drawLine(check_x, check_y, check_x + check_size // 2, check_y + check_size // 2)
        painter.drawLine(check_x + check_size // 2, check_y + check_size // 2, check_x + check_size * 2, check_y - check_size)
        
    elif icon_type == "shuffle":
        # Shuffle icon - diagonal crossing arrows (matches SVG design)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        
        # Arrow head size
        head_size = size // 8
        
        # Main diagonal crossing line (bottom-left to top-right)
        painter.drawLine(margin + 2, size - margin - 2, size - margin - 2, margin + 2)
        
        # Top-right arrow components
        # Top horizontal line with arrow
        painter.drawLine(size - margin - size//3, margin + 2, size - margin - 2, margin + 2)
        painter.drawLine(size - margin - 2, margin + 2, size - margin - head_size, margin + 2 + head_size//2)
        # Right vertical line with arrow  
        painter.drawLine(size - margin - 2, margin + 2, size - margin - 2, margin + size//3)
        painter.drawLine(size - margin - 2, margin + size//3, size - margin - 2 - head_size//2, margin + size//3 - head_size)
        
        # Bottom-left arrow components  
        painter.drawLine(margin + 2, size - margin - size//3, margin + 2, size - margin - 2)
        painter.drawLine(margin + 2, size - margin - 2, margin + 2 + head_size//2, size - margin - 2 - head_size)
        painter.drawLine(margin + 2, size - margin - 2, margin + size//3, size - margin - 2)
        painter.drawLine(margin + size//3, size - margin - 2, margin + size//3 - head_size, size - margin - 2 - head_size//2)
    
    painter.end()
    return QIcon(pixmap)