"""A force density application written from Schek (1974), section by section.

Read it top to bottom: each cell (`# %% [id] title`) is one section of the paper, with
the paper's statement as a docstring and the code that adds that section to the program.
Running the file executes every cell in order and prints the results; `build_note.py`
turns the same cells into the tutorial in knowledge/04_form_finding/compas_fd.md, and
`build_notebook.py` builds knowledge/04_form_finding/compas_fd.ipynb.

Only numpy (and scipy.optimize in Part F) is used. Nothing here is taken from compas_fd;
the application is derived from the paper and compas_fd is compared with it afterwards.

    python examples/form_finding/schek_app.py
"""

# %% [a1] A.1 Network topology and initial node coordinates (section 2.1)
r"""Throughout this entire tutorial, we use one single running example: Schek's **9-node, 12-branch saddle cable net** (Fig. 2). We number the $n = 5$ **free inner nodes first** ($1 \dots 5$, with initial flat coordinates $\mathbf{x}_0, \mathbf{y}_0, \mathbf{z}_0$) and the $n_f = 4$ **fixed outer anchor nodes last** ($6 \dots 9$, with known support coordinates $\mathbf{x}_f, \mathbf{y}_f, \mathbf{z}_f$) across the $m = 12$ directed branches ($i \to k$).

![Fig. 2](images/schek_fig2.png)

![Part A Topology and Matrix Operators on the Cable Net](images/fd_sec_a_topology_split.png)

* **Total Nodes ($n_s = 9$):** Free inner nodes $1 \dots 5$ ($n = 5$, initial flat coordinates $\mathbf{x}_0, \mathbf{y}_0, \mathbf{z}_0$) and fixed anchors $6 \dots 9$ ($n_f = 4$, known boundary supports $\mathbf{x}_f, \mathbf{y}_f, \mathbf{z}_f$).
* **Directed Branches ($m = 12$):** Anchor cables $b_1 \dots b_4$: $(1\to 6),\ (2\to 7),\ (3\to 8),\ (4\to 9)$; inner ring $b_5 \dots b_8$: $(1\to 4),\ (1\to 2),\ (2\to 3),\ (3\to 4)$; center spokes $b_9 \dots b_{12}$: $(4\to 5),\ (1\to 5),\ (2\to 5),\ (3\to 5)$.

### Matrix Example (Initial Free-Node Coordinates $\mathbf{X}_0$ and Fixed Anchor Coordinates $\mathbf{X}_f$)

* **$\mathbf{x}_0, \mathbf{y}_0, \mathbf{z}_0$ $(5 \times 1)$:** Initial flat coordinates of the 5 free inner nodes $1 \dots 5$ ($\text{m}$).
* **$\mathbf{x}_f, \mathbf{y}_f, \mathbf{z}_f$ $(4 \times 1)$:** Known coordinates of the 4 fixed outer anchors $6 \dots 9$ ($\text{m}$).

$$
\begin{bmatrix} \mathbf{x}_0 & \mathbf{y}_0 & \mathbf{z}_0 \end{bmatrix} =
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
\begin{bmatrix} \mathbf{x}_f & \mathbf{y}_f & \mathbf{z}_f \end{bmatrix} =
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
$$"""
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


# %% [a2] A.2 Vectors, diagonal matrices, and the diagonal swap (section 1.4)
r"""In standard matrix algebra, you cannot multiply two $(12 \times 1)$ column vectors $\mathbf{u}$ and $\mathbf{q}$ element-by-element because their dimensions $(12 \times 1) \times (12 \times 1)$ do not match. To write element-by-element branch multiplication ($u_j q_j$ for each cable $j = 1 \dots 12$) as a valid matrix product, Schek places the 12 entries of $\mathbf{u}$ and $\mathbf{q}$ on the main diagonal of $(12 \times 12)$ diagonal matrices $U = \mathrm{diag}(\mathbf{u})$ and $Q = \mathrm{diag}(\mathbf{q})$.

### General Equation

$$
U = \mathrm{diag}(\mathbf{u}), \qquad Q = \mathrm{diag}(\mathbf{q}), \qquad U \mathbf{q} = Q \mathbf{u} =
\begin{bmatrix}
u_1 q_1 \\
\vdots \\
u_{12} q_{12}
\end{bmatrix}
$$

### Matrix Example (12 Branches of the 9-Node Net)

* **$\mathbf{u}$ $(12 \times 1)$ and $U = \mathrm{diag}(\mathbf{u})$ $(12 \times 12)$:** Cable $x$-coordinate differences $u_j = x_i - x_k$ ($\text{m}$) between start node $i$ and end node $k$ of each cable ($\mathbf{x}$ and $\mathbf{x}_f$ are the node $x$-coordinates; $\mathbf{u} = C\mathbf{x} + C_f\mathbf{x}_f$ is their difference per cable).
* **$\mathbf{q}$ $(12 \times 1)$ and $Q = \mathrm{diag}(\mathbf{q})$ $(12 \times 12)$:** Cable force densities $q_j = s_j / l_j$ ($\text{kN/m}$), placed as a column vector $\mathbf{q}$ or on the main diagonal of $Q$.
* **$U\mathbf{q} = Q\mathbf{u}$ $(12 \times 1)$:** Horizontal cable force components $F_{x,j} = u_j q_j$ ($\text{kN}$).

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
$$"""
u_12 = np.array([1.0, 0.0, -1.0, 0.0, -1.0, -1.0, -1.0, 1.0, 0.0, -1.0, 0.0, 1.0])
q_12 = np.array([2.0, 2.0, 2.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
U_12, Q_12 = np.diag(u_12), np.diag(q_12)         # (12, 12) diagonal matrices from (12,) vectors
print("U @ q == Q @ u (12 branches):", (U_12 @ q_12).astype(int))


# %% [a3] A.3 Branch-node connectivity matrix and partitioning (section 2.1)
r"""Encode the 9-node, 12-branch directed graph as a $(12 \times 9)$ branch-node incidence matrix $C_s$ ($+1$ at start node $i$, $-1$ at end node $k$), partitioned into free-node columns $C$ $(12 \times 5)$ and fixed-anchor columns $C_f$ $(12 \times 4)$.

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

* **$C_s$ $(12 \times 9)$:** Full branch-node connectivity matrix (12 rows $b_1 \dots b_{12}$ for cables; 9 columns $n_1 \dots n_9$ for nodes; $+1$ at start node $i$, $-1$ at end node $k$).
* **$C$ $(12 \times 5)$:** Left block of $C_s$ (columns $n_1 \dots n_5$ for the 5 free inner nodes).
* **$C_f$ $(12 \times 4)$:** Right block of $C_s$ (columns $n_6 \dots n_9$ for the 4 fixed anchors).

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
$$"""
C_s: FloatMatrix = np.zeros((m, n + n_f))
for j, (i, k) in enumerate(branches):
    C_s[j, i - 1] = +1.0              # start node i(j): +1 (0-based index)
    C_s[j, k - 1] = -1.0              # end node k(j): -1
C: FloatMatrix = C_s[:, :n]           # (12, 5) first 5 columns -> free nodes 1..5
C_f: FloatMatrix = C_s[:, n:]         # (12, 4) last 4 columns  -> fixed anchors 6..9
print("C_s (12x9):\n", C_s.astype(int))


# %% [a4] A.4 Step-by-step matrix multiplication for $D = C^T Q C$ on the 9-node network
r"""Trace how $D = C^T (Q C)$ assembles the $(5 \times 5)$ nodal equilibrium matrix directly on our **9-node, 12-branch network** with force densities $\mathbf{q} = [2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1]^T$.

### 1. Free Connectivity $C\ (12 \times 5)$ and Transpose $C^T\ (5 \times 12)$

* **$C$ $(12 \times 5)$:** Free-node connectivity matrix (maps 5 free-node coordinates to 12 cables).
* **$C^T$ $(5 \times 12)$:** Transpose of $C$ (sums 12 cable forces at each of the 5 free nodes).
* **$Q$ $(12 \times 12)$:** Diagonal force-density matrix $\mathrm{diag}(q_1, \dots, q_{12})$ ($\text{kN/m}$).
* **$D = C^T Q C$ $(5 \times 5)$:** Free-node stiffness matrix ($D_{ii} = \sum q_j$ at node $i$; $D_{ik} = -q_j$ between nodes $i, k$).

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
$$"""
QC = Q_12 @ C                         # (12, 5) weight each branch row j by q_j
D_preview = C.T @ QC                  # (5, 5)  sum weighted branch rows at each free node
print("D = C.T @ diag(q) @ C (5x5):\n", D_preview.astype(int))


# %% [b1] B.1 Inputs: external nodal loads and initial cable tensions (section 2.2)
r"""Along with the initial free-node coordinates $(\mathbf{x}_0, \mathbf{y}_0, \mathbf{z}_0)$ and fixed-anchor coordinates $(\mathbf{x}_f, \mathbf{y}_f, \mathbf{z}_f)$ defined in A.1, we specify the external vertical loads $(\mathbf{p}_x, \mathbf{p}_y, \mathbf{p}_z)$ at the 5 free nodes ($-0.5\text{ kN}$ each, $+z$ up) and the initial cable tension vector $\mathbf{s}_0$ ($1.0\text{ kN}$ in each of the 12 branches).

### Matrix Example (External Loads $\mathbf{P}$ and Initial Tensions $\mathbf{s}_0$)

* **$\mathbf{p}_x, \mathbf{p}_y, \mathbf{p}_z$ $(5 \times 1)$:** External nodal loads along $x, y, z$ at the 5 free nodes $1 \dots 5$ ($\text{kN}$).
* **$\mathbf{s}_0$ $(12 \times 1)$:** Initial axial tension force in each of the 12 cables $b_1 \dots b_{12}$ ($\text{kN}$).

$$
\begin{bmatrix} \mathbf{p}_x & \mathbf{p}_y & \mathbf{p}_z \end{bmatrix} =
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
\mathbf{s}_0 =
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
$$"""
p_x: FloatVector = np.zeros(n, dtype=np.float64)  # (5,) x-loads at free nodes 1..5 (kN)
p_y: FloatVector = np.zeros(n, dtype=np.float64)  # (5,) y-loads at free nodes 1..5 (kN)
p_z: FloatVector = np.full(n, -0.5, dtype=np.float64)  # (5,) z-loads at free nodes 1..5 (-0.5 kN)
s_0: FloatVector = np.ones(m, dtype=np.float64)   # (12,) initial 1.0 kN tension in cables 1..12
print("External loads [p_x, p_y, p_z] (5x3):\n", np.c_[p_x, p_y, p_z])
print("Initial cable tensions s_0 (12,):", s_0)


# %% [b2] B.2 Coordinate differences and cable lengths, equation (1)
r"""For each branch $j\ (i \to k)$, compute the coordinate differences $(u_j, v_j, w_j) = (x_i - x_k,\ y_i - y_k,\ z_i - z_k)$ and the Euclidean cable length $l_j$ from the initial free-node coordinates $(\mathbf{x}_0, \mathbf{y}_0, \mathbf{z}_0)$ and fixed-anchor coordinates $(\mathbf{x}_f, \mathbf{y}_f, \mathbf{z}_f)$ defined in A.1.

![Section B.2 Geometric Meaning of Coordinate Differences u, v, w and Cable Length l](images/fd_sec_b2_uvw_geometry.png)

### General Equations (Eq. 1)

$$
\mathbf{u} = C \mathbf{x}_0 + C_f \mathbf{x}_f, \qquad
\mathbf{v} = C \mathbf{y}_0 + C_f \mathbf{y}_f, \qquad
\mathbf{w} = C \mathbf{z}_0 + C_f \mathbf{z}_f, \qquad
l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}
$$

### Matrix Example (Initial Coordinates $\mathbf{x}_0 = [-1, 0, 1, 0, 0]^T,\ \mathbf{y}_0 = [0, -1, 0, 1, 0]^T,\ \mathbf{z}_0 = \mathbf{0}$)

* **$\mathbf{x}_0, \mathbf{y}_0, \mathbf{z}_0$ $(5 \times 1)$:** Initial coordinates of free nodes $1 \dots 5$ ($\text{m}$, from A.1).
* **$\mathbf{x}_f, \mathbf{y}_f, \mathbf{z}_f$ $(4 \times 1)$:** Fixed-anchor coordinates of nodes $6 \dots 9$ ($\text{m}$, from A.1).
* **$C$ $(12 \times 5)$ and $C_f$ $(12 \times 4)$:** Free-node and fixed-anchor connectivity matrices (from A.3).
* **$\mathbf{u}, \mathbf{v}, \mathbf{w}$ $(12 \times 1)$:** Cable coordinate differences $u_j = x_i - x_k,\ v_j = y_i - y_k,\ w_j = z_i - z_k$ ($\text{m}$).
* **$\mathbf{l}$ $(12 \times 1)$ and $L^{-1}$ $(12 \times 12)$:** Cable lengths $l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}$ ($\text{m}$) and diagonal inverse-length matrix $\mathrm{diag}(1/\mathbf{l})$ ($\text{m}^{-1}$).

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
\underset{\mathbf{x}_0\ (5\times 1)}{\begin{bmatrix}
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
\underset{\mathbf{x}_f\ (4\times 1)}{\begin{bmatrix}
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
$$"""
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


# %% [b3] B.3 Nonlinear equilibrium in 4 stages, equation (2)
r"""From a single cable's tension $s_j$ and length $l_j$, we derive the 4-stage matrix equilibrium equation $\mathbf{e}_x = C^T U L^{-1} \mathbf{s} - \mathbf{p}_x$, reading the matrix product **right to left** from Stage 1 to Stage 4.

![Section B.3 Four-Stage Nonlinear Equilibrium and Flat Net Imbalance](images/fd_sec_b3_nonlinear_stages.png)

### How Stages 1–4 Are Derived (From One Cable to Matrix Form, Eq. 2)

1. **Single cable $j\ (i \to k)$:** Cable $j$ pulls with axial tension $s_j$ ($\text{kN}$) along its 3D length $l_j$ ($\text{m}$). By similar triangles, its direction cosine along $x$ is $u_j / l_j = (x_i - x_k) / l_j$, so its horizontal force component is:

$$
F_{x,j} = s_j \frac{u_j}{l_j} = u_j \underbrace{\left(\frac{s_j}{l_j}\right)}_{\text{Stage 1: } q_j}
$$

2. **All 12 cables in matrix form (Stages 1 & 2):** Using the diagonal matrices $L^{-1} = \mathrm{diag}(1/l_1, \dots, 1/l_{12})$ and $U = \mathrm{diag}(u_1, \dots, u_{12})$:
   * **Stage 1:** $\mathbf{q} = L^{-1} \mathbf{s}\ (12 \times 1)$ divides each cable's tension $s_j$ by its length $l_j$ ($q_j = s_j / l_j$).
   * **Stage 2:** $\mathbf{F}_x = U \mathbf{q} = U L^{-1} \mathbf{s}\ (12 \times 1)$ multiplies each cable's ratio $q_j$ by its span $u_j$ ($F_{x,j} = u_j q_j$).
3. **Force balance at the 5 free nodes (Stages 3 & 4):** Row $i$ of $C^T\ (5 \times 12)$ has $+1$ for cables starting at node $i$ and $-1$ for cables ending at node $i$, so multiplying by $C^T$ sums the cable forces at each free node $i = 1 \dots 5$, and subtracting external load $\mathbf{p}_x\ (5 \times 1)$ gives the out-of-balance residual:

$$
\mathbf{e}_x = \underbrace{C^T}_{\text{Stage 3: sum at nodes } (5\times 12)} \quad \underbrace{U}_{\text{Stage 2: project } x\ (12\times 12)} \quad \underbrace{L^{-1} \mathbf{s}}_{\text{Stage 1: } q_j = s_j / l_j\ (12\times 1)} \quad - \quad \underbrace{\mathbf{p}_x}_{\text{Stage 4: load } (5\times 1)}
$$

---

### Stage-by-Stage Matrix Breakdown (Flat Trial Net with $s_j = 1\text{ kN}$)

#### Stage 1 — Force Density Ratios: $\mathbf{q} = L^{-1} \mathbf{s}\ (12 \times 1)$

* **$L^{-1}$ $(12 \times 12)$:** Diagonal inverse-length matrix $\mathrm{diag}(1/l_1, \dots, 1/l_{12})$ ($\text{m}^{-1}$).
* **$\mathbf{s}$ $(12 \times 1)$:** Trial axial cable tensions $s_j$ ($\text{kN}$).
* **$\mathbf{q} = L^{-1}\mathbf{s}$ $(12 \times 1)$:** Force-to-length ratios $q_j = s_j / l_j$ ($\text{kN/m}$).

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

#### Stage 2 — Projected Branch Force Components: $\mathbf{F}_x = U \mathbf{q},\ \mathbf{F}_y = V \mathbf{q},\ \mathbf{F}_z = W \mathbf{q}\ (12 \times 1)$

* **$U, V, W$ $(12 \times 12)$:** Diagonal matrices $\mathrm{diag}(\mathbf{u}),\ \mathrm{diag}(\mathbf{v}),\ \mathrm{diag}(\mathbf{w})$ holding the 12 cable coordinate differences $u_j = x_i - x_k,\ v_j = y_i - y_k,\ w_j = z_i - z_k$ ($\text{m}$) from Section B.2 ($\mathbf{u} = C\mathbf{x} + C_f\mathbf{x}_f$).
* **$\mathbf{q}$ $(12 \times 1)$:** Cable force-density vector $q_j = s_j / l_j$ ($\text{kN/m}$) from Stage 1.
* **$\mathbf{F}_x, \mathbf{F}_y, \mathbf{F}_z$ $(12 \times 1)$:** Directed cable force components $F_{x,j} = u_j q_j,\ F_{y,j} = v_j q_j,\ F_{z,j} = w_j q_j$ along $x, y, z$ ($\text{kN}$).

$$
\mathbf{F}_x = U \mathbf{q} =
\underset{U = \mathrm{diag}(\mathbf{u})\ (12\times 12)}{\begin{bmatrix}
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

Similarly along $y$ ($\mathbf{F}_y = V \mathbf{q}$) and $z$ ($\mathbf{F}_z = W \mathbf{q}$):

$$
\mathbf{F}_y = V \mathbf{q} =
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
\mathbf{F}_z = W \mathbf{q} =
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

#### Stage 3 — Sum Cable Forces at Free Nodes: $C^T \mathbf{F}_x,\ C^T \mathbf{F}_y,\ C^T \mathbf{F}_z\ (5 \times 1)$

* **$C^T$ $(5 \times 12)$:** Transpose of the free-node connectivity matrix (row $i$ has $+1$ for cables starting at node $i$ and $-1$ for cables ending at node $i$).
* **$\mathbf{F}_x, \mathbf{F}_y, \mathbf{F}_z$ $(12 \times 1)$:** Cable force components from Stage 2 ($\text{kN}$).
* **$C^T \mathbf{F}_x, C^T \mathbf{F}_y, C^T \mathbf{F}_z$ $(5 \times 1)$:** Net internal cable force resultant at each of the 5 free nodes ($\text{kN}$).

$$
C^T \mathbf{F}_x =
\underset{C^T\ (5\times 12)}{\begin{bmatrix}
1 & 0 & 0 & 0 & 1 & 1 & 0 & 0 & 0 & 1 & 0 & 0 \\
0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 \\
0 & 0 & 0 & 1 & -1 & 0 & 0 & -1 & 1 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & -1 & -1 & -1 & -1
\end{bmatrix}}
\underset{\mathbf{F}_x\ (12\times 1)}{\begin{bmatrix}
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
C^T \mathbf{F}_y =
\underset{C^T\ (5\times 12)}{\begin{bmatrix}
1 & 0 & 0 & 0 & 1 & 1 & 0 & 0 & 0 & 1 & 0 & 0 \\
0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 1 & 0 & 0 & 0 & -1 & 1 & 0 & 0 & 0 & 1 \\
0 & 0 & 0 & 1 & -1 & 0 & 0 & -1 & 1 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & -1 & -1 & -1 & -1
\end{bmatrix}}
\underset{\mathbf{F}_y\ (12\times 1)}{\begin{bmatrix}
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
C^T \mathbf{F}_z =
\begin{bmatrix}
0 \\
-0.316 \\
0 \\
-0.316 \\
0
\end{bmatrix}\text{ kN}
$$

#### Stage 4 — Subtract Applied Loads to Check Equilibrium: $\mathbf{e} = C^T \mathbf{F} - \mathbf{p}\ (5 \times 1)$

* **$C^T \mathbf{F}_x, C^T \mathbf{F}_y, C^T \mathbf{F}_z$ $(5 \times 1)$:** Internal cable force resultants at free nodes $1 \dots 5$ ($\text{kN}$).
* **$\mathbf{p}_x, \mathbf{p}_y, \mathbf{p}_z$ $(5 \times 1)$:** External applied nodal loads at free nodes $1 \dots 5$ ($\text{kN}$).
* **$\mathbf{e}_x, \mathbf{e}_y, \mathbf{e}_z$ $(5 \times 1)$:** Out-of-balance nodal force residuals ($\text{kN}$; zero when in equilibrium).

$$
\mathbf{e}_x =
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
\mathbf{e}_y =
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
\mathbf{e}_z =
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
$$"""
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


# %% [c1] C.1 The force density trick and the diagonal swap, equations (4) to (6)
r"""In Section B.3, the horizontal branch force $F_{x,j} = s_j (u_j / l_j)$ was nonlinear because the unknown length $l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}$ sat in the denominator. If instead we prescribe the **force density** $q_j = s_j / l_j$ ($\text{kN/m}$, so $s_j = q_j l_j$), then $l_j$ in the numerator and denominator cancels out: $F_{x,j} = (q_j l_j)(u_j / l_j) = q_j u_j$.

![Section C.1 How Force Density Uses Coordinate Difference u to Linearize Equilibrium](images/fd_sec_c1_force_density_trick.png)

### General Equations (Eqs. 4–6) & Meaning of $u$

$$
q_j = \frac{s_j}{l_j} \quad (\mathbf{q} = L^{-1} \mathbf{s})
\qquad \Longrightarrow \qquad
F_{x, j} = s_j \frac{u_j}{l_j} = (q_j l_j) \frac{u_j}{l_j} = q_j u_j = q_j (x_i - x_k)
$$

$$
C^T U \mathbf{q} = C^T Q \mathbf{u} = \mathbf{p}_x, \qquad
C^T V \mathbf{q} = C^T Q \mathbf{v} = \mathbf{p}_y, \qquad
C^T W \mathbf{q} = C^T Q \mathbf{w} = \mathbf{p}_z
$$

* **$u_j$, $\mathbf{u}$ $(12 \times 1)$, and $U = \mathrm{diag}(\mathbf{u})$ $(12 \times 12)$:** $u_j = x_i - x_k$ is the $x$-coordinate difference ($\text{m}$) between start node $i$ and end node $k$ of branch $j$ (similarly $v_j = y_i - y_k$ in $V$, $w_j = z_i - z_k$ in $W$).
* **Why we swap $U \mathbf{q} = Q \mathbf{u}$:** moves the **unknown** coordinate vector $\mathbf{u}$ to the right of the **known** diagonal force-density matrix $Q = \mathrm{diag}(\mathbf{q})$.

### Matrix Example ($\mathbf{F}_x = U \mathbf{q} = Q \mathbf{u}$ on All 12 Branches)

* **$U = \mathrm{diag}(\mathbf{u})$ $(12 \times 12)$ and $\mathbf{u}$ $(12 \times 1)$:** Unknown cable $x$-coordinate differences $u_j = x_i - x_k$ ($\text{m}$).
* **$Q = \mathrm{diag}(\mathbf{q})$ $(12 \times 12)$ and $\mathbf{q}$ $(12 \times 1)$:** Known prescribed cable force densities $q_j$ ($\text{kN/m}$).
* **$\mathbf{F}_x = U\mathbf{q} = Q\mathbf{u}$ $(12 \times 1)$:** Linearized horizontal cable force components $q_j(x_i - x_k)$ ($\text{kN}$).

$$
\mathbf{F}_x =
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
$$"""
# 2 kN/m on the 4 outer anchor cables (0..3), 1 kN/m on the 8 inner cables (4..11)
q = np.array([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1], dtype=float)
print("Prescribed force densities q (kN/m):", q)


# %% [c2] C.2 System matrices $D$ and $D_f$, equations (7) and (8)
r"""Substituting $\mathbf{u} = C \mathbf{x} + C_f \mathbf{x}_f$ into $C^T Q \mathbf{u} = \mathbf{p}_x$ separates unknown free-node coordinates $\mathbf{x}$ from known anchor coordinates $\mathbf{x}_f$ via $D = C^T Q C\ (5 \times 5)$ and $D_f = C^T Q C_f\ (5 \times 4)$.

![Sections C.2 to D.1 Physical Meaning of D and Solved 3D Saddle Equilibrium Net](images/fd_sec_c2_c3_solved_net.png)

### General Equations (Eqs. 7–8)

$$
(C^T Q C)\mathbf{x} + (C^T Q C_f)\mathbf{x}_f = \mathbf{p}_x
\qquad \Longrightarrow \qquad
D \mathbf{x} = \mathbf{p}_x - D_f \mathbf{x}_f = \mathbf{b}_x
$$

### 1. Symbolic Structure of $D$ and Schek Fig. 4 ($q_j = j$)

* **$D = C^T Q C$ $(5 \times 5)$:** Free-node stiffness matrix (diagonal $D_{ii}$ sums $q_j$ of cables touching free node $i$; off-diagonal $D_{ik} = -q_j$ for cable $j$ between free nodes $i$ and $k$).
* **$D_f = C^T Q C_f$ $(5 \times 4)$:** Fixed-anchor coupling matrix ($D_{f(i,k)} = -q_j$ if cable $j$ connects free node $i$ to fixed anchor $k$).
* **$\mathbf{p}_z$ $(5 \times 1)$ and $\mathbf{z}_f$ $(4 \times 1)$:** External vertical loads ($\text{kN}$) and known anchor heights ($\text{m}$).
* **$\mathbf{b}_z = \mathbf{p}_z - D_f \mathbf{z}_f$ $(5 \times 1)$:** Known right-hand side vector combining external loads and anchor pull ($\text{kN}$).

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

### 2. Actual Matrices $D$, $D_f$, and Right-Hand Side $\mathbf{b}_z = \mathbf{p}_z - D_f \mathbf{z}_f$

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
\mathbf{b}_z = \mathbf{p}_z - D_f \mathbf{z}_f =
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
$$"""
Q = np.diag(q)                                  # (12, 12) diagonal force-density matrix
D = C.T @ Q @ C                                 # (5, 5)   free-node stiffness matrix, eq. (8)
D_f = C.T @ Q @ C_f                             # (5, 4)   fixed-anchor coupling matrix, eq. (8)
rhs = np.c_[p_x - D_f @ x_f, p_y - D_f @ y_f, p_z - D_f @ z_f]  # (5, 3) right-hand sides [b_x, b_y, b_z]
print("D (5x5):\n", D)
print("D_f (5x4):\n", D_f)
print("RHS [b_x, b_y, b_z] (5x3):\n", rhs)


# %% [c3] C.3 Direct linear solve for free node coordinates, equation (9)
r"""Because $D = C^T Q C$ is constant and symmetric positive-definite, solving $D \mathbf{x} = \mathbf{b}_x$, $D \mathbf{y} = \mathbf{b}_y$, $D \mathbf{z} = \mathbf{b}_z$ gives the exact 3D equilibrium coordinates in one direct step.

### General Equations (Eq. 9)

$$
D \mathbf{x} = \mathbf{p}_x - D_f \mathbf{x}_f, \qquad
D \mathbf{y} = \mathbf{p}_y - D_f \mathbf{y}_f, \qquad
D \mathbf{z} = \mathbf{p}_z - D_f \mathbf{z}_f
$$

### Matrix Example (Vertical Equilibrium Solve $D \mathbf{z} = \mathbf{b}_z$ and 3D Coordinates)

* **$D$ $(5 \times 5)$:** Symmetric positive-definite free-node stiffness matrix ($\text{kN/m}$).
* **$\mathbf{b}_z$ $(5 \times 1)$:** Known vertical right-hand side $\mathbf{p}_z - D_f \mathbf{z}_f$ ($\text{kN}$).
* **$\mathbf{x}, \mathbf{y}, \mathbf{z}$ $(5 \times 1)$:** Solved equilibrium coordinates of the 5 free nodes $1 \dots 5$ ($\text{m}$).

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
\underset{\mathbf{b}_z\ (5\times 1)}{\begin{bmatrix}
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
$$"""
x: FloatVector = np.linalg.solve(D, p_x - D_f @ x_f)    # (5,) solve D x = b_x, eq. (9)
y: FloatVector = np.linalg.solve(D, p_y - D_f @ y_f)    # (5,) solve D y = b_y, eq. (9)
z: FloatVector = np.linalg.solve(D, p_z - D_f @ z_f)    # (5,) solve D z = b_z, eq. (9)
print("Solved free-node coordinates [x, y, z] (5x3):\n", np.c_[x, y, z])


# %% [c4] C.4 Recovering cable lengths, forces, materialization cutting lengths, and verification, equation (10)
r"""From the solved coordinates $(\mathbf{x}, \mathbf{y}, \mathbf{z})$, we recompute branch lengths $\mathbf{l}$, recover branch tensions $\mathbf{s} = Q \mathbf{l}$, and compute unstressed cutting lengths $l_{0,j} = l_j / (1 + s_j / EA_j)$.

### General Equations (Schek Eq. 10 & Linkwitz Eq. 6.37)

$$
s_j = q_j l_j \quad (\mathbf{s} = Q \mathbf{l} = L \mathbf{q}), \qquad
\mathbf{e}_x = C^T U L^{-1} \mathbf{s} - \mathbf{p}_x = \mathbf{0}, \qquad
l_{0,j} = \frac{l_j}{1 + s_j / EA_j}
$$

### Matrix Example ($\mathbf{q}$, $\mathbf{l}$, $\mathbf{s}$, and Cutting Lengths $\mathbf{l}_0$ for $EA = 500\text{ kN}$)

* **$\mathbf{q}$ $(12 \times 1)$:** Prescribed cable force densities $q_j$ ($\text{kN/m}$).
* **$\mathbf{l}$ $(12 \times 1)$:** Solved stressed equilibrium cable lengths $l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}$ ($\text{m}$).
* **$\mathbf{s} = \mathbf{q} \odot \mathbf{l}$ $(12 \times 1)$:** Recovered axial cable tensions $s_j = q_j l_j$ ($\text{kN}$).
* **$EA_j = E_j A_j$:** Cable axial stiffness ($\text{kN}$, Young's modulus $E_j$ times cross-sectional area $A_j$).
* **$\mathbf{l}_0$ $(12 \times 1)$ and $e_j = l_j - l_{0,j}$:** Unstressed workshop cutting lengths $l_{0,j} = l_j / (1 + s_j / EA_j)$ ($\text{m}$) and elastic stretch $e_j$ ($\text{mm}$).

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
\underset{\mathbf{l}_0\ (\text{m})}{\begin{bmatrix}
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
$$"""
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


# %% [d1] D.1 Complete linear form-finding function and support reactions (figure 3)
r"""We package Steps A.3–C.4 into `form_finding` and compute the 3D support reactions $\mathbf{R}_f = C_f^T Q \mathbf{U}_{xyz}$ at the 4 fixed anchors.

![Fig. 3](images/schek_fig3.png)

### General Equations

$$
D \mathbf{X} = \mathbf{P} - D_f \mathbf{X}_f, \qquad
\mathbf{U}_{xyz} = C \mathbf{X} + C_f \mathbf{X}_f, \qquad
\mathbf{R}_f = C_f^T Q \mathbf{U}_{xyz}
$$

### Matrix Example (Support Reactions $\mathbf{R}_f$)

* **$C_f^T$ $(4 \times 12)$:** Transpose of the fixed-anchor connectivity matrix.
* **$Q$ $(12 \times 12)$:** Diagonal force-density matrix $\mathrm{diag}(\mathbf{q})$ ($\text{kN/m}$).
* **$\mathbf{U}_{xyz} = [\mathbf{u}, \mathbf{v}, \mathbf{w}]$ $(12 \times 3)$:** Table of cable coordinate differences along $x, y, z$ ($\text{m}$).
* **$\mathbf{R}_f = C_f^T Q \mathbf{U}_{xyz}$ $(4 \times 3)$:** Support reaction forces $(R_{ix}, R_{iy}, R_{iz})$ at the 4 fixed anchors $6 \dots 9$ ($\text{kN}$).

$$
\mathbf{R}_f = C_f^T Q \mathbf{U}_{xyz} =
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
$$"""
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


# %% [d2] D.2 Parameter study: moving anchors, changing force densities, and scale invariance
r"""Moving anchors $\mathbf{X}_f$ only updates the right-hand side, changing $\mathbf{q}$ rebuilds $D$, and scaling $(2\mathbf{q}, 2\mathbf{P})$ leaves the 3D geometry identical while doubling forces (scale invariance).

![Parts D, E and F Parameter Study, Energy Minimization and Target Length Constraints](images/fd_sec_e_f_constraints.png)

### Matrix Example (Free-Node Heights $\mathbf{z}$ Across 4 Cases)

* **$\mathbf{z}_{\text{case 1..4}}$ $(5 \times 1)$:** Equilibrium heights $z_1 \dots z_5$ of the 5 free nodes ($\text{m}$) for each of the 4 parameter cases.
* **$\mathbf{s}_{\text{case 1}}, \mathbf{s}_{\text{case 4}}$ $(12 \times 1)$:** Cable tension vectors ($\text{kN}$) before and after scaling $(2\mathbf{q}, 2\mathbf{P})$.

$$
\begin{bmatrix}
\mathbf{z}_{\text{case 1}} & \mathbf{z}_{\text{case 2}} & \mathbf{z}_{\text{case 3}} & \mathbf{z}_{\text{case 4}}
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
\mathbf{s}_{\text{case 4}} = 2\mathbf{s}_{\text{case 1}}
$$

| Case | Matrix $D\ (5\times 5)$ | RHS $\mathbf{P} - D_f \mathbf{X}_f$ | Center Height $z_5\ (\text{m})$ | Max Force $\max(\mathbf{s})$ |
|---|---|---|---|---|
| **1. Base case** ($q_{\text{anchor}} = 2,\ \mathbf{p}_z = -0.5$) | built once | base | $0.063\text{ m}$ | $2.748\text{ kN}$ |
| **2. All anchors lifted** $+1\text{ m}$ | **unchanged** | updated | $1.063\text{ m}$ | $2.748\text{ kN}$ |
| **3. Stiffer anchors** ($q_{\text{anchor}} = 10,\ \mathbf{p}_z = -0.5$) | **rebuilt** | updated | $0.313\text{ m}$ | $4.732\text{ kN}$ |
| **4. Scale invariance** ($2\mathbf{q},\ 2\mathbf{p}_z$) | $2\times$ | $2\times$ | **$0.063\text{ m}$** | **$5.496\text{ kN}$ ($2\times$)** |"""
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


# %% [e1] E.1 Geometric meaning of force densities (section 4)
r"""For an unloaded network ($\mathbf{P} = \mathbf{0}$), solving $D\mathbf{X} = -D_f\mathbf{X}_f$ minimizes the weighted squared-length functional $\Phi = \sum q_j l_j^2$ (Theorem 1), and setting $q_j = c / l_j$ produces a constant-force net $s_j = c$ (Theorem 2).

### General Equations (Eqs. 37–40)

$$
\Phi(\mathbf{x}, \mathbf{y}, \mathbf{z}) = \mathbf{u}^T Q \mathbf{u} + \mathbf{v}^T Q \mathbf{v} + \mathbf{w}^T Q \mathbf{w} = \sum_{j=1}^m q_j l_j^2 \longrightarrow \min
\qquad \Longleftrightarrow \qquad
\frac{\partial \Phi}{\partial \mathbf{x}} = 2 C^T Q \mathbf{u} = 2 (D \mathbf{x} + D_f \mathbf{x}_f) = \mathbf{0}
$$

### Matrix Example (Unloaded Saddle $\mathbf{P} = \mathbf{0}$)

* **$\mathbf{X}_0 = [\mathbf{x}_0, \mathbf{y}_0, \mathbf{z}_0]$ $(5 \times 3)$:** Equilibrium coordinates of the 5 free nodes when external load $\mathbf{P} = \mathbf{0}$ ($\text{m}$).
* **$\mathbf{U}_0 = C\mathbf{X}_0 + C_f\mathbf{X}_f$ $(12 \times 3)$:** Cable coordinate differences in the unloaded saddle ($\text{m}$).
* **$\Phi = \sum q_j l_j^2$ and $\nabla\Phi(\mathbf{X}_0)$ $(5 \times 3)$:** Weighted squared-length energy functional and its gradient $2 C^T Q \mathbf{U}_0$ at equilibrium.

$$
\mathbf{X}_0 = \begin{bmatrix}
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
\nabla \Phi(\mathbf{X}_0) = 2 C^T Q \mathbf{U}_0 = \mathbf{0}_{5\times 3}
$$"""
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


# %% [f1] F.1 Target length and force constraints, equation (11)
r"""To enforce target equilibrium branch lengths $\mathbf{l}_v$ or forces $\mathbf{s}_v$, we form the residual vector $\mathbf{g}^{\ast}(\mathbf{q})$ and solve for $\mathbf{q}^{\ast} \gt \mathbf{0}$ such that $\mathbf{g}^{\ast}(\mathbf{q}^{\ast}) = \mathbf{0}$.

### General Equation (Eq. 11)

$$
\mathbf{g}^{\ast}(\mathbf{q}) = \begin{bmatrix}
\mathbf{l}_{\text{constrained}}(\mathbf{q}) - \mathbf{l}_v \\
\mathbf{s}_{\text{constrained}}(\mathbf{q}) - \mathbf{s}_v
\end{bmatrix} = \mathbf{0}
$$

### Matrix Example (Target Anchor Length $l_{1..4} = 1.200\text{ m}$)

* **$\mathbf{l}_{1..4}(\mathbf{q})$ $(4 \times 1)$:** Current equilibrium lengths of the 4 anchor cables $b_1 \dots b_4$ ($\text{m}$).
* **$\mathbf{l}_v$ $(4 \times 1)$:** Prescribed target lengths for those 4 anchor cables ($1.200\text{ m}$).
* **$\mathbf{g}^{\ast}(\mathbf{q}) = \mathbf{l}_{1..4}(\mathbf{q}) - \mathbf{l}_v$ $(4 \times 1)$:** Length constraint residual vector ($\text{m}$; zero when targets are met).

$$
\mathbf{g}^{\ast}(\mathbf{q}) =
\underset{\mathbf{l}_{1..4}(\mathbf{q})}{\begin{bmatrix}
1.201 \\
1.374 \\
1.201 \\
1.374
\end{bmatrix}} -
\underset{\mathbf{l}_v}{\begin{bmatrix}
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
$$"""
length_rows = [0, 1, 2, 3]                    # the four anchor branches
target_lengths = np.full(4, 1.2)              # target length 1.2 m on each
g_lengths = l[length_rows] - target_lengths   # constraint residual vector
print("Initial anchor lengths (m):", l[length_rows])
print("Length residual g*(q) (m): ", g_lengths)


# %% [f2] F.2 Iterative solver for prescribed lengths and forces (sections 3.1 to 3.6)
r"""At each iteration, we run `form_finding(q)` and update $\mathbf{q} \gt \mathbf{0}$ via least squares until the constraint residual $\mathbf{g}^{\ast}(\mathbf{q}^{\ast})$ vanishes.

### Iteration Loop

$$
\mathbf{q}^{(k)} \xrightarrow{D(\mathbf{q}^{(k)})\mathbf{X} = \mathbf{B}} \mathbf{l}(\mathbf{q}^{(k)}),\ \mathbf{s}(\mathbf{q}^{(k)}) \xrightarrow{\text{residual}} \mathbf{g}^{\ast}(\mathbf{q}^{(k)}) \xrightarrow{\Delta\mathbf{q}} \mathbf{q}^{(k+1)}
$$

### Matrix Example (Before vs. After on Anchor Cables 1–4)

* **$\mathbf{q}_{1..4}^{(0)}$ and $\mathbf{l}_{1..4}^{(0)}$ $(4 \times 1)$:** Initial force densities ($\text{kN/m}$) and resulting initial lengths ($\text{m}$) of anchor cables $1 \dots 4$.
* **$\mathbf{q}_{1..4}^{\ast}$ and $\mathbf{l}_{1..4}^{\ast}$ $(4 \times 1)$:** Optimized force densities ($\text{kN/m}$) and achieved target lengths ($1.200\text{ m}$) after least-squares convergence.

$$
\text{Initial:}\quad
\mathbf{q}_{1..4}^{(0)} =
\begin{bmatrix}
2.000 \\
2.000 \\
2.000 \\
2.000
\end{bmatrix}\text{ kN/m},
\quad
\mathbf{l}_{1..4}^{(0)} =
\begin{bmatrix}
1.201 \\
1.374 \\
1.201 \\
1.374
\end{bmatrix}\text{ m}
\qquad \longrightarrow \qquad
\text{Solved:}\quad
\mathbf{q}_{1..4}^{\ast} =
\begin{bmatrix}
1.972 \\
2.412 \\
1.972 \\
2.412
\end{bmatrix}\text{ kN/m},
\quad
\mathbf{l}_{1..4}^{\ast} =
\begin{bmatrix}
1.200 \\
1.200 \\
1.200 \\
1.200
\end{bmatrix}\text{ m}
$$"""
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


# %% [f3] F.3 Sensitivity Jacobian $G^T = \partial \mathbf{g}^{\ast} / \partial \mathbf{q}$ (sections 3.2 to 3.5)
r"""Differentiating $C^T Q \mathbf{u}(\mathbf{q}) = \mathbf{p}_x$ with respect to $\mathbf{q}$ gives the node sensitivity $\partial \mathbf{x} / \partial \mathbf{q} = -D^{-1} C^T U$ and the constraint Jacobian $G^T = \partial \mathbf{g}^{\ast} / \partial \mathbf{q}$.

### General Equations (Eqs. 28 & 31)

$$
\frac{\partial \mathbf{x}}{\partial \mathbf{q}} = -D^{-1} C^T U, \qquad
\frac{\partial \mathbf{y}}{\partial \mathbf{q}} = -D^{-1} C^T V, \qquad
\frac{\partial \mathbf{z}}{\partial \mathbf{q}} = -D^{-1} C^T W, \qquad
G^T = \frac{\partial \mathbf{g}^{\ast}}{\partial \mathbf{q}}
$$

### Matrix Example (Anchor Length Jacobian $G^T_{1..4,\ 1..4}$ and Height Sensitivity $\partial \mathbf{z} / \partial \mathbf{q}_{1..4}$)

* **$G^T_{1..4,\ 1..4} = \partial \mathbf{l}_{1..4} / \partial \mathbf{q}_{1..4}$ $(4 \times 4)$:** Sensitivity Jacobian entry $(r, j)$ giving how much anchor cable length $l_r$ ($\text{m}$) changes per unit change in force density $q_j$ ($\text{kN/m}$).
* **$\partial \mathbf{z} / \partial \mathbf{q}_{1..4} = -D^{-1} C^T W_{:, 1..4}$ $(5 \times 4)$:** Node height sensitivity entry $(i, j)$ giving how much free node height $z_i$ ($\text{m}$) changes per unit change in anchor force density $q_j$ ($\text{kN/m}$).

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
\frac{\partial \mathbf{z}}{\partial \mathbf{q}_{1..4}} = -D^{-1} C^T W_{:, 1..4} =
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
$$"""
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

