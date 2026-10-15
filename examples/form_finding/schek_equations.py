"""Every numbered equation of Schek (1974) as a few lines of NumPy.

The note knowledge/04_form_finding/compas_fd.md quotes these functions one by one,
right after the formula each of them implements.  Run this file to execute them
all on the 9-node network of the paper's figure 2 and to check them against
finite differences and against each other:

    python examples/form_finding/schek_equations.py

Only numpy and scipy are used.  Shapes follow the paper: m branches, n free nodes,
n_f fixed nodes.  Vectors are 1-D arrays, diagonal matrices are built with np.diag.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

np.set_printoptions(precision=4, suppress=True, linewidth=110)

# ---------------------------------------------------------------- the network of figure 2
BRANCHES = [(1, 6), (2, 7), (3, 8), (4, 9), (1, 4), (1, 2), (2, 3), (3, 4), (4, 5), (1, 5), (2, 5), (3, 5)]
XYZ = np.array([[-1, 0, 0], [0, -1, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0],       # free nodes 1-5
                [-2, 0, 0], [0, -2, 1], [2, 0, 0], [0, 2, 1]], dtype=float)    # fixed nodes 6-9
N, NF = 5, 4
M = len(BRANCHES)


# ================================================================ section 2.1: branch-node matrix
def branch_node_matrix(branches, n_nodes):
    """c(j, i) = +1 if i = i(j), -1 if i = k(j), 0 otherwise.   Shape (m, n_s)."""
    C_s = np.zeros((len(branches), n_nodes))
    for j, (i, k) in enumerate(branches):          # branch j goes from node i to node k
        C_s[j, i - 1] = +1.0
        C_s[j, k - 1] = -1.0
    return C_s


def split_free_fixed(C_s, n_free):
    """C_s = [C  C_f]: the first n columns belong to free nodes, the rest to fixed ones."""
    C = C_s[:, :n_free]            # (m, n)
    C_f = C_s[:, n_free:]          # (m, n_f)
    return C, C_f


# ================================================================ eq. (1): coordinate differences
def eq1_coordinate_differences(C, C_f, x, y, z, x_f, y_f, z_f):
    """u = C x + C_f x_f,  v = C y + C_f y_f,  w = C z + C_f z_f.   Each of shape (m,)."""
    u = C @ x + C_f @ x_f
    v = C @ y + C_f @ y_f
    w = C @ z + C_f @ z_f
    return u, v, w


def branch_lengths(u, v, w):
    """l_j = sqrt(u_j^2 + v_j^2 + w_j^2)   (the paper writes the vector l and its diagonal L)."""
    return np.sqrt(u**2 + v**2 + w**2)


# ================================================================ eq. (2): equilibrium with forces s
def eq2_equilibrium(C, u, v, w, l, s, p_x, p_y, p_z):
    """C^t U L^-1 s = p_x  (and y, z).  Returns the three out-of-balance vectors (zero at equilibrium).

    U L^-1 s is the vector of x-components of the branch forces: (u_j / l_j) * s_j.
    C^t adds them up at every free node (with the sign of the branch direction).
    """
    U, V, W, L = np.diag(u), np.diag(v), np.diag(w), np.diag(l)
    L_inv = np.linalg.inv(L)                          # 1 / l_j on the diagonal
    out_x = C.T @ U @ L_inv @ s - p_x
    out_y = C.T @ V @ L_inv @ s - p_y
    out_z = C.T @ W @ L_inv @ s - p_z
    return out_x, out_y, out_z


# ================================================================ eq. (3): Jacobians of the lengths
def eq3_length_jacobians(C, u, v, w, l):
    """dl/dx = C^t U L^-1  ... written as in the paper; row j of (dl/dx)^t is d l_j / d x.

    Note: the paper writes dl/dx = C^t U L^-1, whose shape is (n, m); its transpose
    (m, n) is the usual Jacobian with one row per branch length.
    """
    L_inv = np.diag(1.0 / l)
    return C.T @ np.diag(u) @ L_inv, C.T @ np.diag(v) @ L_inv, C.T @ np.diag(w) @ L_inv


# ================================================================ eq. (4): force densities
def eq4_force_densities(l, s):
    """q = L^-1 s,  i.e. q_j = s_j / l_j."""
    return s / l


# ================================================================ eq. (5): equilibrium with q
def eq5_equilibrium_q(C, u, v, w, q, p_x, p_y, p_z):
    """C^t U q = p_x,  C^t V q = p_y,  C^t W q = p_z.   Same as (2) with L^-1 s replaced by q."""
    U, V, W = np.diag(u), np.diag(v), np.diag(w)
    return C.T @ U @ q - p_x, C.T @ V @ q - p_y, C.T @ W @ q - p_z


# ================================================================ eq. (6): the swap identity
def eq6_identity(u, q):
    """U q = Q u : a diagonal matrix times a vector is an element-wise product, so the order can be swapped."""
    U, Q = np.diag(u), np.diag(q)
    return U @ q, Q @ u            # both equal u * q


# ================================================================ eq. (7): equilibrium in the coordinates
def eq7_equilibrium_xyz(C, C_f, q, x, y, z, x_f, y_f, z_f, p_x, p_y, p_z):
    """C^t Q C x + C^t Q C_f x_f = p_x  (and y, z).   Linear in x, y, z because q is fixed."""
    Q = np.diag(q)
    out_x = C.T @ Q @ C @ x + C.T @ Q @ C_f @ x_f - p_x
    out_y = C.T @ Q @ C @ y + C.T @ Q @ C_f @ y_f - p_y
    out_z = C.T @ Q @ C @ z + C.T @ Q @ C_f @ z_f - p_z
    return out_x, out_y, out_z


# ================================================================ eq. (8): D and D_f
def eq8_system(C, C_f, q):
    """D = C^t Q C  (n x n),   D_f = C^t Q C_f  (n x n_f).   Then  D x = p_x - D_f x_f  etc."""
    Q = np.diag(q)
    D = C.T @ Q @ C
    D_f = C.T @ Q @ C_f
    return D, D_f


# ================================================================ eq. (9): the solution
def eq9_solve(D, D_f, x_f, y_f, z_f, p_x, p_y, p_z):
    """x = D^-1 (p_x - D_f x_f),  y = D^-1 (p_y - D_f y_f),  z = D^-1 (p_z - D_f z_f)."""
    x = np.linalg.solve(D, p_x - D_f @ x_f)        # solve() instead of inv() @: same result, better numerics
    y = np.linalg.solve(D, p_y - D_f @ y_f)
    z = np.linalg.solve(D, p_z - D_f @ z_f)
    return x, y, z


# ================================================================ eq. (10): the forces
def eq10_forces(l, q):
    """s = L q,  i.e. s_j = l_j * q_j  with the lengths of the solved geometry."""
    return l * q


# ================================================================ section 4: theorem 1 (eqs. 36-41)
def theorem1_weighted_least_squares(C, C_f, q, x_f, y_f, z_f):
    """Minimise  u^t Q u + v^t Q v + w^t Q w  (eq. 40 with P = Q) over the free coordinates.

    Its minimiser is the unloaded equilibrium (eq. 41 == eq. 7 with p = 0).
    """
    n = C.shape[1]

    def weighted_sum_of_squared_lengths(free_xyz):
        x, y, z = free_xyz.reshape(3, n)
        u, v, w = eq1_coordinate_differences(C, C_f, x, y, z, x_f, y_f, z_f)
        return u @ np.diag(q) @ u + v @ np.diag(q) @ v + w @ np.diag(q) @ w

    result = minimize(weighted_sum_of_squared_lengths, np.zeros(3 * n), method="BFGS", options={"gtol": 1e-12})
    return result.x.reshape(3, n)


def theorem2_minimum_way_net(l, const=1.0):
    """q_j = const / l_j  makes every branch force s_j = q_j l_j = const: the minimum-way net is a net with equal forces."""
    q = const / l
    return q, eq10_forces(l, q)


# ================================================================ section 3: additional conditions
def eq12_constraint_function(q, C, C_f, x_f, y_f, z_f, p_x, p_y, p_z, condition):
    """g*(q) = g(x(q), y(q), z(q), q):  solve (9) for this q, then evaluate the user's condition g."""
    D, D_f = eq8_system(C, C_f, q)
    x, y, z = eq9_solve(D, D_f, x_f, y_f, z_f, p_x, p_y, p_z)
    return condition(x, y, z, q)


def eq13_to_16_linearise(g_star_q0, G_t):
    """g*(q0) + G^t dq = 0  with  G^t = d g* / d q  (eq. 14) and  r = -g*(q0)  (eq. 15):  the linear system  G^t dq = r  (16)."""
    r = -g_star_q0
    return G_t, r


def eq17_least_squares_step(G_t, r):
    """Minimise dq^t dq subject to G^t dq = r:   T = G^t G (23, first case),  k = T^-1 r (24),  dq = G k (25)."""
    G = G_t.T
    T = G_t @ G
    k = np.linalg.solve(T, r)
    return G @ k


def eq18_19_damped_step(G_t, r, P):
    """Conditions G^t dq = r + a, minimise dq^t dq + a^t P a:   T = G^t G + P^-1 (23, second case)."""
    G = G_t.T
    T = G_t @ G + np.linalg.inv(P)
    k = np.linalg.solve(T, r)
    return G @ k


def eq20_21_modified_damped_step(G_t, r, P, a):
    """Conditions G^t dq = A r  (A = diag(a), damping factors), minimise dq^t dq + (e - a)^t P (e - a):
    T = G^t G + P^-1 A^2 (23, third case),  k = T^-1 (A r) (24),  dq = G k (25)."""
    G = G_t.T
    A = np.diag(a)
    T = G_t @ G + np.linalg.inv(P) @ A @ A
    k = np.linalg.solve(T, A @ r)
    return G @ k


def eq25_update(q0, dq):
    """q0 := q0 + dq, then start again with (13) until g*(q0) is zero within tolerance."""
    return q0 + dq


# ================================================================ eqs. (26)-(28): how x, y, z react to q
def eq27_28_coordinate_jacobians(D, C, u, v, w):
    """dx/dq = -D^-1 C^t U,   dy/dq = -D^-1 C^t V,   dz/dq = -D^-1 C^t W.   Each of shape (n, m).

    Derivation (section 3.2): equilibrium C^t U q = p_x must stay true when q and x change,
    d(C^t U q) = C^t U dq + C^t Q C dx = 0, and C^t Q C is D.
    """
    D_inv = np.linalg.inv(D)
    return -D_inv @ C.T @ np.diag(u), -D_inv @ C.T @ np.diag(v), -D_inv @ C.T @ np.diag(w)


def eq26_chain_rule(dg_dx, dg_dy, dg_dz, dg_dq, dx_dq, dy_dq, dz_dq):
    """G^t = dg/dx dx/dq + dg/dy dy/dq + dg/dz dz/dq + dg/dq.   Shape (r, m)."""
    return dg_dx @ dx_dq + dg_dy @ dy_dq + dg_dz @ dz_dq + dg_dq


# ================================================================ eqs. (29)-(31): prescribed distances
def eq29_distance_conditions(l, constrained, l_v):
    """g = l_bar - l_bar_v = 0 : the first r branches (here: the indices in `constrained`) must have lengths l_v."""
    return l[constrained] - l_v


def eq30_31_distance_jacobian(D, C, u, v, w, l, constrained):
    """G_d^t = -L_bar^-1 (U_bar C_bar D^-1 C^t U + V_bar C_bar D^-1 C^t V + W_bar C_bar D^-1 C^t W).   Shape (r, m).

    A bar means "rows of the constrained branches only": C_bar = C[constrained], U_bar = diag(u[constrained]).
    This is (26) with dg/dx = dl_bar/dx = C_bar^t U_bar L_bar^-1 from (3) and dx/dq from (28), and dg/dq = 0.
    """
    D_inv = np.linalg.inv(D)
    C_bar = C[constrained]
    L_bar_inv = np.diag(1.0 / l[constrained])
    K = (np.diag(u[constrained]) @ C_bar @ D_inv @ C.T @ np.diag(u)
         + np.diag(v[constrained]) @ C_bar @ D_inv @ C.T @ np.diag(v)
         + np.diag(w[constrained]) @ C_bar @ D_inv @ C.T @ np.diag(w))
    return -L_bar_inv @ K


# ================================================================ eqs. (32)-(34): prescribed forces
def eq32_force_conditions(l, q, constrained, s_v):
    """g = L_bar q_bar - s_bar_v = 0 : the constrained branches must carry forces s_v."""
    return l[constrained] * q[constrained] - s_v


def eq33_34_force_jacobian(D, C, u, v, w, l, q, constrained):
    """G_f^t = L_bar - Q_bar L_bar^-1 (U_bar C_bar D^-1 C^t U + ...).   Shape (r, m).

    dg/dq = L_bar (eq. 33) is the direct effect of q_j on s_j = l_j q_j; the second term is the
    change of the lengths, i.e. q_bar times the distance Jacobian (31) with its sign.
    """
    G_d_t = eq30_31_distance_jacobian(D, C, u, v, w, l, constrained)       # = -L_bar^-1 K
    L_bar = np.zeros((len(constrained), C.shape[0]))                     # L_bar as an (r, m) selector of l_j
    for row, j in enumerate(constrained):
        L_bar[row, j] = l[j]
    return L_bar + np.diag(q[constrained]) @ G_d_t                       # L_bar - Q_bar L_bar^-1 K


# ================================================================ eq. (35): prescribed unstrained lengths
def unstrained_length(l, s, h):
    """Hooke's law as the paper writes it: l_u = h l / (h + s), with h the axial stiffness E A of the branch."""
    return h * l / (h + s)


def eq35_unstrained_length_jacobian(D, C, u, v, w, l, q, h, constrained):
    """G_u^t = -L_u_bar^2 H_bar^-1 - L_u_bar^2 L_bar^-3 (U_bar C_bar D^-1 C^t U + ...).   Shape (r, m).

    Tends to G_d^t as h -> infinity (an inextensible bar is a distance condition).
    """
    s = l * q
    l_u = unstrained_length(l, s, h)
    G_d_t = eq30_31_distance_jacobian(D, C, u, v, w, l, constrained)       # = -L_bar^-1 K
    K = -np.diag(l[constrained]) @ G_d_t
    L_u_bar2 = np.diag(l_u[constrained] ** 2)
    first = np.zeros((len(constrained), C.shape[0]))                     # -L_u_bar^2 H_bar^-1, placed on the own column
    for row, j in enumerate(constrained):
        first[row, j] = -l_u[j] ** 2 / h[j]
    return first - L_u_bar2 @ np.diag(1.0 / l[constrained] ** 3) @ K


# ================================================================ the two solvers, chained from the functions above
def linear_solver(branches, n_free, xyz_fixed, q, p):
    """Schek section 2 = compas_fd.fd_numpy.   Executes (8) -> (9) -> (1) -> (10); nothing else.

    (2) to (7) are not run: they are the derivation that turns the nonlinear equilibrium (2)
    into the linear system (8).  Returns free coordinates, lengths, forces.
    """
    C_s = branch_node_matrix(branches, n_free + len(xyz_fixed))     # section 2.1
    C, C_f = split_free_fixed(C_s, n_free)
    x_f, y_f, z_f = xyz_fixed.T
    D, D_f = eq8_system(C, C_f, q)                                   # (8)   D and D_f from q and topology only
    x, y, z = eq9_solve(D, D_f, x_f, y_f, z_f, *p.T)                 # (9)   one linear solve per axis
    u, v, w = eq1_coordinate_differences(C, C_f, x, y, z, x_f, y_f, z_f)   # (1)   geometry of the result
    l = branch_lengths(u, v, w)
    s = eq10_forces(l, q)                                            # (10)  forces from lengths and q
    return np.vstack([x, y, z]).T, l, s


def constrained_solver(branches, n_free, xyz_fixed, q0, p, constrained, l_v, a=0.8, P_scale=1e6, kmax=100, tol=1e-10):
    """Schek section 3 for prescribed lengths l_v on the branches `constrained`.

    Every iteration is: linear solve (8)-(9)-(1)  ->  conditions (29)  ->  Jacobian (31), which
    inside uses (28) and (3)/(30)  ->  one damped least-squares step (15), (23), (24), (25).
    compas_fd does not contain this loop; it is what compas_dr's lpre/fpre terms approximate.
    """
    C_s = branch_node_matrix(branches, n_free + len(xyz_fixed))
    C, C_f = split_free_fixed(C_s, n_free)
    x_f, y_f, z_f = xyz_fixed.T
    q = q0.copy()
    P = np.eye(len(constrained)) * P_scale
    for it in range(kmax):
        D, D_f = eq8_system(C, C_f, q)                               # (8)
        x, y, z = eq9_solve(D, D_f, x_f, y_f, z_f, *p.T)             # (9)   geometry for the current q
        u, v, w = eq1_coordinate_differences(C, C_f, x, y, z, x_f, y_f, z_f)   # (1)
        l = branch_lengths(u, v, w)
        g = eq29_distance_conditions(l, constrained, l_v)            # (29)  how far from the prescribed lengths
        if np.abs(g).max() < tol:
            break
        G_t = eq30_31_distance_jacobian(D, C, u, v, w, l, constrained)   # (31)  = (26) with (28) and (30)
        G_t, r = eq13_to_16_linearise(g, G_t)                        # (15)  r = -g
        dq = eq20_21_modified_damped_step(G_t, r, P, np.full(len(constrained), a))   # (23), (24), (25)
        q = eq25_update(q, dq)                                       # q := q + dq, repeat
    xyz, l, s = linear_solver(branches, n_free, xyz_fixed, q, p)     # final geometry for the converged q
    return xyz, l, s, q, it


# ================================================================ run everything on the figure-2 network
def main():
    C_s = branch_node_matrix(BRANCHES, N + NF)
    C, C_f = split_free_fixed(C_s, N)
    x_f, y_f, z_f = XYZ[N:, 0], XYZ[N:, 1], XYZ[N:, 2]
    p_x, p_y = np.zeros(N), np.zeros(N)
    p_z = np.full(N, -0.5)
    q = np.array([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1], dtype=float)

    # (8), (9): the linear solve
    D, D_f = eq8_system(C, C_f, q)
    x, y, z = eq9_solve(D, D_f, x_f, y_f, z_f, p_x, p_y, p_z)
    u, v, w = eq1_coordinate_differences(C, C_f, x, y, z, x_f, y_f, z_f)   # (1)
    l = branch_lengths(u, v, w)
    s = eq10_forces(l, q)                                                   # (10)
    print("(9)  free x:", x, "\n     free y:", y, "\n     free z:", z)
    print("(10) forces s = l q:", s)

    # (2), (5), (7) must all say "in equilibrium" for the solved geometry
    for name, out in [("(2)", eq2_equilibrium(C, u, v, w, l, s, p_x, p_y, p_z)),
                      ("(5)", eq5_equilibrium_q(C, u, v, w, q, p_x, p_y, p_z)),
                      ("(7)", eq7_equilibrium_xyz(C, C_f, q, x, y, z, x_f, y_f, z_f, p_x, p_y, p_z))]:
        print(f"{name} max out-of-balance: {max(np.abs(o).max() for o in out):.1e}")
    # (4) recovers q from s and l; (6) is an identity
    assert np.allclose(eq4_force_densities(l, s), q)
    a, b = eq6_identity(u, q); assert np.allclose(a, b)
    print("(4) q = s / l recovered; (6) U q == Q u holds")

    # (3): dl/dx against finite differences
    dl_dx, _, _ = eq3_length_jacobians(C, u, v, w, l)      # paper's shape (n, m); transpose = d l_j / d x_i
    h = 1e-6; fd = np.zeros((M, N))
    for i in range(N):
        xp = x.copy(); xp[i] += h
        up, vp, wp = eq1_coordinate_differences(C, C_f, xp, y, z, x_f, y_f, z_f)
        fd[:, i] = (branch_lengths(up, vp, wp) - l) / h
    print(f"(3)  |dl/dx - finite differences| = {np.abs(dl_dx.T - fd).max():.1e}")

    # theorem 1: unloaded equilibrium == weighted least squares of lengths
    D0, D_f0 = eq8_system(C, C_f, q)
    x0, y0, z0 = eq9_solve(D0, D_f0, x_f, y_f, z_f, np.zeros(N), np.zeros(N), np.zeros(N))
    xyz_min = theorem1_weighted_least_squares(C, C_f, q, x_f, y_f, z_f)
    print(f"Thm1 |equilibrium - minimiser| = {np.abs(np.vstack([x0, y0, z0]) - xyz_min).max():.1e}")
    q2, s2 = theorem2_minimum_way_net(l)
    print("Thm2 q = 1/l gives forces:", s2)

    # (27)-(28): dx/dq against finite differences
    dx_dq, dy_dq, dz_dq = eq27_28_coordinate_jacobians(D, C, u, v, w)
    fd = np.zeros((N, M))
    for j in range(M):
        qp = q.copy(); qp[j] += h
        Dp, D_fp = eq8_system(C, C_f, qp)
        fd[:, j] = (eq9_solve(Dp, D_fp, x_f, y_f, z_f, p_x, p_y, p_z)[0] - x) / h
    print(f"(28) |dx/dq - finite differences| = {np.abs(dx_dq - fd).max():.1e}")

    # (29)-(31): distance conditions on the four anchor branches, and the three step rules
    constrained = [0, 1, 2, 3]
    l_v = np.full(4, 1.2)
    g = eq29_distance_conditions(l, constrained, l_v)
    G_t = eq30_31_distance_jacobian(D, C, u, v, w, l, constrained)
    fd = np.zeros((4, M))
    for j in range(M):
        qp = q.copy(); qp[j] += h
        fd[:, j] = (eq12_constraint_function(qp, C, C_f, x_f, y_f, z_f, p_x, p_y, p_z,
                                             lambda X, Y, Z, Q_: eq29_distance_conditions(
                                                 branch_lengths(*eq1_coordinate_differences(C, C_f, X, Y, Z, x_f, y_f, z_f)),
                                                 constrained, l_v)) - g) / h
    print(f"(31) |G_d^t - finite differences| = {np.abs(G_t - fd).max():.1e}")
    G_t, r = eq13_to_16_linearise(g, G_t)
    P = np.eye(4) * 1e6
    for name, dq in [("(17)", eq17_least_squares_step(G_t, r)),
                     ("(18-19)", eq18_19_damped_step(G_t, r, P)),
                     ("(20-21)", eq20_21_modified_damped_step(G_t, r, P, np.full(4, 0.8)))]:
        print(f"{name} first step dq = {dq}")

    # iterate the modified damped rule to convergence
    qk = q.copy()
    for it in range(50):
        Dk, D_fk = eq8_system(C, C_f, qk)
        xk, yk, zk = eq9_solve(Dk, D_fk, x_f, y_f, z_f, p_x, p_y, p_z)
        uk, vk, wk = eq1_coordinate_differences(C, C_f, xk, yk, zk, x_f, y_f, z_f)
        lk = branch_lengths(uk, vk, wk)
        gk = eq29_distance_conditions(lk, constrained, l_v)
        if np.abs(gk).max() < 1e-12:
            break
        G_tk, rk = eq13_to_16_linearise(gk, eq30_31_distance_jacobian(Dk, C, uk, vk, wk, lk, constrained))
        qk = eq25_update(qk, eq20_21_modified_damped_step(G_tk, rk, P, np.full(4, 0.8)))
    print(f"(25) converged in {it} iterations: constrained lengths {lk[constrained]}, q {qk[constrained]}")

    # (32)-(34): force conditions, Jacobian against finite differences
    s_v = np.full(4, 2.0)
    g_f = eq32_force_conditions(l, q, constrained, s_v)
    G_f_t = eq33_34_force_jacobian(D, C, u, v, w, l, q, constrained)
    fd = np.zeros((4, M))
    for j in range(M):
        qp = q.copy(); qp[j] += h
        Dp, D_fp = eq8_system(C, C_f, qp)
        xp, yp, zp = eq9_solve(Dp, D_fp, x_f, y_f, z_f, p_x, p_y, p_z)
        lp = branch_lengths(*eq1_coordinate_differences(C, C_f, xp, yp, zp, x_f, y_f, z_f))
        fd[:, j] = (eq32_force_conditions(lp, qp, constrained, s_v) - g_f) / h
    print(f"(34) |G_f^t - finite differences| = {np.abs(G_f_t - fd).max():.1e}")

    # (35): unstrained lengths with stiffness h, Jacobian against finite differences
    hs = np.full(M, 50.0)
    g_u = unstrained_length(l, s, hs)[constrained]
    G_u_t = eq35_unstrained_length_jacobian(D, C, u, v, w, l, q, hs, constrained)
    fd = np.zeros((4, M))
    for j in range(M):
        qp = q.copy(); qp[j] += h
        Dp, D_fp = eq8_system(C, C_f, qp)
        xp, yp, zp = eq9_solve(Dp, D_fp, x_f, y_f, z_f, p_x, p_y, p_z)
        lp = branch_lengths(*eq1_coordinate_differences(C, C_f, xp, yp, zp, x_f, y_f, z_f))
        fd[:, j] = (unstrained_length(lp, lp * qp, hs)[constrained] - g_u) / h
    print(f"(35) |G_u^t - finite differences| = {np.abs(G_u_t - fd).max():.1e}")
    # the two chained solvers reproduce the results above
    xyz_lin, l_lin, s_lin = linear_solver(BRANCHES, N, XYZ[N:], q, np.c_[p_x, p_y, p_z])
    assert np.allclose(xyz_lin[:, 0], x) and np.allclose(s_lin, s)
    xyz_c, l_c, s_c, q_c, its = constrained_solver(BRANCHES, N, XYZ[N:], q, np.c_[p_x, p_y, p_z], constrained, l_v)
    print(f"linear_solver == (9),(10); constrained_solver: lengths {l_c[constrained]} after {its} iterations")

    G_u_stiff = eq35_unstrained_length_jacobian(D, C, u, v, w, l, q, np.full(M, 1e9), constrained)
    print(f"(35) h -> inf: |G_u^t - G_d^t| = {np.abs(G_u_stiff - eq30_31_distance_jacobian(D, C, u, v, w, l, constrained)).max():.1e}")


if __name__ == "__main__":
    main()
