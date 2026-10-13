# Third-party software

BROWSOR's Windows package includes unmodified third-party runtime libraries. Their licenses apply independently of the BROWSOR application code. Copies of license texts and notices are in the adjacent `LICENSES` folder.

| Component | Version | Source and notices |
| --- | --- | --- |
| Qt / Qt WebEngine | 6.11.1 | [Qt source archives](https://download.qt.io/archive/qt/6.11/6.11.1/), [Qt licensing](https://doc.qt.io/qt-6/licensing.html) |
| PySide6 / Shiboken6 | 6.11.1 | [Qt for Python source](https://code.qt.io/cgit/pyside/pyside-setup.git/?h=v6.11.1), [notices](https://doc.qt.io/qtforpython-6/licenses.html) |
| Chromium and its dependencies | See About BROWSOR | `LICENSES/Qt-WebEngine.html` and the adjacent attribution pages from the Qt 6.11 documentation |
| Python | See BUILD-INFO.json | `LICENSES/Python.txt`, [Python source](https://www.python.org/downloads/source/) |
| PyInstaller bootloader | 6.22.3 | `LICENSES/pyinstaller/COPYING.txt`, [source](https://github.com/pyinstaller/pyinstaller/tree/v6.22.3) |

The Qt and Qt for Python components used here are distributed under their applicable LGPL terms; the LGPL and GPL license texts are included. Chromium and other dependencies carry their own notices. The package retains the notices supplied by the original Python wheels, including alternative commercial-license text; including that text does not grant a commercial Qt license.

Qt libraries remain separate dynamic libraries under `_internal`. They are not statically linked into BROWSOR. You may replace or modify the LGPL components for your own use and reverse engineer for debugging such modifications, as permitted by their licenses. The application source and packaging recipe are available in this repository; building from source provides a route to using a compatible modified Qt/PySide runtime. No restriction in the application overrides rights granted by a third-party license.

Original BROWSOR artwork and application code have not been assigned an open-source license. Public source availability alone does not grant a general reuse license.

The Qt documentation snapshots in `LICENSES/` include attribution pages for additional Qt modules for completeness; inclusion of a notice does not mean that module is shipped. Documentation copyright and its GNU Free Documentation License notice are retained in the pages. Original sources are at https://doc.qt.io/qt-6.11/ and https://doc.qt.io/qtforpython-6/.
