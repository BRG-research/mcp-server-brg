"""Linkwitz, Chapter 6 (Force density method), built step by step on the chapter's own single node, in the order
of the book's sections.  Each `# %% ID title` cell is one notebook cell of knowledge/04_form_finding/force_density_linkwitz.ipynb
(built by build_linkwitz_notebook.py).  The same cells, in study order, are notes/scripts/fdm_step_by_step.py of the
library book force-density-linkwitz.

    python3 linkwitz_app.py      (NumPy; Matplotlib only for the pictures)
"""
# %% A.1 6.2.1 A single node in equilibrium — the data of the exercise (p. 68)
import numpy as np

np.set_printoptions(precision=4, suppress=True, linewidth=110)

# Fixed points P1..P4 of the chapter's exercises (p. 68), one row per point, columns x y z (m)
P_fixed = np.array([[0.0, 0.0, 0.0],    # P1
                    [5.0, 0.0, 3.0],    # P2
                    [0.0, 7.0, 3.0],    # P3
                    [7.0, 5.0, 0.0]])   # P4
p = np.array([0.0, 0.0, -5.0])          # load on P0 (kN): 5 kN gravity acts in -z
q = np.array([1.0, 1.0, 1.0, 1.0])      # force densities of bars a b c d (kN/m)
bars = ["a", "b", "c", "d"]

print("fixed points (4x3):\n", P_fixed)
print("load p =", p, "kN   force densities q =", q, "kN/m")

# %% B.1 6.2.2 Translation to equations — bar lengths, equation (6.2)
def lengths(P0):
    """(6.2): l_k = sqrt((x_k-x0)^2 + (y_k-y0)^2 + (z_k-z0)^2) for the four bars, as one array."""
    return np.linalg.norm(P_fixed - P0, axis=1)


P0_guess = np.array([3.0, 3.0, 1.0])
print("guess P0 =", P0_guess, " -> lengths l =", lengths(P0_guess))

# %% B.2 6.2.2 Translation to equations — direction cosines and equilibrium, (6.4)–(6.6)
def residual(P0, F):
    """(6.6) in x, y and z at once: sum_k (P_k - P0)/l_k * F_k + p.  Zero when P0 is in equilibrium."""
    l = lengths(P0)
    cosines = (P_fixed - P0) / l[:, None]          # (6.4): direction cosines, one row per bar
    return (cosines * F[:, None]).sum(axis=0) + p


F_guess = np.array([1.0, 1.0, 1.0, 1.0])            # kN, as in exercise 1
print("direction cosines at the guess:\n", (P_fixed - P0_guess) / lengths(P0_guess)[:, None])
print("residual (6.6) at the guess with F = 1 kN:", residual(P0_guess, F_guess), " <- not zero, not in equilibrium")

# %% B.3 6.2.3 Force densities — the linear solution, (6.10)–(6.13)
def solve_single_node(q):
    """(6.13): P0 = (p + sum_k q_k P_k) / sum_k q_k, one line per coordinate."""
    return (p + (q[:, None] * P_fixed).sum(axis=0)) / q.sum()


P0 = solve_single_node(q)
l = lengths(P0)
F = q * l                                           # (6.33): the forces follow from the shape, F_k = q_k l_k
print("numerator  p + sum q_k P_k =", p + (q[:, None] * P_fixed).sum(axis=0))
print("denominator sum q_k        =", q.sum())
print("P0 (6.13)                  =", P0)
for k in range(4):
    print(f"  bar {bars[k]}: l = {l[k]:.4f} m, F = q l = {F[k]:.4f} kN")
print("residual (6.6) at P0       =", residual(P0, F), " <- equilibrium")

# %% B.4 6.2.3 Force densities — changing q (exercise 2, second part)
q2 = np.array([1.0, 2.0, 1.0, 2.0])                 # stiffer bars b and d
P0b = solve_single_node(q2)
print("q =", q2, " -> P0 =", P0b)
print("  P0 moved from", P0, "towards the midpoint of P2 and P4", (P_fixed[1] + P_fixed[3]) / 2)
print("  forces F = q l =", q2 * lengths(P0b), "kN;  residual =", residual(P0b, q2 * lengths(P0b)))

# %% B.5 6.2.3 Force densities — why prescribed forces are nonlinear (exercise 1)
def solve_with_forces(F, P0, steps=300):
    """Fixed-point iteration: with the current P0 compute l, turn the given forces into q = F/l (6.10),
    solve the linear (6.13), repeat until P0 stops moving.  Returns P0 and the number of steps."""
    for it in range(steps):
        P0_new = solve_single_node(F / lengths(P0))
        if np.linalg.norm(P0_new - P0) < 1e-12:
            return P0_new, it + 1
        P0 = P0_new
    return P0, steps


P0c, its = solve_with_forces(2.0 * np.ones(4), P0_guess)
print(f"F = 2 kN in every bar: converged in {its} steps to P0 =", P0c, " q = F/l =", 2.0 / lengths(P0c))
P0d, its = solve_with_forces(1.0 * np.ones(4), P0_guess, steps=100)
print(f"F = 1 kN in every bar: after {its} steps P0 =", P0d, " residual =", residual(P0d, np.ones(4)))
print("  four forces of 1 kN pull up with at most 4 kN together: a 5 kN load cannot be balanced")

# %% C.1 6.4 Notation — vectors and diagonal matrices
a = np.array([1.0, 2.0, 3.0])
A = np.diag(a)
print("a =", a, "  a^T =", a.T, " (NumPy does not distinguish row and column for 1-D arrays)")
print("A = diag(a) =\n", A)
u_demo, q_demo = np.array([3.0, -2.0, 3.0, -4.0]), np.array([1.0, 2.0, 1.0, 2.0])
print("U q =", np.diag(u_demo) @ q_demo, "  Q u =", np.diag(q_demo) @ u_demo, "  u*q =", u_demo * q_demo)

# %% C.2 6.4.1 Branch-node matrix — C and u = C x, (6.14)–(6.17)
C = np.array([[+1, -1, 0, 0, 0],    # bar a: P0 - P1
              [+1, 0, -1, 0, 0],    # bar b: P0 - P2
              [+1, 0, 0, -1, 0],    # bar c: P0 - P3
              [+1, 0, 0, 0, -1]],   # bar d: P0 - P4
             dtype=float)
x = np.r_[P0[0], P_fixed[:, 0]]     # (6.16): x = [x0 x1 x2 x3 x4]
y = np.r_[P0[1], P_fixed[:, 1]]
z = np.r_[P0[2], P_fixed[:, 2]]
u = C @ x                           # (6.17)
print("C (4 bars x 5 nodes):\n", C)
print("row sums", C.sum(axis=1), " column sums", C.sum(axis=0), " rank", np.linalg.matrix_rank(C), "= n - 1")
print("x =", x)
print("u = C x =", u, " = x0 - x_k   (the book's (6.15) lists x_k - x0:", x[1:] - x[0], ")")

# %% C.3 6.4.1 Branch-node matrix — the split into free and fixed, (6.18)–(6.20)
C_N, C_F = C[:, :1], C[:, 1:]        # column of P0 | columns of P1..P4
x_N, x_F = x[:1], x[1:]
u = C_N @ x_N + C_F @ x_F            # (6.20)
v = C_N @ y[:1] + C_F @ y[1:]
w = C_N @ z[:1] + C_F @ z[1:]
print("C_N (4x1) =", C_N.ravel(), "  C_F (4x4) =\n", C_F)
print("x_N =", x_N, " x_F =", x_F)
print("u =", u, "\nv =", v, "\nw =", w)

# %% C.4 6.4.1 Branch-node matrix — U, V, W and the lengths L, (6.21)
U, V, W = np.diag(u), np.diag(v), np.diag(w)
L = np.sqrt(U @ U + V @ V + W @ W)   # (6.21); the square root of a diagonal matrix is taken on the diagonal
Q = np.diag(q)
print("U = diag(u) =\n", U)
print("L = (U^2 + V^2 + W^2)^(1/2) =\n", L)
print("diagonal of L =", np.diag(L), " same as lengths(P0) =", lengths(P0))

# %% D.1 6.4.2 Jacobian — the function f(x0) and its derivative by finite differences, (6.22)
def f(x0):
    """(6.22): the four bar lengths as a function of the x-coordinate of the free node alone."""
    return lengths(np.array([x0, P0[1], P0[2]]))


h = 1e-6
dl_dx0_fd = (f(P0[0] + h) - f(P0[0] - h)) / (2 * h)
print("f(x0) = l =", f(P0[0]))
print("f(x0 + 0.1) =", f(P0[0] + 0.1), " <- move P0 0.1 m in +x: bars a, c lengthen, b, d shorten")
print("d l / d x0 by finite differences =", dl_dx0_fd)

# %% D.2 6.4.2 Jacobian — the derivative by the formula, (6.23)
dl_dx0 = -(P_fixed[:, 0] - P0[0]) / l                 # (6.23): -(x_k - x0) / l_k
print("d l / d x0 by (6.23)             =", dl_dx0)
print("direction cosines (x_k - x0)/l_k =", (P_fixed[:, 0] - P0[0]) / l, " <- the same numbers with the opposite sign")

# %% D.3 6.4.2 Jacobian — assembled from the branch-node matrix, (6.24)
J_T = C_N.T @ U @ np.linalg.inv(L)                   # (6.24): C_N^T U L^-1, here a 1 x 4 row
print("U L^-1 (diagonal) =", np.diag(U @ np.linalg.inv(L)))
print("C_N^T U L^-1      =", J_T.ravel(), " <- equal to (6.23)")

# %% D.4 6.4.3 Solution in matrix form — equilibrium with the Jacobian, (6.25)
J_T_z = -(P_fixed[:, 2] - P0[2]) / l                 # (6.23) for z0 instead of x0
print("J_z = d l / d z0 =", J_T_z)
print("bar force components in z, -J_z * F =", -J_T_z * F, " sum =", (-J_T_z * F).sum(), "kN")
print("(6.25): -J_z^T f + p_z =", -J_T_z @ F + p[2], " <- zero: the bars carry the 5 kN")

# %% E.1 6.4.3 Solution in matrix form — from forces to force densities, (6.26)–(6.28)
lhs = C_N.T @ W @ np.linalg.inv(L) @ F               # left-hand side of (6.26) in z
print("(6.26) C_N^T W L^-1 f =", lhs, "   p_z =", p[2])
print("       ... + p_z =", lhs + p[2], " (as printed)      ... - p_z =", lhs - p[2], " (zero)")
q_back = np.linalg.inv(L) @ F                        # (6.27): q = L^-1 f
print("(6.27) q = L^-1 f =", q_back)
print("(6.28) C_N^T W q  =", C_N.T @ W @ q_back, " = p_z: the lengths have cancelled")

# %% E.2 6.4.3 Solution in matrix form — the diagonal swap and C x, (6.29)–(6.30)
print("W q   =", W @ q, "  Q w =", Q @ w, "  Q C z =", Q @ C @ z)
print("(6.29) C_N^T Q C z          =", C_N.T @ Q @ C @ z)
print("(6.30) C_N^T Q C_N z_N + C_N^T Q C_F z_F =", C_N.T @ Q @ C_N @ z[:1] + C_N.T @ Q @ C_F @ z[1:])

# %% E.3 6.4.3 Solution in matrix form — the linear system and its solution, (6.31)–(6.33)
D_N = C_N.T @ Q @ C_N                                # (6.31): n_N x n_N, here 1 x 1
D_F = C_N.T @ Q @ C_F                                # n_N x n_F, here 1 x 4
print("D_N = C_N^T Q C_N =", D_N, "  D_F = C_N^T Q C_F =", D_F)
x_N = np.linalg.solve(D_N, p[0:1] - D_F @ x_F)       # (6.32), x
y_N = np.linalg.solve(D_N, p[1:2] - D_F @ y[1:])     # (6.32), y
z_N = np.linalg.solve(D_N, p[2:3] - D_F @ z[1:])     # (6.32), z
print("right-hand side in z: p_z - D_F z_F =", p[2:3] - D_F @ z[1:], " -> z_N =", z_N)
print("P0 from (6.32) =", np.r_[x_N, y_N, z_N], " same as (6.13):", P0)
print("(6.33) f = L q =", L @ q, "kN")

# %% G.1 6.4.4 Generalization — the standard grid of Figure 6.12 (exercise 3)
n_side, size = 6, 10.0
spacing = size / (n_side - 1)
nodes = [(i, j) for j in range(n_side) for i in range(n_side)]          # node k = 6 j + i
index = {ij: k for k, ij in enumerate(nodes)}
grid_bars = []
for (i, j) in nodes:
    if i + 1 < n_side:
        grid_bars.append((index[(i, j)], index[(i + 1, j)]))           # bar along x
    if j + 1 < n_side:
        grid_bars.append((index[(i, j)], index[(i, j + 1)]))           # bar along y
n, m = len(nodes), len(grid_bars)
Cg = np.zeros((m, n))
for r, (k1, k2) in enumerate(grid_bars):
    Cg[r, k1], Cg[r, k2] = +1, -1                                       # same convention as (6.14)
xy = np.array([(i * spacing, j * spacing) for (i, j) in nodes])
on_edge = [k for k, (i, j) in enumerate(nodes) if i in (0, n_side - 1) or j in (0, n_side - 1)]
corners = [index[(0, 0)], index[(5, 0)], index[(5, 5)], index[(0, 5)]]
edge_bars = [r for r, (k1, k2) in enumerate(grid_bars) if k1 in on_edge and k2 in on_edge]
print(f"n = {n} nodes, m = {m} bars, {len(on_edge)} nodes on the boundary, {len(edge_bars)} boundary bars")
print("C shape", Cg.shape, " rank", np.linalg.matrix_rank(Cg), "= n - 1;  first rows:\n", Cg[:3, :8], "...")

# %% G.2 6.4.4 Generalization — equation (6.32) for any net
def fdm_solve(C, fixed, q, xyz_fixed, p_free):
    """(6.32) for x, y and z.
    C: m x n branch-node matrix; fixed: list of fixed node indices; q: (m,) force densities;
    xyz_fixed: (n_F, 3) coordinates of the fixed nodes; p_free: (n_N, 3) loads at the free nodes.
    Returns the (n, 3) coordinates of all nodes."""
    n = C.shape[1]
    free = [k for k in range(n) if k not in fixed]
    C_N, C_F = C[:, free], C[:, fixed]                                  # (6.18)
    Q = np.diag(q)
    D_N = C_N.T @ Q @ C_N                                               # (6.31)
    D_F = C_N.T @ Q @ C_F
    xyz = np.zeros((n, 3))
    xyz[fixed] = xyz_fixed
    for c in range(3):
        xyz[free, c] = np.linalg.solve(D_N, p_free[:, c] - D_F @ xyz_fixed[:, c])   # (6.32)
    return xyz


def check_equilibrium(C, xyz, q, p_all):
    """sum over bars of q (x_other - x_node) + p at every node; zero at the free nodes, minus the reaction at fixed ones."""
    diff = C @ xyz                                                      # (6.17): one row per bar, x_start - x_end
    return -C.T @ (q[:, None] * diff) + p_all


# the single node again, now through the general function
xyz_single = fdm_solve(C, [1, 2, 3, 4], q, P_fixed, p[None, :])
print("single node through fdm_solve:", xyz_single[0], " = P0")

# %% G.3 6.4.4 Generalization — three shapes of the grid (exercise 4)
cases = []
# (a) boundary nodes fixed flat, q = 1, 1 kN down at every interior node (a hanging net)
q_a = np.ones(m)
xyz_a = fdm_solve(Cg, on_edge, q_a, np.c_[xy[on_edge], np.zeros(len(on_edge))], np.tile([0, 0, -1.0], (n - len(on_edge), 1)))
cases.append(("(a) boundary fixed flat, q = 1, p_z = -1", xyz_a, on_edge, q_a, -1.0))
# (b) only the corners fixed, two opposite corners at z = 4 m, edge bars q = 5, interior q = 1, no load (a saddle)
q_b = np.ones(m); q_b[edge_bars] = 5.0
z_corners = np.array([4.0, 0.0, 4.0, 0.0])
xyz_b = fdm_solve(Cg, corners, q_b, np.c_[xy[corners], z_corners], np.zeros((n - 4, 3)))
cases.append(("(b) corners fixed, two at z = 4 m, q edge:interior = 5:1, no load", xyz_b, corners, q_b, 0.0))
# (c) as (b) with 1 kN down at every free node
xyz_c = fdm_solve(Cg, corners, q_b, np.c_[xy[corners], z_corners], np.tile([0, 0, -1.0], (n - 4, 1)))
cases.append(("(c) as (b) with p_z = -1", xyz_c, corners, q_b, -1.0))
interior = [index[(i, j)] for j in range(1, 5) for i in range(1, 5)]
for name, xyz, fixed, qq, pz in cases:
    free = [k for k in range(n) if k not in fixed]
    p_all = np.zeros((n, 3)); p_all[free, 2] = pz
    res = check_equilibrium(Cg, xyz, qq, p_all)
    lg = np.linalg.norm(xyz[[b[0] for b in grid_bars]] - xyz[[b[1] for b in grid_bars]], axis=1)
    print(name)
    print("  z of the 16 interior nodes:\n", xyz[interior, 2].reshape(4, 4))
    print("  forces f = L q: min %.3f max %.3f kN;  max |residual| at free nodes %.1e;  reactions z at the first 4 fixed nodes %s"
          % ((lg * qq).min(), (lg * qq).max(), np.abs(res[free]).max(), -res[fixed[:4], 2]))

# %% G.4 6.4.4 Generalization — pictures
try:
    import matplotlib
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(6, 5))
    ax = fig.add_subplot(projection="3d")
    for k in range(4):
        ax.plot(*zip(P0, P_fixed[k]), color="#ce4095", lw=2)
        ax.text(*P_fixed[k], f"  P{k + 1} ({P_fixed[k][0]:g}, {P_fixed[k][1]:g}, {P_fixed[k][2]:g})", fontsize=8)
        ax.text(*(P0 + P_fixed[k]) / 2, bars[k], fontsize=10, color="#ce4095")
    ax.scatter(*P_fixed.T, color="k", s=20); ax.scatter(*P0, color="#ce4095", s=40)
    ax.text(*P0, f"  P0 ({P0[0]:g}, {P0[1]:g}, {P0[2]:g})", fontsize=8)
    ax.quiver(*P0, 0, 0, -2.0, color="#3f9c20", arrow_length_ratio=0.2)
    ax.text(P0[0], P0[1], P0[2] - 2.3, "p = 5 kN", color="#3f9c20", fontsize=8)
    ax.set_title("Exercise 2: q = 1 in a, b, c, d", fontsize=9); ax.view_init(elev=20, azim=-50)
    fig.tight_layout(); plt.show()
    fig = plt.figure(figsize=(13, 4.2))
    for a_, (name, xyz, fixed, qq, pz) in enumerate(cases):
        ax = fig.add_subplot(1, 3, a_ + 1, projection="3d")
        for k1, k2 in grid_bars:
            ax.plot(*zip(xyz[k1], xyz[k2]), color="#ce4095", lw=1)
        ax.scatter(*xyz[fixed].T, color="k", s=12)
        ax.set_title(name, fontsize=8); ax.set_zlim(-3, 5); ax.view_init(elev=25, azim=-60)
    fig.tight_layout(); plt.show()
except ImportError:
    print("matplotlib not installed: no pictures")

# %% F.1 6.5 Materialization — cutting lengths for a chosen stiffness, (6.34)–(6.37)
EA = np.diag([500.0, 500.0, 500.0, 500.0])           # kN, one value per bar
I = np.eye(4)
l0 = np.linalg.solve(I + np.linalg.inv(EA) @ Q @ L, l)   # (6.37): l0 = (I + EA^-1 Q L)^-1 l
e = l - l0                                           # (6.34): elastic elongation
print("stressed lengths l =", l)
print("cutting lengths l0 =", l0, " (each bar cut about 1 % short)")
print("elongations e = l - l0 =", e, "  check (6.34) L0 EA^-1 f =", np.diag(l0) @ np.linalg.inv(EA) @ F)
print("Hooke (6.1): EA/l0 * e =", np.diag(EA) / l0 * e, " = F =", F)

