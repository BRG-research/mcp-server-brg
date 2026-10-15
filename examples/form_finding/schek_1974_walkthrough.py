"""Force density method, step by step, on the network of Schek (1974), figure 2.

Prints every matrix of the derivation exactly as quoted in
knowledge/04_form_finding/compas_fd.md.  Only numpy and scipy are needed; if compas_fd
is installed, its fd_numpy result is compared with the hand-rolled solve.  The figures
of the note are rendered separately with session_viewer (see schek_1974_figures.py).

Run:   python examples/form_finding/schek_1974_walkthrough.py
"""

from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import spsolve

np.set_printoptions(precision=3, suppress=True, linewidth=120)

# ---------------------------------------------------------------------------
# 1. Topology: nodes 1..9 (free 1..5, fixed 6..9), branches 1..12 as in figure 2.
#    Branch j runs from node i(j) (+1) to node k(j) (-1). 1-based as in the paper.
# ---------------------------------------------------------------------------
BRANCHES = [(1, 6), (2, 7), (3, 8), (4, 9),          # anchor branches 1-4
            (1, 4), (1, 2), (2, 3), (3, 4),          # ring 5-8
            (4, 5), (1, 5), (2, 5), (3, 5)]          # spokes to the centre 9-12
N_FREE, N_FIXED = 5, 4

# Initial coordinates: free nodes flat, fixed nodes alternately lifted (a small hypar).
XYZ0 = np.array([[-1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.0],
                 [-2.0, 0.0, 0.0], [0.0, -2.0, 1.0], [2.0, 0.0, 0.0], [0.0, 2.0, 1.0]])


def branch_node_matrix(branches, n_nodes):
    """Schek eq. (section 2.1): c(j, i) = +1 if i = i(j), -1 if i = k(j), else 0."""
    C = np.zeros((len(branches), n_nodes))
    for j, (i, k) in enumerate(branches):
        C[j, i - 1] = +1.0
        C[j, k - 1] = -1.0
    return C


def print_matrix(name, M, row_labels=None, col_labels=None, fmt="{:>6.2f}", zero="     ."):
    print(f"\n{name}  shape {M.shape}")
    if col_labels is not None:
        print("      " + "".join(f"{c:>6}" for c in col_labels))
    for r, row in enumerate(M):
        label = f"{row_labels[r]:>4}  " if row_labels is not None else "      "
        print(label + "".join(zero if abs(v) < 1e-12 else fmt.format(v) for v in row))


def force_density_solve(C_s, xyz_fixed, q, p, free, fixed):
    """Schek eqs. (7)-(10) in matrix form; returns xyz, lengths, forces, residuals and the matrices."""
    C, C_f = C_s[:, free], C_s[:, fixed]
    Q = np.diag(q)
    D = C.T @ Q @ C                      # eq. (8) left-hand side
    D_f = C.T @ Q @ C_f                  # coupling to the fixed nodes
    rhs = p[free] - D_f @ xyz_fixed      # right-hand side of (8), one column per axis
    xyz = np.zeros((C_s.shape[1], 3))
    xyz[fixed] = xyz_fixed
    xyz[free] = np.linalg.solve(D, rhs)  # eq. (9)
    uvw = C_s @ xyz                      # eq. (1): u, v, w as columns
    lengths = np.linalg.norm(uvw, axis=1)
    forces = q * lengths                 # eq. (10)
    residuals = p - C_s.T @ Q @ uvw      # p - C^t Q u, zero at free nodes
    return xyz, lengths, forces, residuals, dict(C=C, C_f=C_f, Q=Q, D=D, D_f=D_f, rhs=rhs, uvw=uvw)


def main():

    n_nodes = N_FREE + N_FIXED
    free = list(range(N_FREE))
    fixed = list(range(N_FREE, n_nodes))
    node_labels = [str(i + 1) for i in range(n_nodes)]
    branch_labels = [str(j + 1) for j in range(len(BRANCHES))]

    # ---- step 1: branch-node matrix -------------------------------------------------
    C_s = branch_node_matrix(BRANCHES, n_nodes)
    print_matrix("C_s = [C  C_f]   (figure 2 of the paper)", C_s, branch_labels, node_labels, fmt="{:>6.0f}")

    # ---- step 2: coordinate differences u, v, w  (eq. 1) ----------------------------
    uvw0 = C_s @ XYZ0
    print_matrix("u, v, w = C_s @ xyz0   (eq. 1, columns = u, v, w)", uvw0, branch_labels, ["u", "v", "w"])
    l0 = np.linalg.norm(uvw0, axis=1)
    print("\ninitial lengths l0:", l0)

    # ---- step 3: force densities and Q, D, D_f  (eqs. 4, 7, 8) ------------------------
    q = np.ones(len(BRANCHES))
    q[:4] = 2.0            # anchor branches stiffer
    print("\nq (anchor branches 2, others 1):", q)
    p = np.zeros((n_nodes, 3))
    p[free, 2] = -0.5      # small downward load on every free node
    xyz, lengths, forces, residuals, M = force_density_solve(C_s, XYZ0[fixed], q, p, free, fixed)
    print_matrix("Q = diag(q)", M["Q"], branch_labels, branch_labels, fmt="{:>6.1f}")
    print_matrix("D = C^t Q C   (compare figure 4: diagonal = sum of q at node, off-diagonal = -q_j)", M["D"],
                 node_labels[:N_FREE], node_labels[:N_FREE], fmt="{:>6.1f}")
    print_matrix("D_f = C^t Q C_f", M["D_f"], node_labels[:N_FREE], node_labels[N_FREE:], fmt="{:>6.1f}")
    print_matrix("right-hand side  p_free - D_f @ xyz_fixed   (eq. 8)", M["rhs"], node_labels[:N_FREE], ["x", "y", "z"])

    # symbolic D, like figure 4
    print("\nD with symbolic q_j (figure 4):")
    for i in range(N_FREE):
        row = []
        for k in range(N_FREE):
            terms = [j + 1 for j, (a, b) in enumerate(BRANCHES) if (a - 1 == i and b - 1 == k) or (a - 1 == k and b - 1 == i)]
            if i == k:
                terms = [j + 1 for j, (a, b) in enumerate(BRANCHES) if i in (a - 1, b - 1)]
                row.append("+".join(f"q{j}" for j in terms))
            else:
                row.append(f"-q{terms[0]}" if terms else ".")
        print("   " + "".join(f"{s:>16}" for s in row))

    # ---- step 4: solve, lengths, forces, residuals  (eqs. 9, 10) -------------------------
    print_matrix("xyz (eq. 9; rows 6-9 are the fixed input)", xyz, node_labels, ["x", "y", "z"])
    print("\nlengths l :", lengths)
    print("forces  s = q l (eq. 10):", forces)
    print_matrix("residuals p - C^t Q u (free rows ~ 0, fixed rows = -reaction)", residuals, node_labels, ["x", "y", "z"])
    assert np.abs(residuals[free]).max() < 1e-12

    # optional check against compas_fd
    try:
        from compas_fd.solvers import fd_numpy
        res = fd_numpy(vertices=XYZ0.tolist(), fixed=fixed, edges=[(i - 1, k - 1) for i, k in BRANCHES],
                       forcedensities=q.tolist(), loads=p.tolist())
        print("\ncompas_fd.fd_numpy agrees with the hand-rolled solve to",
              f"{np.abs(res.vertices - xyz).max():.1e}", "(coordinates) and",
              f"{np.abs(res.forces.ravel() - forces).max():.1e}", "(forces)")
    except ImportError:
        print("\n(compas_fd not installed; skipped cross-check)")

    # ---- step 5: vary q  (figures 7 and 8 of the paper) -----------------------------------
    variants = {}
    for label, q_anchor, q_spoke in [("q = 1 everywhere", 1.0, 1.0), ("anchors q = 10", 10.0, 1.0),
                                     ("spokes q = 0.3", 1.0, 0.3)]:
        qq = np.ones(len(BRANCHES))
        qq[:4] = q_anchor
        qq[8:] = q_spoke
        variants[label] = force_density_solve(C_s, XYZ0[fixed], qq, p, free, fixed)[0]
        print(f"\n{label}: centre node 5 at {variants[label][4]}")

    # ---- step 6: Schek section 3, prescribed lengths by damped least squares --------------
    r = 4                               # constrain the four anchor branches
    l_v = np.full(r, 1.2)               # prescribed strained lengths
    qk = q.copy()
    history = []
    for it in range(50):
        xyz_k, L, _, _, Mk = force_density_solve(C_s, XYZ0[fixed], qk, p, free, fixed)
        g = L[:r] - l_v                                               # eq. (29)
        history.append(np.abs(g).max())
        if history[-1] < 1e-10:
            break
        Dinv = np.linalg.inv(Mk["D"])
        C, uvw = Mk["C"], Mk["uvw"]
        Cb = C[:r]
        K = sum(np.diag(uvw[:r, a]) @ Cb @ Dinv @ C.T @ np.diag(uvw[:, a]) for a in range(3))
        Gt = -np.diag(1.0 / L[:r]) @ K                                # eq. (31)
        G = Gt.T
        A = np.diag(np.full(r, 0.8))                                  # damping factors a_j
        T = Gt @ G + 1e-6 * np.eye(r) @ A @ A                         # eq. (23), modified damped
        k_lag = np.linalg.solve(T, A @ (-g))                          # eqs. (20), (24)
        qk = qk + G @ k_lag                                           # eq. (25)
    print(f"\nprescribed anchor-branch length {l_v[0]}: reached in {it} damped iterations;",
          "lengths", L[:r], "q", qk[:r])
    print_matrix("G^t for the length constraints (eq. 31, last iteration)", Gt, [f"g{i+1}" for i in range(r)], branch_labels)
    constrained = xyz_k


if __name__ == "__main__":
    main()
