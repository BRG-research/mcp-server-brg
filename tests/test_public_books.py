import httpx
import pytest

from brg_mcp.adapters.public_books import PublicBooks

LIBRARY = """# Library map
## `example-book/` — Example book, Author, 1886
1 files
  - `01-chapter.md` **Funicular polygons** (pp. 12–14) — Equilibrium and reciprocal diagrams.
"""


def make_books():
    requests = []

    def handle(request):
        requests.append(request)
        assert "authorization" not in request.headers
        if request.url.path == "/LIBRARY.md":
            return httpx.Response(200, text=LIBRARY)
        if request.url.path == "/example-book/01-chapter.md":
            return httpx.Response(200, text="First line\nSecond line\nThird line\n")
        if request.url.path == "/example-book/src/01-chapter.md":
            return httpx.Response(200, text="Exact source formula: $`EI`$\n")
        if request.url.path == "/example-book/GRAPHIC-STATICS-NOTATION.md":
            return httpx.Response(200, text="Roman numerals label nodes.\n")
        return httpx.Response(404)

    return PublicBooks("https://example.test", transport=httpx.MockTransport(handle)), requests


def test_discover_search_fetch_and_cache():
    books, requests = make_books()
    assert books.list_books()[0]["section_count"] == 1
    matches = books.search("reciprocal equilibrium")
    assert matches[0]["summary"].startswith("(pp. 12–14)")
    assert len(requests) == 1  # Searching uses only the small library map.
    result = books.read("example-book", matches[0]["section"], 2, 1)
    assert result["text"] == "Second line"
    assert result["next_start_line"] == 3
    assert result["url"] == "https://example.test/example-book/01-chapter.md"
    books.read("example-book", "01-chapter.md")
    assert len(requests) == 2


def test_unknown_books_paths_and_limits():
    books, requests = make_books()
    for section in ["../secret.md", "https://other.test/file.md", "missing.md"]:
        with pytest.raises(ValueError):
            books.read("example-book", section)
    with pytest.raises(ValueError, match="Unknown book"):
        books.sections("missing")
    with pytest.raises(ValueError):
        books.search("test", limit=100)
    with pytest.raises(ValueError):
        books.read("example-book", "01-chapter.md", line_count=0)
    assert len(requests) == 1
    assert books.search("  ") == []


def test_library_map_notation_and_source_representation():
    books, requests = make_books()
    assert books.library_map()["text"] == LIBRARY
    notation = books.read("example-book", "GRAPHIC-STATICS-NOTATION.md")
    assert "Roman numerals" in notation["text"]
    source = books.read("example-book", "01-chapter.md", representation="source")
    assert "$`EI`$" in source["text"]
    assert source["url"].endswith("/example-book/src/01-chapter.md")
    assert source["representation"] == "source"
    with pytest.raises(ValueError, match="indexed chapters"):
        books.read("example-book", "GLOSSARY.md", representation="source")
    with pytest.raises(ValueError, match="representation"):
        books.read("example-book", "01-chapter.md", representation="../../")
    assert len(requests) == 3


@pytest.mark.parametrize("status", [301, 401, 404, 429, 500])
def test_storage_errors_are_explicit(status):
    books = PublicBooks("https://example.test", transport=httpx.MockTransport(
        lambda _: httpx.Response(status, headers={"Location": "https://other.test"})
    ))
    with pytest.raises(ValueError, match=f"HTTP {status}"):
        books.list_books()


def test_document_size_limit():
    books = PublicBooks("https://example.test", transport=httpx.MockTransport(
        lambda _: httpx.Response(200, content=b"x" * 2_000_001)
    ))
    with pytest.raises(ValueError, match="2 MB"):
        books.list_books()


def test_library_schema_errors_and_optional_config(tmp_path):
    books = PublicBooks("https://example.test", transport=httpx.MockTransport(
        lambda _: httpx.Response(200, text="unexpected index format")
    ))
    with pytest.raises(ValueError, match="No book sections"):
        books.list_books()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "sources.yaml").write_text("[]\n")
    assert PublicBooks.from_config(tmp_path) is None
