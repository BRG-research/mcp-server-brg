"""The funicular polygon of a hanging cable (or, mirrored, an arch) under vertical point loads, solved
exactly and drawn step by step in the graphic statics way: form diagram with Bow's notation, load line,
pole and rays, the funicular polygon, and the forces read off the force diagram."""

from __future__ import annotations

import math
import string

from .canvas import Drawing


def solve(span: float, loads: list[tuple[float, float]], pole_distance: float,
          support_heights: tuple[float, float] = (0.0, 0.0)) -> dict:
    """Vertical loads (x, P) on a cable between A=(0, zA) and B=(span, zB) with horizontal force H = pole_distance.
    Returns the nodes, the segment forces, the reactions and the force polygon (load line + pole)."""
    loads = sorted(loads)
    H = float(pole_distance)
    if H <= 0 or span <= 0:
        raise ValueError("span and pole_distance must be positive")
    if any(not 0 < x < span for x, _ in loads):
        raise ValueError("every load must lie strictly between the supports")
    zA, zB = support_heights
    total = sum(p for _, p in loads)
    # vertical reactions of the equivalent simple beam (the moment M(x)/H gives the sag below the chord)
    RB_beam = sum(p * x for x, p in loads) / span
    RA_beam = total - RB_beam
    nodes = [(0.0, zA)]
    for x, _ in loads:
        moment = RA_beam * x - sum(p * (x - xi) for xi, p in loads if xi < x)
        chord = zA + (zB - zA) * x / span
        nodes.append((x, chord - moment / H))
    nodes.append((span, zB))
    segments = []
    letters = string.ascii_lowercase
    for k, ((xa, za), (xb, zb)) in enumerate(zip(nodes, nodes[1:])):
        slope = (zb - za) / (xb - xa)
        V = -slope * H                                  # vertical component of the segment force
        segments.append({"space": letters[k], "from": [xa, za], "to": [xb, zb], "slope": slope,
                         "horizontal": H, "vertical": V, "force": math.hypot(H, V),
                         "length": math.hypot(xb - xa, zb - za)})
    # force polygon: load line downward from a=(0,0); pole to the right at (H, -V_first) so the rays are
    # parallel to the segments
    load_points = [(0.0, 0.0)]
    for _, p in loads:
        load_points.append((0.0, load_points[-1][1] - p))
    pole = (H, -segments[0]["vertical"])
    reactions = {"A": {"vertical": segments[0]["vertical"], "horizontal": H},
                 "B": {"vertical": -segments[-1]["vertical"], "horizontal": H}}
    sag = min(z for _, z in nodes)
    return {"span": span, "loads": [{"x": x, "P": p} for x, p in loads], "pole_distance": H,
            "support_heights": [zA, zB], "nodes": [[x, z] for x, z in nodes], "segments": segments,
            "reactions": reactions, "total_load": total, "lowest_point": sag,
            "force_polygon": {"load_line": [[x, y] for x, y in load_points], "pole": [pole[0], pole[1]],
                              "points": {letters[i]: [x, y] for i, (x, y) in enumerate(load_points)}}}


def _form_frame(sol: dict, cols: int, rows: int) -> Drawing:
    span = sol["span"]
    zs = [z for _, z in sol["nodes"]]
    depth = max(0.5, max(zs) - min(zs))
    return Drawing(cols, rows, xlim=(-0.08 * span, 1.08 * span),
                   ylim=(min(zs) - 0.2 * depth, max(zs) + 0.12 * span + 0.05 * depth), margin=1)


def _draw_supports_and_loads(d: Drawing, sol: dict, with_spaces: bool = True) -> None:
    """Supports, the loads as arrows at the top (pointing down onto the chord), their lines of action
    dotted below, the spaces lettered between them, the span underneath."""
    span = sol["span"]
    zA, zB = sol["support_heights"]
    zs = [z for _, z in sol["nodes"]]
    depth = max(0.5, max(zs) - min(zs))
    top = max(zA, zB)
    bottom = min(zs) - 0.1 * depth
    d.mark(0, zA, "A")
    d.mark(span, zB, "B")
    letters = string.ascii_lowercase
    arrow_len = 0.12 * span
    for load in sol["loads"]:
        x = load["x"]
        d.dotted(x, top, x, bottom)
        d.arrow(x, top + arrow_len, x, top)
        d.label(x, top + arrow_len, f"{load['P']:g}", dx=0, dy=-1, align="center")
    if with_spaces:
        xs = [0.0] + [l["x"] for l in sol["loads"]] + [span]
        for k, (xa, xb) in enumerate(zip(xs, xs[1:])):
            d.label((xa + xb) / 2, top + arrow_len / 2, letters[k], dx=0, dy=0, align="center")
    d.label(span / 2, bottom, f"span {span:g}", dx=0, dy=1, align="center")


def _force_frame(sol: dict, cols: int, rows: int) -> Drawing:
    H = sol["pole_distance"]
    total = sol["total_load"]
    pole_y = sol["force_polygon"]["pole"][1]
    ymin, ymax = min(-total, pole_y), max(0.0, pole_y)
    return Drawing(cols, rows, xlim=(-0.35 * H - 0.1 * total, 1.3 * H), ylim=(ymin - 0.15 * total, ymax + 0.15 * total), margin=1)


def _draw_load_line(d: Drawing, sol: dict) -> None:
    pts = sol["force_polygon"]["load_line"]
    letters = string.ascii_lowercase
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d.arrow(x0, y0, x1, y1)
    for i, (x, y) in enumerate(pts):
        d.mark(x, y, "o")
        d.label(x, y, letters[i], dx=-2, dy=0, align="right")
    for i, load in enumerate(sol["loads"]):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        d.label(x0, (y0 + y1) / 2, f"{load['P']:g}", dx=-4, dy=0, align="right")


def drawings(sol: dict, cols: int = 80, rows: int = 22) -> list[dict]:
    """The step-by-step drawings for one solution."""
    out: list[dict] = []
    letters = string.ascii_lowercase
    H = sol["pole_distance"]
    nodes = [tuple(n) for n in sol["nodes"]]

    # 1. form diagram: supports, load lines, Bow's notation
    d = _form_frame(sol, cols, rows)
    _draw_supports_and_loads(d, sol)
    out.append({"title": "Step 1 · form diagram: supports A and B, the loads on their lines of action, the spaces a, b, c … lettered (Bow's notation)", "text": d.render()})

    # 2. load line
    d = _force_frame(sol, cols, rows)
    _draw_load_line(d, sol)
    out.append({"title": f"Step 2 · load line: the loads head to tail, {sol['total_load']:g} in all, the points lettered a … {letters[len(sol['loads'])]} after the spaces they separate", "text": d.render()})

    # 3. pole and rays
    d = _force_frame(sol, cols, rows)
    _draw_load_line(d, sol)
    px, py = sol["force_polygon"]["pole"]
    for (x, y) in sol["force_polygon"]["load_line"]:
        d.line(px, py, x, y)
    d.mark(px, py, "O")
    d.label(px, py, "pole", dx=2)
    d.dashed(0, py, px, py)
    d.label(px / 2, py, f"H = {H:g}", dx=0, dy=1, align="center")
    out.append({"title": f"Step 3 · pole O at the horizontal distance H = {H:g} from the load line (H is the horizontal pull in the cable); one ray from O to every point", "text": d.render()})

    # 4. funicular polygon, segment by segment
    d = _form_frame(sol, cols, rows)
    _draw_supports_and_loads(d, sol, with_spaces=False)
    d.polyline(nodes)
    for seg in sol["segments"]:
        (xa, za), (xb, zb) = seg["from"], seg["to"]
        d.label((xa + xb) / 2, (za + zb) / 2, seg["space"], dx=0, dy=-1, align="center")
    for x, z in nodes[1:-1]:
        d.mark(x, z, "o")
        d.label(x, z, f"{z:+.2f}", dx=1, dy=1)
    out.append({"title": "Step 4 · funicular polygon: from A, each segment parallel to its ray (a ∥ O-a, b ∥ O-b …) until the next line of action; the last one arrives at B", "text": d.render()})

    # 5. forces: the two diagrams side by side with the table
    rows_t = [f"  {'segment':8}{'ray':8}{'horizontal':>12}{'vertical':>10}{'force':>9}{'slope':>8}",
              "  " + "─" * 55]
    for seg in sol["segments"]:
        rows_t.append(f"  {seg['space']:8}{'O-' + seg['space']:8}{seg['horizontal']:12.3g}{seg['vertical']:10.3g}{seg['force']:9.3g}{seg['slope']:8.3g}")
    ra, rb = sol["reactions"]["A"], sol["reactions"]["B"]
    rows_t.append("")
    rows_t.append(f"  reactions: A vertical {ra['vertical']:.3g}, B vertical {rb['vertical']:.3g}, horizontal {H:g} at both; "
                  f"lowest point {sol['lowest_point']:+.3g}")
    out.append({"title": "Step 5 · forces: each ray is one segment force; its horizontal part is H, its vertical part the ray's height, its length the force", "text": "\n".join(rows_t)})
    return out
