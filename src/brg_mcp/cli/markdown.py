"""Markdown as the BRG terminal shows it: left-aligned headings without underline, code blocks and inline
code on the terminal's own background (no grey box), quotes dim, and display equations as a bar + line."""

from __future__ import annotations

from rich.console import Console, ConsoleOptions, Group, RenderResult
from rich.markdown import CodeBlock, Heading, Markdown
from rich.segment import Segment
from rich.style import Style
from rich.syntax import Syntax
from rich.text import Text
from rich.theme import Theme

CODE_BAR = Style(color="#f778ba")                  # the pink bar beside code, like the blue one beside equations

from brg_mcp.cli.mathbox import typeset
from brg_mcp.cli.mathtext import blocks, mathify, tex_to_plain

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
    """A fenced block with syntax colours on the terminal background, a pink bar at the left: no box, no
    grey panel."""

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        code = str(self.text).rstrip()
        syntax = Syntax(code, self.lexer_name, theme="github-dark", background_color="default", word_wrap=True)
        lines = console.render_lines(syntax, options.update_width(max(10, options.max_width - 2)), pad=False)
        for line in lines:
            yield Segment("▌ ", CODE_BAR)
            yield from line
            yield Segment.line()


class PlainHeading(Heading):
    """Headings left-aligned, bold, no underline, no panel."""

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        text = self.text
        text.justify = "left"
        yield text


class BRGMarkdown(Markdown):
    elements = {**Markdown.elements, "fence": PlainCodeBlock, "code_block": PlainCodeBlock, "heading_open": PlainHeading}


EQUATION_WIDTH = 100


def equation(tex: str) -> Text:
    """A display equation: typeset in two dimensions when it parses and fits, else the one-line notation."""
    lines = typeset(tex)
    if not lines or max(len(l) for l in lines) > EQUATION_WIDTH:
        lines = [tex_to_plain(tex)]
    out = Text()
    for i, line in enumerate(lines):
        if i:
            out.append("\n")
        out.append("▌ ", style="#58a6ff")
        out.append(line, style="bold #e6edf3")
    return out


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
