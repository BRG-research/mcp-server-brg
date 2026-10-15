"""One bundled guide, available through both tools and MCP resources."""

from importlib.resources import files
from pathlib import Path


def read_guide() -> str:
    return files("brg_mcp").joinpath("book_guidance.md").read_text(encoding="utf-8")


def read_process_workflow() -> str:
    """Use the skill bundled in wheels, or the canonical file in a source checkout."""
    bundled = files("brg_mcp").joinpath("books_process_skill.md")
    if bundled.is_file():
        return bundled.read_text(encoding="utf-8")
    return (Path(__file__).resolve().parents[2] / "skills" / "books-process" / "SKILL.md").read_text(encoding="utf-8")


SERVER_INSTRUCTIONS = (
    "BRG provides course knowledge and a public structural engineering library. "
    "For book questions, call get_book_guide once per session to read the workflow "
    "and current library map, then search and read only relevant chapters. "
    "Read GLOSSARY before comparing notation and GRAPHIC-STATICS-NOTATION.md for "
    "ETH graphic statics questions. Cite author, printed page/slide, section, and URL; "
    "summaries locate evidence but are not evidence. Book tools are read-only. "
    "Read brg://books/guide for the processing workflow; no conversion or hybrid "
    "search is executed by this server."
    " For new scans, use the books_process MCP prompt, or get_book_guide's "
    "processing_workflow if your client does not expose prompts."
)
