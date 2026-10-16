"""Markdown as the BRG terminal shows it: left-aligned headings without underline, code blocks and inline
code on the terminal's own background (no grey box), quotes dim, and display equations as a bar + line."""

from __future__ import annotations

from rich.console import Console, ConsoleOptions, Group, RenderResult
from rich.markdown import CodeBlock, Heading, Markdown
from rich.syntax import Syntax
from rich.text import Text
from rich.theme import Theme

from brg_mcp.cli.mathtext import blocks, mathify

THEME = Theme({
    "markdown.h1": "bold #e6edf3",
    "markdown.h2": "bold #58a6ff",
    "markdown.h3": "bold #79c0ff",
    "markdown.h4": "bold #c9d1d9",
    "markdown.h5": "bold #c9d1d9",
    "markdown.h6": "#c9d1d9",
    "markdown.code": "#79c0ff",                      # inline code and inline math: colour only, no background
    "markdown.code_block": "#c9d1d9",
    "markdown.block_quote": "#8b949e italic",
    "markdown.item.bullet": "bold #58a6ff",
    "markdown.item.number": "#58a6ff",
    "markdown.link": "#58a6ff",
    "markdown.link_url": "underline #58a6ff",
    "markdown.table.border": "#30363d",
    "markdown.table.header": "bold #c9d1d9",
    "markdown.hr": "#30363d",
})


class PlainCodeBlock(CodeBlock):
    """A fenced block with syntax colours on the terminal background: no box, no grey panel."""

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        code = str(self.text).rstrip()
        yield Syntax(code, self.lexer_name, theme="github-dark", background_color="default",
                     word_wrap=True, padding=(0, 0, 0, 2))


class PlainHeading(Heading):
    """Headings left-aligned, bold, no underline, no panel."""

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        text = self.text
        text.justify = "left"
        yield text


class BRGMarkdown(Markdown):
    elements = {**Markdown.elements, "fence": PlainCodeBlock, "code_block": PlainCodeBlock, "heading_open": PlainHeading}


def equation(plain: str) -> Text:
    return Text.assemble(("▌ ", "#58a6ff"), (plain, "bold #e6edf3"))


def reply(text: str) -> Group:
    """A reply (or any Markdown) as renderables: Markdown pieces and display equations."""
    parts: list = []
    pieces = blocks(text)
    for i, (kind, piece) in enumerate(pieces):
        if kind == "eq":
            if parts:
                parts.append(Text(""))
            parts.append(equation(piece))
            if i < len(pieces) - 1:
                parts.append(Text(""))
        else:
            parts.append(BRGMarkdown(mathify(piece)))
    return Group(*parts)
