"""A force density application written from Schek (1974), section by section.

Read it top to bottom: each cell (`# %% [id] title`) is one section of the paper, with
the paper's statement as a docstring and the code that adds that section to the program.
Running the file executes every cell in order and prints the results; `build_note.py`
turns the same cells into the tutorial in knowledge/04_form_finding/compas_fd.md.

Only numpy is used.  Nothing here is taken from compas_fd; the application is derived
from the paper and compas_fd is compared with it afterwards in the note.

    python examples/form_finding/schek_app.py
"""

# %% [setup] Notation (section 1.4)
r"""The paper writes a vector as a lower-case letter and the diagonal matrix built from
it as the same capital letter: for the vector $u$ the matrix $U$ has $u$ on its
diagonal. A general matrix is a capital letter, $C^{t}$ is the transpose. In the
program a vector is a 1-D NumPy array, the diagonal matrix is `np.diag(u)`, the
transpose is `C.T`, and `@` is the matrix product."""
import numpy as np

np.set_printoptions(precision=3, suppress=True, linewidth=120)


def diag(vector):
    """The paper's capital-letter matrix of a vector: U = diag(u)."""
    return np.diag(vector)


def show(name, M, rows=None, cols=None, fmt="{:>7.2f}", zero="      ."):
    """Print a matrix the way the paper prints figures 2 and 4: a dot for a zero."""
    M = np.atleast_2d(M)
    print(f"{name}  shape {M.shape}")
    if cols is not None:
        print("     " + "".join(f"{c:>7}" for c in cols))
    for r, row in enumerate(M):
        label = f"{rows[r]:>4} " if rows is not None else "     "
        print(label + "".join(zero if abs(v) < 1e-12 else fmt.format(v) for v in row))


# %% [s21] Section 2.1: the branch-node matrix
r"""Number the nodes $1 \ldots n_s$ and the branches $1 \ldots m$ in any order, but put
the nodes that will be fixed at the end: $n$ free nodes first, then $n_f$ fixed ones,
$n_s = n + n_f$. For every branch $j$ record its two end nodes $i(j)$ and $k(j)$. The
branch-node matrix $C_s$ has one row per branch and one column per node:

$$
c(j, i) =
\begin{cases}
+1 & \text{if } i = i(j) \\
-1 & \text{if } i = k(j) \\
0 & \text{otherwise}
\end{cases}
$$

Because the fixed nodes come last, the matrix splits into two column blocks,
$C_s = [C \quad C_f]$: $C$ ($m \times n$) for the free nodes and $C_f$
($m \times n_f$) for the fixed ones. The example is the network of the paper's
figure 2: nodes 1 to 5 free, 6 to 9 fixed, 12 branches.

![Fig. 2](images/schek_fig2.png)

*Fig. 2, redrawn: the graph and its branch-node matrix.*"""
branches = [(1, 6), (2, 7), (3, 8), (4, 9),      # 1-4: one branch from each free corner to its anchor
            (1, 4), (1, 2), (2, 3), (3, 4),      # 5-8: the ring
            (4, 5), (1, 5), (2, 5), (3, 5)]      # 9-12: four spokes to the centre node 5
n, n_f = 5, 4                                    # free nodes 1..5, fixed nodes 6..9
m = len(branches)

C_s = np.zeros((m, n + n_f))
for j, (i, k) in enumerate(branches):
    C_s[j, i - 1] = +1.0                          # node i(j): +1   (Python indices start at 0)
    C_s[j, k - 1] = -1.0                          # node k(j): -1
C = C_s[:, :n]                                    # (m, n)   free columns
C_f = C_s[:, n:]                                  # (m, n_f) fixed columns

show("C_s = [C  C_f]   (figure 2)", C_s, range(1, m + 1), range(1, n + n_f + 1), fmt="{:>7.0f}")


# %% [matrices] What the paper does with matrices, shown on this small network
r"""The paper uses five matrix operations and nothing else. Each one is shown here
twice on the figure 2 network: as a loop over branches and nodes, which says what is
being computed, and as the NumPy product, which is how the rest of the program
writes it. Both give the same numbers.

1. **A matrix is a table.** $C_s$ has one row per branch and one column per node;
   the entry in row $j$, column $i$ says how node $i$ enters branch $j$ ($+1$ start,
   $-1$ end, $0$ not at all).
2. **Matrix times vector = one number per row.** $C_s x$ takes every row of $C_s$,
   multiplies it entry by entry with the vector $x$ of node coordinates and adds up.
   Because a row holds one $+1$ and one $-1$, the result for branch $j$ is
   "coordinate of the start node minus coordinate of the end node".
3. **Transpose times vector = add up at the nodes.** $C^{t}$ swaps rows and
   columns, so $C^{t} f$ has one number per *node*: the sum of the branch values $f_j$
   of the branches at that node, with $+$ for branches that start there and $-$ for
   branches that end there. This is how the paper sums forces at a node.
4. **Diagonal matrix times vector = scale each entry.** $Q u$ with $Q = $ `diag(q)`
   is just $q_j u_j$ for every branch, which is why $U q = Q u$ (equation 6).
5. **Solving $D x = b$** means finding the $x$ that makes $D x$ equal to $b$;
   `np.linalg.solve` does it without forming $D^{-1}$. Check: $D x$ reproduces $b$."""
# 2. matrix times vector, by loop and by product
x_demo = np.array([-1.0, 0.0, 1.0, 0.0, 0.0, -2.0, 0.0, 2.0, 0.0])      # one x coordinate per node 1..9
by_loop = np.zeros(m)
for j, (i, k) in enumerate(branches):
    by_loop[j] = x_demo[i - 1] - x_demo[k - 1]                           # start minus end
by_product = C_s @ x_demo                                                # the same, written as a matrix product
print("2. C_s @ x by loop   :", by_loop)
print("   C_s @ x by product:", by_product)

# 3. transpose times vector: add the branch values up at every node, with the branch sign
f_demo = np.arange(1, m + 1, dtype=float)                                # pretend branch j carries the value j
at_nodes = np.zeros(n + n_f)
for j, (i, k) in enumerate(branches):
    at_nodes[i - 1] += f_demo[j]                                         # branch starts here: +
    at_nodes[k - 1] -= f_demo[j]                                         # branch ends here:   -
print("3. C_s^t f by loop   :", at_nodes)
print("   C_s^t f by product:", C_s.T @ f_demo)

# 4. a diagonal matrix scales entry by entry
q_demo = np.array([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1], dtype=float)
print("4. diag(q) @ u == q * u:", np.allclose(diag(q_demo) @ by_product, q_demo * by_product))

# 1 + 3 + 4 together: one entry of D = C^t Q C computed by hand (figure 4: node 1 touches branches 1, 5, 6, 10)
D_demo = C.T @ diag(q_demo) @ C
print("   D[1,1] by hand: q1 + q5 + q6 + q10 =", q_demo[0] + q_demo[4] + q_demo[5] + q_demo[9], "  by product:", D_demo[0, 0])
print("   D[1,2] by hand: -q6 =", -q_demo[5], "  by product:", D_demo[0, 1])

# 5. solving a linear system
b_demo = np.array([1.0, 0.0, 0.0, 0.0, 0.0])
x_sol = np.linalg.solve(D_demo, b_demo)
print("5. solve D x = b gives x =", x_sol, "; check D @ x =", D_demo @ x_sol)


# %% [s22a] Section 2.2: the data of the problem
r"""The nodes are points $P_i = (x_i, y_i, z_i)$. The free coordinates form the
$n$-vectors $x, y, z$ (the unknowns); the fixed coordinates form the $n_f$-vectors
$x_f, y_f, z_f$ (given). Every free node carries a load with components
$p_x, p_y, p_z$ (given). Every branch has a length $l_j$ and a force $s_j$ (unknown).

These numbers are not in the paper: the anchors are placed on a square, two of them
lifted, and a small downward load acts on every free node."""
x_f = np.array([-2.0, 0.0, 2.0, 0.0])             # anchors 6, 7, 8, 9
y_f = np.array([0.0, -2.0, 0.0, 2.0])
z_f = np.array([0.0, 1.0, 0.0, 1.0])             # two anchors lifted by 1 m
p_x = np.zeros(n)
p_y = np.zeros(n)
p_z = np.full(n, -0.5)                            # 0.5 kN downward at every free node


# %% [s22b] Equations (1) and (2): equilibrium with the unknown forces
r"""Multiplying the coordinates by the branch-node matrix gives, for every branch, the
difference of the coordinates of its two end nodes (1):

$$
u = C x + C_f x_f, \qquad v = C y + C_f y_f, \qquad w = C z + C_f z_f
$$

Dividing by the length gives the direction cosines $u_j / l_j$, and multiplying by the
force gives the force components. Summing them at every free node (that is what
$C^{t}$ does) must give the load. This is the equilibrium (2):

$$
C^{t} U L^{-1} s = p_x, \qquad C^{t} V L^{-1} s = p_y, \qquad C^{t} W L^{-1} s = p_z
$$

It is **nonlinear** in the coordinates: $u, v, w$ and $l$ all depend on them and $l$
holds a square root. The function below evaluates it for any trial geometry; for a
random guess it is not satisfied."""
def coordinate_differences(x, y, z):
    """Eq. (1).  Returns u, v, w and the lengths l (each of shape (m,))."""
    u = C @ x + C_f @ x_f
    v = C @ y + C_f @ y_f
    w = C @ z + C_f @ z_f
    l = np.sqrt(u**2 + v**2 + w**2)
    return u, v, w, l


def equilibrium_error(x, y, z, s):
    """Eq. (2): C^t U L^-1 s - p for the three axes.  All zeros means the net is in equilibrium."""
    u, v, w, l = coordinate_differences(x, y, z)
    L_inv = diag(1.0 / l)
    return (C.T @ diag(u) @ L_inv @ s - p_x,
            C.T @ diag(v) @ L_inv @ s - p_y,
            C.T @ diag(w) @ L_inv @ s - p_z)


x_guess = np.array([-1.0, 0.0, 1.0, 0.0, 0.0])    # a flat guess for the free nodes
y_guess = np.array([0.0, -1.0, 0.0, 1.0, 0.0])
z_guess = np.zeros(n)
s_guess = np.ones(m)                              # 1 kN in every branch
ex, ey, ez = equilibrium_error(x_guess, y_guess, z_guess, s_guess)
print("out of balance at the free nodes for the flat guess, z direction:", ez)


# %% [s22c] Equations (4) to (8): the force density turns (2) into a linear system
r"""Define for every branch the force density (4), the ratio of force to length:

$$
q = L^{-1} s \qquad\text{i.e.}\qquad q_j = s_j / l_j
$$

Written with $q$, the equilibrium (2) becomes (5), $C^{t} U q = p_x$ and so on.
A diagonal matrix times a vector is an element-wise product, so the factors can be
swapped (6): $U q = Q u$. Insert (1) for $u$ and the geometry appears outside the
matrix (7):

$$
C^{t} Q C x + C^{t} Q C_f x_f = p_x \qquad \text{(and the same for } y, z)
$$

With the abbreviations $D = C^{t} Q C$ and $D_f = C^{t} Q C_f$ this is (8):

$$
D x = p_x - D_f x_f, \qquad D y = p_y - D_f y_f, \qquad D z = p_z - D_f z_f
$$

$D$ is built from the topology and $q$ alone. Its diagonal entry for node $i$ is
the sum of the $q$ of the branches at $i$, its entry $(i, k)$ is $-q_j$ for the
branch joining $i$ and $k$, zero otherwise. That is the paper's figure 4.

![Fig. 4](images/schek_fig4.png)

*Fig. 4, redrawn: the structure of $D$ for the graph of fig. 2.*

The paper's figures stop here: figure 2 is $C_s$ and figure 4 is the pattern of
$D$. The numbers that give an actual shape, the anchors $x_f$, the loads $p$, the
values of $q$ and the matrix $D_f$, are not drawn. The program has all of them."""
q = np.array([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1], dtype=float)   # one force density per branch: the design input

Q = diag(q)
D = C.T @ Q @ C                                   # (n, n)   eq. (8)
D_f = C.T @ Q @ C_f                               # (n, n_f)

show("D = C^t Q C   (figure 4 with numbers)", D, range(1, n + 1), range(1, n + 1))
show("D_f = C^t Q C_f", D_f, range(1, n + 1), range(n + 1, n + n_f + 1))
show("right-hand sides  p - D_f x_f  (columns x, y, z)", np.c_[p_x - D_f @ x_f, p_y - D_f @ y_f, p_z - D_f @ z_f],
     range(1, n + 1), ["x", "y", "z"])


# %% [s22d] Equations (9) and (10): solve
r"""One linear solve per axis gives the free coordinates (9), and the lengths of the
solved geometry times the force densities give the forces (10):

$$
x = D^{-1}(p_x - D_f x_f), \quad y = D^{-1}(p_y - D_f y_f), \quad z = D^{-1}(p_z - D_f z_f),
\qquad s = L q
$$

The paper's conclusions: the system is linear; $D$ is positive definite for a
prestressed net ($q_j \gt 0$) without isolated free nodes, so the solution exists and is
unique; and every vector $q$ gives exactly one equilibrium shape, so $q$ is the right
set of design parameters. Checking (2) on the result confirms the equilibrium."""
x = np.linalg.solve(D, p_x - D_f @ x_f)            # eq. (9)
y = np.linalg.solve(D, p_y - D_f @ y_f)
z = np.linalg.solve(D, p_z - D_f @ z_f)
u, v, w, l = coordinate_differences(x, y, z)      # eq. (1) on the solution
s = l * q                                         # eq. (10)

show("free node coordinates (columns x, y, z)", np.c_[x, y, z], range(1, n + 1), ["x", "y", "z"])
print("lengths l:", l)
print("forces  s:", s)
print("equilibrium error (2) on the solution:", max(np.abs(e).max() for e in equilibrium_error(x, y, z, s)))


# %% [s22e] Figure 3: the form-finding loop as one function
r"""Figure 3 of the paper is the workflow: build $C$, build $D$ and the right-hand
sides, solve, compute lengths and forces, look at the shape, then change the fixed
points or the load (only the right-hand side changes), the force densities ($D$ is
rebuilt), or the connectivity ($C$ is rebuilt), and solve again. The whole linear
method is this function.

![Fig. 3](images/schek_fig3.png)

*Fig. 3, redrawn: the diagram of the form finding.*"""
def form_finding(branches, n_free, xyz_fixed, q, p):
    """Schek section 2 as one call.  xyz_fixed: (n_f, 3); p: (n_free, 3) loads; q: (m,)."""
    n_s = n_free + len(xyz_fixed)
    C_s = np.zeros((len(branches), n_s))
    for j, (i, k) in enumerate(branches):
        C_s[j, i - 1], C_s[j, k - 1] = 1.0, -1.0                      # section 2.1
    C, C_f = C_s[:, :n_free], C_s[:, n_free:]
    D, D_f = C.T @ diag(q) @ C, C.T @ diag(q) @ C_f                    # eq. (8)
    xyz = np.vstack([np.linalg.solve(D, p[:, a] - D_f @ xyz_fixed[:, a]) for a in range(3)]).T   # eq. (9)
    uvw = C @ xyz + C_f @ xyz_fixed                                    # eq. (1), three columns
    l = np.linalg.norm(uvw, axis=1)
    s = l * q                                                          # eq. (10)
    reactions = -(C_f.T @ diag(q) @ uvw)                               # eq. (5) at the fixed nodes
    return xyz, l, s, reactions


xyz_fixed = np.c_[x_f, y_f, z_f]
p = np.c_[p_x, p_y, p_z]
xyz1, l1, s1, R1 = form_finding(branches, n, xyz_fixed, q, p)
print("same solution from the function:", np.allclose(xyz1[:, 2], z))
print("reactions at the anchors (sum of z components equals the total load):", R1[:, 2], R1[:, 2].sum())

# a change of fixed points: only the right-hand side changes
xyz2, *_ = form_finding(branches, n, xyz_fixed + np.array([0, 0, 1.0]), q, p)
# a change of force densities: D is rebuilt
xyz3, *_ = form_finding(branches, n, xyz_fixed, np.where(np.arange(m) < 4, 10.0, 1.0), p)
print("centre node height: base %.3f | anchors lifted by 1 m %.3f | anchor branches q = 10: %.3f" % (xyz1[4, 2], xyz2[4, 2], xyz3[4, 2]))


# %% [s4] Section 4: what the force densities mean geometrically
r"""Forget forces for a moment and ask for the node positions that make the weighted
sum of squared branch lengths smallest, with weights $P$ (40):

$$
u^{t} P u + v^{t} P v + w^{t} P w \to \min
$$

Setting the derivative with respect to $x$ to zero, with $\partial u / \partial x = C$
(38), gives $(C^{t} P C) x = -(C^{t} P C_f) x_f$ (41): exactly (8) with $Q = P$ and
no load. **Theorem 1:** an unloaded net with force densities $q$ is the net whose
sum of squared branch lengths weighted by $q$ is minimal. **Theorem 2:** choosing
$q_j = c / l_j$ makes every force $s_j = q_j l_j = c$ equal, so a *minimum way net*
(minimal sum of lengths) is a prestressed net with the same force everywhere.
The check below evaluates the gradient of (40) at the unloaded solution of (8)."""
xyz0, l0, s0, _ = form_finding(branches, n, xyz_fixed, q, np.zeros((n, 3)))      # no load
uvw0 = C @ xyz0 + C_f @ xyz_fixed
gradient = 2 * C.T @ diag(q) @ uvw0                                              # d/dx of u^t Q u, per axis
print("Theorem 1: gradient of the weighted squared lengths at the unloaded equilibrium:", np.abs(gradient).max())
q_const = 1.0 / l0                                                               # Theorem 2
print("Theorem 2: forces with q = 1 / l:", l0 * q_const)


# %% [s31] Section 3.1: additional conditions and the damped least-squares step
r"""The linear method satisfies nothing but equilibrium. To prescribe, say, the lengths
of some branches, the paper keeps the linear solve and iterates on $q$. Write the
$r$ conditions as functions that must vanish (11); through (9) they depend on $q$
alone (12): $g^{\ast}(q) = 0$. Starting from the linear solution $q^{(0)}$,
linearise (13) to (16):

$$
G^{t} := \frac{\partial g^{\ast}}{\partial q}, \qquad r := -g^{\ast}(q^{(0)}), \qquad G^{t}\,\Delta q = r
$$

$G^{t}$ is $r \times m$; with fewer conditions than branches there are many
solutions, so the paper picks the one that minimises $\Delta q^{t} \Delta q$ (17),
or with "damped" conditions $G^{t}\Delta q = r + a$ (18, 19), or, best in practice,
the "modified damped" conditions $G^{t}\Delta q = A r$ with damping factors
$a_j$ on the diagonal of $A$ (20, 21). All three lead to a small $r \times r$ system
for the Lagrange multipliers $k$ (22 to 24) and the update (25):

$$
T = G^{t} G + P^{-1} A^{2}, \qquad k = T^{-1} A r, \qquad \Delta q = G k, \qquad q^{(0)} := q^{(0)} + \Delta q
$$

($P^{-1}$ drops out for the plain least squares, $A$ for the first damped variant.)
The number of equations is $r$, not the number of nodes."""
def damped_step(G_t, g, a=0.8, P_inv_scale=1e-6):
    """One modified damped least-squares step, eqs. (20) to (25).  Returns dq (shape (m,))."""
    G = G_t.T
    A = diag(np.full(len(g), a))
    T = G_t @ G + P_inv_scale * A @ A              # eq. (23), third case
    k = np.linalg.solve(T, A @ (-g))               # eqs. (15), (24)
    return G @ k                                   # eq. (25)


# %% [s32] Section 3.2: how the coordinates react to the force densities
r"""To form $G^{t}$ one needs $\partial x / \partial q$. Inverting $D$ symbolically is
hopeless, so differentiate the equilibrium (5) implicitly: a change $dq$ with a change
$dx$ must keep $C^{t} U q = p_x$ true,

$$
C^{t} U\, dq + C^{t} Q C\, dx = 0
\qquad\Longrightarrow\qquad
\frac{\partial x}{\partial q} = -D^{-1} C^{t} U, \quad
\frac{\partial y}{\partial q} = -D^{-1} C^{t} V, \quad
\frac{\partial z}{\partial q} = -D^{-1} C^{t} W
$$

(27, 28). Then the chain rule (26) gives any condition's Jacobian:
$G^{t} = \partial g/\partial x \cdot \partial x/\partial q + \ldots + \partial g/\partial q$."""
def coordinate_jacobians(D, u, v, w):
    """Eq. (28): dx/dq, dy/dq, dz/dq, each (n, m)."""
    D_inv = np.linalg.inv(D)
    return -D_inv @ C.T @ diag(u), -D_inv @ C.T @ diag(v), -D_inv @ C.T @ diag(w)


# %% [s33] Sections 3.3 to 3.5: distance, force and unstrained-length conditions
r"""Prescribed strained lengths $\bar l_v$ for a set of branches (a bar means "rows of
the constrained branches only"): $g = \bar l - \bar l_v$ (29). With
$\partial l / \partial x = C^{t} U L^{-1}$ from (3) and $\partial x / \partial q$ from
(28), the chain rule gives (31):

$$
G_d^{t} = -\bar L^{-1}\left(\bar U \bar C D^{-1} C^{t} U + \bar V \bar C D^{-1} C^{t} V + \bar W \bar C D^{-1} C^{t} W\right)
$$

Prescribed forces $\bar s_v$: $g = \bar L \bar q - \bar s_v$ (32); the direct
derivative is $\partial g / \partial q = \bar L$ (33), and (34):

$$
G_f^{t} = \bar L - \bar Q \bar L^{-1}\left(\bar U \bar C D^{-1} C^{t} U + \ldots\right)
$$

Prescribed unstrained lengths with Hooke's law $l_u = h\,l / (h + s)$ and stiffness
$h$ give (35), which tends to (31) as $h \to \infty$. Mixed conditions (3.6) stack the
rows: $G^{t} = [G_d^{t};\ G_f^{t};\ G_u^{t}]$. All three share the kernel
$C D^{-1} C^{t}$."""
def distance_jacobian(D, u, v, w, l, rows):
    """Eq. (31) for the branches in `rows`.  Returns g's Jacobian G_d^t of shape (r, m)."""
    D_inv = np.linalg.inv(D)
    C_bar = C[rows]
    K = (diag(u[rows]) @ C_bar @ D_inv @ C.T @ diag(u)
         + diag(v[rows]) @ C_bar @ D_inv @ C.T @ diag(v)
         + diag(w[rows]) @ C_bar @ D_inv @ C.T @ diag(w))
    return -diag(1.0 / l[rows]) @ K


def force_jacobian(D, u, v, w, l, q, rows):
    """Eq. (34): L_bar on the own columns plus q_bar times the length change."""
    G_f_t = diag(q[rows]) @ distance_jacobian(D, u, v, w, l, rows)
    for row, j in enumerate(rows):
        G_f_t[row, j] += l[j]                      # dg/dq = L_bar, eq. (33)
    return G_f_t


def unstrained_length_jacobian(D, u, v, w, l, q, h, rows):
    """Eq. (35) with Hooke's law l_u = h l / (h + s)."""
    s = l * q
    l_u = h * l / (h + s)
    K = -diag(l[rows]) @ distance_jacobian(D, u, v, w, l, rows)
    G_u_t = -diag(l_u[rows] ** 2 / l[rows] ** 3) @ K
    for row, j in enumerate(rows):
        G_u_t[row, j] += -l_u[j] ** 2 / h[j]
    return G_u_t


# %% [s3loop] Section 3 assembled: constrained form finding
r"""Each iteration is one linear solve (section 2) plus one small solve (section 3):
geometry for the current $q$, evaluate the conditions, stop if they hold, else build
$G^{t}$, take a damped step, update $q$. The paper leaves the damping factors $a_j$
and the weights $P$ to the user and notes that with unattainable conditions "a damped
sequence may stop at a shape which fulfils the conditions as close as physically
possible". The loop below chooses them automatically: a step is kept only if it
reduces the largest condition error, otherwise the damping is strengthened and the
step retried; when no damping helps, the loop stops where it is. Force densities are
also kept from changing sign (a cable stays a cable). Here the four anchor branches
of the fig. 2 net are asked to be exactly 1.2 m long, then a mixed case."""
def constrained_form_finding(branches, n_free, xyz_fixed, q0, p, length_rows=(), l_v=(), force_rows=(), s_v=(),
                             a=0.8, P_inv=1e-6, kmax=200, tol=1e-10):
    """Schek section 3 on any network.  Returns q, xyz, l, s, iterations, final condition error."""
    n_s = n_free + len(xyz_fixed)
    C_s = np.zeros((len(branches), n_s))
    for j, (i, k) in enumerate(branches):
        C_s[j, i - 1], C_s[j, k - 1] = 1.0, -1.0
    C, C_f = C_s[:, :n_free], C_s[:, n_free:]
    length_rows, force_rows = list(length_rows), list(force_rows)
    l_v, s_v = np.asarray(l_v, float), np.asarray(s_v, float)

    def solve(q):                                                             # section 2 for this q
        D, D_f = C.T @ diag(q) @ C, C.T @ diag(q) @ C_f                       # (8)
        xyz = np.vstack([np.linalg.solve(D, p[:, ax] - D_f @ xyz_fixed[:, ax]) for ax in range(3)]).T   # (9)
        uvw = C @ xyz + C_f @ xyz_fixed                                       # (1)
        l = np.linalg.norm(uvw, axis=1)
        g = np.r_[l[length_rows] - l_v, l[force_rows] * q[force_rows] - s_v]  # (29), (32)
        return D, xyz, uvw, l, g

    def jacobian(D, uvw, l, q):                                               # (31), (34), stacked (3.6)
        D_inv = np.linalg.inv(D)
        u, v, w = uvw.T
        def G_d(rows):
            C_bar = C[rows]
            K = (diag(u[rows]) @ C_bar @ D_inv @ C.T @ diag(u) + diag(v[rows]) @ C_bar @ D_inv @ C.T @ diag(v)
                 + diag(w[rows]) @ C_bar @ D_inv @ C.T @ diag(w))
            return -diag(1.0 / l[rows]) @ K
        blocks = []
        if length_rows:
            blocks.append(G_d(length_rows))
        if force_rows:
            G_f = diag(q[force_rows]) @ G_d(force_rows)
            for row, j in enumerate(force_rows):
                G_f[row, j] += l[j]                                           # (33)
            blocks.append(G_f)
        return np.vstack(blocks)

    q = q0.astype(float).copy()
    D, xyz, uvw, l, g = solve(q)
    damping = P_inv
    for it in range(kmax):
        err = np.abs(g).max()
        if err < tol:
            break
        G_t = jacobian(D, uvw, l, q)
        G = G_t.T
        A = diag(np.full(len(g), a))
        for _ in range(12):                                                   # strengthen the damping until the step helps
            T = G_t @ G + damping * diag(np.diag(G_t @ G)) @ A @ A            # (23), P^-1 scaled to the problem
            k = np.linalg.solve(T, A @ (-g))                                  # (15), (24)
            dq = G @ k                                                        # (25)
            flip = np.sign(q + dq) != np.sign(q)                              # keep every q on its side of zero
            if flip.any():
                dq *= min(1.0, 0.5 * np.min(np.abs(q[flip] / dq[flip])))
            trial = solve(q + dq)
            if np.abs(trial[4]).max() < err:
                q = q + dq; D, xyz, uvw, l, g = trial; damping = max(damping / 2, 1e-9)
                break
            damping *= 4
        else:
            break                                                             # unattainable: stop at the closest shape
    return q, xyz, l, l * q, it, np.abs(g).max()


q_c, xyz_c, l_c, s_c, iterations, err = constrained_form_finding(branches, n, xyz_fixed, q, p, length_rows=[0, 1, 2, 3], l_v=[1.2] * 4)
print(f"anchor branches prescribed to 1.2 m: lengths {l_c[:4]} after {iterations} iterations; their q became {q_c[:4]}")
q_m, xyz_m, l_m, s_m, iterations, err = constrained_form_finding(branches, n, xyz_fixed, q, p, length_rows=[8, 9, 10, 11], l_v=[0.9] * 4,
                                                                 force_rows=[0, 1, 2, 3], s_v=[2.0] * 4)
print(f"mixed: spokes 0.9 m and anchor forces 2 kN: lengths {l_m[8:]}, forces {s_m[:4]} after {iterations} iterations")


# %% [s5] Section 5: the paper's examples with the same program
r"""The application is complete; section 5 only feeds it the paper's data, and every
picture below is rendered from what this cell computes (the shapes are written to
`viewer_scenes/json/shapes.json`, which `schek_1974_figures.py` draws). The first
example is the 67-node radial net of figure 5, its topology traced from the printed
figure: nodes 62 to 66 are the border corners, 67 the apex, all six fixed. The paper
prescribes border branches $q = 100$, radial branches to the apex $q = 0.5$,
everything else $q = 1$, and "a small vertical load in each node"; the anchor
coordinates and the load value are not printed, so they are chosen here to match the
printed proportions.

![Fig. 5](images/schek_fig5.png)

*Fig. 5, redrawn: the graph of the first example.*"""
import json
from pathlib import Path

FIG5_PX = {   # plan positions read off the printed figure (pixels, y down)
    1: (162, 368), 2: (150, 591), 3: (182, 345), 4: (165, 618), 5: (247, 230), 6: (190, 666), 7: (217, 611),
    8: (315, 405), 9: (360, 305), 10: (265, 198), 11: (430, 95), 12: (452, 105), 13: (537, 132), 14: (445, 368),
    15: (413, 448), 16: (357, 593), 17: (250, 773), 18: (412, 703), 19: (282, 836), 20: (445, 951), 21: (527, 921),
    22: (567, 909), 23: (595, 801), 24: (472, 678), 25: (455, 581), 26: (480, 477), 27: (519, 420), 28: (662, 172),
    29: (664, 346), 30: (665, 445), 31: (639, 451), 32: (599, 476), 33: (588, 492), 34: (571, 515), 35: (562, 536),
    36: (559, 568), 37: (561, 596), 38: (573, 632), 39: (592, 661), 40: (624, 683), 41: (652, 696), 42: (694, 703),
    43: (732, 821), 44: (737, 851), 45: (837, 230), 46: (787, 365), 47: (719, 448), 48: (749, 463), 49: (793, 506),
    50: (807, 546), 51: (809, 596), 52: (804, 628), 53: (752, 686), 54: (864, 239), 55: (964, 385), 56: (919, 526),
    57: (977, 514), 58: (919, 643), 59: (989, 653), 60: (992, 676), 61: (857, 811), 62: (97, 494), 63: (362, 981),
    64: (999, 763), 65: (954, 270), 66: (340, 68), 67: (685, 571)}
BORDER = [62, 2, 4, 6, 17, 19, 63, 20, 21, 22, 44, 61, 64, 60, 59, 57, 55, 65, 54, 45, 28, 13, 12, 11, 66, 10, 5, 3, 1]
INNER_RING = [31, 30, 47, 48, 49, 50, 51, 52, 53, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32]
MIDDLE_RING = [27, 29, 46, 56, 58, 43, 23, 24, 25, 26]
SPOKES = [31, 33, 35, 37, 39, 41, 53, 51, 49, 47]
OTHER = [(30, 29), (32, 27), (34, 26), (36, 25), (38, 24), (40, 23), (42, 43), (52, 58), (50, 56), (48, 46),
         (27, 14), (29, 28), (46, 45), (56, 57), (58, 59), (43, 44), (23, 22), (24, 18), (25, 16), (26, 15),
         (1, 2), (4, 7), (6, 7), (7, 8), (3, 8), (8, 9), (5, 9), (9, 12), (9, 14), (13, 14), (10, 11), (8, 15),
         (14, 15), (15, 16), (7, 16), (16, 18), (17, 18), (18, 21), (19, 20), (61, 60), (59, 58), (57, 56),
         (46, 45), (28, 29), (54, 55)]
ring = lambda nodes: [(nodes[i], nodes[(i + 1) % len(nodes)]) for i in range(len(nodes))]
seen, branches5 = set(), []
for e in ring(BORDER) + ring(INNER_RING) + ring(MIDDLE_RING) + [(k, 67) for k in SPOKES] + OTHER:
    if tuple(sorted(e)) not in seen:
        seen.add(tuple(sorted(e))); branches5.append(e)
border5 = {tuple(sorted(e)) for e in ring(BORDER)}
xy = np.array([FIG5_PX[k] for k in range(1, 68)], dtype=float) * np.array([0.04, -0.04])   # 0.04 m per pixel
xy -= xy[66]                                                                                # apex at the plan origin
free5, fixed5 = 61, [62, 63, 64, 65, 66, 67]
q5 = np.array([100.0 if tuple(sorted(e)) in border5 else 0.5 if 67 in e else 1.0 for e in branches5])
p5 = np.zeros((free5, 3)); p5[:, 2] = -0.4
is_spoke = np.array([67 in e for e in branches5])
is_border = np.array([tuple(sorted(e)) in border5 for e in branches5])
touches_border = np.array([any(k in BORDER for k in e) for e in branches5])

def anchors5(apex_dx=0.0, apex_dy=0.0, apex_h=16.0):
    A = np.c_[xy[61:67], np.zeros(6)]
    A[5] += [apex_dx, apex_dy, apex_h]
    return A

shapes = {}                                                                    # name -> (branches, all node coordinates, fixed nodes)
def keep(name, brs, xyz_free, xyz_fixed, fixed_nodes):
    shapes[name] = {"branches": [list(e) for e in brs], "xyz": np.vstack([xyz_free, xyz_fixed]).tolist(), "fixed": list(fixed_nodes)}

# figure 6: different fixed points (the apex moved in plan): only the right-hand sides change
for name, (dx, dy) in zip(["fig6_1", "fig6_2", "fig6_3"], [(0, 0), (6, 2), (12, 4)]):
    xyz, l, s_, R = form_finding(branches5, free5, anchors5(dx, dy), q5, p5)
    keep(name, branches5, xyz, anchors5(dx, dy), fixed5)
    print(f"{name}: apex moved by ({dx}, {dy}) m; radial lengths {l[is_spoke].min():.1f}-{l[is_spoke].max():.1f} m; apex reaction {-R[5, 2]:.1f} kN")
keep("fig1", *(lambda r: (branches5, r[0], anchors5(), fixed5))(form_finding(branches5, free5, anchors5(), q5, p5)))
# figure 7: the radial force density 1.0, 0.7, 0.3 instead of 0.5: D is rebuilt
for name, qs in zip(["fig7_1", "fig7_2", "fig7_3"], [1.0, 0.7, 0.3]):
    xyz, l, *_ = form_finding(branches5, free5, anchors5(), np.where(is_spoke, qs, q5), p5)
    keep(name, branches5, xyz, anchors5(), fixed5)
    print(f"{name}: radial q = {qs}: radial lengths {l[is_spoke].min():.1f}-{l[is_spoke].max():.1f} m")
# figure 8: the border force density 10, 5, 1 instead of 100
for name, qb in zip(["fig8_1", "fig8_2", "fig8_3"], [10.0, 5.0, 1.0]):
    xyz, l, *_ = form_finding(branches5, free5, anchors5(), np.where(is_border, qb, q5), p5)
    keep(name, branches5, xyz, anchors5(), fixed5)
    print(f"{name}: border q = {qb:g}: border lengths {l[is_border].min():.1f}-{l[is_border].max():.1f} m")
# figure 9: distance conditions on all branches not connected with the border (section 3)
base_l = form_finding(branches5, free5, anchors5(), q5, p5)[1]
inner = [j for j in range(len(branches5)) if not touches_border[j]]
for name, (l_radial, ring_factor) in zip(["fig9_1", "fig9_2", "fig9_3"], [(6.0, 1.25), (6.0, 0.85), (4.5, 0.70)]):
    l_v = [l_radial if is_spoke[j] else base_l[j] * ring_factor for j in inner]
    q_k, xyz, l, s_, its, err = constrained_form_finding(branches5, free5, anchors5(), q5, p5, length_rows=inner, l_v=l_v)
    keep(name, branches5, xyz, anchors5(), fixed5)
    print(f"{name}: radial l = {l_radial} m, rings x{ring_factor}: largest length error {err:.1e} after {its} iterations"
          + ("  (unattainable, stopped)" if err > 1e-6 else ""))
# figure 10: the 112-bar grid-shell model, 8 x 8 nodes
g = 8
gid = {(i, k): i * g + k + 1 for i in range(g) for k in range(g)}
grid = [(gid[i, k], gid[i, k + 1]) for i in range(g) for k in range(g - 1)] + [(gid[i, k], gid[i + 1, k]) for i in range(g - 1) for k in range(g)]
corners = [gid[0, 0], gid[0, g - 1], gid[g - 1, g - 1], gid[g - 1, 0]]
order = [v for v in range(1, g * g + 1) if v not in corners] + corners           # renumber: free nodes first, corners last
renum = {old: new + 1 for new, old in enumerate(order)}
grid = [(renum[a_], renum[b_]) for a_, b_ in grid]
flat = np.array([[(v - 1) % g, (v - 1) // g, 0.0] for v in order], dtype=float)  # 1 m spacing, in the new order
on_edge = lambda v: ((order[v - 1] - 1) // g in (0, g - 1), (order[v - 1] - 1) % g in (0, g - 1))
grid_border = np.array([(on_edge(a_)[0] and on_edge(b_)[0]) or (on_edge(a_)[1] and on_edge(b_)[1]) for a_, b_ in grid])
grid_touch = np.array([any(on_edge(v)[0] or on_edge(v)[1] for v in e) for e in grid])
weight = 0.15                                                                   # kN per bar
degree = np.bincount(np.array(grid).ravel())[1:]
p10 = np.zeros((g * g - 4, 3)); p10[:, 2] = -0.5 * weight * degree[:g * g - 4]    # half of every bar's weight at each end
anchors10 = flat[-4:].copy(); anchors10[:, :2] = (anchors10[:, :2] - 3.5) * 0.8 + 3.5   # anchors pulled in to 80 % of the span
q_k, xyz, l, s_, its, err = constrained_form_finding(grid, g * g - 4, anchors10, np.ones(112), p10, length_rows=range(112), l_v=[1.0] * 112)
keep("fig10_1", grid, xyz, anchors10, [renum[c] for c in corners])
print(f"fig10_1: 112 bars of 1.0 m hanging under their weight: length error {err:.1e} after {its} iterations; bar forces {s_.min():.2f}-{s_.max():.2f} kN")
anchors10b = anchors10.copy(); anchors10b[[0, 2], 2] = 3.0                      # two corners raised: prestressed net
q10 = np.where(grid_border, 10.0, 1.0)
xyz, l, s_, R = form_finding(grid, g * g - 4, anchors10b, q10, np.zeros_like(p10))
keep("fig10_2", grid, xyz, anchors10b, [renum[c] for c in corners])
print(f"fig10_2: corners raised, inner q = 1, border q = 10: inner lengths {l[~grid_border].min():.2f}-{l[~grid_border].max():.2f} m")
inner10 = [j for j in range(112) if not grid_border[j] and not grid_touch[j]]
link10 = [j for j in range(112) if not grid_border[j] and grid_touch[j]]
q_k, xyz, l, s_, its, err = constrained_form_finding(grid, g * g - 4, anchors10b, q10, np.zeros_like(p10),
                                                     length_rows=inner10, l_v=[l[inner10].mean()] * len(inner10),
                                                     force_rows=link10, s_v=[s_[link10].mean()] * len(link10))
keep("fig10_3", grid, xyz, anchors10b, [renum[c] for c in corners])
print(f"fig10_3: equidistant inner net and constant force in the branches connected with the border: error {err:.1e} after {its} iterations")

keep("fig5_plan", branches5, np.c_[xy[:61], np.zeros(61)], np.c_[xy[61:], np.zeros(6)], fixed5)
out = Path(__file__).resolve().parent / "viewer_scenes/json/shapes.json" if "__file__" in dir() else Path("viewer_scenes/json/shapes.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(shapes))
print(f"{len(shapes)} shapes written to {out.name}; schek_1974_figures.py draws them")
