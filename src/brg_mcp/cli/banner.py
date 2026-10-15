"""The BRG pixel logo and header, in the style of the Claude Code banner but in blues."""

from __future__ import annotations

from rich.text import Text

# 7-row pixel bitmaps, '#' = lit pixel.  Letters are 6 pixels wide.
LETTERS = {
    "B": ["#####.", "#....#", "#....#", "#####.", "#....#", "#....#", "#####."],
    "R": ["#####.", "#....#", "#....#", "#####.", "#..#..", "#...#.", "#....#"],
    "G": [".####.", "#....#", "#.....", "#..###", "#....#", "#....#", ".####."],
}
BLUES = ["#5fb3ff", "#3d9bff", "#2b86f0", "#1f6feb", "#1b5fcc"]   # left-to-right gradient of the face
SHADOW = "#0e2d52"                                                  # the offset shadow behind the letters
GAP = 1


def pixel_grid(word: str = "BRG") -> list[list[str | None]]:
    """Return a grid of colour strings (or None) with the lit letters and a shadow offset by one pixel."""
    rows = 7
    cols = sum(6 for _ in word) + GAP * (len(word) - 1)
    face: list[list[bool]] = [[False] * cols for _ in range(rows)]
    x = 0
    for ch in word:
        for r, row in enumerate(LETTERS[ch]):
            for c, px in enumerate(row):
                face[r][x + c] = px == "#"
        x += 6 + GAP
    grid: list[list[str | None]] = [[None] * (cols + 1) for _ in range(rows + 1)]
    for r in range(rows):                     # shadow first (one pixel right and down)
        for c in range(cols):
            if face[r][c]:
                grid[r + 1][c + 1] = SHADOW
    for r in range(rows):                     # the face on top, coloured by column
        for c in range(cols):
            if face[r][c]:
                grid[r][c] = BLUES[min(int(c / cols * len(BLUES)), len(BLUES) - 1)]
    return grid


def logo() -> Text:
    """The pixel grid rendered with half-block characters: two pixel rows per terminal line."""
    grid = pixel_grid()
    text = Text()
    for r in range(0, len(grid), 2):
        top, bottom = grid[r], grid[r + 1] if r + 1 < len(grid) else [None] * len(grid[r])
        for t, b in zip(top, bottom):
            if t and b:
                text.append("▀", style=f"{t} on {b}")
            elif t:
                text.append("▀", style=t)
            elif b:
                text.append("▄", style=b)
            else:
                text.append(" ")
        if r + 2 < len(grid):
            text.append("\n")
    return text


def header_lines(version: str, model_line: str, where: str) -> Text:
    """The three text lines to the right of the logo, like Claude Code's header."""
    text = Text()
    text.append("BRG Terminal", style="bold #e6edf3")
    text.append(f"  v{version}", style="#8b949e")
    text.append("\n")
    text.append(model_line, style="#8b949e")
    text.append("\n")
    text.append(where, style="#8b949e")
    return text
