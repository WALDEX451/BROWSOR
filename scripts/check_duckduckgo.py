"""Check DuckDuckGo navigation from the actual start-page form and address bar."""
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import parse_qs, urlsplit

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-gpu')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication
from appdata import HOME_URL, resolve_destination
from browser import BrowserWindow
from homepage import register_scheme

register_scheme()
app = QApplication(sys.argv)
temporary = tempfile.TemporaryDirectory(prefix='browsor-search-')
settings = QSettings(str(Path(temporary.name) / 'settings.ini'), QSettings.Format.IniFormat)
window = BrowserWindow(settings)
window.show()
query = 'BROWSOR browser & privacy'
results = {}
stage = 'home'

def finish(code):
    print(json.dumps(results, indent=2), flush=True)
    window.close()
    app.exit(code)

def loaded(ok):
    global stage
    view = window.current_view()
    if stage == 'home' and view.url() == HOME_URL and ok:
        results['default_engine'] = window.prefs.search_engine
        address = urlsplit(resolve_destination(query).toString())
        results['address_resolution'] = address.hostname == 'duckduckgo.com' and parse_qs(address.query).get('q') == [query]
        stage = 'form'
        view.page().runJavaScript("document.querySelector('input[name=q]').value=" + json.dumps(query) + "; document.querySelector('form.search').requestSubmit();")
    elif stage == 'form':
        url = urlsplit(view.url().toString())
        if url.hostname and url.hostname.endswith('duckduckgo.com'):
            results['form_query'] = parse_qs(url.query).get('q') == [query]
            results['search_page_loaded'] = ok
            results['title'] = view.title()
            stage = 'address'
            window.address_bar.setText('DuckDuckGo privacy browser')
            window.navigate_to_address()
    elif stage == 'address':
        url = urlsplit(view.url().toString())
        results['address_bar_navigation'] = url.hostname == 'duckduckgo.com' and parse_qs(url.query).get('q') == ['DuckDuckGo privacy browser']
        results['address_page_loaded'] = ok
        finish(0 if all(results.get(k) for k in ('address_resolution', 'form_query', 'search_page_loaded', 'address_bar_navigation', 'address_page_loaded')) else 1)

window.current_view().loadFinished.connect(loaded)
window.current_view().page().loadingChanged.connect(lambda info: print('LOAD', info.url().toString(), info.errorCode(), info.errorString(), flush=True) if info.errorCode() else None)
QTimer.singleShot(50000, lambda: (results.update(timeout=True), finish(2)))
sys.exit(app.exec())
