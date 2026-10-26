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

* **1. Why cable equilibrium is nonlinear:** A cable $j$ between node $i$ and node $k$ has length $l_j = \sqrt{(x_i - x_k)^2 + (y_i - y_k)^2 + (z_i - z_k)^2}$ and tension $s_j$ ($\text{kN}$). By similar triangles, its $x$-force component is $F_{x,j} = s_j \frac{x_i - x_k}{l_j}$. Because the unknown coordinates $(x, y, z)$ sit inside the square root $l_j$ in the denominator, solving for node positions directly from forces $s_j$ is **nonlinear**.
* **2. How force density ($q_j = s_j / l_j$) makes it linear:** Prescribe the **force-to-length ratio** $q_j = s_j / l_j$ ($\text{kN/m}$), so $s_j = q_j l_j$. Substituting $s_j = q_j l_j$ into $F_{x,j}$ cancels the unknown length $l_j$ in the numerator and denominator:

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
| $\mathbf{x}, \mathbf{y}, \mathbf{z}$ / $\mathbf{x} _ f, \mathbf{y} _ f, \mathbf{z} _ f$ | `x, y, z` / `x_f, y_f, z_f` | `(5,)` / `(4,)` | Free-node (unknown) and fixed-anchor (known) coordinates ($\text{m}$) |
| $\mathbf{p} _ x, \mathbf{p} _ y, \mathbf{p} _ z$ | `p_x, p_y, p_z` | `(5,)` | External nodal loads at the 5 free nodes ($\text{kN}$) |
| $\mathbf{u}, \mathbf{v}, \mathbf{w}$ / $U, V, W$ | `u` / `np.diag(u)` | `(12,)` / `(12, 12)` | Branch coordinate differences $x_i - x_k,\ y_i - y_k,\ z_i - z_k$ ($\text{m}$) |
| $\mathbf{l}, \mathbf{s}, \mathbf{q}$ / $L, Q$ | `l, s, q` | `(12,)` / `(12, 12)` | Branch lengths $l_j$ ($\text{m}$), forces $s_j = q_j l_j$ ($\text{kN}$), force densities $q_j = s_j / l_j$ ($\text{kN/m}$) |
| $D = C^T Q C$, $D_f = C^T Q C_f$ | `D`, `D_f` | `(5, 5)`, `(5, 4)` | Free-node stiffness matrix and fixed-anchor coupling matrix |
| $\mathbf{l} _ 0, EA$ | `l_cutting, EA` | `(12,)` | Unstressed cutting lengths $l_j / (1 + s_j/EA_j)$ ($\text{m}$) and axial stiffness ($\text{kN}$) |

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

---

## Part A. The network as data

### A.1 Network topology: numbering the 9 nodes and 12 branches (section 2.1)

Throughout this entire tutorial, we use one single running example: Schek's **9-node, 12-branch saddle cable net** (Fig. 2). We number the $n = 5$ **free inner nodes first** ($1 \dots 5$) and the $n_f = 4$ **fixed outer anchor nodes last** ($6 \dots 9$) across the $m = 12$ directed branches ($i \to k$) so the connectivity matrix splits cleanly with a single vertical cut.

![Fig. 2](images/schek_fig2.png)

![Part A Topology and Matrix Operators on the Cable Net](images/fd_sec_a_topology_split.png)

* **Total Nodes ($n_s = 9$):** Free inner nodes $1 \dots 5$ ($n = 5$, unknown coordinates) and fixed anchors $6 \dots 9$ ($n_f = 4$, known boundary supports).
* **Directed Branches ($m = 12$):** Anchor cables $b_1 \dots b_4$: $(1\to 6),\ (2\to 7),\ (3\to 8),\ (4\to 9)$; inner ring $b_5 \dots b_8$: $(1\to 4),\ (1\to 2),\ (2\to 3),\ (3\to 4)$; center spokes $b_9 \dots b_{12}$: $(4\to 5),\ (1\to 5),\ (2\to 5),\ (3\to 5)$.

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
print(f"Network counts: m={m} branches, n={n} free nodes, n_f={n_f} fixed anchors")
```

* `branches` stores `(start_node, end_node)` pairs using Schek's 1-based node numbers $1 \dots 9$ (subtract `1` when indexing NumPy arrays).

**Example output:**

```text
Network counts: m=12 branches, n=5 free nodes, n_f=4 fixed anchors
```

### A.2 Vectors, diagonal matrices, and the diagonal swap (section 1.4)

On our 9-node, 12-branch network, lowercase bold letters ($\mathbf{u}, \mathbf{q}, \mathbf{l}$) denote $(12 \times 1)$ branch column vectors, while uppercase letters ($U, Q, L$) denote the $(12 \times 12)$ diagonal matrices formed by placing those 12 branch values on the main diagonal.

### General Equation

$$
U = \mathrm{diag}(\mathbf{u}), \qquad Q = \mathrm{diag}(\mathbf{q}), \qquad U \mathbf{q} = Q \mathbf{u}
$$

### Matrix Example (12 Branches of the 9-Node Net)

Placing the 12-branch coordinate-difference vector $\mathbf{u}$ and force-density vector $\mathbf{q}$ of our 9-node net onto $(12 \times 12)$ diagonals scales each branch row independently, so the factors commute ($U \mathbf{q} = Q \mathbf{u}$):

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
\underset{\mathbf{q}\ (12\times 1)}{\begin{bmatrix}
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
\underset{\mathbf{u}\ (12\times 1)}{\begin{bmatrix}
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
U_12, Q_12 = np.diag(u_12), np.diag(q_12)
print("U @ q == Q @ u (12 branches):", (U_12 @ q_12).astype(int))
```

* `np.diag(u_12)` and `np.diag(q_12)` place the `(12,)` branch vectors on the main diagonal of `(12, 12)` matrices; `U_12 @ q_12`, `Q_12 @ u_12`, and `u_12 * q_12` all produce the exact same `(12,)` vector.

**Example output:**

```text
U @ q == Q @ u (12 branches): [ 2  0 -2  0 -1 -1 -1  1  0 -1  0  1]
```

### A.3 Branch-node connectivity matrix and partitioning (section 2.1)

Encode the 9-node, 12-branch directed graph as a $(12 \times 9)$ branch-node incidence matrix $C_s$ ($+1$ at start node $i$, $-1$ at end node $k$), partitioned into free-node columns $C$ $(12 \times 5)$ and fixed-anchor columns $C_f$ $(12 \times 4)$.

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
C: FloatMatrix = C_s[:, :n]           # (m, n)   free-node columns
C_f: FloatMatrix = C_s[:, n:]         # (m, n_f) fixed-anchor columns
print("C_s (12x9):\n", C_s.astype(int))
```

* `C = C_s[:, :n]` slices the first `5` columns (free nodes, `(12, 5)`); `C_f = C_s[:, n:]` slices the last `4` columns (fixed anchors, `(12, 4)`).

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

Trace how $D = C^T (Q C)$ assembles the $(5 \times 5)$ nodal equilibrium matrix directly on our **9-node, 12-branch network** with force densities $\mathbf{q} = [2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1]^T$.

### 1. Free Connectivity $C\ (12 \times 5)$ and Transpose $C^T\ (5 \times 12)$

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
QC = Q_12 @ C
D_preview = C.T @ QC
print("D = C.T @ diag(q) @ C (5x5):\n", D_preview.astype(int))
```

* `Q_12 @ C` weights each of the 12 branch rows by $q_j$, and `C.T @ QC` sums those weighted rows at each of the 5 free nodes ($D_{ii} = \sum q_j$ of branches touching node $i$; $D_{ik} = -q_j$ of the branch joining free nodes $i$ and $k$).

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

### B.1 Inputs: fixed anchor coordinates and nodal loads (section 2.2)

Specify the known boundary support coordinates $(\mathbf{x} _ f, \mathbf{y} _ f, \mathbf{z} _ f)$ in $\text{m}$ ($4 \times 3$) and external free-node loads $(\mathbf{p} _ x, \mathbf{p} _ y, \mathbf{p} _ z)$ in $\text{kN}$ ($5 \times 3$, $+z$ up).

### Matrix Example (Inputs)

$$
\begin{bmatrix} \mathbf{x} _ f & \mathbf{y} _ f & \mathbf{z} _ f \end{bmatrix} =
\begin{bmatrix}
-2 & 0 & 0 \\
0 & 2 & 1 \\
2 & 0 & 0 \\
0 & -2 & 1
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Anchor 6 (ground)} \\
\leftarrow \text{Anchor 7 (lifted } +1\text{ m)} \\
\leftarrow \text{Anchor 8 (ground)} \\
\leftarrow \text{Anchor 9 (lifted } +1\text{ m)}
\end{matrix},
\qquad
\begin{bmatrix} \mathbf{p} _ x & \mathbf{p} _ y & \mathbf{p} _ z \end{bmatrix} =
\begin{bmatrix}
0 & 0 & -0.5 \\
0 & 0 & -0.5 \\
0 & 0 & -0.5 \\
0 & 0 & -0.5 \\
0 & 0 & -0.5
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Node 1 (}-0.5\text{ kN)} \\
\leftarrow \text{Node 2 (}-0.5\text{ kN)} \\
\leftarrow \text{Node 3 (}-0.5\text{ kN)} \\
\leftarrow \text{Node 4 (}-0.5\text{ kN)} \\
\leftarrow \text{Node 5 (}-0.5\text{ kN)}
\end{matrix}
$$

**Add to your program:**

```python
x_f: FloatVector = np.array([-2.0, 0.0, 2.0, 0.0], dtype=np.float64)
y_f: FloatVector = np.array([0.0, 2.0, 0.0, -2.0], dtype=np.float64)
z_f: FloatVector = np.array([0.0, 1.0, 0.0, 1.0], dtype=np.float64)
p_x: FloatVector = np.zeros(n, dtype=np.float64)
p_y: FloatVector = np.zeros(n, dtype=np.float64)
p_z: FloatVector = np.full(n, -0.5, dtype=np.float64)
print("Fixed anchors [x_f, y_f, z_f] (4x3):\n", np.c_[x_f, y_f, z_f])
```

* `x_f, y_f, z_f` have shape `(4,)` for anchors $6 \dots 9$; `p_x, p_y, p_z` have shape `(5,)` for free nodes $1 \dots 5$.

**Example output:**

```text
Fixed anchors [x_f, y_f, z_f] (4x3):
 [[-2.  0.  0.]
 [ 0.  2.  1.]
 [ 2.  0.  0.]
 [ 0. -2.  1.]]
```

### B.2 Coordinate differences and cable lengths, equation (1)

For each branch $j\ (i \to k)$, compute the coordinate differences $(u_j, v_j, w_j) = (x_i - x_k,\ y_i - y_k,\ z_i - z_k)$ and the Euclidean cable length $l_j$.

![Section B.2 Geometric Meaning of Coordinate Differences u, v, w and Cable Length l](images/fd_sec_b2_uvw_geometry.png)

### General Equations (Eq. 1)

$$
\mathbf{u} = C \mathbf{x} + C_f \mathbf{x} _ f, \qquad
\mathbf{v} = C \mathbf{y} + C_f \mathbf{y} _ f, \qquad
\mathbf{w} = C \mathbf{z} + C_f \mathbf{z} _ f, \qquad
l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}
$$

### Matrix Example (Flat Trial Coordinates $\mathbf{x} = [-1, 0, 1, 0, 0]^T,\ \mathbf{y} = [0, -1, 0, 1, 0]^T,\ \mathbf{z} = \mathbf{0}$)

$$
\underset{\mathbf{u}\ (12\times 1)}{\begin{bmatrix}
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
\underset{\mathbf{x}\ (5\times 1)}{\begin{bmatrix}
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
\underset{\mathbf{x} _ f\ (4\times 1)}{\begin{bmatrix}
-2 \\
0 \\
2 \\
0
\end{bmatrix}}
$$

$$
\begin{bmatrix} \mathbf{u} & \mathbf{v} & \mathbf{w} \end{bmatrix} =
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
\mathbf{l} =
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
L^{-1} = \mathrm{diag}(1 / \mathbf{l}) =
\begin{bmatrix}
1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & \tfrac{1}{\sqrt{10}} & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & \tfrac{1}{\sqrt{10}} & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & \tfrac{1}{\sqrt{2}} & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & \tfrac{1}{\sqrt{2}} & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & \tfrac{1}{\sqrt{2}} & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & \tfrac{1}{\sqrt{2}} & 0 & 0 & 0 & 0 \\
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
    u = C @ x + C_f @ x_f
    v = C @ y + C_f @ y_f
    w = C @ z + C_f @ z_f
    l = np.sqrt(u**2 + v**2 + w**2)
    return u, v, w, l


u_flat, v_flat, w_flat, l_flat = coordinate_differences(
    C, np.array([-1.0, 0.0, 1.0, 0.0, 0.0]), np.array([0.0, -1.0, 0.0, 1.0, 0.0]), np.zeros(n), C_f, x_f, y_f, z_f
)
print("Flat trial cable lengths l (m):", l_flat)
```

* `C @ x + C_f @ x_f` evaluates $(12, 5) \times (5,) + (12, 4) \times (4,) \to (12,)$, computing $x_{\text{start}} - x_{\text{end}}$ for all 12 branches at once.

**Example output:**

```text
Flat trial cable lengths l (m): [1.    3.162 1.    3.162 1.414 1.414 1.414 1.414 1.    1.    1.    1.   ]
```

### B.3 Nonlinear equilibrium in 4 stages, equation (2)

From a single cable's tension $s_j$ and length $l_j$, we derive the 4-stage matrix equilibrium equation $\mathbf{e} _ x = C^T U L^{-1} \mathbf{s} - \mathbf{p} _ x$, reading the matrix product **right to left** from Stage 1 to Stage 4.

![Section B.3 Four-Stage Nonlinear Equilibrium and Flat Net Imbalance](images/fd_sec_b3_nonlinear_stages.png)

### How Stages 1–4 Are Derived (From One Cable to Matrix Form, Eq. 2)

1. **Single cable $j\ (i \to k)$:** Cable $j$ pulls with axial tension $s_j$ ($\text{kN}$) along its 3D length $l_j$ ($\text{m}$). By similar triangles, its direction cosine along $x$ is $u_j / l_j = (x_i - x_k) / l_j$, so its horizontal force component is:

$$
F_{x,j} = s_j \frac{u_j}{l_j} = u_j \underbrace{\left(\frac{s_j}{l_j}\right)} _ {\text{Stage 1: } q_j}
$$

2. **All 12 cables in matrix form (Stages 1 & 2):** Using the diagonal matrices $L^{-1} = \mathrm{diag}(1/l_1, \dots, 1/l_{12})$ and $U = \mathrm{diag}(u_1, \dots, u_{12})$:
   * **Stage 1:** $\mathbf{q} = L^{-1} \mathbf{s}\ (12 \times 1)$ divides each cable's tension $s_j$ by its length $l_j$ ($q_j = s_j / l_j$).
   * **Stage 2:** $\mathbf{F} _ x = U \mathbf{q} = U L^{-1} \mathbf{s}\ (12 \times 1)$ multiplies each cable's ratio $q_j$ by its span $u_j$ ($F_{x,j} = u_j q_j$).
3. **Force balance at the 5 free nodes (Stages 3 & 4):** Row $i$ of $C^T\ (5 \times 12)$ has $+1$ for cables starting at node $i$ and $-1$ for cables ending at node $i$, so multiplying by $C^T$ sums the cable forces at each free node $i = 1 \dots 5$, and subtracting external load $\mathbf{p} _ x\ (5 \times 1)$ gives the out-of-balance residual:

$$
\mathbf{e} _ x = \underbrace{C^T} _ {\text{Stage 3: sum at nodes } (5\times 12)} \quad \underbrace{U} _ {\text{Stage 2: project } x\ (12\times 12)} \quad \underbrace{L^{-1} \mathbf{s}} _ {\text{Stage 1: } q_j = s_j / l_j\ (12\times 1)} \quad - \quad \underbrace{\mathbf{p} _ x} _ {\text{Stage 4: load } (5\times 1)}
$$

---

### Stage-by-Stage Matrix Breakdown (Flat Trial Net with $s_j = 1\text{ kN}$)

#### Stage 1 — Force Density Ratios: $\mathbf{q} = L^{-1} \mathbf{s}\ (12 \times 1)$

$$
\mathbf{q} =
\underset{L^{-1}\ (12\times 12)}{\begin{bmatrix}
1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & \tfrac{1}{\sqrt{10}} & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & \tfrac{1}{\sqrt{10}} & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & \tfrac{1}{\sqrt{2}} & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & \tfrac{1}{\sqrt{2}} & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & \tfrac{1}{\sqrt{2}} & 0 & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & \tfrac{1}{\sqrt{2}} & 0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 1
\end{bmatrix}}
\underset{\mathbf{s}\ (12\times 1)}{\begin{bmatrix}
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
\tfrac{1}{\sqrt{10}} \\
1 \\
\tfrac{1}{\sqrt{10}} \\
\tfrac{1}{\sqrt{2}} \\
\tfrac{1}{\sqrt{2}} \\
\tfrac{1}{\sqrt{2}} \\
\tfrac{1}{\sqrt{2}} \\
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

#### Stage 2 — Projected Branch Force Components: $\mathbf{F} _ x = U \mathbf{q},\ \mathbf{F} _ y = V \mathbf{q},\ \mathbf{F} _ z = W \mathbf{q}\ (12 \times 1)$

$$
\mathbf{F} _ x = U \mathbf{q} =
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
\underset{\mathbf{q}\ (12\times 1)}{\begin{bmatrix}
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
$$

Similarly along $y$ ($\mathbf{F} _ y = V \mathbf{q}$) and $z$ ($\mathbf{F} _ z = W \mathbf{q}$):

$$
\mathbf{F} _ y = V \mathbf{q} =
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
\underset{\mathbf{q}\ (12\times 1)}{\begin{bmatrix}
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
\mathbf{F} _ z = W \mathbf{q} =
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
\underset{\mathbf{q}\ (12\times 1)}{\begin{bmatrix}
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

#### Stage 3 — Sum Cable Forces at Free Nodes: $C^T \mathbf{F} _ x,\ C^T \mathbf{F} _ y,\ C^T \mathbf{F} _ z\ (5 \times 1)$

$$
C^T \mathbf{F} _ x =
\underset{C^T\ (5\times 12)}{\begin{bmatrix}
1 & 0 & 0 & 0 & 1 & 1 & 0 & 0 & 0 & 1 & 0 & 0 \\
0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 \\
0 & 0 & 0 & 1 & -1 & 0 & 0 & -1 & 1 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & -1 & -1 & -1 & -1
\end{bmatrix}}
\underset{\mathbf{F} _ x\ (12\times 1)}{\begin{bmatrix}
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
C^T \mathbf{F} _ y =
\underset{C^T\ (5\times 12)}{\begin{bmatrix}
1 & 0 & 0 & 0 & 1 & 1 & 0 & 0 & 0 & 1 & 0 & 0 \\
0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 \\
0 & 0 & 0 & 1 & -1 & 0 & 0 & -1 & 1 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & -1 & -1 & -1 & -1
\end{bmatrix}}
\underset{\mathbf{F} _ y\ (12\times 1)}{\begin{bmatrix}
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
C^T \mathbf{F} _ z =
\begin{bmatrix}
0 \\
-0.316 \\
0 \\
-0.316 \\
0
\end{bmatrix}\text{ kN}
$$

#### Stage 4 — Subtract Applied Loads to Check Equilibrium: $\mathbf{e} = C^T \mathbf{F} - \mathbf{p}\ (5 \times 1)$

$$
\mathbf{e} _ x =
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
\mathbf{e} _ y =
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
\mathbf{e} _ z =
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
    L_inv = np.diag(1.0 / l)
    return (
        C.T @ np.diag(u) @ L_inv @ s - p_x,
        C.T @ np.diag(v) @ L_inv @ s - p_y,
        C.T @ np.diag(w) @ L_inv @ s - p_z,
    )


x_guess = np.array([-1.0, 0.0, 1.0, 0.0, 0.0])   # flat guess for free nodes
y_guess = np.array([0.0, -1.0, 0.0, 1.0, 0.0])
z_guess = np.zeros(n)
s_guess = np.ones(m)                             # 1 kN in every branch
ex, ey, ez = equilibrium_error(x_guess, y_guess, z_guess, s_guess)
print("Flat guess out-of-balance residual e_z (kN):", ez)
```

* `L_inv = np.diag(1.0 / l)` builds the `(12, 12)` diagonal inverse-length matrix $L^{-1}$, and `C.T @ np.diag(u) @ L_inv @ s - p_x` chains Stages 1–4 right-to-left (nonlinear in $\mathbf{x}, \mathbf{y}, \mathbf{z}$ because $L^{-1}$ divides by $\sqrt{u_j^2 + v_j^2 + w_j^2}$).

**Example output:**

```text
Flat guess out-of-balance residual e_z (kN): [0.5   0.184 0.5   0.184 0.5  ]
```

---

## Part C. The force density trick: a linear system

### C.1 The force density trick and the diagonal swap, equations (4) to (6)

In Section B.3, the horizontal branch force $F_{x,j} = s_j (u_j / l_j)$ was nonlinear because the unknown length $l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}$ sat in the denominator. If instead we prescribe the **force density** $q_j = s_j / l_j$ ($\text{kN/m}$, so $s_j = q_j l_j$), then $l_j$ in the numerator and denominator cancels out: $F_{x,j} = (q_j l_j)(u_j / l_j) = q_j u_j$.

![Section C.1 How Force Density Uses Coordinate Difference u to Linearize Equilibrium](images/fd_sec_c1_force_density_trick.png)

### General Equations (Eqs. 4–6) & Meaning of $u$

$$
q_j = \frac{s_j}{l_j} \quad (\mathbf{q} = L^{-1} \mathbf{s})
\qquad \Longrightarrow \qquad
F_{x, j} = s_j \frac{u_j}{l_j} = (q_j l_j) \frac{u_j}{l_j} = q_j u_j = q_j (x_i - x_k)
$$

$$
C^T U \mathbf{q} = C^T Q \mathbf{u} = \mathbf{p} _ x, \qquad
C^T V \mathbf{q} = C^T Q \mathbf{v} = \mathbf{p} _ y, \qquad
C^T W \mathbf{q} = C^T Q \mathbf{w} = \mathbf{p} _ z
$$

* **$u_j$, $\mathbf{u}$ $(12 \times 1)$, and $U = \mathrm{diag}(\mathbf{u})$ $(12 \times 12)$:** $u_j = x_i - x_k$ is the $x$-coordinate difference ($\text{m}$) between start node $i$ and end node $k$ of branch $j$ (similarly $v_j = y_i - y_k$ in $V$, $w_j = z_i - z_k$ in $W$).
* **Why we swap $U \mathbf{q} = Q \mathbf{u}$:** moves the **unknown** coordinate vector $\mathbf{u}$ to the right of the **known** diagonal force-density matrix $Q = \mathrm{diag}(\mathbf{q})$.

### Matrix Example ($\mathbf{F} _ x = U \mathbf{q} = Q \mathbf{u}$ on All 12 Branches)

$$
\mathbf{F} _ x =
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
\underset{\mathbf{q}\ (12\times 1)}{\begin{bmatrix}
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
\underset{\mathbf{u}\ (12\times 1)}{\begin{bmatrix}
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
q = np.array([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1], dtype=float)
print("Prescribed force densities q (kN/m):", q)
```

* `q` assigns $2\text{ kN/m}$ to the 4 outer anchor branches (`0..3`) and $1\text{ kN/m}$ to the 8 inner branches (`4..11`).

**Example output:**

```text
Prescribed force densities q (kN/m): [2. 2. 2. 2. 1. 1. 1. 1. 1. 1. 1. 1.]
```

### C.2 System matrices $D$ and $D_f$, equations (7) and (8)

Substituting $\mathbf{u} = C \mathbf{x} + C_f \mathbf{x} _ f$ into $C^T Q \mathbf{u} = \mathbf{p} _ x$ separates unknown free-node coordinates $\mathbf{x}$ from known anchor coordinates $\mathbf{x} _ f$ via $D = C^T Q C\ (5 \times 5)$ and $D_f = C^T Q C_f\ (5 \times 4)$.

![Sections C.2 to D.1 Physical Meaning of D and Solved 3D Saddle Equilibrium Net](images/fd_sec_c2_c3_solved_net.png)

### General Equations (Eqs. 7–8)

$$
(C^T Q C)\mathbf{x} + (C^T Q C_f)\mathbf{x} _ f = \mathbf{p} _ x
\qquad \Longrightarrow \qquad
D \mathbf{x} = \mathbf{p} _ x - D_f \mathbf{x} _ f = \mathbf{b} _ x
$$

### 1. Symbolic Structure of $D$ and Schek Fig. 4 ($q_j = j$)

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

### 2. Actual Matrices $D$, $D_f$, and Right-Hand Side $\mathbf{b} _ z = \mathbf{p} _ z - D_f \mathbf{z} _ f$

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
\mathbf{b} _ z = \mathbf{p} _ z - D_f \mathbf{z} _ f =
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
Q = np.diag(q)
D = C.T @ Q @ C                                 # (n, n)   eq. (8)
D_f = C.T @ Q @ C_f                             # (n, n_f)
rhs = np.c_[p_x - D_f @ x_f, p_y - D_f @ y_f, p_z - D_f @ z_f]
print("D (5x5):\n", D)
print("D_f (5x4):\n", D_f)
print("RHS [b_x, b_y, b_z] (5x3):\n", rhs)
```

* `D = C.T @ Q @ C` is `(5, 5)`, `D_f = C.T @ Q @ C_f` is `(5, 4)`, and `rhs` stacks the three `(5,)` right-hand side vectors into `(5, 3)`.

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

Because $D = C^T Q C$ is constant and symmetric positive-definite, solving $D \mathbf{x} = \mathbf{b} _ x$, $D \mathbf{y} = \mathbf{b} _ y$, $D \mathbf{z} = \mathbf{b} _ z$ gives the exact 3D equilibrium coordinates in one direct step.

### General Equations (Eq. 9)

$$
D \mathbf{x} = \mathbf{p} _ x - D_f \mathbf{x} _ f, \qquad
D \mathbf{y} = \mathbf{p} _ y - D_f \mathbf{y} _ f, \qquad
D \mathbf{z} = \mathbf{p} _ z - D_f \mathbf{z} _ f
$$

### Matrix Example (Vertical Equilibrium Solve $D \mathbf{z} = \mathbf{b} _ z$ and 3D Coordinates)

$$
\underset{D\ (5\times 5)}{\begin{bmatrix}
5 & -1 & 0 & -1 & -1 \\
-1 & 5 & -1 & 0 & -1 \\
0 & -1 & 5 & -1 & -1 \\
-1 & 0 & -1 & 5 & -1 \\
-1 & -1 & -1 & -1 & 4
\end{bmatrix}}
\underset{\mathbf{z}\ (5\times 1)}{\begin{bmatrix}
z_1 \\
z_2 \\
z_3 \\
z_4 \\
z_5
\end{bmatrix}} =
\underset{\mathbf{b} _ z\ (5\times 1)}{\begin{bmatrix}
-0.5 \\
1.5 \\
-0.5 \\
1.5 \\
-0.5
\end{bmatrix}}
\qquad \overset{\text{solve}}{\longrightarrow} \qquad
\mathbf{z} =
\begin{bmatrix}
0.045 \\
0.330 \\
0.045 \\
0.330 \\
0.063
\end{bmatrix}\text{ m}
$$

$$
\begin{bmatrix} \mathbf{x} & \mathbf{y} & \mathbf{z} \end{bmatrix} =
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
x: FloatVector = np.linalg.solve(D, p_x - D_f @ x_f)    # eq. (9)
y: FloatVector = np.linalg.solve(D, p_y - D_f @ y_f)
z: FloatVector = np.linalg.solve(D, p_z - D_f @ z_f)
print("Solved free-node coordinates [x, y, z] (5x3):\n", np.c_[x, y, z])
```

* `np.linalg.solve(D, b)` solves each `(5, 5)` linear system directly using the shared stiffness matrix `D`.

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

From the solved coordinates $(\mathbf{x}, \mathbf{y}, \mathbf{z})$, we recompute branch lengths $\mathbf{l}$, recover branch tensions $\mathbf{s} = Q \mathbf{l}$, and compute unstressed cutting lengths $l_{0,j} = l_j / (1 + s_j / EA_j)$.

### General Equations (Schek Eq. 10 & Linkwitz Eq. 6.37)

$$
s_j = q_j l_j \quad (\mathbf{s} = Q \mathbf{l} = L \mathbf{q}), \qquad
\mathbf{e} _ x = C^T U L^{-1} \mathbf{s} - \mathbf{p} _ x = \mathbf{0}, \qquad
l_{0,j} = \frac{l_j}{1 + s_j / EA_j}
$$

### Matrix Example ($\mathbf{q}$, $\mathbf{l}$, $\mathbf{s}$, and Cutting Lengths $\mathbf{l} _ 0$ for $EA = 500\text{ kN}$)

$$
\underset{\mathbf{q}\ (\text{kN/m})}{\begin{bmatrix}
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
\underset{\mathbf{l}\ (\text{m})}{\begin{bmatrix}
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
\underset{\mathbf{s}\ (\text{kN})}{\begin{bmatrix}
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
\underset{\mathbf{l} _ 0\ (\text{m})}{\begin{bmatrix}
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
\begin{matrix}
\leftarrow b_1\ (1\to 6,\ e_1 = 5.7\text{ mm}) \\
\leftarrow b_2\ (2\to 7,\ e_2 = 7.5\text{ mm}) \\
\leftarrow b_3\ (3\to 8,\ e_3 = 5.7\text{ mm}) \\
\leftarrow b_4\ (4\to 9,\ e_4 = 7.5\text{ mm}) \\
\leftarrow b_5\ (1\to 4,\ e_5 = 2.7\text{ mm}) \\
\leftarrow b_6\ (1\to 2,\ e_6 = 2.7\text{ mm}) \\
\leftarrow b_7\ (2\to 3,\ e_7 = 2.7\text{ mm}) \\
\leftarrow b_8\ (3\to 4,\ e_8 = 2.7\text{ mm}) \\
\leftarrow b_9\ (4\to 5,\ e_9 = 1.4\text{ mm}) \\
\leftarrow b_{10}\ (1\to 5,\ e_{10} = 1.3\text{ mm}) \\
\leftarrow b_{11}\ (2\to 5,\ e_{11} = 1.4\text{ mm}) \\
\leftarrow b_{12}\ (3\to 5,\ e_{12} = 1.3\text{ mm})
\end{matrix}
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

* `s = l * q` recovers axial tensions (longer branches with the same $q$ carry higher force), `l_cutting` gives unstressed cutting lengths, and `max_eq_error` is `4.44e-16`.

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

We package Steps A.3–C.4 into `form_finding` and compute the 3D support reactions $\mathbf{R} _ f = C_f^T Q \mathbf{U} _ {xyz}$ at the 4 fixed anchors.

![Fig. 3](images/schek_fig3.png)

### General Equations

$$
D \mathbf{X} = \mathbf{P} - D_f \mathbf{X} _ f, \qquad
\mathbf{U} _ {xyz} = C \mathbf{X} + C_f \mathbf{X} _ f, \qquad
\mathbf{R} _ f = C_f^T Q \mathbf{U} _ {xyz}
$$

### Matrix Example (Support Reactions $\mathbf{R} _ f$)

$$
\mathbf{R} _ f = C_f^T Q \mathbf{U} _ {xyz} =
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
    reactions = C_f.T @ Q @ uvw                                # eq. (5)
    return xyz, l, s, reactions
```

* `reactions = C_f.T @ Q @ uvw` computes the `(4, 3)` support reactions; vertical reactions sum to $+2.500\text{ kN}$, balancing the $-2.500\text{ kN}$ total load.

### D.2 Parameter study: moving anchors, changing force densities, and scale invariance

Moving anchors $\mathbf{X} _ f$ only updates the right-hand side, changing $\mathbf{q}$ rebuilds $D$, and scaling $(2\mathbf{q}, 2\mathbf{P})$ leaves the 3D geometry identical while doubling forces (scale invariance).

![Parts D, E and F Parameter Study, Energy Minimization and Target Length Constraints](images/fd_sec_e_f_constraints.png)

### Matrix Example (Free-Node Heights $\mathbf{z}$ Across 4 Cases)

$$
\begin{bmatrix}
\mathbf{z} _ {\text{case 1}} & \mathbf{z} _ {\text{case 2}} & \mathbf{z} _ {\text{case 3}} & \mathbf{z} _ {\text{case 4}}
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
\mathbf{s} _ {\text{case 4}} = 2\mathbf{s} _ {\text{case 1}}
$$

| Case | Matrix $D\ (5\times 5)$ | RHS $\mathbf{P} - D_f \mathbf{X} _ f$ | Center Height $z_5\ (\text{m})$ | Max Force $\max(\mathbf{s})$ |
|---|---|---|---|---|
| **1. Base case** ($q_{\text{anchor}} = 2,\ \mathbf{p} _ z = -0.5$) | built once | base | $0.063\text{ m}$ | $2.748\text{ kN}$ |
| **2. All anchors lifted** $+1\text{ m}$ | **unchanged** | updated | $1.063\text{ m}$ | $2.748\text{ kN}$ |
| **3. Stiffer anchors** ($q_{\text{anchor}} = 10,\ \mathbf{p} _ z = -0.5$) | **rebuilt** | updated | $0.313\text{ m}$ | $4.732\text{ kN}$ |
| **4. Scale invariance** ($2\mathbf{q},\ 2\mathbf{p} _ z$) | $2\times$ | $2\times$ | **$0.063\text{ m}$** | **$5.496\text{ kN}$ ($2\times$)** |

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

* Raising $q_{1..4}$ from $2 \to 10\text{ kN/m}$ pulls center node 5 from $z_5 = 0.063 \to 0.313\text{ m}$, while doubling both `q` and `p` gives `scale_invariance_xyz_diff == 0.0`.

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

For an unloaded network ($\mathbf{P} = \mathbf{0}$), solving $D\mathbf{X} = -D_f\mathbf{X} _ f$ minimizes the weighted squared-length functional $\Phi = \sum q_j l_j^2$ (Theorem 1), and setting $q_j = c / l_j$ produces a constant-force net $s_j = c$ (Theorem 2).

### General Equations (Eqs. 37–40)

$$
\Phi(\mathbf{x}, \mathbf{y}, \mathbf{z}) = \mathbf{u}^T Q \mathbf{u} + \mathbf{v}^T Q \mathbf{v} + \mathbf{w}^T Q \mathbf{w} = \sum_{j=1}^m q_j l_j^2 \longrightarrow \min
\qquad \Longleftrightarrow \qquad
\frac{\partial \Phi}{\partial \mathbf{x}} = 2 C^T Q \mathbf{u} = 2 (D \mathbf{x} + D_f \mathbf{x} _ f) = \mathbf{0}
$$

### Matrix Example (Unloaded Saddle $\mathbf{P} = \mathbf{0}$)

$$
\mathbf{X} _ 0 = \begin{bmatrix}
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
\nabla \Phi(\mathbf{X} _ 0) = 2 C^T Q \mathbf{U} _ 0 = \mathbf{0} _ {5\times 3}
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

* `max_grad_unloaded` is `8.88e-16` ($\approx 0$), and setting `q_const = 1.0 / l0` gives uniform tensions `s_uniform = [1, 1, ..., 1]` kN.

**Example output:**

```text
Theorem 1 max |dPhi/dX|: 2.22e-15
Theorem 2 uniform forces s (kN): [1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1.]
```

---

## Part F. Asking for lengths and forces

### F.1 Target length and force constraints, equation (11)

To enforce target equilibrium branch lengths $\mathbf{l} _ v$ or forces $\mathbf{s} _ v$, we form the residual vector $\mathbf{g}^{\ast}(\mathbf{q})$ and solve for $\mathbf{q}^{\ast} \gt \mathbf{0}$ such that $\mathbf{g}^{\ast}(\mathbf{q}^{\ast}) = \mathbf{0}$.

### General Equation (Eq. 11)

$$
\mathbf{g}^{\ast}(\mathbf{q}) = \begin{bmatrix}
\mathbf{l} _ {\text{constrained}}(\mathbf{q}) - \mathbf{l} _ v \\
\mathbf{s} _ {\text{constrained}}(\mathbf{q}) - \mathbf{s} _ v
\end{bmatrix} = \mathbf{0}
$$

### Matrix Example (Target Anchor Length $l_{1..4} = 1.200\text{ m}$)

$$
\mathbf{g}^{\ast}(\mathbf{q}) =
\underset{\mathbf{l} _ {1..4}(\mathbf{q})}{\begin{bmatrix}
1.201 \\
1.374 \\
1.201 \\
1.374
\end{bmatrix}} -
\underset{\mathbf{l} _ v}{\begin{bmatrix}
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

* `g_lengths` measures how far the 4 anchor branches deviate from $1.200\text{ m}$ at the initial $\mathbf{q}$.

**Example output:**

```text
Initial anchor lengths (m): [1.201 1.374 1.201 1.374]
Length residual g*(q) (m):  [0.001 0.174 0.001 0.174]
```

### F.2 Iterative solver for prescribed lengths and forces (sections 3.1 to 3.6)

At each iteration, we run `form_finding(q)` and update $\mathbf{q} \gt \mathbf{0}$ via least squares until the constraint residual $\mathbf{g}^{\ast}(\mathbf{q}^{\ast})$ vanishes.

### Iteration Loop

$$
\mathbf{q}^{(k)} \xrightarrow{D(\mathbf{q}^{(k)})\mathbf{X} = \mathbf{B}} \mathbf{l}(\mathbf{q}^{(k)}),\ \mathbf{s}(\mathbf{q}^{(k)}) \xrightarrow{\text{residual}} \mathbf{g}^{\ast}(\mathbf{q}^{(k)}) \xrightarrow{\Delta\mathbf{q}} \mathbf{q}^{(k+1)}
$$

### Matrix Example (Before vs. After on Anchor Cables 1–4)

$$
\text{Initial:}\quad
\mathbf{q} _ {1..4}^{(0)} =
\begin{bmatrix}
2.000 \\
2.000 \\
2.000 \\
2.000
\end{bmatrix}\text{ kN/m},
\quad
\mathbf{l} _ {1..4}^{(0)} =
\begin{bmatrix}
1.201 \\
1.374 \\
1.201 \\
1.374
\end{bmatrix}\text{ m}
\qquad \longrightarrow \qquad
\text{Solved:}\quad
\mathbf{q} _ {1..4}^{\ast} =
\begin{bmatrix}
1.972 \\
2.412 \\
1.972 \\
2.412
\end{bmatrix}\text{ kN/m},
\quad
\mathbf{l} _ {1..4}^{\ast} =
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

* `least_squares(residual, q_start, bounds=(1e-9, np.inf))` adjusts `q > 0` until all prescribed length and force residuals reach zero.

**Example output:**

```text
Optimized q*_[1..4]: [1.972 2.412 1.972 2.412] -> lengths l*_[1..4]: [1.2 1.2 1.2 1.2] (err=1.8e-08)
Mixed target spokes l*_[9..12]: [0.9 0.9 0.9 0.9] m, anchor forces s*_[1..4]: [2. 2. 2. 2.] kN (err=7.5e-11)
```

### F.3 Sensitivity Jacobian $G^T = \partial \mathbf{g}^{\ast} / \partial \mathbf{q}$ (sections 3.2 to 3.5)

Differentiating $C^T Q \mathbf{u}(\mathbf{q}) = \mathbf{p} _ x$ with respect to $\mathbf{q}$ gives the node sensitivity $\partial \mathbf{x} / \partial \mathbf{q} = -D^{-1} C^T U$ and the constraint Jacobian $G^T = \partial \mathbf{g}^{\ast} / \partial \mathbf{q}$.

### General Equations (Eqs. 28 & 31)

$$
\frac{\partial \mathbf{x}}{\partial \mathbf{q}} = -D^{-1} C^T U, \qquad
\frac{\partial \mathbf{y}}{\partial \mathbf{q}} = -D^{-1} C^T V, \qquad
\frac{\partial \mathbf{z}}{\partial \mathbf{q}} = -D^{-1} C^T W, \qquad
G^T = \frac{\partial \mathbf{g}^{\ast}}{\partial \mathbf{q}}
$$

### Matrix Example (Anchor Length Jacobian $G^T_{1..4,\ 1..4}$ and Height Sensitivity $\partial \mathbf{z} / \partial \mathbf{q} _ {1..4}$)

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
\frac{\partial \mathbf{z}}{\partial \mathbf{q} _ {1..4}} = -D^{-1} C^T W_{:, 1..4} =
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


G_t = sensitivity(q, [0, 1, 2, 3])
print("Jacobian block G_t[:, :4] (4x4):\n", G_t[:, :4])
```

* Nudging each `q[j]` by `1e-6` and dividing the length change by `step` matches Schek's analytic Jacobian (Eqs. 31–35) to 3 decimal places.

**Example output:**

```text
Jacobian block G_t[:, :4] (4x4):
 [[-0.313  0.002  0.073  0.002]
 [ 0.002 -0.358  0.002  0.044]
 [ 0.073  0.002 -0.313  0.002]
 [ 0.002  0.044  0.002 -0.358]]
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
| full $C_s^{t} Q C_s\ (9 \times 9)$ | `A` | `C.T @ Q @ C` (used only for residuals) |
| right-hand side of (8) $(5 \times 3)$ | `b` | `p[free] - Af @ xyz[fixed]` |
| (9) $(5 \times 3)$ | — | `xyz[free] = spsolve(Ai, b)` |
| $\mathbf{l}\ (12 \times 1)$ | `lengths` | `normrow(C @ xyz)` |
| (10) $\mathbf{s}\ (12 \times 1)$ | `forces` | `q * lengths` |
| residual $(9 \times 3)$ | `residuals` | `p - A @ xyz` |

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
| Free nodes 1, 3 (`vertices[0]`, `vertices[2]`) | $(\mp 0.800,\ 0.000,\ 0.045)\text{ m}$; difference $\lt  10^{-15}\text{ m}$ |
| Free nodes 2, 4 (`vertices[1]`, `vertices[3]`) | $(0.000,\ \pm 0.800,\ 0.330)\text{ m}$; difference $\lt  10^{-15}\text{ m}$ |
| Center free node 5 (`vertices[4]`) | $(0.000,\ 0.000,\ 0.063)\text{ m}$; difference $\lt  10^{-15}\text{ m}$ |
| Residuals at free nodes 1–5 | $(0,\ 0,\ 0)\text{ kN}$ ($\lt  10^{-15}\text{ kN}$) |
| Anchor lengths $l_{1,3}$ / $l_{2,4}$ | $1.201\text{ m}$ / $1.374\text{ m}$ |
| Anchor forces $s_{1,3}$ / $s_{2,4}$ | $2.402\text{ kN}$ / $2.749\text{ kN}$ ($= q_j l_j$) |
| Support reactions $\sum_{i=6}^9 R_{i,z}$ | $-0.089 + 1.339 - 0.089 + 1.339 = +2.500\text{ kN}$ — balances $5 \times (-0.5)\text{ kN}$ |

**Structure of D (Schek figure 4).** Building $C_s$ for the 9-node, 12-branch graph
of figure 2 and setting $q_j = j$ gives
$D _ {11} = q_1 + q_5 + q_6 + q _ {10} = 22$,
$D _ {33} = q_3 + q_7 + q_8 + q _ {12} = 30$,
$D _ {55} = q_9 + q _ {10} + q _ {11} + q _ {12} = 42$
and off-diagonals $-q_j$ exactly as printed in the paper. (Branch 5 joins nodes 1
and 4; the scanned figure is ambiguous there, but figure 4 fixes it.)

**Theorem 1.** For random anchors and random $q \in [0.5, 3]$ on that graph, the
unloaded FDM solution and a BFGS minimiser of $\sum_j q_j l_j^{2}$ agree to
$4 \times 10^{-8}$.

**Jacobian (31) and damped iteration (20 to 25).** Implemented literally for
$r = 4$ prescribed strained lengths on the same graph: the analytic $G_d^{t}$ matches
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
  $(\partial \mathbf{f}(\mathbf{x})/\partial \mathbf{x})^T = C^T U L^{-1}$ (Sec. 6.4.2,
  Eqs. 6.22–6.24), the materialization cutting-length equation
  $\mathbf{l} _ 0 = (I + (EA)^{-1} Q L)^{-1} \mathbf{l}$ (Sec. 6.5, Eqs. 6.34–6.37),
  and the scale invariance of $(\mathbf{q}, \mathbf{p})$ (Sec. 6.7, Figs. 6.9–6.11).
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
