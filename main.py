"""Launch BROWSOR from any working directory with `python main.py`."""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from appdata import APP_NAME
from browser import BrowserWindow
from homepage import register_scheme
from version import VERSION


def main():
    if "--version" in sys.argv:
        print(f"{APP_NAME} {VERSION}")
        return
    register_scheme()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    window = BrowserWindow()
    window.show()
    QTimer.singleShot(150, window.finish_startup)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
