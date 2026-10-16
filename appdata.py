"""Local preferences and destinations. No credentials or cloud account data."""

import json
import re
from urllib.parse import quote_plus, urlsplit

from PySide6.QtCore import QSettings, QUrl

APP_NAME = "BROWSOR"
HOME_URL = QUrl("browsor://home/")
SEARCH_ENGINES = {
    "DuckDuckGo": ("https://duckduckgo.com/?q={}", "https://duckduckgo.com/"),
    "Google": ("https://www.google.com/search?q={}", "https://www.google.com/search"),
    "Bing": ("https://www.bing.com/search?q={}", "https://www.bing.com/search"),
}
AI_PROVIDERS = {
    "Google Gemini": "https://gemini.google.com/app",
    "ChatGPT": "https://chatgpt.com/",
    "Claude": "https://claude.ai/new",
    "Microsoft Copilot": "https://copilot.microsoft.com/",
    "Perplexity": "https://www.perplexity.ai/",
}
ACCENTS = {"Lavender": "#c4b5fd", "Mint": "#99e2c5", "Blue": "#a7c9ff"}
LEGACY_ACCENTS = {"Lavendel": "Lavender", "Blauw": "Blue"}
PURPOSES = ("Explore", "Work", "Study")
LEGACY_PURPOSES = {"Ontdekken": "Explore", "Werk": "Work", "Studie": "Study"}
DEFAULT_BOOKMARKS = [
    {"title": "Wikipedia", "url": "https://www.wikipedia.org/"},
    {"title": "YouTube", "url": "https://www.youtube.com/"},
    {"title": "GitHub", "url": "https://github.com/"},
    {"title": "Notion", "url": "https://www.notion.so/"},
    {"title": "Figma", "url": "https://www.figma.com/"},
]


def web_url(value: str) -> QUrl | None:
    """Validate a web address without ever accepting executable/local schemes."""
    value = value.strip()
    if not value or any(character.isspace() for character in value):
        return None
    if "://" not in value:
        value = "https://" + value
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        if parsed.port is not None and not 0 < parsed.port <= 65535:
            return None
        url = QUrl(value, QUrl.ParsingMode.StrictMode)
        return url if url.isValid() and url.host() else None
    except ValueError:
        return None


def resolve_destination(value: str, search_url: str = SEARCH_ENGINES["DuckDuckGo"][0]) -> QUrl | None:
    value = value.strip()
    if not value:
        return None
    if value == HOME_URL.toString():
        return QUrl(HOME_URL)
    # A supplied scheme is always validated; unknown schemes never reach Chromium.
    if "://" in value or re.match(r"^(javascript|data|file|vbscript|about):", value, re.I):
        return web_url(value) if "://" in value else None
    host = value.split("/", 1)[0]
    if not any(c.isspace() for c in value) and ("." in host or ":" in host or host == "localhost"):
        return web_url(value)
    return QUrl(search_url.format(quote_plus(value)))


class Preferences:
    def __init__(self, settings: QSettings | None = None):
        self.settings = settings if settings is not None else QSettings(APP_NAME, APP_NAME)

    def text(self, key: str, default: str = "") -> str:
        return str(self.settings.value(key, default))

    def flag(self, key: str, default: bool = False) -> bool:
        return self.settings.value(key, default, type=bool)

    @property
    def name(self) -> str:
        return self.text("profile/name").strip()[:40]

    @property
    def search_engine(self) -> str:
        value = self.text("preferences/search_engine", "DuckDuckGo")
        return value if value in SEARCH_ENGINES else "DuckDuckGo"

    @property
    def ai_provider(self) -> str:
        value = self.text("preferences/ai_provider", "Google Gemini")
        return value if value in AI_PROVIDERS else "Google Gemini"

    @property
    def accent(self) -> str:
        value = self.text("appearance/accent", "Blue")
        value = LEGACY_ACCENTS.get(value, value)
        return ACCENTS.get(value, ACCENTS["Lavender"])

    @property
    def purpose(self) -> str:
        value = self.text("profile/purpose", "Explore")
        value = LEGACY_PURPOSES.get(value, value)
        return value if value in PURPOSES else "Explore"

    @property
    def bookmarks(self) -> list[dict[str, str]]:
        try:
            items = json.loads(self.text("bookmarks/items", json.dumps(DEFAULT_BOOKMARKS)))
            if not isinstance(items, list):
                raise ValueError
            return [
                {"title": item["title"][:60], "url": web_url(item["url"]).toString()}
                for item in items[:100]
                if isinstance(item, dict) and isinstance(item.get("title"), str)
                and isinstance(item.get("url"), str) and web_url(item["url"]) is not None
            ]
        except (TypeError, ValueError):
            return [dict(item) for item in DEFAULT_BOOKMARKS]

    def save_bookmarks(self, items: list[dict[str, str]]) -> None:
        self.settings.setValue("bookmarks/items", json.dumps(items, ensure_ascii=False))
        self.settings.sync()

    def saved_session(self) -> tuple[list[str], int]:
        if not self.flag("preferences/restore_tabs"):
            return [], 0
        try:
            data = json.loads(self.text("session/tabs", "{}"))
            urls = data.get("urls", [])
            if not isinstance(urls, list):
                return [], 0
            safe = [value for value in urls[:20] if isinstance(value, str)
                    and (value == HOME_URL.toString() or web_url(value) is not None)]
            active = data.get("active", 0)
            active = active if isinstance(active, int) else 0
            return safe, max(0, min(active, len(safe) - 1))
        except (ValueError, AttributeError, TypeError):
            return [], 0

    def save_session(self, urls: list[str], active: int) -> None:
        if self.flag("preferences/restore_tabs"):
            safe = [url for url in urls[:20] if url == HOME_URL.toString() or web_url(url) is not None]
            self.settings.setValue("session/tabs", json.dumps({"urls": safe, "active": active}))
        else:
            self.settings.remove("session")
        self.settings.sync()
