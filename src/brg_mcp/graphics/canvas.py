"""Line drawings for the terminal and for an image file from the same primitives.

Text: diagonals are drawn with Braille dots (2×4 per character cell, square-ish on screen, so proportions
hold); vertical and horizontal lines with box-drawing characters (│ ─, dotted ┆ ┄), which look crisp;
labels and markers are plain characters.  Image: the same primitives rendered with Pillow, antialiased
and in colour (main lines blue, construction lines grey, loads red)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

# dot (x in 0..1, y in 0..3) -> bit of the Braille pattern (U+2800 + bits)
_BITS = ((0x01, 0x08), (0x02, 0x10), (0x04, 0x20), (0x40, 0x80))
_JOIN = {frozenset("│─"): "┼", frozenset("┆┄"): "┼", frozenset("│┄"): "┼", frozenset("┆─"): "┼"}


@dataclass
class Canvas:
    cols: int
    rows: int
    dots: set = field(default_factory=set)              # (dx, dy)
    overlay: dict = field(default_factory=dict)         # (row, col) -> char

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

    def rule(self, row: int, col: int, ch: str) -> None:
        """A box-drawing character, joined with one already there."""
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return
        old = self.overlay.get((row, col))
        if old and old in "│─┆┄┼" and old != ch:
            ch = _JOIN.get(frozenset((old, ch)), "┼")
        elif old and old not in "│─┆┄┼":
            return                                       # never overwrite a label or a marker
        self.overlay[(row, col)] = ch

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
    """Primitives in world coordinates (y up), rendered to text with equal scale on both axes, or to PNG."""

    def __init__(self, cols: int = 80, rows: int = 24, xlim: tuple[float, float] = (0, 1), ylim: tuple[float, float] = (0, 1),
                 margin: int = 1) -> None:
        self.cols, self.rows, self.margin = cols, rows, margin
        (x0, x1), (y0, y1) = xlim, ylim
        self.xlim = (x0, x1 if x1 > x0 else x0 + 1)
        self.ylim = (y0, y1 if y1 > y0 else y0 + 1)
        self.ops: list[tuple] = []

    # ------------------------------------------------------------------ primitives
    def line(self, x0: float, y0: float, x1: float, y1: float, kind: str = "main") -> None:
        self.ops.append(("line", x0, y0, x1, y1, kind))

    def polyline(self, points: list[tuple[float, float]], kind: str = "main") -> None:
        for (xa, ya), (xb, yb) in zip(points, points[1:]):
            self.line(xa, ya, xb, yb, kind)

    def dashed(self, x0: float, y0: float, x1: float, y1: float, dash: float = 3.0) -> None:
        self.ops.append(("line", x0, y0, x1, y1, "dashed"))

    def dotted(self, x0: float, y0: float, x1: float, y1: float, step: float = 4.0) -> None:
        self.ops.append(("line", x0, y0, x1, y1, "dotted"))

    def arrow(self, x0: float, y0: float, x1: float, y1: float, kind: str = "load") -> None:
        self.ops.append(("arrow", x0, y0, x1, y1, kind))

    def mark(self, x: float, y: float, char: str = "o") -> None:
        self.ops.append(("mark", x, y, char))

    def label(self, x: float, y: float, text: str, dx: int = 1, dy: int = 0, align: str = "left") -> None:
        self.ops.append(("label", x, y, text, dx, dy, align))

    def title(self, text: str) -> None:
        self.ops.append(("title", text))

    # ------------------------------------------------------------------ text rendering
    def _text_mapping(self):
        x0, x1 = self.xlim
        y0, y1 = self.ylim
        usable_w = max(1, (self.cols - 2 * self.margin) * 2)
        usable_h = max(1, (self.rows - 2 * self.margin) * 4)
        scale = min(usable_w / (x1 - x0), usable_h / (y1 - y0))
        ox = self.margin * 2 + (usable_w - (x1 - x0) * scale) / 2
        oy = self.margin * 4 + (usable_h - (y1 - y0) * scale) / 2
        height = self.rows * 4

        def dot_xy(x: float, y: float) -> tuple[float, float]:
            return ox + (x - x0) * scale, height - 1 - (oy + (y - y0) * scale)
        return dot_xy

    def render(self) -> str:
        canvas = Canvas(self.cols, self.rows)
        dot_xy = self._text_mapping()

        def cell(x: float, y: float) -> tuple[int, int]:
            dx, dy = dot_xy(x, y)
            return int(dy // 4), int(dx // 2)

        def straight(x0, y0, x1, y1, kind) -> bool:
            """Vertical or horizontal lines as box characters; returns False for diagonals."""
            (r0, c0), (r1, c1) = cell(x0, y0), cell(x1, y1)
            if c0 == c1 and r0 != r1:
                ch = "┆" if kind in ("dotted", "dashed") else "│"
                for r in range(min(r0, r1), max(r0, r1) + 1):
                    canvas.rule(r, c0, ch)
                return True
            if r0 == r1 and c0 != c1:
                ch = "┄" if kind in ("dotted", "dashed") else "─"
                for c in range(min(c0, c1), max(c0, c1) + 1):
                    canvas.rule(r0, c, ch)
                return True
            return False

        def sampled(x0, y0, x1, y1, step: float, dash: bool) -> None:
            ax, ay = dot_xy(x0, y0)
            bx, by = dot_xy(x1, y1)
            length = math.hypot(bx - ax, by - ay)
            n = max(1, int(length // step))
            for k in range(n + 1):
                if dash:
                    if k % 2 == 1 or k == n:
                        continue
                    t0, t1 = k / n, min((k + 1) / n, 1)
                    canvas.line(ax + (bx - ax) * t0, ay + (by - ay) * t0, ax + (bx - ax) * t1, ay + (by - ay) * t1)
                else:
                    t = k / n
                    canvas.dot(int(round(ax + (bx - ax) * t)), int(round(ay + (by - ay) * t)))

        for op in self.ops:
            if op[0] == "line":
                _, x0, y0, x1, y1, kind = op
                if straight(x0, y0, x1, y1, kind):
                    continue
                if kind == "dotted":
                    sampled(x0, y0, x1, y1, 4.0, dash=False)
                elif kind == "dashed":
                    sampled(x0, y0, x1, y1, 3.0, dash=True)
                else:
                    canvas.line(*dot_xy(x0, y0), *dot_xy(x1, y1))
            elif op[0] == "arrow":
                _, x0, y0, x1, y1, kind = op
                if not straight(x0, y0, x1, y1, "main"):
                    canvas.line(*dot_xy(x0, y0), *dot_xy(x1, y1))
                dx, dy = x1 - x0, y1 - y0
                head = "v" if dy < 0 and abs(dy) >= abs(dx) else "^" if dy > 0 and abs(dy) >= abs(dx) else ">" if dx > 0 else "<"
                r, c = cell(x1, y1)
                canvas.text(r, c, head)
        for op in self.ops:                                  # labels and marks on top of the lines
            if op[0] == "mark":
                _, x, y, ch = op
                r, c = cell(x, y)
                canvas.text(r, c, ch)
            elif op[0] == "label":
                _, x, y, text, dx, dy, align = op
                r, c = cell(x, y)
                if align == "center":
                    c -= len(text) // 2
                elif align == "right":
                    c -= len(text) - 1
                canvas.text(r + dy, c + dx, text)
            elif op[0] == "title":
                canvas.text(0, 0, op[1])
        lines = canvas.render()
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines)

    # ------------------------------------------------------------------ image rendering
    COLOURS = {"main": (31, 111, 235), "construction": (140, 150, 160), "dotted": (140, 150, 160),
               "dashed": (140, 150, 160), "load": (215, 58, 73), "ray": (90, 100, 110)}

    def render_png(self, path: Path, width_px: int = 1400, title: str = "") -> Path:
        from PIL import Image, ImageDraw, ImageFont
        x0, x1 = self.xlim
        y0, y1 = self.ylim
        margin = 60
        scale = (width_px - 2 * margin) / (x1 - x0)
        height_px = int((y1 - y0) * scale) + 2 * margin + (40 if title else 0)
        img = Image.new("RGB", (width_px, height_px), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default(size=22)
            small = ImageFont.load_default(size=18)
        except TypeError:                                   # older Pillow: no size parameter
            font = small = ImageFont.load_default()
        top = 40 if title else 0

        def px(x: float, y: float) -> tuple[float, float]:
            return margin + (x - x0) * scale, top + margin + (y1 - y) * scale

        def seg(x0_, y0_, x1_, y1_, kind):
            colour = self.COLOURS.get(kind, self.COLOURS["main"])
            a, b = px(x0_, y0_), px(x1_, y1_)
            if kind in ("dotted", "dashed", "construction"):
                length = math.hypot(b[0] - a[0], b[1] - a[1])
                n = max(1, int(length // 12))
                for k in range(0, n, 2):
                    t0, t1 = k / n, min((k + 1) / n, 1)
                    draw.line([a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0,
                               a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1], fill=colour, width=2)
            else:
                draw.line([a, b], fill=colour, width=4 if kind == "main" else 3)

        for op in self.ops:
            if op[0] == "line":
                seg(*op[1:])
            elif op[0] == "arrow":
                _, ax, ay, bx, by, kind = op
                seg(ax, ay, bx, by, kind)
                a, b = px(ax, ay), px(bx, by)
                ang = math.atan2(b[1] - a[1], b[0] - a[0])
                size = 14
                tip = b
                left = (tip[0] - size * math.cos(ang - 0.4), tip[1] - size * math.sin(ang - 0.4))
                right = (tip[0] - size * math.cos(ang + 0.4), tip[1] - size * math.sin(ang + 0.4))
                draw.polygon([tip, left, right], fill=self.COLOURS.get(kind, self.COLOURS["load"]))
        for op in self.ops:
            if op[0] == "mark":
                _, x, y, ch = op
                cx, cy = px(x, y)
                draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(255, 255, 255), outline=(30, 30, 30), width=3)
                if ch not in ("o", "."):
                    draw.text((cx + 10, cy - 26), ch, fill=(30, 30, 30), font=font)
            elif op[0] == "label":
                _, x, y, text, dx, dy, align = op
                cx, cy = px(x, y)
                cx += dx * 10
                cy += dy * 22
                anchor = {"left": "lm", "center": "mm", "right": "rm"}[align]
                draw.text((cx, cy), text, fill=(30, 30, 30), font=small, anchor=anchor)
        if title:
            draw.text((margin, 14), title, fill=(30, 30, 30), font=font)
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path, "PNG", optimize=True)
        return path
