"""Portable bookmark files. Imported content is data, never executable markup."""

from html import escape
from html.parser import HTMLParser
import json

from appdata import web_url

MAX_BOOKMARKS = 100
MAX_IMPORT_BYTES = 5 * 1024 * 1024


class BookmarkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items, self.href, self.title = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self.href = dict(attrs).get("href")
            self.title = []

    def handle_data(self, data):
        if self.href is not None:
            self.title.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.href is not None:
            self.items.append({"title": "".join(self.title), "url": self.href})
            self.href, self.title = None, []


def read_bookmarks(content: bytes, html: bool = False) -> list:
    if len(content) > MAX_IMPORT_BYTES:
        raise ValueError("Choose a bookmark file smaller than 5 MB.")
    text = content.decode("utf-8-sig")
    if html:
        parser = BookmarkParser()
        parser.feed(text)
        parser.close()
        return parser.items
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("bookmarks")
    if not isinstance(data, list):
        raise ValueError("This file does not contain a bookmark list.")
    return data


def merge_bookmarks(existing: list, incoming: list) -> tuple[list, int, int]:
    result = [dict(item) for item in existing[:MAX_BOOKMARKS]]
    seen = {item["url"] for item in result}
    added = 0
    for item in incoming:
        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
            continue
        url = web_url(item["url"])
        if url is None or url.toString() in seen or len(result) >= MAX_BOOKMARKS:
            continue
        title = item.get("title", "")
        title = title.strip()[:60] if isinstance(title, str) else ""
        result.append({"title": title or url.host(), "url": url.toString()})
        seen.add(url.toString())
        added += 1
    return result, added, len(incoming) - added


def write_bookmarks(items: list, html: bool = False) -> bytes:
    if not html:
        return (json.dumps({"format": "browsor-bookmarks-v1", "bookmarks": items}, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    rows = [f'<DT><A HREF="{escape(item["url"], quote=True)}">{escape(item["title"])}</A>' for item in items]
    document = '<!DOCTYPE NETSCAPE-Bookmark-file-1>\n<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">\n<TITLE>BROWSOR favorites</TITLE>\n<H1>BROWSOR favorites</H1>\n<DL><p>\n' + "\n".join(rows) + '\n</DL><p>\n'
    return document.encode("utf-8")
