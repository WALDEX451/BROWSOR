"""Qt WebEngine Widgets needs QtQml libraries, but BROWSOR loads no QML plugins.

Keep the normal dependency discovery without bundling the wheel's unrelated
QML applications and add-on plugins.
"""
from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
