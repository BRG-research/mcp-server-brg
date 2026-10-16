"""Equations in the terminal.  TeX between $...$ becomes Unicode mathematics (bold vectors, sub- and
superscripts, Greek, operators), which every terminal can show; display equations ($$...$$ or \\[...\\])
are set on their own line as a quoted block."""

from __future__ import annotations

import re

import unicodeit

_REPLACEMENTS = [
    (r"\\left\s*", ""), (r"\\right\s*", ""), (r"\\,|\;|\\:|\\!|\\quad|\\qquad|~", " "),
    (r"\\(?:text|mathrm|mathsf|mathit|mathcal|mathbb|operatorname|textrm|boldsymbol|bm|vec|hat|bar|tilde)\{([^{}]*)\}", r"\1"),
    (r"\\(?:mathsf|mathrm|mathit|mathcal|mathbb)\s+([A-Za-z])", r"\1"),
    (r"\\(?:top|intercal)", "T"), (r"\\(?:ldots|cdots|dots)", "…"), (r"\\infty", "∞"), (r"\\partial", "∂"), (r"\\nabla", "∇"),
    (r"\^\\circ", "°"), (r"\\degree", "°"), (r"\\cdot", "·"), (r"\\times", "×"),
    (r"\\mathbf\{([A-Za-z])\}", r"\\mathbf{\1}"),
]
_FRAC = re.compile(r"\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}")


def _frac(m: re.Match) -> str:
    a, b = m.group(1).strip(), m.group(2).strip()
    wrap = lambda s: s if re.fullmatch(r"[\w\\^]+(\{[^{}]*\})?", s) else f"({s})"   # noqa: E731
    return f"{wrap(a)}/{wrap(b)}"


def tex_to_unicode(tex: str) -> str:
    """One TeX math expression → Unicode text."""
    s = tex.strip()
    for _ in range(3):                      # nested fractions, inside out
        s2 = _FRAC.sub(_frac, s)
        if s2 == s:
            break
        s = s2
    for pattern, repl in _REPLACEMENTS:
        s = re.sub(pattern, repl, s)
    s = unicodeit.replace(s)
    s = s.replace("\\", "").replace("{", "").replace("}", "")
    return re.sub(r"[ ]{2,}", " ", s).strip()


_DISPLAY = re.compile(r"(?<!\\)\$\$(.+?)\$\$|\\\[(.+?)\\\]", re.S)
_INLINE = re.compile(r"(?<![\\$\w])\$(?!\s)((?:[^$\n]|\\\$)+?)(?<!\s)\$(?!\w)")
_FENCE = re.compile(r"(```.*?```|`[^`\n]*`)", re.S)


def mathify(markdown: str) -> str:
    """Replace the TeX in a Markdown text by Unicode mathematics, leaving code spans and fences alone.
    Only complete $...$ pairs are touched, so a text still streaming is safe to pass."""
    parts = _FENCE.split(markdown)
    for i in range(0, len(parts), 2):
        text = parts[i]
        text = _DISPLAY.sub(lambda m: "\n\n> " + tex_to_unicode(m.group(1) or m.group(2)) + "\n\n", text)
        text = _INLINE.sub(lambda m: tex_to_unicode(m.group(1)), text)
        parts[i] = text
    return "".join(parts)
