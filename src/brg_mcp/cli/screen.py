"""The pinned header.  The top rows of the terminal hold the banner (logo, model, effort, mode, context
share) and never scroll: the transcript scrolls in a DECSTBM region below them.  A terminal does not keep
lines that scroll out of such a region, so this module also remembers every printed line and pages back
through them on PageUp/PageDown, which stands in for the terminal's own scrollback."""

from __future__ import annotations

from rich.color import ColorSystem
from rich.console import Console

MAX_LINES = 50_000


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


class PinnedScreen:
    def __init__(self, console: Console, header_rows: int) -> None:
        self.console = console
        self.header_rows = header_rows
        self.buffer: list[str] = []            # everything printed, as ANSI lines
        self.offset = 0                        # lines paged back from the end (0: live view)
        self.header: list[str] = []
        self.active = False

    # ------------------------------------------------------------------ geometry
    @property
    def rows(self) -> int:
        return self.console.size.height

    @property
    def cols(self) -> int:
        return self.console.size.width

    @property
    def view_rows(self) -> int:
        """Transcript rows above the prompt (the input row and the bar under it stay as they are)."""
        return max(1, self.rows - self.header_rows - 2)

    def _write(self, s: str) -> None:
        self.console.file.write(s)
        self.console.file.flush()

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        self.active = True
        self._write("\x1b[2J" + f"\x1b[{self.header_rows + 1};{self.rows}r" + f"\x1b[{self.header_rows + 1};1H")

    def resize(self) -> None:
        """After the window changed size: the region and the header again."""
        if not self.active:
            return
        self._write(f"\x1b[{self.header_rows + 1};{self.rows}r")
        self.draw_header(self.header)
        if self.offset:
            self.redraw_view()

    def stop(self) -> None:
        if not self.active:
            return
        self.active = False
        self._write("\x1b[r" + f"\x1b[{self.rows};1H\n")

    # ------------------------------------------------------------------ header
    def draw_header(self, lines: list[str]) -> None:
        self.header = lines
        if not self.active:
            return
        out = ["\x1b7"]                                        # save cursor
        for i in range(self.header_rows):
            line = lines[i] if i < len(lines) else ""
            out.append(f"\x1b[{i + 1};1H\x1b[2K{line}")
        out.append("\x1b8")                                    # restore cursor
        self._write("".join(out))

    # ------------------------------------------------------------------ transcript memory
    def remember(self, lines: list[str]) -> None:
        self.buffer.extend(lines)
        if len(self.buffer) > MAX_LINES:
            del self.buffer[: len(self.buffer) - MAX_LINES]

    def fill_to_bottom(self) -> None:
        """Blank lines so the prompt sits at the bottom of the region (the transcript grows upward)."""
        printed = len(self.buffer)
        free = self.rows - self.header_rows - printed - 1
        if free > 0:
            self._write("\n" * free)
            self.remember([""] * free)

    # ------------------------------------------------------------------ paging
    def page(self, delta: int) -> None:
        if not self.active:
            return
        top = max(0, len(self.buffer) - self.view_rows)
        self.offset = max(0, min(top, self.offset + delta))
        self.redraw_view()

    def reset_view(self) -> None:
        if self.offset:
            self.offset = 0
            self.redraw_view()

    def redraw_view(self) -> None:
        end = len(self.buffer) - self.offset
        start = max(0, end - self.view_rows)
        shown = self.buffer[start:end]
        out = ["\x1b7"]
        for i in range(self.view_rows):
            line = shown[i] if i < len(shown) else ""
            out.append(f"\x1b[{self.header_rows + 1 + i};1H\x1b[2K{line}")
        if self.offset:
            note = f" ▲ {self.offset} lines back · PageDown / End returns "
            out.append(f"\x1b[{self.header_rows + 1};{max(1, self.cols - len(note))}H\x1b[7m{note}\x1b[27m")
        out.append("\x1b8")
        self._write("".join(out))
