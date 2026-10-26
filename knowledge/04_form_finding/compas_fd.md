---
id: form-finding-compas-fd
title: Force density method with compas_fd
status: reviewed
related_domains: [form_finding, thrust_network_analysis]
---

# Force density method with compas_fd

This tutorial builds the **force density method (FDM)** from scratch, following
H.-J. Schek (1974). Start with [Build the force density method step by step](#build-the-force-density-method-step-by-step):
create the network data, construct connectivity, write equilibrium, introduce
force densities, solve the free coordinates, and recover branch forces and reactions.
At D.2 you have a reusable linear solver. Later steps add length and force conditions.

The assumptions below serve as a reference while you work through the steps.
The final sections compare our implementation with `compas_fd`, whose linear
solver computes the same free-node equilibrium coordinates. Its constrained solver
moves selected anchors along geometric constraints; it differs from the tutorial's
iteration on force densities for prescribed branch lengths or forces.

- Repository: <https://github.com/BlockResearchGroup/compas_fd>
- Documentation: <https://blockresearchgroup.github.io/compas_fd>
- PyPI: `pip install compas_fd` (version `0.5.4` of 2024-11-10 was read and run for this note)
- Used by the Rhino plugin described in [compas_fofin](compas_fofin.md); the same
  force-density parametrisation drives the iterative solver in [compas_dr](compas_dr.md).

## Concept and assumptions

![Physical and geometric foundation of the Force Density Method](images/fd_linkwitz_intuition.png)

* **1. Why cable equilibrium is nonlinear:** A cable $j$ between node $i$ and node $k$ has length $l_j = \sqrt{(x_i - x_k)^2 + (y_i - y_k)^2 + (z_i - z_k)^2}$ and tension $s_j$ (kN). By similar triangles, its $x$-force component is $F_{x,j} = s_j \frac{x_i - x_k}{l_j}$. Because the unknown coordinates $(x, y, z)$ sit inside the square root $l_j$ in the denominator, solving for node positions directly from forces $s_j$ is **nonlinear**.
* **2. How force density ($q_j = s_j / l_j$) makes it linear:** Prescribe the **force-to-length ratio** $q_j = s_j / l_j$ (kN/m), so $s_j = q_j l_j$. Substituting $s_j = q_j l_j$ into $F_{x,j}$ cancels the unknown length $l_j$ in the numerator and denominator:

$$
F_{x,j} = s_j \frac{x_i - x_k}{l_j} = (q_j l_j) \frac{x_i - x_k}{l_j} = q_j (x_i - x_k)
$$

* **3. Physical meaning at a node (Node 1 in our 9-node net):** For free Node 1 connected to Anchor 6 and Free Nodes 4, 2, 5 by branches $1, 5, 6, 10$ with force densities $q_1, q_5, q_6, q_{10}$, force balance $\sum q_j (x_1 - x_k) = p_{x,1}$ is a **linear equation** whose solution places Node 1 at the $q$-weighted average of its neighbors (and then recovers unstressed cutting length $l_{0,j}$ from Hooke's law, where $EA_j = E_j A_j$ is Young's modulus times cross-sectional area):

$$
q_1(x_1 - x_6) + q_5(x_1 - x_4) + q_6(x_1 - x_2) + q_{10}(x_1 - x_5) = p_{x,1}
\quad \Longrightarrow \quad
x_1 = \frac{p_{x,1} + q_1 x_6 + q_5 x_4 + q_6 x_2 + q_{10} x_5}{q_1 + q_5 + q_6 + q_{10}}, \qquad
l_{0,j} = \frac{l_j}{1 + s_j / EA_j}
$$

* **Assumptions:** Pin-jointed straight branches ($q_j \gt 0$ in tension), loads applied only at nodes, and nodes split into $n$ **free inner nodes** (unknown coordinates) and $n_f$ **fixed anchors** (known coordinates).

| Symbol | Code | Shape | Meaning |
|---|---|---|---|
| $C_s = [C \mid C_f]$ | `C_s`, `C`, `C_f` | `(12, 9)` = `(12, 5)` \| `(12, 4)` | Branch-node connectivity ($+1$ at start node $i$, $-1$ at end node $k$) |
| $\mathbf x, \mathbf y, \mathbf z$ / $\mathbf x _ f, \mathbf y _ f, \mathbf z _ f$ | `x, y, z` / `x_f, y_f, z_f` | `(5,)` / `(4,)` | Free-node (unknown) and fixed-anchor (known) coordinates (m) |
| $\mathbf p _ x, \mathbf p _ y, \mathbf p _ z$ | `p_x, p_y, p_z` | `(5,)` | External nodal loads at the 5 free nodes (kN) |
| $\mathbf u, \mathbf v, \mathbf w$ / $U, V, W$ | `u` / `np.diag(u)` | `(12,)` / `(12, 12)` | Branch coordinate differences $x_i - x_k,\ y_i - y_k,\ z_i - z_k$ (m) |
| $\mathbf l, \mathbf s, \mathbf q$ / $L, Q$ | `l, s, q` | `(12,)` / `(12, 12)` | Branch lengths $l_j$ (m), forces $s_j = q_j l_j$ (kN), force densities $q_j = s_j / l_j$ (kN/m) |
| $D = C^T Q C$, $D_f = C^T Q C_f$ | `D`, `D_f` | `(5, 5)`, `(5, 4)` | Free-node stiffness matrix and fixed-anchor coupling matrix |
| $\mathbf l _ 0, EA$ | `l_cutting, EA` | `(12,)` | Unstressed cutting lengths $l_j / (1 + s_j/EA_j)$ (m) and axial stiffness (kN) |

<!-- schek-app:start -->

## Build the force density method step by step

Follow the subsections in order (`examples/form_finding/schek_app.py`). Every equation is paired immediately with an explicit numerical matrix example on the same **9-node, 12-branch saddle cable net** (`n = 5` free nodes, `n_f = 4` fixed anchors, `m = 12` branches).

| Milestone | What you can do |
|---|---|
| **A.1–A.4** | Define the 9-node, 12-branch cable net, diagonal matrices $U, Q$, connectivity $C_s = [C \mid C_f]$, and $D = C^T Q C$. |
| **B.1–B.3** | Compute branch coordinate differences, lengths, and the 4-stage nonlinear equilibrium residual on the 9-node net. |
| **C.1–C.4** | Apply $q_j = s_j / l_j$, assemble $D$ and $D_f$, solve the 5 free-node coordinates, and recover all 12 cable forces and cutting lengths. |
| **D.1–D.2** | Package the 3D linear solver and 4-anchor support reactions into a single function and compare 4 load/prestress cases. |
| **E.1** | Interpret $q_j$ geometrically as a weight minimizing $\sum_{j=1}^{12} q_j l_j^2$ on the unloaded 9-node saddle. |
| **F.1–F.3** | Enforce target branch lengths and forces on the 9-node net via constrained least-squares and the sensitivity Jacobian $G^T$. |
| **G.1–G.6** | Recompute and visualize the paper's form-found geometries (Figs. 1 and 5–10): the 67-node pointed tent and the 112-bar grid-shell. |

---

## Part A. The network as data

### A.1 Network topology and initial node coordinates (section 2.1)

Throughout this entire tutorial, we use one single running example: Schek's **9-node, 12-branch saddle cable net** (Fig. 2). We number the $n = 5$ **free inner nodes first** ($1 \dots 5$, with initial flat coordinates $\mathbf x_0, \mathbf y_0, \mathbf z_0$) and the $n_f = 4$ **fixed outer anchor nodes last** ($6 \dots 9$, with known support coordinates $\mathbf x_f, \mathbf y_f, \mathbf z_f$) across the $m = 12$ directed branches ($i \to k$).

![Fig. 2](images/schek_fig2.png)

![Part A Topology and Matrix Operators on the Cable Net](images/fd_sec_a_topology_split.png)

* **Total Nodes ($n_s = 9$):** Free inner nodes $1 \dots 5$ ($n = 5$, initial flat coordinates $\mathbf x_0, \mathbf y_0, \mathbf z_0$) and fixed anchors $6 \dots 9$ ($n_f = 4$, known boundary supports $\mathbf x_f, \mathbf y_f, \mathbf z_f$).
* **Directed Branches ($m = 12$):** Anchor cables $b_1 \dots b_4$: $(1\to 6),\ (2\to 7),\ (3\to 8),\ (4\to 9)$; inner ring $b_5 \dots b_8$: $(1\to 4),\ (1\to 2),\ (2\to 3),\ (3\to 4)$; center spokes $b_9 \dots b_{12}$: $(4\to 5),\ (1\to 5),\ (2\to 5),\ (3\to 5)$.

### Matrix Example (Initial Free-Node Coordinates $\mathbf X_0$ and Fixed Anchor Coordinates $\mathbf X_f$)

* **$\mathbf x_0, \mathbf y_0, \mathbf z_0$ (5×1):** Initial flat coordinates of the 5 free inner nodes $1 \dots 5$ (m).
* **$\mathbf x_f, \mathbf y_f, \mathbf z_f$ (4×1):** Known coordinates of the 4 fixed outer anchors $6 \dots 9$ (m).

$$
\begin{bmatrix} \mathbf x_0 & \mathbf y_0 & \mathbf z_0 \end{bmatrix} =
\begin{bmatrix}
-1 & 0 & 0 \\
0 & -1 & 0 \\
1 & 0 & 0 \\
0 & 1 & 0 \\
0 & 0 & 0
\end{bmatrix}\text{ m}
\begin{matrix}
\leftarrow \text{Free Node 1} \\
\leftarrow \text{Free Node 2} \\
\leftarrow \text{Free Node 3} \\
\leftarrow \text{Free Node 4} \\
\leftarrow \text{Free Node 5 (center)}
\end{matrix},
\qquad
\begin{bmatrix} \mathbf x_f & \mathbf y_f & \mathbf z_f \end{bmatrix} =
\begin{bmatrix}
-2 & 0 & 0 \\
0 & 2 & 1 \\
2 & 0 & 0 \\
0 & -2 & 1
\end{bmatrix}\text{ m}
\begin{matrix}
\leftarrow \text{Fixed Anchor 6 (ground)} \\
\leftarrow \text{Fixed Anchor 7 (lifted } +1\text{ m)} \\
\leftarrow \text{Fixed Anchor 8 (ground)} \\
\leftarrow \text{Fixed Anchor 9 (lifted } +1\text{ m)}
\end{matrix}
$$

**Add to your program:**

```python
import numpy as np
from typing import TypeAlias

FloatMatrix: TypeAlias = np.ndarray[tuple[int, int], np.dtype[np.float64]]
FloatVector: TypeAlias = np.ndarray[tuple[int], np.dtype[np.float64]]

branches: list[tuple[int, int]] = [
    (1, 6), (2, 7), (3, 8), (4, 9),   # 1-4: free corners to fixed anchors
    (1, 4), (1, 2), (2, 3), (3, 4),   # 5-8: inner ring
    (4, 5), (1, 5), (2, 5), (3, 5),   # 9-12: four spokes to center node 5
]
n, n_f = 5, 4                         # free nodes 1..5, fixed nodes 6..9
m = len(branches)

# Initial flat coordinates of the 5 free nodes (nodes 1..5, in m)
x_0: FloatVector = np.array([-1.0, 0.0, 1.0, 0.0, 0.0], dtype=np.float64)
y_0: FloatVector = np.array([0.0, -1.0, 0.0, 1.0, 0.0], dtype=np.float64)
z_0: FloatVector = np.zeros(n, dtype=np.float64)

# Known coordinates of the 4 fixed anchors (nodes 6..9, in m)
x_f: FloatVector = np.array([-2.0, 0.0, 2.0, 0.0], dtype=np.float64)
y_f: FloatVector = np.array([0.0, 2.0, 0.0, -2.0], dtype=np.float64)
z_f: FloatVector = np.array([0.0, 1.0, 0.0, 1.0], dtype=np.float64)

print(f"Network counts: m={m} branches, n={n} free nodes, n_f={n_f} fixed anchors")
print("Initial free-node coordinates [x_0, y_0, z_0] (5x3):\n", np.c_[x_0, y_0, z_0])
print("Fixed anchor coordinates [x_f, y_f, z_f] (4x3):\n", np.c_[x_f, y_f, z_f])
```

**Example output:**

```text
Network counts: m=12 branches, n=5 free nodes, n_f=4 fixed anchors
Initial free-node coordinates [x_0, y_0, z_0] (5x3):
 [[-1.  0.  0.]
 [ 0. -1.  0.]
 [ 1.  0.  0.]
 [ 0.  1.  0.]
 [ 0.  0.  0.]]
Fixed anchor coordinates [x_f, y_f, z_f] (4x3):
 [[-2.  0.  0.]
 [ 0.  2.  1.]
 [ 2.  0.  0.]
 [ 0. -2.  1.]]
```

### A.2 Vectors, diagonal matrices, and the diagonal swap (section 1.4)

In standard matrix algebra, you cannot multiply two (12×1) column vectors $\mathbf u$ and $\mathbf q$ element-by-element because their dimensions $(12 \times 1) \times (12 \times 1)$ do not match. To write element-by-element branch multiplication ($u_j q_j$ for each cable $j = 1 \dots 12$) as a valid matrix product, Schek places the 12 entries of $\mathbf u$ and $\mathbf q$ on the main diagonal of (12×12) diagonal matrices $U = \mathrm{diag}(\mathbf u)$ and $Q = \mathrm{diag}(\mathbf q)$.

### General Equation

$$
U = \mathrm{diag}(\mathbf u), \qquad Q = \mathrm{diag}(\mathbf q), \qquad U \mathbf q = Q \mathbf u =
\begin{bmatrix}
u_1 q_1 \\
\vdots \\
u_{12} q_{12}
\end{bmatrix}
$$

### Matrix Example (12 Branches of the 9-Node Net)

* **$\mathbf u$ (12×1) and $U = \mathrm{diag}(\mathbf u)$ (12×12):** Cable $x$-coordinate differences $u_j = x_i - x_k$ (m) between start node $i$ and end node $k$ of each cable ($\mathbf x$ and $\mathbf x_f$ are the node $x$-coordinates; $\mathbf u = C\mathbf x + C_f\mathbf x_f$ is their difference per cable).
* **$\mathbf q$ (12×1) and $Q = \mathrm{diag}(\mathbf q)$ (12×12):** Cable force densities $q_j = s_j / l_j$ (kN/m), placed as a column vector $\mathbf q$ or on the main diagonal of $Q$.
* **$U\mathbf q = Q\mathbf u$ (12×1):** Horizontal cable force components $F_{x,j} = u_j q_j$ (kN).

$$
\underset{U\ (12\times 12)}{\begin{bmatrix}
1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & -1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & -1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & -1 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & -1 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & -1 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1
\end{bmatrix}}
\underset{\mathbf q\ (12\times 1)}{\begin{bmatrix}
2 \\
2 \\
2 \\
2 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1
\end{bmatrix}} =
\underset{Q\ (12\times 12)}{\begin{bmatrix}
2 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 2 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 2 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 2 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1
\end{bmatrix}}
\underset{\mathbf u\ (12\times 1)}{\begin{bmatrix}
1 \\
0 \\
-1 \\
0 \\
-1 \\
-1 \\
-1 \\
1 \\
0 \\
-1 \\
0 \\
1
\end{bmatrix}} =
\begin{bmatrix}
2 \\
0 \\
-2 \\
0 \\
-1 \\
-1 \\
-1 \\
1 \\
0 \\
-1 \\
0 \\
1
\end{bmatrix}
\begin{matrix}
\leftarrow u_1 q_1 = 1 \times 2 \\
\leftarrow u_2 q_2 = 0 \times 2 \\
\leftarrow u_3 q_3 = -1 \times 2 \\
\leftarrow u_4 q_4 = 0 \times 2 \\
\leftarrow u_5 q_5 = -1 \times 1 \\
\leftarrow u_6 q_6 = -1 \times 1 \\
\leftarrow u_7 q_7 = -1 \times 1 \\
\leftarrow u_8 q_8 = 1 \times 1 \\
\leftarrow u_9 q_9 = 0 \times 1 \\
\leftarrow u_{10} q_{10} = -1 \times 1 \\
\leftarrow u_{11} q_{11} = 0 \times 1 \\
\leftarrow u_{12} q_{12} = 1 \times 1
\end{matrix}
$$

**Add to your program:**

```python
u_12 = np.array([1.0, 0.0, -1.0, 0.0, -1.0, -1.0, -1.0, 1.0, 0.0, -1.0, 0.0, 1.0])
q_12 = np.array([2.0, 2.0, 2.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
U_12, Q_12 = np.diag(u_12), np.diag(q_12)         # (12, 12) diagonal matrices from (12,) vectors
print("U @ q == Q @ u (12 branches):", (U_12 @ q_12).astype(int))
```

**Example output:**

```text
U @ q == Q @ u (12 branches): [ 2  0 -2  0 -1 -1 -1  1  0 -1  0  1]
```

### A.3 Branch-node connectivity matrix and partitioning (section 2.1)

Encode the 9-node, 12-branch directed graph as a (12×9) branch-node incidence matrix $C_s$ ($+1$ at start node $i$, $-1$ at end node $k$), partitioned into free-node columns $C$ (12×5) and fixed-anchor columns $C_f$ (12×4).

### General Equation

$$
C_{s(j, i)} = \begin{cases}
+1 & \text{if branch } j \text{ starts at node } i \\
-1 & \text{if branch } j \text{ ends at node } i \\
0 & \text{otherwise}
\end{cases}
\qquad \Longrightarrow \qquad
C_s = \begin{bmatrix} C & C_f \end{bmatrix}
$$

### Matrix Example ($12 \text{ cables} \times 9 \text{ nodes}$)

* **$C_s$ (12×9):** Full branch-node connectivity matrix (12 rows $b_1 \dots b_{12}$ for cables; 9 columns $n_1 \dots n_9$ for nodes; $+1$ at start node $i$, $-1$ at end node $k$).
* **$C$ (12×5):** Left block of $C_s$ (columns $n_1 \dots n_5$ for the 5 free inner nodes).
* **$C_f$ (12×4):** Right block of $C_s$ (columns $n_6 \dots n_9$ for the 4 fixed anchors).

$$
C_s =
\left[\begin{array}{r|ccccc|cccc}
 & n_1 & n_2 & n_3 & n_4 & n_5 & n_6 & n_7 & n_8 & n_9 \\
\hline
b_1\ (1\to 6) & +1 & 0 & 0 & 0 & 0 & -1 & 0 & 0 & 0 \\
b_2\ (2\to 7) & 0 & +1 & 0 & 0 & 0 & 0 & -1 & 0 & 0 \\
b_3\ (3\to 8) & 0 & 0 & +1 & 0 & 0 & 0 & 0 & -1 & 0 \\
b_4\ (4\to 9) & 0 & 0 & 0 & +1 & 0 & 0 & 0 & 0 & -1 \\
\hline
b_5\ (1\to 4) & +1 & 0 & 0 & -1 & 0 & 0 & 0 & 0 & 0 \\
b_6\ (1\to 2) & +1 & -1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
b_7\ (2\to 3) & 0 & +1 & -1 & 0 & 0 & 0 & 0 & 0 & 0 \\
b_8\ (3\to 4) & 0 & 0 & +1 & -1 & 0 & 0 & 0 & 0 & 0 \\
\hline
b_9\ (4\to 5) & 0 & 0 & 0 & +1 & -1 & 0 & 0 & 0 & 0 \\
b_{10}\ (1\to 5) & +1 & 0 & 0 & 0 & -1 & 0 & 0 & 0 & 0 \\
b_{11}\ (2\to 5) & 0 & +1 & 0 & 0 & -1 & 0 & 0 & 0 & 0 \\
b_{12}\ (3\to 5) & 0 & 0 & +1 & 0 & -1 & 0 & 0 & 0 & 0
\end{array}\right]
\begin{matrix}
\\
\leftarrow \text{anchor} \\
\leftarrow \text{anchor} \\
\leftarrow \text{anchor} \\
\leftarrow \text{anchor} \\
\leftarrow \text{ring} \\
\leftarrow \text{ring} \\
\leftarrow \text{ring} \\
\leftarrow \text{ring} \\
\leftarrow \text{spoke} \\
\leftarrow \text{spoke} \\
\leftarrow \text{spoke} \\
\leftarrow \text{spoke}
\end{matrix}
$$

**Add to your program:**

```python
C_s: FloatMatrix = np.zeros((m, n + n_f))
for j, (i, k) in enumerate(branches):
    C_s[j, i - 1] = +1.0              # start node i(j): +1 (0-based index)
    C_s[j, k - 1] = -1.0              # end node k(j): -1
C: FloatMatrix = C_s[:, :n]           # (12, 5) first 5 columns -> free nodes 1..5
C_f: FloatMatrix = C_s[:, n:]         # (12, 4) last 4 columns  -> fixed anchors 6..9
print("C_s (12x9):\n", C_s.astype(int))
```

**Example output:**

```text
C_s (12x9):
 [[ 1  0  0  0  0 -1  0  0  0]
 [ 0  1  0  0  0  0 -1  0  0]
 [ 0  0  1  0  0  0  0 -1  0]
 [ 0  0  0  1  0  0  0  0 -1]
 [ 1  0  0 -1  0  0  0  0  0]
 [ 1 -1  0  0  0  0  0  0  0]
 [ 0  1 -1  0  0  0  0  0  0]
 [ 0  0  1 -1  0  0  0  0  0]
 [ 0  0  0  1 -1  0  0  0  0]
 [ 1  0  0  0 -1  0  0  0  0]
 [ 0  1  0  0 -1  0  0  0  0]
 [ 0  0  1  0 -1  0  0  0  0]]
```

### A.4 Step-by-step matrix multiplication for $D = C^T Q C$ on the 9-node network

Trace how $D = C^T (Q C)$ assembles the (5×5) nodal equilibrium matrix directly on our **9-node, 12-branch network** with force densities $\mathbf q = [2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1]^T$.

### 1. Free Connectivity $C\ (12 \times 5)$ and Transpose $C^T\ (5 \times 12)$

* **$C$ (12×5):** Free-node connectivity matrix (maps 5 free-node coordinates to 12 cables).
* **$C^T$ (5×12):** Transpose of $C$ (sums 12 cable forces at each of the 5 free nodes).
* **$Q$ (12×12):** Diagonal force-density matrix $\mathrm{diag}(q_1, \dots, q_{12})$ (kN/m).
* **$D = C^T Q C$ (5×5):** Free-node stiffness matrix ($D_{ii} = \sum q_j$ at node $i$; $D_{ik} = -q_j$ between nodes $i, k$).

$$
C = \begin{bmatrix}
1 & 0 & 0 & 0 & 0 \\
0 & 1 & 0 & 0 & 0 \\
0 & 0 & 1 & 0 & 0 \\
0 & 0 & 0 & 1 & 0 \\
1 & 0 & 0 & -1 & 0 \\
1 & -1 & 0 & 0 & 0 \\
0 & 1 & -1 & 0 & 0 \\
0 & 0 & 1 & -1 & 0 \\
0 & 0 & 0 & 1 & -1 \\
1 & 0 & 0 & 0 & -1 \\
0 & 1 & 0 & 0 & -1 \\
0 & 0 & 1 & 0 & -1
\end{bmatrix}
\begin{matrix}
\leftarrow b_1\ (1\to 6) \\
\leftarrow b_2\ (2\to 7) \\
\leftarrow b_3\ (3\to 8) \\
\leftarrow b_4\ (4\to 9) \\
\leftarrow b_5\ (1\to 4) \\
\leftarrow b_6\ (1\to 2) \\
\leftarrow b_7\ (2\to 3) \\
\leftarrow b_8\ (3\to 4) \\
\leftarrow b_9\ (4\to 5) \\
\leftarrow b_{10}\ (1\to 5) \\
\leftarrow b_{11}\ (2\to 5) \\
\leftarrow b_{12}\ (3\to 5)
\end{matrix}
\quad \overset{\text{transpose}}{\longrightarrow} \quad
C^T = \begin{bmatrix}
1 & 0 & 0 & 0 & 1 & 1 & 0 & 0 & 0 & 1 & 0 & 0 \\
0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 \\
0 & 0 & 0 & 1 & -1 & 0 & 0 & -1 & 1 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & -1 & -1 & -1 & -1
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Node 1} \\
\leftarrow \text{Node 2} \\
\leftarrow \text{Node 3} \\
\leftarrow \text{Node 4} \\
\leftarrow \text{Node 5}
\end{matrix}
$$

### 2. Step 1 — Compute $Q C$ (Force Density per Cable, $12 \times 5$)

$$
Q C =
\underset{Q\ (12\times 12)}{\begin{bmatrix}
2 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 2 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 2 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 2 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1
\end{bmatrix}}
\underset{C\ (12\times 5)}{\begin{bmatrix}
1 & 0 & 0 & 0 & 0 \\
0 & 1 & 0 & 0 & 0 \\
0 & 0 & 1 & 0 & 0 \\
0 & 0 & 0 & 1 & 0 \\
1 & 0 & 0 & -1 & 0 \\
1 & -1 & 0 & 0 & 0 \\
0 & 1 & -1 & 0 & 0 \\
0 & 0 & 1 & -1 & 0 \\
0 & 0 & 0 & 1 & -1 \\
1 & 0 & 0 & 0 & -1 \\
0 & 1 & 0 & 0 & -1 \\
0 & 0 & 1 & 0 & -1
\end{bmatrix}} =
\underset{Q C\ (12\times 5)}{\begin{bmatrix}
2 & 0 & 0 & 0 & 0 \\
0 & 2 & 0 & 0 & 0 \\
0 & 0 & 2 & 0 & 0 \\
0 & 0 & 0 & 2 & 0 \\
1 & 0 & 0 & -1 & 0 \\
1 & -1 & 0 & 0 & 0 \\
0 & 1 & -1 & 0 & 0 \\
0 & 0 & 1 & -1 & 0 \\
0 & 0 & 0 & 1 & -1 \\
1 & 0 & 0 & 0 & -1 \\
0 & 1 & 0 & 0 & -1 \\
0 & 0 & 1 & 0 & -1
\end{bmatrix}}
\begin{matrix}
\leftarrow q_1 = 2 \\
\leftarrow q_2 = 2 \\
\leftarrow q_3 = 2 \\
\leftarrow q_4 = 2 \\
\leftarrow q_5 = 1 \\
\leftarrow q_6 = 1 \\
\leftarrow q_7 = 1 \\
\leftarrow q_8 = 1 \\
\leftarrow q_9 = 1 \\
\leftarrow q_{10} = 1 \\
\leftarrow q_{11} = 1 \\
\leftarrow q_{12} = 1
\end{matrix}
$$

### 3. Step 2 — Compute $D = C^T (Q C)$ (Sum at the 5 Free Nodes, $5 \times 5$)

$$
D =
\underset{C^T\ (5\times 12)}{\begin{bmatrix}
1 & 0 & 0 & 0 & 1 & 1 & 0 & 0 & 0 & 1 & 0 & 0 \\
0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 \\
0 & 0 & 0 & 1 & -1 & 0 & 0 & -1 & 1 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & -1 & -1 & -1 & -1
\end{bmatrix}}
\underset{Q C\ (12\times 5)}{\begin{bmatrix}
2 & 0 & 0 & 0 & 0 \\
0 & 2 & 0 & 0 & 0 \\
0 & 0 & 2 & 0 & 0 \\
0 & 0 & 0 & 2 & 0 \\
1 & 0 & 0 & -1 & 0 \\
1 & -1 & 0 & 0 & 0 \\
0 & 1 & -1 & 0 & 0 \\
0 & 0 & 1 & -1 & 0 \\
0 & 0 & 0 & 1 & -1 \\
1 & 0 & 0 & 0 & -1 \\
0 & 1 & 0 & 0 & -1 \\
0 & 0 & 1 & 0 & -1
\end{bmatrix}}
$$

$$
D =
\begin{bmatrix}
q_1+q_5+q_6+q_{10} & -q_6 & 0 & -q_5 & -q_{10} \\
-q_6 & q_2+q_6+q_7+q_{11} & -q_7 & 0 & -q_{11} \\
0 & -q_7 & q_3+q_7+q_8+q_{12} & -q_8 & -q_{12} \\
-q_5 & 0 & -q_8 & q_4+q_5+q_8+q_9 & -q_9 \\
-q_{10} & -q_{11} & -q_{12} & -q_9 & q_9+q_{10}+q_{11}+q_{12}
\end{bmatrix} =
\begin{bmatrix}
5 & -1 & 0 & -1 & -1 \\
-1 & 5 & -1 & 0 & -1 \\
0 & -1 & 5 & -1 & -1 \\
-1 & 0 & -1 & 5 & -1 \\
-1 & -1 & -1 & -1 & 4
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Node 1: } 2+1+1+1=5 \\
\leftarrow \text{Node 2: } 2+1+1+1=5 \\
\leftarrow \text{Node 3: } 2+1+1+1=5 \\
\leftarrow \text{Node 4: } 2+1+1+1=5 \\
\leftarrow \text{Node 5: } 1+1+1+1=4
\end{matrix}
$$

**Add to your program:**

```python
QC = Q_12 @ C                         # (12, 5) weight each branch row j by q_j
D_preview = C.T @ QC                  # (5, 5)  sum weighted branch rows at each free node
print("D = C.T @ diag(q) @ C (5x5):\n", D_preview.astype(int))
```

**Example output:**

```text
D = C.T @ diag(q) @ C (5x5):
 [[ 5 -1  0 -1 -1]
 [-1  5 -1  0 -1]
 [ 0 -1  5 -1 -1]
 [-1  0 -1  5 -1]
 [-1 -1 -1 -1  4]]
```

---

## Part B. Equilibrium, the nonlinear form

### B.1 Inputs: external nodal loads and initial cable tensions (section 2.2)

Along with the initial free-node coordinates $(\mathbf x_0, \mathbf y_0, \mathbf z_0)$ and fixed-anchor coordinates $(\mathbf x_f, \mathbf y_f, \mathbf z_f)$ defined in A.1, we specify the external vertical loads $(\mathbf p_x, \mathbf p_y, \mathbf p_z)$ at the 5 free nodes (-0.5 kN each, $+z$ up) and the initial cable tension vector $\mathbf s_0$ (1.0 kN in each of the 12 branches).

### Matrix Example (External Loads $\mathbf P$ and Initial Tensions $\mathbf s_0$)

* **$\mathbf p_x, \mathbf p_y, \mathbf p_z$ (5×1):** External nodal loads along $x, y, z$ at the 5 free nodes $1 \dots 5$ (kN).
* **$\mathbf s_0$ (12×1):** Initial axial tension force in each of the 12 cables $b_1 \dots b_{12}$ (kN).

$$
\begin{bmatrix} \mathbf p_x & \mathbf p_y & \mathbf p_z \end{bmatrix} =
\begin{bmatrix}
0 & 0 & -0.5 \\
0 & 0 & -0.5 \\
0 & 0 & -0.5 \\
0 & 0 & -0.5 \\
0 & 0 & -0.5
\end{bmatrix}\text{ kN}
\begin{matrix}
\leftarrow \text{Node 1 (}-0.5\text{ kN)} \\
\leftarrow \text{Node 2 (}-0.5\text{ kN)} \\
\leftarrow \text{Node 3 (}-0.5\text{ kN)} \\
\leftarrow \text{Node 4 (}-0.5\text{ kN)} \\
\leftarrow \text{Node 5 (}-0.5\text{ kN)}
\end{matrix},
\qquad
\mathbf s_0 =
\begin{bmatrix}
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1
\end{bmatrix}\text{ kN}
$$

**Add to your program:**

```python
p_x: FloatVector = np.zeros(n, dtype=np.float64)  # (5,) x-loads at free nodes 1..5 (kN)
p_y: FloatVector = np.zeros(n, dtype=np.float64)  # (5,) y-loads at free nodes 1..5 (kN)
p_z: FloatVector = np.full(n, -0.5, dtype=np.float64)  # (5,) z-loads at free nodes 1..5 (-0.5 kN)
s_0: FloatVector = np.ones(m, dtype=np.float64)   # (12,) initial 1.0 kN tension in cables 1..12
print("External loads [p_x, p_y, p_z] (5x3):\n", np.c_[p_x, p_y, p_z])
print("Initial cable tensions s_0 (12,):", s_0)
```

**Example output:**

```text
External loads [p_x, p_y, p_z] (5x3):
 [[ 0.   0.  -0.5]
 [ 0.   0.  -0.5]
 [ 0.   0.  -0.5]
 [ 0.   0.  -0.5]
 [ 0.   0.  -0.5]]
Initial cable tensions s_0 (12,): [1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1.]
```

### B.2 Coordinate differences and cable lengths, equation (1)

For each branch $j\ (i \to k)$, compute the coordinate differences $(u_j, v_j, w_j) = (x_i - x_k,\ y_i - y_k,\ z_i - z_k)$ and the Euclidean cable length $l_j$ from the initial free-node coordinates $(\mathbf x_0, \mathbf y_0, \mathbf z_0)$ and fixed-anchor coordinates $(\mathbf x_f, \mathbf y_f, \mathbf z_f)$ defined in A.1.

![Section B.2 Geometric Meaning of Coordinate Differences u, v, w and Cable Length l](images/fd_sec_b2_uvw_geometry.png)

### General Equations (Eq. 1)

$$
\mathbf u = C \mathbf x_0 + C_f \mathbf x_f, \qquad
\mathbf v = C \mathbf y_0 + C_f \mathbf y_f, \qquad
\mathbf w = C \mathbf z_0 + C_f \mathbf z_f, \qquad
l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}
$$

### Matrix Example (Initial Coordinates $\mathbf x_0 = [-1, 0, 1, 0, 0]^T,\ \mathbf y_0 = [0, -1, 0, 1, 0]^T,\ \mathbf z_0 = \mathbf 0$)

* **$\mathbf x_0, \mathbf y_0, \mathbf z_0$ (5×1):** Initial coordinates of free nodes $1 \dots 5$ (m, from A.1).
* **$\mathbf x_f, \mathbf y_f, \mathbf z_f$ (4×1):** Fixed-anchor coordinates of nodes $6 \dots 9$ (m, from A.1).
* **$C$ (12×5) and $C_f$ (12×4):** Free-node and fixed-anchor connectivity matrices (from A.3).
* **$\mathbf u, \mathbf v, \mathbf w$ (12×1):** Cable coordinate differences $u_j = x_i - x_k,\ v_j = y_i - y_k,\ w_j = z_i - z_k$ (m).
* **$\mathbf l$ (12×1) and $L^{-1}$ (12×12):** Cable lengths $l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}$ (m) and diagonal inverse-length matrix $\mathrm{diag}(1/\mathbf l)$ (m⁻¹).

$$
\underset{\mathbf u\ (12\times 1)}{\begin{bmatrix}
1 \\
0 \\
-1 \\
0 \\
-1 \\
-1 \\
-1 \\
1 \\
0 \\
-1 \\
0 \\
1
\end{bmatrix}} =
\underset{C\ (12\times 5)}{\begin{bmatrix}
1 & 0 & 0 & 0 & 0 \\
0 & 1 & 0 & 0 & 0 \\
0 & 0 & 1 & 0 & 0 \\
0 & 0 & 0 & 1 & 0 \\
1 & 0 & 0 & -1 & 0 \\
1 & -1 & 0 & 0 & 0 \\
0 & 1 & -1 & 0 & 0 \\
0 & 0 & 1 & -1 & 0 \\
0 & 0 & 0 & 1 & -1 \\
1 & 0 & 0 & 0 & -1 \\
0 & 1 & 0 & 0 & -1 \\
0 & 0 & 1 & 0 & -1
\end{bmatrix}}
\underset{\mathbf x_0\ (5\times 1)}{\begin{bmatrix}
-1 \\
0 \\
1 \\
0 \\
0
\end{bmatrix}} +
\underset{C_f\ (12\times 4)}{\begin{bmatrix}
-1 & 0 & 0 & 0 \\
0 & -1 & 0 & 0 \\
0 & 0 & -1 & 0 \\
0 & 0 & 0 & -1 \\
0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0
\end{bmatrix}}
\underset{\mathbf x_f\ (4\times 1)}{\begin{bmatrix}
-2 \\
0 \\
2 \\
0
\end{bmatrix}}
$$

$$
\begin{bmatrix} \mathbf u & \mathbf v & \mathbf w \end{bmatrix} =
\begin{bmatrix}
1 & 0 & 0 \\
0 & -3 & -1 \\
-1 & 0 & 0 \\
0 & 3 & -1 \\
-1 & -1 & 0 \\
-1 & 1 & 0 \\
-1 & -1 & 0 \\
1 & -1 & 0 \\
0 & 1 & 0 \\
-1 & 0 & 0 \\
0 & -1 & 0 \\
1 & 0 & 0
\end{bmatrix}\text{ m},
\qquad
\mathbf l =
\begin{bmatrix}
1 \\
\sqrt{10} \\
1 \\
\sqrt{10} \\
\sqrt{2} \\
\sqrt{2} \\
\sqrt{2} \\
\sqrt{2} \\
1 \\
1 \\
1 \\
1
\end{bmatrix}
\approx
\begin{bmatrix}
1.000 \\
3.162 \\
1.000 \\
3.162 \\
1.414 \\
1.414 \\
1.414 \\
1.414 \\
1.000 \\
1.000 \\
1.000 \\
1.000
\end{bmatrix}\text{ m}
$$

$$
L^{-1} = \mathrm{diag}(1 / \mathbf l) =
\begin{bmatrix}
1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 1/\sqrt{10} & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 1/\sqrt{10} & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 1/\sqrt{2} & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 1/\sqrt{2} & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 1/\sqrt{2} & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 1/\sqrt{2} & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1
\end{bmatrix}\text{ m}^{-1}
$$

**Add to your program:**

```python
def coordinate_differences(
    C: FloatMatrix,
    x: FloatVector,
    y: FloatVector,
    z: FloatVector,
    C_f: FloatMatrix,
    x_f: FloatVector,
    y_f: FloatVector,
    z_f: FloatVector,
) -> tuple[FloatVector, FloatVector, FloatVector, FloatVector]:
    """Branch differences (u, v, w) and lengths l of shape (m,)."""
    u = C @ x + C_f @ x_f             # (12,) x_start - x_end for all 12 cables
    v = C @ y + C_f @ y_f             # (12,) y_start - y_end for all 12 cables
    w = C @ z + C_f @ z_f             # (12,) z_start - z_end for all 12 cables
    l = np.sqrt(u**2 + v**2 + w**2)   # (12,) Euclidean length of each cable
    return u, v, w, l


u_init, v_init, w_init, l_init = coordinate_differences(
    C, x_0, y_0, z_0, C_f, x_f, y_f, z_f
)
print("Initial cable lengths l_init (m):", l_init)
```

**Example output:**

```text
Initial cable lengths l_init (m): [1.    3.162 1.    3.162 1.414 1.414 1.414 1.414 1.    1.    1.    1.   ]
```

### B.3 Nonlinear equilibrium in 4 stages, equation (2)

From a single cable's tension $s_j$ and length $l_j$, we derive the 4-stage matrix equilibrium equation $\mathbf e_x = C^T U L^{-1} \mathbf s - \mathbf p_x$, reading the matrix product **right to left** from Stage 1 to Stage 4.

![Section B.3 Four-Stage Nonlinear Equilibrium and Flat Net Imbalance](images/fd_sec_b3_nonlinear_stages.png)

### How Stages 1–4 Are Derived (From One Cable to Matrix Form, Eq. 2)

1. **Single cable $j\ (i \to k)$:** Cable $j$ pulls with axial tension $s_j$ (kN) along its 3D length $l_j$ (m). By similar triangles, its direction cosine along $x$ is $u_j / l_j = (x_i - x_k) / l_j$, so its horizontal force component is:

$$
F_{x,j} = s_j \frac{u_j}{l_j} = u_j \underbrace{\left(\frac{s_j}{l_j}\right)} _ {\text{Stage 1: } q_j}
$$

2. **All 12 cables in matrix form (Stages 1 & 2):** Using the diagonal matrices $L^{-1} = \mathrm{diag}(1/l_1, \dots, 1/l_{12})$ and $U = \mathrm{diag}(u_1, \dots, u_{12})$:
   * **Stage 1:** $\mathbf q = L^{-1} \mathbf s\ (12 \times 1)$ divides each cable's tension $s_j$ by its length $l_j$ ($q_j = s_j / l_j$).
   * **Stage 2:** $\mathbf F_x = U \mathbf q = U L^{-1} \mathbf s\ (12 \times 1)$ multiplies each cable's ratio $q_j$ by its span $u_j$ ($F_{x,j} = u_j q_j$).
3. **Force balance at the 5 free nodes (Stages 3 & 4):** Row $i$ of $C^T\ (5 \times 12)$ has $+1$ for cables starting at node $i$ and $-1$ for cables ending at node $i$, so multiplying by $C^T$ sums the cable forces at each free node $i = 1 \dots 5$, and subtracting external load $\mathbf p_x\ (5 \times 1)$ gives the out-of-balance residual:

$$
\mathbf e_x = \underbrace{C^T} _ {\text{Stage 3: sum at nodes } (5\times 12)} \quad \underbrace{U} _ {\text{Stage 2: project } x\ (12\times 12)} \quad \underbrace{L^{-1} \mathbf s} _ {\text{Stage 1: } q_j = s_j / l_j\ (12\times 1)} \quad - \quad \underbrace{\mathbf p_x} _ {\text{Stage 4: load } (5\times 1)}
$$

---

### Stage-by-Stage Matrix Breakdown (Flat Trial Net with $s_j = 1$ kN)

#### Stage 1 — Force Density Ratios: $\mathbf q = L^{-1} \mathbf s\ (12 \times 1)$

* **$L^{-1}$ (12×12):** Diagonal inverse-length matrix $\mathrm{diag}(1/l_1, \dots, 1/l_{12})$ (m⁻¹).
* **$\mathbf s$ (12×1):** Trial axial cable tensions $s_j$ (kN).
* **$\mathbf q = L^{-1}\mathbf s$ (12×1):** Force-to-length ratios $q_j = s_j / l_j$ (kN/m).

$$
\mathbf q =
\underset{L^{-1}\ (12\times 12)}{\begin{bmatrix}
1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 1/\sqrt{10} & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 1/\sqrt{10} & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 1/\sqrt{2} & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 1/\sqrt{2} & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 1/\sqrt{2} & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 1/\sqrt{2} & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1
\end{bmatrix}}
\underset{\mathbf s\ (12\times 1)}{\begin{bmatrix}
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1
\end{bmatrix}} =
\begin{bmatrix}
1 \\
1/\sqrt{10} \\
1 \\
1/\sqrt{10} \\
1/\sqrt{2} \\
1/\sqrt{2} \\
1/\sqrt{2} \\
1/\sqrt{2} \\
1 \\
1 \\
1 \\
1
\end{bmatrix}
\approx
\begin{bmatrix}
1.000 \\
0.316 \\
1.000 \\
0.316 \\
0.707 \\
0.707 \\
0.707 \\
0.707 \\
1.000 \\
1.000 \\
1.000 \\
1.000
\end{bmatrix}\text{ kN/m}
$$

#### Stage 2 — Projected Branch Force Components: $\mathbf F_x = U \mathbf q,\ \mathbf F_y = V \mathbf q,\ \mathbf F_z = W \mathbf q\ (12 \times 1)$

* **$U, V, W$ (12×12):** Diagonal matrices $\mathrm{diag}(\mathbf u),\ \mathrm{diag}(\mathbf v),\ \mathrm{diag}(\mathbf w)$ holding the 12 cable coordinate differences $u_j = x_i - x_k,\ v_j = y_i - y_k,\ w_j = z_i - z_k$ (m) from Section B.2 ($\mathbf u = C\mathbf x + C_f\mathbf x_f$).
* **$\mathbf q$ (12×1):** Cable force-density vector $q_j = s_j / l_j$ (kN/m) from Stage 1.
* **$\mathbf F_x, \mathbf F_y, \mathbf F_z$ (12×1):** Directed cable force components $F_{x,j} = u_j q_j,\ F_{y,j} = v_j q_j,\ F_{z,j} = w_j q_j$ along $x, y, z$ (kN).

$$
\mathbf F_x = U \mathbf q =
\underset{U = \mathrm{diag}(\mathbf u)\ (12\times 12)}{\begin{bmatrix}
1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & -1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & -1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & -1 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & -1 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & -1 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1
\end{bmatrix}}
\underset{\mathbf q\ (12\times 1)}{\begin{bmatrix}
1.000 \\
0.316 \\
1.000 \\
0.316 \\
0.707 \\
0.707 \\
0.707 \\
0.707 \\
1.000 \\
1.000 \\
1.000 \\
1.000
\end{bmatrix}} =
\begin{bmatrix}
1.000 \\
0 \\
-1.000 \\
0 \\
-0.707 \\
-0.707 \\
-0.707 \\
0.707 \\
0 \\
-1.000 \\
0 \\
1.000
\end{bmatrix}\text{ kN}
\begin{matrix}
\leftarrow b_1: u_1 q_1 = (+1)(1.000) \\
\leftarrow b_2: u_2 q_2 = (0)(0.316) \\
\leftarrow b_3: u_3 q_3 = (-1)(1.000) \\
\leftarrow b_4: u_4 q_4 = (0)(0.316) \\
\leftarrow b_5: u_5 q_5 = (-1)(0.707) \\
\leftarrow b_6: u_6 q_6 = (-1)(0.707) \\
\leftarrow b_7: u_7 q_7 = (-1)(0.707) \\
\leftarrow b_8: u_8 q_8 = (+1)(0.707) \\
\leftarrow b_9: u_9 q_9 = (0)(1.000) \\
\leftarrow b_{10}: u_{10} q_{10} = (-1)(1.000) \\
\leftarrow b_{11}: u_{11} q_{11} = (0)(1.000) \\
\leftarrow b_{12}: u_{12} q_{12} = (+1)(1.000)
\end{matrix}
$$

Similarly along $y$ ($\mathbf F_y = V \mathbf q$) and $z$ ($\mathbf F_z = W \mathbf q$):

$$
\mathbf F_y = V \mathbf q =
\underset{V\ (12\times 12)}{\begin{bmatrix}
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & -3 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 3 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & -1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & -1 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & -1 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & -1 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0
\end{bmatrix}}
\underset{\mathbf q\ (12\times 1)}{\begin{bmatrix}
1.000 \\
0.316 \\
1.000 \\
0.316 \\
0.707 \\
0.707 \\
0.707 \\
0.707 \\
1.000 \\
1.000 \\
1.000 \\
1.000
\end{bmatrix}} =
\begin{bmatrix}
0 \\
-0.949 \\
0 \\
0.949 \\
-0.707 \\
0.707 \\
-0.707 \\
-0.707 \\
1.000 \\
0 \\
-1.000 \\
0
\end{bmatrix}\text{ kN}
$$

$$
\mathbf F_z = W \mathbf q =
\underset{W\ (12\times 12)}{\begin{bmatrix}
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & -1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & -1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0
\end{bmatrix}}
\underset{\mathbf q\ (12\times 1)}{\begin{bmatrix}
1.000 \\
0.316 \\
1.000 \\
0.316 \\
0.707 \\
0.707 \\
0.707 \\
0.707 \\
1.000 \\
1.000 \\
1.000 \\
1.000
\end{bmatrix}} =
\begin{bmatrix}
0 \\
-0.316 \\
0 \\
-0.316 \\
0 \\
0 \\
0 \\
0 \\
0 \\
0 \\
0 \\
0
\end{bmatrix}\text{ kN}
$$

#### Stage 3 — Sum Cable Forces at Free Nodes: $C^T \mathbf F_x,\ C^T \mathbf F_y,\ C^T \mathbf F_z\ (5 \times 1)$

* **$C^T$ (5×12):** Transpose of the free-node connectivity matrix (row $i$ has $+1$ for cables starting at node $i$ and $-1$ for cables ending at node $i$).
* **$\mathbf F_x, \mathbf F_y, \mathbf F_z$ (12×1):** Cable force components from Stage 2 (kN).
* **$C^T \mathbf F_x, C^T \mathbf F_y, C^T \mathbf F_z$ (5×1):** Net internal cable force resultant at each of the 5 free nodes (kN).

$$
C^T \mathbf F_x =
\underset{C^T\ (5\times 12)}{\begin{bmatrix}
1 & 0 & 0 & 0 & 1 & 1 & 0 & 0 & 0 & 1 & 0 & 0 \\
0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 \\
0 & 0 & 0 & 1 & -1 & 0 & 0 & -1 & 1 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & -1 & -1 & -1 & -1
\end{bmatrix}}
\underset{\mathbf F_x\ (12\times 1)}{\begin{bmatrix}
1.000 \\
0 \\
-1.000 \\
0 \\
-0.707 \\
-0.707 \\
-0.707 \\
0.707 \\
0 \\
-1.000 \\
0 \\
1.000
\end{bmatrix}} =
\begin{bmatrix}
-1.414 \\
0 \\
1.414 \\
0 \\
0
\end{bmatrix}\text{ kN}
\begin{matrix}
\leftarrow \text{Node 1: } 1 - 0.707 - 0.707 - 1 = -1.414 \\
\leftarrow \text{Node 2: } 0 - (-0.707) - 0.707 + 0 = 0 \\
\leftarrow \text{Node 3: } -1 - (-0.707) + 0.707 + 1 = 1.414 \\
\leftarrow \text{Node 4: } 0 - (-0.707) - 0.707 + 0 = 0 \\
\leftarrow \text{Node 5: } 0 - (-1) - 0 - 1 = 0
\end{matrix}
$$

$$
C^T \mathbf F_y =
\underset{C^T\ (5\times 12)}{\begin{bmatrix}
1 & 0 & 0 & 0 & 1 & 1 & 0 & 0 & 0 & 1 & 0 & 0 \\
0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 \\
0 & 0 & 0 & 1 & -1 & 0 & 0 & -1 & 1 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & -1 & -1 & -1 & -1
\end{bmatrix}}
\underset{\mathbf F_y\ (12\times 1)}{\begin{bmatrix}
0 \\
-0.949 \\
0 \\
0.949 \\
-0.707 \\
0.707 \\
-0.707 \\
-0.707 \\
1.000 \\
0 \\
-1.000 \\
0
\end{bmatrix}} =
\begin{bmatrix}
0 \\
-3.363 \\
0 \\
3.363 \\
0
\end{bmatrix}\text{ kN},
\qquad
C^T \mathbf F_z =
\begin{bmatrix}
0 \\
-0.316 \\
0 \\
-0.316 \\
0
\end{bmatrix}\text{ kN}
$$

#### Stage 4 — Subtract Applied Loads to Check Equilibrium: $\mathbf e = C^T \mathbf F - \mathbf p\ (5 \times 1)$

* **$C^T \mathbf F_x, C^T \mathbf F_y, C^T \mathbf F_z$ (5×1):** Internal cable force resultants at free nodes $1 \dots 5$ (kN).
* **$\mathbf p_x, \mathbf p_y, \mathbf p_z$ (5×1):** External applied nodal loads at free nodes $1 \dots 5$ (kN).
* **$\mathbf e_x, \mathbf e_y, \mathbf e_z$ (5×1):** Out-of-balance nodal force residuals (kN; zero when in equilibrium).

$$
\mathbf e_x =
\begin{bmatrix}
-1.414 \\
0 \\
1.414 \\
0 \\
0
\end{bmatrix} -
\begin{bmatrix}
0 \\
0 \\
0 \\
0 \\
0
\end{bmatrix} =
\begin{bmatrix}
-1.414 \\
0 \\
1.414 \\
0 \\
0
\end{bmatrix},
\qquad
\mathbf e_y =
\begin{bmatrix}
0 \\
-3.363 \\
0 \\
3.363 \\
0
\end{bmatrix} -
\begin{bmatrix}
0 \\
0 \\
0 \\
0 \\
0
\end{bmatrix} =
\begin{bmatrix}
0 \\
-3.363 \\
0 \\
3.363 \\
0
\end{bmatrix}\text{ kN}
$$

$$
\mathbf e_z =
\begin{bmatrix}
0 \\
-0.316 \\
0 \\
-0.316 \\
0
\end{bmatrix} -
\begin{bmatrix}
-0.5 \\
-0.5 \\
-0.5 \\
-0.5 \\
-0.5
\end{bmatrix} =
\begin{bmatrix}
0.500 \\
0.184 \\
0.500 \\
0.184 \\
0.500
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Node 1 out of balance} \\
\leftarrow \text{Node 2 out of balance} \\
\leftarrow \text{Node 3 out of balance} \\
\leftarrow \text{Node 4 out of balance} \\
\leftarrow \text{Node 5 out of balance}
\end{matrix}
$$

**Add to your program:**

```python
def equilibrium_error(x, y, z, s):
    """Eq. (2): C^T U L^-1 s - p along (x, y, z). Zero means equilibrium."""
    u, v, w, l = coordinate_differences(C, x, y, z, C_f, x_f, y_f, z_f)
    L_inv = np.diag(1.0 / l)          # (12, 12) diagonal inverse-length matrix L^-1
    return (
        C.T @ np.diag(u) @ L_inv @ s - p_x,   # chain Stages 1-4 right-to-left along x
        C.T @ np.diag(v) @ L_inv @ s - p_y,   # chain Stages 1-4 right-to-left along y
        C.T @ np.diag(w) @ L_inv @ s - p_z,   # chain Stages 1-4 right-to-left along z
    )


ex, ey, ez = equilibrium_error(x_0, y_0, z_0, s_0)
print("Initial out-of-balance residual e_z at (x_0, y_0, z_0) (kN):", ez)
```

**Example output:**

```text
Initial out-of-balance residual e_z at (x_0, y_0, z_0) (kN): [0.5   0.184 0.5   0.184 0.5  ]
```

---

## Part C. The force density trick: a linear system

### C.1 The force density trick and the diagonal swap, equations (4) to (6)

In Section B.3, the horizontal branch force $F_{x,j} = s_j (u_j / l_j)$ was nonlinear because the unknown length $l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}$ sat in the denominator. If instead we prescribe the **force density** $q_j = s_j / l_j$ (kN/m, so $s_j = q_j l_j$), then $l_j$ in the numerator and denominator cancels out: $F_{x,j} = (q_j l_j)(u_j / l_j) = q_j u_j$.

![Section C.1 How Force Density Uses Coordinate Difference u to Linearize Equilibrium](images/fd_sec_c1_force_density_trick.png)

### General Equations (Eqs. 4–6) & Meaning of $u$

$$
q_j = \frac{s_j}{l_j} \quad (\mathbf q = L^{-1} \mathbf s)
\qquad \Longrightarrow \qquad
F_{x, j} = s_j \frac{u_j}{l_j} = (q_j l_j) \frac{u_j}{l_j} = q_j u_j = q_j (x_i - x_k)
$$

$$
C^T U \mathbf q = C^T Q \mathbf u = \mathbf p_x, \qquad
C^T V \mathbf q = C^T Q \mathbf v = \mathbf p_y, \qquad
C^T W \mathbf q = C^T Q \mathbf w = \mathbf p_z
$$

* **$u_j$, $\mathbf u$ (12×1), and $U = \mathrm{diag}(\mathbf u)$ (12×12):** $u_j = x_i - x_k$ is the $x$-coordinate difference (m) between start node $i$ and end node $k$ of branch $j$ (similarly $v_j = y_i - y_k$ in $V$, $w_j = z_i - z_k$ in $W$).
* **Why we swap $U \mathbf q = Q \mathbf u$:** moves the **unknown** coordinate vector $\mathbf u$ to the right of the **known** diagonal force-density matrix $Q = \mathrm{diag}(\mathbf q)$.

### Matrix Example ($\mathbf F_x = U \mathbf q = Q \mathbf u$ on All 12 Branches)

* **$U = \mathrm{diag}(\mathbf u)$ (12×12) and $\mathbf u$ (12×1):** Unknown cable $x$-coordinate differences $u_j = x_i - x_k$ (m).
* **$Q = \mathrm{diag}(\mathbf q)$ (12×12) and $\mathbf q$ (12×1):** Known prescribed cable force densities $q_j$ (kN/m).
* **$\mathbf F_x = U\mathbf q = Q\mathbf u$ (12×1):** Linearized horizontal cable force components $q_j(x_i - x_k)$ (kN).

$$
\mathbf F_x =
\underset{U\ (12\times 12)}{\begin{bmatrix}
u_1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & u_2 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & u_3 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & u_4 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & u_5 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & u_6 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & u_7 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & u_8 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & u_9 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & u_{10} & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & u_{11} & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & u_{12}
\end{bmatrix}}
\underset{\mathbf q\ (12\times 1)}{\begin{bmatrix}
2 \\
2 \\
2 \\
2 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1 \\
1
\end{bmatrix}} =
\underset{Q\ (12\times 12)}{\begin{bmatrix}
2 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 2 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 2 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 2 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1
\end{bmatrix}}
\underset{\mathbf u\ (12\times 1)}{\begin{bmatrix}
u_1 \\
u_2 \\
u_3 \\
u_4 \\
u_5 \\
u_6 \\
u_7 \\
u_8 \\
u_9 \\
u_{10} \\
u_{11} \\
u_{12}
\end{bmatrix}} =
\begin{bmatrix}
2(x_1 - x_6) \\
2(x_2 - x_7) \\
2(x_3 - x_8) \\
2(x_4 - x_9) \\
1(x_1 - x_4) \\
1(x_1 - x_2) \\
1(x_2 - x_3) \\
1(x_3 - x_4) \\
1(x_4 - x_5) \\
1(x_1 - x_5) \\
1(x_2 - x_5) \\
1(x_3 - x_5)
\end{bmatrix}
$$

**Add to your program:**

```python
# 2 kN/m on the 4 outer anchor cables (0..3), 1 kN/m on the 8 inner cables (4..11)
q = np.array([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1], dtype=float)
print("Prescribed force densities q (kN/m):", q)
```

**Example output:**

```text
Prescribed force densities q (kN/m): [2. 2. 2. 2. 1. 1. 1. 1. 1. 1. 1. 1.]
```

### C.2 System matrices $D$ and $D_f$, equations (7) and (8)

Substituting $\mathbf u = C \mathbf x + C_f \mathbf x_f$ into $C^T Q \mathbf u = \mathbf p_x$ separates unknown free-node coordinates $\mathbf x$ from known anchor coordinates $\mathbf x_f$ via $D = C^T Q C\ (5 \times 5)$ and $D_f = C^T Q C_f\ (5 \times 4)$.

![Sections C.2 to D.1 Physical Meaning of D and Solved 3D Saddle Equilibrium Net](images/fd_sec_c2_c3_solved_net.png)

### General Equations (Eqs. 7–8)

$$
(C^T Q C)\mathbf x + (C^T Q C_f)\mathbf x_f = \mathbf p_x
\qquad \Longrightarrow \qquad
D \mathbf x = \mathbf p_x - D_f \mathbf x_f = \mathbf b_x
$$

### 1. Symbolic Structure of $D$ and Schek Fig. 4 ($q_j = j$)

* **$D = C^T Q C$ (5×5):** Free-node stiffness matrix (diagonal $D_{ii}$ sums $q_j$ of cables touching free node $i$; off-diagonal $D_{ik} = -q_j$ for cable $j$ between free nodes $i$ and $k$).
* **$D_f = C^T Q C_f$ (5×4):** Fixed-anchor coupling matrix ($D_{f(i,k)} = -q_j$ if cable $j$ connects free node $i$ to fixed anchor $k$).
* **$\mathbf p_z$ (5×1) and $\mathbf z_f$ (4×1):** External vertical loads (kN) and known anchor heights (m).
* **$\mathbf b_z = \mathbf p_z - D_f \mathbf z_f$ (5×1):** Known right-hand side vector combining external loads and anchor pull (kN).

$$
D =
\begin{bmatrix}
q_1+q_5+q_6+q_{10} & -q_6 & 0 & -q_5 & -q_{10} \\
-q_6 & q_2+q_6+q_7+q_{11} & -q_7 & 0 & -q_{11} \\
0 & -q_7 & q_3+q_7+q_8+q_{12} & -q_8 & -q_{12} \\
-q_5 & 0 & -q_8 & q_4+q_5+q_8+q_9 & -q_9 \\
-q_{10} & -q_{11} & -q_{12} & -q_9 & q_9+q_{10}+q_{11}+q_{12}
\end{bmatrix},
\qquad
D_{(q_j = j)} =
\begin{bmatrix}
22 & -6 & 0 & -5 & -10 \\
-6 & 26 & -7 & 0 & -11 \\
0 & -7 & 30 & -8 & -12 \\
-5 & 0 & -8 & 26 & -9 \\
-10 & -11 & -12 & -9 & 42
\end{bmatrix}
$$

### 2. Actual Matrices $D$, $D_f$, and Right-Hand Side $\mathbf b_z = \mathbf p_z - D_f \mathbf z_f$

$$
D = C^T Q C =
\begin{bmatrix}
5 & -1 & 0 & -1 & -1 \\
-1 & 5 & -1 & 0 & -1 \\
0 & -1 & 5 & -1 & -1 \\
-1 & 0 & -1 & 5 & -1 \\
-1 & -1 & -1 & -1 & 4
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Node 1: } 2+1+1+1=5 \\
\leftarrow \text{Node 2: } 2+1+1+1=5 \\
\leftarrow \text{Node 3: } 2+1+1+1=5 \\
\leftarrow \text{Node 4: } 2+1+1+1=5 \\
\leftarrow \text{Node 5: } 1+1+1+1=4
\end{matrix},
\qquad
D_f = C^T Q C_f =
\begin{bmatrix}
-2 & 0 & 0 & 0 \\
0 & -2 & 0 & 0 \\
0 & 0 & -2 & 0 \\
0 & 0 & 0 & -2 \\
0 & 0 & 0 & 0
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Node 1 to Anchor 6} \\
\leftarrow \text{Node 2 to Anchor 7} \\
\leftarrow \text{Node 3 to Anchor 8} \\
\leftarrow \text{Node 4 to Anchor 9} \\
\leftarrow \text{Node 5 (no anchor)}
\end{matrix}
$$

$$
\mathbf b_z = \mathbf p_z - D_f \mathbf z_f =
\begin{bmatrix}
-0.5 \\
-0.5 \\
-0.5 \\
-0.5 \\
-0.5
\end{bmatrix} -
\begin{bmatrix}
-2 & 0 & 0 & 0 \\
0 & -2 & 0 & 0 \\
0 & 0 & -2 & 0 \\
0 & 0 & 0 & -2 \\
0 & 0 & 0 & 0
\end{bmatrix}
\begin{bmatrix}
0 \\
1 \\
0 \\
1
\end{bmatrix} =
\begin{bmatrix}
-0.5 \\
-0.5 \\
-0.5 \\
-0.5 \\
-0.5
\end{bmatrix} -
\begin{bmatrix}
0 \\
-2.0 \\
0 \\
-2.0 \\
0
\end{bmatrix} =
\begin{bmatrix}
-0.5 \\
1.5 \\
-0.5 \\
1.5 \\
-0.5
\end{bmatrix}\text{ kN}
\begin{matrix}
\leftarrow \text{Node 1 (Anchor 6 at } z_6=0\text{)} \\
\leftarrow \text{Node 2 (Anchor 7 at } z_7=1\text{ pulls up }+2.0\text{ kN)} \\
\leftarrow \text{Node 3 (Anchor 8 at } z_8=0\text{)} \\
\leftarrow \text{Node 4 (Anchor 9 at } z_9=1\text{ pulls up }+2.0\text{ kN)} \\
\leftarrow \text{Node 5 (no direct anchor cable)}
\end{matrix}
$$

**Add to your program:**

```python
Q = np.diag(q)                                  # (12, 12) diagonal force-density matrix
D = C.T @ Q @ C                                 # (5, 5)   free-node stiffness matrix, eq. (8)
D_f = C.T @ Q @ C_f                             # (5, 4)   fixed-anchor coupling matrix, eq. (8)
rhs = np.c_[p_x - D_f @ x_f, p_y - D_f @ y_f, p_z - D_f @ z_f]  # (5, 3) right-hand sides [b_x, b_y, b_z]
print("D (5x5):\n", D)
print("D_f (5x4):\n", D_f)
print("RHS [b_x, b_y, b_z] (5x3):\n", rhs)
```

**Example output:**

```text
D (5x5):
 [[ 5. -1.  0. -1. -1.]
 [-1.  5. -1.  0. -1.]
 [ 0. -1.  5. -1. -1.]
 [-1.  0. -1.  5. -1.]
 [-1. -1. -1. -1.  4.]]
D_f (5x4):
 [[-2.  0.  0.  0.]
 [ 0. -2.  0.  0.]
 [ 0.  0. -2.  0.]
 [ 0.  0.  0. -2.]
 [ 0.  0.  0.  0.]]
RHS [b_x, b_y, b_z] (5x3):
 [[-4.   0.  -0.5]
 [ 0.   4.   1.5]
 [ 4.   0.  -0.5]
 [ 0.  -4.   1.5]
 [ 0.   0.  -0.5]]
```

### C.3 Direct linear solve for free node coordinates, equation (9)

Because $D = C^T Q C$ is constant and symmetric positive-definite, solving $D \mathbf x = \mathbf b_x$, $D \mathbf y = \mathbf b_y$, $D \mathbf z = \mathbf b_z$ gives the exact 3D equilibrium coordinates in one direct step.

### General Equations (Eq. 9)

$$
D \mathbf x = \mathbf p_x - D_f \mathbf x_f, \qquad
D \mathbf y = \mathbf p_y - D_f \mathbf y_f, \qquad
D \mathbf z = \mathbf p_z - D_f \mathbf z_f
$$

### Matrix Example (Vertical Equilibrium Solve $D \mathbf z = \mathbf b_z$ and 3D Coordinates)

* **$D$ (5×5):** Symmetric positive-definite free-node stiffness matrix (kN/m).
* **$\mathbf b_z$ (5×1):** Known vertical right-hand side $\mathbf p_z - D_f \mathbf z_f$ (kN).
* **$\mathbf x, \mathbf y, \mathbf z$ (5×1):** Solved equilibrium coordinates of the 5 free nodes $1 \dots 5$ (m).

$$
\underset{D\ (5\times 5)}{\begin{bmatrix}
5 & -1 & 0 & -1 & -1 \\
-1 & 5 & -1 & 0 & -1 \\
0 & -1 & 5 & -1 & -1 \\
-1 & 0 & -1 & 5 & -1 \\
-1 & -1 & -1 & -1 & 4
\end{bmatrix}}
\underset{\mathbf z\ (5\times 1)}{\begin{bmatrix}
z_1 \\
z_2 \\
z_3 \\
z_4 \\
z_5
\end{bmatrix}} =
\underset{\mathbf b_z\ (5\times 1)}{\begin{bmatrix}
-0.5 \\
1.5 \\
-0.5 \\
1.5 \\
-0.5
\end{bmatrix}}
\qquad \overset{\text{solve}}{\longrightarrow} \qquad
\mathbf z =
\begin{bmatrix}
0.045 \\
0.330 \\
0.045 \\
0.330 \\
0.063
\end{bmatrix}\text{ m}
$$

$$
\begin{bmatrix} \mathbf x & \mathbf y & \mathbf z \end{bmatrix} =
\begin{bmatrix}
-0.800 & 0.000 & 0.045 \\
0.000 & 0.800 & 0.330 \\
0.800 & 0.000 & 0.045 \\
0.000 & -0.800 & 0.330 \\
0.000 & 0.000 & 0.063
\end{bmatrix}\text{ m}
\begin{matrix}
\leftarrow \text{Node 1 (low corner)} \\
\leftarrow \text{Node 2 (pulled up by Anchor 7)} \\
\leftarrow \text{Node 3 (low corner)} \\
\leftarrow \text{Node 4 (pulled up by Anchor 9)} \\
\leftarrow \text{Node 5 (center saddle)}
\end{matrix}
$$

**Add to your program:**

```python
x: FloatVector = np.linalg.solve(D, p_x - D_f @ x_f)    # (5,) solve D x = b_x, eq. (9)
y: FloatVector = np.linalg.solve(D, p_y - D_f @ y_f)    # (5,) solve D y = b_y, eq. (9)
z: FloatVector = np.linalg.solve(D, p_z - D_f @ z_f)    # (5,) solve D z = b_z, eq. (9)
print("Solved free-node coordinates [x, y, z] (5x3):\n", np.c_[x, y, z])
```

**Example output:**

```text
Solved free-node coordinates [x, y, z] (5x3):
 [[-0.8   -0.     0.045]
 [-0.     0.8    0.33 ]
 [ 0.8   -0.     0.045]
 [-0.    -0.8    0.33 ]
 [ 0.    -0.     0.063]]
```

### C.4 Recovering cable lengths, forces, materialization cutting lengths, and verification, equation (10)

From the solved coordinates $(\mathbf x, \mathbf y, \mathbf z)$, we recompute branch lengths $\mathbf l$, recover branch tensions $\mathbf s = Q \mathbf l$, and compute unstressed cutting lengths $l_{0,j} = l_j / (1 + s_j / EA_j)$.

### General Equations (Schek Eq. 10 & Linkwitz Eq. 6.37)

$$
s_j = q_j l_j \quad (\mathbf s = Q \mathbf l = L \mathbf q), \qquad
\mathbf e_x = C^T U L^{-1} \mathbf s - \mathbf p_x = \mathbf 0, \qquad
l_{0,j} = \frac{l_j}{1 + s_j / EA_j}
$$

### Matrix Example ($\mathbf q$, $\mathbf l$, $\mathbf s$, and Cutting Lengths $\mathbf l_0$ for $EA = 500$ kN)

* **$\mathbf q$ (12×1):** Prescribed cable force densities $q_j$ (kN/m).
* **$\mathbf l$ (12×1):** Solved stressed equilibrium cable lengths $l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}$ (m).
* **$\mathbf s = \mathbf q \odot \mathbf l$ (12×1):** Recovered axial cable tensions $s_j = q_j l_j$ (kN).
* **$EA_j = E_j A_j$:** Cable axial stiffness (kN, Young's modulus $E_j$ times cross-sectional area $A_j$).
* **$\mathbf l_0$ (12×1) and $e_j = l_j - l_{0,j}$:** Unstressed workshop cutting lengths $l_{0,j} = l_j / (1 + s_j / EA_j)$ (m) and elastic stretch $e_j$ (mm).

$$
\underset{\mathbf q\ (\text{kN/m})}{\begin{bmatrix}
2.0 \\
2.0 \\
2.0 \\
2.0 \\
1.0 \\
1.0 \\
1.0 \\
1.0 \\
1.0 \\
1.0 \\
1.0 \\
1.0
\end{bmatrix}} \odot
\underset{\mathbf l\ (\text{m})}{\begin{bmatrix}
1.201 \\
1.374 \\
1.201 \\
1.374 \\
1.167 \\
1.167 \\
1.167 \\
1.167 \\
0.844 \\
0.800 \\
0.844 \\
0.800
\end{bmatrix}} =
\underset{\mathbf s\ (\text{kN})}{\begin{bmatrix}
2.402 \\
2.748 \\
2.402 \\
2.748 \\
1.167 \\
1.167 \\
1.167 \\
1.167 \\
0.844 \\
0.800 \\
0.844 \\
0.800
\end{bmatrix}}
\qquad \overset{EA_j = 500\text{ kN}}{\longrightarrow} \qquad
\underset{\mathbf l_0\ (\text{m})}{\begin{bmatrix}
1.195 \\
1.367 \\
1.195 \\
1.367 \\
1.164 \\
1.164 \\
1.164 \\
1.164 \\
0.842 \\
0.799 \\
0.842 \\
0.799
\end{bmatrix}}
\underset{\text{stretch } e_j\ (\text{mm})}{\begin{matrix}
\leftarrow b_1\ (1\to 6,\ e_1 = 5.7) \\
\leftarrow b_2\ (2\to 7,\ e_2 = 7.5) \\
\leftarrow b_3\ (3\to 8,\ e_3 = 5.7) \\
\leftarrow b_4\ (4\to 9,\ e_4 = 7.5) \\
\leftarrow b_5\ (1\to 4,\ e_5 = 2.7) \\
\leftarrow b_6\ (1\to 2,\ e_6 = 2.7) \\
\leftarrow b_7\ (2\to 3,\ e_7 = 2.7) \\
\leftarrow b_8\ (3\to 4,\ e_8 = 2.7) \\
\leftarrow b_9\ (4\to 5,\ e_9 = 1.4) \\
\leftarrow b_{10}\ (1\to 5,\ e_{10} = 1.3) \\
\leftarrow b_{11}\ (2\to 5,\ e_{11} = 1.4) \\
\leftarrow b_{12}\ (3\to 5,\ e_{12} = 1.3)
\end{matrix}}
$$

**Add to your program:**

```python
u, v, w, l = coordinate_differences(C, x, y, z, C_f, x_f, y_f, z_f)
s = l * q                                       # eq. (10): axial forces (kN)
EA = np.full(m, 500.0)                          # Linkwitz Sec. 6.5: axial stiffness EA (kN)
l_cutting = l / (1.0 + s / EA)                  # Linkwitz eq. (6.37): unstressed cutting lengths (m)
e_stretch = l - l_cutting                       # elastic elongation e = l - l_0 (m)
xyz_free = np.c_[x, y, z]
max_eq_error = max(
    np.abs(e).max() for e in equilibrium_error(x, y, z, s)
)
print("Lengths l (m):      ", l)
print("Forces s (kN):      ", s)
print("Cutting l_0 (m):    ", l_cutting)
print("Max equilibrium err:", f"{max_eq_error:.2e}")
```

**Example output:**

```text
Lengths l (m):       [1.201 1.374 1.201 1.374 1.167 1.167 1.167 1.167 0.844 0.8   0.844 0.8  ]
Forces s (kN):       [2.402 2.748 2.402 2.748 1.167 1.167 1.167 1.167 0.844 0.8   0.844 0.8  ]
Cutting l_0 (m):     [1.195 1.367 1.195 1.367 1.164 1.164 1.164 1.164 0.842 0.799 0.842 0.799]
Max equilibrium err: 1.11e-15
```

---

## Part D. The form-finding loop

### D.1 Complete linear form-finding function and support reactions (figure 3)

We package Steps A.3–C.4 into `form_finding` and compute the 3D support reactions $\mathbf R_f = C_f^T Q \mathbf U_{xyz}$ at the 4 fixed anchors.

![Fig. 3](images/schek_fig3.png)

### General Equations

$$
D \mathbf X = \mathbf P - D_f \mathbf X_f, \qquad
\mathbf U_{xyz} = C \mathbf X + C_f \mathbf X_f, \qquad
\mathbf R_f = C_f^T Q \mathbf U_{xyz}
$$

### Matrix Example (Support Reactions $\mathbf R_f$)

* **$C_f^T$ (4×12):** Transpose of the fixed-anchor connectivity matrix.
* **$Q$ (12×12):** Diagonal force-density matrix $\mathrm{diag}(\mathbf q)$ (kN/m).
* **$\mathbf U_{xyz} = [\mathbf u, \mathbf v, \mathbf w]$ (12×3):** Table of cable coordinate differences along $x, y, z$ (m).
* **$\mathbf R_f = C_f^T Q \mathbf U_{xyz}$ (4×3):** Support reaction forces $(R_{ix}, R_{iy}, R_{iz})$ at the 4 fixed anchors $6 \dots 9$ (kN).

$$
\mathbf R_f = C_f^T Q \mathbf U_{xyz} =
\begin{bmatrix}
R_{6x} & R_{6y} & R_{6z} \\
R_{7x} & R_{7y} & R_{7z} \\
R_{8x} & R_{8y} & R_{8z} \\
R_{9x} & R_{9y} & R_{9z}
\end{bmatrix} =
\begin{bmatrix}
-2.400 & 0.000 & -0.089 \\
0.000 & 2.400 & 1.339 \\
2.400 & 0.000 & -0.089 \\
0.000 & -2.400 & 1.339
\end{bmatrix}\text{ kN}
\begin{matrix}
\leftarrow \text{Anchor 6 (ground hold-down: }-0.089\text{ kN)} \\
\leftarrow \text{Anchor 7 (lifted mast: }+1.339\text{ kN)} \\
\leftarrow \text{Anchor 8 (ground hold-down: }-0.089\text{ kN)} \\
\leftarrow \text{Anchor 9 (lifted mast: }+1.339\text{ kN)}
\end{matrix}
$$

**Add to your program:**

```python
def form_finding(branches, n_free, xyz_fixed, q, p):
    """Schek section 2 in one call. xyz_fixed: (n_f, 3); p: (n_free, 3)."""
    n_s = n_free + len(xyz_fixed)
    C_s = np.zeros((len(branches), n_s))
    for j, (i, k) in enumerate(branches):
        C_s[j, i - 1], C_s[j, k - 1] = 1.0, -1.0               # sec. 2.1
    C, C_f = C_s[:, :n_free], C_s[:, n_free:]
    Q = np.diag(q)
    D, D_f = C.T @ Q @ C, C.T @ Q @ C_f                        # eq. (8)
    xyz = np.vstack([
        np.linalg.solve(D, p[:, a] - D_f @ xyz_fixed[:, a])
        for a in range(3)
    ]).T                                                       # eq. (9)
    uvw = C @ xyz + C_f @ xyz_fixed                            # eq. (1)
    l = np.linalg.norm(uvw, axis=1)
    s = l * q                                                  # eq. (10)
    reactions = C_f.T @ Q @ uvw                                # (4, 3) support reactions, eq. (5)
    return xyz, l, s, reactions
```

### D.2 Parameter study: moving anchors, changing force densities, and scale invariance

Moving anchors $\mathbf X_f$ only updates the right-hand side, changing $\mathbf q$ rebuilds $D$, and scaling $(2\mathbf q, 2\mathbf P)$ leaves the 3D geometry identical while doubling forces (scale invariance).

![Parts D, E and F Parameter Study, Energy Minimization and Target Length Constraints](images/fd_sec_e_f_constraints.png)

### Matrix Example (Free-Node Heights $\mathbf z$ Across 4 Cases)

* **$\mathbf z_{\text{case 1..4}}$ (5×1):** Equilibrium heights $z_1 \dots z_5$ of the 5 free nodes (m) for each of the 4 parameter cases.
* **$\mathbf s_{\text{case 1}}, \mathbf s_{\text{case 4}}$ (12×1):** Cable tension vectors (kN) before and after scaling $(2\mathbf q, 2\mathbf P)$.

$$
\begin{bmatrix}
\mathbf z_{\text{case 1}} & \mathbf z_{\text{case 2}} & \mathbf z_{\text{case 3}} & \mathbf z_{\text{case 4}}
\end{bmatrix} =
\begin{bmatrix}
0.045 & 1.045 & 0.104 & 0.045 \\
0.330 & 1.330 & 0.771 & 0.330 \\
0.045 & 1.045 & 0.104 & 0.045 \\
0.330 & 1.330 & 0.771 & 0.330 \\
0.063 & 1.063 & 0.313 & 0.063
\end{bmatrix}\text{ m}
\begin{matrix}
\leftarrow \text{Node 1} \\
\leftarrow \text{Node 2} \\
\leftarrow \text{Node 3} \\
\leftarrow \text{Node 4} \\
\leftarrow \text{Node 5 (center)}
\end{matrix},
\qquad
\mathbf s_{\text{case 4}} = 2\mathbf s_{\text{case 1}}
$$

| Case | Matrix $D\ (5\times 5)$ | RHS $\mathbf P - D_f \mathbf X_f$ | Center Height $z_5\ (\text{m})$ | Max Force $\max(\mathbf s)$ |
|---|---|---|---|---|
| **1. Base case** ($q_{\text{anchor}} = 2,\ \mathbf p_z = -0.5$) | built once | base | 0.063 m | 2.748 kN |
| **2. All anchors lifted** +1 m | **unchanged** | updated | 1.063 m | 2.748 kN |
| **3. Stiffer anchors** ($q_{\text{anchor}} = 10,\ \mathbf p_z = -0.5$) | **rebuilt** | updated | 0.313 m | 4.732 kN |
| **4. Scale invariance** ($2\mathbf q,\ 2\mathbf p_z$) | $2\times$ | $2\times$ | **0.063 m** | **5.496 kN ($2\times$)** |

**Add to your program:**

```python
xyz_fixed = np.c_[x_f, y_f, z_f]
p = np.c_[p_x, p_y, p_z]
xyz1, l1, s1, R1 = form_finding(branches, n, xyz_fixed, q, p)

# Case 2: shift fixed anchor heights by +1 m (only RHS changes)
xyz2, *_ = form_finding(
    branches, n, xyz_fixed + np.array([0.0, 0.0, 1.0]), q, p
)

# Case 3: raise anchor force densities to 10 kN/m (D is rebuilt)
q_stiff_anchors = np.where(np.arange(m) < 4, 10.0, 1.0)
xyz3, *_ = form_finding(branches, n, xyz_fixed, q_stiff_anchors, p)

# Case 4: Linkwitz Sec. 6.7 scale invariance — doubling both q and p leaves geometry identical
xyz4, l4, s4, R4 = form_finding(branches, n, xyz_fixed, 2.0 * q, 2.0 * p)
scale_invariance_xyz_diff = np.abs(xyz4 - xyz1).max()
z_center_cases = (xyz1[4, 2], xyz2[4, 2], xyz3[4, 2], xyz4[4, 2])
print("Support reactions R_f (4x3):\n", R1)
print("Vertical reaction sum (kN):", R1[:, 2].sum())
print("Center z_5 across Cases 1..4 (m):", np.round(z_center_cases, 3))
print("Scale invariance max |xyz4 - xyz1|:", scale_invariance_xyz_diff)
```

**Example output:**

```text
Support reactions R_f (4x3):
 [[-2.4    0.    -0.089]
 [ 0.     2.4    1.339]
 [ 2.4    0.    -0.089]
 [ 0.    -2.4    1.339]]
Vertical reaction sum (kN): 2.5
Center z_5 across Cases 1..4 (m): [0.063 1.063 0.313 0.063]
Scale invariance max |xyz4 - xyz1|: 0.0
```

---

## Part E. What the force densities mean

### E.1 Geometric meaning of force densities (section 4)

For an unloaded network ($\mathbf P = \mathbf 0$), solving $D\mathbf X = -D_f\mathbf X_f$ minimizes the weighted squared-length functional $\Phi = \sum q_j l_j^2$ (Theorem 1), and setting $q_j = c / l_j$ produces a constant-force net $s_j = c$ (Theorem 2).

### General Equations (Eqs. 37–40)

$$
\Phi(\mathbf x, \mathbf y, \mathbf z) = \mathbf u^T Q \mathbf u + \mathbf v^T Q \mathbf v + \mathbf w^T Q \mathbf w = \sum_{j=1}^m q_j l_j^2 \longrightarrow \min
\qquad \Longleftrightarrow \qquad
\frac{\partial \Phi}{\partial \mathbf x} = 2 C^T Q \mathbf u = 2 (D \mathbf x + D_f \mathbf x_f) = \mathbf 0
$$

### Matrix Example (Unloaded Saddle $\mathbf P = \mathbf 0$)

* **$\mathbf X_0 = [\mathbf x_0, \mathbf y_0, \mathbf z_0]$ (5×3):** Equilibrium coordinates of the 5 free nodes when external load $\mathbf P = \mathbf 0$ (m).
* **$\mathbf U_0 = C\mathbf X_0 + C_f\mathbf X_f$ (12×3):** Cable coordinate differences in the unloaded saddle (m).
* **$\Phi = \sum q_j l_j^2$ and $\nabla\Phi(\mathbf X_0)$ (5×3):** Weighted squared-length energy functional and its gradient $2 C^T Q \mathbf U_0$ at equilibrium.

$$
\mathbf X_0 = \begin{bmatrix}
-0.800 & 0.000 & 0.357 \\
0.000 & 0.800 & 0.643 \\
0.800 & 0.000 & 0.357 \\
0.000 & -0.800 & 0.643 \\
0.000 & 0.000 & 0.500
\end{bmatrix}\text{ m}
\begin{matrix}
\leftarrow \text{Node 1 (low corner, } z_1 = 5/14 \approx 0.357\text{ m)} \\
\leftarrow \text{Node 2 (high corner, } z_2 = 9/14 \approx 0.643\text{ m)} \\
\leftarrow \text{Node 3 (low corner, } z_3 = 5/14 \approx 0.357\text{ m)} \\
\leftarrow \text{Node 4 (high corner, } z_4 = 9/14 \approx 0.643\text{ m)} \\
\leftarrow \text{Node 5 (exact saddle midpoint } z_5 = 0.500\text{ m)}
\end{matrix},
\qquad
\nabla \Phi(\mathbf X_0) = 2 C^T Q \mathbf U_0 = \mathbf 0_{5\times 3}
$$

**Add to your program:**

```python
xyz0, l0, s0, _ = form_finding(
    branches, n, xyz_fixed, q, np.zeros((n, 3))
)
uvw0 = C @ xyz0 + C_f @ xyz_fixed
gradient = 2 * C.T @ np.diag(q) @ uvw0             # Theorem 1: dPhi/dX == 0
max_grad_unloaded = np.abs(gradient).max()
q_const = 1.0 / l0                                 # Theorem 2: q = 1 / l
s_uniform = l0 * q_const                           # all forces equal 1.0 kN
print("Theorem 1 max |dPhi/dX|:", f"{max_grad_unloaded:.2e}")
print("Theorem 2 uniform forces s (kN):", s_uniform)
```

**Example output:**

```text
Theorem 1 max |dPhi/dX|: 2.22e-15
Theorem 2 uniform forces s (kN): [1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1.]
```

---

## Part F. Asking for lengths and forces

### F.1 Target length and force constraints, equation (11)

To enforce target equilibrium branch lengths $\mathbf l_v$ or forces $\mathbf s_v$, we form the residual vector $\mathbf g^{\ast}(\mathbf q)$ and solve for $\mathbf q^{\ast} \gt \mathbf 0$ such that $\mathbf g^{\ast}(\mathbf q^{\ast}) = \mathbf 0$.

### General Equation (Eq. 11)

$$
\mathbf g^{\ast}(\mathbf q) = \begin{bmatrix}
\mathbf l_{\text{constrained}}(\mathbf q) - \mathbf l_v \\
\mathbf s_{\text{constrained}}(\mathbf q) - \mathbf s_v
\end{bmatrix} = \mathbf 0
$$

### Matrix Example (Target Anchor Length $l_{1..4} = 1.200$ m)

* **$\mathbf l_{1..4}(\mathbf q)$ (4×1):** Current equilibrium lengths of the 4 anchor cables $b_1 \dots b_4$ (m).
* **$\mathbf l_v$ (4×1):** Prescribed target lengths for those 4 anchor cables (1.200 m).
* **$\mathbf g^{\ast}(\mathbf q) = \mathbf l_{1..4}(\mathbf q) - \mathbf l_v$ (4×1):** Length constraint residual vector (m; zero when targets are met).

$$
\mathbf g^{\ast}(\mathbf q) =
\underset{\mathbf l_{1..4}(\mathbf q)}{\begin{bmatrix}
1.201 \\
1.374 \\
1.201 \\
1.374
\end{bmatrix}} -
\underset{\mathbf l_v}{\begin{bmatrix}
1.200 \\
1.200 \\
1.200 \\
1.200
\end{bmatrix}} =
\begin{bmatrix}
+0.001 \\
+0.174 \\
+0.001 \\
+0.174
\end{bmatrix}\text{ m}
\begin{matrix}
\leftarrow \text{Branch 1 (}+1\text{ mm error)} \\
\leftarrow \text{Branch 2 (lifted anchor: }+17.4\text{ cm too long)} \\
\leftarrow \text{Branch 3 (}+1\text{ mm error)} \\
\leftarrow \text{Branch 4 (lifted anchor: }+17.4\text{ cm too long)}
\end{matrix}
$$

**Add to your program:**

```python
length_rows = [0, 1, 2, 3]                    # the four anchor branches
target_lengths = np.full(4, 1.2)              # target length 1.2 m on each
g_lengths = l[length_rows] - target_lengths   # constraint residual vector
print("Initial anchor lengths (m):", l[length_rows])
print("Length residual g*(q) (m): ", g_lengths)
```

**Example output:**

```text
Initial anchor lengths (m): [1.201 1.374 1.201 1.374]
Length residual g*(q) (m):  [0.001 0.174 0.001 0.174]
```

### F.2 Iterative solver for prescribed lengths and forces (sections 3.1 to 3.6)

At each iteration, we run `form_finding(q)` and update $\mathbf q \gt \mathbf 0$ via least squares until the constraint residual $\mathbf g^{\ast}(\mathbf q^{\ast})$ vanishes.

### Iteration Loop

$$
\mathbf q^{(k)} \xrightarrow{D(\mathbf q^{(k)})\mathbf X = \mathbf B} \mathbf l(\mathbf q^{(k)}),\ \mathbf s(\mathbf q^{(k)}) \xrightarrow{\text{residual}} \mathbf g^{\ast}(\mathbf q^{(k)}) \xrightarrow{\Delta\mathbf q} \mathbf q^{(k+1)}
$$

### Matrix Example (Before vs. After on Anchor Cables 1–4)

* **$\mathbf q_{1..4}^{(0)}$ and $\mathbf l_{1..4}^{(0)}$ (4×1):** Initial force densities (kN/m) and resulting initial lengths (m) of anchor cables $1 \dots 4$.
* **$\mathbf q_{1..4}^{\ast}$ and $\mathbf l_{1..4}^{\ast}$ (4×1):** Optimized force densities (kN/m) and achieved target lengths (1.200 m) after least-squares convergence.

$$
\text{Initial:}\quad
\mathbf q_{1..4}^{(0)} =
\begin{bmatrix}
2.000 \\
2.000 \\
2.000 \\
2.000
\end{bmatrix}\text{ kN/m},
\quad
\mathbf l_{1..4}^{(0)} =
\begin{bmatrix}
1.201 \\
1.374 \\
1.201 \\
1.374
\end{bmatrix}\text{ m}
\qquad \longrightarrow \qquad
\text{Solved:}\quad
\mathbf q_{1..4}^{\ast} =
\begin{bmatrix}
1.972 \\
2.412 \\
1.972 \\
2.412
\end{bmatrix}\text{ kN/m},
\quad
\mathbf l_{1..4}^{\ast} =
\begin{bmatrix}
1.200 \\
1.200 \\
1.200 \\
1.200
\end{bmatrix}\text{ m}
$$

**Add to your program:**

```python
from scipy.optimize import least_squares


def fit_force_densities(
    branches, n_free, xyz_fixed, q_start, p,
    length_rows=(), l_v=(), force_rows=(), s_v=(),
):
    """Find q > 0 whose equilibrium shape matches target l_v and s_v."""
    length_rows, force_rows = list(length_rows), list(force_rows)
    l_v, s_v = np.asarray(l_v, float), np.asarray(s_v, float)

    def residual(q_trial):
        _, l_cur, s_cur, _ = form_finding(
            branches, n_free, xyz_fixed, q_trial, p
        )
        return np.r_[l_cur[length_rows] - l_v, s_cur[force_rows] - s_v]

    found = least_squares(residual, q_start, bounds=(1e-9, np.inf))
    xyz_opt, l_opt, s_opt, _ = form_finding(
        branches, n_free, xyz_fixed, found.x, p
    )
    max_err = np.abs(found.fun).max()
    return found.x, xyz_opt, l_opt, s_opt, found.nfev, max_err


q_c, xyz_c, l_c, s_c, tries_c, err_c = fit_force_densities(
    branches, n, xyz_fixed, q, p,
    length_rows=[0, 1, 2, 3], l_v=[1.2] * 4,
)

q_m, xyz_m, l_m, s_m, tries_m, err_m = fit_force_densities(
    branches, n, xyz_fixed, q, p,
    length_rows=[8, 9, 10, 11], l_v=[0.9] * 4,
    force_rows=[0, 1, 2, 3], s_v=[2.0] * 4,
)
print(f"Optimized q*_[1..4]: {q_c[:4]} -> lengths l*_[1..4]: {l_c[:4]} (err={err_c:.1e})")
print(f"Mixed target spokes l*_[9..12]: {l_m[8:]} m, anchor forces s*_[1..4]: {s_m[:4]} kN (err={err_m:.1e})")
```

**Example output:**

```text
Optimized q*_[1..4]: [1.972 2.412 1.972 2.412] -> lengths l*_[1..4]: [1.2 1.2 1.2 1.2] (err=1.8e-08)
Mixed target spokes l*_[9..12]: [0.9 0.9 0.9 0.9] m, anchor forces s*_[1..4]: [2. 2. 2. 2.] kN (err=7.5e-11)
```

### F.3 Sensitivity Jacobian $G^T = \partial \mathbf g^{\ast} / \partial \mathbf q$ (sections 3.2 to 3.5)

Differentiating $C^T Q \mathbf u(\mathbf q) = \mathbf p_x$ with respect to $\mathbf q$ gives the node sensitivity $\partial \mathbf x / \partial \mathbf q = -D^{-1} C^T U$ and the constraint Jacobian $G^T = \partial \mathbf g^{\ast} / \partial \mathbf q$.

### General Equations (Eqs. 28 & 31)

$$
\frac{\partial \mathbf x}{\partial \mathbf q} = -D^{-1} C^T U, \qquad
\frac{\partial \mathbf y}{\partial \mathbf q} = -D^{-1} C^T V, \qquad
\frac{\partial \mathbf z}{\partial \mathbf q} = -D^{-1} C^T W, \qquad
G^T = \frac{\partial \mathbf g^{\ast}}{\partial \mathbf q}
$$

### Matrix Example (Anchor Length Jacobian $G^T_{1..4,\ 1..4}$ and Height Sensitivity $\partial \mathbf z / \partial \mathbf q_{1..4}$)

* **$G^T_{1..4,\ 1..4} = \partial \mathbf l_{1..4} / \partial \mathbf q_{1..4}$ (4×4):** Sensitivity Jacobian entry $(r, j)$ giving how much anchor cable length $l_r$ (m) changes per unit change in force density $q_j$ (kN/m).
* **$\partial \mathbf z / \partial \mathbf q_{1..4} = -D^{-1} C^T W_{:, 1..4}$ (5×4):** Node height sensitivity entry $(i, j)$ giving how much free node height $z_i$ (m) changes per unit change in anchor force density $q_j$ (kN/m).

$$
G^T_{1..4,\ 1..4} =
\begin{bmatrix}
-0.313 & 0.002 & 0.073 & 0.002 \\
0.002 & -0.358 & 0.002 & 0.044 \\
0.073 & 0.002 & -0.313 & 0.002 \\
0.002 & 0.044 & 0.002 & -0.358
\end{bmatrix}
\begin{matrix}
\leftarrow \partial l_1 / \partial q_{1..4}\ (\text{tightening } q_1\text{ shortens } l_1) \\
\leftarrow \partial l_2 / \partial q_{1..4}\ (\text{tightening } q_2\text{ shortens } l_2) \\
\leftarrow \partial l_3 / \partial q_{1..4}\ (\text{tightening } q_3\text{ shortens } l_3) \\
\leftarrow \partial l_4 / \partial q_{1..4}\ (\text{tightening } q_4\text{ shortens } l_4)
\end{matrix}
$$

$$
\frac{\partial \mathbf z}{\partial \mathbf q_{1..4}} = -D^{-1} C^T W_{:, 1..4} =
\begin{bmatrix}
-0.012 & 0.060 & -0.003 & 0.060 \\
-0.004 & 0.175 & -0.004 & 0.041 \\
-0.003 & 0.060 & -0.012 & 0.060 \\
-0.004 & 0.041 & -0.004 & 0.175 \\
-0.006 & 0.084 & -0.006 & 0.084
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Node 1} \\
\leftarrow \text{Node 2 (rises }+0.175\text{ m per kN/m of } q_2\text{)} \\
\leftarrow \text{Node 3} \\
\leftarrow \text{Node 4 (rises }+0.175\text{ m per kN/m of } q_4\text{)} \\
\leftarrow \text{Node 5 (center rises }+0.084\text{ m per kN/m of } q_2, q_4\text{)}
\end{matrix}
$$

**Add to your program:**

```python
def sensitivity(q_vec, rows, step=1e-6):
    """Finite-difference Jacobian d(l[rows]) / dq of shape (r, m)."""
    base = form_finding(branches, n, xyz_fixed, q_vec, p)[1][rows]
    G_t = np.zeros((len(rows), len(q_vec)))
    for j in range(len(q_vec)):
        q_nudged = q_vec.copy()
        q_nudged[j] += step
        l_nudged = form_finding(branches, n, xyz_fixed, q_nudged, p)[1][rows]
        G_t[:, j] = (l_nudged - base) / step
    return G_t


G_t = sensitivity(q, [0, 1, 2, 3])               # (4, 12) finite-difference Jacobian d(l_1..4)/dq
print("Jacobian block G_t[:, :4] (4x4):\n", G_t[:, :4])
```

**Example output:**

```text
Jacobian block G_t[:, :4] (4x4):
 [[-0.313  0.002  0.073  0.002]
 [ 0.002 -0.358  0.002  0.044]
 [ 0.073  0.002 -0.313  0.002]
 [ 0.002  0.044  0.002 -0.358]]
```

---

## Part G. The paper's examples, recomputed

### G.1 Larger network: the 67-node, 110-branch pointed tent (section 5, figure 5)

Apply the exact same `form_finding` function without modification to Schek's larger pointed-tent network ($n = 61$ free nodes, $n_f = 6$ fixed supports including high apex node 67, $m = 110$ branches).

![Fig. 5](images/schek_fig5.png)

### Problem Dimensions & Prescribed Force Densities

| Matrix / Vector | Fig. 2 Net (Parts A–F) | Fig. 5 Tent (Part G) |
|---|---|---|
| Connectivity $C_s = [C \mid C_f]$ | $(12 \times 5)\ \big\|\ (12 \times 4)$ | $(110 \times 61)\ \big\|\ (110 \times 6)$ |
| Diagonal Force Density $Q$ | (12×12) | (110×110) |
| Free System Matrix $D = C^T Q C$ | (5×5) | (61×61) |

$$
q_j = \begin{cases}
100.0 & \text{29 border cables (stiff edge)} \\
0.5 & \text{10 radial apex cables (long)} \\
1.0 & \text{71 interior field cables}
\end{cases}
$$

**Add to your program:**

```python
FIG5_PX = {   # plan positions read off the printed figure (pixels, y down)
    1: (162, 368), 2: (150, 591), 3: (182, 345), 4: (165, 618),
    5: (247, 230), 6: (190, 666), 7: (217, 611), 8: (315, 405),
    9: (360, 305), 10: (265, 198), 11: (430, 95), 12: (452, 105),
    13: (537, 132), 14: (445, 368), 15: (413, 448), 16: (357, 593),
    17: (250, 773), 18: (412, 703), 19: (282, 836), 20: (445, 951),
    21: (527, 921), 22: (567, 909), 23: (595, 801), 24: (472, 678),
    25: (455, 581), 26: (480, 477), 27: (519, 420), 28: (662, 172),
    29: (664, 346), 30: (665, 445), 31: (639, 451), 32: (599, 476),
    33: (588, 492), 34: (571, 515), 35: (562, 536), 36: (559, 568),
    37: (561, 596), 38: (573, 632), 39: (592, 661), 40: (624, 683),
    41: (652, 696), 42: (694, 703), 43: (732, 821), 44: (737, 851),
    45: (837, 230), 46: (787, 365), 47: (719, 448), 48: (749, 463),
    49: (793, 506), 50: (807, 546), 51: (809, 596), 52: (804, 628),
    53: (752, 686), 54: (864, 239), 55: (964, 385), 56: (919, 526),
    57: (977, 514), 58: (919, 643), 59: (989, 653), 60: (992, 676),
    61: (857, 811), 62: (97, 494), 63: (362, 981), 64: (999, 763),
    65: (954, 270), 66: (340, 68), 67: (685, 571),
}
BORDER = [
    62, 2, 4, 6, 17, 19, 63, 20, 21, 22, 44, 61, 64, 60, 59,
    57, 55, 65, 54, 45, 28, 13, 12, 11, 66, 10, 5, 3, 1,
]
INNER_RING = [
    31, 30, 47, 48, 49, 50, 51, 52, 53, 42,
    41, 40, 39, 38, 37, 36, 35, 34, 33, 32,
]
MIDDLE_RING = [27, 29, 46, 56, 58, 43, 23, 24, 25, 26]
SPOKES = [31, 33, 35, 37, 39, 41, 53, 51, 49, 47]
OTHER = [
    (30, 29), (32, 27), (34, 26), (36, 25), (38, 24), (40, 23),
    (42, 43), (52, 58), (50, 56), (48, 46), (27, 14), (29, 28),
    (46, 45), (56, 57), (58, 59), (43, 44), (23, 22), (24, 18),
    (25, 16), (26, 15), (1, 2), (4, 7), (6, 7), (7, 8), (3, 8),
    (8, 9), (5, 9), (9, 12), (9, 14), (13, 14), (10, 11), (8, 15),
    (14, 15), (15, 16), (7, 16), (16, 18), (17, 18), (18, 21),
    (19, 20), (61, 60), (59, 58), (57, 56), (46, 45), (28, 29),
    (54, 55),
]
ring = lambda nodes: [
    (nodes[i], nodes[(i + 1) % len(nodes)]) for i in range(len(nodes))
]
seen, branches5 = set(), []
all_edges5 = (
    ring(BORDER) + ring(INNER_RING) + ring(MIDDLE_RING)
    + [(k, 67) for k in SPOKES] + OTHER
)
for e in all_edges5:
    if tuple(sorted(e)) not in seen:
        seen.add(tuple(sorted(e)))
        branches5.append(e)
border5 = {tuple(sorted(e)) for e in ring(BORDER)}
xy = np.array([FIG5_PX[k] for k in range(1, 68)], dtype=float)
xy = xy * np.array([0.04, -0.04])
xy -= xy[66]                                  # apex at the plan origin
free5, fixed5 = 61, [62, 63, 64, 65, 66, 67]  # 61 free nodes (1..61), 6 fixed anchors (62..67)
q5 = np.array([
    100.0 if tuple(sorted(e)) in border5 else 0.5 if 67 in e else 1.0
    for e in branches5
])                                            # (110,) force densities: 100 border, 0.5 spoke, 1.0 field
p5 = np.zeros((free5, 3))
p5[:, 2] = -0.4                               # -0.4 kN vertical load at each free node
is_spoke = np.array([67 in e for e in branches5])
is_border = np.array([tuple(sorted(e)) in border5 for e in branches5])
touches_border = np.array([any(k in BORDER for k in e) for e in branches5])


def anchors5(apex_dx=0.0, apex_dy=0.0, apex_h=16.0):
    A = np.c_[xy[61:67], np.zeros(6)]
    A[5] += [apex_dx, apex_dy, apex_h]        # node 67 lifted to apex_h = 16 m
    return A


shapes = {}


def keep(name, brs, xyz_free_nodes, xyz_fixed_nodes, fixed_nodes):
    shapes[name] = {
        "branches": [list(e) for e in brs],
        "xyz": np.vstack([xyz_free_nodes, xyz_fixed_nodes]).tolist(),
        "fixed": list(fixed_nodes),
    }


print(f"Fig. 5 tent: {free5} free nodes, {len(fixed5)} fixed supports, {len(branches5)} branches")
print(f"Branch counts: {int(is_border.sum())} border, {int(is_spoke.sum())} radial spokes, {int((~is_border & ~is_spoke).sum())} interior")
```

**Example output:**

```text
Fig. 5 tent: 61 free nodes, 6 fixed supports, 110 branches
Branch counts: 29 border, 10 radial spokes, 71 interior
```

### G.2 Figure 6: shifting fixed support coordinates

Translate the high apex support (node 67) horizontally in plan by $(\Delta x, \Delta y) = (0, 0),\ (6, 2),\ (12, 4)$ m. Because $\mathbf q$ is unchanged, $D\ (61 \times 61)$ is invariant and only the right-hand side $\mathbf P - D_f \mathbf X_f$ updates.

![Fig. 1](images/schek_fig1.png)

![Fig. 6](images/schek_fig6_persp.png)
![Fig. 6, plan](images/schek_fig6_plan.png)

### Apex Shift Summary

| Run | Apex Shift $(\Delta x, \Delta y)$ | Radial Length Range | Vertical Apex Reaction $R_{67, z}$ |
|---|---|---|---|
| `fig6_1` | $(0, 0)$ m | 8.1 to 9.0 m | 38.9 kN |
| `fig6_2` | $(6, 2)$ m | 8.0 to 9.3 m | 38.9 kN |
| `fig6_3` | $(12, 4)$ m | 8.4 to 10.9 m | 38.9 kN |

**Add to your program:**

```python
fig6_shifts = [("fig6_1", (0, 0)), ("fig6_2", (6, 2)), ("fig6_3", (12, 4))]
for name, (dx, dy) in fig6_shifts:
    # Shifting the apex horizontally only updates the x, y RHS; D and the z-system stay unchanged
    xyz_6, l_6, s_6, R_6 = form_finding(
        branches5, free5, anchors5(dx, dy), q5, p5
    )
    keep(name, branches5, xyz_6, anchors5(dx, dy), fixed5)
    print(f"{name}: radial l in [{l_6[is_spoke].min():.1f}, {l_6[is_spoke].max():.1f}] m, apex R_z = {R_6[5, 2]:.1f} kN")

xyz_fig1, *_ = form_finding(branches5, free5, anchors5(), q5, p5)
keep("fig1", branches5, xyz_fig1, anchors5(), fixed5)
```

**Example output:**

```text
fig6_1: radial l in [8.1, 9.0] m, apex R_z = 38.9 kN
fig6_2: radial l in [8.0, 9.3] m, apex R_z = 38.9 kN
fig6_3: radial l in [8.4, 10.9] m, apex R_z = 38.9 kN
```

### G.3 Figures 7 and 8: varying radial and border force densities

Vary the radial force density $q_{\text{spoke}} \in \{1.0, 0.7, 0.3\}$ (Fig. 7) and border force density $q_{\text{border}} \in \{10, 5, 1\}$ (Fig. 8), rebuilding $D = C^T Q C$ each time.

![Fig. 7](images/schek_fig7_persp.png)
![Fig. 7, plan](images/schek_fig7_plan.png)

![Fig. 8](images/schek_fig8_persp.png)
![Fig. 8, plan](images/schek_fig8_plan.png)

### Parameter Study Results

| Fig. 7 Run | $q_{\text{spoke}}$ | Radial Lengths | Fig. 8 Run | $q_{\text{border}}$ | Border Lengths |
|---|---|---|---|---|---|
| `fig7_1` | $1.0$ | 5.0 to 5.9 m | `fig8_1` | $10.0$ | 3.4 to 4.8 m |
| `fig7_2` | $0.7$ | 6.5 to 7.4 m | `fig8_2` | $5.0$ | 3.5 to 4.9 m |
| `fig7_3` | $0.3$ | 10.6 to 11.6 m | `fig8_3` | $1.0$ | 2.9 to 6.5 m |

**Add to your program:**

```python
for name, qs in zip(["fig7_1", "fig7_2", "fig7_3"], [1.0, 0.7, 0.3]):
    q_spoke_run = np.where(is_spoke, qs, q5)  # replace q on the 10 radial spokes
    xyz_7, l_7, *_ = form_finding(
        branches5, free5, anchors5(), q_spoke_run, p5
    )
    keep(name, branches5, xyz_7, anchors5(), fixed5)
    print(f"{name} (q_spoke={qs}): radial l in [{l_7[is_spoke].min():.1f}, {l_7[is_spoke].max():.1f}] m")

for name, qb in zip(["fig8_1", "fig8_2", "fig8_3"], [10.0, 5.0, 1.0]):
    q_border_run = np.where(is_border, qb, q5)  # replace q on the 29 border cables
    xyz_8, l_8, *_ = form_finding(
        branches5, free5, anchors5(), q_border_run, p5
    )
    keep(name, branches5, xyz_8, anchors5(), fixed5)
    print(f"{name} (q_border={qb}): border l in [{l_8[is_border].min():.1f}, {l_8[is_border].max():.1f}] m")
```

**Example output:**

```text
fig7_1 (q_spoke=1.0): radial l in [5.0, 5.9] m
fig7_2 (q_spoke=0.7): radial l in [6.5, 7.4] m
fig7_3 (q_spoke=0.3): radial l in [10.6, 11.6] m
fig8_1 (q_border=10.0): border l in [3.4, 4.8] m
fig8_2 (q_border=5.0): border l in [3.5, 4.9] m
fig8_3 (q_border=1.0): border l in [2.9, 6.5] m
```

### G.4 Figure 9: prescribed length constraints on 62 interior branches

Constrain all $r = 62$ interior branches not touching the boundary ($10$ radial cables set to $l_{\text{radial}}$, $52$ ring/field cables scaled by `ring_factor`) across $m = 110$ force densities.

![Fig. 9](images/schek_fig9_persp.png)
![Fig. 9, plan](images/schek_fig9_plan.png)

### Constrained Runs (62 Equations in 110 Unknowns)

| Run | Target $l_{\text{radial}}$ | Ring Scale Factor | Evaluations | $\max \|\mathbf g^{\ast}(\mathbf q)\|$ |
|---|---|---|---|---|
| `fig9_1` | 6.0 m | $1.25 \times \mathbf l_{\text{base}}$ | $35$ | $3.8 \times 10^{-9}$ m |
| `fig9_2` | 6.0 m | $0.85 \times \mathbf l_{\text{base}}$ | $38$ | $6.3 \times 10^{-12}$ m |
| `fig9_3` | 4.5 m | $0.70 \times \mathbf l_{\text{base}}$ | $47$ | $9.1 \times 10^{-10}$ m |

**Add to your program:**

```python
base_l = form_finding(branches5, free5, anchors5(), q5, p5)[1]
inner = [j for j in range(len(branches5)) if not touches_border[j]]  # 62 interior branches
fig9_runs = [
    ("fig9_1", (6.0, 1.25)),
    ("fig9_2", (6.0, 0.85)),
    ("fig9_3", (4.5, 0.70)),
]
for name, (l_radial, ring_factor) in fig9_runs:
    l_v = [
        l_radial if is_spoke[j] else base_l[j] * ring_factor
        for j in inner
    ]
    q_k, xyz_9, l_9, s_9, tries_9, err_9 = fit_force_densities(
        branches5, free5, anchors5(), q5, p5,
        length_rows=inner, l_v=l_v,
    )
    keep(name, branches5, xyz_9, anchors5(), fixed5)
    print(f"{name}: {tries_9} evals, max length residual = {err_9:.2e} m")
```

**Example output:**

```text
fig9_1: 42 evals, max length residual = 1.19e-09 m
fig9_2: 35 evals, max length residual = 1.07e-09 m
fig9_3: 58 evals, max length residual = 7.49e-10 m
```

### G.5 Figure 10: 8x8 grid-shell of 112 bars

Generate an $8 \times 8$ orthogonal grid ($n = 60$ free nodes, $n_f = 4$ corner supports, $m = 112$ bars) and solve three benchmark problems: (10.1) hanging net of 112 equal-length 1.0 m bars under self-weight, (10.2) prestressed saddle with raised corners, and (10.3) mixed equal-length and equal-force constraints.

![Fig. 10](images/schek_fig10_persp.png)
![Fig. 10, plan](images/schek_fig10_plan.png)

### Summary of the Three 112-Bar Cases

| Case | Corner Supports | Load $\mathbf P$ | Constraints | Result |
|---|---|---|---|---|
| `fig10_1` | 4 corners at 80% span | bar weight | $l_j = 1.0\text{ m}\ (\forall j=1..112)$ | $\|\mathbf e_l\| \le 7.6\times 10^{-10}\text{ m},\ s \in [0.12, 2.77]$ kN |
| `fig10_2` | 2 corners lifted to 3 m | $\mathbf 0$ | linear ($q_{\text{border}}=10, q_{\text{in}}=1$) | $l_{\text{in}} \in [0.65, 0.81]$ m |
| `fig10_3` | 2 corners lifted to 3 m | $\mathbf 0$ | equal inner $l$ + equal link $s$ | $\|\mathbf g^{\ast}\| \le 1.6\times 10^{-8}$ |

**Add to your program:**

```python
g = 8
gid = {(i, k): i * g + k + 1 for i in range(g) for k in range(g)}
grid_h = [(gid[i, k], gid[i, k + 1]) for i in range(g) for k in range(g - 1)]
grid_v = [(gid[i, k], gid[i + 1, k]) for i in range(g - 1) for k in range(g)]
grid = grid_h + grid_v
corners = [gid[0, 0], gid[0, g - 1], gid[g - 1, g - 1], gid[g - 1, 0]]
# Renumber the 8x8 grid so the 60 free nodes come first (1..60) and the 4 corners come last (61..64)
order = [
    v for v in range(1, g * g + 1) if v not in corners
] + corners
renum = {old: new + 1 for new, old in enumerate(order)}
grid = [(renum[a_], renum[b_]) for a_, b_ in grid]
flat = np.array(
    [[(v - 1) % g, (v - 1) // g, 0.0] for v in order], dtype=float
)
on_edge = lambda v: (
    (order[v - 1] - 1) // g in (0, g - 1),
    (order[v - 1] - 1) % g in (0, g - 1),
)
grid_border = np.array([
    (on_edge(a_)[0] and on_edge(b_)[0])
    or (on_edge(a_)[1] and on_edge(b_)[1])
    for a_, b_ in grid
])
grid_touch = np.array([
    any(on_edge(v)[0] or on_edge(v)[1] for v in e) for e in grid
])
weight = 0.15                                       # kN per bar
degree = np.bincount(np.array(grid).ravel())[1:]    # number of bars meeting at each node
p10 = np.zeros((g * g - 4, 3))
p10[:, 2] = -0.5 * weight * degree[: g * g - 4]     # lump half of each bar's weight onto its two endpoints
anchors10 = flat[-4:].copy()
anchors10[:, :2] = (anchors10[:, :2] - 3.5) * 0.8 + 3.5

# Case 10.1: 112 equal-length 1.0 m bars under self-weight
q_10_1, xyz_10_1, l_10_1, s_10_1, tries_10_1, err_10_1 = (
    fit_force_densities(
        grid, g * g - 4, anchors10, np.ones(112), p10,
        length_rows=range(112), l_v=[1.0] * 112,
    )
)
keep("fig10_1", grid, xyz_10_1, anchors10, [renum[c] for c in corners])

# Case 10.2: two corners lifted to 3 m, linear solve
anchors10b = anchors10.copy()
anchors10b[[0, 2], 2] = 3.0
q10 = np.where(grid_border, 10.0, 1.0)
xyz_10_2, l_10_2, s_10_2, R_10_2 = form_finding(
    grid, g * g - 4, anchors10b, q10, np.zeros_like(p10)
)
keep("fig10_2", grid, xyz_10_2, anchors10b, [renum[c] for c in corners])

# Case 10.3: equal inner lengths and equal link forces near border
inner10 = [
    j for j in range(112) if not grid_border[j] and not grid_touch[j]
]
link10 = [
    j for j in range(112) if not grid_border[j] and grid_touch[j]
]
q_10_3, xyz_10_3, l_10_3, s_10_3, tries_10_3, err_10_3 = (
    fit_force_densities(
        grid, g * g - 4, anchors10b, q10, np.zeros_like(p10),
        length_rows=inner10, l_v=[l_10_2[inner10].mean()] * len(inner10),
        force_rows=link10, s_v=[s_10_2[link10].mean()] * len(link10),
    )
)
keep("fig10_3", grid, xyz_10_3, anchors10b, [renum[c] for c in corners])
print(f"fig10_1: err={err_10_1:.2e} m, forces in [{s_10_1.min():.2f}, {s_10_1.max():.2f}] kN")
print(f"fig10_2: inner lengths in [{l_10_2[inner10].min():.2f}, {l_10_2[inner10].max():.2f}] m")
print(f"fig10_3: err={err_10_3:.2e}, uniform inner l={l_10_3[inner10].mean():.3f} m, link s={s_10_3[link10].mean():.3f} kN")
```

**Example output:**

```text
fig10_1: err=7.48e-10 m, forces in [0.12, 2.77] kN
fig10_2: inner lengths in [0.69, 0.81] m
fig10_3: err=1.33e-08, uniform inner l=0.752 m, link s=0.708 kN
```

### G.6 Export computed shapes for figure generation

Write all computed 3D shapes (`fig1`, `fig5_plan`, `fig6_1`..`fig10_3`) to `shapes.json` so `schek_1974_figures.py` can plot them.

**Add to your program:**

```python
import json
from pathlib import Path

keep(
    "fig5_plan",
    branches5,
    np.c_[xy[:61], np.zeros(61)],
    np.c_[xy[61:], np.zeros(6)],
    fixed5,
)
base_dir = (
    Path(__file__).resolve().parent if "__file__" in dir() else Path(".")
)
out = base_dir / "viewer_scenes/json/shapes.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(shapes))                 # serialize all form-found 3D geometries to JSON
print(f"Saved {len(shapes)} shapes ({list(shapes.keys())}) to {out.name}")
```

**Example output:**

```text
Saved 17 shapes (['fig6_1', 'fig6_2', 'fig6_3', 'fig1', 'fig7_1', 'fig7_2', 'fig7_3', 'fig8_1', 'fig8_2', 'fig8_3', 'fig9_1', 'fig9_2', 'fig9_3', 'fig10_1', 'fig10_2', 'fig10_3', 'fig5_plan']) to shapes.json
```

<!-- schek-app:end -->

## Implementation in compas_fd 0.5.4

Compared with the application above: `fd_numpy` performs the same linear solve as the
`form_finding` function in D.1, using sparse matrices (figure 3's loop, one call per shape). The
constrained loop of section 3, prescribed lengths or forces by iterating on $q$, is
**not** in `compas_fd`; its `fd_constrained_numpy` instead moves anchors on geometric
constraints between linear solves. The iterative solver in [compas_dr](compas_dr.md)
reaches prescribed forces and lengths through its `fpre` / `lpre` terms.


### Linear solver (on the 9-node, 12-branch net)

```python
from compas_fd.solvers import fd_numpy

# Exact same 9-node, 12-branch network (nodes 0..4 free, nodes 5..8 fixed anchors)
vertices = [
    [-1.0,  0.0, 0.0], [ 0.0,  1.0, 0.0], [ 1.0,  0.0, 0.0], [ 0.0, -1.0, 0.0], [0.0, 0.0, 0.0],
    [-2.0,  0.0, 0.0], [ 0.0,  2.0, 1.0], [ 2.0,  0.0, 0.0], [ 0.0, -2.0, 1.0],
]
fixed = [5, 6, 7, 8]
edges = [(i - 1, k - 1) for i, k in branches]
q = [2.0, 2.0, 2.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
loads = [[0.0, 0.0, -0.5]] * 5 + [[0.0, 0.0, 0.0]] * 4

result = fd_numpy(
    vertices=vertices,    # (9, 3) all node coordinates (5 free + 4 fixed)
    fixed=fixed,          # [5, 6, 7, 8] indices of the 4 fixed anchors
    edges=edges,          # 12 (i, k) index pairs; i -> +1, k -> -1 in C_s
    forcedensities=q,     # 12 branch force densities (kN/m)
    loads=loads,          # (9, 3) nodal loads (kN)
)
result.vertices           # (9, 3) equilibrium coordinates matching D.1
result.residuals          # (9, 3) 0 at free nodes 0..4; support reactions at 5..8
result.forces             # (12, 1) s = q * l
result.lengths            # (12, 1) equilibrium cable lengths l
```

Internally (`solvers/fd_numerical_data.py`, `solvers/fd_numpy.py`):

| symbol in Schek (9-node net) | name in code | construction |
|---|---|---|
| $C_s\ (12 \times 9)$ | `C` | `connectivity_matrix(edges, "csr")` |
| $C\ (12 \times 5)$ (free columns) | `Ci` | `C[:, free]` |
| $C_f\ (12 \times 4)$ (fixed columns) | `Cf` | `C[:, fixed]` |
| $Q\ (12 \times 12)$ | `Q` | `diags([q.flatten()], [0])` |
| $D\ (5 \times 5)$ | `Ai` | `Ci.T @ Q @ Ci` |
| $D_f\ (5 \times 4)$ | `Af` | `Ci.T @ Q @ Cf` |
| full $C_s^t Q C_s\ (9 \times 9)$ | `A` | `C.T @ Q @ C` (used only for residuals) |
| right-hand side of (8) (5×3) | `b` | `p[free] - Af @ xyz[fixed]` |
| (9) (5×3) | — | `xyz[free] = spsolve(Ai, b)` |
| $\mathbf l\ (12 \times 1)$ | `lengths` | `normrow(C @ xyz)` |
| (10) $\mathbf s\ (12 \times 1)$ | `forces` | `q * lengths` |
| residual (9×3) | `residuals` | `p - A @ xyz` |

The compas-FoFin GitBook shows the same lines verbatim as the "matrix formulation".
Node ordering is free: the code selects columns by index, so fixed nodes need not
be last as Schek advises. Vertex and edge ordering of the outputs equals the input
ordering. `Result` is a `NamedTuple`; `vertices` is a new array built from the input
list, not the input list itself.

### Constrained solver (sliding Anchor 7 of the 9-node net)

```python
from compas.geometry import Line
from compas_fd.constraints import Constraint
from compas_fd.solvers import fd_constrained_numpy

constraints = [None] * 9
# allow fixed anchor 7 (0-based index 6) to slide along a horizontal line at z = 1 m
constraints[6] = Constraint(Line([-1.0, 2.0, 1.0], [1.0, 2.0, 1.0]))

result = fd_constrained_numpy(
    vertices=vertices,
    fixed=fixed,
    edges=edges,
    forcedensities=q,
    loads=loads,
    constraints=constraints,  # aligned with the 9 vertices; None = unconstrained
    kmax=100,
    tol_res=1e-3,
    tol_disp=1e-3,
    damping=0.1,
    selfweight=None,          # optional callable xyz -> (9, 1) weights
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
  `diags`/`dot`, and a free node not connected to any fixed node by a path of positive $q$
  makes `Ai` singular (`spsolve` warns and returns `nan`/`inf`).
- `requirements.txt` lists only `compas`; `numpy` and `scipy` arrive through
  `compas`. Tested here with compas 2.15.1, numpy 2.4.6, scipy 1.17.1.

## Verification on the 9-node, 12-branch network

Running `compas_fd` 0.5.4 (`fd_numpy`) on our **9-node, 12-branch saddle cable net** (sections A.1–D.1) reproduces our NumPy derivation to machine precision:

| Quantity (9-node, 12-branch net) | Value from `fd_numpy` & `schek_app.py` |
|---|---|
| Free nodes 1, 3 (`vertices[0]`, `vertices[2]`) | $(\mp 0.800,\ 0.000,\ 0.045)$ m; difference $\lt  10^{-15}$ m |
| Free nodes 2, 4 (`vertices[1]`, `vertices[3]`) | $(0.000,\ \pm 0.800,\ 0.330)$ m; difference $\lt  10^{-15}$ m |
| Center free node 5 (`vertices[4]`) | $(0.000,\ 0.000,\ 0.063)$ m; difference $\lt  10^{-15}$ m |
| Residuals at free nodes 1–5 | $(0,\ 0,\ 0)$ kN ($\lt  10^{-15}$ kN) |
| Anchor lengths $l_{1,3}$ / $l_{2,4}$ | 1.201 m / 1.374 m |
| Anchor forces $s_{1,3}$ / $s_{2,4}$ | 2.402 kN / 2.749 kN ($= q_j l_j$) |
| Support reactions $\sum_{i=6}^9 R_{i,z}$ | $-0.089 + 1.339 - 0.089 + 1.339 = +2.500$ kN — balances $5 \times (-0.5)$ kN |

**Structure of D (Schek figure 4).** Building $C_s$ for the 9-node, 12-branch graph
of figure 2 and setting $q_j = j$ gives
$D _ {11} = q_1 + q_5 + q_6 + q _ {10} = 22$,
$D _ {33} = q_3 + q_7 + q_8 + q _ {12} = 30$,
$D _ {55} = q_9 + q _ {10} + q _ {11} + q _ {12} = 42$
and off-diagonals $-q_j$ exactly as printed in the paper. (Branch 5 joins nodes 1
and 4; the scanned figure is ambiguous there, but figure 4 fixes it.)

**Theorem 1.** For random anchors and random $q \in [0.5, 3]$ on that graph, the
unloaded FDM solution and a BFGS minimiser of $\sum_j q_j l_j^2$ agree to
$4 \times 10^{-8}$.

**Jacobian (31) and damped iteration (20 to 25).** Implemented literally for
$r = 4$ prescribed strained lengths on the same graph: the analytic $G_d^t$ matches
finite differences to $9 \times 10^{-8}$, and the modified damped scheme with
$a_j = 0.8$ and $P^{-1} = 10^{-6} I$ reaches the prescribed lengths to $10^{-12}$
in 17 iterations while the free-node residual stays at machine precision. These
checks are part of `examples/form_finding/schek_equations.py`.

## References and provenance

- Schek, H.-J. (1974). *The force density method for form finding and computation
  of general networks.* Computer Methods in Applied Mechanics and Engineering 3,
  115–134. <https://doi.org/10.1016/0045-7825(74)90045-0>. Read in full from the
  publisher PDF (20 pages; OCR text checked against page images for every equation
  cited above). Received 26 June 1973; work done within SFB 64, Stuttgart, for the
  Munich Olympic roofs (references 16 and 17 of the paper).
- Linkwitz, K. (2014). *Chapter 6: Force density method — Design of a timber shell.*
  In S. Adriaenssens, P. Block, D. Veenendaal & C. Williams (eds.), *Shell
  Structures for Architecture: Form Finding and Optimization*, Routledge, pp. 59–69.
  Provides the physical rubber-band box thought experiment for anticlastic vs.
  synclastic curvature (Sec. 6.1–6.2, Figs. 6.2–6.3 & 6.7), the single-node 4-bar
  derivation of direction cosines and the $q$-weighted average coordinates
  (Sec. 6.2.1–6.2.3, Fig. 6.4, Eqs. 6.1–6.13), the Jacobian identity
  $(\partial \mathbf f(\mathbf x)/\partial \mathbf x)^T = C^T U L^{-1}$ (Sec. 6.4.2,
  Eqs. 6.22–6.24), the materialization cutting-length equation
  $\mathbf l _ 0 = (I + (EA)^{-1} Q L)^{-1} \mathbf l$ (Sec. 6.5, Eqs. 6.34–6.37),
  and the scale invariance of $(\mathbf q, \mathbf p)$ (Sec. 6.7, Figs. 6.9–6.11).
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
  2026-10-15 with compas_fd 0.5.4 in a throw-away virtual environment; the runnable NumPy derivation and equation checks are in
  `examples/form_finding/`. A standalone package benchmark, reusable adapter,
  MCP tool, and repository test remain to be added (see chapter README).

[Chapter README](README.md) · [compas_dr](compas_dr.md) · [compas_fofin](compas_fofin.md)
