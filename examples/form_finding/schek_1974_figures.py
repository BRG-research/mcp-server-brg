"""Draw the figures of Schek (1974) as session_viewer scenes.

Figures 2, 3 and 4 are redraws of the paper's graph, flow diagram and matrix.
Figures 1 and 5 to 10 are drawn from `viewer_scenes/json/shapes.json`, which the
tutorial program `schek_app.py` writes when it runs: this script computes nothing,
it only draws what the tutorial computed.

This script writes plain JSON scene descriptions (lines, polylines, points) plus a
layout file.  `viewer_scenes.py` turns them into session .pb files and manifests,
and `render_figures.sh` renders them with the session_viewer headless harness.
Text is drawn as filled glyphs: the outlines come from the viewer's JetBrains Mono
font and are triangulated by the session kernel into meshes on the viewer's text
lane, so no plotting library is involved anywhere.

Run:  python examples/form_finding/schek_app.py        (writes shapes.json)
      python examples/form_finding/schek_1974_figures.py [--out examples/form_finding/viewer_scenes/json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

np.set_printoptions(precision=3, suppress=True, linewidth=120)

FONT = Path("/home/pv/brg/code_rust/session/session_viewer/assets/fonts/JetBrainsMono-Regular.ttf")

# =============================================================================
# Glyph outlines for labels (the viewer has no text lane; text becomes polylines)
# =============================================================================

class Glyphs:
    def __init__(self, path=FONT):
        from fontTools.ttLib import TTFont
        from fontTools.pens.recordingPen import DecomposingRecordingPen
        self.font = TTFont(str(path))
        self.gs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font["head"].unitsPerEm
        self.RecordingPen = DecomposingRecordingPen          # composites such as "i" (stem + dot) get flattened
        self.alternates = {"0": "zero.zero"}                 # plain zero: the default dotted zero reads as an 8 when small
        self.cache = {}

    def _outline(self, ch):
        """Closed contours of one character in em units, quadratic curves flattened."""
        if ch in self.cache:
            return self.cache[ch]
        name = self.alternates.get(ch, self.cmap[ord(ch)])
        glyph = self.gs[name if name in self.gs else self.cmap[ord(ch)]]
        pen = self.RecordingPen(self.gs); glyph.draw(pen)
        contours, cur = [], []
        for op, pts in pen.value:
            if op == "moveTo":
                cur = [pts[0]]
            elif op == "lineTo":
                cur.append(pts[0])
            elif op == "qCurveTo":
                p0 = cur[-1]
                ctrl = list(pts[:-1]); end = pts[-1]
                # TrueType implied on-curve points between consecutive off-curve points
                pts_full = []
                for i, c in enumerate(ctrl):
                    pts_full.append(c)
                    if i + 1 < len(ctrl):
                        pts_full.append(((c[0] + ctrl[i + 1][0]) / 2, (c[1] + ctrl[i + 1][1]) / 2))
                pts_full.append(end)
                start = p0
                for i in range(0, len(pts_full) - 1, 2):
                    c, e = pts_full[i], pts_full[i + 1]
                    for t in np.linspace(0, 1, 7)[1:]:
                        x = (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * c[0] + t ** 2 * e[0]
                        y = (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * c[1] + t ** 2 * e[1]
                        cur.append((x, y))
                    start = e
            elif op == "closePath":
                if cur:
                    cur.append(cur[0]); contours.append(cur); cur = []
        self.cache[ch] = (contours, glyph.width)
        return self.cache[ch]

    @staticmethod
    def _inside(pt, ring):
        """Even-odd point-in-polygon test in the glyph plane."""
        x, y = pt; inside = False
        for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
            if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
                inside = not inside
        return inside

    def _groups(self, contours):
        """Split a glyph's contours into [outer, hole, hole, ...] groups by nesting depth."""
        depth = []
        for i, c in enumerate(contours):
            depth.append(sum(1 for j, d in enumerate(contours) if j != i and self._inside(c[0], d)))
        groups = []
        for i, c in enumerate(contours):
            if depth[i] % 2 == 0:                               # an outer contour
                holes = [d for j, d in enumerate(contours) if depth[j] == depth[i] + 1 and self._inside(d[0], c)]
                groups.append([c] + holes)
        return groups

    def text(self, s, origin, height, align="left"):
        """Filled glyphs for string s on the z = origin[2] plane: a list of [outer, holes...] groups,
        each contour a closed list of [x, y, z].  The viewer triangulates them (Mesh.from_polygon_with_holes)."""
        k = height / self.upm
        total = sum(self._outline(ch)[1] for ch in s if ch != " ") + s.count(" ") * 600
        x0 = {"left": 0.0, "center": -0.5 * total * k, "right": -total * k}[align]
        out, x = [], x0
        for ch in s:
            if ch == " ":
                x += 600 * k; continue
            contours, adv = self._outline(ch)
            for group in self._groups([c[:-1] for c in contours]):        # drop the repeated closing point
                out.append([[[origin[0] + x + px * k, origin[1] + py * k, origin[2]] for px, py in c] for c in group])
            x += adv * k
        return out


# =============================================================================
# scene container
# =============================================================================

class Scene:
    def __init__(self, name, stroke=0.02):
        self.name = name
        self.stroke = stroke          # default stroke width in world units (never 1.0: see viewer_scenes.py)
        self.lines, self.polylines, self.points, self.meshes = [], [], [], []

    def line(self, a, b, width=None, color=(0, 0, 0, 1)):
        self.lines.append({"a": [float(v) for v in a], "b": [float(v) for v in b],
                           "width": float(width if width is not None else self.stroke), "color": list(color)})

    def polyline(self, pts, color=(0, 0, 0, 1), width=None):
        self.polylines.append({"pts": [[float(v) for v in p] for p in pts], "color": list(color),
                               "width": float(width if width is not None else self.stroke)})

    def point(self, p, width=1.0, color=(0, 0, 0, 1)):
        self.points.append({"p": [float(v) for v in p], "width": width, "color": list(color)})

    def text(self, glyphs, s, origin, height, align="left", color=(0, 0, 0, 1)):
        for group in glyphs.text(s, origin, height, align):
            self.meshes.append({"contours": group, "color": list(color), "kind": "text"})

    def fill(self, x, y, w, h, color):
        """A filled rectangle (viewer print-fill lane, drawn under the ink)."""
        self.meshes.append({"contours": [[[x, y, 0], [x + w, y, 0], [x + w, y + h, 0], [x, y + h, 0]]],
                            "color": list(color), "kind": "fill"})

    def rect(self, x, y, w, h, width=None, color=(0, 0, 0, 1)):
        self.polyline([[x, y, 0], [x + w, y, 0], [x + w, y + h, 0], [x, y + h, 0], [x, y, 0]], color, width)

    def arrow(self, a, b, head=0.18, color=(0, 0, 0, 1)):
        a, b = np.array(a, float), np.array(b, float)
        d = b - a; n = np.linalg.norm(d); d = d / n
        self.polyline([a.tolist(), b.tolist()], color)
        perp = np.array([-d[1], d[0], 0.0])
        self.polyline([(b - d * head + perp * head * 0.4).tolist(), b.tolist(), (b - d * head - perp * head * 0.4).tolist()], color)

    def dump(self, path):
        path.write_text(json.dumps({"name": self.name, "lines": self.lines, "polylines": self.polylines,
                                    "points": self.points, "meshes": self.meshes}))


# =============================================================================
# Figure 2 network (section 2.1)
# =============================================================================

def branch_node_matrix(branches, n_nodes):
    """c(j, i) = +1 for i = i(j), -1 for i = k(j), 0 otherwise  (branches 1-based)."""
    C = np.zeros((len(branches), n_nodes))
    for j, (i, k) in enumerate(branches):
        C[j, i - 1] = 1.0
        C[j, k - 1] = -1.0
    return C


FIG2_BRANCHES = [(1, 6), (2, 7), (3, 8), (4, 9), (1, 4), (1, 2), (2, 3), (3, 4), (4, 5), (1, 5), (2, 5), (3, 5)]
FIG2_XY = {1: (-1, 0), 2: (0, -1), 3: (1, 0), 4: (0, 1), 5: (0, 0), 6: (-2, 0), 7: (0, -2), 8: (2, 0), 9: (0, 2)}

# =============================================================================
# drawing helpers
# =============================================================================

NET_W = 0.12          # cable radius-ish width for the computed nets (metres)
NODE_W = 0.45


def draw_net(sc, branches, X, fixed_nodes, width=NET_W, node_w=NODE_W):
    """The paper's plots show branches only; fixed points are marked with a dot here."""
    for i, k in branches:
        sc.line(X[i - 1], X[k - 1], width)
    for n in fixed_nodes:
        sc.point(X[n - 1], node_w, (0, 0, 0, 1))


def labelled_graph(sc, gl, branches, XY, fixed_nodes, node_r, text_h, branch_numbers=False):
    """Plan drawing like the paper's figures 2 and 5: nodes are dots (fixed nodes larger), node
    numbers are plain text beside the dot, branch numbers plain text beside the branch midpoint."""
    for i, k in branches:
        sc.line([*XY[i - 1], 0], [*XY[k - 1], 0], sc.stroke * 1.6)
    for n in range(len(XY)):
        fx = (n + 1) in fixed_nodes
        sc.point([XY[n][0], XY[n][1], 0.0], node_r * (2.6 if fx else 1.6), (0, 0, 0, 1))
        sc.text(gl, str(n + 1), [XY[n][0] + 0.9 * node_r, XY[n][1] + 0.6 * node_r, 0.0], text_h)
    if branch_numbers:
        for j, (i, k) in enumerate(branches):
            a_, b_ = np.array(XY[i - 1], float), np.array(XY[k - 1], float)
            m = (a_ + b_) / 2
            d = b_ - a_; d = d / (np.linalg.norm(d) + 1e-12)
            perp = np.array([-d[1], d[0]])                      # offset the label off the branch
            pos = m + perp * text_h * 0.9
            sc.text(gl, str(j + 1), [pos[0], pos[1] - 0.35 * text_h * 0.8, 0.0], text_h * 0.8, "center")


def matrix_drawing(sc, gl, cells, cell_w, cell_h, text_h, row_labels=None, col_labels=None, origin=(0, 0)):
    """Rows top to bottom, like a printed matrix.  cells[r][c] is a string."""
    ox, oy = origin
    nr, nc = len(cells), len(cells[0])
    for r in range(nr):
        for c in range(nc):
            y = oy - (r + 0.5) * cell_h
            sc.text(gl, cells[r][c], [ox + (c + 0.5) * cell_w, y - 0.35 * text_h, 0], text_h, "center")
    if col_labels:
        for c, lab in enumerate(col_labels):
            sc.text(gl, lab, [ox + (c + 0.5) * cell_w, oy + 0.4 * cell_h, 0], text_h, "center")
    if row_labels:
        for r, lab in enumerate(row_labels):
            sc.text(gl, lab, [ox - 0.5 * cell_w, oy - (r + 0.5) * cell_h - 0.35 * text_h, 0], text_h, "right")
    # brackets
    h = nr * cell_h; b = 0.25 * cell_w
    sc.polyline([[ox + b, oy, 0], [ox, oy, 0], [ox, oy - h, 0], [ox + b, oy - h, 0]])
    x1 = ox + nc * cell_w
    sc.polyline([[x1 - b, oy, 0], [x1, oy, 0], [x1, oy - h, 0], [x1 - b, oy - h, 0]])



# =============================================================================
# matrix icons: a matrix as a grid of cells, with highlighted rows / columns
# =============================================================================

PLUS, MINUS, ZERO, HI, HI2, GREY = (0.80, 0.88, 1.0, 1), (1.0, 0.84, 0.80, 1), (1, 1, 1, 1), (1.0, 0.95, 0.55, 1), (0.85, 1.0, 0.85, 1), (0.93, 0.93, 0.93, 1)


def matrix_icon(sc, gl, M, x0, y0, cell=0.5, name=None, row_labels=None, col_labels=None, hi_rows=(), hi_cols=(),
                hi_cells=(), fmt="{:g}", text_h=None, value_colors=True, stroke=None):
    """Draw matrix M (2-D) with its top-left corner at (x0, y0) going down. Returns (x1, y_bottom)."""
    M = np.atleast_2d(np.asarray(M, float))
    nr, nc = M.shape
    th = text_h or cell * 0.42
    st = stroke or sc.stroke
    for r in range(nr):
        for c in range(nc):
            x, y = x0 + c * cell, y0 - (r + 1) * cell
            v = M[r, c]
            col = ZERO
            if value_colors and abs(v) > 1e-12:
                col = PLUS if v > 0 else MINUS
            if r in hi_rows or c in hi_cols or (r, c) in hi_cells:
                col = HI if col == ZERO else tuple(0.5 * (a + b) for a, b in zip(col, HI))
            sc.fill(x, y, cell, cell, col)
            sc.polyline([[x, y, 0], [x + cell, y, 0], [x + cell, y + cell, 0], [x, y + cell, 0], [x, y, 0]], GREY, st * 0.6)
            label = "." if abs(v) < 1e-12 else fmt.format(v)
            sc.text(gl, label, [x + cell / 2, y + cell / 2 - 0.35 * th, 0], th, "center")
    # brackets
    bw = cell * 0.25
    sc.polyline([[x0 + bw, y0, 0], [x0, y0, 0], [x0, y0 - nr * cell, 0], [x0 + bw, y0 - nr * cell, 0]], (0, 0, 0, 1), st)
    x1 = x0 + nc * cell
    sc.polyline([[x1 - bw, y0, 0], [x1, y0, 0], [x1, y0 - nr * cell, 0], [x1 - bw, y0 - nr * cell, 0]], (0, 0, 0, 1), st)
    if col_labels is not None:
        for c, lab in enumerate(col_labels):
            sc.text(gl, str(lab), [x0 + (c + 0.5) * cell, y0 + 0.25 * cell, 0], th * 0.85, "center")
    if row_labels is not None:
        for r, lab in enumerate(row_labels):
            sc.text(gl, str(lab), [x0 - 0.3 * cell, y0 - (r + 0.5) * cell - 0.35 * th, 0], th * 0.85, "right")
    if name:
        sc.text(gl, name, [x0 + nc * cell / 2, y0 - nr * cell - 0.9 * cell, 0], th * 1.1, "center")
    return x1, y0 - nr * cell


def op_symbol(sc, gl, sym, x, y_mid, h):
    sc.text(gl, sym, [x, y_mid - 0.35 * h, 0], h, "center")


def flow_diagram(sc, gl):
    """Figure 3 of the paper, redrawn as a clean pipeline: inputs on the left, the loop-backs on the right.
    Box widths are computed from their text (JetBrains Mono advances 0.6 of the text height per character)."""
    H = 0.26                                    # text height
    cw = 0.6 * H                                # width of one character
    def width(lines, pad=0.6):
        return max(len(t) for t in lines) * cw + pad
    main = [("start", ["Start form finding"], True),
            ("cmat", ["1. form the branch-node matrix  C_s = [C  C_f]"], False),
            ("dmat", ["2. form D = C^t Q C  and  D_f = C^t Q C_f,", "   prepare the right-hand sides  p - D_f x_f"], False),
            ("solve", ["3. solve  D x = p_x - D_f x_f  (and y, z)   (9)", "   lengths  l = |C x + C_f x_f|          (1)", "   forces   s = L q                      (10)"], False),
            ("out", ["4. output the equilibrium shape", "   (plotter, display), analyse"], False),
            ("q1", ["changes in the fixed points or the load?"], False),
            ("q2", ["changes in the force densities?"], False),
            ("q3", ["changes in the interconnections?"], False),
            ("end", ["End of form finding.  Additional conditions", "(prescribed lengths or forces): section 3"], True)]
    inputs = [("branch list  i(j), k(j)", "cmat"), ("force densities  q", "dmat"), ("fixed points  x_f, y_f, z_f", "solve"), ("loads  p_x, p_y, p_z", "solve")]
    W_in = width(["input: " + t for t, _ in inputs])
    X = 0.2 + W_in + 1.2                        # main column left edge
    W = max(width(lines) for _, lines, _ in main)
    def box(x, y, w, h, lines, bold=False, fill=None):
        if fill:
            sc.fill(x, y, w, h, fill)
        sc.rect(x, y, w, h)
        if bold:
            sc.rect(x - 0.06, y - 0.06, w + 0.12, h + 0.12)
        for i, t in enumerate(lines):
            sc.text(gl, t, [x + 0.3, y + h - 0.2 - (i + 1) * (H * 1.45) + 0.45 * H, 0], H)
    def arrow_down(x, y0, y1, label=None):
        sc.arrow([x, y0, 0], [x, y1, 0], head=0.22)
        if label:
            sc.text(gl, label, [x + 0.15, (y0 + y1) / 2 - 0.35 * H * 0.9, 0], H * 0.9)
    # lay the main column out from the top
    ys, y = {}, 14.0
    for key, lines, bold in main:
        h = 0.3 + len(lines) * H * 1.45 + 0.2
        y -= h
        ys[key] = (y, h)
        box(X, y, W, h, lines, bold, fill=(0.96, 0.96, 0.96, 1) if key.startswith("q") else None)
        y -= 0.75 if key != "out" else 0.75
    xc = X + W / 2
    order = [k for k, _, _ in main]
    for a, b in zip(order, order[1:]):
        arrow_down(xc, ys[a][0], ys[b][0] + ys[b][1], "no" if a.startswith("q") else None)
    # inputs on the left, each feeding the step that consumes it
    per_target = {}
    for text, target in inputs:
        y0, h = ys[target]
        k = per_target.get(target, 0); per_target[target] = k + 1
        yy = y0 + h - 0.45 - k * 0.75
        box(0.2, yy - 0.3, W_in, 0.6, ["input: " + text])
        sc.arrow([0.2 + W_in, yy, 0], [X, yy, 0], head=0.22)
    # loop-backs on the right: "yes" returns to the step that has to be redone
    for src, dst, dx in [("q1", "solve", 0.8), ("q2", "dmat", 1.4), ("q3", "cmat", 2.0)]:
        y_src = ys[src][0] + ys[src][1] / 2
        y_top = ys[dst][0] + ys[dst][1]
        xr = X + W + dx
        sc.polyline([[X + W, y_src, 0], [xr, y_src, 0], [xr, y_top + 0.38, 0], [xc + 0.8, y_top + 0.38, 0]])
        sc.arrow([xc + 0.8, y_top + 0.38, 0], [xc + 0.8, y_top, 0], head=0.22)
        sc.text(gl, "yes", [X + W + 0.1, y_src + 0.08, 0], H * 0.9)


def icon_scenes(gl, out, layout):
    """The matrix icons used by the tutorial."""
    n, n_f = 5, 4
    C_s = branch_node_matrix(FIG2_BRANCHES, n + n_f); m = len(FIG2_BRANCHES)
    C, C_f = C_s[:, :n], C_s[:, n:]
    q = np.array([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1], float)
    x_all = np.array([-1, 0, 1, 0, 0, -2, 0, 2, 0], float)
    u = C_s @ x_all
    f = np.arange(1, m + 1, dtype=float)
    D = C.T @ np.diag(q) @ C
    rows, cols = [str(i) for i in range(1, m + 1)], [str(i) for i in range(1, n + n_f + 1)]
    cell = 0.5

    def scene(name, caption):
        sc = Scene(name, stroke=0.012)
        return sc

    # icon 1: the branch-node matrix with its two column blocks
    sc = scene("icon_split", "")
    x1, yb = matrix_icon(sc, gl, C_s, 0, 0, cell, "C_s  (12 x 9)", rows, cols, hi_cols=range(n), value_colors=False)
    sc.fill(0, yb, n * cell, m * cell, (1, 0.95, 0.55, 0.35))
    x_, yb2 = matrix_icon(sc, gl, C, x1 + 1.2, 0, cell, "C  (12 x 5)  free nodes", rows, cols[:n])
    matrix_icon(sc, gl, C_f, x_ + 1.2, 0, cell, "C_f  (12 x 4)  fixed nodes", rows, cols[n:])
    sc.text(gl, "C_s = [C  C_f]: the columns of the free nodes form C, those of the fixed nodes C_f", [0, yb - 1.9, 0], 0.26)
    sc.dump(out / "icon_split.json")
    layout["icon_split"] = {"panels": [["icon_split.json", [0, 0, 0]]], "views": ["top"], "caption": ""}

    # icon 2: matrix times vector, row 1 highlighted
    sc = scene("icon_matvec", "")
    x1, yb = matrix_icon(sc, gl, C_s, 0, 0, cell, "C_s  (12 x 9)", rows, cols, hi_rows=[0])
    op_symbol(sc, gl, "x", x1 + 0.5, -m * cell / 2, 0.4)
    x2, _ = matrix_icon(sc, gl, x_all[:, None], x1 + 1.0, 0, cell, "x  (9)", cols, None, hi_rows=[0, 5])
    op_symbol(sc, gl, "=", x2 + 0.5, -m * cell / 2, 0.4)
    matrix_icon(sc, gl, u[:, None], x2 + 1.0, 0, cell, "u = C_s x  (12)", rows, None, hi_rows=[0])
    sc.text(gl, "row 1 of C_s has +1 at node 1 and -1 at node 6:   u_1 = (+1)(x_1) + (-1)(x_6) = -1 - (-2) = 1", [0, yb - 1.9, 0], 0.26)
    sc.text(gl, "every other entry of the row is 0, so the other seven coordinates do not matter for branch 1", [0, yb - 2.4, 0], 0.26)
    sc.dump(out / "icon_matvec.json")
    layout["icon_matvec"] = {"panels": [["icon_matvec.json", [0, 0, 0]]], "views": ["top"], "caption": ""}

    # icon 3: the transpose sums at the nodes, column 5 highlighted
    sc = scene("icon_transpose", "")
    x1, yb = matrix_icon(sc, gl, C_s.T, 0, 0, cell, "C_s^t  (9 x 12): rows are nodes now", cols, rows, hi_rows=[4])
    op_symbol(sc, gl, "x", x1 + 0.5, -(n + n_f) * cell / 2, 0.4)
    x2, yb = matrix_icon(sc, gl, f[:, None], x1 + 1.0, 0, cell, "f  (12)", rows, None, hi_rows=[8, 9, 10, 11])
    op_symbol(sc, gl, "=", x2 + 0.5, -(n + n_f) * cell / 2, 0.4)
    matrix_icon(sc, gl, (C_s.T @ f)[:, None], x2 + 1.0, 0, cell, "C_s^t f  (9)", cols, None, hi_rows=[4])
    sc.text(gl, "row 5 of C_s^t (= column 5 of C_s) says which branches touch node 5: branches 9, 10, 11, 12 end there (-1)", [0, yb - 1.9, 0], 0.26)
    sc.text(gl, "(C_s^t f)_5 = -f_9 - f_10 - f_11 - f_12 = -(9 + 10 + 11 + 12) = -42:  a sum of branch values at a node", [0, yb - 2.4, 0], 0.26)
    sc.dump(out / "icon_transpose.json")
    layout["icon_transpose"] = {"panels": [["icon_transpose.json", [0, 0, 0]]], "views": ["top"], "caption": ""}

    # icon 4: the diagonal matrix scales entry by entry
    sc = scene("icon_diag", "")
    x1, yb = matrix_icon(sc, gl, np.diag(q), 0, 0, cell, "Q = diag(q)  (12 x 12)", rows, rows, hi_cells=[(1, 1)])
    op_symbol(sc, gl, "x", x1 + 0.5, -m * cell / 2, 0.4)
    x2, _ = matrix_icon(sc, gl, u[:, None], x1 + 1.0, 0, cell, "u  (12)", rows, None, hi_rows=[1])
    op_symbol(sc, gl, "=", x2 + 0.5, -m * cell / 2, 0.4)
    matrix_icon(sc, gl, (q * u)[:, None], x2 + 1.0, 0, cell, "Q u = q * u  (12)", rows, None, hi_rows=[1])
    sc.text(gl, "a diagonal matrix only scales: (Q u)_2 = q_2 u_2.  That is why U q = Q u (eq. 6): both are the entry-wise product", [0, yb - 1.9, 0], 0.26)
    sc.dump(out / "icon_diag.json")
    layout["icon_diag"] = {"panels": [["icon_diag.json", [0, 0, 0]]], "views": ["top"], "caption": ""}

    # icon 5: D = C^t Q C, one entry built from the contributing cells
    sc = scene("icon_D", "")
    x1, yb = matrix_icon(sc, gl, C.T, 0, 0, cell, "C^t  (5 x 12)", cols[:n], rows, hi_rows=[0])
    op_symbol(sc, gl, "x", x1 + 0.5, -n * cell / 2, 0.4)
    x2, yb = matrix_icon(sc, gl, np.diag(q), x1 + 1.0, 0, cell, "Q  (12 x 12)", rows, rows, hi_cells=[(0, 0), (4, 4), (5, 5), (9, 9)])
    op_symbol(sc, gl, "x", x2 + 0.5, -n * cell / 2, 0.4)
    x3, _ = matrix_icon(sc, gl, C, x2 + 1.0, 0, cell, "C  (12 x 5)", rows, cols[:n], hi_cols=[0])
    op_symbol(sc, gl, "=", x3 + 0.5, -n * cell / 2, 0.4)
    matrix_icon(sc, gl, D, x3 + 1.0, 0, cell, "D  (5 x 5)", cols[:n], cols[:n], hi_cells=[(0, 0)])
    sc.text(gl, "D[1,1] = sum over the branches j of  C[j,1] * q_j * C[j,1] = q_1 + q_5 + q_6 + q_10 = 2 + 1 + 1 + 1 = 5  (the branches at node 1)", [0, yb - 1.9, 0], 0.26)
    sc.text(gl, "D[1,2] = sum of  C[j,1] * q_j * C[j,2]: only branch 6 touches both nodes, with opposite signs, so  D[1,2] = -q_6 = -1   (figure 4)", [0, yb - 2.4, 0], 0.26)
    sc.dump(out / "icon_D.json")
    layout["icon_D"] = {"panels": [["icon_D.json", [0, 0, 0]]], "views": ["top"], "caption": ""}

    # icon 6: the linear system D x = b, solved
    sc = scene("icon_solve", "")
    x_f = x_all[n:]; D_f = C.T @ np.diag(q) @ C_f; b = np.zeros(n) - D_f @ x_f
    xs = np.linalg.solve(D, b)
    x1, yb = matrix_icon(sc, gl, D, 0, 0, cell, "D  (5 x 5)  known", cols[:n], cols[:n])
    op_symbol(sc, gl, "x", x1 + 0.5, -n * cell / 2, 0.4)
    x2, _ = matrix_icon(sc, gl, xs[:, None], x1 + 1.0, 0, cell, "x  (5)  unknown", cols[:n], None, fmt="{:.2f}", hi_rows=range(n))
    op_symbol(sc, gl, "=", x2 + 0.5, -n * cell / 2, 0.4)
    x3, _ = matrix_icon(sc, gl, b[:, None], x2 + 1.0, 0, cell, "b = p_x - D_f x_f  (5)  known", cols[:n], None, fmt="{:.2f}")
    sc.text(gl, "np.linalg.solve(D, b) finds the five numbers x that make every row of D times x equal to the row's b", [0, yb - 1.9, 0], 0.26)
    sc.text(gl, "row 1: 5 x_1 - x_2 - x_4 - x_5 = -4  ...  five equations, five unknowns, one solution because D is positive definite", [0, yb - 2.4, 0], 0.26)
    sc.dump(out / "icon_solve.json")
    layout["icon_solve"] = {"panels": [["icon_solve.json", [0, 0, 0]]], "views": ["top"], "caption": ""}

    # icon 7: the right-hand side, fixed nodes move to the known side
    sc = scene("icon_rhs", "")
    x1, yb = matrix_icon(sc, gl, D_f, 0, 0, cell, "D_f = C^t Q C_f  (5 x 4)", cols[:n], cols[n:])
    op_symbol(sc, gl, "x", x1 + 0.5, -n * cell / 2, 0.4)
    x2, _ = matrix_icon(sc, gl, x_f[:, None], x1 + 1.0, 0, cell, "x_f  (4)  anchors", cols[n:], None)
    op_symbol(sc, gl, "=", x2 + 0.5, -n * cell / 2, 0.4)
    x3, _ = matrix_icon(sc, gl, (D_f @ x_f)[:, None], x2 + 1.0, 0, cell, "D_f x_f  (5)", cols[:n], None)
    sc.text(gl, "eq. (8):  D x = p_x - D_f x_f.  The anchors are known, so their part D_f x_f is computed and moved to the right-hand side", [0, yb - 1.9, 0], 0.26)
    sc.text(gl, "moving an anchor changes only this vector; D stays the same  (figure 6 of the paper)", [0, yb - 2.4, 0], 0.26)
    sc.dump(out / "icon_rhs.json")
    layout["icon_rhs"] = {"panels": [["icon_rhs.json", [0, 0, 0]]], "views": ["top"], "caption": ""}



# =============================================================================
# shape schemes: matrices as blocks proportional to their size, operators between
# =============================================================================

BLOCK, VEC, RESULT = (0.90, 0.93, 1.0, 1), (0.85, 1.0, 0.85, 1), (1.0, 0.95, 0.55, 1)


def shape_scheme(sc, gl, rows_of_items, scale=0.18, min_size=0.32, gap=0.55, row_gap=1.6, caption=(), th=0.26):
    """rows_of_items: list of rows; a row is a list of items, each either a string (operator text)
    or a tuple (name, n_rows, n_cols[, kind]) drawn as a block of size n_cols x n_rows times scale.
    kind: "result" tints the block yellow, "vec" green. The first block of a row is drawn at x = 0."""
    y_top = 0.0
    for row in rows_of_items:
        heights = [max(it[1] * scale, min_size) for it in row if isinstance(it, tuple)]
        hmax = max(heights) if heights else 1.0
        y_mid = y_top - hmax / 2 - 0.3
        x = 0.0
        for it in row:
            if isinstance(it, str):
                sc.text(gl, it, [x + 0.05, y_mid - 0.35 * th, 0], th)
                x += len(it) * 0.6 * th + 0.1 + gap
                continue
            name, nr, nc = it[0], it[1], it[2]
            kind = it[3] if len(it) > 3 else ("vec" if nc == 1 else "block")
            w, h = max(nc * scale, min_size), max(nr * scale, min_size)
            col = {"result": RESULT, "vec": VEC}.get(kind, BLOCK)
            sc.fill(x, y_mid - h / 2, w, h, col)
            sc.rect(x, y_mid - h / 2, w, h)
            name_w = len(name) * 0.6 * th
            if name_w + 0.15 <= w and th + 0.1 <= h:
                sc.text(gl, name, [x + w / 2, y_mid - 0.35 * th, 0], th, "center")
            else:
                sc.text(gl, name, [x + w / 2, y_mid + h / 2 + 0.15, 0], th, "center")
            sc.text(gl, f"{nr} x {nc}" if nc > 1 else f"{nr}", [x + w / 2, y_mid - h / 2 - 0.42 - 0.35 * th * 0.85, 0], th * 0.85, "center")
            x += w + gap
        y_top = y_mid - hmax / 2 - row_gap
    for i, line in enumerate(caption):
        sc.text(gl, line, [0, y_top - 0.2 - i * 0.5, 0], th)


def scheme_scenes(gl, out, layout):
    """One shape scheme per code cell of the tutorial that multiplies matrices."""
    S = {}
    S["eq1"] = ([[("C", 12, 5), "x", ("x", 5, 1), "+", ("C_f", 12, 4), "x", ("x_f", 4, 1), "=", ("u", 12, 1, "result")]],
                ["u_j = (start-node x) - (end-node x) for every branch j; the free and the fixed end come from the two column blocks.",
                 "The same two products with y and z give v and w.  l_j = sqrt(u_j^2 + v_j^2 + w_j^2) is entry-wise: no matrix."])
    S["eq2"] = ([[("C^t", 5, 12), "x", ("U", 12, 12), "x", ("L^-1", 12, 12), "x", ("s", 12, 1), "-", ("p_x", 5, 1), "=", ("out_x", 5, 1, "result")]],
                ["U L^-1 s is entry-wise:  (u_j / l_j) s_j = the x component of the force in branch j   (12 numbers).",
                 "C^t adds those 12 numbers up at the 5 free nodes, with the sign of the branch direction.   Zero means equilibrium."])
    S["eq4"] = ([[("s", 12, 1), "/", ("l", 12, 1), "=", ("q", 12, 1, "result")]],
                ["entry-wise division: q_j = s_j / l_j.  In the program q is the input, so this line is never executed; (10) runs it backwards."])
    S["eq8"] = ([[("C^t", 5, 12), "x", ("Q", 12, 12), "x", ("C", 12, 5), "=", ("D", 5, 5, "result")],
                 [("C^t", 5, 12), "x", ("Q", 12, 12), "x", ("C_f", 12, 4), "=", ("D_f", 5, 4, "result")]],
                ["D couples free nodes to free nodes, D_f couples free nodes to the fixed ones.  Both use only the topology and q."])
    S["eq9"] = ([[("D", 5, 5), "x", ("x", 5, 1, "result"), "=", ("p_x", 5, 1), "-", ("D_f", 5, 4), "x", ("x_f", 4, 1)]],
                ["everything on the right is known; np.linalg.solve finds the 5 unknowns x.  Repeat with p_y, y_f and p_z, z_f."])
    S["eq10"] = ([[("l", 12, 1), "*", ("q", 12, 1), "=", ("s", 12, 1, "result")]],
                 ["entry-wise product: the force in branch j is its solved length times its force density."])
    S["loop"] = ([[("C^t", 5, 12), "x", ("Q", 12, 12), "x", ("C", 12, 5), "=", ("D", 5, 5, "result"), "and", ("C^t", 5, 12), "x", ("Q", 12, 12), "x", ("C_f", 12, 4), "=", ("D_f", 5, 4, "result")],
                  [("D", 5, 5), "x", ("xyz", 5, 3, "result"), "=", ("p", 5, 3), "-", ("D_f", 5, 4), "x", ("xyz_f", 4, 3)],
                  [("C", 12, 5), "x", ("xyz", 5, 3), "+", ("C_f", 12, 4), "x", ("xyz_f", 4, 3), "=", ("uvw", 12, 3, "result")],
                  [("reactions", 4, 3, "result"), "=", "-", ("C_f^t", 4, 12), "x", ("Q", 12, 12), "x", ("uvw", 12, 3)]],
                 ["the three axes are handled at once: xyz, p, xyz_f and uvw have three columns (x, y, z), so one solve() call does (9) for all of them.",
                  "lengths l = norm of each row of uvw (12 numbers); forces s = l * q (12).  The last row is (5) evaluated at the fixed nodes."])
    S["e1"] = ([[("gradient", 5, 3, "result"), "=", "2", ("C^t", 5, 12), "x", ("Q", 12, 12), "x", ("uvw", 12, 3)]],
               ["derivative of  u^t Q u + v^t Q v + w^t Q w  with respect to the free coordinates; it vanishes at the unloaded equilibrium (Theorem 1)."])
    S["f2"] = ([[("G^t", 4, 12), "x", ("dq", 12, 1, "result"), "=", ("r", 4, 1)],
                [("T", 4, 4, "result"), "=", ("G^t", 4, 12), "x", ("G", 12, 4), "+", ("P^-1 A^2", 4, 4)],
                [("k", 4, 1, "result"), "=", "solve(", ("T", 4, 4), ",", ("A r", 4, 1), ")", "then", ("dq", 12, 1, "result"), "=", ("G", 12, 4), "x", ("k", 4, 1)]],
               ["r = 4 conditions, m = 12 branches: the linear system (16) is 4 equations for 12 unknowns.  The small 4 x 4 system picks one solution.",
                "A = diag(a) damping factors, P^-1 the weights of (21); for plain least squares both terms are absent (T = G^t G)."])
    S["f3"] = ([[("dx/dq", 5, 12, "result"), "=", "-", ("D^-1", 5, 5), "x", ("C^t", 5, 12), "x", ("U", 12, 12)]],
               ["column j says how all 5 free x coordinates move when q_j changes by one unit.  Same for y with V and z with W.",
                "D^-1 is the inverse of the 5 x 5 matrix already factorised in (9); C^t U is the matrix of (5)."])
    S["f4"] = ([[("K", 4, 12, "result"), "=", ("U_bar", 4, 4), "x", ("C_bar", 4, 5), "x", ("D^-1", 5, 5), "x", ("C^t", 5, 12), "x", ("U", 12, 12), "+ (v terms) + (w terms)"],
                [("G_d^t", 4, 12, "result"), "=", "-", ("L_bar^-1", 4, 4), "x", ("K", 4, 12)],
                [("G_f^t", 4, 12, "result"), "=", ("L_bar", 4, 12), "+", ("Q_bar", 4, 4), "x", ("G_d^t", 4, 12)]],
               ["a bar means 'rows of the 4 constrained branches only': C_bar = C[rows] (4 x 5), U_bar = diag(u[rows]) (4 x 4), L_bar^-1 = diag(1 / l[rows]).",
                "row i of G_d^t = how the length of constrained branch i changes with every q_j.   L_bar in the last line is l_j placed on the own column j."])
    S["f5"] = ([[("G^t", 8, 12, "result"), "=", "stack of", ("G_d^t", 4, 12), "and", ("G_f^t", 4, 12)],
                [("T", 8, 8, "result"), "=", ("G^t", 8, 12), "x", ("G", 12, 8), "+", ("P^-1 A^2", 8, 8)]],
               ["mixed conditions (3.6): length conditions and force conditions are just more rows of G^t; T grows to r x r with r = 8."])
    S["g1"] = ([[("C_s", 110, 67), "=", ("C", 110, 61), ("C_f", 110, 6)],
                [("D", 61, 61, "result"), "=", ("C^t", 61, 110), "x", ("Q", 110, 110), "x", ("C", 110, 61), "and", ("D_f", 61, 6, "result"), "=", ("C^t", 61, 110), "x", ("Q", 110, 110), "x", ("C_f", 110, 6)]],
               ["the same program, larger matrices: 110 branches, 61 free nodes, 6 fixed nodes.  D is 61 x 61 and is solved once per shape;",
                "the 112-bar grid of figure 10 has 60 free nodes, and its constrained loop has r = 112 conditions, so T is 112 x 112."])
    for key, (rows, caption) in S.items():
        sc = Scene(f"scheme_{key}", stroke=0.018)
        shape_scheme(sc, gl, rows, scale=0.03 if key == "g1" else 0.18, caption=caption)
        sc.dump(out / f"scheme_{key}.json")
        layout[f"scheme_{key}"] = {"panels": [[f"scheme_{key}.json", [0, 0, 0]]], "views": ["top"], "caption": ""}
    return list(S)


# =============================================================================
# main
# =============================================================================

def main(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    gl = Glyphs()
    layout = {}      # scene name -> {"panels": [(json file, [dx, dy, dz])], "views": [...]}

    # ------------------------------------------------------------------ figure 2: graph + branch-node matrix
    sc = Scene("fig2_graph", stroke=0.012)
    XY2 = [FIG2_XY[n] for n in range(1, 10)]
    labelled_graph(sc, gl, FIG2_BRANCHES, XY2, {6, 7, 8, 9}, 0.05, 0.2, branch_numbers=True)
    sc.dump(out / "fig2_graph.json")
    C_s = branch_node_matrix(FIG2_BRANCHES, 9)
    sc = Scene("fig2_matrix", stroke=0.012)
    cells = [["1" if v > 0 else ("-1" if v < 0 else ".") for v in row] for row in C_s]
    matrix_drawing(sc, gl, cells, 0.5, 0.42, 0.2, [str(r + 1) for r in range(12)], [str(c + 1) for c in range(9)])
    sc.line([2.5, 0.1, 0], [2.5, -12 * 0.42 - 0.1, 0])                       # the C | C_f split
    sc.text(gl, "C", [1.25, -12 * 0.42 - 0.6, 0], 0.26, "center"); sc.text(gl, "Cf", [3.5, -12 * 0.42 - 0.6, 0], 0.26, "center")
    sc.dump(out / "fig2_matrix.json")
    layout["fig2"] = {"panels": [["fig2_graph.json", [0, -2.3, 0]], ["fig2_matrix.json", [3.2, 0, 0]]], "views": ["top"],
                      "caption": "Fig. 2. Graph and branch-node matrix C_s = [C C_f]."}

    # ------------------------------------------------------------------ figure 3: flow diagram (clean redraw)
    sc = Scene("fig3_flow", stroke=0.018)
    flow_diagram(sc, gl)
    sc.dump(out / "fig3_flow.json")
    layout["fig3"] = {"panels": [["fig3_flow.json", [0, 0, 0]]], "views": ["top"], "caption": "Fig. 3. Diagram of the form finding."}
    icon_scenes(gl, out, layout)
    scheme_scenes(gl, out, layout)

    # ------------------------------------------------------------------ figure 4: matrix D (symbolic)
    sc = Scene("fig4_matrix", stroke=0.016)
    sym = [[None] * 5 for _ in range(5)]
    for i in range(5):
        for k in range(5):
            if i == k:
                sym[i][k] = "+".join(f"q{j + 1}" for j, (p_, r_) in enumerate(FIG2_BRANCHES) if i + 1 in (p_, r_))
            else:
                hits = [j + 1 for j, (p_, r_) in enumerate(FIG2_BRANCHES) if {p_, r_} == {i + 1, k + 1}]
                sym[i][k] = f"-q{hits[0]}" if hits else "."
    matrix_drawing(sc, gl, sym, 2.4, 0.7, 0.22)
    sc.text(gl, "D =", [-1.0, -5 * 0.7 / 2 - 0.1, 0], 0.3, "right")
    sc.dump(out / "fig4_matrix.json")
    layout["fig4"] = {"panels": [["fig4_matrix.json", [0, 0, 0]]], "views": ["top"], "caption": "Fig. 4. Structure of the matrix D."}

    # ------------------------------------------------------------------ figures 1, 5-10: drawn from the tutorial's shapes.json
    shapes = json.loads((out / "shapes.json").read_text())
    plan = shapes["fig5_plan"]
    sc = Scene("fig5_graph", stroke=0.05)
    labelled_graph(sc, gl, [tuple(e) for e in plan["branches"]], [p_[:2] for p_ in plan["xyz"]], set(plan["fixed"]), 0.22, 0.85)
    sc.dump(out / "fig5_graph.json")
    layout["fig5"] = {"panels": [["fig5_graph.json", [0, 0, 0]]], "views": ["top"], "caption": "Fig. 5. Graph of the first example."}
    print("figure 5:", len(plan["xyz"]), "nodes,", len(plan["branches"]), "branches")

    captions = {"fig6": "Fig. 6. Different fixed points.",
                "fig7": "Fig. 7. Global changes in the force densities and lengthening of the radial branches.",
                "fig8": "Fig. 8. Global changes in the force densities of the main cables.",
                "fig9": "Fig. 9. Additional distance conditions.",
                "fig10": "Fig. 10. Hanging and prestressed net with the same structure."}
    for name in ["fig6", "fig7", "fig8", "fig9", "fig10"]:
        span = 9.0 if name == "fig10" else 46.0
        items = []
        for c in range(3):
            shp = shapes[f"{name}_{c + 1}"]
            brs = [tuple(e) for e in shp["branches"]]
            X = np.array(shp["xyz"])
            sc = Scene(f"{name}_{c + 1}")
            draw_net(sc, brs, X, set(shp["fixed"]), width=NET_W * (0.25 if name == "fig10" else 1.0),
                     node_w=NODE_W * (0.3 if name == "fig10" else 1.0))
            sc.dump(out / f"{name}_{c + 1}.json")
            items.append([f"{name}_{c + 1}.json", [c * span, 0, 0]])
        layout[name] = {"panels": items, "views": ["persp", "top"], "caption": captions[name]}
    shp = shapes["fig1"]
    sc = Scene("fig1_net"); draw_net(sc, [tuple(e) for e in shp["branches"]], np.array(shp["xyz"]), set(shp["fixed"])); sc.dump(out / "fig1_net.json")
    layout["fig1"] = {"panels": [["fig1_net.json", [0, 0, 0]]], "views": ["persp", "persp2"],
                      "caption": "Fig. 1. Views of a prestressed net."}
    (out / "layout.json").write_text(json.dumps(layout, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "viewer_scenes/json")
    main(ap.parse_args().out)
