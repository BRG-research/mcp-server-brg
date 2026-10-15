"""The step chain of a reply: one badge per step of the agent loop, drawn between the text messages.

Each badge is a glyph on a dark tile, joined by chevrons, as in a pipeline view: ◐ the model is thinking,
≣ a read of a note or a book, ⚙ any other tool, coloured amber while running, green once it returned and
red if it failed.  A terminal cannot show tooltips, so each badge is also an OSC 8 hyperlink whose target
is the tool name and its arguments: GNOME Terminal, VS Code and iTerm2 show it on hover.  /trace prints
the same steps in full for any terminal."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from urllib.parse import quote

from rich.table import Table
from rich.text import Text

from brg_mcp.cli.providers.base import READ_TOOLS, Event

BLUE, AMBER, GREEN, RED, GREY, TILE = "#58a6ff", "#d29922", "#3fb950", "#f85149", "#6e7681", "#21262d"


@dataclass
class Step:
    kind: str                       # "thinking" | "tool"
    name: str = ""
    args: str = ""
    ok: bool | None = None          # None while running
    result: str = ""
    started: float = field(default_factory=time.monotonic)
    ended: float | None = None

    @property
    def seconds(self) -> float:
        return (self.ended or time.monotonic()) - self.started

    def glyph(self) -> str:
        if self.kind == "thinking":
            return "◐"
        if self.ok is False:
            return "✗"
        return "≣" if self.name in READ_TOOLS else "⚙"

    def colour(self) -> str:
        if self.kind == "thinking":
            return BLUE
        return AMBER if self.ok is None else (GREEN if self.ok else RED)

    def hover(self) -> str:
        """The badge's link target: what the step queried, shown by terminals that display link targets."""
        if self.kind == "thinking":
            return "brg://step/thinking"
        tail = self.args[:300]
        return f"brg://step/{quote(self.name)}?{quote(tail)}"

    def badge(self) -> Text:
        return Text(f" {self.glyph()} ", style=f"bold {self.colour()} on {TILE} link {self.hover()}")


class Trace:
    """The steps of one reply, grouped into chains: a new chain starts each time text was printed."""

    def __init__(self) -> None:
        self.steps: list[Step] = []
        self.chain: list[Step] = []          # the steps since the last printed text
        self.usage: dict | None = None

    def add(self, event: Event) -> bool:
        """Record an event; return True when the chain drawing changed."""
        if event.kind == "thinking":
            if self.chain and self.chain[-1].kind == "thinking" and self.chain[-1].ended is None:
                return False
            self._close_thinking()
            step = Step("thinking")
        elif event.kind == "tool_call":
            self._close_thinking()
            step = Step("tool", event.name, event.detail)
        elif event.kind == "tool_args":
            for s in reversed(self.steps):
                if s.kind == "tool" and s.name == event.name and not s.args:
                    s.args = event.detail
                    return False
            step = Step("tool", event.name, event.detail)
        elif event.kind == "tool_result":
            for s in reversed(self.steps):
                if s.kind == "tool" and s.ok is None and (not event.name or s.name == event.name):
                    s.ok, s.result, s.ended = event.ok is not False, event.detail, time.monotonic()
                    return True
            return False
        elif event.kind == "usage":
            self._close_thinking()
            self.usage = event.data
            return False
        else:
            return False
        self.steps.append(step)
        self.chain.append(step)
        return True

    def _close_thinking(self) -> None:
        for s in reversed(self.steps):
            if s.kind == "thinking" and s.ended is None:
                s.ended = time.monotonic()
            break

    def text_started(self) -> None:
        """Text follows: the current chain is finished (it is printed by the terminal)."""
        self._close_thinking()
        self.chain = []

    def chain_text(self) -> Text:
        out = Text()
        for i, step in enumerate(self.chain):
            if i:
                out.append(" › ", style=GREY)
            out.append_text(step.badge())
        return out

    def running(self) -> str:
        """The label for the spinner: what is happening right now."""
        for s in reversed(self.steps):
            if s.kind == "tool" and s.ok is None:
                return f"{s.name}…"
            if s.kind == "thinking" and s.ended is None:
                return "Thinking…"
        return "Working…" if self.steps else "Thinking…"

    def table(self) -> Table:
        """/trace: every step with its arguments, timing and result."""
        t = Table(box=None, padding=(0, 1), show_header=True, header_style=GREY)
        t.add_column("#", justify="right", style=GREY)
        t.add_column("step")
        t.add_column("s", justify="right", style=GREY)
        t.add_column("arguments → result", overflow="fold")
        for i, s in enumerate(self.steps, 1):
            label = Text.assemble((s.glyph() + " ", f"bold {s.colour()}"), (s.name or "thinking", "bold"))
            detail = Text()
            if s.kind == "tool":
                detail.append(_pretty(s.args), style="#c9d1d9")
                if s.result:
                    detail.append("\n→ " + s.result, style=GREY)
                if s.ok is False:
                    detail.append("  (failed)", style=RED)
            t.add_row(str(i), label, f"{s.seconds:.1f}", detail)
        return t


def _pretty(args: str) -> str:
    try:
        data = json.loads(args) if args else {}
    except json.JSONDecodeError:
        return args
    if isinstance(data, dict):
        return ", ".join(f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in data.items()) or "(no arguments)"
    return json.dumps(data, ensure_ascii=False)


def tokens(n: int) -> str:
    return f"{n/1000:.0f}k" if n >= 1000 else str(n)


def metrics_line(usage: dict | None, context_pct: float | None, seconds: float, show_cost: bool = False) -> Text:
    """The dim line under a reply: tokens in/out, cache, tool count, context used, time."""
    parts: list[str] = []
    if usage:
        parts.append(f"in {tokens(usage.get('input', 0) + usage.get('cache_read', 0) + usage.get('cache_write', 0))}")
        parts.append(f"out {tokens(usage.get('output', 0))}")
        if usage.get("cache_read"):
            parts.append(f"cache {tokens(usage['cache_read'])}")
        if usage.get("tools"):
            parts.append(f"{usage['tools']} tool{'s' if usage['tools'] != 1 else ''}")
        if show_cost and usage.get("cost"):
            parts.append(f"${usage['cost']:.3f}")
    if context_pct is not None:
        filled = max(0, min(8, round(context_pct / 12.5)))
        parts.append(f"ctx {'▰' * filled}{'▱' * (8 - filled)} {context_pct:.0f}%")
    parts.append(f"{seconds:.0f}s")
    return Text("  " + " · ".join(parts), style=GREY)
