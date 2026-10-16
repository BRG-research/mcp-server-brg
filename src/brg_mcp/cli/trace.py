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
from urllib.parse import quote, urlencode

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

    def arguments(self) -> dict:
        try:
            data = json.loads(self.args) if self.args else {}
        except json.JSONDecodeError:
            return {"input": self.args}
        return data if isinstance(data, dict) else {"input": data}

    def hover(self) -> str:
        """The badge's link target: what the step queried, shown by terminals that display link targets."""
        if self.kind == "thinking":
            return "brg://thinking"
        query = urlencode({k: str(v)[:120] for k, v in self.arguments().items()})
        return f"brg://{quote(self.name)}" + (f"?{query}" if query else "")

    def label(self) -> str:
        """The short text after the badge: the tool and its main argument, so the chain reads without hovering."""
        if self.kind == "thinking":
            return "thinking"
        args = self.arguments()
        main = next((args[k] for k in ("query", "uri", "id", "note_id", "path", "section", "section_id", "book", "title", "domain")
                     if isinstance(args.get(k), str) and args[k].strip()), None)
        if main is None:
            main = next((v for v in args.values() if isinstance(v, str) and v.strip()), None)
        if main is None:
            main = next((str(v) for v in args.values() if v not in (None, "", [], {})), "")
        main = " ".join(main.split())
        if len(main) > 36:
            main = main[:35] + "…"
        return f'{self.name} "{main}"' if main else self.name

    def badge(self) -> Text:
        link = f" link {self.hover()}"
        return Text.assemble((f" {self.glyph()} ", f"bold {self.colour()} on {TILE}{link}"),
                             (" " + self.label(), f"{GREY}{link}"))


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

    def chain_text(self, width: int = 10_000) -> Text:
        """The chain as lines no wider than `width`, broken only between steps (a badge and its label
        stay together); a line that continues ends with the chevron."""
        out = Text()
        col = 0
        for i, step in enumerate(self.chain):
            badge = step.badge()
            need = badge.cell_len + (3 if i else 0)
            if i and col + need > width:
                out.append(" ›\n", style=GREY)
                col = 0
            elif i:
                out.append(" › ", style=GREY)
                col += 3
            out.append_text(badge)
            col += badge.cell_len
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
    return Text(" · ".join(parts), style=GREY)


def legend() -> Table:
    """/legend: what every symbol of the terminal means."""
    t = Table(box=None, padding=(0, 2), show_header=False)
    t.add_column("symbol", justify="left", no_wrap=True, min_width=16)
    t.add_column("meaning")

    def tile(glyph: str, colour: str) -> Text:
        return Text.assemble((f" {glyph} ", f"bold {colour} on {TILE}"))     # the tile covers the glyph only

    def heading(text: str) -> None:
        t.add_row("", Text(text, style="bold #c9d1d9"))

    heading("The step chain between the messages")
    t.add_row(tile("◐", BLUE), "the model is thinking (reasoning before it writes or calls a tool)")
    t.add_row(tile("≣", GREEN), 'a read: a knowledge note, a book section or a search, e.g.  ≣ search_knowledge "force density"')
    t.add_row(tile("⚙", GREEN), "any other tool call (in Codex also a shell command)")
    t.add_row(tile("⚙", AMBER), "amber: the step is still running")
    t.add_row(tile("⚙", GREEN), "green: the tool returned")
    t.add_row(tile("✗", RED), "red: the tool failed; /trace shows the error")
    t.add_row(Text("›", style=GREY), "the next step; a chain is as long as the steps taken before the next message")
    t.add_row(Text("label", style=GREY), "after a badge: the tool and its main argument; /trace prints all arguments and results")
    t.add_row("", "")
    heading("The line under a reply")
    t.add_row(Text("in 41k", style=GREY), "tokens the model read this turn (your question, the notes, the tool results, the history)")
    t.add_row(Text("out 310", style=GREY), "tokens the model wrote (the reply and the tool calls)")
    t.add_row(Text("cache 38k", style=GREY), "the part of 'in' that came from the cache (cheaper and faster)")
    t.add_row(Text("4 tools", style=GREY), "number of tool calls in this reply")
    t.add_row(Text("ctx ▰▰▱▱▱▱▱▱ 24%", style=GREY), "share of the model's context window already filled by this conversation; /clear empties it")
    t.add_row(Text("14s", style=GREY), "time from your question to the end of the reply")
    t.add_row("", "")
    heading("Elsewhere")
    t.add_row(Text("●", style=f"bold {GREEN}"), "a message from the terminal itself (model, account, tools)")
    t.add_row(Text("●", style=f"bold {RED}"), "an error")
    t.add_row(Text("▌ 𝐀𝐟 + 𝐩 = 𝟎", style="#c9d1d9"), "a display equation (TeX shown as Unicode mathematics)")
    t.add_row(Text("● Idle", style=GREEN), "bottom bar: the terminal is waiting for you; the model name and the context share follow")
    return t
