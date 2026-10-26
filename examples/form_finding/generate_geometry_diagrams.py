"""Generate clean, minimal geometric figures for compas_fd.md (no text-box clutter).

Run:
    /opt/anaconda3/bin/python examples/form_finding/generate_geometry_diagrams.py
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import proj3d

OUT = Path(__file__).resolve().parents[2] / "knowledge/04_form_finding/images"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
    "mathtext.fontset": "dejavusans",
    "axes.edgecolor": "#334155",
    "axes.linewidth": 0.9,
})

C_FREE = "#1d4ed8"
C_FREE_FILL = "#dbeafe"
C_FIXED = "#b91c1c"
C_FIXED_FILL = "#fee2e2"
C_ANCHOR_CAB = "#dc2626"
C_RING_CAB = "#2563eb"
C_SPOKE_CAB = "#059669"
C_LOAD = "#d97706"
C_DARK = "#0f172a"
C_MUTED = "#475569"


class Arrow3D(FancyArrowPatch):
    def __init__(self, xs, ys, zs, *args, **kwargs):
        super().__init__((0, 0), (0, 0), *args, **kwargs)
        self._verts3d = xs, ys, zs

    def do_3d_projection(self, renderer=None):
        xs3d, ys3d, zs3d = self._verts3d
        xs, ys, zs = proj3d.proj_transform(xs3d, ys3d, zs3d, self.axes.M)
        self.set_positions((xs[0], ys[0]), (xs[1], ys[1]))
        return np.min(zs)


BRANCHES = [
    (1, 6), (2, 7), (3, 8), (4, 9),   # 1-4: anchor cables
    (1, 4), (1, 2), (2, 3), (3, 4),   # 5-8: inner ring
    (4, 5), (1, 5), (2, 5), (3, 5),   # 9-12: spokes to center node 5
]

XY_PLAN = {
    1: (-0.9, 0.0),
    2: (0.0, 0.9),
    3: (0.9, 0.0),
    4: (0.0, -0.9),
    5: (0.0, 0.0),
    6: (-2.0, 0.0),
    7: (0.0, 2.0),
    8: (2.0, 0.0),
    9: (0.0, -2.0),
}

XYZ_SOLVED = {
    1: np.array([-0.800, 0.000, 0.045]),
    2: np.array([0.000, 0.800, 0.330]),
    3: np.array([0.800, 0.000, 0.045]),
    4: np.array([0.000, -0.800, 0.330]),
    5: np.array([0.000, 0.000, 0.063]),
    6: np.array([-2.000, 0.000, 0.000]),
    7: np.array([0.000, 2.000, 1.000]),
    8: np.array([2.000, 0.000, 0.000]),
    9: np.array([0.000, -2.000, 1.000]),
}

BRANCH_LABEL_POS = {
    1: (-1.45, 0.26),
    2: (0.28, 1.45),
    3: (1.45, 0.26),
    4: (0.28, -1.45),
    5: (-0.64, -0.64),
    6: (-0.64, 0.64),
    7: (0.64, 0.64),
    8: (0.64, -0.64),
    9: (-0.22, -0.44),
    10: (-0.44, 0.20),
    11: (0.22, 0.44),
    12: (0.44, -0.20),
}


def draw_net_plan(ax, coords=XY_PLAN, show_branch_labels=True, highlight_node=None, title="", xlim=(-2.5, 2.5), ylim=(-2.5, 2.5)):
    for idx, (i, k) in enumerate(BRANCHES, start=1):
        p1, p2 = np.array(coords[i]), np.array(coords[k])
        col = C_ANCHOR_CAB if idx <= 4 else (C_RING_CAB if idx <= 8 else C_SPOKE_CAB)
        lw = 2.4 if idx <= 4 else 2.0
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=col, lw=lw, zorder=2)
        mid = 0.52 * p1 + 0.48 * p2
        d = p2 - p1
        ax.annotate(
            "", xy=(mid[0] + 0.12 * d[0], mid[1] + 0.12 * d[1]),
            xytext=(mid[0] - 0.12 * d[0], mid[1] - 0.12 * d[1]),
            arrowprops=dict(arrowstyle="-|>", color=col, lw=1.5, mutation_scale=12),
            zorder=3,
        )
        if show_branch_labels:
            lx, ly = BRANCH_LABEL_POS[idx]
            ax.text(lx, ly, f"$b_{{{idx}}}$", fontsize=10.5, color=col, fontweight="bold", ha="center", va="center", zorder=4)

    for node, (x, y) in coords.items():
        is_free = node <= 5
        ring_ec = "#f59e0b" if node == highlight_node else (C_FREE if is_free else C_FIXED)
        ring_lw = 3.2 if node == highlight_node else 2.0
        if is_free:
            ax.scatter([x], [y], s=320, c=C_FREE_FILL, edgecolors=ring_ec, linewidths=ring_lw, zorder=5)
            ax.text(x, y, f"{node}", fontsize=11, fontweight="bold", color=C_FREE, ha="center", va="center", zorder=6)
        else:
            ax.scatter([x], [y], s=340, marker="s", c=C_FIXED_FILL, edgecolors=ring_ec, linewidths=ring_lw, zorder=5)
            ax.text(x, y, f"{node}", fontsize=11, fontweight="bold", color=C_FIXED, ha="center", va="center", zorder=6)

    ax.set_aspect("equal")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=11.5, fontweight="bold", color=C_DARK, pad=8)


# =============================================================================
# FIGURE 1: Linkwitz Physical Intuition (3 clean geometric views, no text boxes)
# =============================================================================
def fig_linkwitz_intuition():
    fig = plt.figure(figsize=(13.5, 4.2), dpi=160, facecolor="white")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.05, 1.05], wspace=0.18, left=0.02, right=0.98, top=0.84, bottom=0.06)

    # Panel 1: Anticlastic saddle
    ax1 = fig.add_subplot(gs[0], projection="3d")
    ax1.set_facecolor("white")
    t = np.linspace(-1, 1, 40)
    X, Y = np.meshgrid(np.linspace(-1, 1, 13), np.linspace(-1, 1, 13))
    Z = 0.45 * (Y**2 - X**2) + 0.5
    ax1.plot_wireframe(X, Y, Z, color="#cbd5e1", linewidth=0.6, alpha=0.55)
    ax1.plot(np.zeros_like(t), t, 0.45 * t**2 + 0.5, color=C_FIXED, lw=3.2)
    ax1.plot(t, np.zeros_like(t), -0.45 * t**2 + 0.5, color=C_FREE, lw=3.2)
    ax1.scatter([0], [0], [0.5], color=C_DARK, s=75, zorder=10)
    ax1.add_artist(Arrow3D([0, 0], [0, 0], [0.5, 0.88], mutation_scale=13, lw=2.2, arrowstyle="-|>", color=C_FIXED))
    ax1.add_artist(Arrow3D([0, 0], [0, 0], [0.5, 0.12], mutation_scale=13, lw=2.2, arrowstyle="-|>", color=C_FREE))
    ax1.text(0.16, 0.10, 0.52, "Node 5", fontsize=11.0, fontweight="bold", color=C_DARK)
    ax1.text(0.0, 0.75, 1.06, "High anchors 7, 9 (pull up)", fontsize=10, fontweight="bold", color=C_FIXED, ha="center")
    ax1.text(-0.75, 0.0, -0.18, "Low anchors 6, 8 (pull down)", fontsize=10, fontweight="bold", color=C_FREE, ha="center")
    ax1.set_xlim(-1.1, 1.1); ax1.set_ylim(-1.1, 1.1); ax1.set_zlim(-0.15, 1.1)
    ax1.set_xticks([]); ax1.set_yticks([]); ax1.set_zticks([])
    ax1.view_init(elev=22, azim=-48)
    ax1.set_title("1. Anticlastic Saddle (9-Node Net)", fontsize=11.5, fontweight="bold", color=C_DARK, pad=6)

    # Panel 2: Node 1 with its 4 neighbors (Anchor 6, Node 2, Node 5, Node 4)
    ax2 = fig.add_subplot(gs[1])
    ax2.set_xlim(-2.4, 2.4)
    ax2.set_ylim(-2.1, 2.2)
    ax2.set_aspect("equal")
    ax2.axis("off")
    ax2.set_title("2. Node 1 Equilibrium ($q$-Weighted Average)", fontsize=11.5, fontweight="bold", color=C_DARK, pad=6)

    p0 = np.array([0.0, 0.0])
    neighbors = [
        ("Anchor 6", np.array([-1.75, 0.30]), "$q_1$", C_FIXED, (-1.75, 0.72), (-0.95, 0.42), "s", C_FIXED_FILL),
        ("Node 2", np.array([0.25, 1.55]), "$q_6$", C_FREE, (0.25, 1.95), (0.48, 0.85), "o", C_FREE_FILL),
        ("Node 5", np.array([1.75, -0.10]), "$q_{10}$", C_FREE, (1.75, 0.32), (0.95, 0.18), "o", C_FREE_FILL),
        ("Node 4", np.array([-0.25, -1.45]), "$q_5$", C_FREE, (-0.25, -1.90), (-0.58, -0.82), "o", C_FREE_FILL),
    ]
    for name, pk, qlab, col, npos, bpos, mkr, mfill in neighbors:
        ax2.plot([p0[0], pk[0]], [p0[1], pk[1]], color="#64748b", lw=2.2, zorder=2)
        d = pk - p0
        ax2.annotate(
            "", xy=(p0[0] + 0.45 * d[0], p0[1] + 0.45 * d[1]), xytext=p0,
            arrowprops=dict(arrowstyle="-|>", color=col, lw=2.5, mutation_scale=13), zorder=4,
        )
        ax2.text(bpos[0], bpos[1], qlab, fontsize=11, color=col, fontweight="bold", ha="center")
        ax2.scatter([pk[0]], [pk[1]], s=240, marker=mkr, c=mfill, edgecolors=col, linewidths=2.0, zorder=5)
        ax2.text(npos[0], npos[1], name, fontsize=10.5, fontweight="bold", color=C_DARK, ha="center")

    ax2.annotate(
        "", xy=(0.35, -0.85), xytext=p0,
        arrowprops=dict(arrowstyle="-|>", color=C_LOAD, lw=2.6, mutation_scale=13), zorder=4,
    )
    ax2.text(0.80, -0.78, "Load $p_1$", fontsize=10.5, fontweight="bold", color=C_LOAD)
    ax2.scatter([p0[0]], [p0[1]], s=300, c=C_FREE_FILL, edgecolors=C_FREE, linewidths=2.4, zorder=6)
    ax2.text(-0.55, 0.25, "Node 1", fontsize=11.0, fontweight="bold", color=C_FREE)

    # Panel 3: Materialization (Cutting Length l_0 vs Stressed Length l)
    ax3 = fig.add_subplot(gs[2])
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0.5, 5.5)
    ax3.axis("off")
    ax3.set_title("3. Cutting Length $l_0$ vs. Stressed $l$", fontsize=11.5, fontweight="bold", color=C_DARK, pad=6)

    y_top = 4.1
    ax3.plot([1.0, 6.2], [y_top, y_top], color="#475569", lw=6, solid_capstyle="round")
    ax3.scatter([1.0, 6.2], [y_top, y_top], s=110, color="#334155", zorder=4)
    ax3.annotate("", xy=(6.2, y_top + 0.45), xytext=(1.0, y_top + 0.45), arrowprops=dict(arrowstyle="<->", color="#334155", lw=1.6))
    ax3.text(3.6, y_top + 0.72, "Unstressed cutting length $l_{0,j}$", fontsize=10.5, fontweight="bold", color="#334155", ha="center")

    y_bot = 2.1
    ax3.plot([1.0, 6.2], [y_bot, y_bot], color=C_FREE, lw=5.5, solid_capstyle="butt")
    ax3.plot([6.2, 8.8], [y_bot, y_bot], color=C_ANCHOR_CAB, lw=5.5, ls="--")
    ax3.scatter([1.0], [y_bot], s=180, c=C_FREE_FILL, edgecolors=C_FREE, lw=2.2, zorder=5)
    ax3.scatter([8.8], [y_bot], s=190, marker="s", c=C_FIXED_FILL, edgecolors=C_FIXED, lw=2.2, zorder=5)

    ax3.annotate("", xy=(8.8, y_bot + 0.45), xytext=(6.2, y_bot + 0.45), arrowprops=dict(arrowstyle="<->", color=C_ANCHOR_CAB, lw=1.6))
    ax3.text(7.5, y_bot + 0.72, "Stretch $e_j$", fontsize=10.5, fontweight="bold", color=C_ANCHOR_CAB, ha="center")

    ax3.annotate("", xy=(8.8, y_bot - 0.55), xytext=(1.0, y_bot - 0.55), arrowprops=dict(arrowstyle="<->", color=C_FREE, lw=1.8))
    ax3.text(4.9, y_bot - 1.05, "Stressed length $l_j$  ($s_j = q_j l_j$)", fontsize=10.5, fontweight="bold", color=C_FREE, ha="center")

    out_path = OUT / "fd_linkwitz_intuition.png"
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    print("Saved", out_path)


# =============================================================================
# FIGURE 2: Part A — Topology & Operators C vs C^T
# =============================================================================
def fig_sec_a_topology():
    fig = plt.figure(figsize=(13.5, 4.3), dpi=160, facecolor="white")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.0, 1.0], wspace=0.14, left=0.02, right=0.98, top=0.84, bottom=0.04)

    # Panel 1: Directed Network Graph
    ax1 = fig.add_subplot(gs[0])
    draw_net_plan(
        ax1, show_branch_labels=True,
        title="1. Topology ($n=5$ free, $n_f=4$ fixed)",
    )

    # Panel 2: Operator C_s = [C | C_f]
    ax2 = fig.add_subplot(gs[1])
    draw_net_plan(
        ax2, show_branch_labels=False,
        title="2. Row $j$ of $C_s$: Span $u_j = x_i - x_k$",
    )
    p1, p6, p2 = np.array(XY_PLAN[1]), np.array(XY_PLAN[6]), np.array(XY_PLAN[2])
    ax2.plot([p1[0], p6[0]], [p1[1], p6[1]], color="#f59e0b", lw=5.0, zorder=3)
    ax2.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#10b981", lw=5.0, zorder=3)
    ax2.text(-1.45, 0.52, "$u_1 = x_1 - x_6$", fontsize=11, fontweight="bold", color="#b45309", ha="center")
    ax2.text(-0.95, 1.15, "$u_6 = x_1 - x_2$", fontsize=11, fontweight="bold", color="#047857", ha="center")

    # Panel 3: Operator C^T
    ax3 = fig.add_subplot(gs[2])
    draw_net_plan(
        ax3, show_branch_labels=False, highlight_node=1,
        title="3. Row 1 of $C^T$: Sums Forces at Node 1",
    )
    label_offsets = {
        1: (-1.45, 0.42),
        6: (-0.78, 0.82),
        5: (-0.78, -0.82),
        10: (-0.36, -0.26),
    }
    for b_idx, nbr in [(1, 6), (5, 4), (6, 2), (10, 5)]:
        pa, pb = np.array(XY_PLAN[1]), np.array(XY_PLAN[nbr])
        d = pb - pa
        ax3.annotate(
            "", xy=(pa[0] + 0.62 * d[0], pa[1] + 0.62 * d[1]), xytext=(pa[0] + 0.18 * d[0], pa[1] + 0.18 * d[1]),
            arrowprops=dict(arrowstyle="-|>", color="#d97706", lw=3.0, mutation_scale=13), zorder=7,
        )
        lx, ly = label_offsets[b_idx]
        ax3.text(lx, ly, f"$F_{{x,{b_idx}}}$", fontsize=10.5, fontweight="bold", color="#b45309", ha="center", zorder=8)

    out_path = OUT / "fd_sec_a_topology_split.png"
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    print("Saved", out_path)


# =============================================================================
# FIGURE 3: Section B.2 (Eq. 1) — Coordinate Differences (u, v, w) & Length l
# =============================================================================
def fig_sec_b2_uvw_geometry():
    fig = plt.figure(figsize=(12.5, 4.3), dpi=160, facecolor="white")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.1, 1.0], wspace=0.16, left=0.02, right=0.98, top=0.84, bottom=0.06)

    # Left Panel: 3D right box of a single cable j
    ax1 = fig.add_subplot(gs[0], projection="3d")
    ax1.set_facecolor("white")

    pi = np.array([0.0, 0.8, 0.30])
    pk = np.array([1.6, 2.0, 1.00])
    px = np.array([pk[0], pi[1], pi[2]])
    pxy = np.array([pk[0], pk[1], pi[2]])

    ax1.plot([pi[0], pk[0]], [pi[1], pk[1]], [pi[2], pk[2]], color=C_ANCHOR_CAB, lw=3.8, zorder=5)
    ax1.add_artist(Arrow3D([pi[0], pk[0]], [pi[1], pk[1]], [pi[2], pk[2]], mutation_scale=15, lw=2.5, arrowstyle="-|>", color=C_ANCHOR_CAB))

    ax1.plot([pi[0], px[0]], [pi[1], px[1]], [pi[2], px[2]], color="#2563eb", lw=2.6, ls="--")
    ax1.plot([px[0], pxy[0]], [px[1], pxy[1]], [px[2], pxy[2]], color="#059669", lw=2.6, ls="--")
    ax1.plot([pxy[0], pk[0]], [pxy[1], pk[1]], [pxy[2], pk[2]], color="#d97706", lw=2.6, ls="--")

    ax1.scatter([pi[0]], [pi[1]], [pi[2]], s=200, c=C_FREE_FILL, edgecolors=C_FREE, lw=2.2, zorder=8)
    ax1.scatter([pk[0]], [pk[1]], [pk[2]], s=210, marker="s", c=C_FIXED_FILL, edgecolors=C_FIXED, lw=2.2, zorder=8)

    ax1.text(pi[0] - 0.15, pi[1] - 0.22, pi[2] + 0.10, "Node $i$", fontsize=11, fontweight="bold", color=C_FREE, ha="right")
    ax1.text(pk[0] - 0.05, pk[1] + 0.10, pk[2] + 0.08, "Node $k$", fontsize=11, fontweight="bold", color=C_FIXED, ha="left")

    ax1.text(0.80, pi[1] - 0.25, pi[2] - 0.08, "$u_j = x_i - x_k$", fontsize=11, fontweight="bold", color="#2563eb", ha="center")
    ax1.text(pk[0] + 0.15, 1.40, pi[2] - 0.04, "$v_j = y_i - y_k$", fontsize=11, fontweight="bold", color="#059669", ha="left")
    ax1.text(pk[0] + 0.12, pk[1] + 0.05, 0.65, "$w_j = z_i - z_k$", fontsize=11, fontweight="bold", color="#d97706", ha="left")
    ax1.text(0.55, 1.35, 0.82, "$l_j = \\sqrt{u_j^2 + v_j^2 + w_j^2}$", fontsize=11, fontweight="bold", color=C_ANCHOR_CAB, ha="center")

    ax1.set_xlim(-0.35, 2.15); ax1.set_ylim(0.45, 2.35); ax1.set_zlim(0.15, 1.18)
    ax1.set_xticks([]); ax1.set_yticks([]); ax1.set_zticks([])
    ax1.view_init(elev=22, azim=-52)
    ax1.set_title("1. Single Cable $j$: Box Sides $(u_j, v_j, w_j)$ & Length $l_j$", fontsize=11.5, fontweight="bold", color=C_DARK, pad=6)

    # Right Panel: Flat Trial Lengths on the 12-branch net
    ax2 = fig.add_subplot(gs[1])
    draw_net_plan(
        ax2, show_branch_labels=False,
        title="2. Flat Trial Lengths $l_j$ on the 12-Cable Net",
    )
    ax2.text(-1.45, 0.30, "$l_1 = 1$", fontsize=10.5, fontweight="bold", color=C_ANCHOR_CAB, ha="center")
    ax2.text(1.45, 0.30, "$l_3 = 1$", fontsize=10.5, fontweight="bold", color=C_ANCHOR_CAB, ha="center")
    ax2.text(0.58, 1.45, "$l_2 = \\sqrt{10}$", fontsize=10.5, fontweight="bold", color=C_ANCHOR_CAB, ha="center")
    ax2.text(0.58, -1.45, "$l_4 = \\sqrt{10}$", fontsize=10.5, fontweight="bold", color=C_ANCHOR_CAB, ha="center")
    ax2.text(-0.78, 0.68, "$l_6 = \\sqrt{2}$", fontsize=10.5, fontweight="bold", color=C_RING_CAB, ha="center")
    ax2.text(0.78, 0.68, "$l_7 = \\sqrt{2}$", fontsize=10.5, fontweight="bold", color=C_RING_CAB, ha="center")
    ax2.text(-0.78, -0.68, "$l_5 = \\sqrt{2}$", fontsize=10.5, fontweight="bold", color=C_RING_CAB, ha="center")
    ax2.text(0.78, -0.68, "$l_8 = \\sqrt{2}$", fontsize=10.5, fontweight="bold", color=C_RING_CAB, ha="center")
    ax2.text(0.0, -2.35, "Spokes $l_{9..12} = 1$", fontsize=10.5, fontweight="bold", color=C_SPOKE_CAB, ha="center")

    out_path = OUT / "fd_sec_b2_uvw_geometry.png"
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    print("Saved", out_path)


# =============================================================================
# FIGURE 4: Section B.3 (Eq. 2) — Why a Flat Trial Net Fails Vertical Equilibrium
# =============================================================================
def fig_sec_b3_nonlinear_stages():
    fig = plt.figure(figsize=(10.5, 3.8), dpi=160, facecolor="white")
    ax = fig.add_subplot(111)
    ax.set_xlim(-2.4, 2.4)
    ax.set_ylim(-0.85, 1.45)
    ax.axis("off")
    ax.set_title("Side Elevation of Flat Trial Net ($z_1..z_5 = 0$): Flat Spokes Have Zero Vertical Pull ($F_z = 0$)", fontsize=11.5, fontweight="bold", color=C_DARK, pad=6)

    ax.plot([-2.0, -0.9, 0.0, 0.9, 2.0], [1.0, 0.0, 0.0, 0.0, 1.0], color=C_RING_CAB, lw=2.8, zorder=2)
    ax.plot([-2.0, -0.9], [1.0, 0.0], color=C_ANCHOR_CAB, lw=3.2, zorder=3)
    ax.plot([0.9, 2.0], [0.0, 1.0], color=C_ANCHOR_CAB, lw=3.2, zorder=3)

    ax.scatter([-2.0, 2.0], [1.0, 1.0], s=240, marker="s", c=C_FIXED_FILL, edgecolors=C_FIXED, lw=2.2, zorder=5)
    ax.text(-2.0, 1.18, "Anchor 9 ($z_9 = 1$ m)", fontsize=10.5, fontweight="bold", color=C_FIXED, ha="center")
    ax.text(2.0, 1.18, "Anchor 7 ($z_7 = 1$ m)", fontsize=10.5, fontweight="bold", color=C_FIXED, ha="center")

    for x_n, lbl, ez_val in [(-0.9, "Node 4", "$e_{z,4} = +0.184$ kN"), (0.0, "Node 5", "$e_{z,5} = +0.500$ kN"), (0.9, "Node 2", "$e_{z,2} = +0.184$ kN")]:
        ax.scatter([x_n], [0.0], s=240, c=C_FREE_FILL, edgecolors=C_FREE, lw=2.2, zorder=5)
        ax.annotate("", xy=(x_n, -0.45), xytext=(x_n, -0.05), arrowprops=dict(arrowstyle="-|>", color=C_LOAD, lw=2.6, mutation_scale=13))
        ax.text(x_n, -0.65, f"$p_z = -0.5$ kN\n({ez_val})", fontsize=10, fontweight="bold", color=C_LOAD, ha="center")
        ax.text(x_n, 0.16, lbl, fontsize=10.5, fontweight="bold", color=C_FREE, ha="center")

    ax.text(0.0, 0.60, "Flat inner cables ($w_5..w_{12} = 0$) $\\Rightarrow F_z = 0$", fontsize=11, fontweight="bold", color=C_ANCHOR_CAB, ha="center")

    out_path = OUT / "fd_sec_b3_nonlinear_stages.png"
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    print("Saved", out_path)


# =============================================================================
# FIGURE 5: Section C.1 (Eqs. 4–6) — The Force Density Trick & Role of u
# =============================================================================
def fig_sec_c1_force_density_trick():
    fig = plt.figure(figsize=(12.5, 4.0), dpi=160, facecolor="white")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.05, 1.05], wspace=0.18, left=0.03, right=0.97, top=0.83, bottom=0.08)

    # Panel 1: Direction cosine projection (Before Trick)
    ax1 = fig.add_subplot(gs[0])
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0.8, 6.8)
    ax1.axis("off")
    ax1.set_title("1. Direction Cosine Projection: $F_{x,j} = s_j (u_j / l_j)$", fontsize=11.5, fontweight="bold", color=C_DARK, pad=6)

    p_start = np.array([1.5, 2.4])
    p_end = np.array([8.3, 5.6])
    p_corner = np.array([8.3, 2.4])
    ax1.plot([p_start[0], p_corner[0]], [p_start[1], p_corner[1]], color=C_FREE, lw=2.2, ls="--")
    ax1.plot([p_corner[0], p_end[0]], [p_corner[1], p_end[1]], color="#d97706", lw=2.2, ls="--")
    ax1.plot([p_start[0], p_end[0]], [p_start[1], p_end[1]], color="#64748b", lw=2.6)

    d = p_end - p_start
    ax1.annotate("", xy=(p_start[0] + 0.55 * d[0], p_start[1] + 0.55 * d[1]), xytext=p_start, arrowprops=dict(arrowstyle="-|>", color=C_ANCHOR_CAB, lw=3.4, mutation_scale=15))
    ax1.annotate("", xy=(p_start[0] + 0.55 * d[0], p_start[1]), xytext=p_start, arrowprops=dict(arrowstyle="-|>", color=C_FREE, lw=3.2, mutation_scale=14))

    ax1.scatter([p_start[0]], [p_start[1]], s=220, c=C_FREE_FILL, edgecolors=C_FREE, lw=2.2, zorder=5)
    ax1.scatter([p_end[0]], [p_end[1]], s=220, marker="s", c=C_FIXED_FILL, edgecolors=C_FIXED, lw=2.2, zorder=5)
    ax1.text(p_start[0] - 0.2, p_start[1] + 0.55, "Node $i$ ($x_i$)", fontsize=11, fontweight="bold", color=C_FREE, ha="center")
    ax1.text(p_end[0], p_end[1] + 0.45, "Node $k$ ($x_k$)", fontsize=11, fontweight="bold", color=C_FIXED, ha="center")
    ax1.text(3.3, 2.75, "$\\alpha_j$", fontsize=11.5, fontweight="bold", color=C_DARK)
    ax1.text(4.0, 4.55, "Tension $s_j$\n(length $l_j$)", fontsize=10.5, fontweight="bold", color=C_ANCHOR_CAB, ha="center")
    ax1.text(4.9, 1.75, "Span $u_j = x_i - x_k$", fontsize=11, fontweight="bold", color=C_FREE, ha="center")
    ax1.text(4.9, 1.05, "$\\cos\\alpha_j = u_j / l_j$", fontsize=11, fontweight="bold", color=C_DARK, ha="center")
    ax1.text(8.7, 4.0, "$w_j$", fontsize=11, fontweight="bold", color="#d97706")

    # Panel 2: Force Density Substitution q_j = s_j / l_j
    ax2 = fig.add_subplot(gs[1])
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0.8, 6.8)
    ax2.axis("off")
    ax2.set_title("2. Force Density $q_j = s_j / l_j$: Linear Pull $F_{x,j} = q_j u_j$", fontsize=11.5, fontweight="bold", color=C_DARK, pad=6)

    ax2.text(5.0, 5.4, "$F_{x,j} = s_j \\frac{u_j}{l_j} = (q_j l_j) \\frac{u_j}{l_j} = q_j u_j = q_j(x_i - x_k)$", fontsize=12, fontweight="bold", color=C_DARK, ha="center")

    ax2.plot([1.2, 8.8], [3.4, 3.4], color=C_SPOKE_CAB, lw=4.5)
    ax2.scatter([1.2], [3.4], s=220, c=C_FREE_FILL, edgecolors=C_FREE, lw=2.2, zorder=5)
    ax2.scatter([8.8], [3.4], s=220, marker="s", c=C_FIXED_FILL, edgecolors=C_FIXED, lw=2.2, zorder=5)
    ax2.text(1.2, 4.10, "Node $i$ ($x_i$)", fontsize=11, fontweight="bold", color=C_FREE, ha="center")
    ax2.text(8.8, 4.10, "Node $k$ ($x_k$)", fontsize=11, fontweight="bold", color=C_FIXED, ha="center")
    ax2.text(5.0, 3.78, "Stiffness $q_j$ (kN/m)", fontsize=10.5, fontweight="bold", color=C_SPOKE_CAB, ha="center")

    ax2.annotate("", xy=(8.8, 2.5), xytext=(1.2, 2.5), arrowprops=dict(arrowstyle="<->", color=C_FREE, lw=2.0))
    ax2.text(5.0, 1.85, "Coordinate difference $u_j = x_i - x_k$", fontsize=11, fontweight="bold", color=C_FREE, ha="center")
    ax2.text(5.0, 1.10, " Matrix swap: $U\\mathbf{q} = Q\\mathbf{u} \\Longrightarrow C^T Q \\mathbf{u} = \\mathbf{p}_x$", fontsize=11, fontweight="bold", color=C_DARK, ha="center")

    out_path = OUT / "fd_sec_c1_force_density_trick.png"
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    print("Saved", out_path)


# =============================================================================
# FIGURE 6: Sections C.2–C.3 — Stiffness Matrix D at Node 2 & Solved 3D Saddle
# =============================================================================
def fig_sec_c2_c3_solved_net():
    fig = plt.figure(figsize=(12.5, 4.4), dpi=160, facecolor="white")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.15], wspace=0.14, left=0.02, right=0.98, top=0.84, bottom=0.04)

    # Left Panel: Row 2 of D at Free Node 2
    ax1 = fig.add_subplot(gs[0])
    draw_net_plan(
        ax1, show_branch_labels=False, highlight_node=2,
        title="1. Row 2 of $D$: 4 Cables Meeting at Node 2",
    )
    p2 = np.array(XY_PLAN[2])
    for nbr in [7, 1, 3, 5]:
        pn = np.array(XY_PLAN[nbr])
        ax1.plot([p2[0], pn[0]], [p2[1], pn[1]], color="#f59e0b", lw=4.5, zorder=3)

    ax1.text(0.55, 1.45, "$q_2 = 2$", fontsize=11, fontweight="bold", color="#b45309", ha="center")
    ax1.text(-0.78, 0.68, "$q_6 = 1$", fontsize=11, fontweight="bold", color="#b45309", ha="center")
    ax1.text(0.78, 0.68, "$q_7 = 1$", fontsize=11, fontweight="bold", color="#b45309", ha="center")
    ax1.annotate(
        "$q_{11} = 1$", xy=(0.0, 0.45), xytext=(-0.75, 1.45),
        fontsize=11, fontweight="bold", color="#b45309", ha="center", va="center",
        arrowprops=dict(arrowstyle="->", color="#b45309", lw=1.4), zorder=8,
    )

    # Right Panel: 3D Solved Equilibrium Cable Net (clean non-overlapping labels)
    ax2 = fig.add_subplot(gs[1], projection="3d", computed_zorder=False)
    ax2.set_facecolor("white")

    for i, k in BRANCHES:
        p1, p2 = XYZ_SOLVED[i], XYZ_SOLVED[k]
        ax2.plot([p1[0], p2[0]], [p1[1], p2[1]], [0, 0], color="#e2e8f0", lw=1.0, ls=":", zorder=1)

    for node, pt in XYZ_SOLVED.items():
        if pt[2] > 0.01:
            ax2.plot([pt[0], pt[0]], [pt[1], pt[1]], [0, pt[2]], color="#94a3b8", lw=1.0, ls="--", zorder=2)

    for idx, (i, k) in enumerate(BRANCHES, start=1):
        p1, p2 = XYZ_SOLVED[i], XYZ_SOLVED[k]
        col = C_ANCHOR_CAB if idx <= 4 else (C_RING_CAB if idx <= 8 else C_SPOKE_CAB)
        lw = 2.8 if idx <= 4 else 2.2
        ax2.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]], color=col, lw=lw, zorder=4)

    for node, pt in XYZ_SOLVED.items():
        if node <= 5:
            ax2.scatter([pt[0]], [pt[1]], [pt[2]], s=230, c=C_FREE_FILL, edgecolors=C_FREE, lw=2.0, zorder=6)
            ax2.text(pt[0], pt[1], pt[2], f"{node}", fontsize=9.5, fontweight="bold", color=C_FREE, ha="center", va="center", zorder=8)
        else:
            ax2.scatter([pt[0]], [pt[1]], [pt[2]], s=250, marker="s", c=C_FIXED_FILL, edgecolors=C_FIXED, lw=2.0, zorder=6)
            ax2.text(pt[0], pt[1], pt[2], f"{node}", fontsize=9.5, fontweight="bold", color=C_FIXED, ha="center", va="center", zorder=8)

    ax2.text(0.0, 2.0, 1.16, "$z_7 = 1.0$ m", fontsize=10, fontweight="bold", color=C_FIXED, ha="center", zorder=9)
    ax2.text(0.0, -2.0, 1.16, "$z_9 = 1.0$ m", fontsize=10, fontweight="bold", color=C_FIXED, ha="center", zorder=9)

    ax2.set_xlim(-2.0, 2.0); ax2.set_ylim(-2.0, 2.0); ax2.set_zlim(-0.05, 1.15)
    ax2.set_box_aspect((1.0, 1.0, 0.72))
    ax2.set_xticks([]); ax2.set_yticks([]); ax2.set_zticks([])
    ax2.view_init(elev=22, azim=-56)
    ax2.set_title("2. Solved 3D Saddle ($z_2,z_4=0.330$ m, $z_5=0.063$ m)", fontsize=11.5, fontweight="bold", color=C_DARK, pad=6)

    out_path = OUT / "fd_sec_c2_c3_solved_net.png"
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    print("Saved", out_path)


# =============================================================================
# FIGURE 7: Parts D, E & F — Saddle Height Control & Target Length Constraints
# =============================================================================
def fig_sec_e_f_constraints():
    fig = plt.figure(figsize=(12.5, 4.1), dpi=160, facecolor="white")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.05, 1.1], wspace=0.18, left=0.03, right=0.97, top=0.83, bottom=0.14)

    # Left Panel: Side elevation showing Center Node 5 height across Cases
    ax1 = fig.add_subplot(gs[0])
    ax1.set_xlim(-2.3, 2.3)
    ax1.set_ylim(-0.15, 1.25)
    ax1.axis("off")
    ax1.set_title("1. Side Elevation: How $q$ Controls Saddle Height", fontsize=11.5, fontweight="bold", color=C_DARK, pad=6)

    ax1.axhline(0.0, color="#cbd5e1", lw=1.2, ls="--")
    ax1.axhline(1.0, color="#cbd5e1", lw=1.2, ls="--")

    y_sec = np.array([-2.0, -0.8, 0.0, 0.8, 2.0])
    z_base = np.array([1.0, 0.330, 0.063, 0.330, 1.0])
    z_stiff = np.array([1.0, 0.679, 0.313, 0.679, 1.0])
    z_unloaded = np.array([1.0, 0.643, 0.500, 0.643, 1.0])

    ax1.plot(y_sec, z_unloaded, "-o", color="#059669", lw=2.4, label="Unloaded ($p=0$): $z_5 = 0.500$ m")
    ax1.plot(y_sec, z_stiff, "-s", color="#2563eb", lw=2.4, label="Stiff anchors ($q_{1..4}=10$): $z_5 = 0.313$ m")
    ax1.plot(y_sec, z_base, "-^", color=C_ANCHOR_CAB, lw=2.6, label="Base case ($q_{1..4}=2$): $z_5 = 0.063$ m")

    ax1.scatter([-2.0, 2.0], [1.0, 1.0], s=220, marker="s", c=C_FIXED_FILL, edgecolors=C_FIXED, lw=2.0, zorder=6)
    ax1.legend(loc="lower center", bbox_to_anchor=(0.5, -0.12), fontsize=9.5, frameon=False)

    # Right Panel: Part F Target Length Constraint l_{1..4} = 1.200 m
    ax2 = fig.add_subplot(gs[1])
    ax2.set_xlim(0, 10.8)
    ax2.set_ylim(0.4, 5.2)
    ax2.axis("off")
    ax2.set_title("2. Target Length $l_{1..4} = 1.20$ m (Before vs. After)", fontsize=11.5, fontweight="bold", color=C_DARK, pad=6)

    branches_lbl = ["$b_1$", "$b_2$", "$b_3$", "$b_4$"]
    l_init = [1.201, 1.374, 1.201, 1.374]
    q_opt = [1.97, 2.41, 1.97, 2.41]
    xs = [1.5, 4.0, 6.5, 9.0]

    for x0, lbl, li, qo in zip(xs, branches_lbl, l_init, q_opt):
        h_init = (li - 0.9) * 5.2
        h_targ = (1.200 - 0.9) * 5.2
        ax2.add_patch(mpatches.Rectangle((x0 - 0.68, 1.6), 0.60, h_init, facecolor="#fca5a5" if li > 1.21 else "#bfdbfe", edgecolor=C_DARK, lw=1.0))
        ax2.add_patch(mpatches.Rectangle((x0 + 0.08, 1.6), 0.60, h_targ, facecolor="#86efac", edgecolor="#065f46", lw=1.0))
        ax2.text(x0 - 0.38, 1.6 + h_init + 0.16, f"{li:.2f}", fontsize=9.5, ha="center", color=C_DARK)
        ax2.text(x0 + 0.38, 1.6 + h_targ + 0.16, "1.20", fontsize=9.5, ha="center", fontweight="bold", color="#065f46")
        ax2.text(x0, 1.12, lbl, fontsize=10.5, fontweight="bold", color=C_DARK, ha="center")
        ax2.text(x0, 0.65, f"$q^*={qo}$", fontsize=9.5, fontweight="bold", color="#065f46", ha="center")

    ax2.axhline(1.6 + (1.200 - 0.9) * 5.2, xmin=0.04, xmax=0.95, color="#059669", lw=1.6, ls="--")

    out_path = OUT / "fd_sec_e_f_constraints.png"
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    print("Saved", out_path)


if __name__ == "__main__":
    fig_linkwitz_intuition()
    fig_sec_a_topology()
    fig_sec_b2_uvw_geometry()
    fig_sec_b3_nonlinear_stages()
    fig_sec_c1_force_density_trick()
    fig_sec_c2_c3_solved_net()
    fig_sec_e_f_constraints()
