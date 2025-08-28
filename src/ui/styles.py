"""UI styling constants and themes."""

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