"""Computing and drawing tools: exact solutions and text drawings the terminal shows as they are made."""

from __future__ import annotations

import os
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from brg_mcp.graphics import funicular
from brg_mcp.graphics.canvas import Drawing

FIGURE_DIR = Path(os.environ.get("BRG_FIGURE_DIR", Path.home() / ".brg" / "figures"))


def register(server: FastMCP) -> None:
    @server.tool()
    def funicular_cable(span: float, loads: list[list[float]], pole_distance: float,
                        support_heights: list[float] | None = None, width: int = 80, height: int = 22) -> dict:
        """Solve and draw the funicular polygon of a hanging cable under vertical point loads with graphic statics,
        step by step: form diagram with Bow's notation, load line, pole and rays, funicular polygon, forces.
        loads: [[x, P], ...] positions from support A and magnitudes (downward positive); pole_distance: the
        horizontal force H (the pole's distance from the load line); support_heights: [zA, zB] (default level).
        Returns the exact numbers and the drawings (text, plus a PNG of each); the terminal shows them to the
        user directly, so describe them, do not redraw them.  width: use the terminal width the system prompt
        gives you.  For an arch, mirror the result (negate the heights)."""
        if not loads:
            raise ValueError("give at least one load as [x, P]")
        sol = funicular.solve(span, [(float(x), float(p)) for x, p in loads], pole_distance,
                              tuple(support_heights) if support_heights else (0.0, 0.0))
        sol["drawings"] = funicular.drawings(sol, max(40, min(160, width)), max(12, min(60, height)), image_dir=FIGURE_DIR)
        return sol

    @server.tool()
    def draw_diagram(lines: list[list[float]] | None = None, arrows: list[list[float]] | None = None,
                     points: list[list] | None = None, labels: list[list] | None = None,
                     dashed: list[list[float]] | None = None, title: str = "", width: int = 80, height: int = 22) -> dict:
        """Draw a 2D line diagram (form diagram, force polygon, truss, arch, any construction) as a text drawing with
        equal scale on both axes, y upward.  lines/dashed/arrows: [[x0, y0, x1, y1], ...]; points: [[x, y, "A"], ...]
        (the third item is the marker or name, one character shown at the point); labels: [[x, y, "text"], ...].
        The terminal shows the drawing to the user directly; refer to it by its title."""
        xs, ys = [], []
        for seg in (lines or []) + (arrows or []) + (dashed or []):
            xs += [seg[0], seg[2]]; ys += [seg[1], seg[3]]
        for p in (points or []) + (labels or []):
            xs.append(float(p[0])); ys.append(float(p[1]))
        if not xs:
            raise ValueError("nothing to draw")
        pad_x = max(0.05 * (max(xs) - min(xs)), 0.5)
        pad_y = max(0.05 * (max(ys) - min(ys)), 0.5)
        d = Drawing(max(40, min(160, width)), max(8, min(60, height)),
                    xlim=(min(xs) - pad_x, max(xs) + pad_x), ylim=(min(ys) - pad_y, max(ys) + pad_y), margin=1)
        for seg in lines or []:
            d.line(*seg[:4])
        for seg in dashed or []:
            d.dashed(*seg[:4])
        for seg in arrows or []:
            d.arrow(*seg[:4])
        for p in points or []:
            d.mark(float(p[0]), float(p[1]), str(p[2])[:1] if len(p) > 2 and str(p[2]) else "o")
            if len(p) > 2 and len(str(p[2])) > 1:
                d.label(float(p[0]), float(p[1]), str(p[2]), dx=2)
        for lab in labels or []:
            d.label(float(lab[0]), float(lab[1]), str(lab[2]), dx=0, align="center")
        result = {"title": title, "drawing": d.render()}
        try:
            result["image"] = str(d.render_png(FIGURE_DIR / f"diagram-{time.strftime('%Y%m%d-%H%M%S')}.png", title=title))
        except Exception:                                       # noqa: BLE001
            pass
        return result
