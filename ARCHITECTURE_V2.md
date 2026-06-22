# Glimpse V2 Architecture - Feh-Based Rewrite

## Overview

Complete rewrite of Glimpse using **feh** as the image rendering backend while maintaining the same UI/UX. This approach leverages feh's C-based performance (instant image loading) while adding a Python/Qt UI layer for collection management and controls.

## Why Rewrite?

### Current Issues (V1)
- Python/Qt image loading: 50-400ms per image (too slow for rapid navigation)
- Even with optimizations (TurboJPEG, caching), Python overhead limits performance
- Complex architecture with multiple managers and signal chains

### Benefits of Feh-Based Approach (V2)
- **Instant image loading** - feh's C/Imlib2 backend loads images in <10ms
- **Native performance** - No Python/Qt overhead for rendering
- **Simpler architecture** - Feh handles all image rendering, we just control it
- **Cross-platform** - Works on Linux, can adapt for Windows/macOS with alternatives

## Architecture Design

### Core Concept

```
┌─────────────────────────────────────────────────┐
│  Python/Qt UI Layer (Glimpse)                   │
│  - Collection management                        │
│  - Startup dialog                               │
│  - Navigation controls                          │
│  - Timer system                                 │
└──────────────────┬──────────────────────────────┘
                   │ IPC/Signals
┌──────────────────▼──────────────────────────────┐
│  Feh Process (Image Rendering)                  │
│  - Blazing fast image display                   │
│  - Handles zoom, pan, transforms                │
│  - X11/Wayland rendering                        │
└─────────────────────────────────────────────────┘
```

### Two Possible Approaches

#### **Option 1: Embedded Feh (Recommended for Linux)**
- Embed feh window inside Qt container using `--window-id`
- Qt provides UI chrome (buttons, dialogs, menus)
- Feh renders images in embedded window
- Seamless integration

```python
# Get Qt widget's X11 window ID
window_id = self.image_container.winId()

# Launch feh embedded in our window
subprocess.Popen([
    'feh',
    '--window-id', str(window_id),
    '--scale-down',
    '--auto-zoom',
    image_path
])
```

**Pros:**
- Single unified window
- Native feh performance
- Can add Qt overlays (buttons, progress bar)

**Cons:**
- Linux/X11 only (doesn't work on Windows/macOS)
- Window management complexity

#### **Option 2: Headless Control (Cross-Platform)**
- Feh runs in separate window (fullscreen or borderless)
- Python controls feh via signals/IPC
- Qt UI provides separate control panel or overlay

```python
# Launch feh in slideshow mode
feh_process = subprocess.Popen([
    'feh',
    '--fullscreen',
    '--slideshow-delay', '0',  # Manual control
    '--image-bg', 'black',
    *image_list
])

# Send signals to control feh
def next_image():
    os.kill(feh_process.pid, signal.SIGUSR1)

def previous_image():
    os.kill(feh_process.pid, signal.SIGUSR2)
```

**Pros:**
- Works with any feh version
- Simpler window management
- Can adapt to Windows/macOS with different viewers

**Cons:**
- Separate windows
- Less integrated feel

#### **Option 3: Hybrid - Custom Imlib2 Renderer**
- Use PyImlib2 bindings directly (like feh does internally)
- Render to Qt QWidget using custom painting
- Best of both worlds

**Pros:**
- Cross-platform potential
- Full control
- Native performance

**Cons:**
- More complex implementation
- May not have good Python bindings

## Recommended Architecture: Embedded Feh (Linux) + Fallback

### Component Structure

```
glimpse/
├── src/
│   ├── core/
│   │   ├── feh_controller.py          # Feh process management
│   │   ├── image_manager.py           # Image list management
│   │   ├── collections.py             # Collection system (keep existing)
│   │   └── settings.py                # Settings management
│   ├── ui/
│   │   ├── main_window.py             # Main window with embedded feh
│   │   ├── startup_dialog.py          # Collection selector (keep existing)
│   │   ├── controls_overlay.py        # Transparent overlay for buttons
│   │   └── widgets/
│   │       ├── feh_container.py       # Widget that hosts feh window
│   │       └── control_panel.py       # Navigation controls
│   └── platform/
│       ├── linux_feh.py               # Linux feh implementation
│       ├── windows_wic.py             # Windows fallback (WIC viewer)
│       └── macos_preview.py           # macOS fallback (Preview)
├── main.py
└── ARCHITECTURE_V2.md                 # This file
```

### Key Classes

#### **FehController**
```python
class FehController:
    """Manages feh subprocess and communication."""

    def __init__(self, window_id):
        self.window_id = window_id
        self.process = None
        self.current_index = 0
        self.images = []

    def load_image(self, image_path):
        """Load a single image in feh."""
        if self.process:
            self.process.terminate()

        self.process = subprocess.Popen([
            'feh',
            '--window-id', str(self.window_id),
            '--scale-down',
            '--auto-zoom',
            '--image-bg', 'black',
            image_path
        ])

    def navigate_next(self):
        """Navigate to next image."""
        if self.current_index < len(self.images) - 1:
            self.current_index += 1
            self.load_image(self.images[self.current_index])

    def navigate_prev(self):
        """Navigate to previous image."""
        if self.current_index > 0:
            self.current_index -= 1
            self.load_image(self.images[self.current_index])
```

#### **FehContainer Widget**
```python
class FehContainer(QWidget):
    """Qt widget that hosts the feh window."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: black;")

        # Enable native window for X11 embedding
        self.setAttribute(Qt.WA_NativeWindow, True)
        self.setAttribute(Qt.WA_DontCreateNativeAncestors, True)

    def winId(self):
        """Get X11 window ID for feh embedding."""
        return super().winId()
```

#### **MainWindow**
```python
class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # Create feh container
        self.feh_container = FehContainer()

        # Create feh controller
        self.feh_controller = None  # Initialize in showEvent

        # Create controls overlay
        self.controls = ControlsOverlay(self.feh_container)

        # Setup UI
        self.setup_ui()

    def showEvent(self, event):
        """Initialize feh when window is shown."""
        super().showEvent(event)
        if not self.feh_controller:
            window_id = self.feh_container.winId()
            self.feh_controller = FehController(window_id)
```

## UI/UX Preservation

### Keep from V1
- ✅ **Startup Dialog** - Collection/folder selection with timer config
- ✅ **Collection System** - Multi-folder collections with sorting
- ✅ **Timer System** - Auto-advance with play/pause/stop controls
- ✅ **Dark Theme** - Professional dark UI aesthetic
- ✅ **Button Overlays** - Media-style controls at bottom
- ✅ **History Panel** - Navigation history with thumbnails
- ✅ **Keyboard Shortcuts** - Same shortcuts (arrows, space, etc.)
- ✅ **Settings Persistence** - QSettings for preferences

### Change in V2
- ❌ **Image Display** - Delegate to feh instead of Qt QLabel
- ❌ **Zoom/Pan** - Use feh's built-in zoom/pan controls
- ❌ **Transforms** - Use feh's flip/rotate if available
- ⚠️ **Grayscale** - May need custom implementation or skip

## Implementation Plan

### Phase 1: Proof of Concept
1. Create simple Qt window with embedded feh widget
2. Test feh `--window-id` integration
3. Implement basic next/previous navigation
4. Verify performance (should be instant!)

### Phase 2: Core Functionality
1. Port collection management system
2. Implement FehController with full navigation
3. Add history tracking
4. Integrate timer system

### Phase 3: UI Polish
1. Port startup dialog
2. Add control overlays
3. Implement keyboard shortcuts
4. Add settings persistence

### Phase 4: Platform Support
1. Test on different Linux distros
2. Implement Windows fallback (optional)
3. Implement macOS fallback (optional)

## Migration Strategy

### Git Branching
```bash
# Current main branch
git checkout main

# Create V2 development branch
git checkout -b v2-feh-rewrite

# Keep V1 as fallback
git checkout -b v1-backup
git push origin v1-backup
```

### Code Reuse
- **Keep**: Collection system, startup dialog, settings, utils
- **Rewrite**: Image display, zoom/pan, main window
- **Remove**: ImageDisplayManager, pre-loading cache, Qt image loading

### File Organization
```
v2-feh-rewrite/
├── src/
│   ├── core/
│   │   ├── collections.py        # FROM V1 (reuse)
│   │   ├── feh_controller.py     # NEW
│   │   └── image_utils.py        # SIMPLIFIED (no Qt image loading)
│   └── ui/
│       ├── startup_dialog.py     # FROM V1 (reuse with minor changes)
│       ├── main_window.py        # REWRITE
│       └── widgets/
│           ├── feh_container.py  # NEW
│           └── controls.py       # NEW (simplified from V1 managers)
```

## Performance Expectations

### V1 (Current - Qt-based)
- First image load: 50-400ms
- Cached images: 1-5ms
- Rapid navigation: Acceptable but not instant

### V2 (Feh-based) - Expected
- First image load: **<10ms** (feh is instant!)
- Cached images: **<10ms** (same, feh handles everything)
- Rapid navigation: **Feels like native feh** (instantaneous)

## Fallback Strategy

If feh embedding proves difficult:
1. Use separate feh window (headless control mode)
2. Fall back to V1 architecture with TurboJPEG optimizations
3. Consider platform-specific viewers:
   - Linux: feh or sxiv
   - Windows: Custom DirectX/WIC viewer
   - macOS: Use native ImageIO

## Success Criteria

V2 is successful if:
- ✅ Image navigation feels **instant** (like feh)
- ✅ All V1 features preserved (collections, timer, history)
- ✅ Same UI/UX aesthetic maintained
- ✅ Works reliably on Linux
- ✅ Code is simpler and more maintainable than V1

## Questions to Resolve

1. **Window embedding stability** - Does `--window-id` work reliably across window managers?
2. **Event handling** - Can we capture keyboard events in Qt while feh has focus?
3. **Overlays** - Can we draw Qt widgets on top of embedded feh window?
4. **Cross-platform** - Is this worth pursuing for Windows/macOS, or Linux-only?

## Next Steps

1. ✅ Create this architecture document
2. ✅ Create `v2-feh-rewrite` branch
3. ⏳ Build proof of concept (feh embedding test)
4. ⏳ Test performance and window integration
5. ⏳ Decide: proceed with V2 or optimize V1 further?

---

**Decision Point**: After POC, we decide whether the complexity of feh embedding is worth the performance gain, or if V1 with TurboJPEG is "good enough."
