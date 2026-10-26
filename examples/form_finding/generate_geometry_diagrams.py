"""Generate textbook-style geometric and physical explanation figures for compas_fd.md.

Combines Klaus Linkwitz's Chapter 6 (Shell Structures for Architecture, 2014) single-node
and physical intuition with H.-J. Schek's (1974) 9-node, 12-branch cable net benchmark,
so every equation in the tutorial is paired with a visual diagram showing what is
happening geometrically on the cable net.

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

# Palette
C_FREE = "#1d4ed8"      # deep blue for free nodes
C_FREE_FILL = "#dbeafe"
C_FIXED = "#b91c1c"     # crimson for fixed anchors
C_FIXED_FILL = "#fee2e2"
C_ANCHOR_CAB = "#dc2626"
C_RING_CAB = "#2563eb"
C_SPOKE_CAB = "#059669"
C_LOAD = "#d97706"      # amber/orange for external loads
C_REACT = "#7c3aed"     # purple for support reactions
C_DARK = "#0f172a"
C_MUTED = "#475569"
C_BG_BOX = "#f8fafc"
C_BORDER = "#cbd5e1"


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
    1: (-1.45, 0.22),
    2: (0.24, 1.45),
    3: (1.45, 0.22),
    4: (0.24, -1.45),
    5: (-0.62, -0.62),
    6: (-0.62, 0.62),
    7: (0.62, 0.62),
    8: (0.62, -0.62),
    9: (-0.20, -0.42),
    10: (-0.42, -0.18),
    11: (-0.20, 0.42),
    12: (0.42, -0.18),
}


def draw_net_plan(ax, coords=XY_PLAN, show_branch_labels=True, highlight_node=None, title="", xlim=(-2.55, 2.55), ylim=(-2.95, 2.35)):
    """Draw the 9-node, 12-branch directed network in plan with color-coded groups."""
    for idx, (i, k) in enumerate(BRANCHES, start=1):
        p1, p2 = np.array(coords[i]), np.array(coords[k])
        if idx <= 4:
            col, lw = C_ANCHOR_CAB, 2.2
        elif idx <= 8:
            col, lw = C_RING_CAB, 1.9
        else:
            col, lw = C_SPOKE_CAB, 1.7
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=col, lw=lw, zorder=2)
        mid = 0.52 * p1 + 0.48 * p2
        d = p2 - p1
        ax.annotate(
            "", xy=(mid[0] + 0.12 * d[0], mid[1] + 0.12 * d[1]),
            xytext=(mid[0] - 0.12 * d[0], mid[1] - 0.12 * d[1]),
            arrowprops=dict(arrowstyle="-|>", color=col, lw=1.4, mutation_scale=11),
            zorder=3,
        )
        if show_branch_labels:
            lx, ly = BRANCH_LABEL_POS[idx]
            ax.text(
                lx, ly, f"$b_{{{idx}}}$",
                fontsize=8.5, color=col, fontweight="bold", ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none", alpha=0.88),
                zorder=4,
            )

    for node, (x, y) in coords.items():
        is_free = node <= 5
        ring_ec = "#f59e0b" if node == highlight_node else (C_FREE if is_free else C_FIXED)
        ring_lw = 3.2 if node == highlight_node else 1.8
        if is_free:
            ax.scatter([x], [y], s=250, c=C_FREE_FILL, edgecolors=ring_ec, linewidths=ring_lw, zorder=5)
            ax.text(x, y, f"{node}", fontsize=9.5, fontweight="bold", color=C_FREE, ha="center", va="center", zorder=6)
        else:
            ax.scatter([x], [y], s=270, marker="s", c=C_FIXED_FILL, edgecolors=ring_ec, linewidths=ring_lw, zorder=5)
            ax.text(x, y, f"{node}", fontsize=9.5, fontweight="bold", color=C_FIXED, ha="center", va="center", zorder=6)

    ax.set_aspect("equal")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=10.2, fontweight="bold", color=C_DARK, pad=6)


# =============================================================================
# FIGURE 1: Linkwitz Chapter 6 Physical Intuition & Single-Node Equilibrium
# =============================================================================
def fig_linkwitz_intuition():
    fig = plt.figure(figsize=(15.8, 5.2), dpi=180, facecolor="white")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.08, 1.18, 1.16], wspace=0.16, left=0.02, right=0.98, top=0.83, bottom=0.05)

    fig.suptitle(
        "Physical & Geometric Foundation (Linkwitz Ch. 6): From Anticlastic Cables & Single-Node Balance to Materialization",
        fontsize=12.5, fontweight="bold", color=C_DARK, y=0.96,
    )

    # --- Panel A: Anticlastic curvature ---
    ax1 = fig.add_subplot(gs[0], projection="3d")
    ax1.set_facecolor("white")
    t = np.linspace(-1, 1, 40)
    X, Y = np.meshgrid(np.linspace(-1, 1, 15), np.linspace(-1, 1, 15))
    Z = 0.45 * (Y**2 - X**2) + 0.5
    ax1.plot_wireframe(X, Y, Z, color="#cbd5e1", linewidth=0.6, alpha=0.6)
    ax1.plot(np.zeros_like(t), t, 0.45 * t**2 + 0.5, color=C_FIXED, lw=3.0)
    ax1.plot(t, np.zeros_like(t), -0.45 * t**2 + 0.5, color=C_FREE, lw=3.0)
    ax1.scatter([0], [0], [0.5], color="#0f172a", s=70, zorder=10)
    ax1.add_artist(Arrow3D([0, 0], [0, 0], [0.5, 0.85], mutation_scale=12, lw=2.0, arrowstyle="-|>", color=C_FIXED))
    ax1.add_artist(Arrow3D([0, 0], [0, 0], [0.5, 0.15], mutation_scale=12, lw=2.0, arrowstyle="-|>", color=C_FREE))
    ax1.text(0.10, 0.08, 0.53, "$P_0$", fontsize=10, fontweight="bold", color=C_DARK)
    ax1.text(0.0, 0.85, 1.02, "High anchors\n(pull $P_0$ up)", fontsize=8.5, color=C_FIXED, ha="center")
    ax1.text(-0.88, 0.0, -0.14, "Low anchors\n(pull $P_0$ down)", fontsize=8.5, color=C_FREE, ha="center")
    ax1.set_xlim(-1.1, 1.1)
    ax1.set_ylim(-1.1, 1.1)
    ax1.set_zlim(-0.15, 1.1)
    ax1.set_xticks([]); ax1.set_yticks([]); ax1.set_zticks([])
    ax1.view_init(elev=22, azim=-48)
    ax1.set_title("1. Anticlastic Saddle Curvature (Fig. 6.2–6.3)\nTwo cables pull UP $\\updownarrow$ two cables pull DOWN at $P_0$", fontsize=9.8, fontweight="bold", color=C_DARK, pad=4)

    # --- Panel B: Single Node P0 with 4 neighbor bars a,b,c,d ---
    ax2 = fig.add_subplot(gs[1])
    ax2.set_xlim(-2.6, 2.6)
    ax2.set_ylim(-2.85, 2.35)
    ax2.set_aspect("equal")
    ax2.axis("off")
    ax2.set_title("2. Single Node $P_0$ in Equilibrium (Fig. 6.4, Eqs. 6.6–6.13)\n$P_0$ settles at the $q$-weighted average of its neighbors", fontsize=9.8, fontweight="bold", color=C_DARK, pad=4)

    p0 = np.array([0.0, 0.15])
    neighbors = [
        ("P_1", np.array([-1.75, 0.45]), "a", "$F_a = q_a l_a$", C_FREE, (-1.75, 0.82), (-0.95, 0.62)),
        ("P_2", np.array([0.30, 1.65]), "b", "$F_b = q_b l_b$", C_FIXED, (0.30, 2.00), (0.68, 1.08)),
        ("P_3", np.array([1.75, 0.05]), "c", "$F_c = q_c l_c$", C_FREE, (1.75, 0.46), (0.95, -0.25)),
        ("P_4", np.array([-0.30, -1.10]), "d", "$F_d = q_d l_d$", C_FIXED, (-1.15, -1.15), (-0.65, -0.52)),
    ]
    for name, pk, bar, flab, col, npos, bpos in neighbors:
        ax2.plot([p0[0], pk[0]], [p0[1], pk[1]], color="#64748b", lw=2.0, ls="-", zorder=2)
        d = pk - p0
        ax2.annotate(
            "", xy=(p0[0] + 0.46 * d[0], p0[1] + 0.46 * d[1]), xytext=(p0[0], p0[1]),
            arrowprops=dict(arrowstyle="-|>", color=col, lw=2.4, mutation_scale=13), zorder=4,
        )
        ax2.text(bpos[0], bpos[1], f"bar ${bar}$: {flab}", fontsize=8.2, color=col, fontweight="bold", ha="center")
        ax2.scatter([pk[0]], [pk[1]], s=200, marker="s", c=C_FIXED_FILL, edgecolors=C_FIXED, linewidths=1.8, zorder=5)
        ax2.text(npos[0], npos[1], f"${name}(x_{name[-1]},y_{name[-1]},z_{name[-1]})$", fontsize=8.3, fontweight="bold", color=C_DARK, ha="center")

    ax2.annotate(
        "", xy=(p0[0] + 0.18, p0[1] - 0.82), xytext=(p0[0], p0[1]),
        arrowprops=dict(arrowstyle="-|>", color=C_LOAD, lw=2.6, mutation_scale=13), zorder=4,
    )
    ax2.text(p0[0] + 0.65, p0[1] - 0.68, "Load $p_z$", fontsize=8.8, fontweight="bold", color=C_LOAD)
    ax2.scatter([p0[0]], [p0[1]], s=260, c=C_FREE_FILL, edgecolors=C_FREE, linewidths=2.2, zorder=6)
    ax2.text(p0[0] - 0.52, p0[1] + 0.25, "$P_0(x_0,y_0,z_0)$", fontsize=9.0, fontweight="bold", color=C_FREE)

    eq_text = (
        "Force balance along $x$ (Linkwitz Eq. 6.11–6.13):\n"
        "$q_a(x_1 - x_0) + q_b(x_2 - x_0) + q_c(x_3 - x_0) + q_d(x_4 - x_0) + p_x = 0$\n"
        "Solve directly for unknown $x_0$:   "
        "$x_0 = \\dfrac{p_x + q_a x_1 + q_b x_2 + q_c x_3 + q_d x_4}{q_a + q_b + q_c + q_d}$"
    )
    ax2.text(
        0.0, -2.78, eq_text, fontsize=8.2, color=C_DARK, ha="center", va="bottom",
        bbox=dict(boxstyle="round,pad=0.32", fc=C_BG_BOX, ec=C_BORDER, lw=1.0),
    )

    # --- Panel C: Materialization ---
    ax3 = fig.add_subplot(gs[2])
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0, 6.4)
    ax3.axis("off")
    ax3.set_title("3. Materialization (Sec. 6.5, Eqs. 6.1 & 6.37)\nCut cable shorter ($l_0 < l$) and stretch to induce force $s = q \\cdot l$", fontsize=9.8, fontweight="bold", color=C_DARK, pad=4)

    y_top = 4.85
    ax3.plot([1.0, 6.2], [y_top, y_top], color="#475569", lw=6, solid_capstyle="round")
    ax3.scatter([1.0, 6.2], [y_top, y_top], s=90, color="#334155", zorder=4)
    ax3.annotate("", xy=(6.2, y_top + 0.42), xytext=(1.0, y_top + 0.42), arrowprops=dict(arrowstyle="<->", color="#334155", lw=1.4))
    ax3.text(3.6, y_top + 0.62, "1. Unstressed (cutting) length $l_{0,j}$ (slack, $s_j = 0$)", fontsize=8.6, fontweight="bold", color="#334155", ha="center")

    y_bot = 3.1
    ax3.plot([1.0, 6.2], [y_bot, y_bot], color=C_FREE, lw=5, solid_capstyle="butt")
    ax3.plot([6.2, 8.6], [y_bot, y_bot], color=C_ANCHOR_CAB, lw=5, ls="--")
    ax3.scatter([1.0], [y_bot], s=140, c=C_FREE_FILL, edgecolors=C_FREE, lw=2, zorder=5)
    ax3.scatter([8.6], [y_bot], s=150, marker="s", c=C_FIXED_FILL, edgecolors=C_FIXED, lw=2, zorder=5)
    ax3.text(1.0, y_bot - 0.42, "Node $i$", fontsize=8.5, fontweight="bold", color=C_FREE, ha="center")
    ax3.text(8.6, y_bot - 0.42, "Node $k$", fontsize=8.5, fontweight="bold", color=C_FIXED, ha="center")

    ax3.annotate("", xy=(8.6, y_bot + 0.42), xytext=(6.2, y_bot + 0.42), arrowprops=dict(arrowstyle="<->", color=C_ANCHOR_CAB, lw=1.5))
    ax3.text(7.4, y_bot + 0.60, "Stretch $e_j = l_j - l_{0,j}$", fontsize=8.4, fontweight="bold", color=C_ANCHOR_CAB, ha="center")

    ax3.annotate("", xy=(8.6, y_bot - 0.80), xytext=(1.0, y_bot - 0.80), arrowprops=dict(arrowstyle="<->", color=C_FREE, lw=1.6))
    ax3.text(4.8, y_bot - 1.15, "2. Stressed 3D length in equilibrium $l_j = \\sqrt{u_j^2+v_j^2+w_j^2}$", fontsize=8.6, fontweight="bold", color=C_FREE, ha="center")

    mat_text = (
        "Step 1 (Form-finding): Solve geometry with pure $q_j = s_j / l_j$ (no $EA$ needed!).\n"
        "Step 2 (Materialization, Eq. 6.37): Pick stiffness $EA_j$, compute cutting length:\n"
        "$s_j = \\dfrac{EA_j}{l_{0,j}}(l_j - l_{0,j}) = q_j l_j \\quad \\Longrightarrow \\quad "
        "l_{0,j} = \\dfrac{l_j}{1 + s_j / EA_j} = \\dfrac{l_j}{1 + q_j l_j / EA_j}$"
    )
    ax3.text(
        5.0, 0.08, mat_text, fontsize=8.2, color=C_DARK, ha="center", va="bottom",
        bbox=dict(boxstyle="round,pad=0.32", fc=C_BG_BOX, ec=C_BORDER, lw=1.0),
    )

    out_path = OUT / "fd_linkwitz_intuition.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print("Saved", out_path)


# =============================================================================
# FIGURE 2: Part A — Topology, [C | C_f] Split, and C vs C^T on the Cable Net
# =============================================================================
def fig_sec_a_topology():
    fig = plt.figure(figsize=(15.8, 5.1), dpi=180, facecolor="white")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.1, 1.15, 1.15], wspace=0.14, left=0.02, right=0.98, top=0.83, bottom=0.04)

    fig.suptitle(
        "Part A — How the 9-Node, 12-Cable Net Is Encoded in $C_s = [C \\mid C_f]$ and How $C$ vs. $C^T$ Operate on the Net",
        fontsize=12.5, fontweight="bold", color=C_DARK, y=0.96,
    )

    # Panel 1: Directed Network Graph
    ax1 = fig.add_subplot(gs[0])
    draw_net_plan(
        ax1, show_branch_labels=True,
        title="1. Directed Network Graph ($n=5$ free, $n_f=4$ fixed, $m=12$)",
    )
    ax1.text(
        0.0, -2.85,
        "Blue circles (1..5) = Free nodes ($C$ columns)\nRed squares (6..9) = Fixed anchors ($C_f$ columns)",
        fontsize=8.3, color=C_DARK, ha="center", va="bottom",
        bbox=dict(boxstyle="round,pad=0.25", fc=C_BG_BOX, ec=C_BORDER),
    )

    # Panel 2: Operator C_s = [C | C_f]
    ax2 = fig.add_subplot(gs[1])
    draw_net_plan(
        ax2, show_branch_labels=False,
        title="2. Forward Multiply $\\mathbf{u} = C\\mathbf{x} + C_f\\mathbf{x}_f$ (Nodes $\\rightarrow$ Branches)",
    )
    p1, p6, p2 = np.array(XY_PLAN[1]), np.array(XY_PLAN[6]), np.array(XY_PLAN[2])
    ax2.plot([p1[0], p6[0]], [p1[1], p6[1]], color="#f59e0b", lw=4.5, zorder=3)
    ax2.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#10b981", lw=4.5, zorder=3)
    ax2.text(-1.50, 0.55, "$b_1 (1\\to 6)$:\n$u_1 = (+1)x_1 + (-1)x_6$\n$= x_1 - x_6$", fontsize=8.2, fontweight="bold", color="#b45309", ha="center", bbox=dict(boxstyle="round,pad=0.2", fc="#fef3c7", ec="#f59e0b"))
    ax2.text(-1.05, 1.38, "$b_6 (1\\to 2)$:\n$u_6 = x_1 - x_2$", fontsize=8.2, fontweight="bold", color="#047857", ha="center", bbox=dict(boxstyle="round,pad=0.2", fc="#d1fae5", ec="#10b981"))
    ax2.text(
        0.0, -2.85,
        "Each ROW $j$ of $C_s$ has $+1$ at start node $i$ and $-1$ at end node $k$.\nMultiplying $C_s \\mathbf{x}_s$ subtracts endpoints for all 12 cables at once!",
        fontsize=8.3, color=C_DARK, ha="center", va="bottom",
        bbox=dict(boxstyle="round,pad=0.25", fc=C_BG_BOX, ec=C_BORDER),
    )

    # Panel 3: Operator C^T
    ax3 = fig.add_subplot(gs[2])
    draw_net_plan(
        ax3, show_branch_labels=False, highlight_node=1,
        title="3. Transpose Multiply $C^T \\mathbf{F}_x$ (Branches $\\rightarrow$ Free Nodes)",
    )
    label_offsets = {
        1: (-1.45, 0.35),
        6: (-0.75, 0.72),
        5: (-0.75, -0.72),
        10: (-0.45, 0.24),
    }
    for b_idx, nbr in [(1, 6), (5, 4), (6, 2), (10, 5)]:
        pa, pb = np.array(XY_PLAN[1]), np.array(XY_PLAN[nbr])
        d = pb - pa
        ax3.annotate(
            "", xy=(pa[0] + 0.65 * d[0], pa[1] + 0.65 * d[1]), xytext=(pa[0], pa[1]),
            arrowprops=dict(arrowstyle="-|>", color="#f59e0b", lw=3.2, mutation_scale=14), zorder=7,
        )
        lx, ly = label_offsets[b_idx]
        ax3.text(lx, ly, f"$F_{{x,{b_idx}}}$", fontsize=8.3, fontweight="bold", color="#b45309", ha="center", bbox=dict(boxstyle="round,pad=0.12", fc="#fef3c7", ec="#f59e0b", lw=0.8), zorder=8)

    ax3.text(
        0.0, -2.85,
        "Row 1 of $C^T$ is Column 1 of $C$: nonzeros at $b_1, b_5, b_6, b_{10}$.\nMultiplying $C^T \\mathbf{F}_x$ sums all cable forces meeting at Node 1..5!",
        fontsize=8.3, color=C_DARK, ha="center", va="bottom",
        bbox=dict(boxstyle="round,pad=0.25", fc=C_BG_BOX, ec=C_BORDER),
    )

    out_path = OUT / "fd_sec_a_topology_split.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print("Saved", out_path)


# =============================================================================
# FIGURE 3: Section B.2 (Eq. 1) — Coordinate Differences (u, v, w) & Length l
# =============================================================================
def fig_sec_b2_uvw_geometry():
    fig = plt.figure(figsize=(15.8, 5.2), dpi=180, facecolor="white")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.12, 1.18], wspace=0.14, left=0.02, right=0.98, top=0.83, bottom=0.05)

    fig.suptitle(
        "Section B.2 (Eq. 1) — Geometric Meaning of Coordinate Differences $(u_j, v_j, w_j)$ and Cable Length $l_j$",
        fontsize=12.5, fontweight="bold", color=C_DARK, y=0.96,
    )

    # --- Left Panel: 3D right box / triangle of a single cable j ---
    ax1 = fig.add_subplot(gs[0], projection="3d")
    ax1.set_facecolor("white")

    pi = np.array([0.0, 0.8, 0.30])
    pk = np.array([1.6, 2.0, 1.00])
    px = np.array([pk[0], pi[1], pi[2]])
    pxy = np.array([pk[0], pk[1], pi[2]])

    ax1.plot([pi[0], pk[0]], [pi[1], pk[1]], [pi[2], pk[2]], color=C_ANCHOR_CAB, lw=3.5, zorder=5)
    ax1.add_artist(Arrow3D([pi[0], pk[0]], [pi[1], pk[1]], [pi[2], pk[2]], mutation_scale=15, lw=2.5, arrowstyle="-|>", color=C_ANCHOR_CAB))

    ax1.plot([pi[0], px[0]], [pi[1], px[1]], [pi[2], px[2]], color="#2563eb", lw=2.4, ls="--")
    ax1.plot([px[0], pxy[0]], [px[1], pxy[1]], [px[2], pxy[2]], color="#059669", lw=2.4, ls="--")
    ax1.plot([pxy[0], pk[0]], [pxy[1], pk[1]], [pxy[2], pk[2]], color="#d97706", lw=2.4, ls="--")
    ax1.plot([pi[0], pxy[0]], [pi[1], pxy[1]], [pi[2], pxy[2]], color="#94a3b8", lw=1.4, ls=":")

    ax1.scatter([pi[0]], [pi[1]], [pi[2]], s=180, c=C_FREE_FILL, edgecolors=C_FREE, lw=2.2, zorder=8)
    ax1.scatter([pk[0]], [pk[1]], [pk[2]], s=190, marker="s", c=C_FIXED_FILL, edgecolors=C_FIXED, lw=2.2, zorder=8)

    ax1.text(pi[0] - 0.15, pi[1] - 0.15, pi[2] + 0.08, "Start Node $i$\n$(x_i, y_i, z_i)$", fontsize=8.8, fontweight="bold", color=C_FREE)
    ax1.text(pk[0] + 0.05, pk[1] + 0.02, pk[2] + 0.06, "End Node $k$\n$(x_k, y_k, z_k)$", fontsize=8.8, fontweight="bold", color=C_FIXED)

    ax1.text(0.85, pi[1] - 0.28, pi[2] - 0.08, "$u_j = x_i - x_k$\n($x$-difference)", fontsize=8.8, fontweight="bold", color="#2563eb", ha="center")
    ax1.text(pk[0] + 0.18, 1.40, pi[2] - 0.04, "$v_j = y_i - y_k$\n($y$-difference)", fontsize=8.8, fontweight="bold", color="#059669", ha="left")
    ax1.text(pk[0] + 0.14, pk[1] + 0.05, 0.65, "$w_j = z_i - z_k$\n($z$-drop/rise)", fontsize=8.8, fontweight="bold", color="#d97706", ha="left")
    ax1.text(0.35, 1.45, 0.88, "3D Cable Length\n$l_j = \\sqrt{u_j^2 + v_j^2 + w_j^2}$\nDirection cos $\\cos\\alpha_j = u_j / l_j$", fontsize=8.6, fontweight="bold", color=C_ANCHOR_CAB, ha="center", bbox=dict(boxstyle="round,pad=0.22", fc="#fff1f2", ec=C_ANCHOR_CAB, lw=1.0))

    ax1.set_xlim(-0.35, 2.15)
    ax1.set_ylim(0.45, 2.35)
    ax1.set_zlim(0.15, 1.18)
    ax1.set_xlabel("$x$ (m)", fontsize=8.5, labelpad=-8)
    ax1.set_ylabel("$y$ (m)", fontsize=8.5, labelpad=-8)
    ax1.set_zlabel("$z$ (m)", fontsize=8.5, labelpad=-8)
    ax1.set_xticks([]); ax1.set_yticks([]); ax1.set_zticks([])
    ax1.view_init(elev=22, azim=-52)
    ax1.set_title("1. Single Cable $j$: $(u_j, v_j, w_j)$ Are the 3D Box Sides of Length $l_j$", fontsize=10.2, fontweight="bold", color=C_DARK, pad=4)

    # --- Right Panel: Global Picture on the 12-branch net ---
    ax2 = fig.add_subplot(gs[1])
    draw_net_plan(
        ax2, show_branch_labels=True,
        title="2. Global Net Picture: $\\mathbf{u} = C\\mathbf{x} + C_f\\mathbf{x}_f$ Measures All 12 Cables",
        xlim=(-2.95, 2.95), ylim=(-2.55, 2.55),
    )
    ax2.text(
        -1.85, 1.45,
        "Cable $b_1 (1\\to 6)$:\n$x_1=-1,\\ x_6=-2$\n$u_1 = x_1 - x_6 = +1\\text{ m}$\n$v_1=0,\\ w_1=0 \\Rightarrow l_1=1\\text{ m}$",
        fontsize=8.0, color=C_DARK, ha="center",
        bbox=dict(boxstyle="round,pad=0.22", fc="#eff6ff", ec=C_FREE, lw=1.0),
    )
    ax2.text(
        1.85, 1.45,
        "Cable $b_3 (3\\to 8)$:\n$x_3=+1,\\ x_8=+2$\n$u_3 = x_3 - x_8 = -1\\text{ m}$\n$v_3=0,\\ w_3=0 \\Rightarrow l_3=1\\text{ m}$",
        fontsize=8.0, color=C_DARK, ha="center",
        bbox=dict(boxstyle="round,pad=0.22", fc="#eff6ff", ec=C_FREE, lw=1.0),
    )
    ax2.text(
        1.85, -1.55,
        "Ring cables $b_5..b_8$:\n$|u_j|=1,\\ |v_j|=1,\\ w_j=0$\n$l_j = \\sqrt{1^2+1^2} = \\sqrt{2}\\approx 1.414\\text{ m}$",
        fontsize=8.0, color=C_DARK, ha="center",
        bbox=dict(boxstyle="round,pad=0.22", fc="#f0fdf4", ec=C_SPOKE_CAB, lw=1.0),
    )
    ax2.text(
        -1.85, -1.55,
        "Anchor cables $b_2, b_4$:\nReach lifted anchors $z_7=z_9=1\\text{ m}$\n$w_2 = z_2 - z_7 = 0 - 1 = -1\\text{ m}$\n(only cables with vertical slope!)",
        fontsize=8.0, color=C_DARK, ha="center",
        bbox=dict(boxstyle="round,pad=0.22", fc="#fef2f2", ec=C_FIXED, lw=1.0),
    )

    out_path = OUT / "fd_sec_b2_uvw_geometry.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print("Saved", out_path)


# =============================================================================
# FIGURE 4: Section B.3 (Eq. 2) — 4-Stage Nonlinear Equilibrium & Why Flat Net Fails
# =============================================================================
def fig_sec_b3_nonlinear_stages():
    fig = plt.figure(figsize=(15.8, 4.9), dpi=180, facecolor="white")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1.15], wspace=0.15, left=0.02, right=0.98, top=0.82, bottom=0.07)

    fig.suptitle(
        "Section B.3 (Eq. 2) — Reading $\\mathbf{e} = C^T U L^{-1}\\mathbf{s} - \\mathbf{p}$ Right-to-Left & Why a Flat Trial Net Is Out of Equilibrium",
        fontsize=12.0, fontweight="bold", color=C_DARK, y=0.96,
    )

    # --- Left Panel: 4-stage pipeline diagram + Linkwitz Jacobian identity ---
    ax1 = fig.add_subplot(gs[0])
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 6.8)
    ax1.axis("off")
    ax1.set_title("1. The 4 Stages of $\\mathbf{e}_x = C^T U L^{-1} \\mathbf{s} - \\mathbf{p}_x$ (and Jacobian Meaning)", fontsize=9.8, fontweight="bold", color=C_DARK, pad=4)

    stages = [
        (5.55, "#eff6ff", C_FREE, "Stage 1 (Branches, $12\\times 1$):  $\\mathbf{q} = L^{-1}\\mathbf{s} \\Longrightarrow q_j = s_j / l_j$ (tension per unit length)"),
        (4.20, "#f0fdf4", C_SPOKE_CAB, "Stage 2 (Branches, $12\\times 1$):  $\\mathbf{F}_x = U\\mathbf{q} = U L^{-1}\\mathbf{s} \\Longrightarrow F_{x,j} = s_j(u_j / l_j) = s_j\\cos\\alpha_j$"),
        (2.85, "#fff7ed", "#ea580c", "Stage 3 (Free Nodes, $5\\times 1$):  $C^T \\mathbf{F}_x$ sums the $x$-forces of all cables meeting at each free node"),
        (1.50, "#fef2f2", C_FIXED, "Stage 4 (Free Nodes, $5\\times 1$):  $\\mathbf{e}_x = C^T \\mathbf{F}_x - \\mathbf{p}_x$ subtracts external load ($\\mathbf{e}_x = \\mathbf{0}$ at equilibrium)"),
    ]
    for y0, fc, ec, txt in stages:
        ax1.text(5.0, y0, txt, fontsize=8.3, fontweight="bold", color=C_DARK, ha="center", va="center", bbox=dict(boxstyle="round,pad=0.32", fc=fc, ec=ec, lw=1.2))
    for y_top, y_bot in [(5.1, 4.65), (3.75, 3.30), (2.40, 1.95)]:
        ax1.annotate("", xy=(5.0, y_bot), xytext=(5.0, y_top), arrowprops=dict(arrowstyle="-|>", color=C_DARK, lw=1.8, mutation_scale=12))

    ax1.text(
        5.0, 0.15,
        "Linkwitz Sec. 6.4.2 (Eqs. 6.22–6.24): Since $\\partial l_j / \\partial x_i = \\pm u_j / l_j = \\pm \\cos\\alpha_j$,\n"
        "the matrix $C^T U L^{-1} = (\\partial \\mathbf{l} / \\partial \\mathbf{x})^T$ is simultaneously the direction-cosine projection AND the length Jacobian!",
        fontsize=8.0, color=C_DARK, ha="center", va="bottom",
        bbox=dict(boxstyle="round,pad=0.25", fc=C_BG_BOX, ec=C_BORDER),
    )

    # --- Right Panel: Side elevation of the Flat Trial Net showing why e_z != 0 ---
    ax2 = fig.add_subplot(gs[1])
    ax2.set_xlim(-2.4, 2.4)
    ax2.set_ylim(-0.95, 1.45)
    ax2.axis("off")
    ax2.set_title("2. Side Elevation of Flat Trial Shape ($z_1..z_5 = 0$): Why $\\mathbf{e}_z \\neq \\mathbf{0}$", fontsize=9.8, fontweight="bold", color=C_DARK, pad=4)

    # Draw flat inner nodes at z=0 and lifted anchors 7, 9 at z=1
    ax2.plot([-2.0, -0.9, 0.0, 0.9, 2.0], [1.0, 0.0, 0.0, 0.0, 1.0], color=C_RING_CAB, lw=2.5, zorder=2)
    ax2.plot([-2.0, -0.9], [1.0, 0.0], color=C_ANCHOR_CAB, lw=2.8, zorder=3)
    ax2.plot([0.9, 2.0], [0.0, 1.0], color=C_ANCHOR_CAB, lw=2.8, zorder=3)

    ax2.scatter([-2.0, 2.0], [1.0, 1.0], s=180, marker="s", c=C_FIXED_FILL, edgecolors=C_FIXED, lw=2, zorder=5)
    ax2.text(-2.0, 1.16, "Anchor 9\n($z_9 = 1$ m)", fontsize=8.2, fontweight="bold", color=C_FIXED, ha="center")
    ax2.text(2.0, 1.16, "Anchor 7\n($z_7 = 1$ m)", fontsize=8.2, fontweight="bold", color=C_FIXED, ha="center")

    for x_n, lbl, ez_val in [(-0.9, "Node 4", "+0.184 kN"), (0.0, "Node 5 (center)", "+0.500 kN"), (0.9, "Node 2", "+0.184 kN")]:
        ax2.scatter([x_n], [0.0], s=180, c=C_FREE_FILL, edgecolors=C_FREE, lw=2, zorder=5)
        ax2.annotate("", xy=(x_n, -0.45), xytext=(x_n, 0.0), arrowprops=dict(arrowstyle="-|>", color=C_LOAD, lw=2.4, mutation_scale=13))
        ax2.text(x_n, -0.58, f"$p_z = -0.5$ kN\n$e_z = {ez_val}$", fontsize=8.0, fontweight="bold", color=C_LOAD, ha="center")
        ax2.text(x_n, 0.16, lbl, fontsize=8.2, fontweight="bold", color=C_FREE, ha="center")

    ax2.text(0.0, 0.55, "Inner cables are FLAT ($w_5..w_{12} = 0$)\n$\\Rightarrow$ zero vertical cable force ($F_z = 0$)\n$\\Rightarrow$ nothing balances $-0.5$ kN load at Node 5!", fontsize=8.4, fontweight="bold", color="#991b1b", ha="center", bbox=dict(boxstyle="round,pad=0.25", fc="#fef2f2", ec="#f87171"))

    out_path = OUT / "fd_sec_b3_nonlinear_stages.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print("Saved", out_path)


# =============================================================================
# FIGURE 5: Section C.1 (Eqs. 4–6) — The Force Density Trick & Role of u / U
# =============================================================================
def fig_sec_c1_force_density_trick():
    fig = plt.figure(figsize=(15.8, 5.0), dpi=180, facecolor="white")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.12, 1.14, 1.14], wspace=0.15, left=0.02, right=0.98, top=0.82, bottom=0.06)

    fig.suptitle(
        "Section C.1 (Eqs. 4–6) — How Force Density $q_j = s_j / l_j$ Uses Coordinate Difference $u_j$ to Linearize Equilibrium",
        fontsize=12.2, fontweight="bold", color=C_DARK, y=0.96,
    )

    # --- Panel 1: Geometric Force Projection (Before Trick: Nonlinear) ---
    ax1 = fig.add_subplot(gs[0])
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 7.2)
    ax1.axis("off")
    ax1.set_title("1. Geometric Force Projection (Linkwitz Eq. 6.4–6.6)\nWhy $F_{x,j} = s_j (u_j / l_j)$ is nonlinear in coordinates", fontsize=9.6, fontweight="bold", color=C_DARK, pad=4)

    p_start = np.array([1.5, 2.9])
    p_end = np.array([8.3, 5.9])
    p_corner = np.array([8.3, 2.9])
    ax1.plot([p_start[0], p_corner[0]], [p_start[1], p_corner[1]], color=C_FREE, lw=2.0, ls="--")
    ax1.plot([p_corner[0], p_end[0]], [p_corner[1], p_end[1]], color="#d97706", lw=2.0, ls="--")
    ax1.plot([p_start[0], p_end[0]], [p_start[1], p_end[1]], color="#64748b", lw=2.4)

    d = p_end - p_start
    ax1.annotate("", xy=(p_start[0] + 0.55 * d[0], p_start[1] + 0.55 * d[1]), xytext=p_start, arrowprops=dict(arrowstyle="-|>", color=C_ANCHOR_CAB, lw=3.2, mutation_scale=15))
    ax1.annotate("", xy=(p_start[0] + 0.55 * d[0], p_start[1]), xytext=p_start, arrowprops=dict(arrowstyle="-|>", color=C_FREE, lw=3.0, mutation_scale=14))

    ax1.scatter([p_start[0]], [p_start[1]], s=160, c=C_FREE_FILL, edgecolors=C_FREE, lw=2, zorder=5)
    ax1.scatter([p_end[0]], [p_end[1]], s=160, marker="s", c=C_FIXED_FILL, edgecolors=C_FIXED, lw=2, zorder=5)
    ax1.text(p_start[0] - 0.1, p_start[1] + 0.45, "Node $i (x_i)$", fontsize=8.6, fontweight="bold", color=C_FREE)
    ax1.text(p_end[0] - 0.3, p_end[1] + 0.35, "Node $k (x_k)$", fontsize=8.6, fontweight="bold", color=C_FIXED)
    ax1.text(3.2, 3.25, "$\\alpha_j$", fontsize=10, fontweight="bold", color=C_DARK)
    ax1.text(3.7, 4.85, "Tension $s_j$\n(along length $l_j$)", fontsize=8.6, fontweight="bold", color=C_ANCHOR_CAB, ha="center")
    ax1.text(5.0, 2.38, "Horizontal span $u_j = x_i - x_k$", fontsize=8.5, fontweight="bold", color=C_FREE, ha="center")
    ax1.text(5.0, 1.72, "Projected force $F_{x,j} = s_j \\cos\\alpha_j = s_j \\dfrac{u_j}{l_j}$", fontsize=8.5, fontweight="bold", color=C_FREE, ha="center")
    ax1.text(8.65, 4.4, "$w_j$", fontsize=9, fontweight="bold", color="#d97706")

    ax1.text(
        5.0, 0.12,
        "NONLINEAR BOTTLENECK:\n$\\cos\\alpha_j = \\dfrac{u_j}{l_j} = \\dfrac{x_i - x_k}{\\sqrt{(x_i-x_k)^2 + (y_i-y_k)^2 + (z_i-z_k)^2}}$",
        fontsize=8.1, color="#991b1b", ha="center",
        bbox=dict(boxstyle="round,pad=0.26", fc="#fef2f2", ec="#f87171"),
    )

    # --- Panel 2: The Force Density Substitution q_j = s_j / l_j (Eqs. 4-5) ---
    ax2 = fig.add_subplot(gs[1])
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 7.2)
    ax2.axis("off")
    ax2.set_title("2. The Force Density Substitution (Eqs. 4–5)\nPrescribing $q_j = s_j / l_j$ cancels $l_j$ out of $F_{x,j}$!", fontsize=9.6, fontweight="bold", color=C_DARK, pad=4)

    box1 = (
        "Group the unknown length $l_j$ with force $s_j$:\n\n"
        "$F_{x,j} = s_j \\dfrac{u_j}{l_j} = \\left(\\dfrac{s_j}{l_j}\\right) u_j = q_j u_j = q_j (x_i - x_k)$"
    )
    ax2.text(5.0, 5.45, box1, fontsize=9.0, color=C_DARK, ha="center", va="center", bbox=dict(boxstyle="round,pad=0.38", fc="#eff6ff", ec=C_FREE, lw=1.4))

    ax2.plot([1.6, 8.4], [3.25, 3.25], color=C_SPOKE_CAB, lw=3.5, ls="-")
    ax2.scatter([1.6], [3.25], s=160, c=C_FREE_FILL, edgecolors=C_FREE, lw=2, zorder=5)
    ax2.scatter([8.4], [3.25], s=160, marker="s", c=C_FIXED_FILL, edgecolors=C_FIXED, lw=2, zorder=5)
    ax2.annotate("", xy=(8.4, 2.68), xytext=(1.6, 2.68), arrowprops=dict(arrowstyle="<->", color=C_FREE, lw=1.6))
    ax2.text(5.0, 3.65, "Equivalent linear spring of stiffness $q_j$ (kN/m)", fontsize=8.6, fontweight="bold", color=C_SPOKE_CAB, ha="center")
    ax2.text(5.0, 2.22, "Coordinate difference $u_j = x_i - x_k$ (m)", fontsize=8.6, fontweight="bold", color=C_FREE, ha="center")

    ax2.text(
        5.0, 0.12,
        "LINEAR IN COORDINATES!\nAlong $x$: $F_{x,j} = q_j u_j = q_j(x_i - x_k)$\nAlong $y$: $F_{y,j} = q_j v_j = q_j(y_i - y_k)$\nAlong $z$: $F_{z,j} = q_j w_j = q_j(z_i - z_k)$",
        fontsize=8.1, color="#065f46", ha="center",
        bbox=dict(boxstyle="round,pad=0.26", fc="#ecfdf5", ec="#34d399"),
    )

    # --- Panel 3: The Diagonal Commutation Swap U q = Q u (Eq. 6) ---
    ax3 = fig.add_subplot(gs[2])
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0, 7.2)
    ax3.axis("off")
    ax3.set_title("3. Why Swap $U\\mathbf{q} = Q\\mathbf{u}$ in Eq. 6?\nIsolate the unknown coordinate vector $\\mathbf{u}$ on the right", fontsize=9.6, fontweight="bold", color=C_DARK, pad=4)

    swap_top = (
        "Before Swap: $C^T U \\mathbf{q} = \\mathbf{p}_x$\n"
        "• $U = \\mathrm{diag}(u_1, \\dots, u_{12})$ is a $(12\\times 12)$ matrix of UNKNOWNS\n"
        "• $\\mathbf{q} = [q_1, \\dots, q_{12}]^T$ is a $(12\\times 1)$ vector of KNOWNS"
    )
    ax3.text(5.0, 5.6, swap_top, fontsize=8.4, color=C_DARK, ha="center", va="center", bbox=dict(boxstyle="round,pad=0.32", fc="#fff7ed", ec="#fb923c"))

    ax3.annotate("", xy=(5.0, 3.65), xytext=(5.0, 4.65), arrowprops=dict(arrowstyle="-|>", color=C_DARK, lw=2.2, mutation_scale=15))
    ax3.text(5.0, 4.15, "Diagonal matrices commute: $u_j q_j = q_j u_j \\Longleftrightarrow U\\mathbf{q} = Q\\mathbf{u}$", fontsize=8.1, fontweight="bold", color=C_DARK, ha="center", bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none"))

    swap_bot = (
        "After Swap: $C^T Q \\mathbf{u} = \\mathbf{p}_x$\n"
        "• $Q = \\mathrm{diag}(q_1, \\dots, q_{12})$ is a $(12\\times 12)$ KNOWN matrix\n"
        "• $\\mathbf{u} = C\\mathbf{x} + C_f\\mathbf{x}_f$ is a $(12\\times 1)$ vector of UNKNOWNS!"
    )
    ax3.text(5.0, 2.65, swap_bot, fontsize=8.4, color=C_DARK, ha="center", va="center", bbox=dict(boxstyle="round,pad=0.32", fc="#eff6ff", ec=C_FREE))

    ax3.text(
        5.0, 0.12,
        "NEXT STEP (Eqs. 7–8): Substitute $\\mathbf{u} = C\\mathbf{x} + C_f\\mathbf{x}_f$:\n"
        "$C^T Q (C\\mathbf{x} + C_f\\mathbf{x}_f) = \\mathbf{p}_x \\Longrightarrow D\\mathbf{x} = \\mathbf{p}_x - D_f\\mathbf{x}_f$   ($D=C^T Q C,\\ D_f=C^T Q C_f$)",
        fontsize=8.1, color=C_DARK, ha="center",
        bbox=dict(boxstyle="round,pad=0.26", fc=C_BG_BOX, ec=C_BORDER),
    )

    out_path = OUT / "fd_sec_c1_force_density_trick.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print("Saved", out_path)


# =============================================================================
# FIGURE 6: Sections C.2–D.1 — Stiffness Matrix D, Anchor Pull -D_f x_f & 3D Solved Net
# =============================================================================
def fig_sec_c2_c3_solved_net():
    fig = plt.figure(figsize=(15.8, 5.2), dpi=180, facecolor="white")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.12, 1.18], wspace=0.14, left=0.02, right=0.98, top=0.83, bottom=0.04)

    fig.suptitle(
        "Sections C.2–D.1 (Eqs. 7–10) — How $D\\mathbf{x} = \\mathbf{p}_x - D_f\\mathbf{x}_f$ Balances Every Node & Produces the 3D Saddle Shape",
        fontsize=12.2, fontweight="bold", color=C_DARK, y=0.96,
    )

    # --- Left Panel: Physical Meaning of D and -D_f z_f at Node 2 ---
    ax1 = fig.add_subplot(gs[0])
    draw_net_plan(
        ax1, show_branch_labels=False, highlight_node=2,
        title="1. Physical Meaning of $D = C^T Q C$ and $-D_f \\mathbf{z}_f$ at Node 2",
    )
    p2 = np.array(XY_PLAN[2])
    for nbr in [7, 1, 3, 5]:
        pn = np.array(XY_PLAN[nbr])
        ax1.plot([p2[0], pn[0]], [p2[1], pn[1]], color="#f59e0b", lw=4.0, zorder=3)

    ax1.text(1.12, 1.48, "$q_2 = 2$ (to Anchor 7,\nlifted at $z_7 = 1.0$ m)", fontsize=8.0, fontweight="bold", color="#b45309", ha="center", bbox=dict(boxstyle="round,pad=0.18", fc="#fef3c7", ec="#f59e0b"))
    ax1.text(-0.78, 0.68, "$q_6 = 1$", fontsize=8.0, fontweight="bold", color="#b45309", ha="center", bbox=dict(boxstyle="round,pad=0.15", fc="#fef3c7", ec="#f59e0b"))
    ax1.text(0.78, 0.68, "$q_7 = 1$", fontsize=8.0, fontweight="bold", color="#b45309", ha="center", bbox=dict(boxstyle="round,pad=0.15", fc="#fef3c7", ec="#f59e0b"))
    ax1.text(0.42, 0.36, "$q_{11} = 1$", fontsize=8.0, fontweight="bold", color="#b45309", ha="center", bbox=dict(boxstyle="round,pad=0.15", fc="#fef3c7", ec="#f59e0b"))

    ax1.text(
        0.0, -2.88,
        "Row 2 of $D\\mathbf{z} = \\mathbf{p}_z - D_f\\mathbf{z}_f$ (vertical balance at Free Node 2):\n"
        "$(q_2+q_6+q_7+q_{11}) z_2 - q_6 z_1 - q_7 z_3 - q_{11} z_5 = p_{z,2} + q_2 z_7$\n"
        "$5 z_2 - z_1 - z_3 - z_5 = -0.5 + 2.0 = +1.5$ kN   ($D_{22}=5,\\ -(D_f z_f)_2 = +2.0$)",
        fontsize=8.1, color=C_DARK, ha="center", va="bottom",
        bbox=dict(boxstyle="round,pad=0.25", fc=C_BG_BOX, ec=C_BORDER),
    )

    # --- Right Panel: 3D Solved Equilibrium Cable Net ---
    ax2 = fig.add_subplot(gs[1], projection="3d")
    ax2.set_facecolor("white")

    for i, k in BRANCHES:
        p1, p2 = XYZ_SOLVED[i], XYZ_SOLVED[k]
        ax2.plot([p1[0], p2[0]], [p1[1], p2[1]], [0, 0], color="#e2e8f0", lw=1.0, ls=":")

    for node, pt in XYZ_SOLVED.items():
        if pt[2] > 0.01:
            ax2.plot([pt[0], pt[0]], [pt[1], pt[1]], [0, pt[2]], color="#94a3b8", lw=1.0, ls="--")

    for idx, (i, k) in enumerate(BRANCHES, start=1):
        p1, p2 = XYZ_SOLVED[i], XYZ_SOLVED[k]
        col = C_ANCHOR_CAB if idx <= 4 else (C_RING_CAB if idx <= 8 else C_SPOKE_CAB)
        lw = 2.8 if idx <= 4 else 2.2
        ax2.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]], color=col, lw=lw, zorder=4)

    label_shifts_3d = {
        1: (-0.08, 0.42, 0.14),
        2: (0.28, 0.18, 0.08),
        3: (0.55, 0.25, 0.04),
        4: (-0.52, -0.25, 0.10),
        5: (-0.42, -0.42, -0.16),
        6: (-0.20, 0.25, 0.12),
        7: (0.0, 0.12, 0.09),
        8: (0.15, -0.22, 0.10),
        9: (-0.25, -0.20, 0.09),
    }
    for node, pt in XYZ_SOLVED.items():
        dx, dy, dz = label_shifts_3d[node]
        if node <= 5:
            ax2.scatter([pt[0]], [pt[1]], [pt[2]], s=150, c=C_FREE_FILL, edgecolors=C_FREE, lw=2.0, zorder=6)
            ax2.text(
                pt[0] + dx, pt[1] + dy, pt[2] + dz,
                f"N{node} ($z={pt[2]:.3f}$)",
                fontsize=7.6, fontweight="bold", color=C_FREE, ha="center",
                bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none", alpha=0.82),
            )
        else:
            ax2.scatter([pt[0]], [pt[1]], [pt[2]], s=170, marker="s", c=C_FIXED_FILL, edgecolors=C_FIXED, lw=2.0, zorder=6)
            ax2.text(
                pt[0] + dx, pt[1] + dy, pt[2] + dz,
                f"Anchor {node}\n($z_f={pt[2]:.1f}$ m)",
                fontsize=7.8, fontweight="bold", color=C_FIXED, ha="center",
                bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none", alpha=0.82),
            )

    for node in range(1, 6):
        pt = XYZ_SOLVED[node]
        ax2.add_artist(Arrow3D([pt[0], pt[0]], [pt[1], pt[1]], [pt[2], pt[2] - 0.22], mutation_scale=10, lw=1.6, arrowstyle="-|>", color=C_LOAD))

    ax2.set_xlim(-2.15, 2.15)
    ax2.set_ylim(-2.15, 2.15)
    ax2.set_zlim(-0.22, 1.18)
    ax2.set_xticks([]); ax2.set_yticks([]); ax2.set_zticks([])
    ax2.view_init(elev=30, azim=-18)
    ax2.set_title(
        "2. Solved 3D Saddle Equilibrium Shape (C.3–C.4)\n"
        "High free nodes N2, N4 ($z=0.330$ m) vs. low N1, N3 ($z=0.045$ m) & center N5 ($z=0.063$ m)",
        fontsize=9.8, fontweight="bold", color=C_DARK, pad=4,
    )

    out_path = OUT / "fd_sec_c2_c3_solved_net.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print("Saved", out_path)


# =============================================================================
# FIGURE 7: Parts E & F — Energy Minimization & Target Length Constraints (G^T)
# =============================================================================
def fig_sec_e_f_constraints():
    fig = plt.figure(figsize=(15.8, 4.9), dpi=180, facecolor="white")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.08, 1.22], wspace=0.15, left=0.02, right=0.98, top=0.82, bottom=0.08)

    fig.suptitle(
        "Parts D, E & F — How Changing Force Densities $\\mathbf{q}$ Steers Node Heights & Enforces Target Cable Lengths $\\mathbf{l}_v$",
        fontsize=12.2, fontweight="bold", color=C_DARK, y=0.96,
    )

    # --- Left Panel: Side elevation showing Center Node 5 height across Cases (D.2 & E.1) ---
    ax1 = fig.add_subplot(gs[0])
    ax1.set_xlim(-2.3, 2.3)
    ax1.set_ylim(-0.32, 1.32)
    ax1.axis("off")
    ax1.set_title("1. Side Elevation: How $q_{\\text{anchor}}$ and Load $\\mathbf{p}_z$ Control Saddle Height (D.2 & E.1)", fontsize=9.6, fontweight="bold", color=C_DARK, pad=4)

    ax1.axhline(0.0, color="#cbd5e1", lw=1.2, ls="--")
    ax1.axhline(1.0, color="#cbd5e1", lw=1.2, ls="--")
    ax1.text(-2.25, 0.04, "$z=0.0$ m (Anchors 6, 8)", fontsize=8, color=C_MUTED)
    ax1.text(-1.55, 1.05, "$z=1.0$ m (Anchors 7, 9)", fontsize=8, color=C_MUTED)

    y_sec = np.array([-2.0, -0.8, 0.0, 0.8, 2.0])
    z_base = np.array([1.0, 0.330, 0.063, 0.330, 1.0])
    z_stiff = np.array([1.0, 0.679, 0.313, 0.679, 1.0])
    z_unloaded = np.array([1.0, 0.643, 0.500, 0.643, 1.0])

    ax1.plot(y_sec, z_unloaded, "-o", color="#059669", lw=2.2, label="Unloaded ($\\mathbf{p}=0$, Part E.1): $z_5 = 0.500$ m (minimizes $\\sum q_j l_j^2$)")
    ax1.plot(y_sec, z_stiff, "-s", color="#2563eb", lw=2.4, label="Stiff anchors ($q_{1..4}=10$, Part D.2): $z_5 = 0.313$ m (taut anchor cables)")
    ax1.plot(y_sec, z_base, "-^", color=C_ANCHOR_CAB, lw=2.6, label="Base case ($q_{1..4}=2$, Part C.3): $z_5 = 0.063$ m (sags under $-0.5$ kN loads)")

    ax1.scatter([-2.0, 2.0], [1.0, 1.0], s=180, marker="s", c=C_FIXED_FILL, edgecolors=C_FIXED, lw=2, zorder=6)
    ax1.annotate("", xy=(0.0, 0.313), xytext=(0.0, 0.063), arrowprops=dict(arrowstyle="-|>", color=C_FREE, lw=2.2, mutation_scale=13))
    ax1.text(0.14, 0.16, "Raising $q_{1..4}: 2 \\to 10$\npulls center up $+0.25$ m!", fontsize=8.2, fontweight="bold", color=C_FREE)

    ax1.legend(loc="lower center", bbox_to_anchor=(0.5, -0.04), fontsize=7.9, frameon=True, facecolor=C_BG_BOX, edgecolor=C_BORDER)

    # --- Right Panel: Part F Target Length Constraint l_{1..4} = 1.200 m & Jacobian G^T ---
    ax2 = fig.add_subplot(gs[1])
    ax2.set_xlim(0, 11.2)
    ax2.set_ylim(0, 6.7)
    ax2.axis("off")
    ax2.set_title("2. Enforcing Target Lengths $l_{1..4} = 1.200$ m via Sensitivity Jacobian $G^T$ (Part F)", fontsize=9.6, fontweight="bold", color=C_DARK, pad=4)

    branches_lbl = ["$b_1 (1\\to 6)$\nGround", "$b_2 (2\\to 7)$\nLifted", "$b_3 (3\\to 8)$\nGround", "$b_4 (4\\to 9)$\nLifted"]
    l_init = [1.201, 1.374, 1.201, 1.374]
    q_opt = [1.972, 2.412, 1.972, 2.412]
    xs = [1.45, 3.95, 6.45, 8.95]

    for x0, lbl, li, qo in zip(xs, branches_lbl, l_init, q_opt):
        h_init = (li - 0.9) * 5.0
        h_targ = (1.200 - 0.9) * 5.0
        ax2.add_patch(mpatches.Rectangle((x0 - 0.72, 2.2), 0.62, h_init, facecolor="#fca5a5" if li > 1.21 else "#bfdbfe", edgecolor=C_DARK, lw=1.0))
        ax2.add_patch(mpatches.Rectangle((x0 + 0.10, 2.2), 0.62, h_targ, facecolor="#86efac", edgecolor="#065f46", lw=1.0))
        ax2.text(x0 - 0.41, 2.2 + h_init + 0.14, f"{li:.3f} m\n($q=2.0$)", fontsize=7.3, ha="center", color=C_DARK)
        ax2.text(x0 + 0.41, 2.2 + h_targ + 0.14, f"1.200 m\n($q^*={qo:.2f}$)", fontsize=7.3, ha="center", fontweight="bold", color="#065f46")
        ax2.text(x0, 1.55, lbl, fontsize=8.1, fontweight="bold", ha="center", color=C_DARK)

    ax2.plot([0.4, 10.0], [2.2 + (1.200 - 0.9) * 5.0] * 2, color="#059669", lw=1.5, ls="--")
    ax2.text(10.1, 2.2 + (1.200 - 0.9) * 5.0, "Target\n$1.200$ m", fontsize=8.0, fontweight="bold", color="#059669", va="center")

    f_text = (
        "How the Jacobian $G^T = \\partial \\mathbf{g}^* / \\partial \\mathbf{q}$ steers the update (F.1–F.3):\n"
        "• Diagonal sensitivity is negative ($\\partial l_2 / \\partial q_2 = -0.358$ m per kN/m): increasing $q_j$ ALWAYS shortens cable $j$.\n"
        "• Since lifted cables $b_2, b_4$ are $+0.174$ m too long ($1.374 > 1.200$ m), the solver raises $q_2, q_4: 2.000 \\to 2.412$ kN/m."
    )
    ax2.text(5.4, 0.08, f_text, fontsize=8.0, color=C_DARK, ha="center", va="bottom", bbox=dict(boxstyle="round,pad=0.3", fc=C_BG_BOX, ec=C_BORDER))

    out_path = OUT / "fd_sec_e_f_constraints.png"
    fig.savefig(out_path, dpi=180)
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
