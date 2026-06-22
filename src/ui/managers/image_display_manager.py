"""Image display management - handles zoom, pan, transformations, and image processing."""

import os
import time
from PIL import Image
from turbojpeg import TurboJPEG
from PySide6.QtGui import QPixmap, QImage, QTransform, QPainter, QColor
from PySide6.QtCore import Qt, QObject, Signal, QThread

from ...core.image_utils import set_adaptive_bg

# Performance benchmarking flag
BENCHMARK = False

# Initialize TurboJPEG for blazing fast JPEG loading
try:
    jpeg = TurboJPEG()
    TURBOJPEG_AVAILABLE = True
except Exception:
    TURBOJPEG_AVAILABLE = False


class ImagePreloader(QThread):
    """Background thread for pre-loading images."""

    image_loaded = Signal(str, QPixmap)  # path, pixmap

    def __init__(self):
        super().__init__()
        self.paths_to_load = []
        self.running = True

    def add_path(self, path):
        """Add a path to the preload queue."""
        if path not in self.paths_to_load:
            self.paths_to_load.append(path)

    def clear_queue(self):
        """Clear the preload queue."""
        self.paths_to_load.clear()

    def run(self):
        """Load images in background using fast Pillow library."""
        while self.running:
            if self.paths_to_load:
                path = self.paths_to_load.pop(0)
                try:
                    if os.path.exists(path):
                        # Use Pillow for faster image loading
                        pil_image = Image.open(path)

                        # Use draft mode for JPEG - loads reduced size for speed
                        if pil_image.format == "JPEG":
                            # Load at ~1920x1080 max for speed (most screens)
                            pil_image.draft("RGB", (1920, 1080))

                        # Convert PIL image to QPixmap
                        pixmap = self._pil_to_qpixmap(pil_image)

                        if not pixmap.isNull():
                            self.image_loaded.emit(path, pixmap)
                except Exception:
                    pass  # Silently skip problematic images
            else:
                self.msleep(10)  # Shorter sleep for more responsiveness

    def _pil_to_qpixmap(self, pil_image):
        """Convert PIL Image to QPixmap efficiently."""
        # Convert to RGB if needed
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        # Get image data
        data = pil_image.tobytes("raw", "RGB")
        qimage = QImage(
            data,
            pil_image.width,
            pil_image.height,
            pil_image.width * 3,
            QImage.Format_RGB888,
        )
        return QPixmap.fromImage(qimage)

    def stop(self):
        """Stop the preloader thread and wait for it to finish."""
        self.running = False
        self.wait()


class ImageDisplayManager(QObject):
    """Manages image display functionality including zoom, pan, transformations, and processing."""

    # Signals
    image_changed = Signal(str)  # Emitted when image changes
    zoom_changed = Signal(float)  # Emitted when zoom level changes
    transform_changed = Signal()  # Emitted when image transforms change

    def __init__(self, image_label, settings):
        super().__init__()
        self.image_label = image_label
        self.settings = settings

        # Image state
        self.current_image = None
        self._cached_pixmap = None

        # Pre-loading cache for fast navigation
        self._pixmap_cache = {}  # path -> pixmap
        self._max_cache_size = 10  # Keep last 10 images in memory

        # Background preloader
        self.preloader = ImagePreloader()
        self.preloader.image_loaded.connect(self._on_image_preloaded)
        self.preloader.start()

        # Zoom and pan state
        self.zoom_factor = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0

        # Transform state - initialize from settings
        self.is_flipped_h = False
        self.is_flipped_v = False
        self.is_grayscale = settings.value("grayscale_enabled", False, type=bool)

        # Image processing constants
        self.MIN_ZOOM = 0.1
        self.MAX_ZOOM = 10.0
        self.ZOOM_STEP = 0.1

    def cleanup(self):
        """Stop background threads; call from the main window's closeEvent."""
        self.preloader.stop()

    def _on_image_preloaded(self, path, pixmap):
        """Handle preloaded image from background thread."""
        # Add to cache
        self._pixmap_cache[path] = pixmap

        # Limit cache size (LRU-style)
        if len(self._pixmap_cache) > self._max_cache_size:
            # Remove oldest (first) item
            first_key = next(iter(self._pixmap_cache))
            del self._pixmap_cache[first_key]

    def preload_images(self, paths):
        """Request preloading of images in background."""
        for path in paths[:5]:  # Preload next 5 images
            if path not in self._pixmap_cache and os.path.exists(path):
                self.preloader.add_path(path)

    def display_image(self, img_path, fast_mode=False):
        """Display an image with current zoom, pan, and transform settings."""
        if BENCHMARK:
            start_total = time.perf_counter()

        if not img_path or not os.path.exists(img_path):
            self.image_label.clear()
            self.image_label.setText("Image not found")
            return False

        # Check if image is too large for Qt
        if self._is_image_too_large(img_path):
            self.image_label.clear()
            self.image_label.setText("Image too large to display")
            return False

        self.current_image = img_path

        # Set background according to settings (skip adaptive background in fast mode - expensive!)
        if BENCHMARK:
            start_bg = time.perf_counter()

        mode = self.settings.value("bg_mode", "Black")
        if mode == "Adaptive Color" and not fast_mode:
            set_adaptive_bg(self.image_label, img_path)
        elif mode == "Gray":
            self.image_label.parentWidget().setStyleSheet("background-color: #444444;")
        elif mode == "Black" or (mode == "Adaptive Color" and fast_mode):
            # Use black background in fast mode even for adaptive (avoid expensive sampling)
            self.image_label.parentWidget().setStyleSheet("background-color: #000000;")

        if BENCHMARK:
            print(f"  BG: {(time.perf_counter() - start_bg) * 1000:.1f}ms")

        # Load and process the image
        success = self._load_and_process_image(img_path, fast_mode)

        if success:
            self.image_changed.emit(img_path)

        if BENCHMARK:
            total_time = (time.perf_counter() - start_total) * 1000
            print(f"TOTAL DISPLAY: {total_time:.1f}ms (fast_mode={fast_mode})")
            print("-" * 50)

        return success

    def _is_image_too_large(self, img_path):
        """Check if an image file is likely too large for Qt to handle."""
        try:
            file_size = os.path.getsize(img_path)
            # Skip files larger than 500MB - likely to cause Qt issues
            return file_size > 500 * 1024 * 1024
        except OSError:
            return False

    def _load_and_process_image(self, img_path, fast_mode=False):
        """Load image and apply current transforms and zoom."""
        try:
            if BENCHMARK:
                start_load = time.perf_counter()

            # Check cache first for instant loading
            cache_hit = img_path in self._pixmap_cache
            if cache_hit:
                pixmap = self._pixmap_cache[img_path]
                if BENCHMARK:
                    print(
                        f"  CACHE HIT: {(time.perf_counter() - start_load) * 1000:.1f}ms"
                    )
            else:
                # Cache miss - load from disk using fast Pillow
                pixmap = self._load_with_pillow(img_path, fast_mode)
                if BENCHMARK:
                    print(
                        f"  LOAD DISK (Pillow): {(time.perf_counter() - start_load) * 1000:.1f}ms"
                    )

                if not pixmap.isNull():
                    # Add to cache for future use
                    self._pixmap_cache[img_path] = pixmap
                    # Limit cache size
                    if len(self._pixmap_cache) > self._max_cache_size:
                        first_key = next(iter(self._pixmap_cache))
                        del self._pixmap_cache[first_key]

            if pixmap.isNull():
                self.image_label.clear()
                self.image_label.setText("Failed to load image")
                return False

            return self._process_image_immediately(pixmap, img_path, fast_mode)

        except Exception as e:
            print(f"Error loading image: {e}")
            self.image_label.clear()
            self.image_label.setText("Error loading image")
            return False

    def _load_with_pillow(self, img_path, fast_mode=False):
        """Load image using fastest available method: TurboJPEG > Pillow > Qt."""
        try:
            # Check if it's a JPEG and TurboJPEG is available
            file_ext = os.path.splitext(img_path)[1].lower()
            is_jpeg = file_ext in (".jpg", ".jpeg")

            if is_jpeg and TURBOJPEG_AVAILABLE:
                # Use TurboJPEG for blazing fast JPEG loading (1.5x faster!)
                if BENCHMARK:
                    print("  Using TurboJPEG")

                with open(img_path, "rb") as f:
                    jpeg_data = f.read()

                # Decode JPEG to RGB array
                if fast_mode:
                    # Use fast scaling for speed - TurboJPEG can scale during decode!
                    container_size = self.image_label.size()
                    # Scale factors: 1/8, 1/4, 1/2, 1
                    # Use 1/2 for fast mode
                    bgr_array = jpeg.decode(jpeg_data, scaling_factor=(1, 2))
                else:
                    bgr_array = jpeg.decode(jpeg_data)

                # Convert BGR to RGB
                import numpy as np

                rgb_array = np.ascontiguousarray(bgr_array[:, :, ::-1])

                # Create QImage from numpy array
                height, width, channel = rgb_array.shape
                bytes_per_line = 3 * width
                qimage = QImage(
                    rgb_array.data, width, height, bytes_per_line, QImage.Format_RGB888
                )

                # Keep reference to prevent garbage collection
                qimage._array_ref = rgb_array

                return QPixmap.fromImage(qimage)

            else:
                # Use Pillow for non-JPEG images
                pil_image = Image.open(img_path)

                # Use draft mode for JPEG - must be called BEFORE loading pixel data!
                if pil_image.format == "JPEG" and fast_mode:
                    container_size = self.image_label.size()
                    max_size = (container_size.width(), container_size.height())
                    pil_image.draft("RGB", max_size)

                # Load pixel data
                pil_image.load()

                # Convert to RGB if needed
                if pil_image.mode not in ("RGB", "RGBA"):
                    pil_image = pil_image.convert("RGB")

                # Convert PIL to QPixmap
                if pil_image.mode == "RGBA":
                    data = pil_image.tobytes("raw", "RGBA")
                    qimage = QImage(
                        data,
                        pil_image.width,
                        pil_image.height,
                        pil_image.width * 4,
                        QImage.Format_RGBA8888,
                    )
                else:
                    data = pil_image.tobytes("raw", "RGB")
                    qimage = QImage(
                        data,
                        pil_image.width,
                        pil_image.height,
                        pil_image.width * 3,
                        QImage.Format_RGB888,
                    )

                return QPixmap.fromImage(qimage)

        except Exception as e:
            # Fallback to Qt loading if everything fails
            if BENCHMARK:
                print(f"  Fast loading failed, using Qt: {e}")
            return QPixmap(img_path)

    def _process_image_immediately(self, pixmap, img_path, fast_mode=False):
        """Process image with transforms and display immediately."""
        try:
            if BENCHMARK:
                start_process = time.perf_counter()

            # OPTIMIZATION: Use reference instead of expensive copy for caching
            # Only copy if we need to modify the pixmap
            self._cached_pixmap = pixmap

            # Fast mode: Skip transforms if none are active (for rapid navigation)
            if fast_mode and not (
                self.is_flipped_h or self.is_flipped_v or self.is_grayscale
            ):
                # Direct display for speed with fast transformation
                self._update_zoom_display(use_fast_transform=True)
                if BENCHMARK:
                    print(
                        f"  PROCESS (fast, no transforms): {(time.perf_counter() - start_process) * 1000:.1f}ms"
                    )
                return True

            # Apply transforms to cached pixmap
            if BENCHMARK:
                start_transform = time.perf_counter()

            transform = QTransform()

            if self.is_flipped_h:
                transform = transform.scale(-1, 1)
            if self.is_flipped_v:
                transform = transform.scale(1, -1)

            if self.is_flipped_h or self.is_flipped_v:
                # Use fast transform in fast_mode
                transform_mode = (
                    Qt.FastTransformation if fast_mode else Qt.SmoothTransformation
                )
                self._cached_pixmap = self._cached_pixmap.transformed(
                    transform, transform_mode
                )

            # Apply grayscale if enabled
            if self.is_grayscale:
                image = self._cached_pixmap.toImage()
                image = self._apply_improved_grayscale(image)
                self._cached_pixmap = QPixmap.fromImage(image)

            if BENCHMARK and (
                self.is_flipped_h or self.is_flipped_v or self.is_grayscale
            ):
                print(
                    f"  TRANSFORM: {(time.perf_counter() - start_transform) * 1000:.1f}ms"
                )

            # Update display with zoom - use fast transform in fast mode
            self._update_zoom_display(use_fast_transform=fast_mode)

            if BENCHMARK:
                print(
                    f"  PROCESS (with transforms): {(time.perf_counter() - start_process) * 1000:.1f}ms"
                )

            return True

        except Exception as e:
            print(f"Error processing image: {e}")
            self.image_label.clear()
            self.image_label.setText("Error processing image")
            return False

    def _apply_improved_grayscale(self, image):
        """Apply improved grayscale conversion."""
        return image.convertToFormat(QImage.Format_Grayscale8)

    def _update_zoom_display(self, use_fast_transform=False):
        """Update the image display with current zoom and pan settings."""
        if BENCHMARK:
            start_zoom = time.perf_counter()

        if not self._cached_pixmap:
            return

        # Get container size (label size)
        container_size = self.image_label.size()
        original_size = self._cached_pixmap.size()

        # Calculate target size based on zoom
        if self.zoom_factor == 1.0:
            # For zoom level 1.0, fit image to container
            target_size = original_size.scaled(container_size, Qt.KeepAspectRatio)
        else:
            # Calculate zoom from the fit-to-container size
            if (
                original_size.width() <= container_size.width()
                and original_size.height() <= container_size.height()
            ):
                # Scale from original size for small images
                target_size = original_size * self.zoom_factor
            else:
                # Scale from fit-to-container size for large images
                fit_size = original_size.scaled(container_size, Qt.KeepAspectRatio)
                target_size = fit_size * self.zoom_factor

        if BENCHMARK:
            start_scale = time.perf_counter()

        # Scale the cached pixmap - use fast transform for rapid navigation
        transform_mode = (
            Qt.FastTransformation if use_fast_transform else Qt.SmoothTransformation
        )
        scaled = self._cached_pixmap.scaled(
            target_size, Qt.KeepAspectRatio, transform_mode
        )

        if BENCHMARK:
            print(
                f"  SCALE ({transform_mode}): {(time.perf_counter() - start_scale) * 1000:.1f}ms"
            )

        # Apply panning - always use canvas when there's any pan offset
        if self.pan_offset_x != 0 or self.pan_offset_y != 0:
            if BENCHMARK:
                start_pan = time.perf_counter()

            # Create a canvas the size of the label
            canvas = QPixmap(self.image_label.size())

            # Get the appropriate background color based on current mode
            bg_color = self._get_current_background_color()
            canvas.fill(bg_color)

            # Paint the scaled image with offset
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            # Calculate position to center the image with pan offset
            x = (self.image_label.width() - scaled.width()) // 2 + self.pan_offset_x
            y = (self.image_label.height() - scaled.height()) // 2 + self.pan_offset_y

            # Draw the scaled image at offset position
            painter.drawPixmap(x, y, scaled)
            painter.end()

            self.image_label.setPixmap(canvas)

            if BENCHMARK:
                print(f"  PAN: {(time.perf_counter() - start_pan) * 1000:.1f}ms")
        else:
            if BENCHMARK:
                start_set = time.perf_counter()

            self.image_label.setPixmap(scaled)
            # Force immediate update in fast mode - don't wait for event loop
            if use_fast_transform:
                self.image_label.repaint()

            if BENCHMARK:
                print(f"  SET_PIXMAP: {(time.perf_counter() - start_set) * 1000:.1f}ms")

        if BENCHMARK:
            print(f"  ZOOM_DISPLAY: {(time.perf_counter() - start_zoom) * 1000:.1f}ms")

    def _get_current_background_color(self):
        """Get the current background color as QColor based on the active mode."""
        mode = self.settings.value("bg_mode", "Black")

        if mode == "Gray":
            return QColor(0x44, 0x44, 0x44)  # #444444
        elif mode == "Adaptive Color":
            parent = self.image_label.parentWidget()
            if parent:
                style = parent.styleSheet()
                import re

                rgb_match = re.search(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", style)
                if rgb_match:
                    r, g, b = map(int, rgb_match.groups())
                    return QColor(r, g, b)
            return QColor(40, 40, 40)
        else:
            return QColor(0, 0, 0)

    # Zoom Methods
    def zoom_in(self):
        """Zoom in on the image."""
        if self.zoom_factor < self.MAX_ZOOM:
            self.zoom_factor = min(self.zoom_factor + self.ZOOM_STEP, self.MAX_ZOOM)
            self._update_zoom_display()
            self.zoom_changed.emit(self.zoom_factor)

    def zoom_out(self):
        """Zoom out on the image."""
        if self.zoom_factor > self.MIN_ZOOM:
            self.zoom_factor = max(self.zoom_factor - self.ZOOM_STEP, self.MIN_ZOOM)
            self._update_zoom_display()
            self.zoom_changed.emit(self.zoom_factor)

    def handle_wheel_zoom(self, angle):
        """Handle mouse wheel zoom."""
        if angle > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def reset_zoom(self):
        """Reset zoom to fit-to-container and center image."""
        self.zoom_factor = 1.0
        self.reset_pan()
        self._update_zoom_display()
        self.zoom_changed.emit(self.zoom_factor)

    # Pan Methods
    def start_panning(self, pos):
        """Start panning operation."""
        pass  # Just for signal connection, actual panning handled in handle_panning

    def handle_panning(self, delta):
        """Handle panning movement with improved logic."""
        if not self._cached_pixmap:
            return

        # Get image and container dimensions for calculations
        container_size = self.image_label.size()

        # Always allow panning if there's currently a pan offset (to reset position)
        new_offset_x = self.pan_offset_x + delta.x()
        new_offset_y = self.pan_offset_y + delta.y()

        if self.zoom_factor > 1.0:
            # Apply panning with constraints
            # Get current displayed image size
            original_size = self._cached_pixmap.size()
            if (
                original_size.width() <= container_size.width()
                and original_size.height() <= container_size.height()
            ):
                # Constrain panning so image doesn't go too far off screen
                target_size = original_size * self.zoom_factor
            else:
                fit_size = original_size.scaled(container_size, Qt.KeepAspectRatio)
                # Constrain panning so image doesn't go too far off screen
                target_size = fit_size * self.zoom_factor

            max_offset_x = max(
                0, (target_size.width() - container_size.width()) // 2 + 50
            )
            max_offset_y = max(
                0, (target_size.height() - container_size.height()) // 2 + 50
            )

            self.pan_offset_x = max(-max_offset_x, min(max_offset_x, new_offset_x))
            self.pan_offset_y = max(-max_offset_y, min(max_offset_y, new_offset_y))
        else:
            # Allow small movements even when zoomed out to help repositioning
            max_movement = min(container_size.width(), container_size.height()) // 4
            self.pan_offset_x = max(-max_movement, min(max_movement, new_offset_x))
            self.pan_offset_y = max(-max_movement, min(max_movement, new_offset_y))

        self._update_zoom_display()

    def end_panning(self):
        """End panning operation."""
        pass  # Panning state is maintained until next pan or reset

    def reset_pan(self):
        """Reset pan offset to center."""
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        if self.current_image:
            self._update_zoom_display()

    # Transform Methods
    def flip_horizontal(self):
        """Toggle horizontal flip of the image."""
        self.is_flipped_h = not self.is_flipped_h
        if self.current_image:
            self.display_image(self.current_image)
        self.transform_changed.emit()

    def flip_vertical(self):
        """Toggle vertical flip of the image."""
        self.is_flipped_v = not self.is_flipped_v
        if self.current_image:
            self.display_image(self.current_image)
        self.transform_changed.emit()

    def toggle_grayscale(self):
        """Toggle grayscale mode."""
        self.is_grayscale = not self.is_grayscale
        if self.current_image:
            self.display_image(self.current_image)
        self.transform_changed.emit()

    # Background Methods
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

    def change_bg_mode(self, mode):
        """Change the background color mode."""
        self.settings.setValue("bg_mode", mode)
        if self.current_image:
            self.display_image(self.current_image)

    # State Methods
    def get_zoom_info(self):
        """Get current zoom information."""
        return {
            "zoom_factor": self.zoom_factor,
            "pan_offset_x": self.pan_offset_x,
            "pan_offset_y": self.pan_offset_y,
        }

    def get_transform_info(self):
        """Get current transform information."""
        return {
            "is_flipped_h": self.is_flipped_h,
            "is_flipped_v": self.is_flipped_v,
            "is_grayscale": self.is_grayscale,
        }

    def reset_all_transforms(self):
        """Reset all image transforms to default state."""
        self.is_flipped_h = False
        self.is_flipped_v = False
        self.is_grayscale = False
        self.zoom_factor = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0

        if self.current_image:
            self.display_image(self.current_image)

        self.zoom_changed.emit(self.zoom_factor)
        self.transform_changed.emit()

    def reset_all_transforms_without_display(self):
        """Reset all image transforms to default state without re-displaying image."""
        self.is_flipped_h = False
        self.is_flipped_v = False
        self.is_grayscale = False
        self.zoom_factor = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0

        self.zoom_changed.emit(self.zoom_factor)
        self.transform_changed.emit()

    def reset_positional_transforms_without_display(self):
        """Reset zoom/pan and flips but preserve user preferences like grayscale."""
        self.is_flipped_h = False
        self.is_flipped_v = False
        # Preserve grayscale - it's a user preference that should persist across collections
        self.zoom_factor = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0

        self.zoom_changed.emit(self.zoom_factor)
        self.transform_changed.emit()
