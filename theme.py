"""Shared vector icons and visual tokens for the browser and its local pages."""

from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

PATHS = {
    "command": '<path d="M9 7V5a2 2 0 1 0-2 2h10a2 2 0 1 0-2-2v14a2 2 0 1 0 2-2H7a2 2 0 1 0 2 2V7Z"/>',
    "copy": '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v.5"/>',
    "back": '<path d="m14 6-6 6 6 6M8 12h12"/>',
    "forward": '<path d="m10 6 6 6-6 6M4 12h12"/>',
    "reload": '<path d="M20 7v5h-5M19.1 7A8 8 0 1 0 20 16"/>',
    "home": '<path d="m3 10 9-7 9 7M5 9v11h5v-6h4v6h5V9"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "close": '<path d="m6 6 12 12M6 18 18 6"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    "shield": '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
    "spark": '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3ZM20 2v4M18 4h4"/>',
    "star": '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9L12 3Z"/>',
    "star-filled": '<path fill="currentColor" d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9L12 3Z"/>',
    "lock": '<rect x="5" y="10" width="14" height="11" rx="3"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
    "external": '<path d="M14 3h7v7M21 3l-11 11M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/>',
    "sliders": '<path d="M4 6h5m4 0h7M4 12h9m4 0h3M4 18h3m4 0h9"/><circle cx="11" cy="6" r="2"/><circle cx="15" cy="12" r="2"/><circle cx="9" cy="18" r="2"/>',
    "menu": '<path d="M5 6h14M5 12h14M5 18h14"/>',
    "download": '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 6 0 0 1 16 0v2"/>',
    "leaf": '<path d="M20 3C6 2 2 10 5 16s15 6 15-13ZM4 21l11-11"/>',
    "book": '<path d="M12 5c-3-2-6-2-10-1v15c4-1 7-1 10 1 3-2 6-2 10-1V4c-4-1-7-1-10 1Zm0 0v15"/>',
    "briefcase": '<rect x="3" y="7" width="18" height="14" rx="3"/><path d="M8 7V3h8v4M3 12a20 20 0 0 0 18 0M12 12v3"/>',
}


def svg(name: str, color: str = "currentColor", size: int = 24) -> str:
    if name == "logo":
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 32 32"><rect width="32" height="32" rx="10" fill="{color}"/><path d="M10 8v16h6a5 5 0 0 0 0-10h-6m0 0h5a3 3 0 0 0 0-6h-5" fill="none" stroke="#171820" stroke-width="2.4" stroke-linejoin="round"/></svg>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" color="{color}" stroke="{color}" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">{PATHS.get(name, PATHS["globe"])}</svg>'


def icon(name: str, color: str = "#acacbd") -> QIcon:
    # Render at 2x so the same icon stays sharp on high-DPI displays.
    renderer = QSvgRenderer(QByteArray(svg(name, color, 48).encode()))
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


def stylesheet(accent: str = "#c4b5fd") -> str:
    return """
    QMainWindow, QDialog { background: #f5f5f7; }
    QWidget { color: #1d1d1f; font-family: 'Segoe UI'; font-size: 13px; }
    QLabel { background: transparent; }
    QFrame#chrome { background: rgba(255,255,255,235); border-bottom: 1px solid #d2d2d7; }
    QLabel#brand { font-size: 13px; font-weight: 800; letter-spacing: 2px; padding-right: 4px; }
    QToolButton#betaBadge { color: #007aff; background: #e8f2ff; border: 1px solid #b7d7ff; font-size: 9px; letter-spacing: 1px; padding: 4px 7px; border-radius: 6px; }
    QLabel#muted, QLabel#help { color: #6e6e73; }
    QLabel#help { font-size: 12px; }
    QLabel#eyebrow { color: #007aff; font-size: 11px; font-weight: 700; letter-spacing: 2px; }
    QLabel#dialogTitle { font-size: 29px; font-weight: 700; }
    QLabel#fieldLabel { color: #3a3a3c; font-size: 12px; font-weight: 600; }
    QLabel#error { color: #c9343d; }
    QToolButton { background: transparent; border: 1px solid transparent; border-radius: 10px; padding: 7px; }
    QToolButton:hover { background: #e9e9ed; color: #1d1d1f; }
    QToolButton:pressed, QToolButton:checked { background: #dcecff; color: #007aff; }
    QToolButton:focus { border-color: ACCENT; }
    QToolButton:disabled { color: #50515e; }
    QToolButton#aiToggle { background: #e8f2ff; color: #007aff; padding: 8px 14px; font-weight: 600; }
    QToolButton#aiToggle:hover, QToolButton#aiToggle:checked { background: #dcecff; }
    QToolButton#avatar { background: #dcecff; color: #007aff; font-weight: 700; border-radius: 16px; }
    QTabBar { background: transparent; qproperty-drawBase: 0; }
    QTabBar::tab { background: transparent; color: #6e6e73; min-width: 100px; max-width: 195px; padding: 9px 12px; margin: 0 3px; border: 1px solid transparent; border-radius: 9px; }
    QTabBar::tab:selected { background: #e9e9ed; border-color: #d2d2d7; color: #1d1d1f; }
    QTabBar::tab:hover:!selected { background: #f0f0f2; }
    QToolButton#tabClose { padding: 3px; border: 0; border-radius: 5px; }
    QLineEdit, QComboBox { background: #ffffff; color: #1d1d1f; border: 1px solid #d2d2d7; border-radius: 10px; padding: 10px 13px; selection-background-color: #b7d7ff; }
    QLineEdit:focus, QComboBox:focus { border-color: ACCENT; }
    QLineEdit#address { background: #f5f5f7; border: 1px solid #d2d2d7; border-radius: 13px; padding: 10px 9px; }
    QLineEdit#address:focus { border-color: #007aff; background: #ffffff; }
    QComboBox { padding-right: 25px; }
    QComboBox::drop-down { border: 0; width: 25px; }
    QComboBox::down-arrow { image: url(ARROW_ICON); width: 14px; height: 14px; }
    QComboBox QAbstractItemView { background: #252632; border: 1px solid #414250; padding: 6px; selection-background-color: #443b57; outline: none; }
    QProgressBar { border: 0; background: #e9e9ed; }
    QProgressBar::chunk { background: #007aff; }
    QStatusBar { background: #f5f5f7; color: #6e6e73; border-top: 1px solid #d2d2d7; font-size: 11px; }
    QStatusBar::item { border: 0; }
    QSplitter::handle { background: #343440; }
    QFrame#aiPanel { background: #ffffff; }
    QFrame#card, QFrame#findBar { background: #ffffff; border: 1px solid #d2d2d7; border-radius: 12px; }
    QLabel#panelTitle { font-size: 17px; font-weight: 700; }
    QPushButton { background: #f0f0f2; border: 1px solid #d2d2d7; border-radius: 10px; padding: 10px 18px; font-weight: 600; }
    QPushButton:hover { background: #e5e5ea; border-color: #b8b8bd; }
    QPushButton:focus { border-color: ACCENT; }
    QPushButton:checked { border-color: ACCENT; color: ACCENT; background: #302c3d; }
    QPushButton#primary { background: #007aff; color: #fff; border-color: #007aff; }
    QPushButton#primary:hover { background: #0068d6; }
    QPushButton#secondary { background: transparent; }
    QPushButton:disabled { color: #666675; background: #22232d; border-color: #30313a; }
    QCheckBox { spacing: 10px; padding: 7px 0; }
    QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #b8b8bd; border-radius: 5px; background: #fff; }
    QCheckBox::indicator:checked { background: ACCENT; border-color: ACCENT; image: url(CHECK_ICON); }
    QListWidget { background: #fff; border: 1px solid #d2d2d7; border-radius: 12px; padding: 6px; outline: none; }
    QListWidget::item { padding: 12px; border-radius: 8px; }
    QListWidget::item:selected { background: #3b334b; color: #f1ebff; }
    QListWidget::item:hover:!selected { background: #42453b; }
    QMenu { background: #fff; border: 1px solid #d2d2d7; padding: 7px; border-radius: 9px; }
    QMenu::item { padding: 9px 25px 9px 12px; border-radius: 6px; }
    QMenu::item:selected { background: #3c344c; }
    QMenu::separator { height: 1px; background: #3b3b49; margin: 6px; }
    QToolTip { background: #1d1d1f; color: #fff; border: 1px solid #1d1d1f; padding: 6px; }
    QScrollBar:vertical { width: 9px; background: transparent; }
    QScrollBar::handle:vertical { background: #4a475a; min-height: 24px; border-radius: 4px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    """.replace("ACCENT", accent).replace("CHECK_ICON", (Path(__file__).parent / "assets" / "check.svg").as_posix()).replace("ARROW_ICON", (Path(__file__).parent / "assets" / "chevron.svg").as_posix())
