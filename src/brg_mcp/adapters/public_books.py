"""Discover public books through LIBRARY.md and fetch selected Markdown only."""

from functools import lru_cache
from pathlib import Path, PurePosixPath
import re
from urllib.parse import quote, urlsplit

import unicodedata

import httpx
import yaml


def _words(text: str) -> list[str]:
    """Words, lower case, without accents, so "funiculaire" and "Lévy" match as typed."""
    plain = unicodedata.normalize("NFD", text.casefold())
    return re.findall(r"[a-z0-9]+", "".join(c for c in plain if not unicodedata.combining(c)))


def _has(words: list[str], term: str) -> bool:
    return any(word.startswith(term) for word in words)


_FOUNDERS = re.compile(r"levy|culmann|cremona|maxwell|wolfe|ritter|rankine|varignon|mohr|muller.breslau|henneberg|bow\b")


def _historical(book: dict) -> bool:
    year = re.search(r"\b(1[5-9]\d\d)\b", book["title"])
    return bool(year and int(year.group(1)) < 1950) or bool(_FOUNDERS.search(" ".join(_words(book["id"] + " " + book["title"]))))


class PublicBooks:
    def __init__(self, base_url: str, library_path: str = "LIBRARY.md", transport=None):
        parts = urlsplit(base_url)
        if parts.scheme != "https" or not parts.netloc or parts.query or parts.fragment or parts.username:
            raise ValueError("Public book base_url must be an HTTPS URL without credentials or query")
        self.base_url = base_url.rstrip("/")
        self.library_path = self._safe_path(library_path)
        self.transport = transport

    @classmethod
    def from_config(cls, root: Path):
        path = root / "config" / "sources.yaml"
        sources = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        matches = [source for source in sources if source.get("type") == "public_http"]
        if len(matches) > 1:
            raise ValueError("Only one public book library is supported currently")
        if not matches:
            return None
        source = matches[0]
        return cls(source["base_url"], source.get("library_path", "LIBRARY.md"))

    @staticmethod
    def _safe_path(path: str) -> str:
        if (not path or PurePosixPath(path).is_absolute() or
                any(part in {"", ".", ".."} for part in path.split("/")) or
                any(char in path for char in ("\\", "%", "?", "#", ":"))):
            raise ValueError("Invalid book path")
        return path

    def url(self, path: str) -> str:
        return self.base_url + "/" + quote(self._safe_path(path), safe="/")

    @lru_cache(maxsize=32)
    def _text(self, path: str) -> str:
        # Cache a small number of documents for this process. Never fetch credentials
        # or follow redirects to other hosts. Bound downloaded data, not only output.
        try:
            with httpx.Client(timeout=30, transport=self.transport, follow_redirects=False) as client:
                with client.stream("GET", self.url(path)) as response:
                    if response.status_code != 200:
                        raise ValueError(f"Book storage returned HTTP {response.status_code} for {path}")
                    content = bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content) > 2_000_000:
                            raise ValueError("Book document exceeds the 2 MB text limit")
                    return content.decode("utf-8")
        except (httpx.HTTPError, UnicodeError) as error:
            raise ValueError(f"Could not retrieve book text ({type(error).__name__}); try again later") from None

    def _catalog(self) -> dict:
        books = {}
        current = None
        for line in self._text(self.library_path).splitlines():
            heading = re.match(r"^## `([a-zA-Z0-9_-]+)/` — (.+)$", line)
            if heading:
                current = heading.group(1)
                if current in books:
                    raise ValueError("Duplicate book ID in library map")
                books[current] = {"id": current, "title": heading.group(2), "sections": []}
                continue
            entry = re.match(r"^\s+- `([^`]+\.md)` \*\*(.*?)\*\*(.*)$", line)
            if current and entry:
                filename = self._safe_path(entry.group(1))      # a basename or a relative path inside the book
                books[current]["sections"].append({
                    "book": current, "section": filename, "title": entry.group(2),
                    "summary": entry.group(3).strip(),
                    "url": self.url(f"{current}/{filename}"),
                })
        if not books or not any(book["sections"] for book in books.values()):
            raise ValueError("No book sections found in LIBRARY.md; check the library map format")
        return books

    def library_map(self) -> dict:
        return {"url": self.url(self.library_path), "text": self._text(self.library_path)}

    def list_books(self) -> list[dict]:
        return [{"id": book["id"], "title": book["title"],
                 "section_count": len(book["sections"]),
                 "index_url": self.url(f"{book['id']}/INDEX.md")}
                for book in self._catalog().values()]

    def sections(self, book: str) -> list[dict]:
        books = self._catalog()
        if book not in books:
            raise ValueError(f"Unknown book ID: {book}")
        return books[book]["sections"]

    def search(self, query: str, book: str | None = None, limit: int = 10) -> list[dict]:
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        terms = _words(query)
        if not terms:
            return []
        books = self._catalog()
        if book is not None and book not in books:
            raise ValueError(f"Unknown book ID: {book}")
        hits = []
        for item in books.values() if book is None else [books[book]]:
            old, in_book = _historical(item), _words(item["title"])
            for entry in item["sections"]:
                in_title, in_summary = _words(entry["title"]), _words(entry["summary"])
                # a word in the chapter title counts most, then the summary, then the book's title
                score = sum(3 * _has(in_title, t) + _has(in_summary, t) + _has(in_book, t) for t in terms)
                if score:
                    hits.append((old, score, {**entry, "historical": old}))
        # historical books first (before 1950, or by the founders of graphic statics), as the course reads them
        hits.sort(key=lambda hit: (hit[0], hit[1]), reverse=True)
        return [entry for _, _, entry in hits[:limit]]

    def figure(self, url: str) -> tuple[bytes, str]:
        """An image in the library, as bytes and its format, from a URL or a path relative to the library."""
        if url.startswith("https://"):
            if not url.startswith(self.base_url + "/"):
                raise ValueError("Only images in the library can be shown")
            url = url[len(self.base_url) + 1:]
        extension = PurePosixPath(url).suffix.lower()
        formats = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".gif": "gif", ".webp": "webp"}
        if extension not in formats:
            raise ValueError("A figure is a .png, .jpg, .gif or .webp file")
        try:
            with httpx.Client(timeout=30, transport=self.transport, follow_redirects=False) as client:
                response = client.get(self.url(url))
        except httpx.HTTPError as error:
            raise ValueError(f"Could not retrieve the figure ({type(error).__name__}); try again later") from None
        if response.status_code != 200:
            raise ValueError(f"Book storage returned HTTP {response.status_code} for {url}")
        if len(response.content) > 10_000_000:
            raise ValueError("The figure exceeds the 10 MB limit")
        return response.content, formats[extension]

    def read(self, book: str, section: str, start_line: int = 1, line_count: int = 100,
             representation: str = "published") -> dict:
        if start_line < 1 or not 1 <= line_count <= 200:
            raise ValueError("start_line must be positive and line_count between 1 and 200")
        entries = self.sections(book)
        indexed = any(entry["section"] == section for entry in entries)
        if not indexed and section not in {
            "README.md", "INDEX.md", "GLOSSARY.md", "FIGURES.md", "GRAPHIC-STATICS-NOTATION.md"
        }:
            raise ValueError("Unknown section; use list_book_sections or search_books first")
        if representation not in {"published", "source"}:
            raise ValueError("representation must be published or source")
        if representation == "source" and not indexed:
            raise ValueError("Source representation is available only for indexed chapters")
        path = f"{book}/" + ("src/" if representation == "source" else "") + section
        lines = self._text(path).splitlines()
        selected = "\n".join(lines[start_line - 1:start_line - 1 + line_count])
        # Long Markdown lines can contain paragraphs or embedded data; cap tool output.
        text = selected[:20000]
        return {"book": book, "section": section, "representation": representation, "url": self.url(path),
                "start_line": start_line, "total_lines": len(lines), "text": text,
                "truncated": len(selected) > len(text),
                "next_start_line": start_line + line_count if start_line + line_count <= len(lines) else None}
