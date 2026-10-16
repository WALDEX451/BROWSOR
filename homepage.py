"""The trusted, entirely local start page. No remote assets or tracking."""

from datetime import datetime
from html import escape
from pathlib import Path
import re

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtWebEngineCore import QWebEngineUrlRequestJob, QWebEngineUrlScheme, QWebEngineUrlSchemeHandler

from appdata import Preferences, SEARCH_ENGINES
from theme import svg
from version import DISPLAY_VERSION

TEMPLATE = (Path(__file__).parent / "assets" / "start.html").read_text(encoding="utf-8")


def register_scheme() -> None:
    scheme = QWebEngineUrlScheme(b"browsor")
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.HostAndPort)
    scheme.setDefaultPort(443)
    scheme.setFlags(QWebEngineUrlScheme.Flag.SecureScheme | QWebEngineUrlScheme.Flag.LocalScheme)
    QWebEngineUrlScheme.registerScheme(scheme)


def render_home(prefs: Preferences, persistent: bool) -> str:
    now = datetime.now()
    salutation = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 18 else "Good evening"
    greeting = f"{salutation}, {prefs.name}." if prefs.name else f"{salutation}. Welcome home."
    days = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    months = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
    colors = [("#e6e4d7", "#595a50"), ("#f3ddd4", "#a45742"), ("#dde4d4", "#526445"), ("#e7e4de", "#57574d"), ("#e8e0ed", "#776183")]
    favorites = []
    # Keep the landing page calm; the manager exposes the complete list.
    for index, item in enumerate(prefs.bookmarks[:5]):
        background, color = colors[index % len(colors)]
        title = escape(item["title"] or "Favorite")
        letter = escape((item["title"] or "F")[0].upper())
        favorites.append(f'<a class="favorite" href="{escape(item["url"], quote=True)}" title="{title}"><span class="favicon" style="--tile-bg:{background};--tile-text:{color}">{letter}</span><span class="favorite-name">{title}</span></a>')
    purpose = prefs.purpose
    taglines = {
        "Work": "Room to focus, think creatively, and build what matters to you.",
        "Study": "Turn a small question into a new insight. Start here.",
        "Explore": "A calm beginning. The whole internet within reach.",
    }
    replacements = {
        "ACCENT": prefs.accent,
        "VERSION": DISPLAY_VERSION,
        "DENSITY": "compact" if prefs.flag("appearance/compact") else "comfortable",
        "DATE": f"{days[now.weekday()]} {now.day} {months[now.month - 1]}",
        "GREETING": greeting,
        "TAGLINE": prefs.text("profile/intention").strip()[:100] or taglines.get(purpose, taglines["Explore"]),
        "SEARCH_ACTION": SEARCH_ENGINES[prefs.search_engine][1],
        "SEARCH_ENGINE": prefs.search_engine,
        "AI_PROVIDER": prefs.ai_provider,
        "PURPOSE": purpose,
        "FILTER_STATE": "Tracker filter on" if prefs.flag("privacy/tracking", True) else "Tracker filter off",
        "SESSION_LABEL": "Website sign-ins are saved" if persistent else "Temporary cookies · cleared on exit",
    }
    tokens = {key: escape(value, quote=True) for key, value in replacements.items()}
    tokens["FAVORITES"] = "".join(favorites)
    for key, name, size in (
        ("HERO_ICON", "spark", 36), ("SEARCH_ICON", "search", 21), ("ARROW_ICON", "forward", 20),
        ("SMALL_ARROW", "forward", 15), ("TINY_ARROW", "forward", 12), ("PLUS_ICON", "plus", 23),
        ("SPARK_ICON", "spark", 16), ("SLIDERS_ICON", "sliders", 16), ("SHIELD_ICON", "shield", 13),
        ("DOWNLOAD_ICON", "download", 16),
        ("BOOK_ICON", "book", 16),
    ):
        tokens[key] = svg(name, size=size)
    # Single pass prevents a user-entered token from being interpreted as markup.
    return re.sub(r"__([A-Z_]+)__", lambda match: tokens.get(match[1], ""), TEMPLATE)


class HomeSchemeHandler(QWebEngineUrlSchemeHandler):
    def __init__(self, prefs: Preferences, persistent: bool, parent=None):
        super().__init__(parent)
        self.prefs, self.persistent = prefs, persistent

    def requestStarted(self, job):
        if job.requestUrl().host() != "home" or job.requestMethod() != b"GET":
            job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
            return
        buffer = QBuffer(job)
        buffer.setData(render_home(self.prefs, self.persistent).encode("utf-8"))
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        # Keep the Python wrapper alive for the asynchronous request as well.
        job._response_buffer = buffer
        job.reply(b"text/html", buffer)
