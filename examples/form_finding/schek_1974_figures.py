"""Rebuild the figures of Schek (1974) as session_viewer scenes.

Figures 2, 3, 4 and 5 are exact redraws of the paper's graph, flow diagram, matrix
and example network (topology traced from the printed figure).  Figures 1 and 6-10
are recomputed with the linear force density method (section 2) and its damped
least-squares extension for length and force constraints (section 3).  The paper
does not print the anchor coordinates or the load, so those are chosen to match the
printed proportions; everything else (force densities, which branches are
constrained, 112 identical bars in figure 10) follows the text.

This script writes plain JSON scene descriptions (lines, polylines, points) plus a
layout file.  `viewer_scenes.py` turns them into session .pb files and manifests,
and `render_figures.sh` renders them with the session_viewer headless harness.
Text is drawn as glyph outlines taken from the viewer's JetBrains Mono font, so
no plotting library is involved anywhere.

Run:  python examples/form_finding/schek_1974_figures.py [--out examples/form_finding/viewer_scenes/json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

np.set_printoptions(precision=3, suppress=True, linewidth=120)

FONT = Path("/home/pv/brg/code_rust/session/session_viewer/assets/fonts/JetBrainsMono-Regular.ttf")

# =============================================================================
# Force density method (Schek 1974, section 2) and constraints (section 3)
# =============================================================================


def branch_node_matrix(branches, n_nodes):
    """c(j, i) = +1 for i = i(j), -1 for i = k(j), 0 otherwise  (branches 1-based)."""
    C = np.zeros((len(branches), n_nodes))
    for j, (i, k) in enumerate(branches):
        C[j, i - 1] = 1.0
        C[j, k - 1] = -1.0
    return C


def fd_solve(C_s, free, fixed, xyz_fixed, q, p):
    """Equations (7)-(10). Returns xyz, u/v/w, lengths, forces, residuals, D^-1 and C."""
    C, C_f = C_s[:, free], C_s[:, fixed]
    Q = np.diag(q)
    D = C.T @ Q @ C
    D_f = C.T @ Q @ C_f
    xyz = np.zeros((C_s.shape[1], 3))
    xyz[fixed] = xyz_fixed
    Dinv = np.linalg.inv(D)
    xyz[free] = Dinv @ (p[free] - D_f @ xyz_fixed)      # eq. (9)
    uvw = C_s @ xyz                                      # eq. (1)
    l = np.linalg.norm(uvw, axis=1)
    return xyz, uvw, l, q * l, p - C_s.T @ Q @ uvw, Dinv, C


def fd_constrained(C_s, free, fixed, xyz_fixed, q0, p, length_cons=(), force_cons=(),
                   a=0.7, lam0=0.05, kmax=80, tol=1e-9):
    """Section 3: iterate on q so that prescribed lengths / forces are met.

    length_cons: list of (branch index 0-based, l_v);  force_cons: list of (branch index, s_v).
    'Modified damped' least squares, eqs. (20)-(25): T k = A r, dq = G k, with
    T = G^t G + P^-1 A^2.  Here P^-1 = lam * diag(G^t G) and lam is adapted: it is
    halved after a step that reduces max|g| and multiplied by 4 after one that does not
    (the Levenberg-Marquardt rule), which is what keeps 112 simultaneous length
    conditions (figure 10.1) from overshooting.  Jacobians from eqs. (28), (31), (34).
    """
    q = q0.astype(float).copy()
    lam = lam0
    hist = []

    def residual_and_jac(q):
        xyz, uvw, l, s, r, Dinv, C = fd_solve(C_s, free, fixed, xyz_fixed, q, p)
        CDC = C @ Dinv @ C.T
        rows, g = [], []
        for j, lv in length_cons:
            dl = -(1.0 / l[j]) * sum(uvw[j, a_] * CDC[j, :] * uvw[:, a_] for a_ in range(3))   # eq. (31)
            rows.append(dl); g.append(l[j] - lv)                                              # eq. (29)
        for j, sv in force_cons:
            dl = -(1.0 / l[j]) * sum(uvw[j, a_] * CDC[j, :] * uvw[:, a_] for a_ in range(3))
            ds = q[j] * dl; ds[j] += l[j]                                                     # eq. (34)
            rows.append(ds); g.append(q[j] * l[j] - sv)                                       # eq. (32)
        return np.array(g), np.array(rows)

    g, Gt = residual_and_jac(q)
    for it in range(kmax):
        err = np.abs(g).max(); hist.append(err)
        if err < tol:
            break
        G = Gt.T
        GtG = Gt @ G
        A = a * np.eye(len(g))
        for _ in range(12):
            T = GtG + lam * (np.diag(np.diag(GtG)) + 1e-12 * np.eye(len(g))) @ A @ A       # eq. (23)
            k = np.linalg.solve(T, A @ (-g))                                                 # eqs. (20), (24)
            dq = G @ k                                                                       # eq. (25)
            # keep every force density on its side of zero (a cable must stay a cable)
            shrink = np.where(np.sign(q + dq) != np.sign(q), np.abs(0.5 * q / np.where(dq == 0, 1, dq)), 1.0)
            dq = dq * min(1.0, shrink.min())
            g_new, Gt_new = residual_and_jac(q + dq)
            if np.abs(g_new).max() < err:
                q, g, Gt = q + dq, g_new, Gt_new
                lam = max(lam / 2, 1e-9)
                break
            lam *= 4
        else:
            break   # no damping value improves the residual: the conditions are unattainable
    xyz, uvw, l, s, r, _, _ = fd_solve(C_s, free, fixed, xyz_fixed, q, p)
    return xyz, l, s, q, hist


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

    def text(self, s, origin, height, align="left"):
        """Polylines (lists of [x, y, z]) for string s on the z = origin[2] plane."""
        k = height / self.upm
        total = sum(self._outline(ch)[1] for ch in s if ch != " ") + s.count(" ") * 600
        x0 = {"left": 0.0, "center": -0.5 * total * k, "right": -total * k}[align]
        out, x = [], x0
        for ch in s:
            if ch == " ":
                x += 600 * k; continue
            contours, adv = self._outline(ch)
            for c in contours:
                out.append([[origin[0] + x + px * k, origin[1] + py * k, origin[2]] for px, py in c])
            x += adv * k
        return out


# =============================================================================
# scene container
# =============================================================================

class Scene:
    def __init__(self, name, stroke=0.02):
        self.name = name
        self.stroke = stroke          # default stroke width in world units (never 1.0: see viewer_scenes.py)
        self.lines, self.polylines, self.points = [], [], []

    def line(self, a, b, width=None, color=(0, 0, 0, 1)):
        self.lines.append({"a": [float(v) for v in a], "b": [float(v) for v in b],
                           "width": float(width if width is not None else self.stroke), "color": list(color)})

    def polyline(self, pts, color=(0, 0, 0, 1), width=None):
        self.polylines.append({"pts": [[float(v) for v in p] for p in pts], "color": list(color),
                               "width": float(width if width is not None else self.stroke)})

    def point(self, p, width=1.0, color=(0, 0, 0, 1)):
        self.points.append({"p": [float(v) for v in p], "width": width, "color": list(color)})

    def text(self, glyphs, s, origin, height, align="left", color=(0, 0, 0, 1)):
        for pl in glyphs.text(s, origin, height, align):
            self.polyline(pl, color)

    def rect(self, x, y, w, h, width=None, color=(0, 0, 0, 1)):
        self.polyline([[x, y, 0], [x + w, y, 0], [x + w, y + h, 0], [x, y + h, 0], [x, y, 0]], color, width)

    def arrow(self, a, b, head=0.18, color=(0, 0, 0, 1)):
        a, b = np.array(a, float), np.array(b, float)
        d = b - a; n = np.linalg.norm(d); d = d / n
        self.polyline([a.tolist(), b.tolist()], color)
        perp = np.array([-d[1], d[0], 0.0])
        self.polyline([(b - d * head + perp * head * 0.4).tolist(), b.tolist(), (b - d * head - perp * head * 0.4).tolist()], color)

    def dump(self, path):
        path.write_text(json.dumps({"name": self.name, "lines": self.lines, "polylines": self.polylines, "points": self.points}))


# =============================================================================
# Figure 2 network (section 2.1)
# =============================================================================

FIG2_BRANCHES = [(1, 6), (2, 7), (3, 8), (4, 9), (1, 4), (1, 2), (2, 3), (3, 4), (4, 5), (1, 5), (2, 5), (3, 5)]
FIG2_XY = {1: (-1, 0), 2: (0, -1), 3: (1, 0), 4: (0, 1), 5: (0, 0), 6: (-2, 0), 7: (0, -2), 8: (2, 0), 9: (0, 2)}

# =============================================================================
# Figure 5 network (section 5): topology traced from the printed figure.
# Nodes 1-61 free, 62-66 border corners (fixed), 67 apex (fixed).
# Plan positions are pixel positions read off the figure (y down), scaled below.
# =============================================================================

FIG5_PX = {
    1: (162, 368), 2: (150, 591), 3: (182, 345), 4: (165, 618), 5: (247, 230), 6: (190, 666), 7: (217, 611),
    8: (315, 405), 9: (360, 305), 10: (265, 198), 11: (430, 95), 12: (452, 105), 13: (537, 132), 14: (445, 368),
    15: (413, 448), 16: (357, 593), 17: (250, 773), 18: (412, 703), 19: (282, 836), 20: (445, 951), 21: (527, 921),
    22: (567, 909), 23: (595, 801), 24: (472, 678), 25: (455, 581), 26: (480, 477), 27: (519, 420), 28: (662, 172),
    29: (664, 346), 30: (665, 445), 31: (639, 451), 32: (599, 476), 33: (588, 492), 34: (571, 515), 35: (562, 536),
    36: (559, 568), 37: (561, 596), 38: (573, 632), 39: (592, 661), 40: (624, 683), 41: (652, 696), 42: (694, 703),
    43: (732, 821), 44: (737, 851), 45: (837, 230), 46: (787, 365), 47: (719, 448), 48: (749, 463), 49: (793, 506),
    50: (807, 546), 51: (809, 596), 52: (804, 628), 53: (752, 686), 54: (864, 239), 55: (964, 385), 56: (919, 526),
    57: (977, 514), 58: (919, 643), 59: (989, 653), 60: (992, 676), 61: (857, 811), 62: (97, 494), 63: (362, 981),
    64: (999, 763), 65: (954, 270), 66: (340, 68), 67: (685, 571),
}

BORDER = [62, 2, 4, 6, 17, 19, 63, 20, 21, 22, 44, 61, 64, 60, 59, 57, 55, 65, 54, 45, 28, 13, 12, 11, 66, 10, 5, 3, 1]
INNER_RING = [31, 30, 47, 48, 49, 50, 51, 52, 53, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32]
MIDDLE_RING = [27, 29, 46, 56, 58, 43, 23, 24, 25, 26]
SPOKES = [31, 33, 35, 37, 39, 41, 53, 51, 49, 47]                      # radial branches to the top (67)
RING_LINKS = [(30, 29), (32, 27), (34, 26), (36, 25), (38, 24), (40, 23), (42, 43), (52, 58), (50, 56), (48, 46)]
MIDDLE_OUT = [(27, 14), (29, 28), (46, 45), (56, 57), (58, 59), (43, 44), (23, 22), (24, 18), (25, 16), (26, 15)]
OUTER = [(1, 2), (4, 7), (6, 7), (7, 8), (3, 8), (8, 9), (5, 9), (9, 12), (9, 14), (13, 14), (10, 11), (8, 15),
         (14, 15), (15, 16), (7, 16), (16, 18), (17, 18), (18, 21), (19, 20), (61, 60), (59, 58), (57, 56),
         (46, 45), (28, 29), (54, 55)]


def fig5_branches():
    border = [(BORDER[i], BORDER[(i + 1) % len(BORDER)]) for i in range(len(BORDER))]
    inner = [(INNER_RING[i], INNER_RING[(i + 1) % len(INNER_RING)]) for i in range(len(INNER_RING))]
    middle = [(MIDDLE_RING[i], MIDDLE_RING[(i + 1) % len(MIDDLE_RING)]) for i in range(len(MIDDLE_RING))]
    spokes = [(n, 67) for n in SPOKES]
    seen, out = set(), []
    for e in border + inner + middle + spokes + RING_LINKS + MIDDLE_OUT + OUTER:
        key = tuple(sorted(e))
        if key not in seen:
            seen.add(key); out.append(e)
    return out, dict(border=border, spokes=spokes)


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
    """Plan drawing like the paper's figures 2 and 5: circles for nodes, numbers beside them."""
    th = np.linspace(0, 2 * np.pi, 25)
    for i, k in branches:
        sc.line([*XY[i - 1], 0], [*XY[k - 1], 0], sc.stroke * 1.6)
    for n in range(len(XY)):
        fx = (n + 1) in fixed_nodes
        r = node_r * (1.25 if fx else 1.0)
        circ = [[XY[n][0] + r * np.cos(t), XY[n][1] + r * np.sin(t), 0.0] for t in th]
        sc.polyline(circ)
        if fx:  # the paper draws fixed points with a heavier circle
            sc.polyline([[XY[n][0] + 0.8 * r * np.cos(t), XY[n][1] + 0.8 * r * np.sin(t), 0.0] for t in th])
        sc.text(gl, str(n + 1), [XY[n][0] + 1.3 * r, XY[n][1] + 0.9 * r, 0.0], text_h)
    if branch_numbers:
        for j, (i, k) in enumerate(branches):
            m = (np.array(XY[i - 1]) + np.array(XY[k - 1])) / 2
            circ = [[m[0] + node_r * 1.1 * np.cos(t), m[1] + node_r * 1.1 * np.sin(t), 0.0] for t in th]
            sc.polyline(circ)
            sc.text(gl, str(j + 1), [m[0], m[1] - 0.35 * text_h, 0.0], text_h * 0.8, "center")


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
    labelled_graph(sc, gl, FIG2_BRANCHES, XY2, {6, 7, 8, 9}, 0.09, 0.22, branch_numbers=True)
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

    # ------------------------------------------------------------------ figure 5: graph of the example
    branches, groups = fig5_branches()
    n_nodes = 67
    scale = 0.04                                   # metres per figure pixel: radial branches come out ~5 m
    xy = np.array([FIG5_PX[n] for n in range(1, 68)], dtype=float)
    xy[:, 1] = -xy[:, 1]
    xy = (xy - xy[66]) * scale                     # apex 67 at the plan origin
    sc = Scene("fig5_graph", stroke=0.05)
    labelled_graph(sc, gl, branches, xy.tolist(), set(range(62, 68)), 0.38, 0.9)
    sc.dump(out / "fig5_graph.json")
    layout["fig5"] = {"panels": [["fig5_graph.json", [0, 0, 0]]], "views": ["top"], "caption": "Fig. 5. Graph of the first example."}
    deg = np.bincount(np.array(branches).ravel())[1:]
    print("figure 5:", n_nodes, "nodes,", len(branches), "branches; apex degree", deg[66], "; corner degrees", deg[61:66].tolist())

    # ------------------------------------------------------------------ figures 1, 6-9: the example net
    C_s = branch_node_matrix(branches, n_nodes)
    free = list(range(61)); fixed = list(range(61, 67))
    border_set = {tuple(sorted(b)) for b in groups["border"]}
    is_border = np.array([tuple(sorted(e)) in border_set for e in branches])
    is_spoke = np.array([67 in e for e in branches])
    touches_border = np.array([any(n in BORDER for n in e) for e in branches])

    def q_vec(q_border=100.0, q_spoke=0.5, q_other=1.0):
        q = np.full(len(branches), q_other); q[is_border] = q_border; q[is_spoke] = q_spoke
        return q

    apex_h = 16.0
    def fixed_xyz(apex_dx=0.0, apex_dy=0.0):
        X = np.zeros((6, 3)); X[:, :2] = xy[61:67]
        X[5, 0] += apex_dx; X[5, 1] += apex_dy; X[5, 2] = apex_h
        return X
    p = np.zeros((n_nodes, 3)); p[free, 2] = -0.4          # "a small vertical load in each node"
    fixed_nodes = {62, 63, 64, 65, 66, 67}

    panels = {}
    X61 = fd_solve(C_s, free, fixed, fixed_xyz(), q_vec(), p)[0]
    panels["fig6"] = [X61, fd_solve(C_s, free, fixed, fixed_xyz(6, 2), q_vec(), p)[0],
                      fd_solve(C_s, free, fixed, fixed_xyz(12, 4), q_vec(), p)[0]]
    panels["fig7"] = [fd_solve(C_s, free, fixed, fixed_xyz(), q_vec(q_spoke=qs), p)[0] for qs in (1.0, 0.7, 0.3)]
    panels["fig8"] = [fd_solve(C_s, free, fixed, fixed_xyz(), q_vec(q_border=qb), p)[0] for qb in (10, 5, 1)]

    base_l = fd_solve(C_s, free, fixed, fixed_xyz(), q_vec(), p)[2]
    inner_branches = [j for j in range(len(branches)) if not touches_border[j]]
    spoke_j = [j for j in inner_branches if is_spoke[j]]
    ring_j = [j for j in inner_branches if not is_spoke[j]]
    def dist_case(l_spoke, ring_factor, kmax=60):
        cons = [(j, l_spoke) for j in spoke_j] + [(j, base_l[j] * ring_factor) for j in ring_j]
        X, L, S, Q, hist = fd_constrained(C_s, free, fixed, fixed_xyz(), q_vec(), p, length_cons=cons, kmax=kmax)
        return X, hist, L, Q
    X91, h91, *_ = dist_case(6.0, 1.25, kmax=6)      # rings too long: unattainable, the damped sequence is stopped
    X92, h92, L92, Q92 = dist_case(6.0, 0.85)        # rings shortened: attainable
    X93, h93, L93, Q93 = dist_case(4.5, 0.70)        # another uniform prescription
    print("fig 9: 9.1 max|l-lv| %.2e after %d it (stopped)  9.2 %.2e (%d it)  9.3 %.2e (%d it); q>0: %s %s"
          % (h91[-1], len(h91), h92[-1], len(h92), h93[-1], len(h93), bool((Q92 > 0).all()), bool((Q93 > 0).all())))
    panels["fig9"] = [X91, X92, X93]

    # ------------------------------------------------------------------ figure 10: 112 identical bars
    n = 8
    gid = {(i, k): i * n + k + 1 for i in range(n) for k in range(n)}
    g_branches = []
    for i in range(n):
        for k in range(n):
            if k + 1 < n: g_branches.append((gid[i, k], gid[i, k + 1]))
            if i + 1 < n: g_branches.append((gid[i, k], gid[i + 1, k]))
    assert len(g_branches) == 112
    corners = [gid[0, 0], gid[0, n - 1], gid[n - 1, n - 1], gid[n - 1, 0]]
    g_fixed = [c - 1 for c in corners]; g_free = [i for i in range(n * n) if i not in g_fixed]
    Cg = branch_node_matrix(g_branches, n * n)
    flat = np.array([[k, i, 0.0] for i in range(n) for k in range(n)], dtype=float)      # 1 m bars
    on_edge = lambda v: ((v - 1) // n in (0, n - 1), (v - 1) % n in (0, n - 1))
    g_border = np.array([(on_edge(a)[0] and on_edge(b)[0]) or (on_edge(a)[1] and on_edge(b)[1]) for a, b in g_branches])
    bar_w = 0.15
    degg = np.bincount(np.array(g_branches).ravel())[1:]
    pw = np.zeros((n * n, 3)); pw[:, 2] = -0.5 * bar_w * degg            # half of every bar's weight at each end
    anchors = flat[g_fixed].copy(); anchors[:, :2] = (anchors[:, :2] - 3.5) * 0.8 + 3.5
    X101, L101, S101, Q101, h101 = fd_constrained(Cg, g_free, g_fixed, anchors, np.ones(112), pw,
                                                   length_cons=[(j, 1.0) for j in range(112)], kmax=120)
    print("fig 10.1: bar length error %.2e after %d it; bar forces %.3f..%.3f (all tension: %s)"
          % (h101[-1], len(h101), S101.min(), S101.max(), bool((S101 > 0).all())))
    anchors2 = anchors.copy(); anchors2[[0, 2], 2] = 3.0
    q102 = np.where(g_border, 10.0, 1.0)
    X102, _, L102, S102, *_ = fd_solve(Cg, g_free, g_fixed, anchors2, q102, np.zeros_like(pw))
    # "an equidistant net in the inner region and a constant force over all branches connected with the border"
    touches = lambda e: any(on_edge(v)[0] or on_edge(v)[1] for v in e)
    inner_j = [j for j, e in enumerate(g_branches) if not g_border[j] and not touches(e)]
    link_j = [j for j, e in enumerate(g_branches) if not g_border[j] and touches(e)]
    X103, L103, S103, Q103, h103 = fd_constrained(Cg, g_free, g_fixed, anchors2, q102, np.zeros_like(pw),
                                                   length_cons=[(j, L102[inner_j].mean()) for j in inner_j],
                                                   force_cons=[(j, S102[link_j].mean()) for j in link_j], kmax=120)
    print("fig 10.3: mixed conditions residual %.2e after %d it" % (h103[-1], len(h103)))
    panels["fig10"] = [X101, X102, X103]

    # ------------------------------------------------------------------ scenes for figures 6-10 (three panels in a row)
    captions = {"fig6": "Fig. 6. Different fixed points.",
                "fig7": "Fig. 7. Global changes in the force densities and lengthening of the radial branches.",
                "fig8": "Fig. 8. Global changes in the force densities of the main cables.",
                "fig9": "Fig. 9. Additional distance conditions.",
                "fig10": "Fig. 10. Hanging and prestressed net with the same structure."}
    for name, Xs in panels.items():
        brs = g_branches if name == "fig10" else branches
        fx = set(corners) if name == "fig10" else fixed_nodes
        span = 9.0 if name == "fig10" else 46.0
        items = []
        for c, X in enumerate(Xs):
            sc = Scene(f"{name}_{c + 1}")
            draw_net(sc, brs, X, fx, width=NET_W * (0.25 if name == "fig10" else 1.0), node_w=NODE_W * (0.3 if name == "fig10" else 1.0))
            sc.dump(out / f"{name}_{c + 1}.json")
            items.append([f"{name}_{c + 1}.json", [c * span, 0, 0]])
        layout[name] = {"panels": items, "views": ["persp", "top"], "caption": captions[name]}
    # figure 1: two perspective views of the prestressed net (fig. 6.1)
    sc = Scene("fig1_net"); draw_net(sc, branches, X61, fixed_nodes); sc.dump(out / "fig1_net.json")
    layout["fig1"] = {"panels": [["fig1_net.json", [0, 0, 0]]], "views": ["persp", "persp2"],
                      "caption": "Fig. 1. Views of a prestressed net."}
    (out / "layout.json").write_text(json.dumps(layout, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "viewer_scenes/json")
    main(ap.parse_args().out)
