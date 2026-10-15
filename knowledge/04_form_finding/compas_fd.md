---
id: form-finding-compas-fd
title: Force density method with compas_fd
status: reviewed
related_domains: [form_finding, thrust_network_analysis]
---

# Force density method with compas_fd

`compas_fd` implements the **force density method (FDM)** of H.-J. Schek (1974):
given the connectivity of a pin-jointed network, the positions of its fixed nodes,
the nodal loads, and one *force density* per branch, the equilibrium coordinates of
all free nodes follow from **one linear system**. A constrained, iterative variant
moves selected anchors along geometric constraints between linear solves.

- Repository: <https://github.com/BlockResearchGroup/compas_fd>
- Documentation: <https://blockresearchgroup.github.io/compas_fd>
- PyPI: `pip install compas_fd` (version `0.5.4` of 2024-11-10 was read and run for this note)
- Used by the Rhino plugin described in [compas_fofin](compas_fofin.md); the same
  force-density parametrisation drives the iterative solver in [compas_dr](compas_dr.md).

## Concept and assumptions

**Force density.** For branch $j$ with axial force $s_j$ and strained length $l_j$,

$$
q_j = \frac{s_j}{l_j}
$$

Dimension: force / length (N/m, kN/m). The same force gives a larger $q$ in a
shorter branch. Schek calls $q$ the "network description parameter": prescribing
$q$ for every branch selects exactly one equilibrium shape.

**Model assumptions (Schek 1974, section 1).**

- Branches are straight axial members (cables or bars) connected by frictionless pins.
- Loads act only at nodes.
- No material law is needed for the linear method; the branches may be elastic or
  inextensible. Material enters only through the optional *unstrained length*
  constraints of the nonlinear extension (section 3.5).
- Nodes are either **free** (unknown coordinates) or **fixed** (prescribed coordinates).
- No geometric restriction is imposed on the shape: the only requirement is
  nodal equilibrium.

**Sign conventions.**

- $q_j \gt 0$ and $s_j \gt 0$: tension. A net with all $q_j \gt 0$ and no isolated free
  node has a positive-definite equation matrix and a unique solution.
- $q_j \lt 0$: compression. `compas_fd` accepts negative values (FormFinder uses them
  for compression-only funiculars), but mixed signs can make the matrix singular
  or indefinite; check the residuals.
- Loads $p$ are external forces on nodes in global $x, y, z$; gravity is a negative $p_z$
  when $z$ points up.
- The **residual** returned by the solver is $r = p - C^{t} Q C x$. At free nodes it is
  zero at convergence. At a fixed node it equals the resultant force the connected
  branches exert on the support, so the **support reaction** is $-r$.

**Units.** The method is unit-agnostic as long as coordinates, loads, and force
densities are consistent (e.g. m, kN, kN/m). Forces returned are $q \cdot l$ in the
load unit; lengths are in the coordinate unit.

## Formulation (Schek 1974)

Notation follows the paper: lower-case = column vector, capital = matrix,
and for any vector $a$ the capital $A$ is the diagonal matrix with $a$ on its
diagonal. $C^{t}$ is the transpose of $C$. Equation numbers in parentheses are
those of the paper.

### Branch-node matrix (section 2.1)

Number the nodes $1 \ldots n_s$ with the $n_f$ fixed nodes last, so $n_s = n + n_f$
with $n$ free nodes, and the branches $1 \ldots m$. Branch $j$ runs from node $i(j)$ to
node $k(j)$. The branch-node matrix $C_s$ ($m$ rows, $n_s$ columns) has entries

$$
c(j, i) =
\begin{cases}
+1 & \text{if } i = i(j) \\
-1 & \text{if } i = k(j) \\
0 & \text{otherwise}
\end{cases}
$$

Splitting the columns into free and fixed nodes gives $C_s = [\ C \quad  C_f\ ]$.
(`compas.matrices.connectivity_matrix` builds $C_s$ with the same +1/−1 convention;
`compas_fd` then column-slices it into `Ci` (free) and `Cf` (fixed).)

### Coordinate differences and equilibrium (section 2.2)

With free-node coordinate vectors $x, y, z$ and fixed-node vectors $x_f, y_f, z_f$,
the per-branch coordinate differences are (1):

$$
u = C x + C_f x_f, \qquad v = C y + C_f y_f, \qquad w = C z + C_f z_f
$$

With $U, V, W, L$ the diagonal matrices of $u, v, w, l$, and $s$ the branch forces,
nodal equilibrium (sum of forces zero at every free node) reads (2):

$$
C^{t} U L^{-1} s = p_x, \qquad C^{t} V L^{-1} s = p_y, \qquad C^{t} W L^{-1} s = p_z
$$

$U L^{-1} s$ is the vector of $x$-components of the branch forces (direction cosine
$u_j / l_j$ times force $s_j$), and $C^{t}$ sums them per node. The matrices
$C^{t} U L^{-1}$ etc. are also the Jacobians $\partial l / \partial x$,
$\partial l / \partial y$, $\partial l / \partial z$ (3).

Equation (2) is **nonlinear** in the coordinates because $L$ depends on them.
The compas-FoFin GitBook makes the same point for a single node $0$ with four cables:

$$
\sum_{j=1}^{4} F_j \frac{x_j - x_0}{L_j} = R_x, \qquad
L_{0j} = \sqrt{(x_j - x_0)^2 + (y_j - y_0)^2 + (z_j - z_0)^2}
$$

### The linearising substitution (section 2.2, equations 4 to 8)

Define the force densities (4):

$$
q = L^{-1} s
$$

Then (2) becomes (5):

$$
C^{t} U q = p_x, \qquad C^{t} V q = p_y, \qquad C^{t} W q = p_z
$$

Using the identities $U q = Q u$, $V q = Q v$, $W q = Q w$ (both sides are the
element-wise product of the same two vectors, (6)) and substituting (1) gives (7):

$$
C^{t} Q C x + C^{t} Q C_f x_f = p_x, \qquad
C^{t} Q C y + C^{t} Q C_f y_f = p_y, \qquad
C^{t} Q C z + C^{t} Q C_f z_f = p_z
$$

With $D = C^{t} Q C$ ($n \times n$) and $D_f = C^{t} Q C_f$ ($n \times n_f$) this is (8):

$$
D x = p_x - D_f x_f, \qquad D y = p_y - D_f y_f, \qquad D z = p_z - D_f z_f
$$

Schek's conclusions:

1. (8) is **linear** in the free coordinates. $D$ is the "generalised Gaussian
   transformation" of $C$; its diagonal entry for node $i$ is the sum of the $q$
   of all branches at $i$, and its off-diagonal entry $(i, k)$ is $-q_j$ for the
   branch joining $i$ and $k$ (figure 4 of the paper; reproduced numerically below).
   $D$ is positive definite for a prestressed net ($q_j \gt 0$) without isolated nodes.
2. For given load and fixed points, each vector $q$ yields **exactly one** equilibrium (9), (10):

$$
x = D^{-1}(p_x - D_f x_f), \qquad
y = D^{-1}(p_y - D_f y_f), \qquad
z = D^{-1}(p_z - D_f z_f), \qquad
s = L q
$$

   with $L$ evaluated from the solved coordinates.
3. The set of equilibrium shapes for a fixed topology, load, and anchors is in
   one-to-one correspondence with the set of vectors $q$.

The three systems in (8) share the matrix $D$; `compas_fd` solves them as one
system with a 3-column right-hand side. Figure 3 of the paper is the workflow:
input connectivity, build $C$, build $D$ and the right-hand sides, solve (9),
compute lengths and forces (10), plot, then change anchors, loads, $q$, or
topology and repeat.

### Geometric interpretation (section 4)

Minimising the *weighted* sum of squared branch lengths
$u^{t} P u + v^{t} P v + w^{t} P w$ with diagonal weights $P$ and at least four
fixed points in general position yields the stationarity conditions (41):

$$
(C^{t} P C)\  x = -(C^{t} P C_f)\  x_f \qquad \text{(and the same for } y, z)
$$

which are (7) with $Q = P$ and zero load. Hence:

- **Theorem 1.** Every equilibrium state of an *unloaded* network with force
  densities $q_j$ is the net whose sum of squared branch lengths weighted by
  $q_j$ is minimal. With all $q_j = 1$ it is the net with minimal unweighted
  sum of squared lengths (39).
- **Theorem 2.** A *minimum way net* (minimal sum of lengths, not squared) is a
  prestressed net with the same force in every branch: choose $q_j = c / l_j$,
  so $s_j = q_j l_j = c$ is constant, and $l_j \gt 0$ gives $q_j \gt 0$.

### Nonlinear extension: additional constraints (section 3)

Linear FDM fulfils no condition other than equilibrium (meshes are in general
neither equidistant nor orthogonal). Schek adds $r$ conditions (11):

$$
g(x, y, z, q) = 0
$$

Since (9) makes $x, y, z$ functions of $q$, the conditions depend on $q$ alone,
$g^{\ast}(q) = 0$ (12). Starting from the linear solution $q^{(0)}$, linearise (13 to 16):

$$
g^{\ast}(q^{(0)}) + \frac{\partial g^{\ast}}{\partial q}\  \Delta q = 0,
\qquad
G^{t} := \frac{\partial g^{\ast}}{\partial q}, \quad r := -g^{\ast}(q^{(0)})
\qquad \Longrightarrow \qquad
G^{t} \Delta q = r
$$

$G^{t}$ is $r \times m$. With $r \lt m$ there are $m - r$ free directions; pick
$\Delta q$ by a minimum principle:

| variant | condition | minimised | normal-equation matrix $T$ |
|---|---|---|---|
| least squares (16, 17) | $G^{t} \Delta q = r$ | $\Delta q^{t} \Delta q$ | $G^{t} G$ |
| damped (18, 19) | $G^{t} \Delta q = r + a$ | $\Delta q^{t} \Delta q + a^{t} P a$ | $G^{t} G + P^{-1}$ |
| modified damped (20, 21) | $G^{t} \Delta q = A r$, $A$ = diagonal of damping factors $a_j$ | $\Delta q^{t} \Delta q + (e - a)^{t} P (e - a)$ | $G^{t} G + P^{-1} A^{2}$ |

In all cases the Lagrange multipliers $k$ solve the small $r \times r$ system
$T k = r$ (22 to 24) and (25):

$$
\Delta q = G k, \qquad q^{(0)} := q^{(0)} + \Delta q
$$

iterated until $g^{\ast}$ vanishes within tolerance. The number of nonlinear equations
equals the number of constraints, **not** the number of nodes. Schek recommends the
modified damped variant: it converges without oscillation and, when the
constraints are physically unattainable, stops at the closest feasible shape.

**Jacobian via implicit differentiation (section 3.2).** By the chain rule (26):

$$
G^{t} =
\frac{\partial g}{\partial x}\frac{\partial x}{\partial q} +
\frac{\partial g}{\partial y}\frac{\partial y}{\partial q} +
\frac{\partial g}{\partial z}\frac{\partial z}{\partial q} +
\frac{\partial g}{\partial q}
$$

Differentiating the equilibrium $C^{t} U q = p_x$ at fixed load, with
$\partial (C^{t} U q) / \partial q = C^{t} U$ and
$\partial (C^{t} U q) / \partial x = C^{t} Q C = D$, gives (27), (28):

$$
\frac{\partial x}{\partial q} = -D^{-1} C^{t} U, \qquad
\frac{\partial y}{\partial q} = -D^{-1} C^{t} V, \qquad
\frac{\partial z}{\partial q} = -D^{-1} C^{t} W
$$

**Constraint types.** A bar over a symbol restricts it to the first $r$ branches
(the constrained ones). Let

$$
K := \bar U \bar C D^{-1} C^{t} U + \bar V \bar C D^{-1} C^{t} V + \bar W \bar C D^{-1} C^{t} W
$$

- *Node distance* (strained length), $g = \bar l - \bar l_v = 0$ (29). With
  $\partial l / \partial x = C^{t} U L^{-1}$ from (3), the Jacobian is (31):

$$
G_d^{t} = -\bar L^{-1} K
$$

- *Force*, $g = \bar L \bar q - \bar s_v = \bar Q \bar l - \bar s_v = 0$ (32).
  Using $\partial g / \partial q = \bar L$ (33), the Jacobian is (34):

$$
G_f^{t} = \bar L - \bar Q \bar L^{-1} K
$$

- *Unstrained length* with linear Hooke's law $l_{u,j} = h_j l_j / (h_j + s_j)$,
  where $h_j$ is the axial stiffness of branch $j$ (35):

$$
G_u^{t} = -\bar L_u^{2} \bar H^{-1} - \bar L_u^{2} \bar L^{-3} K
$$

  which tends to $G_d^{t}$ as $h \to \infty$.
- *Mixed*: stack the class matrices, $G = [\ G_d  \mid  G_f  \mid  G_u  \mid  \ldots\ ]$.

All three share the kernel $C D^{-1} C^{t}$ scaled by the diagonal
coordinate-difference matrices, which is why they are cheap to assemble together.

**What `compas_fd` implements of this.** Only the linear method (section 2) and a
*geometric* constraint loop that is not Schek's section 3: anchors are projected onto
lines, planes, circles, curves, or surfaces and moved by a damped fraction of the
tangential residual between linear solves. Prescribed branch lengths or forces
(Schek sections 3.3 to 3.5) are **not** available in `compas_fd` 0.5.4. The iterative
solver in [compas_dr](compas_dr.md) reaches prescribed forces/lengths through its
`fpre`/`lpre` terms instead.

### Schek's worked example (section 5)

Radial net with 67 nodes, nodes 62 to 67 fixed, a small vertical load at every node:

| branches | $q$ | effect |
|---|---|---|
| border (main cables) | 100 | borders nearly straight |
| radial branches to the apex (node 67) | 0.5 | radial branches lengthen relative to the rest |
| all others | 1 | reference value |

Changing the apex position only changes the right-hand side (one matrix
multiplication per variant, figure 6). Raising the apex $q$ to 1.0 / 0.7 / 0.3
(figure 7) or lowering the border $q$ to 10 / 5 / 1 (figure 8) shortens or lengthens
those branch families; with $q = 1$ everywhere the net is also the minimal
squared-length net (Theorem 1). Prescribing 6 m for all radial branches needed
5 damped iterations (figure 9). A hanging grid-shell model of 112 identical bars was
reproduced from anchor coordinates, bar length, and bar weight alone, then turned
into a prestressed net by moving the anchors (figure 10).

## Step by step in NumPy, with the paper's figures

Everything below is produced by two scripts in `examples/form_finding/`:
`schek_1974_walkthrough.py` prints the matrices (NumPy and SciPy only), and
`schek_1974_figures.py` rebuilds the paper's figures as `session_viewer` scenes
(see `examples/form_finding/README.md` for the render pipeline). Figures 2 to 5
are exact redraws of the paper's drawings; figures 1 and 6 to 10 are recomputed
with the method itself. The paper does not print the anchor coordinates or the
load of its example, so those are chosen to match the printed proportions.

![Fig. 1. Views of a prestressed net.](images/schek_fig1.png)

*Fig. 1 of the paper, recomputed: two views of the prestressed net of the example
(section 5), rendered with session_viewer.*

### Step 1. Graph and branch-node matrix (fig. 2)

![Fig. 2. Graph and branch-node matrix](images/schek_fig2.png)

*Fig. 2, redrawn: 5 free nodes (1 to 5), 4 fixed nodes (6 to 9), 12 branches with
their numbers in circles; branch-node matrix $C_s = [C \quad  C_f]$.*

Branch $j$ is an ordered pair $(i(j), k(j))$; node $i(j)$ gets $+1$ and node $k(j)$
gets $-1$ in row $j$:

```python
import numpy as np

BRANCHES = [(1, 6), (2, 7), (3, 8), (4, 9),          # anchor branches 1-4
            (1, 4), (1, 2), (2, 3), (3, 4),          # ring 5-8
            (4, 5), (1, 5), (2, 5), (3, 5)]          # spokes to the centre 9-12
N_FREE, N_FIXED = 5, 4

def branch_node_matrix(branches, n_nodes):
    C = np.zeros((len(branches), n_nodes))
    for j, (i, k) in enumerate(branches):
        C[j, i - 1] = +1.0
        C[j, k - 1] = -1.0
    return C

C_s = branch_node_matrix(BRANCHES, N_FREE + N_FIXED)
free, fixed = list(range(N_FREE)), list(range(N_FREE, N_FREE + N_FIXED))
C, C_f = C_s[:, free], C_s[:, fixed]        # column split: free | fixed
```

The printed matrix is the one in the paper's figure 2 (a dot is a zero):

```text
C_s = [C  C_f]   (figure 2 of the paper)  shape (12, 9)
           1     2     3     4     5     6     7     8     9
   1       1     .     .     .     .    -1     .     .     .
   2       .     1     .     .     .     .    -1     .     .
   3       .     .     1     .     .     .     .    -1     .
   4       .     .     .     1     .     .     .     .    -1
   5       1     .     .    -1     .     .     .     .     .
   6       1    -1     .     .     .     .     .     .     .
   7       .     1    -1     .     .     .     .     .     .
   8       .     .     1    -1     .     .     .     .     .
   9       .     .     .     1    -1     .     .     .     .
  10       1     .     .     .    -1     .     .     .     .
  11       .     1     .     .    -1     .     .     .     .
  12       .     .     1     .    -1     .     .     .     .
```

`compas.matrices.connectivity_matrix(edges, "csr")` builds the same matrix as a
sparse CSR matrix with 0-based edges; `compas_fd` slices it into `Ci = C[:, free]`
and `Cf = C[:, fixed]`.

### Step 2. Coordinate differences, equation (1)

The initial geometry is a flat net with the four anchors alternately lifted (a small
hypar). Multiplying the coordinates by $C_s$ gives the per-branch differences
$u, v, w$ as three columns:

```python
xyz0 = np.array([[-1, 0, 0], [0, -1, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0],      # free 1-5
                 [-2, 0, 0], [0, -2, 1], [2, 0, 0], [0, 2, 1]], dtype=float)   # fixed 6-9
uvw = C_s @ xyz0                 # eq. (1): u = C x + C_f x_f, same for v, w
l0 = np.linalg.norm(uvw, axis=1) # branch lengths
```

```text
u, v, w = C_s @ xyz0   (eq. 1, columns = u, v, w)  shape (12, 3)
           u     v     w
   1    1.00     .     .
   2       .  1.00 -1.00
   3   -1.00     .     .
   4       . -1.00 -1.00
   5   -1.00 -1.00     .
   6   -1.00  1.00     .
   7   -1.00 -1.00     .
   8    1.00 -1.00     .
   9       .  1.00     .
  10   -1.00     .     .
  11       . -1.00     .
  12    1.00     .     .

initial lengths l0: [1.    1.414 1.    1.414 1.414 1.414 1.414 1.414 1.    1.    1.    1.   ]
```

### Step 3. Force densities and the matrices Q, D, D_f, equations (4), (7), (8)

Choose one force density per branch. Here the four anchor branches get $q = 2$ and the
rest $q = 1$; a small downward load acts on every free node.

```python
q = np.ones(len(BRANCHES)); q[:4] = 2.0
p = np.zeros((9, 3)); p[free, 2] = -0.5

Q   = np.diag(q)
D   = C.T @ Q @ C          # (5 x 5)  eq. (8) left-hand side: "generalised Gaussian transformation"
D_f = C.T @ Q @ C_f        # (5 x 4)  coupling to the fixed nodes
rhs = p[free] - D_f @ xyz0[fixed]      # right-hand side of (8), one column per axis
```

$D$ has the structure of the paper's figure 4: the diagonal entry of node $i$ is the
sum of the $q$ of the branches meeting at $i$, the off-diagonal entry $(i, k)$ is
$-q_j$ for the branch joining $i$ and $k$, and it is zero where no branch exists.

![Fig. 4. Structure of the matrix D](images/schek_fig4.png)

*Fig. 4, redrawn: the symbolic structure of $D$ for the graph of fig. 2.*

The script prints the same structure symbolically and then with the chosen numbers:

```text
D with symbolic q_j (figure 4):
       q1+q5+q6+q10             -q6               .             -q5            -q10
                -q6    q2+q6+q7+q11             -q7               .            -q11
                  .             -q7    q3+q7+q8+q12             -q8            -q12
                -q5               .             -q8     q4+q5+q8+q9             -q9
               -q10            -q11            -q12             -q9  q9+q10+q11+q12

D = C^t Q C   (compare figure 4: diagonal = sum of q at node, off-diagonal = -q_j)  shape (5, 5)
           1     2     3     4     5
   1     5.0  -1.0     .  -1.0  -1.0
   2    -1.0   5.0  -1.0     .  -1.0
   3       .  -1.0   5.0  -1.0  -1.0
   4    -1.0     .  -1.0   5.0  -1.0
   5    -1.0  -1.0  -1.0  -1.0   4.0

D_f = C^t Q C_f  shape (5, 4)
           6     7     8     9
   1    -2.0     .     .     .
   2       .  -2.0     .     .
   3       .     .  -2.0     .
   4       .     .     .  -2.0
   5       .     .     .     .

right-hand side  p_free - D_f @ xyz_fixed   (eq. 8)  shape (5, 3)
           x     y     z
   1   -4.00     . -0.50
   2       . -4.00  1.50
   3    4.00     . -0.50
   4       .  4.00  1.50
   5       .     . -0.50
```

### Step 4. Solve, lengths, forces, residuals, equations (9) and (10)

```python
xyz = xyz0.copy()
xyz[free] = np.linalg.solve(D, rhs)        # eq. (9), three right-hand sides at once
uvw = C_s @ xyz
lengths = np.linalg.norm(uvw, axis=1)
forces = q * lengths                        # eq. (10)  s = L q
residuals = p - C_s.T @ Q @ uvw             # zero at free nodes; minus the reaction at supports
```

```text
xyz (eq. 9; rows 6-9 are the fixed input)  shape (9, 3)
           x     y     z
   1   -0.80     .  0.04
   2       . -0.80  0.33
   3    0.80     .  0.04
   4       .  0.80  0.33
   5       .     .  0.06
   6   -2.00     .     .
   7       . -2.00  1.00
   8    2.00     .     .
   9       .  2.00  1.00

lengths l : [1.201 1.374 1.201 1.374 1.167 1.167 1.167 1.167 0.844 0.8   0.844 0.8  ]
forces  s = q l (eq. 10): [2.402 2.748 2.402 2.748 1.167 1.167 1.167 1.167 0.844 0.8   0.844 0.8  ]

residuals p - C^t Q u (free rows ~ 0, fixed rows = -reaction)  shape (9, 3)
           x     y     z
   1       .     .     .
   2       .     .     .
   3       .     .     .
   4       .     .     .
   5       .     .     .
   6    2.40     .  0.09
   7       .  2.40 -1.34
   8   -2.40     .  0.09
   9       . -2.40 -1.34
```

The free rows of the residual are zero to machine precision; the fixed rows are the
forces the branches apply to the anchors. The run cross-checks itself against
`compas_fd.fd_numpy`:

```text
compas_fd.fd_numpy agrees with the hand-rolled solve to 1.1e-16 (coordinates) and 4.4e-16 (forces)
```

`fd_numpy` differs from the lines above only in using sparse matrices and `spsolve`.

### Step 5. The paper's workflow (fig. 3) and example (figs. 5 to 8)

![Fig. 3. Diagram of the form finding](images/schek_fig3.png)

*Fig. 3, redrawn: the loop of the linear method. A change of anchors or loads only
changes the right-hand side of (8); a change of $q$ rebuilds $D$; a change of
connectivity rebuilds $C$.*

![Fig. 5. Graph of the first example](images/schek_fig5.png)

*Fig. 5, redrawn from the printed figure: 67 nodes and 110 branches. Nodes 62 to 66
are the border corners and 67 the apex; all six are fixed. The 20-node inner ring
alternates between a branch to the apex (10 radial branches) and a branch to the
10-node middle ring.*

With $q = 100$ on the border, $q = 0.5$ on the radial branches and $q = 1$
elsewhere, plus a small vertical load on every node, one linear solve gives the net
of figure 6.1. Figures 6.2 and 6.3 move the apex in plan, which only changes the
right-hand side of (8):

![Fig. 6. Different fixed points](images/schek_fig6_persp.png)
![Fig. 6, plan](images/schek_fig6_plan.png)

*Fig. 6, recomputed: apex at the position of fig. 5, then moved by (6, 2) m and
(12, 4) m in plan. Top: perspective; bottom: plan, as in the paper.*

Raising the radial force density to 1.0, 0.7 and 0.3 shortens or lengthens the
radial branches relative to the rest (fig. 7); lowering the border force density to
10, 5 and 1 lets the border sag inward (fig. 8). With $q = 1$ everywhere, fig. 8.3
is also the net with the minimal sum of squared branch lengths (Theorem 1).

![Fig. 7](images/schek_fig7_persp.png)
![Fig. 7, plan](images/schek_fig7_plan.png)

*Fig. 7, recomputed: radial branches with $q = 1.0$, $0.7$, $0.3$.*

![Fig. 8](images/schek_fig8_persp.png)
![Fig. 8, plan](images/schek_fig8_plan.png)

*Fig. 8, recomputed: border branches with $q = 10$, $5$, $1$.*

### Step 6. Constraints by damped least squares (section 3, figs. 9 and 10)

Prescribing lengths (or forces) makes the problem nonlinear in $q$. The Jacobian of
the lengths with respect to the force densities follows from the implicit
differentiation of equilibrium, equations (28) and (31); in NumPy, for the first
$r$ branches:

```python
Dinv = np.linalg.inv(D)
CDC = C @ Dinv @ C.T                                   # the kernel  C D^-1 C^t
rows = []
for j in constrained:                                  # dl_j / dq, eq. (31)
    rows.append(-(1.0 / lengths[j]) * sum(uvw[j, a] * CDC[j, :] * uvw[:, a] for a in range(3)))
Gt = np.array(rows)                                    # (r x m)
g = lengths[constrained] - l_v                         # eq. (29)
```

One "modified damped" step, equations (20) to (25), with damping factors $a_j$ and
weights $P$:

```python
G = Gt.T
A = np.diag(a)                                         # damping factors, e.g. 0.8
T = Gt @ G + Pinv @ A @ A                              # eq. (23), third case
k = np.linalg.solve(T, A @ (-g))                       # eqs. (20), (24)
q = q + G @ k                                          # eq. (25); then rebuild D and repeat
```

On the fig. 2 network with the four anchor branches prescribed to 1.2 m:

```text
prescribed anchor-branch length 1.2: reached in 14 damped iterations; lengths [1.2 1.2 1.2 1.2] q [1.893 2.352 1.893 2.352]
G^t for the length constraints (eq. 31, last iteration)  shape (4, 12)
           1     2     3     4     5     6     7     8     9    10    11    12
  g1   -0.32  0.00  0.07  0.00  0.16  0.16  0.02  0.02  0.00  0.11  0.00  0.06
  g2    0.00 -0.30  0.00  0.03  0.02  0.17  0.17  0.02  0.04  0.00  0.14  0.00
  g3    0.07  0.00 -0.32  0.00  0.02  0.02  0.16  0.16  0.00  0.06  0.00  0.11
  g4    0.00  0.03  0.00 -0.30  0.17  0.02  0.02  0.17  0.14  0.00  0.04  0.00
```

The analytic Jacobian matches finite differences to $4 \times 10^{-7}$ (checked in
the script). For the paper's example, prescribing 6 m for the radial branches together
with over-long ring lengths cannot be met by a tension net and the damped sequence is
stopped (fig. 9.1); shortening the ring lengths makes it attainable (fig. 9.2); a
third uniform prescription gives fig. 9.3:

![Fig. 9](images/schek_fig9_persp.png)
![Fig. 9, plan](images/schek_fig9_plan.png)

*Fig. 9, recomputed: additional distance conditions on all branches not connected
with the border.*

Figure 10 is the grid-shell model of 112 identical bars (an 8 by 8 node grid). The
hanging shape (10.1) needs only the anchor coordinates, the bar length and the bar
weight: all 112 bars carry a length condition and the loads are the bar weights.
Moving the anchors (two corners raised) and dropping the load gives a prestressed net
with inner $q = 1$ and border $q = 10$ (10.2). Asking for an equidistant inner net and
a constant force in the branches that connect to the border (mixed conditions,
$G = [G_d  \mid  G_f]$) gives 10.3:

![Fig. 10](images/schek_fig10_persp.png)
![Fig. 10, plan](images/schek_fig10_plan.png)

*Fig. 10, recomputed: hanging and prestressed net with the same structure.*

The constraint iteration in `schek_1974_figures.py` keeps Schek's matrix
$T = G^{t} G + P^{-1} A^{2}$ but adapts $P^{-1}$ with the Levenberg-Marquardt
rule (halve it after a step that reduces the residual, multiply by four otherwise)
and never lets a force density change sign; without that, 112 simultaneous length
conditions overshoot.

## Implementation in compas_fd 0.5.4

### Linear solver

```python
from compas_fd.solvers import fd_numpy

result = fd_numpy(
    vertices=vertices,          # (n_s, 3) coordinates of ALL nodes, free and fixed
    fixed=fixed,                # indices of fixed nodes
    edges=edges,                # list of (i, k) index pairs; i -> +1, k -> -1 in C
    forcedensities=q,           # one float per edge
    loads=loads,                # (n_s, 3) nodal loads, optional (defaults to zero)
)
result.vertices    # (n_s, 3) equilibrium coordinates; fixed rows unchanged
result.residuals   # (n_s, 3) p - C^t Q C x  (zero at free nodes; -reaction at supports)
result.forces      # (m, 1)   q * l
result.lengths     # (m, 1)   strained lengths
```

Internally (`solvers/fd_numerical_data.py`, `solvers/fd_numpy.py`):

| symbol in Schek | name in code | construction |
|---|---|---|
| $C_s$ | `C` | `connectivity_matrix(edges, "csr")` |
| $C$ (free columns) | `Ci` | `C[:, free]` |
| $C_f$ | `Cf` | `C[:, fixed]` |
| $Q$ | `Q` | `diags([q.flatten()], [0])` |
| $D$ | `Ai` | `Ci.T @ Q @ Ci` |
| $D_f$ | `Af` | `Ci.T @ Q @ Cf` |
| full $C_s^{t} Q C_s$ | `A` | `C.T @ Q @ C` (used only for residuals) |
| right-hand side of (8) | `b` | `p[free] - Af @ xyz[fixed]` |
| (9) | — | `xyz[free] = spsolve(Ai, b)` |
| $l$ | `lengths` | `normrow(C @ xyz)` |
| (10) | `forces` | `q * lengths` |
| residual | `residuals` | `p - A @ xyz` |

The compas-FoFin GitBook shows the same lines verbatim as the "matrix formulation".
Node ordering is free: the code selects columns by index, so fixed nodes need not
be last as Schek advises. Vertex and edge ordering of the outputs equals the input
ordering. `Result` is a `NamedTuple`; `vertices` is a new array built from the input
list, not the input list itself.

### Constrained solver

```python
from compas.geometry import Line
from compas_fd.constraints import Constraint
from compas_fd.solvers import fd_constrained_numpy

constraints = [None] * len(vertices)
constraints[k] = Constraint(Line([0, 0, 0], [1, 0, 0]))   # vertex k may slide on this line

result = fd_constrained_numpy(
    vertices=vertices, fixed=fixed, edges=edges, forcedensities=q, loads=loads,
    constraints=constraints,   # list aligned with vertices; None = unconstrained
    kmax=100, tol_res=1e-3, tol_disp=1e-3, damping=0.1,
    selfweight=None,           # optional callable xyz -> (n_s, 1) weights, subtracted from p_z
)
```

Each iteration: solve the linear system with the constrained vertices treated as
fixed; compute residuals; for every constrained vertex set `location` and
`residual` on its constraint, call `update(damping)`, which moves the vertex by
`damping × tangent` (the residual component along the constraint) and re-projects
it onto the geometry; collect the tangential residuals. Convergence requires the
largest tangential residual below `tol_res`. Constrained vertices must therefore
be listed in `fixed`; a constraint on a free vertex is ignored by the linear solve.

Constraint geometries are registered on `Constraint(geometry)`: `Vector`,
`Frame`, `Line`, `Plane`, `Circle`, `NurbsCurve`, `NurbsSurface`
(`constraints/__init__.py`). Each subclass defines `project`, `compute_tangent`,
`compute_normal`, `update`, `compute_param`.

`compas_fd.loads.SelfweightCalculator(mesh, density, thickness_attr_name="t")`
returns a callable that multiplies each vertex's tributary area (a quarter of each
adjacent face, from the current coordinates) by thickness × density.

### Caveats found while reading the source

- In `fd_constrained_numpy`, `xyz_prev = numdata.xyz` binds the same array that
  the linear solve then overwrites in place, so the displacement test
  `_is_converged_disp` compares the array with itself and is always true; only
  the tangential-residual test actually stops the loop (0.5.4).
- With `constraints` all `None`, the constrained solver returns the linear
  result after one iteration.
- `fd_numpy` has no input validation: an edge index out of range raises inside
  `connectivity_matrix`, mismatched lengths of `forcedensities` and `edges` raise in
  `diags`/`dot`, and a free node not connected to any fixed node by a positive-$q$
  path makes `Ai` singular (`spsolve` warns and returns `nan`/`inf`).
- `requirements.txt` lists only `compas`; `numpy` and `scipy` arrive through
  `compas`. Tested here with compas 2.15.1, numpy 2.4.6, scipy 1.17.1.

## Verification

**Benchmark from the chapter README.** Four fixed nodes at $(\pm 1, \pm 1, 0)$, one
free node at the origin connected to all four, $q = 1$ N/m on every edge, load
$(0, 0, -1)$ N on the free node. Vertical equilibrium gives
$4 \cdot q \cdot (0 - z) = 1$, so $z = -0.25$ m independent of the cable lengths
(that is the whole point of equation 8).

Run with `compas_fd` 0.5.4 (`fd_numpy`):

| quantity | value |
|---|---|
| free node | $(0, 0, -0.25)$; error below $10^{-12}$ m |
| residual at free node | $(0, 0, 0)$ |
| edge length | 1.436140662 m $= \sqrt{1 + 1 + 0.0625}$ |
| edge force | 1.436140662 N $= q\ l$ |
| residual at support $(-1, -1, 0)$ | $(1, 1, -0.25)$ N, the force the cable exerts on the support |

The support residuals sum to $(0, 0, -1)$, i.e. the applied load, as they must.

**Structure of D (Schek figure 4).** Building $C_s$ for the 9-node, 12-branch graph
of figure 2 and setting $q_j = j$ gives
$D_{11} = q_1 + q_5 + q_6 + q_{10} = 22$,
$D_{33} = q_3 + q_7 + q_8 + q_{12} = 30$,
$D_{55} = q_9 + q_{10} + q_{11} + q_{12} = 42$
and off-diagonals $-q_j$ exactly as printed in the paper. (Branch 5 joins nodes 1
and 4; the scanned figure is ambiguous there, but figure 4 fixes it.)

**Theorem 1.** For random anchors and random $q \in [0.5, 3]$ on that graph, the
unloaded FDM solution and a BFGS minimiser of $\sum_j q_j l_j^{2}$ agree to
$3 \times 10^{-7}$.

**Jacobian (31) and damped iteration (20 to 25).** Implemented literally for
$r = 4$ prescribed strained lengths on the same graph: the analytic $G_d^{t}$ matches
finite differences to $4 \times 10^{-7}$, and the modified damped scheme with
$a_j = 0.8$ and $P^{-1} = 10^{-6} I$ reaches the prescribed lengths to $10^{-12}$
in 19 iterations while the free-node residual stays at machine precision. These
checks are part of `examples/form_finding/schek_1974_walkthrough.py`.

## References and provenance

- Schek, H.-J. (1974). *The force density method for form finding and computation
  of general networks.* Computer Methods in Applied Mechanics and Engineering 3,
  115–134. <https://doi.org/10.1016/0045-7825(74)90045-0>. Read in full from the
  publisher PDF (20 pages; OCR text checked against page images for every equation
  cited above). Received 26 June 1973; work done within SFB 64, Stuttgart, for the
  Munich Olympic roofs (references 16 and 17 of the paper).
- Block Research Group. *Force Densities Method*, compas-FoFin GitBook,
  <https://blockresearchgroup.gitbook.io/compas-fofin/theoretical-background/force-densities-method>
  (read 2026-10-15). Gives the single-node motivation, the rope analogy for $q$,
  and the NumPy/SciPy snippet reproduced above. It cites Schek (1974);
  Veenendaal & Block (2012), *An overview and comparison of structural form finding
  methods for general networks*, Int. J. Solids Struct. 49, 3741–3753,
  <https://doi.org/10.1016/j.ijsolstr.2012.08.008>; and Adriaenssens, Block,
  Veenendaal & Williams (eds., 2014), *Shell Structures for Architecture: Form
  Finding and Optimization*, Routledge.
- Source read: `BlockResearchGroup/compas_fd` at commit `7ee3c5a` (0.5.4, 2024-11-10):
  `solvers/fd_numpy.py`, `solvers/fd_constrained_numpy.py`,
  `solvers/fd_numerical_data.py`, `solvers/result.py`, `constraints/*.py`,
  `loads/selfweight.py`. MIT licence.
- Verification status: benchmark and the four numerical checks above were run on
  2026-10-15 with compas_fd 0.5.4 in a throw-away virtual environment; no adapter,
  example, or test has been added to this repository yet (see chapter README).

[Chapter README](README.md) · [compas_dr](compas_dr.md) · [compas_fofin](compas_fofin.md)
