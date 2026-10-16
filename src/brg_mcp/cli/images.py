"""Figures in the terminal.  Kitty, Ghostty and WezTerm take real images through the kitty graphics
protocol, iTerm2 through its inline-image escape.  Every other terminal gets the caption and the path as a
file:// link (Ctrl+click opens the image viewer), or the figure is opened in the system viewer right away
(mode "open").  A half-block pixel rendering exists for the curious (mode "blocks") but is not the default.

Modes (BRG_FIGURES, or /figures <mode> in the terminal):
  auto    inline image where the terminal can, else a link          (default)
  link    always the link only
  open    the link, and the image opened in the system viewer
  blocks  the pixel rendering in any terminal"""

from __future__ import annotations

import base64
import io
import os
import re
import shutil
from pathlib import Path

from rich.console import Console
from rich.text import Text

MODES = ("auto", "link", "open", "blocks")
IMAGE_LINK = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")


def protocol() -> str:
    term, program = os.environ.get("TERM", ""), os.environ.get("TERM_PROGRAM", "")
    if os.environ.get("KITTY_WINDOW_ID") or term == "xterm-kitty" or program.lower() in ("ghostty", "wezterm"):
        return "kitty"
    if program == "iTerm.app":
        return "iterm2"
    return "blocks"


def resolve(path: str, roots: list[Path]) -> Path | None:
    """The file for an image reference: as given, under a root, or by its basename anywhere in knowledge/."""
    p = Path(path)
    if p.is_file():
        return p
    for root in roots:
        if (root / p).is_file():
            return root / p
    for root in roots:
        hits = list((root / "knowledge").glob(f"**/{p.name}")) if (root / "knowledge").is_dir() else []
        if hits:
            return hits[0]
    return None


def show(console: Console, path: Path, caption: str = "", max_cols: int = 80, mode: str = "auto") -> None:
    """Show one figure according to `mode` (see the module docstring)."""
    kind = protocol()
    inline = mode == "blocks" or (mode == "auto" and kind in ("kitty", "iterm2") and console.is_terminal)
    if inline:
        from PIL import Image
        cols = max(20, min(max_cols, console.width - 4))
        with Image.open(path) as im:
            im = im.convert("RGBA")
            bg = Image.new("RGBA", im.size, (11, 18, 32, 255))
            bg.alpha_composite(im)
            im = bg.convert("RGB")
            if mode == "blocks" or kind == "blocks":
                _blocks(console, im, cols)
            elif kind == "kitty":
                _kitty(console, im, cols)
            else:
                _iterm2(console, im, cols)
    link = f"file://{path.resolve()}"
    hint = "" if inline else "   Ctrl+click opens it · /figures open shows figures in your image viewer"
    console.print(Text.assemble(("  ▣ ", "#58a6ff"), (caption or path.name, f"bold #c9d1d9 link {link}"), ("  ", ""),
                                (str(path), f"#8b949e link {link}"), (hint, "#484f58")))
    if mode == "open":
        open_external(path)


def _png(im) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _kitty(console: Console, im, cols: int) -> None:
    rows = max(1, round(cols * im.height / im.width / 2.2))
    data = base64.b64encode(_png(im)).decode()
    out = console.file
    out.write("  ")
    chunks = [data[i:i + 4096] for i in range(0, len(data), 4096)]
    for i, chunk in enumerate(chunks):
        more = 1 if i < len(chunks) - 1 else 0
        head = f"a=T,f=100,c={cols},r={rows},m={more}" if i == 0 else f"m={more}"
        out.write(f"\x1b_G{head};{chunk}\x1b\\")
    out.write("\n")
    out.flush()


def _iterm2(console: Console, im, cols: int) -> None:
    data = base64.b64encode(_png(im)).decode()
    console.file.write(f"  \x1b]1337;File=inline=1;width={cols};preserveAspectRatio=1:{data}\x07\n")
    console.file.flush()


def _blocks(console: Console, im, cols: int) -> None:
    """Half-block rendering: each character cell is one pixel wide and two pixels tall."""
    w = cols
    h = max(2, round(im.height * w / im.width / 1.0))
    h += h % 2
    small = im.resize((w, h))
    px = small.load()
    for y in range(0, h, 2):
        line = Text("  ")
        for x in range(w):
            top, bottom = px[x, y], px[x, y + 1]
            line.append("▀", style=f"rgb({top[0]},{top[1]},{top[2]}) on rgb({bottom[0]},{bottom[1]},{bottom[2]})")
        console.print(line)


def open_external(path: Path) -> bool:
    opener = shutil.which("xdg-open") or shutil.which("open")
    if not opener:
        return False
    import subprocess
    subprocess.Popen([opener, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True
