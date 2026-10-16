"""Discover public books through LIBRARY.md and fetch selected Markdown only."""

from functools import lru_cache
from pathlib import Path, PurePosixPath
import re
from urllib.parse import quote, urlsplit

import httpx
import yaml


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
        terms = query.casefold().split()
        if not terms:
            return []
        entries = self.sections(book) if book is not None else [
            section for item in self._catalog().values() for section in item["sections"]]
        return [entry for entry in entries if all(
            term in (entry["title"] + " " + entry["summary"]).casefold() for term in terms
        )][:limit]

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
