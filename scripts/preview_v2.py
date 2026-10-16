"""Render the real application with isolated preferences and check page layout."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from homepage import register_scheme, render_home
from browser import BrowserWindow

register_scheme()
app = QApplication(sys.argv)
app.setStyle("Fusion")
for font in ('segoeui.ttf', 'segoeuib.ttf', 'segoeuil.ttf'):
    QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / font))
app.setFont(QFont('Segoe UI', 10))
output = ROOT / '.preview'
output.mkdir(exist_ok=True)
settings = QSettings(str(output / 'v2.ini'), QSettings.Format.IniFormat)
settings.clear()
settings.setValue('profile/name', 'Ewout')
settings.setValue('appearance/accent', 'Mint')
settings.setValue('preferences/ai_provider', 'ChatGPT')
window = BrowserWindow(settings)
window.resize(1440, 1000)
window.show()
failures = []

def check_layout(label):
    window.current_view().page().runJavaScript(
        "JSON.stringify({overflow:document.documentElement.scrollWidth>innerWidth, heading:document.querySelector('h1')?.innerText, unresolved:document.body.innerText.includes('__')})",
        lambda result: record(label, result))

def record(label, result):
    import json
    data = json.loads(result)
    print(label, data, flush=True)
    if data['overflow'] or data['unresolved'] or not data['heading']:
        failures.append(label)

def capture():
    check_layout('desktop')
    window.grab().save(str(ROOT / 'assets' / 'preview-v2.png'))
    (output / 'start-v2.html').write_text(render_home(window.prefs, False), encoding='utf-8')
    window.resize(800, 800)
    QTimer.singleShot(1200, compact)

def compact():
    check_layout('small window')
    window.grab().save(str(output / 'v2-small.png'))
    # Exercise tab creation, closing, and reopening against local content.
    window.new_tab()
    assert window.tabs.count() == 2
    window.close_current_tab()
    assert window.tabs.count() == 1
    # Internal start pages are intentionally not added to the closed-web-tabs list.
    window.reopen_tab()
    assert window.tabs.count() == 1
    QTimer.singleShot(700, finish)

def finish():
    window.close()
    app.exit(1 if failures else 0)

QTimer.singleShot(5000, capture)
QTimer.singleShot(20000, lambda: app.exit(2))
sys.exit(app.exec())
