"""A text canvas for line drawings in the terminal.  Lines are drawn with Braille dots (2×4 dots per
character cell, which are square-ish on screen, so shapes keep their proportions); labels and markers are
plain characters laid over the dots.  World coordinates are mapped with equal scale on both axes."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# dot (x in 0..1, y in 0..3) -> bit of the Braille pattern (U+2800 + bits)
_BITS = ((0x01, 0x08), (0x02, 0x10), (0x04, 0x20), (0x40, 0x80))


@dataclass
class Canvas:
    cols: int
    rows: int
    dots: set = field(default_factory=set)              # (dx, dy)
    overlay: dict = field(default_factory=dict)         # (row, col) -> char

    # ------------------------------------------------------------------ dot space
    @property
    def width(self) -> int:
        return self.cols * 2

    @property
    def height(self) -> int:
        return self.rows * 4

    def dot(self, x: int, y: int) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.dots.add((x, y))

    def line(self, x0: float, y0: float, x1: float, y1: float) -> None:
        """Bresenham in dot space."""
        x0, y0, x1, y1 = (int(round(v)) for v in (x0, y0, x1, y1))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.dot(x0, y0)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def text(self, row: int, col: int, s: str) -> None:
        for i, ch in enumerate(s):
            if 0 <= row < self.rows and 0 <= col + i < self.cols:
                self.overlay[(row, col + i)] = ch

    def render(self) -> list[str]:
        lines = []
        for r in range(self.rows):
            chars = []
            for c in range(self.cols):
                ch = self.overlay.get((r, c))
                if ch is None:
                    bits = 0
                    for dy in range(4):
                        for dx in range(2):
                            if (c * 2 + dx, r * 4 + dy) in self.dots:
                                bits |= _BITS[dy][dx]
                    ch = chr(0x2800 + bits) if bits else " "
                chars.append(ch)
            lines.append("".join(chars).rstrip())
        return lines


class Drawing:
    """A canvas with a world coordinate system (y up), equal scale on both axes, and a margin for labels."""

    def __init__(self, cols: int = 80, rows: int = 24, xlim: tuple[float, float] = (0, 1), ylim: tuple[float, float] = (0, 1),
                 margin: int = 1) -> None:
        self.canvas = Canvas(cols, rows)
        self.cols, self.rows = cols, rows
        (x0, x1), (y0, y1) = xlim, ylim
        x1, y1 = (x1 if x1 > x0 else x0 + 1), (y1 if y1 > y0 else y0 + 1)
        usable_w = max(1, (cols - 2 * margin) * 2)
        usable_h = max(1, (rows - 2 * margin) * 4)
        self.scale = min(usable_w / (x1 - x0), usable_h / (y1 - y0))     # dots per world unit, both axes
        self.x0, self.y0 = x0, y0
        self.ox = margin * 2 + (usable_w - (x1 - x0) * self.scale) / 2
        self.oy = margin * 4 + (usable_h - (y1 - y0) * self.scale) / 2

    # world -> dot coordinates
    def dot_xy(self, x: float, y: float) -> tuple[float, float]:
        return self.ox + (x - self.x0) * self.scale, self.canvas.height - 1 - (self.oy + (y - self.y0) * self.scale)

    def cell(self, x: float, y: float) -> tuple[int, int]:
        dx, dy = self.dot_xy(x, y)
        return int(dy // 4), int(dx // 2)

    def line(self, x0: float, y0: float, x1: float, y1: float) -> None:
        self.canvas.line(*self.dot_xy(x0, y0), *self.dot_xy(x1, y1))

    def polyline(self, points: list[tuple[float, float]]) -> None:
        for (xa, ya), (xb, yb) in zip(points, points[1:]):
            self.line(xa, ya, xb, yb)

    def dashed(self, x0: float, y0: float, x1: float, y1: float, dash: float = 3.0) -> None:
        """A dashed line (dash length in dots)."""
        ax, ay = self.dot_xy(x0, y0)
        bx, by = self.dot_xy(x1, y1)
        length = math.hypot(bx - ax, by - ay)
        if length == 0:
            return
        n = int(length // dash)
        for k in range(0, n, 2):
            t0, t1 = k / max(n, 1), min((k + 1) / max(n, 1), 1)
            self.canvas.line(ax + (bx - ax) * t0, ay + (by - ay) * t0, ax + (bx - ax) * t1, ay + (by - ay) * t1)

    def dotted(self, x0: float, y0: float, x1: float, y1: float, step: float = 4.0) -> None:
        """A faint line: one dot every `step` dots (lines of action, construction lines)."""
        ax, ay = self.dot_xy(x0, y0)
        bx, by = self.dot_xy(x1, y1)
        length = math.hypot(bx - ax, by - ay)
        n = int(length // step)
        for k in range(n + 1):
            t = k / max(n, 1)
            self.canvas.dot(int(round(ax + (bx - ax) * t)), int(round(ay + (by - ay) * t)))

    def arrow(self, x0: float, y0: float, x1: float, y1: float) -> None:
        """A line with an arrowhead character at its end."""
        self.line(x0, y0, x1, y1)
        dx, dy = x1 - x0, y1 - y0
        head = "v" if dy < 0 and abs(dy) >= abs(dx) else "^" if dy > 0 and abs(dy) >= abs(dx) else ">" if dx > 0 else "<"
        r, c = self.cell(x1, y1)
        self.canvas.text(r, c, head)

    def mark(self, x: float, y: float, char: str = "o") -> None:
        r, c = self.cell(x, y)
        self.canvas.text(r, c, char)

    def label(self, x: float, y: float, text: str, dx: int = 1, dy: int = 0, align: str = "left") -> None:
        """Text near a world point, offset by (dx, dy) cells; align left/center/right on the point."""
        r, c = self.cell(x, y)
        if align == "center":
            c -= len(text) // 2
        elif align == "right":
            c -= len(text) - 1
        self.canvas.text(r + dy, c + dx, text)

    def title(self, text: str) -> None:
        self.canvas.text(0, 0, text)

    def render(self) -> str:
        lines = self.canvas.render()
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines)
