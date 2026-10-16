"""Browser chrome, tabs, AI workspace and WebEngine lifecycle."""

import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, QStandardPaths, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings, QWebEngineUrlRequestInterceptor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu,
    QMessageBox, QProgressBar, QPushButton, QSplitter, QStackedWidget,
    QTabBar, QToolButton, QVBoxLayout, QWidget,
)

from appdata import APP_NAME, AI_PROVIDERS, HOME_URL, SEARCH_ENGINES, Preferences, resolve_destination
from dialogs import BookmarkDialog, BookmarksDialog, CommandDialog, SetupDialog, label
from homepage import HomeSchemeHandler
from theme import icon, stylesheet
from version import DISPLAY_VERSION, RELEASE_URL, REPOSITORY_URL, VERSION

TRACKER_DOMAINS = (
    "doubleclick.net", "google-analytics.com", "googletagmanager.com",
    "googlesyndication.com", "connect.facebook.net", "facebook.net",
    "hotjar.com", "segment.io", "segment.com", "clarity.ms", "adnxs.com",
    "scorecardresearch.com",
)


def is_home(url: QUrl) -> bool:
    return url.scheme() == "browsor" and url.host() == "home"


class TrackingFilter(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None, enabled=True):
        super().__init__(parent)
        self.enabled = enabled

    def interceptRequest(self, info):
        if not self.enabled:
            return
        host = info.requestUrl().host().lower()
        first_party = info.firstPartyUrl().host().lower()
        for domain in TRACKER_DOMAINS:
            if host == domain or host.endswith("." + domain):
                if first_party != domain and not first_party.endswith("." + domain):
                    info.block(True)
                break


class BrowserPage(QWebEnginePage):
    internal_action = Signal(str)

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        scheme = url.scheme().lower()
        if (is_main_frame and is_home(self.url()) and scheme in ("http", "https")
                and navigation_type == QWebEnginePage.NavigationType.NavigationTypeFormSubmitted):
            # Chromium blocks a local-scheme document from submitting to the web.
            # Start the top-level navigation natively without granting local pages
            # remote-resource access. Preserve the form's encoded query unchanged.
            destination = QUrl(url)
            QTimer.singleShot(0, lambda: self.setUrl(destination))
            return False
        if scheme == "browsor":
            if url.host() == "action":
                # Remote documents cannot invoke native settings/favorites actions.
                if is_main_frame and is_home(self.url()) and navigation_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
                    self.internal_action.emit(url.path().strip("/"))
                return False
            return is_main_frame and is_home(url)
        if is_main_frame:
            return scheme in ("http", "https") or url.toString() == "about:blank"
        return scheme in ("http", "https", "about", "data", "blob")


class BrowserTab(QStackedWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.loading, self.cancelled, self.progress = False, False, 0
        self.view = window.make_web_view(self)
        self.addWidget(self.view)
        self.error_page = QWidget()
        layout = QVBoxLayout(self.error_page)
        layout.setContentsMargins(45, 45, 45, 45)
        layout.addStretch()
        symbol = QLabel()
        symbol.setPixmap(icon("globe", window.prefs.accent).pixmap(46, 46))
        layout.addWidget(symbol, alignment=Qt.AlignmentFlag.AlignHCenter)
        title = label("This page is temporarily unavailable.", "dialogTitle", True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        self.error_text = label("Check the address or your internet connection, then try again.", "muted", True)
        self.error_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_text)
        row = QHBoxLayout()
        row.addStretch()
        home = QPushButton("Go to your start page")
        home.clicked.connect(lambda: self.view.setUrl(HOME_URL))
        retry = QPushButton("Try again")
        retry.setObjectName("primary")
        retry.clicked.connect(self.view.reload)
        row.addWidget(home)
        row.addWidget(retry)
        row.addStretch()
        layout.addSpacing(15)
        layout.addLayout(row)
        layout.addStretch()
        self.addWidget(self.error_page)
        self.view.loadStarted.connect(self.started)
        self.view.loadProgress.connect(self.progress_changed)
        self.view.loadFinished.connect(self.finished)
        self.view.page().loadingChanged.connect(self.loading_changed)
        for signal in (self.view.urlChanged, self.view.titleChanged, self.view.iconChanged):
            signal.connect(lambda _value: window.update_tab(self))
        self.view.page().windowCloseRequested.connect(lambda: window.close_view(self))

    def started(self):
        self.loading, self.cancelled, self.progress = True, False, 0
        self.setCurrentWidget(self.view)
        self.window.update_tab(self)

    def progress_changed(self, value):
        self.progress = value
        if self.window.current_tab() is self:
            self.window.progress_bar.setValue(value)

    def finished(self, success):
        self.loading = False
        if not success and not self.cancelled and self.view.url().scheme() in ("http", "https"):
            self.setCurrentWidget(self.error_page)
        self.window.update_tab(self)

    def loading_changed(self, info):
        # Chromium reports cancelled navigation and downloads as aborted loads.
        if info.errorCode() == -3:
            self.cancelled = True
            self.setCurrentWidget(self.view)
        elif info.errorCode() and not self.cancelled:
            self.error_text.setText(f"{info.url().host() or 'This website'} could not be reached.\nCheck your connection and try again.")


class BrowserWindow(QMainWindow):
    def __init__(self, settings: QSettings | None = None):
        super().__init__()
        self.prefs = Preferences(settings)
        self.settings = self.prefs.settings
        self.closed_tabs, self.downloads = [], []
        self.ai_view = None
        self._shutting_down = False
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(icon("logo", self.prefs.accent))
        self.resize(1320, 900)
        self.setMinimumSize(860, 620)
        QApplication.instance().setStyleSheet(stylesheet(self.prefs.accent))
        self.persistent = self.prefs.flag("privacy/remember_signins")
        if self.persistent:
            self.profile = QWebEngineProfile("BROWSOR", self)
            storage = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / "web-profile"
            self.profile.setPersistentStoragePath(str(storage))
            self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        else:
            self.profile = QWebEngineProfile(self)
            self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        self.tracking_filter = TrackingFilter(self.profile, self.prefs.flag("privacy/tracking", True))
        self.profile.setUrlRequestInterceptor(self.tracking_filter)
        self.home_handler = HomeSchemeHandler(self.prefs, self.persistent, self.profile)
        self.profile.installUrlSchemeHandler(b"browsor", self.home_handler)
        self.profile.downloadRequested.connect(self.download_requested)

        self.tabs = QTabBar()
        self.tabs.setMovable(True)
        self.tabs.setExpanding(False)
        self.tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setMinimumWidth(80)
        self.tabs.setIconSize(QSize(15, 15))
        self.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.tab_menu)
        self.pages = QStackedWidget()
        self.pages.setMinimumWidth(300)
        self.tabs.currentChanged.connect(self.select_tab)
        self.tabs.tabMoved.connect(self.move_tab)
        self.tabs.tabBarDoubleClicked.connect(lambda index: self.new_tab() if index < 0 else None)
        chrome = QFrame()
        chrome.setObjectName("chrome")
        chrome_layout = QVBoxLayout(chrome)
        chrome_layout.setContentsMargins(16, 10, 16, 12)
        chrome_layout.setSpacing(10)
        tab_row = QHBoxLayout()
        tab_row.setSpacing(6)
        self.brand_mark = QLabel()
        self.brand_mark.setPixmap(icon("logo", self.prefs.accent).pixmap(28, 28))
        tab_row.addWidget(self.brand_mark)
        tab_row.addWidget(label(APP_NAME, "brand"))
        beta = QToolButton()
        beta.setText(DISPLAY_VERSION)
        beta.setObjectName("betaBadge")
        beta.setToolTip("About BROWSOR " + DISPLAY_VERSION)
        beta.clicked.connect(self.show_about)
        tab_row.addWidget(beta)
        tab_row.addSpacing(10)
        tab_row.addWidget(self.tabs)
        self.new_tab_button = self.tool("plus", "New tab · Ctrl+T", self.new_tab)
        tab_row.addWidget(self.new_tab_button)
        tab_row.addStretch(1)
        tab_row.addWidget(self.tool("command", "Tabs, favorites and quick actions · Ctrl+K", self.show_commands))
        self.profile_button = self.tool("user", "Your profile and preferences", self.open_settings)
        self.profile_button.setObjectName("avatar")
        self.profile_button.setFixedSize(33, 33)
        tab_row.addWidget(self.profile_button)
        self.menu_button = self.tool("menu", "Browser menu", self.show_menu)
        tab_row.addWidget(self.menu_button)
        chrome_layout.addLayout(tab_row)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(5)
        self.back_button = self.tool("back", "Back · Alt+Left", lambda: self.current_view().back())
        self.forward_button = self.tool("forward", "Forward · Alt+Right", lambda: self.current_view().forward())
        self.reload_button = self.tool("reload", "Reload · Ctrl+R", self.reload_or_stop)
        self.home_button = self.tool("home", "Your start page · Alt+Home", self.go_home)
        for button in (self.back_button, self.forward_button, self.reload_button, self.home_button):
            toolbar.addWidget(button)
        toolbar.addSpacing(7)
        self.address_bar = QLineEdit()
        self.address_bar.setObjectName("address")
        self.address_bar.setAccessibleName("Search or enter a web address")
        self.address_bar.setPlaceholderText("Search or enter a web address")
        self.address_bar.setMinimumWidth(180)
        self.address_bar.returnPressed.connect(self.navigate_to_address)
        self.address_icon = self.address_bar.addAction(icon("search"), QLineEdit.ActionPosition.LeadingPosition)
        self.bookmark_action = self.address_bar.addAction(icon("star"), QLineEdit.ActionPosition.TrailingPosition)
        self.bookmark_action.triggered.connect(self.bookmark_current)
        toolbar.addWidget(self.address_bar, 1)
        toolbar.addSpacing(7)
        self.privacy_button = self.tool("shield", "Tracker filter", self.toggle_tracking)
        self.privacy_button.setCheckable(True)
        toolbar.addWidget(self.privacy_button)
        self.ai_button = self.tool("spark", "AI beside your page · Ctrl+Shift+A", self.toggle_ai_panel)
        self.ai_button.setText("AI space")
        self.ai_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.ai_button.setObjectName("aiToggle")
        self.ai_button.setCheckable(True)
        toolbar.addWidget(self.ai_button)
        chrome_layout.addLayout(toolbar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        self.find_bar = self.create_find_bar()
        self.find_bar.hide()
        self.ai_panel = self.create_ai_panel()
        self.ai_panel.hide()
        self.browser_splitter = QSplitter()
        self.browser_splitter.setChildrenCollapsible(False)
        self.browser_splitter.setHandleWidth(1)
        self.browser_splitter.addWidget(self.pages)
        self.browser_splitter.addWidget(self.ai_panel)
        self.browser_splitter.setStretchFactor(0, 1)
        self.browser_splitter.setStretchFactor(1, 0)
        self.browser_splitter.setSizes([920, 390])
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(chrome)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.find_bar)
        layout.addWidget(self.browser_splitter, 1)
        self.setCentralWidget(root)
        self.session_label = label("  Sign-ins saved  " if self.persistent else "  Temporary cookies  ", "help")
        self.zoom_label = label("100%", "help")
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().addPermanentWidget(self.zoom_label)
        self.statusBar().addPermanentWidget(self.session_label)
        self.statusBar().showMessage("Your space. For what's next.")
        shortcuts = {
            "Ctrl+L": self.focus_address_bar, "Ctrl+T": self.new_tab,
            "Ctrl+W": self.close_current_tab, "Ctrl+Shift+T": self.reopen_tab,
            "Ctrl+R": self.reload_current, "F5": self.reload_current,
            "Ctrl+Shift+A": self.toggle_ai_panel, "Ctrl+D": self.bookmark_current,
            "Ctrl+Shift+B": self.show_bookmarks, "Ctrl+F": self.show_find,
            "Ctrl+J": self.show_downloads, "Ctrl+,": self.open_settings,
            "Ctrl+K": self.show_commands,
            "Ctrl++": lambda: self.change_zoom(.1), "Ctrl+=": lambda: self.change_zoom(.1),
            "Ctrl+-": lambda: self.change_zoom(-.1), "Ctrl+0": self.reset_zoom,
            "Alt+Left": lambda: self.current_view().back(), "Alt+Right": lambda: self.current_view().forward(),
            "Alt+Home": self.go_home, "Ctrl+Tab": lambda: self.cycle_tab(1),
            "Ctrl+Shift+Tab": lambda: self.cycle_tab(-1), "F11": self.toggle_fullscreen,
            "Escape": self.escape,
        }
        for key, callback in shortcuts.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
        for number in range(1, 10):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{number}"), self)
            shortcut.activated.connect(lambda n=number: self.tabs.setCurrentIndex(min(n - 1, self.tabs.count() - 1) if n < 9 else self.tabs.count() - 1))
        geometry = self.settings.value("window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        saved_urls, active = self.prefs.saved_session()
        for url in saved_urls or [HOME_URL.toString()]:
            self.new_tab(url)
        self.tabs.setCurrentIndex(active)
        self.apply_preferences()

    def tool(self, glyph, tooltip, callback=None):
        button = QToolButton()
        button.setIcon(icon(glyph))
        button.setIconSize(QSize(18, 18))
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip.split(" · ")[0])
        button.setFixedSize(34, 34)
        if callback:
            button.clicked.connect(lambda _checked=False: callback())
        return button

    def make_web_view(self, parent):
        view = QWebEngineView(parent)
        page = BrowserPage(self.profile, view)
        page.setBackgroundColor(QColor("#13141b"))
        view.setPage(page)
        page.settings().setAttribute(QWebEngineSettings.WebAttribute.HyperlinkAuditingEnabled, False)
        page.settings().setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, False)
        page.internal_action.connect(lambda action: QTimer.singleShot(0, lambda: self.internal_action(action)))
        page.newWindowRequested.connect(self.open_web_window)
        page.linkHovered.connect(lambda url: self.statusBar().showMessage(url, 4000))
        page.findTextFinished.connect(lambda result: self.find_result(view, result))
        return view

    def current_tab(self):
        return self.pages.currentWidget()

    def current_view(self):
        return self.current_tab().view

    def new_tab(self, url=None, load=True):
        tab = BrowserTab(self)
        self.pages.addWidget(tab)
        index = self.tabs.addTab(icon("logo", self.prefs.accent), "New tab")
        close = self.tool("close", "Close tab", lambda: self.close_view(tab))
        close.setObjectName("tabClose")
        close.setFixedSize(20, 20)
        close.setIconSize(QSize(12, 12))
        self.tabs.setTabButton(index, QTabBar.ButtonPosition.RightSide, close)
        self.tabs.setCurrentIndex(index)
        self.pages.setCurrentWidget(tab)
        if load:
            tab.view.setUrl(QUrl(url) if url else HOME_URL)
        self.focus_address_bar()
        return tab

    def select_tab(self, index):
        if index < 0 or index >= self.pages.count():
            return
        self.pages.setCurrentIndex(index)
        self.update_controls(force_address=True)
        if self.find_bar.isVisible():
            self.find_text()

    def move_tab(self, old, new):
        moved = self.pages.widget(old)
        self.pages.removeWidget(moved)
        self.pages.insertWidget(new, moved)
        self.pages.setCurrentIndex(self.tabs.currentIndex())
        self.update_controls(force_address=True)

    def close_view(self, tab):
        index = self.pages.indexOf(tab)
        if index < 0:
            return
        if self.tabs.count() == 1:
            tab.view.setUrl(HOME_URL)
            return
        url = tab.view.url()
        if url.scheme() in ("http", "https"):
            self.closed_tabs.append(url.toString())
            self.closed_tabs = self.closed_tabs[-20:]
        self.tabs.blockSignals(True)
        self.pages.removeWidget(tab)
        self.tabs.removeTab(index)
        self.tabs.blockSignals(False)
        tab.view.stop()
        tab.deleteLater()
        self.select_tab(self.tabs.currentIndex())

    def close_current_tab(self):
        self.close_view(self.current_tab())

    def reopen_tab(self):
        if self.closed_tabs:
            self.new_tab(self.closed_tabs.pop())

    def cycle_tab(self, direction):
        self.tabs.setCurrentIndex((self.tabs.currentIndex() + direction) % self.tabs.count())

    def tab_menu(self, point):
        index = self.tabs.tabAt(point)
        menu = QMenu(self)
        menu.addAction("New tab", self.new_tab)
        if index >= 0:
            tab = self.pages.widget(index)
            menu.addAction("Duplicate", lambda: self.new_tab(tab.view.url()))
            menu.addAction("Close", lambda: self.close_view(tab))
        if self.closed_tabs:
            menu.addAction("Reopen closed tab", self.reopen_tab)
        menu.exec(self.tabs.mapToGlobal(point))

    def update_tab(self, tab):
        index = self.pages.indexOf(tab)
        if index < 0 or self._shutting_down:
            return
        home = is_home(tab.view.url())
        title = "Your start" if home else tab.view.title() or tab.view.url().host() or "New tab"
        self.tabs.setTabText(index, title)
        self.tabs.setTabToolTip(index, title)
        tab_icon = icon("logo", self.prefs.accent) if home else tab.view.icon()
        self.tabs.setTabIcon(index, tab_icon if not tab_icon.isNull() else icon("globe"))
        if tab is self.current_tab():
            self.update_controls()

    def update_controls(self, force_address=False):
        tab = self.current_tab()
        if tab is None or self._shutting_down:
            return
        view, url = tab.view, tab.view.url()
        home = is_home(url) or url.isEmpty()
        if force_address or not self.address_bar.hasFocus():
            self.address_bar.setText("" if home else url.toDisplayString())
            self.address_bar.setCursorPosition(0)
        self.address_icon.setIcon(icon("search" if home else "lock" if url.scheme() == "https" else "globe"))
        self.address_icon.setToolTip("Your start page" if home else "HTTPS connection" if url.scheme() == "https" else "Unencrypted HTTP connection")
        self.back_button.setEnabled(view.history().canGoBack())
        self.forward_button.setEnabled(view.history().canGoForward())
        self.reload_button.setIcon(icon("close" if tab.loading else "reload"))
        self.reload_button.setToolTip("Stop loading" if tab.loading else "Reload · Ctrl+R")
        self.progress_bar.setValue(tab.progress if tab.loading else 0)
        saved = any(item["url"] == url.toString() for item in self.prefs.bookmarks)
        self.bookmark_action.setIcon(icon("star-filled" if saved else "star", self.prefs.accent if saved else "#9792a7"))
        self.bookmark_action.setEnabled(url.scheme() in ("http", "https"))
        self.bookmark_action.setToolTip("Edit favorite · Ctrl+D" if saved else "Save favorite · Ctrl+D")
        self.zoom_label.setText(f"{round(view.zoomFactor() * 100)}%")
        self.setWindowTitle(f"{self.tabs.tabText(self.tabs.currentIndex())} · {APP_NAME} {DISPLAY_VERSION}")

    def focus_address_bar(self):
        self.update_controls(force_address=True)
        self.address_bar.setFocus()
        self.address_bar.selectAll()

    def navigate_to_address(self):
        self.navigate(self.address_bar.text())

    def navigate(self, text):
        url = resolve_destination(text, SEARCH_ENGINES[self.prefs.search_engine][0])
        if url is None:
            self.statusBar().showMessage("Enter a search query or a valid HTTP or HTTPS address.", 6000)
            return
        self.current_view().setFocus()
        self.current_view().setUrl(url)

    def go_home(self):
        self.current_view().setUrl(HOME_URL)
        self.current_view().setFocus()

    def reload_current(self):
        self.current_view().reload()

    def reload_or_stop(self):
        tab = self.current_tab()
        if tab.loading:
            tab.cancelled = True
            tab.view.stop()
        else:
            tab.view.reload()

    def open_web_window(self, request):
        if not request.isUserInitiated():
            self.statusBar().showMessage("An automatic pop-up was blocked.", 5000)
            return
        tab = self.new_tab(load=False)
        request.openIn(tab.view.page())

    def internal_action(self, action):
        actions = {"ai": lambda: self.toggle_ai_panel(True), "settings": self.open_settings,
                   "bookmarks": self.show_bookmarks, "add-bookmark": self.add_bookmark,
                   "privacy": self.show_privacy, "commands": self.show_commands, "about": self.show_about}
        if action in actions:
            actions[action]()

    def refresh_home_pages(self):
        for index in range(self.pages.count()):
            view = self.pages.widget(index).view
            if is_home(view.url()):
                view.reload()
        self.update_controls()

    def apply_preferences(self):
        QApplication.instance().setStyleSheet(stylesheet(self.prefs.accent))
        self.brand_mark.setPixmap(icon("logo", self.prefs.accent).pixmap(28, 28))
        self.setWindowIcon(icon("logo", self.prefs.accent))
        self.ai_button.setIcon(icon("spark", self.prefs.accent))
        self.ai_button.setFixedSize(113, 38)
        if self.prefs.name:
            self.profile_button.setText(self.prefs.name[0].upper())
            self.profile_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        else:
            self.profile_button.setIcon(icon("user", self.prefs.accent))
            self.profile_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.tracking_filter.enabled = self.prefs.flag("privacy/tracking", True)
        self.privacy_button.setChecked(self.tracking_filter.enabled)
        self.privacy_button.setIcon(icon("shield", "#99e2c5" if self.tracking_filter.enabled else "#827d90"))
        self.privacy_button.setToolTip("Tracker filter on · click to turn off" if self.tracking_filter.enabled else "Tracker filter off · click to turn on")
        self.ai_selector.setCurrentText(self.prefs.ai_provider)
        self.ai_title.setText(self.prefs.ai_provider)
        self.refresh_home_pages()

    def open_settings(self):
        dialog = SetupDialog(self.prefs, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.apply_preferences()
            message = "Your preferences have been saved."
            if self.prefs.flag("privacy/remember_signins") != self.persistent:
                message += " Website sign-in storage will change after restarting."
            self.statusBar().showMessage(message, 10000)
        dialog.deleteLater()

    def finish_startup(self):
        if not self.prefs.flag("onboarding/welcome_shown"):
            dialog = SetupDialog(self.prefs, self, first_run=True)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.apply_preferences()
                if self.prefs.flag("privacy/remember_signins") != self.persistent:
                    self.statusBar().showMessage("Your setup is saved. Staying signed in to websites takes effect after restarting.", 12000)
            dialog.deleteLater()
        if self.prefs.flag("preferences/open_ai"):
            self.toggle_ai_panel(True)

    def toggle_tracking(self):
        enabled = self.privacy_button.isChecked()
        self.settings.setValue("privacy/tracking", enabled)
        self.settings.sync()
        self.apply_preferences()
        self.statusBar().showMessage(f"Tracker filter {'on' if enabled else 'off'}. Reload an open website to apply the change.", 7000)

    def show_privacy(self):
        session = ("Website cookies are saved on this computer so you can stay signed in."
                   if self.persistent else "This session keeps cookies in memory only. They are removed when you close BROWSOR.")
        tabs = "Tab addresses are saved on exit (up to 20)." if self.prefs.flag("preferences/restore_tabs") else "Tab addresses are not saved on exit."
        QMessageBox.information(self, "BROWSOR privacy", f"{session}\n\n{tabs} Your profile, preferences, and favorites are stored locally. There is no BROWSOR cloud account or synchronization. Switching off saved sign-ins does not erase an older persistent profile.\n\nThe tracker filter is {'on' if self.tracking_filter.enabled else 'off'}. It blocks a limited list of external tracking domains and does not provide anonymity. Websites can see your IP address.\n\nSearch queries go to {self.prefs.search_engine}. AI services process what you send according to their own terms. Page context is only copied when you ask; paste it into the assistant to share it. Downloads remain on your computer.")

    def show_commands(self):
        entries = []
        for index in range(self.pages.count()):
            tab = self.pages.widget(index)
            entries.append((self.tabs.tabText(index), "Open tab · " + tab.view.url().toDisplayString(), "globe", lambda t=tab: self.tabs.setCurrentIndex(self.pages.indexOf(t))))
        for item in self.prefs.bookmarks:
            entries.append((item["title"], "Favorite · " + item["url"], "star", lambda u=item["url"]: self.new_tab(u)))
        for title, detail, glyph, callback in (
            ("New tab", "Action · Ctrl+T", "plus", self.new_tab),
            ("Your start page", "Action · Alt+Home", "home", self.go_home),
            ("AI space", "Action · Ctrl+Shift+A", "spark", self.toggle_ai_panel),
            ("Manage favorites", "Action · Ctrl+Shift+B", "star", self.show_bookmarks),
            ("Downloads", "Action · Ctrl+J", "download", self.show_downloads),
            ("Your preferences", "Action · Ctrl+,", "sliders", self.open_settings),
            ("Reopen closed tab", "Action · Ctrl+Shift+T", "reload", self.reopen_tab),
            ("About BROWSOR", "Action · " + DISPLAY_VERSION, "info", self.show_about),
        ):
            entries.append((title, detail, glyph, callback))
        dialog = CommandDialog(entries, self.navigate, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_callback:
            callback = dialog.result_callback
            QTimer.singleShot(0, callback)
        dialog.deleteLater()

    def show_about(self):
        from PySide6.QtCore import qVersion
        from PySide6.QtWebEngineCore import qWebEngineChromiumVersion
        dialog = QDialog(self)
        dialog.setWindowTitle("About BROWSOR")
        dialog.setMinimumWidth(530)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(32, 30, 32, 28)
        layout.setSpacing(16)
        mark = QLabel()
        mark.setPixmap(icon("logo", self.prefs.accent).pixmap(56, 56))
        layout.addWidget(mark)
        layout.addWidget(label("Your space. For what's next.", "dialogTitle", True))
        layout.addWidget(label("BROWSOR " + DISPLAY_VERSION, "eyebrow"))
        layout.addWidget(label("A personal browser with a local start page and an AI workspace beside the web. This is an early beta; website compatibility is still being improved.", "muted", True))
        layout.addWidget(label(f"Version {VERSION}\nQt {qVersion()} · Chromium {qWebEngineChromiumVersion()}", "help"))
        row = QHBoxLayout()
        for title, url in (("Release notes", RELEASE_URL), ("Report an issue", REPOSITORY_URL + "/issues/new")):
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, u=url: (dialog.accept(), self.new_tab(u)))
            row.addWidget(button)
        layout.addLayout(row)
        close = QPushButton("Back to browsing")
        close.setObjectName("primary")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()
        dialog.deleteLater()

    def add_bookmark(self):
        if len(self.prefs.bookmarks) >= 100:
            self.show_bookmarks()
            return
        dialog = BookmarkDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.prefs.save_bookmarks(self.prefs.bookmarks + [dialog.result_item])
            self.refresh_home_pages()
            self.statusBar().showMessage("Favorite saved.", 4000)
        dialog.deleteLater()

    def bookmark_current(self):
        url = self.current_view().url()
        if url.scheme() not in ("http", "https"):
            self.show_bookmarks()
            return
        items = self.prefs.bookmarks
        existing = next((i for i, item in enumerate(items) if item["url"] == url.toString()), None)
        if existing is None and len(items) >= 100:
            self.show_bookmarks()
            return
        item = items[existing] if existing is not None else {"title": self.current_view().title()[:60], "url": url.toString()}
        dialog = BookmarkDialog(self, **item)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if existing is None:
                items.append(dialog.result_item)
            else:
                items[existing] = dialog.result_item
            self.prefs.save_bookmarks(items)
            self.refresh_home_pages()
            self.statusBar().showMessage("Favorite saved.", 4000)
        dialog.deleteLater()

    def show_bookmarks(self):
        dialog = BookmarksDialog(self.prefs, self)
        dialog.changed.connect(self.refresh_home_pages)
        dialog.open_requested.connect(self.new_tab)
        dialog.exec()
        dialog.deleteLater()

    def create_ai_panel(self):
        panel = QFrame()
        panel.setObjectName("aiPanel")
        panel.setMinimumWidth(320)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        head = QWidget()
        head_layout = QVBoxLayout(head)
        head_layout.setContentsMargins(19, 18, 15, 16)
        head_layout.setSpacing(12)
        row = QHBoxLayout()
        title_column = QVBoxLayout()
        title_column.setSpacing(3)
        title_column.addWidget(label("YOUR AI SPACE", "eyebrow"))
        self.ai_title = label(self.prefs.ai_provider, "panelTitle")
        title_column.addWidget(self.ai_title)
        row.addLayout(title_column, 1)
        row.addWidget(self.tool("external", "Open the assistant in a tab", lambda: self.new_tab(AI_PROVIDERS[self.ai_selector.currentText()])))
        row.addWidget(self.tool("close", "Close AI space", lambda: self.toggle_ai_panel(False)))
        head_layout.addLayout(row)
        self.ai_selector = QComboBox()
        self.ai_selector.setAccessibleName("Choose an AI assistant")
        self.ai_selector.addItems(list(AI_PROVIDERS))
        self.ai_selector.setCurrentText(self.prefs.ai_provider)
        self.ai_selector.currentTextChanged.connect(self.select_ai_provider)
        head_layout.addWidget(self.ai_selector)
        head_layout.addWidget(label("A fresh perspective, right beside your page.", "help"))
        context_row = QHBoxLayout()
        copy = QPushButton("Copy page context")
        copy.setIcon(icon("copy", self.prefs.accent))
        copy.setObjectName("secondary")
        copy.setToolTip("Copy the page title, address and selected text. Paste into your assistant to share.")
        copy.clicked.connect(self.copy_page_context)
        context_row.addWidget(copy, 1)
        context_row.addWidget(self.tool("reload", "Reload your AI assistant", lambda: self.ai_view.reload() if self.ai_view else None))
        head_layout.addLayout(context_row)
        layout.addWidget(head)
        self.ai_status = label("Your assistant is ready.", "help", True)
        self.ai_status.setContentsMargins(19, 0, 19, 12)
        layout.addWidget(self.ai_status)
        self.ai_container = QWidget()
        self.ai_layout = QVBoxLayout(self.ai_container)
        self.ai_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ai_container, 1)
        return panel

    def copy_page_context(self):
        view = self.current_view()
        if view.url().scheme() not in ("http", "https"):
            self.ai_status.setText("Open a website first, then copy its context here.")
            return
        text = f"Page: {view.title()}\nURL: {view.url().toString()}"
        selection = view.page().selectedText().strip()
        if selection:
            text += "\n\nSelected text:\n" + selection[:12000]
            if len(selection) > 12000:
                text += "\n[Selection shortened to 12,000 characters]"
        QApplication.clipboard().setText(text)
        self.ai_status.setText("Copied. Paste into the assistant when you are ready to share.")

    def toggle_ai_panel(self, visible=None):
        show = not self.ai_panel.isVisible() if visible is None else visible
        self.ai_panel.setVisible(show)
        self.ai_button.setChecked(show)
        if show:
            if self.ai_view is None:
                self.ai_view = self.make_web_view(self.ai_container)
                self.ai_view.loadStarted.connect(lambda: self.ai_status.setText("Opening your assistant…"))
                self.ai_view.loadFinished.connect(lambda success: self.ai_status.setText("Sign in on the AI service's website." if success else "Couldn't load the assistant. Try opening it in a tab."))
                self.ai_layout.addWidget(self.ai_view)
                self.ai_view.setUrl(QUrl(AI_PROVIDERS[self.ai_selector.currentText()]))
            if self.browser_splitter.sizes()[1] < 320:
                self.browser_splitter.setSizes([max(420, self.width() - 400), 400])

    def select_ai_provider(self, provider):
        self.settings.setValue("preferences/ai_provider", provider)
        self.settings.sync()
        self.ai_title.setText(provider)
        if self.ai_view is not None:
            self.ai_view.setUrl(QUrl(AI_PROVIDERS[provider]))
        self.refresh_home_pages()

    def create_find_bar(self):
        frame = QFrame()
        frame.setObjectName("findBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.addStretch()
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Find on this page")
        self.find_input.setAccessibleName("Find on this page")
        self.find_input.setMaximumWidth(300)
        self.find_input.textChanged.connect(lambda _: self.find_text())
        self.find_input.returnPressed.connect(self.find_text)
        layout.addWidget(self.find_input)
        self.find_count = label("", "help")
        self.find_count.setMinimumWidth(85)
        layout.addWidget(self.find_count)
        layout.addWidget(self.tool("back", "Previous match", lambda: self.find_text(True)))
        layout.addWidget(self.tool("forward", "Next match", self.find_text))
        layout.addWidget(self.tool("close", "Close find · Esc", self.hide_find))
        return frame

    def show_find(self):
        self.find_bar.show()
        self.find_input.setFocus()
        self.find_input.selectAll()

    def hide_find(self):
        self.find_bar.hide()
        self.current_view().findText("")
        self.current_view().setFocus()

    def find_text(self, backwards=False):
        flags = QWebEnginePage.FindFlag.FindBackward if backwards else QWebEnginePage.FindFlag(0)
        self.current_view().page().findText(self.find_input.text(), flags)

    def find_result(self, view, result):
        if not self._shutting_down and view is self.current_view():
            self.find_count.setText(f"{result.activeMatch()} / {result.numberOfMatches()}" if self.find_input.text() else "")

    def change_zoom(self, difference):
        view = self.current_view()
        view.setZoomFactor(max(.5, min(2.0, round(view.zoomFactor() + difference, 1))))
        self.update_controls()

    def reset_zoom(self):
        self.current_view().setZoomFactor(1.0)
        self.update_controls()

    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def escape(self):
        if self.find_bar.isVisible():
            self.hide_find()
        elif self.isFullScreen():
            self.showNormal()
        elif self.current_tab().loading:
            self.reload_or_stop()

    def show_menu(self):
        menu = QMenu(self)
        for glyph, title, key, callback in (
            ("plus", "New tab", "Ctrl+T", self.new_tab),
            ("command", "Go anywhere", "Ctrl+K", self.show_commands),
            ("star", "Favorites", "Ctrl+Shift+B", self.show_bookmarks),
            ("download", "Downloads", "Ctrl+J", self.show_downloads),
            ("search", "Find on page", "Ctrl+F", self.show_find),
        ):
            action = menu.addAction(icon(glyph), f"{title}\t{key}")
            action.triggered.connect(callback)
        menu.addSeparator()
        zoom = menu.addMenu("Zoom")
        zoom.addAction("Zoom in    Ctrl++", lambda: self.change_zoom(.1))
        zoom.addAction("Zoom out    Ctrl+-", lambda: self.change_zoom(-.1))
        zoom.addAction("Reset zoom    Ctrl+0", self.reset_zoom)
        menu.addAction(icon("shield"), "About your privacy", self.show_privacy)
        menu.addAction(icon("sliders"), "Your preferences\tCtrl+,", self.open_settings)
        menu.addSeparator()
        menu.addAction(icon("info"), "BROWSOR " + DISPLAY_VERSION, self.show_about)
        menu.exec(self.menu_button.mapToGlobal(self.menu_button.rect().bottomRight()))

    def download_requested(self, download):
        if download.isSavePageDownload():
            download.cancel()
            self.statusBar().showMessage("Use a download link to save a file.", 5000)
            return
        folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        filename = Path(download.downloadFileName()).name
        target, _ = QFileDialog.getSaveFileName(self, "Save download", str(Path(folder) / filename))
        if not target:
            download.cancel()
            return
        destination = Path(target)
        download.setDownloadDirectory(str(destination.parent))
        download.setDownloadFileName(destination.name)
        self.downloads.append(download)
        download.stateChanged.connect(lambda _: self.download_update(download))
        download.accept()
        self.statusBar().showMessage(f"Download started: {destination.name} · Ctrl+J for progress", 8000)

    def download_update(self, download):
        if download.isFinished():
            message = "Download saved" if download.state().name == "DownloadCompleted" else "Download stopped"
            self.statusBar().showMessage(f"{message}: {download.downloadFileName()}", 8000)

    def show_downloads(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Downloads · BROWSOR")
        dialog.resize(610, 430)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.addWidget(label("Your downloads.", "dialogTitle"))
        layout.addWidget(label("This list is kept for the current session. Saved files remain on your computer.", "help", True))
        listing = QListWidget()
        layout.addWidget(listing)
        row = QHBoxLayout()
        cancel = QPushButton("Cancel download")
        close = QPushButton("Done")
        close.setObjectName("primary")
        close.clicked.connect(dialog.accept)
        row.addWidget(cancel)
        row.addStretch()
        row.addWidget(close)
        layout.addLayout(row)
        states = {"DownloadRequested": "Waiting", "DownloadInProgress": "In progress", "DownloadCompleted": "Saved", "DownloadCancelled": "Cancelled", "DownloadInterrupted": "Interrupted"}
        def refresh():
            selected = listing.currentRow()
            listing.clear()
            if not self.downloads:
                listing.addItem("No downloads yet. Your next download will appear here.")
            for download in self.downloads:
                received = download.receivedBytes() / (1024 * 1024)
                total = download.totalBytes() / (1024 * 1024)
                progress = f"{received:.1f} / {total:.1f} MB" if total > 0 else f"{received:.1f} MB"
                item = QListWidgetItem(f"{download.downloadFileName()}\n{states.get(download.state().name, 'In progress')} · {progress}")
                item.setToolTip(str(Path(download.downloadDirectory()) / download.downloadFileName()))
                listing.addItem(item)
            listing.setCurrentRow(selected)
            cancel.setEnabled(0 <= selected < len(self.downloads) and not self.downloads[selected].isFinished())
        def stop():
            index = listing.currentRow()
            if 0 <= index < len(self.downloads):
                self.downloads[index].cancel()
            refresh()
        cancel.clicked.connect(stop)
        listing.currentRowChanged.connect(lambda index: cancel.setEnabled(0 <= index < len(self.downloads) and not self.downloads[index].isFinished()))
        timer = QTimer(dialog)
        timer.timeout.connect(refresh)
        timer.start(750)
        refresh()
        dialog.exec()
        timer.stop()
        dialog.deleteLater()

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            try:
                import ctypes
                dark = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(int(self.winId())), 20, ctypes.byref(dark), ctypes.sizeof(dark))
            except (AttributeError, OSError):
                pass

    def closeEvent(self, event):
        active = [download for download in self.downloads if not download.isFinished()]
        if active:
            result = QMessageBox.question(self, "Downloads are still in progress", "Active downloads will stop if you close BROWSOR. Close anyway?", QMessageBox.StandardButton.Close | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
            if result != QMessageBox.StandardButton.Close:
                event.ignore()
                return
            for download in active:
                download.cancel()
        self._shutting_down = True
        self.prefs.save_session([self.pages.widget(index).view.url().toString() for index in range(self.pages.count())], self.tabs.currentIndex())
        if not self.isFullScreen():
            self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.sync()
        for view in self.findChildren(QWebEngineView):
            view.stop()
            view.page().deleteLater()
        event.accept()
