## Phase 1: Foundation & Code Quality
- [ ] Refactor the main.py and make it modular - easier to maintain
- [ ] Remove on-click proceed (simple cleanup)

## Phase 2: UI/UX Improvements
- [ ] Change timer to just a plain minimal loading bar at the bottom of the window. It should be overlayed and semi-transparent to reduce clutter
- [ ] Add button overlay in the bottom middle, semi-transparent and increases opacity on hover. The buttons will be (from left to right order):
    - previous
    - pause
    - stop
    - next
- [ ] Buttons should have clean, simple icons
- [ ] Change app icon from default Python icon when building executable

## Phase 3: Feature Enhancements
- [ ] Maybe add zoom buttons, make zooming smoother
- [ ] Good to have panning as well and add reset of panning, reference https://github.com/marcel-goldschen-ohm/PyQtImageViewer
- [ ] Maybe improve grayscale? https://tannerhelland.com/2011/10/01/grayscale-image-algorithm-vb6.html

## Phase 4: Major Features
- [ ] Add collections feature where a collection is basically a list of paths where to load images
- [ ] Upon loading the app, users have the option to quick shuffle a folder or to create/load/delete collection, for reference use ShuffleBird https://github.com/PuffedUpBirdie/ShuffleBird