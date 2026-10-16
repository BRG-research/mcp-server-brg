"""rich renderables as ANSI lines, for the transcript of the full-screen application."""

from __future__ import annotations

from rich.color import ColorSystem
from rich.console import Console

def ansi_lines(console: Console, renderable, width: int | None = None) -> list[str]:
    """A renderable as ANSI-coloured lines (no trailing newline, no padding)."""
    width = width or console.width
    options = console.options.update_width(width)
    system = console._color_system or ColorSystem.TRUECOLOR
    lines = console.render_lines(renderable, options, pad=False)
    out = []
    for line in lines:
        parts = []
        for seg in line:
            if seg.control:
                continue
            parts.append(seg.style.render(seg.text, color_system=system) if seg.style else seg.text)
        out.append("".join(parts).rstrip() if all(not s.style for s in line) else "".join(parts))
    return out
