"""Figures in the terminal.  Kitty, Ghostty and WezTerm take real images through the kitty graphics
protocol, iTerm2 through its inline-image escape; every other terminal gets a half-block pixel rendering
(two pixels per character cell), plus a file:// link to open the original."""

from __future__ import annotations

import base64
import io
import os
import re
import shutil
from pathlib import Path

from rich.console import Console
from rich.text import Text

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


def show(console: Console, path: Path, caption: str = "", max_cols: int = 80) -> None:
    from PIL import Image
    cols = max(20, min(max_cols, console.width - 4))
    with Image.open(path) as im:
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (11, 18, 32, 255))
        bg.alpha_composite(im)
        im = bg.convert("RGB")
        kind = protocol()
        if kind == "kitty" and console.is_terminal:
            _kitty(console, im, cols)
        elif kind == "iterm2" and console.is_terminal:
            _iterm2(console, im, cols)
        else:
            _blocks(console, im, cols)
    link = f"file://{path.resolve()}"
    console.print(Text.assemble(("  ", ""), (caption or path.name, f"italic #8b949e link {link}"), ("  ", ""),
                                (str(path), f"#484f58 link {link}")))


def _png(im) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _kitty(console: Console, im, cols: int) -> None:
    rows = max(1, round(cols * im.height / im.width / 2.2))
    data = base64.b64encode(_png(im)).decode()
    out = console.file
    chunks = [data[i:i + 4096] for i in range(0, len(data), 4096)]
    for i, chunk in enumerate(chunks):
        more = 1 if i < len(chunks) - 1 else 0
        head = f"a=T,f=100,c={cols},r={rows},m={more}" if i == 0 else f"m={more}"
        out.write(f"\x1b_G{head};{chunk}\x1b\\")
    out.write("\n")
    out.flush()


def _iterm2(console: Console, im, cols: int) -> None:
    data = base64.b64encode(_png(im)).decode()
    console.file.write(f"\x1b]1337;File=inline=1;width={cols};preserveAspectRatio=1:{data}\x07\n")
    console.file.flush()


def _blocks(console: Console, im, cols: int) -> None:
    """Half-block rendering: each character cell is one pixel wide and two pixels tall."""
    w = cols
    h = max(2, round(im.height * w / im.width / 1.0))
    h += h % 2
    small = im.resize((w, h))
    px = small.load()
    for y in range(0, h, 2):
        line = Text()
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
