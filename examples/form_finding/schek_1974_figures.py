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
            self.meshes.append({"contours": group, "color": list(color)})

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

    # ------------------------------------------------------------------ figure 3: flow diagram
    sc = Scene("fig3_flow", stroke=0.018)
    H = 0.22
    def box(x, y, w, h, lines, bold=False):
        sc.rect(x, y, w, h)
        if bold:
            sc.rect(x - 0.04, y - 0.04, w + 0.08, h + 0.08)
        for i, t in enumerate(lines):
            sc.text(gl, t, [x + 0.15, y + h - (i + 1) * (H * 1.35) + 0.05, 0], H)
    box(4.0, 11.0, 5.6, 0.5, ["Start form finding"], True)
    box(4.0, 10.1, 5.6, 0.5, ["form the branch-node matrix"])
    box(4.0, 8.3, 5.6, 1.35, ["form the general Gaussian", "transformation D, prepare", "the right-hand sides of (8),", "compute the inverse of D"])
    box(4.0, 6.7, 5.6, 1.1, ["compute the equilibrium shape", "with (9), compute the branch", "lengths and forces with (10)"])
    box(2.4, 5.4, 7.2, 0.8, ["output equilibrium shape by plotter", "or display, analyse"])
    box(2.4, 4.6, 7.2, 0.5, ["changes in the fixed points or load?"])
    box(2.4, 3.8, 7.2, 0.5, ["changes in the force densities?"])
    box(2.4, 3.0, 7.2, 0.5, ["changes in the interconnections?"])
    box(2.4, 1.3, 7.2, 1.2, ["End form finding, introduction of", "additional constraints, see", "chapter 3!"], True)
    box(0.2, 10.3, 3.3, 0.8, ["input network", "interconnections"])
    box(0.2, 9.1, 3.3, 0.8, ["input force", "densities"])
    box(0.2, 7.1, 3.3, 0.8, ["input fixed points", "and load"])
    for y0, y1 in [(11.0, 10.6), (10.1, 9.65), (8.3, 7.8), (6.7, 6.2), (5.4, 5.1), (4.6, 4.3), (3.8, 3.5), (3.0, 2.5)]:
        sc.arrow([6.8, y0, 0], [6.8, y1, 0])
    sc.arrow([3.5, 10.7, 0], [4.0, 10.35, 0]); sc.arrow([3.5, 9.5, 0], [4.0, 8.97, 0]); sc.arrow([3.5, 7.5, 0], [4.0, 7.25, 0])
    # the three questions loop back to the input boxes on the left, as in the paper
    for yq, xr, yb in [(4.85, 1.9, 7.5), (4.05, 1.5, 9.5), (3.25, 1.1, 10.7)]:
        sc.polyline([[2.4, yq, 0], [xr, yq, 0], [xr, yb, 0]])
        sc.arrow([xr, yb, 0], [3.5, yb, 0])
    sc.dump(out / "fig3_flow.json")
    layout["fig3"] = {"panels": [["fig3_flow.json", [0, 0, 0]]], "views": ["top"], "caption": "Fig. 3. Diagram of the form finding."}

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
