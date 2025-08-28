## Phase 1: Foundation & Code Quality
- [x] Refactor the main.py and make it modular - easier to maintain
- [x] Remove on-click proceed (simple cleanup)

## Phase 2: UI/UX Improvements
- [x] Change timer to just a plain minimal loading bar at the bottom of the window. It should be overlayed and semi-transparent to reduce clutter
- [x] Add button overlay in the bottom middle, semi-transparent and increases opacity on hover. The buttons will be (from left to right order):
    - previous
    - pause
    - stop
    - next
- [x] Buttons should have clean, simple icons
- [x] Change app icon from default Python icon when building executable

## Phase 3: Feature Enhancements
- [x] Maybe add zoom buttons, make zooming smoother
- [x] Good to have panning as well and add reset of panning, reference https://github.com/marcel-goldschen-ohm/PyQtImageViewer
- [ ] Maybe improve grayscale? https://tannerhelland.com/2011/10/01/grayscale-image-algorithm-vb6.html

## Phase 4: Major Features
- [x] Add collections feature where a collection is basically a list of paths where to load images
- [x] Upon loading the app, users have the option to quick shuffle a folder or to create/load/delete collection, for reference use ShuffleBird https://github.com/PuffedUpBirdie/ShuffleBird

## Refactor
- [ ] Context menu doesn't reflect the current collections workflow and the play/pause, next, previous, stop we have. 

## Bugs
- [x] There's a bug when creating a collection. After selecting a folder, it hides the file dialog but then shows it again. 
- [x] Fix play, pause, stop timer buttons. Make it consistent with enable/disable timer function in context menu.
- [x] Image panning behavior is strange specially when image is zoomed out. The image cannot be panned anymore when the image is zoomed out even if it is out of center.
- [x] Play button looks small that other buttons.
- [x] Quick shuffle closes application instead of opening viewer. 