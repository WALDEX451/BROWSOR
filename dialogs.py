"""Editable local profile, first-run setup and real bookmark management."""

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from appdata import ACCENTS, AI_PROVIDERS, LEGACY_ACCENTS, PURPOSES, SEARCH_ENGINES, Preferences, web_url
from theme import icon


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
        self.setWindowTitle("Welcome to BROWSOR" if first_run else "Your BROWSOR · Settings")
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
        for index, name in enumerate(("01  You", "02  Your space", "03  Preferences")):
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
        field(layout, "Your first name or nickname", self.name_input, "A local profile. No account required.")
        self.purpose = combo(PURPOSES, prefs.purpose)
        field(layout, "What will you mainly use BROWSOR for?", self.purpose)
        self.intention = QLineEdit(prefs.text("profile/intention"))
        self.intention.setMaxLength(100)
        self.intention.setPlaceholderText("For example: learn something new today.")
        field(layout, "Your start page message · optional", self.intention)
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
        note_layout.addWidget(label("Set it up once. Make BROWSOR yours.", "fieldLabel"))
        note_layout.addWidget(label("Your profile, favorites, and preferences are stored locally. You can change them here at any time.", "help", True))
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
        self.title.setText(("A great start begins with you.", "Everything in its place.", "The finishing touches.")[index])
        self.description.setText((
            "Tell us a little about yourself. Every field is optional.",
            "Choose how you search, think, and start your day.",
            "Add some color and choose what BROWSOR remembers.",
        )[index])
        self.step_label.setText(f"{index + 1} / 3" if self.first_run else "Local profile")
        for i, button in enumerate(self.sections):
            button.setChecked(i == index)
            button.setStyleSheet(f"background: {'#3a314c' if i == index else '#1c1d26'}; color: {'#e7dcfc' if i == index else '#9491a5'};")
        self.back.setEnabled(not self.first_run or index > 0)
        self.next.setText("Start BROWSOR" if self.first_run and index == 2 else "Continue" if self.first_run else "Save preferences")

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
            "appearance/accent": self.accent.currentText(),
            "appearance/compact": self.compact.isChecked(),
            "privacy/tracking": self.tracking.isChecked(),
            "privacy/remember_signins": self.remember.isChecked(),
            "onboarding/welcome_shown": True,
        }
        for key, value in values.items():
            self.prefs.settings.setValue(key, value)
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
        self.resize(600, 560)
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
