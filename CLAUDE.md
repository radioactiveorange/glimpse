# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Glimpse** is a cross-platform desktop application for viewing random images from collections, built with Python and PySide6 (Qt). The application features a sophisticated startup system for collection management, professional image viewing capabilities, and an artist-focused workflow. It uses a modular architecture with clean separation between UI components, core functionality, and data management.

## Development Commands

### Running the Application
- **With uv (preferred):** `uv run main.py`
- **With Python:** `python main.py`

### Dependencies
- Install dependencies: `uv pip install pyside6`
- For build dependencies: `uv pip install pyinstaller pyside6`
- Python 3.13+ is required (specified in pyproject.toml)
- Main dependency: PySide6>=6.9.1 (Qt for Python)

### Building Executable
- Install PyInstaller: `uv pip install pyinstaller`
- **Recommended**: Build using spec file: `pyinstaller glimpse.spec`
- Manual build (Windows): `pyinstaller --noconfirm --onefile --windowed --icon=app_icon.ico --name=glimpse main.py`
- Manual build (Linux/macOS): `pyinstaller --noconfirm --onefile --windowed --icon=app_icon.png --name=glimpse main.py`
- Output binary will be in the `dist/` folder
- **Cross-platform icons**: Spec file bundles both PNG and ICO, build-time selects appropriate format

## Architecture

### Modular Structure
The application is organized into a clean modular structure:

- **`main.py`**: Application entry point with startup dialog integration
- **`src/ui/`**: User interface components (~4900 lines)
  - `main_window.py`: Main application window (GlimpseViewer class) - 1047 lines
  - `startup_dialog.py`: Professional startup screen for collection management - 529 lines
  - `widgets.py`: Custom widgets (ClickableLabel, MinimalProgressBar, ButtonOverlay) - 414 lines
  - `collection_dialog.py`: Collection creation and editing dialogs - 307 lines
  - `loading_dialog.py`: Async loading dialog with progress indication for large collections - 236 lines
  - `timer_dialog.py`: Timer configuration dialog for collections/folders - 153 lines
  - `styles.py`: Dark theme stylesheet constants - 203 lines
  - **`components/`**: Reusable UI components
    - `centered_dialog.py`: Base class for centered dialogs
    - `sorting_panel.py`: Sort options panel for collections
  - **`managers/`**: UI logic managers for separation of concerns
    - `image_display_manager.py`: Zoom, pan, transformations - 380 lines
    - `menu_manager.py`: Context menus and actions - 277 lines
    - `history_manager.py`: Navigation history with thumbnails - 221 lines
    - `media_controls_manager.py`: Timer controls - 172 lines
- **`src/core/`**: Core functionality (~736 lines)
  - `image_utils.py`: Image processing utilities and professional icon creation - 511 lines
  - `collections.py`: Collection management system with JSON storage - 225 lines
- **`app_icon.png/ico/svg`**: Multi-format application icons for cross-platform builds
- **`icons/`**: SVG icon collection (19 icons) for UI elements - geometric style

### Key Features Implementation
- **Startup System**: Professional dialog with collection management and timer configuration
- **Collection Management**: JSON-based storage with CollectionManager class
- **Image Display**: Advanced QLabel with pixmap scaling, transformation, and panning support
- **History System**: List-based navigation with thumbnail panel (QListWidget)
- **Timer System**: QTimer-based auto-advance with media-style controls (play/pause/stop)
- **Professional UI**: Button overlays with consistent geometric icons
- **Loading System**: Asynchronous image loading with progress dialog for large collections (72K+ images)
- **Settings Persistence**: QSettings with cross-platform data directory support
- **Signal Architecture**: Clean signal/slot communication between startup and main window
  - Object-typed signals for complex data (tuples, custom objects)
  - Collection/folder signals emit tuples: `(data, timer_enabled, timer_interval)`
- **Window Management**: All dialogs and windows automatically center on screen with multi-monitor support

### State Management
- Image transformations (flip, grayscale) applied via QTransform
- Background modes (black, gray, adaptive) handled through stylesheet updates
- Zoom levels managed through QLabel scaling
- History navigation with bidirectional index tracking

## Code Patterns

### Qt Widget Styling
The application uses a comprehensive dark theme stylesheet (`DARK_STYLESHEET`) that should be maintained when adding new UI elements.

### Image Processing
- Supported formats defined in `IMAGE_EXTENSIONS` constant
- Image loading uses QPixmap with error handling
- Transformations applied through QTransform matrix operations

### Event Handling
- Custom `keyPressEvent()` for keyboard shortcuts
- Context menu actions connected via Qt signals/slots
- Timer events handled through QTimer callbacks

## Development Guidelines

### Manager Pattern Architecture
The application uses a manager-based architecture to separate UI concerns:
- **ImageDisplayManager**: Handles zoom, pan, image transformations, and display logic
- **MediaControlsManager**: Manages timer controls (play/pause/stop) and their synchronization
- **HistoryManager**: Manages navigation history and thumbnail panel
- **MenuManager**: Handles context menus and keyboard shortcuts
- Each manager is a QObject with its own signals and encapsulated logic
- Managers communicate via signals to maintain loose coupling

### Code Patterns
- **Qt Signal Architecture**: Use object-typed signals for complex data (tuples, custom objects)
- **Error Handling**: Implement graceful fallbacks for cancelled dialogs and invalid data
- **Icon System**: SVG-based icons (19 available) with fallback to coded icons via `create_professional_icon()` with consistent sizing (16x16)
- **Settings Management**: Use QSettings with proper cross-platform paths
- **Image Loading**: Always use QPixmap with error handling for unsupported formats
- **Memory Management**: Cache processed pixmaps (`_cached_pixmap`) for smooth UI operations
- **Async Loading**: Use LoadingDialog with QThread (ImageLoadingWorker) for large collections
- **Threading**: Worker threads should emit progress signals and handle cancellation gracefully
- **Dialog Centering**: All dialogs inherit from CenteredDialog or implement `center_on_screen()`
- **Component Reusability**: Use components/ for reusable UI elements

### Current Status (Phase 4 Complete)
All major features have been implemented:
- ✅ **Collections System**: Multi-folder collections with full CRUD operations
- ✅ **Startup Workflow**: Professional ShuffleBird-inspired interface
- ✅ **Timer Configuration**: Flexible timer settings for any viewing session
- ✅ **Professional UI**: Media-style controls with consistent icon design
- ✅ **Smart Panning**: Intelligent constraints based on image and zoom state
- ✅ **Performance Optimization**: Async loading prevents UI freezing during large collection creation
- ✅ **Window Management**: All windows and dialogs properly centered with multi-monitor support

### Maintenance Notes
- **Timer Consistency**: Play/pause/stop buttons synchronized with context menu
- **Panning Logic**: Intelligent constraints - allows repositioning when image is off-center, regardless of zoom
- **Collections Storage**: JSON files in platform-appropriate user data directories via QStandardPaths
- **Startup Flow**: Application uses startup dialog pattern - main window only shows after selection
- **Widget Hierarchy**: GlimpseViewer (main) ← StartupDialog → Collection/Folder selection
- **Loading Performance**: LoadingDialog prevents UI freezing for large collections (72K+ images tested)
- **Collection Creation**: Async image counting during collection creation prevents freezing
- **Thread Safety**: Worker threads properly stopped in dialog closeEvent to prevent crashes
- **Dialog Positioning**: All dialogs use `availableGeometry()` and `frameGeometry()` for accurate centering

When making changes, preserve the existing dark theme aesthetic and ensure cross-platform compatibility (Windows, macOS, Linux).

## Agent skills

### Issue tracker

Issues are tracked as local markdown files under `.scratch/<feature>/` — no remote issue tracker. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
