"""Editable local profile, first-run setup and real bookmark management."""

from pathlib import Path

from PySide6.QtCore import QIODevice, QSaveFile, QSettings, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from appdata import ACCENTS, AI_PROVIDERS, LEGACY_ACCENTS, PURPOSES, SEARCH_ENGINES, Preferences, web_url
from theme import icon
from bookmarks import MAX_IMPORT_BYTES, merge_bookmarks, read_bookmarks, write_bookmarks


def label(text: str, name: str = "", wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def combo(values, current: str) -> QComboBox:
    widget = QComboBox()
    widget.addItems(list(values))
    if current in values:
        widget.setCurrentText(current)
    return widget


def field(layout, title: str, widget, hint: str = ""):
    heading = label(title, "fieldLabel")
    heading.setBuddy(widget)
    layout.addWidget(heading)
    widget.setAccessibleName(title)
    layout.addWidget(widget)
    if hint:
        layout.addWidget(label(hint, "help", True))
    layout.addSpacing(8)


class SetupDialog(QDialog):
    def __init__(self, prefs: Preferences, parent=None, first_run: bool = False):
        super().__init__(parent)
        self.prefs, self.first_run = prefs, first_run
        self.setWindowTitle("Create your local BROWSOR account" if first_run else "Your BROWSOR account & settings")
        self.setMinimumWidth(620)
        self.resize(660, 650)
        self.setModal(True)
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 26)
        root.setSpacing(14)
        brand_row = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(icon("logo", prefs.accent).pixmap(31, 31))
        brand_row.addWidget(mark)
        brand_row.addWidget(label("BROWSOR  /  MAKE IT YOURS", "eyebrow"))
        brand_row.addStretch()
        self.step_label = label("", "muted")
        brand_row.addWidget(self.step_label)
        root.addLayout(brand_row)
        root.addSpacing(5)
        self.title = label("", "dialogTitle")
        self.description = label("", "muted", True)
        root.addWidget(self.title)
        root.addWidget(self.description)

        navigation = QHBoxLayout()
        navigation.setSpacing(8)
        self.sections = []
        for index, name in enumerate(("01  Account", "02  Browsing", "03  Privacy & style")):
            button = QPushButton(name)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, i=index: self.select_step(i))
            self.sections.append(button)
            navigation.addWidget(button)
        root.addLayout(navigation)
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        profile, layout = self.page()
        self.name_input = QLineEdit(prefs.name)
        self.name_input.setPlaceholderText("What should we call you?")
        self.name_input.setMaxLength(40)
        field(layout, "Your name or nickname", self.name_input,
              "This creates a local BROWSOR account on this device. No email, password, or online service is needed.")
        self.purpose = combo(PURPOSES, prefs.purpose)
        field(layout, "What will you mainly use BROWSOR for?", self.purpose)
        self.intention = QLineEdit(prefs.text("profile/intention"))
        self.intention.setMaxLength(100)
        self.intention.setPlaceholderText("For example: learn something new today.")
        field(layout, "Your start page message · optional", self.intention,
              "You can return to this account setup at any time with Ctrl+,")
        layout.addStretch()
        self.stack.addWidget(profile)

        workspace, layout = self.page()
        self.search = combo(SEARCH_ENGINES, prefs.search_engine)
        field(layout, "Where do you like to search?", self.search, "Used in the address bar and on your start page.")
        self.ai = combo(AI_PROVIDERS, prefs.ai_provider)
        field(layout, "Which AI assistant do you prefer?", self.ai, "Opens in the side panel. Sign in on the service's website.")
        self.open_ai = QCheckBox("Open my AI assistant when BROWSOR starts")
        self.open_ai.setChecked(prefs.flag("preferences/open_ai"))
        layout.addWidget(self.open_ai)
        self.compact = QCheckBox("Use a more compact start page")
        self.compact.setChecked(prefs.flag("appearance/compact"))
        layout.addWidget(self.compact)
        self.restore_tabs = QCheckBox("Continue with my tabs the next time I open BROWSOR")
        self.restore_tabs.setChecked(prefs.flag("preferences/restore_tabs"))
        layout.addWidget(self.restore_tabs)
        layout.addWidget(label("Saves up to 20 tab addresses locally when you close the app. Off by default.", "help", True))
        layout.addStretch()
        self.stack.addWidget(workspace)

        appearance, layout = self.page()
        saved_accent = prefs.text("appearance/accent", "Lavender")
        self.accent = combo(ACCENTS, LEGACY_ACCENTS.get(saved_accent, saved_accent))
        for index, color in enumerate(ACCENTS.values()):
            self.accent.setItemIcon(index, icon("logo", color))
        field(layout, "Choose an accent color", self.accent)
        self.tracking = QCheckBox("Block known trackers from other websites")
        self.tracking.setChecked(prefs.flag("privacy/tracking", True))
        layout.addWidget(self.tracking)
        layout.addWidget(label("A basic filter for a limited list of tracking domains. Websites can still see your IP address.", "help", True))
        layout.addSpacing(6)
        self.remember = QCheckBox("Stay signed in to websites")
        self.remember.setChecked(prefs.flag("privacy/remember_signins"))
        layout.addWidget(self.remember)
        layout.addWidget(label("On: website cookies are saved on this computer. Off: cookies are removed when you close BROWSOR. Changes take effect the next time you start the app.", "help", True))
        layout.addSpacing(12)
        note = QFrame()
        note.setObjectName("card")
        note_layout = QVBoxLayout(note)
        note_layout.setContentsMargins(16, 13, 16, 13)
        note_layout.addWidget(label("Your local account stays under your control.", "fieldLabel"))
        note_layout.addWidget(label("Your account name, favorites, and every preference are stored on this device. Change them here whenever you want.", "help", True))
        layout.addWidget(note)
        layout.addStretch()
        self.stack.addWidget(appearance)

        footer = QHBoxLayout()
        self.back = QPushButton("Back" if first_run else "Cancel")
        self.back.setObjectName("secondary")
        self.back.clicked.connect(self.previous_or_cancel)
        footer.addWidget(self.back)
        footer.addStretch()
        self.next = QPushButton()
        self.next.setObjectName("primary")
        self.next.setDefault(True)
        self.next.clicked.connect(self.next_or_save)
        footer.addWidget(self.next)
        root.addLayout(footer)
        self.select_step(0)

    @staticmethod
    def page():
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 12, 0, 4)
        layout.setSpacing(7)
        return widget, layout

    def select_step(self, index):
        self.stack.setCurrentIndex(index)
        self.title.setText(("Create your local account.", "Make browsing yours.", "Choose what stays private.")[index])
        self.description.setText((
            "Your account lives only on this device. Choose a name and how you want BROWSOR to greet you.",
            "Change search, AI, start-page density, and session behaviour whenever you want.",
            "Choose an accent, tracker protection, and whether websites can keep you signed in.",
        )[index])
        self.step_label.setText(f"{index + 1} / 3" if self.first_run else "Local account")
        for i, button in enumerate(self.sections):
            button.setChecked(i == index)
        self.back.setEnabled(not self.first_run or index > 0)
        self.next.setText("Create local account" if self.first_run and index == 2 else "Continue" if self.first_run else "Save all changes")

    def previous_or_cancel(self):
        if self.first_run:
            self.select_step(max(0, self.stack.currentIndex() - 1))
        else:
            self.reject()

    def next_or_save(self):
        if self.first_run and self.stack.currentIndex() < 2:
            self.select_step(self.stack.currentIndex() + 1)
            return
        values = {
            "profile/name": self.name_input.text().strip(),
            "profile/purpose": self.purpose.currentText(),
            "profile/intention": self.intention.text().strip(),
            "preferences/search_engine": self.search.currentText(),
            "preferences/ai_provider": self.ai.currentText(),
            "preferences/open_ai": self.open_ai.isChecked(),
            "preferences/restore_tabs": self.restore_tabs.isChecked(),
            "appearance/accent": self.accent.currentText(),
            "appearance/compact": self.compact.isChecked(),
            "privacy/tracking": self.tracking.isChecked(),
            "privacy/remember_signins": self.remember.isChecked(),
            "profile/type": "local",
            "onboarding/welcome_shown": True,
        }
        for key, value in values.items():
            self.prefs.settings.setValue(key, value)
        if not self.restore_tabs.isChecked():
            self.prefs.settings.remove("session")
        self.prefs.settings.sync()
        if self.prefs.settings.status() != QSettings.Status.NoError:
            QMessageBox.warning(self, "Couldn't save preferences", "Your preferences could not be saved. Check that BROWSOR can write to your user folder.")
            return
        self.accept()


class BookmarkDialog(QDialog):
    def __init__(self, parent=None, title="", url=""):
        super().__init__(parent)
        self.setWindowTitle("Save favorite")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 25, 28, 25)
        layout.setSpacing(10)
        layout.addWidget(label("Keep it close.", "dialogTitle"))
        layout.addWidget(label("Save a place you would like to visit again.", "muted"))
        layout.addSpacing(8)
        self.title_input = QLineEdit(title)
        self.title_input.setMaxLength(60)
        self.title_input.setPlaceholderText("Website name")
        self.url_input = QLineEdit(url)
        self.url_input.setPlaceholderText("https://example.com")
        field(layout, "Name", self.title_input)
        field(layout, "Web address", self.url_input)
        self.error = label("", "error", True)
        layout.addWidget(self.error)
        row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setObjectName("primary")
        save.setDefault(True)
        save.clicked.connect(self.save)
        row.addWidget(cancel)
        row.addStretch()
        row.addWidget(save)
        layout.addLayout(row)
        self.result_item = None

    def save(self):
        url = web_url(self.url_input.text())
        if url is None:
            self.error.setText("Enter a valid HTTP or HTTPS web address.")
            self.url_input.setFocus()
            return
        self.result_item = {"title": self.title_input.text().strip() or url.host(), "url": url.toString()}
        self.accept()


class BookmarksDialog(QDialog):
    changed = Signal()
    open_requested = Signal(str)

    def __init__(self, prefs: Preferences, parent=None):
        super().__init__(parent)
        self.prefs = prefs
        self.setWindowTitle("Your favorites")
        self.resize(650, 620)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 26, 28, 24)
        root.setSpacing(12)
        root.addWidget(label("Your favorite places.", "dialogTitle"))
        root.addWidget(label("The first five appear on your start page. Double-click to open one.", "help", True))
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _: self.open_selected())
        self.list.currentRowChanged.connect(self.update_buttons)
        root.addWidget(self.list, 1)
        row = QHBoxLayout()
        self.actions = []
        for title, callback in (("Add", self.add), ("Edit", self.edit), ("Remove", self.remove), ("Move up", self.move_up)):
            button = QPushButton(title)
            button.clicked.connect(callback)
            row.addWidget(button)
            self.actions.append(button)
        root.addLayout(row)
        transfer = QHBoxLayout()
        for title, callback in (("Import favorites…", self.import_bookmarks), ("Export favorites…", self.export_bookmarks)):
            button = QPushButton(title)
            button.setObjectName("secondary")
            button.clicked.connect(callback)
            transfer.addWidget(button)
        transfer.addStretch()
        root.addLayout(transfer)
        self.transfer_status = label("Up to 100 favorites. HTML files work with other browsers.", "help", True)
        root.addWidget(self.transfer_status)
        close = QPushButton("Done")
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        root.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self.refresh()

    def refresh(self, selected=0):
        self.list.clear()
        for item in self.prefs.bookmarks:
            entry = QListWidgetItem(f'{item["title"]}\n{item["url"]}')
            entry.setIcon(icon("star", self.prefs.accent))
            self.list.addItem(entry)
        self.list.setCurrentRow(min(selected, self.list.count() - 1))
        self.update_buttons()

    def update_buttons(self, *_):
        row = self.list.currentRow()
        for action in self.actions[1:]:
            action.setEnabled(row >= 0)
        self.actions[-1].setEnabled(row > 0)
        self.actions[0].setEnabled(self.list.count() < 100)

    def commit(self, items, selected=0):
        self.prefs.save_bookmarks(items)
        self.refresh(selected)
        self.changed.emit()

    def add(self):
        dialog = BookmarkDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            items = self.prefs.bookmarks
            items.append(dialog.result_item)
            self.commit(items, len(items) - 1)
        dialog.deleteLater()

    def edit(self):
        row = self.list.currentRow()
        if row < 0:
            return
        items = self.prefs.bookmarks
        dialog = BookmarkDialog(self, **items[row])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            items[row] = dialog.result_item
            self.commit(items, row)
        dialog.deleteLater()

    def remove(self):
        row = self.list.currentRow()
        if row >= 0:
            items = self.prefs.bookmarks
            items.pop(row)
            self.commit(items, row)

    def move_up(self):
        row = self.list.currentRow()
        if row > 0:
            items = self.prefs.bookmarks
            items[row - 1], items[row] = items[row], items[row - 1]
            self.commit(items, row - 1)

    def open_selected(self):
        row = self.list.currentRow()
        if row >= 0:
            self.open_requested.emit(self.prefs.bookmarks[row]["url"])
            self.accept()

    def import_bookmarks(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Import favorites", "", "Bookmark files (*.html *.htm *.json)")
        if not filename:
            return
        try:
            with Path(filename).open("rb") as source:
                content = source.read(MAX_IMPORT_BYTES + 1)
            incoming = read_bookmarks(content, Path(filename).suffix.lower() in (".html", ".htm"))
            items, added, skipped = merge_bookmarks(self.prefs.bookmarks, incoming)
            self.commit(items)
            self.transfer_status.setText(f"Imported {added} favorites. Skipped {skipped} duplicates, unsupported entries, or entries above the 100-favorite limit.")
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Couldn't import favorites", str(error))

    def export_bookmarks(self):
        filename, selected = QFileDialog.getSaveFileName(self, "Export favorites", "BROWSOR-favorites.html", "Browser bookmarks (*.html);;BROWSOR bookmarks (*.json)")
        if not filename:
            return
        if not Path(filename).suffix:
            filename += ".json" if "json" in selected else ".html"
        data = write_bookmarks(self.prefs.bookmarks, Path(filename).suffix.lower() != ".json")
        output = QSaveFile(filename)
        if not output.open(QIODevice.OpenModeFlag.WriteOnly):
            QMessageBox.warning(self, "Couldn't export favorites", output.errorString())
            return
        if output.write(data) != len(data):
            output.cancelWriting()
            QMessageBox.warning(self, "Couldn't export favorites", output.errorString())
            return
        if not output.commit():
            QMessageBox.warning(self, "Couldn't export favorites", output.errorString())
            return
        self.transfer_status.setText(f"Exported {len(self.prefs.bookmarks)} favorites to {Path(filename).name}.")


class CommandDialog(QDialog):
    """Keyboard-first access to existing tabs, favorites and browser actions."""

    def __init__(self, entries, navigate, parent=None):
        super().__init__(parent)
        self.entries, self.navigate = entries, navigate
        self.result_callback = None
        self.setWindowTitle("Go anywhere · BROWSOR")
        self.resize(640, 500)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(14)
        root.addWidget(label("A shortcut to everything.", "dialogTitle"))
        self.query = QLineEdit()
        self.query.setPlaceholderText("Find a tab, favorite, action, or search the web…")
        self.query.setAccessibleName("Search tabs, favorites and actions")
        self.query.setClearButtonEnabled(True)
        root.addWidget(self.query)
        self.results = QListWidget()
        self.results.setAccessibleName("Matching destinations and actions")
        self.results.itemActivated.connect(lambda _: self.choose())
        root.addWidget(self.results, 1)
        root.addWidget(label("↑ ↓ to move     Enter to open     Esc to close  ·  Suggestions stay on this computer", "help", True))
        self.query.textChanged.connect(self.refresh)
        self.query.returnPressed.connect(self.choose)
        for key, direction in (("Down", 1), ("Up", -1)):
            shortcut = QShortcut(QKeySequence(key), self.query)
            shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
            shortcut.activated.connect(lambda d=direction: self.results.setCurrentRow((self.results.currentRow() + d) % max(1, self.results.count())))
        self.refresh()
        self.query.setFocus()

    def refresh(self):
        self.results.clear()
        self.callbacks = []
        query = self.query.text().strip()
        words = query.casefold().split()
        matches = [entry for entry in self.entries if all(word in (entry[0] + " " + entry[1]).casefold() for word in words)]
        if query:
            matches.append((f"Open or search: {query}", "Web · your selected search engine", "search", lambda: self.navigate(query)))
        for title, detail, glyph, callback in matches[:60]:
            item = QListWidgetItem(icon(glyph), f"{title}\n{detail}")
            self.results.addItem(item)
            self.callbacks.append(callback)
        self.results.setCurrentRow(0)

    def choose(self):
        row = self.results.currentRow()
        if 0 <= row < len(self.callbacks):
            self.result_callback = self.callbacks[row]
            self.accept()
