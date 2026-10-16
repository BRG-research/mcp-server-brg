"""One log file for everything that must not reach the terminal: the MCP server's own log lines and
the stderr of the Claude subprocess.  BRG_LOG sets the path (default ~/.brg/brg.log)."""

from __future__ import annotations

import os
from pathlib import Path

_handle = None


def path() -> Path:
    return Path(os.environ.get("BRG_LOG", Path.home() / ".brg" / "brg.log"))


def handle():
    """The open log file (append, line-buffered)."""
    global _handle
    if _handle is None:
        p = path()
        p.parent.mkdir(parents=True, exist_ok=True)
        _handle = open(p, "a", buffering=1, encoding="utf-8", errors="replace")
    return _handle


def write(line: str) -> None:
    try:
        handle().write(line if line.endswith("\n") else line + "\n")
    except OSError:
        pass
