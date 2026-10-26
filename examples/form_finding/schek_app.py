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

# %% [a1] A.1 Vectors, matrices, and the diagonal trick (section 1.4)
r"""To multiply cable-by-cable across all $m = 12$ cables without loops (e.g., multiplying each cable's coordinate span $u_j$ by its force density $q_j$ to get horizontal force $F_{x,j} = u_j q_j$), Schek (1974, Sec. 1.4) and Linkwitz (2014, Eq. 6.21) use a **case convention**:
* **Lowercase bold letter** $\mathbf{u}, \mathbf{v}, \mathbf{w}, \mathbf{l}, \mathbf{q}, \mathbf{s}$: column vector of size $(m \times 1)$, with one entry per cable.
* **Uppercase letter** $U, V, W, L, Q$: diagonal matrix of size $(m \times m)$ with that vector on its main diagonal.

### General Equation

$$
U = \mathrm{diag}(\mathbf{u}), \qquad Q = \mathrm{diag}(\mathbf{q}), \qquad U \mathbf{q} = Q \mathbf{u}
$$

* $\mathbf{u}$ and $U$: vector $[u_1, \dots, u_m]^T$ of cable $x$-coordinate differences ($u_j = x_i - x_k$) and its $(m \times m)$ diagonal matrix.
* $\mathbf{q}$ and $Q$: vector $[q_1, \dots, q_m]^T$ of cable force densities ($q_j = s_j / l_j$) and its $(m \times m)$ diagonal matrix.
* **Commutation** $U \mathbf{q} = Q \mathbf{u}$: because row $j$ simply computes $u_j q_j = q_j u_j$, we can swap which letter is the diagonal matrix and which is the vector. In Section C.1, this moves the **unknown** coordinate vector $\mathbf{u}$ to the right of the **known** stiffness matrix $Q$.

### Matrix Example

Turning a 3-cable vector $\mathbf{u}$ into a $(3 \times 3)$ diagonal matrix $U = \mathrm{diag}(\mathbf{u})$:

$$
\mathbf{u} = \begin{bmatrix}
2 \\
-1 \\
3
\end{bmatrix}
\qquad \longrightarrow \qquad
U = \mathrm{diag}(\mathbf{u}) = \begin{bmatrix}
2 & 0 & 0 \\
0 & -1 & 0 \\
0 & 0 & 3
\end{bmatrix}
\begin{matrix}
\leftarrow \text{scales cable 1 by } u_1 = 2\text{ m} \\
\leftarrow \text{scales cable 2 by } u_2 = -1\text{ m} \\
\leftarrow \text{scales cable 3 by } u_3 = 3\text{ m}
\end{matrix}
$$

Multiplying a diagonal matrix by a vector scales each cable row independently, so $U \mathbf{q} = Q \mathbf{u}$:

$$
\underset{U\ (3\times 3)}{\begin{bmatrix}
2 & 0 & 0 \\
0 & -1 & 0 \\
0 & 0 & 3
\end{bmatrix}}
\underset{\mathbf{q}\ (3\times 1)}{\begin{bmatrix}
4 \\
5 \\
6
\end{bmatrix}} =
\underset{Q\ (3\times 3)}{\begin{bmatrix}
4 & 0 & 0 \\
0 & 5 & 0 \\
0 & 0 & 6
\end{bmatrix}}
\underset{\mathbf{u}\ (3\times 1)}{\begin{bmatrix}
2 \\
-1 \\
3
\end{bmatrix}} =
\begin{bmatrix}
8 \\
-5 \\
18
\end{bmatrix}
\begin{matrix}
\leftarrow F_{x,1} = u_1 q_1 = 2 \times 4 = 8\text{ kN} \\
\leftarrow F_{x,2} = u_2 q_2 = -1 \times 5 = -5\text{ kN} \\
\leftarrow F_{x,3} = u_3 q_3 = 3 \times 6 = 18\text{ kN}
\end{matrix}
$$"""
import numpy as np
from typing import TypeAlias

FloatMatrix: TypeAlias = np.ndarray[tuple[int, int], np.dtype[np.float64]]
FloatVector: TypeAlias = np.ndarray[tuple[int], np.dtype[np.float64]]

u_example = np.array([2.0, -1.0, 3.0])
U_example = np.diag(u_example)


# %% explain
r"""* `u_example` is a 1D vector of shape `(3,)`; `np.diag(u_example)` places its entries on the main diagonal of the `(3, 3)` matrix `U_example`.
* In NumPy, `np.diag(u) @ q`, `np.diag(q) @ u`, and element-wise `u * q` all produce the exact same cable-force vector $[8, -5, 18]^T$."""


# %% [a2] A.2 Network topology: numbering nodes and branches (section 2.1)
r"""Before introducing 3D coordinates, we represent the cable net topology as a **directed graph** with $n_s = 9$ nodes and $m = 12$ straight cable branches (Schek Sec. 2.1; Linkwitz Sec. 6.4):
* **Free inner nodes first** ($1 \dots 5$, blue circles, $n = 5$): movable interior joints whose 3D equilibrium positions $(\mathbf{x}, \mathbf{y}, \mathbf{z})$ are **unknown**.
* **Fixed anchor nodes last** ($6 \dots 9$, red squares, $n_f = 4$): boundary supports whose 3D positions $(\mathbf{x}_f, \mathbf{y}_f, \mathbf{z}_f)$ are **known**. Numbering free nodes first and fixed anchors last lets us split the connectivity matrix with a single vertical cut into $[C \mid C_f]$.
* **Branch orientation** ($i \to k$): assigns $+1$ at start node $i$ and $-1$ at end node $k$ to define subtraction $x_i - x_k$. Reversing an arrow flips both $C_s$ and $u_j$, which cancels out in $C^T Q C$ and never changes the physical equilibrium shape.

![Fig. 2](images/schek_fig2.png)

![Part A Topology and Matrix Operators on the Cable Net](images/fd_sec_a_topology_split.png)

### Topological Groups (Schek Fig. 2)

* **Branches 1–4 (Anchor cables, red):** $b_1(1\to 6),\ b_2(2\to 7),\ b_3(3\to 8),\ b_4(4\to 9)$ — connect the 4 free corners to the 4 fixed anchors.
* **Branches 5–8 (Inner ring, blue):** $b_5(1\to 4),\ b_6(1\to 2),\ b_7(2\to 3),\ b_8(3\to 4)$ — form the interior diamond loop.
* **Branches 9–12 (Center spokes, green):** $b_9(4\to 5),\ b_{10}(1\to 5),\ b_{11}(2\to 5),\ b_{12}(3\to 5)$ — tie the 4 inner corners to center node $5$."""
branches: list[tuple[int, int]] = [
    (1, 6), (2, 7), (3, 8), (4, 9),   # 1-4: free corners to fixed anchors
    (1, 4), (1, 2), (2, 3), (3, 4),   # 5-8: inner ring
    (4, 5), (1, 5), (2, 5), (3, 5),   # 9-12: four spokes to center node 5
]
n, n_f = 5, 4                         # free nodes 1..5, fixed nodes 6..9
m = len(branches)


# %% explain
r"""* `branches` is a list of `(start_node, end_node)` tuples for the $m = 12$ directed cables.
* **1-based vs. 0-based indexing:** Schek and Linkwitz number nodes $1 \dots 9$ and branches $1 \dots 12$; subtract `1` when indexing NumPy arrays (`i - 1`, `k - 1`)."""


# %% [a3] A.3 Branch-node connectivity matrix and partitioning (section 2.1)
r"""The **branch-node incidence matrix** $C_s$ $(12 \times 9)$ encodes the graph topology in linear algebra (Linkwitz Sec. 6.4.1, Eqs. 6.14–6.20):
* **Row $j$ of $C_s$ (one cable's span operator):** has $+1$ at start node $i$ and $-1$ at end node $k$, so multiplying row $j$ by node coordinates $\mathbf{x}_s$ computes the cable span $u_j = x_i - x_k$.
* **Column $i$ of $C$ / Row $i$ of $C^T$ (one node's force collector):** lists every cable attached to Free Node $i$, so multiplying by $C^T$ sums all cable forces meeting at Node $i$.

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

* $C_s$ $(12 \times 9)$: full incidence matrix for all 12 cables and 9 nodes.
* $C$ $(12 \times 5)$ (Linkwitz $\mathbf{C}_N$): left slice (columns $1 \dots 5$) for the **5 free inner nodes**.
* $C_f$ $(12 \times 4)$ (Linkwitz $\mathbf{C}_F$): right slice (columns $6 \dots 9$) for the **4 fixed anchors**.

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
\leftarrow \text{anchor } b_1:\ +x_1 - x_6 \\
\leftarrow \text{anchor } b_2:\ +x_2 - x_7 \\
\leftarrow \text{anchor } b_3:\ +x_3 - x_8 \\
\leftarrow \text{anchor } b_4:\ +x_4 - x_9 \\
\leftarrow \text{ring } b_5:\ +x_1 - x_4 \\
\leftarrow \text{ring } b_6:\ +x_1 - x_2 \\
\leftarrow \text{ring } b_7:\ +x_2 - x_3 \\
\leftarrow \text{ring } b_8:\ +x_3 - x_4 \\
\leftarrow \text{spoke } b_9:\ +x_4 - x_5 \\
\leftarrow \text{spoke } b_{10}:\ +x_1 - x_5 \\
\leftarrow \text{spoke } b_{11}:\ +x_2 - x_5 \\
\leftarrow \text{spoke } b_{12}:\ +x_3 - x_5
\end{matrix}
$$

* **Left block** $C\ (12 \times 5)$: column $n_1$ has nonzeros in rows $b_1, b_5, b_6, b_{10}$—the exact 4 cables attached to Node 1.
* **Right block** $C_f\ (12 \times 4)$: rows $5 \dots 12$ are zero because ring and spoke cables connect only free nodes."""
C_s: FloatMatrix = np.zeros((m, n + n_f))
for j, (i, k) in enumerate(branches):
    C_s[j, i - 1] = +1.0              # start node i(j): +1 (0-based index)
    C_s[j, k - 1] = -1.0              # end node k(j): -1
C: FloatMatrix = C_s[:, :n]           # (m, n)   free-node columns
C_f: FloatMatrix = C_s[:, n:]         # (m, n_f) fixed-anchor columns


# %% explain
r"""* `np.zeros((m, n + n_f))` allocates the `(12, 9)` matrix; `enumerate(branches)` visits each branch `j` (`0..11`) and writes `+1.0` at start column `i - 1` and `-1.0` at end column `k - 1`.
* `C = C_s[:, :n]` slices the first `5` columns (free nodes, shape `(12, 5)`); `C_f = C_s[:, n:]` slices the last `4` columns (fixed anchors, shape `(12, 4)`)."""


# %% [a4] A.4 Step-by-step matrix multiplication for $C^T Q C$
r"""How does the triple product $D = C^T Q C$ assemble the nodal stiffness matrix for every free node at once (Linkwitz Sec. 6.4.3–6.4.4, Eq. 6.26)? We trace $C^T (Q C)$ on a **5-branch, 3-free-node mini-network** with $q = [2, 3, 4, 5, 6]^T$:
* **Step 1** $Q C$: scales row $j$ of $C$ by cable stiffness $q_j$, turning $+1, -1$ into $+q_j, -q_j$.
* **Step 2** $C^T (Q C)$: row $i$ of $C^T$ gathers all cables touching Free Node $i$, accumulating $+q_j$ on the diagonal $D _ {ii}$ and $-q_j$ on the off-diagonal $D _ {ik}$ for each connected free neighbor $k$.

### 1. Free Connectivity $C\ (5 \times 3)$ and Transpose $C^T\ (3 \times 5)$

$$
C = \begin{bmatrix}
1 & 0 & 0 \\
0 & 1 & 0 \\
1 & -1 & 0 \\
-1 & 0 & 1 \\
0 & 1 & -1
\end{bmatrix}
\begin{matrix}
\leftarrow b_1\ (1\text{ to anchor }4) \\
\leftarrow b_2\ (2\text{ to anchor }5) \\
\leftarrow b_3\ (1\to 2) \\
\leftarrow b_4\ (3\to 1) \\
\leftarrow b_5\ (2\to 3)
\end{matrix}
\qquad \overset{\text{transpose}}{\longrightarrow} \qquad
C^T = \begin{bmatrix}
1 & 0 & 1 & -1 & 0 \\
0 & 1 & -1 & 0 & 1 \\
0 & 0 & 0 & 1 & -1
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Node 1 (touched by } b_1, b_3, b_4\text{)} \\
\leftarrow \text{Node 2 (touched by } b_2, b_3, b_5\text{)} \\
\leftarrow \text{Node 3 (touched by } b_4, b_5\text{)}
\end{matrix}
$$

### 2. Step 1 — Compute $Q C$ (Force Density per Cable, $5 \times 3$)

$$
Q C =
\underset{Q\ (5\times 5)}{\begin{bmatrix}
2 & 0 & 0 & 0 & 0 \\
0 & 3 & 0 & 0 & 0 \\
0 & 0 & 4 & 0 & 0 \\
0 & 0 & 0 & 5 & 0 \\
0 & 0 & 0 & 0 & 6
\end{bmatrix}}
\underset{C\ (5\times 3)}{\begin{bmatrix}
1 & 0 & 0 \\
0 & 1 & 0 \\
1 & -1 & 0 \\
-1 & 0 & 1 \\
0 & 1 & -1
\end{bmatrix}} =
\underset{Q C\ (5\times 3)}{\begin{bmatrix}
2 & 0 & 0 \\
0 & 3 & 0 \\
4 & -4 & 0 \\
-5 & 0 & 5 \\
0 & 6 & -6
\end{bmatrix}}
\begin{matrix}
\leftarrow q_1 = 2\text{ kN/m} \\
\leftarrow q_2 = 3\text{ kN/m} \\
\leftarrow q_3 = 4\text{ kN/m} \\
\leftarrow q_4 = 5\text{ kN/m} \\
\leftarrow q_5 = 6\text{ kN/m}
\end{matrix}
$$

### 3. Step 2 — Compute $D = C^T (Q C)$ (Sum at Free Nodes, $3 \times 3$)

$$
D =
\underset{C^T\ (3\times 5)}{\begin{bmatrix}
1 & 0 & 1 & -1 & 0 \\
0 & 1 & -1 & 0 & 1 \\
0 & 0 & 0 & 1 & -1
\end{bmatrix}}
\underset{Q C\ (5\times 3)}{\begin{bmatrix}
2 & 0 & 0 \\
0 & 3 & 0 \\
4 & -4 & 0 \\
-5 & 0 & 5 \\
0 & 6 & -6
\end{bmatrix}} =
\begin{bmatrix}
q_1+q_3+q_4 & -q_3 & -q_4 \\
-q_3 & q_2+q_3+q_5 & -q_5 \\
-q_4 & -q_5 & q_4+q_5
\end{bmatrix} =
\begin{bmatrix}
11 & -4 & -5 \\
-4 & 13 & -6 \\
-5 & -6 & 11
\end{bmatrix}
$$

* **Diagonal** $D_{ii}$: sum of $q_j$ of all cables connected to free node $i$ (matching $\sum q_k$ in Linkwitz Eq. 6.12).
* **Off-diagonal** $D_{ik}$: $-q_j$ of the cable connecting free nodes $i$ and $k$ ($0$ if not connected)."""
C_mini = np.array(
    [[1, 0, 0], [0, 1, 0], [1, -1, 0], [-1, 0, 1], [0, 1, -1]],
    dtype=float,
)
q_mini = np.array([2.0, 3.0, 4.0, 5.0, 6.0])
QC_mini = np.diag(q_mini) @ C_mini
D_mini = C_mini.T @ QC_mini


# %% explain
r"""* `C_mini.T` transposes the `(5, 3)` branch-to-node matrix into `(3, 5)` (rows = free nodes).
* `@` is NumPy's matrix multiplication operator: `np.diag(q_mini) @ C_mini` scales each cable row by $q_j$, and `C_mini.T @ QC_mini` sums those weighted rows at each free node."""


# %% [b1] B.1 Inputs: fixed anchor coordinates and nodal loads (section 2.2)
r"""We place the 9-node graph into 3D space $(x, y, z)$ with $+z$ pointing vertically upward:
* **Fixed anchors** $\mathbf{x}_f, \mathbf{y}_f, \mathbf{z}_f$ $(4,)$: Anchors $6, 8$ sit on the ground ($z_6 = z_8 = 0\text{ m}$) and Anchors $7, 9$ sit on high masts ($z_7 = z_9 = 1.0\text{ m}$), forcing the net into an anticlastic saddle (Linkwitz Figs. 6.2–6.3).
* **External nodal loads** $\mathbf{p}_x, \mathbf{p}_y, \mathbf{p}_z$ $(5,)$: zero horizontal load ($\mathbf{p}_x = \mathbf{p}_y = \mathbf{0}$) and a downward vertical load $p_{z,i} = -0.5\text{ kN}$ on each of the 5 free nodes.

### Matrix Example (Inputs)

Fixed anchor coordinates $(4 \times 3)$ and external free-node loads $(5 \times 3)$:

$$
\begin{bmatrix} \mathbf{x}_f & \mathbf{y}_f & \mathbf{z}_f \end{bmatrix} =
\begin{bmatrix}
-2 & 0 & 0 \\
0 & 2 & 1 \\
2 & 0 & 0 \\
0 & -2 & 1
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Anchor 6 (left support, ground } z_6 = 0\text{ m)} \\
\leftarrow \text{Anchor 7 (top support, high mast } z_7 = +1\text{ m)} \\
\leftarrow \text{Anchor 8 (right support, ground } z_8 = 0\text{ m)} \\
\leftarrow \text{Anchor 9 (bottom support, high mast } z_9 = +1\text{ m)}
\end{matrix}
$$

$$
\begin{bmatrix} \mathbf{p}_x & \mathbf{p}_y & \mathbf{p}_z \end{bmatrix} =
\begin{bmatrix}
0 & 0 & -0.5 \\
0 & 0 & -0.5 \\
0 & 0 & -0.5 \\
0 & 0 & -0.5 \\
0 & 0 & -0.5
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Free Node 1 (downward load }-0.5\text{ kN)} \\
\leftarrow \text{Free Node 2 (downward load }-0.5\text{ kN)} \\
\leftarrow \text{Free Node 3 (downward load }-0.5\text{ kN)} \\
\leftarrow \text{Free Node 4 (downward load }-0.5\text{ kN)} \\
\leftarrow \text{Free Node 5 (downward load }-0.5\text{ kN)}
\end{matrix}
$$"""
x_f: FloatVector = np.array([-2.0, 0.0, 2.0, 0.0], dtype=np.float64)
y_f: FloatVector = np.array([0.0, 2.0, 0.0, -2.0], dtype=np.float64)
z_f: FloatVector = np.array([0.0, 1.0, 0.0, 1.0], dtype=np.float64)
p_x: FloatVector = np.zeros(n, dtype=np.float64)
p_y: FloatVector = np.zeros(n, dtype=np.float64)
p_z: FloatVector = np.full(n, -0.5, dtype=np.float64)


# %% explain
r"""* `x_f, y_f, z_f` are `(4,)` vectors for fixed anchors $6 \dots 9$ (anchors $7$ and $9$ lifted to $z_f = 1.0\text{ m}$).
* `np.zeros(n)` sets horizontal loads `p_x, p_y` to zero; `np.full(n, -0.5)` sets a downward vertical load of $-0.5\text{ kN}$ on all $n = 5$ free nodes."""


# %% [b2] B.2 Coordinate differences and cable lengths, equation (1)
r"""For each directed cable $j\ (i \to k)$, the coordinate differences $(u_j, v_j, w_j)$ are the 3 orthogonal sides of its 3D bounding box along $(x, y, z)$, and $l_j$ is the 3D space diagonal (Linkwitz Eq. 6.2 & Eqs. 6.15–6.20).

![Section B.2 Geometric Meaning of Coordinate Differences u, v, w and Cable Length l](images/fd_sec_b2_uvw_geometry.png)

### General Equations (Eq. 1)

$$
\mathbf{u} = C \mathbf{x} + C_f \mathbf{x}_f, \qquad
\mathbf{v} = C \mathbf{y} + C_f \mathbf{y}_f, \qquad
\mathbf{w} = C \mathbf{z} + C_f \mathbf{z}_f, \qquad
l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}
$$

* $\mathbf{u}, \mathbf{v}, \mathbf{w}$ $(12 \times 1)$: cable coordinate spans $u_j = x_i - x_k$, $v_j = y_i - y_k$, $w_j = z_i - z_k$ ($\text{m}$). The `+` between $C\mathbf{x}$ and $C_f\mathbf{x}_f$ still subtracts $x_i - x_k$ because the $-1$ for end node $k$ is stored inside $C$ or $C_f$.
* $\mathbf{l}$ $(12 \times 1)$ and $L^{-1} = \mathrm{diag}(1/\mathbf{l})$ $(12 \times 12)$: stressed 3D cable lengths ($\text{m}$) and inverse-length diagonal matrix.

### Matrix Example (Evaluated on Flat Trial Coordinates)

For a flat trial guess with all 5 free nodes at $z = 0$ ($\mathbf{x} = [-1, 0, 1, 0, 0]^T$, $\mathbf{y} = [0, -1, 0, 1, 0]^T$, $\mathbf{z} = \mathbf{0}$):

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
\underset{\mathbf{x}_f\ (4\times 1)}{\begin{bmatrix}
-2 \\
0 \\
2 \\
0
\end{bmatrix}}
$$

Collecting $[\mathbf{u}, \mathbf{v}, \mathbf{w}]$ and the resulting 3D lengths $l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}$:

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
\end{bmatrix},
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
\end{bmatrix}
\begin{matrix}
\leftarrow b_1\ (1\to 6):\ \text{flat ground cable, } l_1 = 1\text{ m} \\
\leftarrow b_2\ (2\to 7):\ \text{climbs to } z_7=1\text{ m},\ l_2 = \sqrt{10}\text{ m} \\
\leftarrow b_3\ (3\to 8):\ \text{flat ground cable, } l_3 = 1\text{ m} \\
\leftarrow b_4\ (4\to 9):\ \text{climbs to } z_9=1\text{ m},\ l_4 = \sqrt{10}\text{ m} \\
\leftarrow b_5..b_8:\ \text{45}^\circ\text{ ring diagonals, } l_j = \sqrt{2}\text{ m} \\
\\
\\
\\
\leftarrow b_9..b_{12}:\ \text{flat spokes, } l_j = 1\text{ m} \\
\\
\\
\\
\end{matrix}
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
    u = C @ x + C_f @ x_f
    v = C @ y + C_f @ y_f
    w = C @ z + C_f @ z_f
    l = np.sqrt(u**2 + v**2 + w**2)
    return u, v, w, l


# %% explain
r"""* `u = C @ x + C_f @ x_f` evaluates $(12, 5) \times (5,) + (12, 4) \times (4,) \to (12,)$, computing $x_{\text{start}} - x_{\text{end}}$ for all 12 cables in one vectorized step.
* `np.sqrt(u**2 + v**2 + w**2)` squares each vector element-wise (`**2`), sums them, and takes the square root to get the `(12,)` length vector `l`.
* **Source of nonlinearity:** $l_j$ traps the unknown coordinates $\mathbf{x}, \mathbf{y}, \mathbf{z}$ inside a square root."""


# %% [b3] B.3 Nonlinear equilibrium in 4 stages, equation (2)
r"""To check 3D static equilibrium when cable $j$ carries tension $s_j$, we project $s_j$ onto $(x, y, z)$ using direction cosines $\cos\alpha_j = u_j / l_j$, $\cos\beta_j = v_j / l_j$, $\cos\gamma_j = w_j / l_j$ and sum forces at each free node (Linkwitz Sec. 6.2.2 & Sec. 6.4.2, where $C^T U L^{-1} = (\partial \mathbf{l} / \partial \mathbf{x})^T$):
* **Why the flat trial net fails vertical equilibrium:** in the flat trial shape ($z_1 \dots z_5 = 0$), all inner cables $b_5 \dots b_{12}$ have zero vertical span ($w_j = 0 \implies F_{z,j} = 0$), providing no upward lift against the $-0.5\text{ kN}$ load.

![Section B.3 Four-Stage Nonlinear Equilibrium and Flat Net Imbalance](images/fd_sec_b3_nonlinear_stages.png)

### General Equation (Eq. 2)

Read the equilibrium residual equation **from right to left** in 4 stages:

$$
\mathbf{e}_x = \underset{\text{Stage 3: sum at free nodes}}{C^T} \quad \underset{\text{Stage 2: multiply by } u_j}{U} \quad \underset{\text{Stage 1: } q_j = s_j / l_j}{L^{-1} \mathbf{s}} \quad - \quad \underset{\text{Stage 4: external load}}{\mathbf{p}_x}
$$

* **Stage 1** ($L^{-1} \mathbf{s}$, $12 \times 1$): divides tension $s_j$ by length $l_j$ to get $q_j = s_j / l_j$ ($\text{kN/m}$).
* **Stage 2** ($U L^{-1} \mathbf{s}$, $12 \times 1$): multiplies by span $u_j$ to get cable force component $F_{x,j} = s_j (u_j / l_j)$ ($\text{kN}$).
* **Stage 3** ($C^T U L^{-1} \mathbf{s}$, $5 \times 1$): sums cable forces meeting at each of the 5 free nodes.
* **Stage 4** ($\mathbf{e}_x, \mathbf{e}_y, \mathbf{e}_z$, $5 \times 1$): out-of-balance nodal force residual ($\text{kN}$) after subtracting load $\mathbf{p}$.

### Matrix Example (Flat Trial Shape with $s_j = 1\text{ kN}$)

Stage 1 ($\mathbf{q} = L^{-1}\mathbf{s}$) and Stage 2 ($\mathbf{F}_x = U\mathbf{q},\ \mathbf{F}_y = V\mathbf{q},\ \mathbf{F}_z = W\mathbf{q}$):

$$
\mathbf{q} = L^{-1} \mathbf{s} =
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
\end{bmatrix},
\qquad
\mathbf{F}_x = U \mathbf{q} =
\begin{bmatrix}
1 \\
0 \\
-1 \\
0 \\
-\tfrac{1}{\sqrt{2}} \\
-\tfrac{1}{\sqrt{2}} \\
-\tfrac{1}{\sqrt{2}} \\
\tfrac{1}{\sqrt{2}} \\
0 \\
-1 \\
0 \\
1
\end{bmatrix},
\qquad
\mathbf{F}_y = V \mathbf{q} =
\begin{bmatrix}
0 \\
-\tfrac{3}{\sqrt{10}} \\
0 \\
\tfrac{3}{\sqrt{10}} \\
-\tfrac{1}{\sqrt{2}} \\
\tfrac{1}{\sqrt{2}} \\
-\tfrac{1}{\sqrt{2}} \\
-\tfrac{1}{\sqrt{2}} \\
1 \\
0 \\
-1 \\
0
\end{bmatrix},
\qquad
\mathbf{F}_z = W \mathbf{q} =
\begin{bmatrix}
0 \\
-\tfrac{1}{\sqrt{10}} \\
0 \\
-\tfrac{1}{\sqrt{10}} \\
0 \\
0 \\
0 \\
0 \\
0 \\
0 \\
0 \\
0
\end{bmatrix}
$$

Stage 3 ($C^T \mathbf{F}_x$) and Stage 4 ($\mathbf{e} = C^T \mathbf{F} - \mathbf{p}$ at the 5 free nodes):

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
1 \\
0 \\
-1 \\
0 \\
-0.707 \\
-0.707 \\
-0.707 \\
0.707 \\
0 \\
-1 \\
0 \\
1
\end{bmatrix}} =
\begin{bmatrix}
-1.414 \\
0 \\
1.414 \\
0 \\
0
\end{bmatrix}
$$

$$
\mathbf{e}_x =
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
\end{bmatrix},
\qquad
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
\leftarrow \text{Node 5 (spokes flat }\Rightarrow 0\text{ lift)}
\end{matrix}
$$"""
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


# %% explain
r"""* `L_inv = np.diag(1.0 / l)` builds the `(12, 12)` diagonal inverse-length matrix $L^{-1}$, and `C.T @ np.diag(u) @ L_inv @ s - p_x` chains Stages 1–4 right-to-left.
* Solving Eq. (2) directly for $\mathbf{x}, \mathbf{y}, \mathbf{z}$ is nonlinear because $L^{-1}$ divides by $\sqrt{u_j^2 + v_j^2 + w_j^2}$. Part C eliminates $L^{-1}$ with a single substitution."""


# %% [c1] C.1 The force density trick and the diagonal swap, equations (4) to (6)
r"""Prescribing the **force density** $q_j = s_j / l_j$ ($\text{kN/m}$) cancels the nonlinear length $l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}$ out of the direction cosine $u_j / l_j$, turning each cable into a zero-rest-length 3D linear spring with horizontal pull $F_{x,j} = q_j u_j = q_j(x_i - x_k)$ (Schek Eqs. 4–6; Linkwitz Sec. 6.2.3, Eqs. 6.9–6.11).

![Section C.1 How Force Density Uses Coordinate Difference u to Linearize Equilibrium](images/fd_sec_c1_force_density_trick.png)

### General Equations (Eqs. 4–6) & What $u$ Means

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

* $u_j$, $\mathbf{u}$ $(12 \times 1)$, and $U = \mathrm{diag}(\mathbf{u})$ $(12 \times 12)$: **horizontal coordinate difference** $u_j = x_i - x_k$ ($\text{m}$) between start node $i$ and end node $k$ of cable $j$ (similarly $v_j = y_i - y_k$ in $V$, $w_j = z_i - z_k$ in $W$).
* $u_j / l_j = \cos\alpha_j$: **direction cosine** projecting 3D cable tension $s_j$ onto the $x$-axis; substituting $s_j = q_j l_j$ cancels $l_j$ so $F_{x,j} = q_j u_j$.
* **Why we swap** $U \mathbf{q} = Q \mathbf{u}$: moves the **unknown** coordinate spans $\mathbf{u}$ out of the diagonal matrix $U$ into the right-hand vector, multiplied by the **known** diagonal stiffness matrix $Q = \mathrm{diag}(\mathbf{q})$.

### Matrix Example (Prescribed Force Densities)

We assign $q = 2\text{ kN/m}$ to the 4 outer anchor cables (branches 1–4) and $q = 1\text{ kN/m}$ to the 8 inner ring and spoke cables (branches 5–12):

$$
\mathbf{q} = \begin{bmatrix}
2 & 2 & 2 & 2 & 1 & 1 & 1 & 1 & 1 & 1 & 1 & 1
\end{bmatrix}^T\text{ kN/m},
\qquad
Q = \mathrm{diag}(\mathbf{q})_{(12\times 12)}
$$"""
q = np.array([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1], dtype=float)


# %% explain
r"""* `q` is a 1D NumPy array of shape `(12,)` holding the prescribed force density $q_j$ ($\text{kN/m}$) for each branch.
* **Predict:** If $q$ on the 4 anchor cables is raised from $2.0$ to $10.0\text{ kN/m}$, does center node 5 move higher or sag lower? (Checked in D.2.)"""


# %% [c2] C.2 System matrices $D$ and $D_f$, equations (7) and (8)
r"""Substituting $\mathbf{u} = C \mathbf{x} + C_f \mathbf{x}_f$ into $C^T Q \mathbf{u} = \mathbf{p}_x$ expresses equilibrium directly in terms of the unknown free-node coordinates $\mathbf{x}$ and known fixed-anchor coordinates $\mathbf{x}_f$ (Linkwitz Sec. 6.4.3, Eqs. 6.25–6.33):
* **Row $i$ of $D\mathbf{z} = \mathbf{p}_z - D_f\mathbf{z}_f$ matches Linkwitz Eq. 6.12:** for Free Node 2 (Row 2), $(q_2+q_6+q_7+q_{11})z_2 - q_6 z_1 - q_7 z_3 - q_{11} z_5 = p_{z,2} + q_2 z_7 \iff 5z_2 - z_1 - z_3 - z_5 = -0.5 + 2.0 = +1.5\text{ kN}$.

![Sections C.2 to D.1 Physical Meaning of D and Solved 3D Saddle Equilibrium Net](images/fd_sec_c2_c3_solved_net.png)

### General Equations (Eqs. 7–8)

$$
(C^T Q C)\mathbf{x} + (C^T Q C_f)\mathbf{x}_f = \mathbf{p}_x
\qquad \Longrightarrow \qquad
D \mathbf{x} = \mathbf{p}_x - D_f \mathbf{x}_f = \mathbf{b}_x
$$

* $D = C^T Q C$ $(5 \times 5)$ (Linkwitz $\mathbf{D}_N$): **free-node stiffness matrix** ($\text{kN/m}$), with diagonal $D_{ii} = \sum q_j$ at Node $i$ and off-diagonal $D_{ik} = -q_j$ between connected Free Nodes $i, k$.
* $D_f = C^T Q C_f$ $(5 \times 4)$ (Linkwitz $\mathbf{D}_F$): **fixed-anchor coupling matrix** ($\text{kN/m}$); $-D_f \mathbf{x}_f$ is the boundary anchor pull ($\text{kN}$) on the 5 free nodes.

### 1. Symbolic Structure of $D$ (Schek Fig. 4)

$$
D =
\begin{bmatrix}
q_1+q_5+q_6+q_{10} & -q_6 & 0 & -q_5 & -q_{10} \\
-q_6 & q_2+q_6+q_7+q_{11} & -q_7 & 0 & -q_{11} \\
0 & -q_7 & q_3+q_7+q_8+q_{12} & -q_8 & -q_{12} \\
-q_5 & 0 & -q_8 & q_4+q_5+q_8+q_9 & -q_9 \\
-q_{10} & -q_{11} & -q_{12} & -q_9 & q_9+q_{10}+q_{11}+q_{12}
\end{bmatrix}
$$

### 2. Numerical Matrices $D$, $D_f$, and Right-Hand Side $\mathbf{b}_z$ for $\mathbf{q} = [2,2,2,2,1,\dots,1]^T$

$$
D = C^T Q C =
\begin{bmatrix}
5 & -1 & 0 & -1 & -1 \\
-1 & 5 & -1 & 0 & -1 \\
0 & -1 & 5 & -1 & -1 \\
-1 & 0 & -1 & 5 & -1 \\
-1 & -1 & -1 & -1 & 4
\end{bmatrix},
\qquad
D_f = C^T Q C_f =
\begin{bmatrix}
-2 & 0 & 0 & 0 \\
0 & -2 & 0 & 0 \\
0 & 0 & -2 & 0 \\
0 & 0 & 0 & -2 \\
0 & 0 & 0 & 0
\end{bmatrix}
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
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Node 1 (ground Anchor 6 at } z_6=0\text{)} \\
\leftarrow \text{Node 2 (Anchor 7 at } z_7=1\text{ pulls up }+2.0\text{ kN)} \\
\leftarrow \text{Node 3 (ground Anchor 8 at } z_8=0\text{)} \\
\leftarrow \text{Node 4 (Anchor 9 at } z_9=1\text{ pulls up }+2.0\text{ kN)} \\
\leftarrow \text{Node 5 (no direct anchor cable)}
\end{matrix}
$$"""
Q = np.diag(q)
D = C.T @ Q @ C                                 # (n, n)   eq. (8)
D_f = C.T @ Q @ C_f                             # (n, n_f)
rhs = np.c_[p_x - D_f @ x_f, p_y - D_f @ y_f, p_z - D_f @ z_f]


# %% explain
r"""* `Q = np.diag(q)` builds the `(12, 12)` diagonal force-density matrix; `D = C.T @ Q @ C` is `(5, 5)` and `D_f = C.T @ Q @ C_f` is `(5, 4)`.
* `np.c_[...]` stacks the three `(5,)` right-hand side vectors $[b_x \mid b_y \mid b_z]$ side-by-side into a `(5, 3)` matrix `rhs`."""


# %% [c3] C.3 Direct linear solve for free node coordinates, equation (9)
r"""Because $D = C^T Q C$ is constant and symmetric positive-definite, we solve the three $(5 \times 5)$ linear systems $D\mathbf{x} = \mathbf{b}_x$, $D\mathbf{y} = \mathbf{b}_y$, $D\mathbf{z} = \mathbf{b}_z$ in **one direct step** without iteration (Schek Eq. 9; Linkwitz Eqs. 6.31–6.33):
* **Weighted-average heights** (Linkwitz Eq. 6.13): high corners $z_2 = z_4 = 0.330\text{ m}$ are pulled up by lifted anchors $7, 9$ ($z=1\text{ m}$), low corners $z_1 = z_3 = 0.045\text{ m}$ are held down by ground anchors $6, 8$ ($z=0\text{ m}$), and center node 5 settles at $z_5 = (z_1+z_2+z_3+z_4 - 0.5)/4 = 0.063\text{ m}$ (Panel 2 in C.2).

### General Equations (Eq. 9)

$$
D \mathbf{x} = \mathbf{p}_x - D_f \mathbf{x}_f, \qquad
D \mathbf{y} = \mathbf{p}_y - D_f \mathbf{y}_f, \qquad
D \mathbf{z} = \mathbf{p}_z - D_f \mathbf{z}_f
$$

### Matrix Example (Vertical Solve $D \mathbf{z} = \mathbf{b}_z$ and 3D Coordinates)

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

Solved 3D free-node coordinates $[\mathbf{x}, \mathbf{y}, \mathbf{z}]$ $(5 \times 3)$:

$$
\begin{bmatrix} \mathbf{x} & \mathbf{y} & \mathbf{z} \end{bmatrix} =
\begin{bmatrix}
-0.800 & 0.000 & 0.045 \\
0.000 & 0.800 & 0.330 \\
0.800 & 0.000 & 0.045 \\
0.000 & -0.800 & 0.330 \\
0.000 & 0.000 & 0.063
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Node 1 (low corner tied to ground Anchor 6)} \\
\leftarrow \text{Node 2 (high corner pulled up by lifted Anchor 7)} \\
\leftarrow \text{Node 3 (low corner tied to ground Anchor 8)} \\
\leftarrow \text{Node 4 (high corner pulled up by lifted Anchor 9)} \\
\leftarrow \text{Node 5 (center saddle hub)}
\end{matrix}
$$"""
x: FloatVector = np.linalg.solve(D, p_x - D_f @ x_f)    # eq. (9)
y: FloatVector = np.linalg.solve(D, p_y - D_f @ y_f)
z: FloatVector = np.linalg.solve(D, p_z - D_f @ z_f)


# %% explain
r"""* `np.linalg.solve(D, b)` solves the $(5 \times 5)$ linear system $D \mathbf{x} = \mathbf{b}$ directly via LU factorization without forming $D^{-1}$.
* All three axes share the exact same left-hand matrix `D`; only the right-hand side vector `p - D_f @ x_f` changes per axis."""


# %% [c4] C.4 Recovering cable lengths, forces, materialization cutting lengths, and verification, equation (10)
r"""From the solved coordinates $(\mathbf{x}, \mathbf{y}, \mathbf{z})$, we recompute stressed cable lengths $\mathbf{l}$, recover axial tension forces $\mathbf{s} = Q \mathbf{l}$ (Schek Eq. 10), and—given elastic axial stiffness $EA_j$—compute the unstressed workshop **cutting lengths** $\mathbf{l}_0$ (Linkwitz Sec. 6.5, Eqs. 6.34–6.37).

### General Equations (Schek Eq. 10 & Linkwitz Eq. 6.37)

$$
s_j = q_j l_j \quad (\mathbf{s} = Q \mathbf{l} = L \mathbf{q}), \qquad
\mathbf{e}_x = C^T U L^{-1} \mathbf{s} - \mathbf{p}_x = \mathbf{0}, \qquad
l_{0,j} = \frac{l_j}{1 + s_j / EA_j}
$$

* $s_j = q_j l_j$: axial tension force ($\text{kN}$) in cable $j$; substituting $(\mathbf{x}, \mathbf{y}, \mathbf{z}, \mathbf{s})$ into Eq. (2) gives $\max |\mathbf{e}| = 4.44 \times 10^{-16}\text{ kN} \approx 0$.
* $l_{0,j}$: unstressed workshop cutting length ($\text{m}$) for axial stiffness $EA_j$ ($\text{kN}$), so elastic stretch $e_j = l_j - l_{0,j}$ induces tension $s_j$.

### Matrix Example (Lengths $\mathbf{l}$, Forces $\mathbf{s}$, and Cutting Lengths $\mathbf{l}_0$ for $EA = 500\text{ kN}$)

$$
\underset{\mathbf{q}\ (\text{kN/m})}{\begin{bmatrix}
2.0 \\
2.0 \\
2.0 \\
2.0 \\
1.0 \\
\vdots \\
1.0 \\
1.0
\end{bmatrix}} \odot
\underset{\mathbf{l}\ (\text{m})}{\begin{bmatrix}
1.201 \\
1.374 \\
1.201 \\
1.374 \\
1.167 \\
\vdots \\
0.844 \\
0.800
\end{bmatrix}} =
\underset{\mathbf{s}\ (\text{kN})}{\begin{bmatrix}
2.402 \\
2.748 \\
2.402 \\
2.748 \\
1.167 \\
\vdots \\
0.844 \\
0.800
\end{bmatrix}}
\qquad \overset{EA_j = 500\text{ kN}}{\longrightarrow} \qquad
\underset{\mathbf{l}_0\ (\text{m, cutting})}{\begin{bmatrix}
1.195 \\
1.367 \\
1.195 \\
1.367 \\
1.164 \\
\vdots \\
0.842 \\
0.799
\end{bmatrix}}
\begin{matrix}
\leftarrow b_1\ (\text{stretch } e_1 = 5.7\text{ mm}) \\
\leftarrow b_2\ (\text{lifted anchor, } e_2 = 7.5\text{ mm}) \\
\leftarrow b_3\ (\text{stretch } e_3 = 5.7\text{ mm}) \\
\leftarrow b_4\ (\text{lifted anchor, } e_4 = 7.5\text{ mm}) \\
\leftarrow b_5..b_8\ (\text{ring, } e_j = 2.7\text{ mm}) \\
\vdots \\
\leftarrow b_9, b_{11}\ (\text{high spokes, } e_j = 1.4\text{ mm}) \\
\leftarrow b_{10}, b_{12}\ (\text{low spokes, } e_j = 1.3\text{ mm})
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


# %% explain
r"""* `coordinate_differences` recomputes the equilibrium cable lengths `l` from the solved coordinates `(x, y, z)`.
* `s = l * q` multiplies element-by-element (`*`, equivalent to $Q \mathbf{l}$) to recover axial forces: among branches with equal $q$, **longer branches carry larger tension**.
* `l_cutting = l / (1.0 + s / EA)` implements Linkwitz Eq. (6.37), giving the exact unstressed workshop cutting lengths $\mathbf{l}_0$ so that stretching each cable into place induces tension $\mathbf{s}$.
* `max_eq_error` evaluates to `4.44e-16` (machine zero), confirming exact nonlinear 3D equilibrium."""


# %% [d1] D.1 Complete linear form-finding function and support reactions (figure 3)
r"""We package Steps A.3–C.4 into a single function `form_finding` (matching Linkwitz's flowchart in Fig. 6.8) and compute the 3D support reactions $\mathbf{R}_f = C_f^T Q \mathbf{U}_{xyz}$ at the 4 fixed anchors (Schek Eq. 5, Fig. 3):
* **Hanging vs. hold-down anchor reactions:** lifted anchors $7, 9$ carry upward reactions $R_{7z} = R_{9z} = +1.339\text{ kN}$ (hanging cables), while ground anchors $6, 8$ have downward reactions $R_{6z} = R_{8z} = -0.089\text{ kN}$ holding low corners $1, 3$ ($z = 0.045\text{ m}$) down against the saddle's upward pull. Total vertical reaction $\sum R_{fz} = +2.500\text{ kN}$ balances the $-2.500\text{ kN}$ load.

![Fig. 3](images/schek_fig3.png)

### General Equations (3-Column Form & Support Reactions)

$$
D \mathbf{X} = \mathbf{P} - D_f \mathbf{X}_f, \qquad
\mathbf{U}_{xyz} = C \mathbf{X} + C_f \mathbf{X}_f, \qquad
\mathbf{R}_f = C_f^T Q \mathbf{U}_{xyz}
$$

* $\mathbf{X}$ $(5 \times 3)$ and $\mathbf{X}_f$ $(4 \times 3)$: free-node and fixed-anchor 3D coordinate matrices $[\mathbf{x}, \mathbf{y}, \mathbf{z}]$ ($\text{m}$).
* $\mathbf{U}_{xyz}$ $(12 \times 3)$: matrix of 3D cable coordinate differences $[\mathbf{u}, \mathbf{v}, \mathbf{w}]$ ($\text{m}$).
* $\mathbf{R}_f = C_f^T Q \mathbf{U}_{xyz}$ $(4 \times 3)$: 3D support reaction forces $[R_{fx}, R_{fy}, R_{fz}]$ ($\text{kN}$) at fixed anchors $6 \dots 9$.

### Matrix Example (Support Reactions $\mathbf{R}_f$)

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
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Anchor 6 (ground: holds Node 1 down with }-0.089\text{ kN)} \\
\leftarrow \text{Anchor 7 (lifted mast: supports }+1.339\text{ kN upward)} \\
\leftarrow \text{Anchor 8 (ground: holds Node 3 down with }-0.089\text{ kN)} \\
\leftarrow \text{Anchor 9 (lifted mast: supports }+1.339\text{ kN upward)}
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
    reactions = C_f.T @ Q @ uvw                                # eq. (5)
    return xyz, l, s, reactions


# %% explain
r"""* `np.vstack([...]).T` solves axes `a = 0, 1, 2` ($x, y, z$) and stacks them as columns into `xyz` of shape `(n_free, 3)`.
* `uvw = C @ xyz + C_f @ xyz_fixed` computes `[u | v | w]` as an `(m, 3)` matrix, and `np.linalg.norm(uvw, axis=1)` computes the Euclidean length $\sqrt{u_j^2 + v_j^2 + w_j^2}$ of each row.
* **Global Equilibrium Check:** `reactions = C_f.T @ Q @ uvw` gives $\sum_{i=6}^9 R_{iz} = +2.500\text{ kN}$, which exactly balances the total downward load $\sum_{i=1}^5 p_{iz} = -2.500\text{ kN}$."""


# %% [d2] D.2 Parameter study: moving anchors, changing force densities, and scale invariance
r"""How do the three design controls—anchor positions $\mathbf{X}_f$, stiffness ratios $\mathbf{q}$, and overall force scale $\lambda$—affect $D \mathbf{X} = \mathbf{P} - D_f \mathbf{X}_f$?
* **Moving anchors** $\mathbf{X}_f$ (Case 2): only updates the right-hand side $\mathbf{P} - D_f \mathbf{X}_f$; $D$ is unchanged.
* **Changing stiffness ratios** $\mathbf{q}$ (Case 3, Linkwitz Fig. 6.6): raising $q_{1..4}$ from $2 \to 10\text{ kN/m}$ rebuilds $D$ and pulls center node 5 up from $z_5 = 0.063 \to 0.313\text{ m}$.
* **Scale invariance** $(2\mathbf{q}, 2\mathbf{P})$ (Case 4, Linkwitz Sec. 6.7): scaling both $\mathbf{q}$ and $\mathbf{P}$ by $\lambda = 2$ cancels on both sides of $D\mathbf{X} = \mathbf{P} - D_f\mathbf{X}_f$, leaving the 3D geometry $\mathbf{X}$ **100% identical** while doubling cable forces $\mathbf{s}$.

![Parts D, E and F Parameter Study, Energy Minimization and Target Length Constraints](images/fd_sec_e_f_constraints.png)

### Matrix Comparison Across 4 Runs

| Case | Matrix $D\ (5\times 5)$ | RHS $\mathbf{P} - D_f \mathbf{X}_f$ | Center Height $z_5\ (\text{m})$ | Max Cable Force $\max(\mathbf{s})$ |
|---|---|---|---|---|
| **1. Base case** ($q_{\text{anchor}} = 2,\ \mathbf{p}_z = -0.5$) | built once | base | $0.063\text{ m}$ | $2.748\text{ kN}$ |
| **2. All anchors lifted** $+1\text{ m}$ | **unchanged** | updated | $1.063\text{ m}$ | $2.748\text{ kN}$ |
| **3. Stiffer anchors** ($q_{\text{anchor}} = 10,\ \mathbf{p}_z = -0.5$) | **rebuilt** | updated | $0.313\text{ m}$ | $4.732\text{ kN}$ |
| **4. Scale invariance** ($2\mathbf{q},\ 2\mathbf{p}_z$, Linkwitz Sec. 6.7) | scaled by $2\times$ | scaled by $2\times$ | **$0.063\text{ m}$ (identical!)** | **$5.496\text{ kN}$ ($2\times$)** |"""
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


# %% explain
r"""* `xyz_fixed + np.array([0.0, 0.0, 1.0])` broadcasts $+1.0\text{ m}$ to the $z$ coordinate of all 4 anchors without changing `D`.
* `np.where(np.arange(m) < 4, 10.0, 1.0)` raises $q$ on the first 4 branches from $2$ to $10\text{ kN/m}$ (rebuilding `D`), pulling center node 5 up from $0.063\text{ m}$ to $0.313\text{ m}$.
* `scale_invariance_xyz_diff` is `0.0`: multiplying both `q` and `p` by `2.0` leaves `xyz4` identical to `xyz1` while doubling forces `s4 = 2 * s1` (Linkwitz Sec. 6.7)."""


# %% [e1] E.1 Geometric meaning of force densities (section 4)
r"""For an unloaded net ($\mathbf{P} = \mathbf{0}$), solving $D\mathbf{X} = -D_f\mathbf{X}_f$ is equivalent to minimizing the **$q$-weighted sum of squared cable lengths** $\Phi = \sum q_j l_j^2$—twice the elastic potential energy of a zero-rest-length spring network (Schek Sec. 4, Eqs. 37–40).

### General Equations (Eqs. 37–40, Theorems 1 & 2)

$$
\Phi(\mathbf{x}, \mathbf{y}, \mathbf{z}) = \mathbf{u}^T Q \mathbf{u} + \mathbf{v}^T Q \mathbf{v} + \mathbf{w}^T Q \mathbf{w} = \sum_{j=1}^m q_j l_j^2 \longrightarrow \min
$$

$$
\frac{\partial \Phi}{\partial \mathbf{x}} = 2 C^T Q \mathbf{u} = 2 (D \mathbf{x} + D_f \mathbf{x}_f) = \mathbf{0}
$$

* **Theorem 1:** $q_j$ weights $l_j^2$ in $\Phi$—a **large** $q_j$ penalizes length and keeps cable $j$ **short and taut**; a **small** $q_j$ lets it stretch.
* **Theorem 2 (Constant-Force Net):** setting $q_j = c / l_j$ gives uniform cable tensions $s_j = q_j l_j = c$ and minimizes $\sum l_j$.

### Matrix Example (Unloaded Saddle $\mathbf{P} = \mathbf{0}$)

$$
\mathbf{X}_0 = \begin{bmatrix}
-0.800 & 0.000 & 0.357 \\
0.000 & 0.800 & 0.643 \\
0.800 & 0.000 & 0.357 \\
0.000 & -0.800 & 0.643 \\
0.000 & 0.000 & 0.500
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Node 1 (symmetric low corner, } z_1 = 5/14 \approx 0.357\text{ m)} \\
\leftarrow \text{Node 2 (symmetric high corner, } z_2 = 9/14 \approx 0.643\text{ m)} \\
\leftarrow \text{Node 3 (symmetric low corner, } z_3 = 5/14 \approx 0.357\text{ m)} \\
\leftarrow \text{Node 4 (symmetric high corner, } z_4 = 9/14 \approx 0.643\text{ m)} \\
\leftarrow \text{Node 5 (exact saddle midpoint } z_5 = 0.500\text{ m)}
\end{matrix}
$$

$$
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


# %% explain
r"""* Passing `np.zeros((n, 3))` sets external loads $\mathbf{P} = \mathbf{0}$; `max_grad_unloaded` evaluates to `8.88e-16` ($\approx 0$), confirming Theorem 1.
* With `q_const = 1.0 / l0`, the recovered forces `s_uniform = l0 * q_const` are `[1, 1, ..., 1]` $\text{kN}$ across all 12 cables, confirming Theorem 2."""


# %% [f1] F.1 Target length and force constraints, equation (11)
r"""With $\mathbf{q} = [2, 2, 2, 2, 1, \dots, 1]^T$, lifted anchor cables $b_2, b_4$ come out $+17.4\text{ cm}$ longer than ground anchor cables $b_1, b_3$ ($1.374\text{ m}$ vs. $1.201\text{ m}$). To prescribe target equilibrium lengths $\mathbf{l}_v$ or forces $\mathbf{s}_v$, we form the **constraint residual vector** $\mathbf{g}^{\ast}(\mathbf{q})$ (Schek Sec. 3.1, Eq. 11) and solve for $\mathbf{q}^{\ast} > \mathbf{0}$ such that $\mathbf{g}^{\ast}(\mathbf{q}^{\ast}) = \mathbf{0}$.

### General Equation (Eq. 11)

$$
\mathbf{g}^{\ast}(\mathbf{q}) = \begin{bmatrix}
\mathbf{l}_{\text{constrained}}(\mathbf{q}) - \mathbf{l}_v \\
\mathbf{s}_{\text{constrained}}(\mathbf{q}) - \mathbf{s}_v
\end{bmatrix} = \mathbf{0}
$$

* $\mathbf{g}^{\ast}(\mathbf{q})$ $(r \times 1)$: vector of $r$ constraint residuals evaluated at the equilibrium shape for $\mathbf{q}$.
* $\mathbf{l}_{\text{constrained}}(\mathbf{q}), \mathbf{s}_{\text{constrained}}(\mathbf{q})$ and $\mathbf{l}_v, \mathbf{s}_v$: equilibrium lengths/forces at $\mathbf{q}$ and their prescribed target values.

### Matrix Example (Requiring Anchor Cables 1–4 to Have Length $1.200\text{ m}$)

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
\leftarrow \text{Branch 1 (ground anchor cable: } +1\text{ mm error)} \\
\leftarrow \text{Branch 2 (lifted anchor cable: } +17.4\text{ cm too long!)} \\
\leftarrow \text{Branch 3 (ground anchor cable: } +1\text{ mm error)} \\
\leftarrow \text{Branch 4 (lifted anchor cable: } +17.4\text{ cm too long!)}
\end{matrix}
$$"""
length_rows = [0, 1, 2, 3]                    # the four anchor branches
target_lengths = np.full(4, 1.2)              # target length 1.2 m on each
g_lengths = l[length_rows] - target_lengths   # constraint residual vector


# %% explain
r"""* `l[length_rows] - target_lengths` slices the 4 anchor cable lengths (`[0, 1, 2, 3]`) and subtracts $1.2\text{ m}$ to form the `(4,)` residual vector `g_lengths`.
* Here 4 equations constrain 12 unknown force densities $\mathbf{q}$ ($r = 4 < m = 12$), forming an underdetermined nonlinear system solved by least-squares iteration in F.2."""


# %% [f2] F.2 Iterative solver for prescribed lengths and forces (sections 3.1 to 3.6)
r"""At each iteration $k$, we solve the linear equilibrium system $D(\mathbf{q}^{(k)})\mathbf{X} = \mathbf{B}$, evaluate the mismatch $\mathbf{g}^{\ast}(\mathbf{q}^{(k)})$, and update $\mathbf{q}$ via least squares until $\mathbf{g}^{\ast}(\mathbf{q}^{\ast}) = \mathbf{0}$ (Panel 2 of the diagram in D.2):
* Because branches $2, 4$ were too long ($1.374 > 1.200\text{ m}$), the solver automatically increases $q_2, q_4$ from $2.000 \to 2.412\text{ kN/m}$ to pull them shorter.

### Iteration Loop

$$
\mathbf{q}^{(k)} \xrightarrow{\text{linear solve } D(\mathbf{q}^{(k)})\mathbf{X} = \mathbf{B}} \mathbf{l}(\mathbf{q}^{(k)}),\ \mathbf{s}(\mathbf{q}^{(k)}) \xrightarrow{\text{check mismatch}} \mathbf{g}^{\ast}(\mathbf{q}^{(k)}) \xrightarrow{\text{Jacobian update } \Delta\mathbf{q}} \mathbf{q}^{(k+1)}
$$

### Matrix Example (Before vs. After Optimization on Anchor Cables 1–4)

$$
\text{Initial:}\quad
\mathbf{q} _ {1..4}^{(0)} =
\begin{bmatrix}
2.000 \\
2.000 \\
2.000 \\
2.000
\end{bmatrix}\text{ kN/m},
\qquad
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
\qquad
\mathbf{l} _ {1..4}^{\ast} =
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


# %% explain
r"""* `residual(q_trial)` runs the linear `form_finding` solver at candidate `q_trial` and concatenates length errors `l_cur[length_rows] - l_v` and force errors `s_cur[force_rows] - s_v` via `np.r_[...]`.
* `scipy.optimize.least_squares` adjusts `q` until `residual` reaches zero (`found.x` is the optimal $\mathbf{q}^{\ast}$), while `bounds=(1e-9, np.inf)` enforces $q_j > 0$ so cables never go slack or compressive."""


# %% [f3] F.3 Sensitivity Jacobian $G^T = \partial \mathbf{g}^{\ast} / \partial \mathbf{q}$ (sections 3.2 to 3.5)
r"""How does the optimizer know which $q_j$ to adjust and by how much? Differentiating $C^T Q \mathbf{u}(\mathbf{q}) = \mathbf{p}_x$ with respect to $\mathbf{q}$ gives the node-position sensitivity $\partial \mathbf{x} / \partial \mathbf{q} = -D^{-1} C^T U$, which projects onto the cable directions to form the **constraint Jacobian** $G^T = \partial \mathbf{g}^{\ast} / \partial \mathbf{q}$ (Schek Sec. 3.2–3.5, Eqs. 28–35).

### General Equations (Eqs. 28 & 31)

$$
\frac{\partial \mathbf{x}}{\partial \mathbf{q}} = -D^{-1} C^T U, \qquad
\frac{\partial \mathbf{y}}{\partial \mathbf{q}} = -D^{-1} C^T V, \qquad
\frac{\partial \mathbf{z}}{\partial \mathbf{q}} = -D^{-1} C^T W, \qquad
G^T = \frac{\partial \mathbf{g}^{\ast}}{\partial \mathbf{q}}
$$

* $\partial \mathbf{x} / \partial \mathbf{q},\ \partial \mathbf{y} / \partial \mathbf{q},\ \partial \mathbf{z} / \partial \mathbf{q}$ $(5 \times 12)$: how many meters each free node $i$ moves per unit increase in $q_j$.
* $G^T = \partial \mathbf{g}^{\ast} / \partial \mathbf{q}$ $(r \times 12)$: rate of change of constraint $i$ with respect to $q_j$. Diagonal entries are negative ($-0.313, -0.358$) because tightening cable $j$ ($\Delta q_j > 0$) shortens its own length ($\Delta l_j < 0$).

### Matrix Example (Anchor Length Jacobian $G^T_{1..4,\ 1..4}$ and Height Sensitivity)

$$
G^T_{1..4,\ 1..4} =
\begin{bmatrix}
-0.313 & 0.002 & 0.073 & 0.002 \\
0.002 & -0.358 & 0.002 & 0.044 \\
0.073 & 0.002 & -0.313 & 0.002 \\
0.002 & 0.044 & 0.002 & -0.358
\end{bmatrix}
\begin{matrix}
\leftarrow \partial l_1 / \partial q_{1..4}\ (\text{raising } q_1\text{ shortens } l_1\text{ by }-0.313\text{ m per kN/m}) \\
\leftarrow \partial l_2 / \partial q_{1..4}\ (\text{raising } q_2\text{ shortens } l_2\text{ by }-0.358\text{ m per kN/m}) \\
\leftarrow \partial l_3 / \partial q_{1..4}\ (\text{raising } q_3\text{ shortens } l_3\text{ by }-0.313\text{ m per kN/m}) \\
\leftarrow \partial l_4 / \partial q_{1..4}\ (\text{raising } q_4\text{ shortens } l_4\text{ by }-0.358\text{ m per kN/m})
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
\leftarrow \text{Node 1 (pulled down }-0.012\text{ by } q_1,\text{ lifted }+0.060\text{ by } q_2, q_4\text{)} \\
\leftarrow \text{Node 2 (rises }+0.175\text{ m per kN/m when } q_2\text{ is tightened)} \\
\leftarrow \text{Node 3 (pulled down }-0.012\text{ by } q_3,\text{ lifted }+0.060\text{ by } q_2, q_4\text{)} \\
\leftarrow \text{Node 4 (rises }+0.175\text{ m per kN/m when } q_4\text{ is tightened)} \\
\leftarrow \text{Node 5 (center rises }+0.084\text{ m per kN/m when } q_2, q_4\text{ are tightened)}
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


G_t = sensitivity(q, [0, 1, 2, 3])


# %% explain
r"""* Column `j` of `G_t` (`shape (4, 12)`) is computed by copying `q`, nudging `q_nudged[j] += step` (`1e-6`), re-running `form_finding`, and dividing the length change by `step`.
* These finite differences match Schek's analytic Jacobian formulas (Eqs. 31, 34, 35 in `schek_equations.py`) to 3 decimal places."""


# %% [g1] G.1 Larger network: the 67-node, 110-branch pointed tent (section 5, figure 5)
r"""Apply the exact same `form_finding` function without modification to Schek's larger pointed-tent network ($n = 61$ free nodes, $n_f = 6$ fixed supports including high apex node 67, $m = 110$ branches).

![Fig. 5](images/schek_fig5.png)

### Problem Dimensions & Prescribed Force Densities

| Matrix / Vector | Fig. 2 Net (Parts A–F) | Fig. 5 Tent (Part G) |
|---|---|---|
| Connectivity $C_s = [C \mid C_f]$ | $(12 \times 5)\ \big\|\ (12 \times 4)$ | $(110 \times 61)\ \big\|\ (110 \times 6)$ |
| Diagonal Force Density $Q$ | $(12 \times 12)$ | $(110 \times 110)$ |
| Free System Matrix $D = C^T Q C$ | $(5 \times 5)$ | $(61 \times 61)$ |

$$
q_j = \begin{cases}
100.0 & \text{29 border cables (stiff edge)} \\
0.5 & \text{10 radial apex cables (long)} \\
1.0 & \text{71 interior field cables}
\end{cases}
$$"""
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
free5, fixed5 = 61, [62, 63, 64, 65, 66, 67]
q5 = np.array([
    100.0 if tuple(sorted(e)) in border5 else 0.5 if 67 in e else 1.0
    for e in branches5
])
p5 = np.zeros((free5, 3))
p5[:, 2] = -0.4
is_spoke = np.array([67 in e for e in branches5])
is_border = np.array([tuple(sorted(e)) in border5 for e in branches5])
touches_border = np.array([any(k in BORDER for k in e) for e in branches5])


def anchors5(apex_dx=0.0, apex_dy=0.0, apex_h=16.0):
    A = np.c_[xy[61:67], np.zeros(6)]
    A[5] += [apex_dx, apex_dy, apex_h]
    return A


shapes = {}


def keep(name, brs, xyz_free_nodes, xyz_fixed_nodes, fixed_nodes):
    shapes[name] = {
        "branches": [list(e) for e in brs],
        "xyz": np.vstack([xyz_free_nodes, xyz_fixed_nodes]).tolist(),
        "fixed": list(fixed_nodes),
    }


# %% explain
r"""* Boolean masks `is_spoke`, `is_border`, and `touches_border` (`shape (110,)`) classify each branch so we can selectively modify $q$ or slice lengths `l[is_spoke]`.
* A $200\times$ ratio between border cables ($q = 100$) and radial cables ($q = 0.5$) keeps the boundary scallops taut while letting the radial cables drape steeply to the $16\text{ m}$ apex."""


# %% [g2] G.2 Figure 6: shifting fixed support coordinates
r"""Translate the high apex support (node 67) horizontally in plan by $(\Delta x, \Delta y) = (0, 0),\ (6, 2),\ (12, 4)\text{ m}$. Because $\mathbf{q}$ is unchanged, $D\ (61 \times 61)$ is invariant and only the right-hand side $\mathbf{P} - D_f \mathbf{X}_f$ updates.

![Fig. 1](images/schek_fig1.png)

![Fig. 6](images/schek_fig6_persp.png)
![Fig. 6, plan](images/schek_fig6_plan.png)

### Apex Shift Summary

| Run | Apex Shift $(\Delta x, \Delta y)$ | Radial Length Range | Vertical Apex Reaction $R_{67, z}$ |
|---|---|---|---|
| `fig6_1` | $(0, 0)\text{ m}$ | $8.1\text{ to }9.0\text{ m}$ | $38.9\text{ kN}$ |
| `fig6_2` | $(6, 2)\text{ m}$ | $8.0\text{ to }9.3\text{ m}$ | $38.9\text{ kN}$ |
| `fig6_3` | $(12, 4)\text{ m}$ | $8.4\text{ to }10.9\text{ m}$ | $38.9\text{ kN}$ |"""
fig6_shifts = [("fig6_1", (0, 0)), ("fig6_2", (6, 2)), ("fig6_3", (12, 4))]
for name, (dx, dy) in fig6_shifts:
    xyz_6, l_6, s_6, R_6 = form_finding(
        branches5, free5, anchors5(dx, dy), q5, p5
    )
    keep(name, branches5, xyz_6, anchors5(dx, dy), fixed5)

xyz_fig1, *_ = form_finding(branches5, free5, anchors5(), q5, p5)
keep("fig1", branches5, xyz_fig1, anchors5(), fixed5)


# %% explain
r"""* Shifting the apex horizontally changes only the $x$ and $y$ right-hand sides; the $z$ system $D \mathbf{z} = \mathbf{p}_z - D_f \mathbf{z}_f$ is completely untouched, so the vertical apex reaction stays constant at $38.9\text{ kN}$."""


# %% [g3] G.3 Figures 7 and 8: varying radial and border force densities
r"""Vary the radial force density $q_{\text{spoke}} \in \{1.0, 0.7, 0.3\}$ (Fig. 7) and border force density $q_{\text{border}} \in \{10, 5, 1\}$ (Fig. 8), rebuilding $D = C^T Q C$ each time.

![Fig. 7](images/schek_fig7_persp.png)
![Fig. 7, plan](images/schek_fig7_plan.png)

![Fig. 8](images/schek_fig8_persp.png)
![Fig. 8, plan](images/schek_fig8_plan.png)

### Parameter Study Results

| Fig. 7 Run | $q_{\text{spoke}}$ | Radial Lengths | Fig. 8 Run | $q_{\text{border}}$ | Border Lengths |
|---|---|---|---|---|---|
| `fig7_1` | $1.0$ | $5.0\text{ to }5.9\text{ m}$ | `fig8_1` | $10.0$ | $3.4\text{ to }4.8\text{ m}$ |
| `fig7_2` | $0.7$ | $6.5\text{ to }7.4\text{ m}$ | `fig8_2` | $5.0$ | $3.5\text{ to }4.9\text{ m}$ |
| `fig7_3` | $0.3$ | $10.6\text{ to }11.6\text{ m}$ | `fig8_3` | $1.0$ | $2.9\text{ to }6.5\text{ m}$ |"""
for name, qs in zip(["fig7_1", "fig7_2", "fig7_3"], [1.0, 0.7, 0.3]):
    q_spoke_run = np.where(is_spoke, qs, q5)
    xyz_7, l_7, *_ = form_finding(
        branches5, free5, anchors5(), q_spoke_run, p5
    )
    keep(name, branches5, xyz_7, anchors5(), fixed5)

for name, qb in zip(["fig8_1", "fig8_2", "fig8_3"], [10.0, 5.0, 1.0]):
    q_border_run = np.where(is_border, qb, q5)
    xyz_8, l_8, *_ = form_finding(
        branches5, free5, anchors5(), q_border_run, p5
    )
    keep(name, branches5, xyz_8, anchors5(), fixed5)


# %% explain
r"""* `np.where(is_spoke, qs, q5)` replaces $q$ only on the 10 radial spokes (`is_spoke == True`) and keeps `q5` elsewhere.
* Reducing $q_{\text{spoke}}$ from $1.0 \to 0.3$ doubles the radial cable lengths ($5.5\text{ m} \to 11.1\text{ m}$), making the tent steeper and more pointed."""


# %% [g4] G.4 Figure 9: prescribed length constraints on 62 interior branches
r"""Constrain all $r = 62$ interior branches not touching the boundary ($10$ radial cables set to $l_{\text{radial}}$, $52$ ring/field cables scaled by `ring_factor`) across $m = 110$ force densities.

### Constrained Runs (62 Equations in 110 Unknowns)

| Run | Target $l_{\text{radial}}$ | Ring Scale Factor | Evaluations | $\max \|\mathbf{g}^*(\mathbf{q})\|$ |
|---|---|---|---|---|
| `fig9_1` | $6.0\text{ m}$ | $1.25 \times \mathbf{l}_{\text{base}}$ | $35$ | $3.8 \times 10^{-9}\text{ m}$ |
| `fig9_2` | $6.0\text{ m}$ | $0.85 \times \mathbf{l}_{\text{base}}$ | $38$ | $6.3 \times 10^{-12}\text{ m}$ |
| `fig9_3` | $4.5\text{ m}$ | $0.70 \times \mathbf{l}_{\text{base}}$ | $47$ | $9.1 \times 10^{-10}\text{ m}$ |"""
base_l = form_finding(branches5, free5, anchors5(), q5, p5)[1]
inner = [j for j in range(len(branches5)) if not touches_border[j]]
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


# %% explain
r"""* Bounded trust-region least squares satisfies all 62 length constraints to $\sim 10^{-9}\text{ m}$ on all three cases."""


# %% [g5] G.5 Figure 10: 8x8 grid-shell of 112 bars
r"""Generate an $8 \times 8$ orthogonal grid ($n = 60$ free nodes, $n_f = 4$ corner supports, $m = 112$ bars) and solve three benchmark problems: (10.1) hanging net of 112 equal-length $1.0\text{ m}$ bars under self-weight, (10.2) prestressed saddle with raised corners, and (10.3) mixed equal-length and equal-force constraints.

### Summary of the Three 112-Bar Cases

| Case | Corner Supports | Load $\mathbf{P}$ | Constraints | Result |
|---|---|---|---|---|
| `fig10_1` | 4 corners at 80% span | bar weight | $l_j = 1.0\text{ m}\ (\forall j=1..112)$ | $\|\mathbf{e}_l\| \le 7.6\times 10^{-10}\text{ m},\ s \in [0.12, 2.77]\text{ kN}$ |
| `fig10_2` | 2 corners lifted to $3\text{ m}$ | $\mathbf{0}$ | linear ($q_{\text{border}}=10, q_{\text{in}}=1$) | $l_{\text{in}} \in [0.65, 0.81]\text{ m}$ |
| `fig10_3` | 2 corners lifted to $3\text{ m}$ | $\mathbf{0}$ | equal inner $l$ + equal link $s$ | $\|\mathbf{g}^*\| \le 1.6\times 10^{-8}$ |"""
g = 8
gid = {(i, k): i * g + k + 1 for i in range(g) for k in range(g)}
grid_h = [(gid[i, k], gid[i, k + 1]) for i in range(g) for k in range(g - 1)]
grid_v = [(gid[i, k], gid[i + 1, k]) for i in range(g - 1) for k in range(g)]
grid = grid_h + grid_v
corners = [gid[0, 0], gid[0, g - 1], gid[g - 1, g - 1], gid[g - 1, 0]]
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
degree = np.bincount(np.array(grid).ravel())[1:]
p10 = np.zeros((g * g - 4, 3))
p10[:, 2] = -0.5 * weight * degree[: g * g - 4]
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


# %% explain
r"""* `order` renumbers the $8 \times 8$ grid so the $60$ free nodes come first (`1..60`) and the $4$ corner supports come last (`61..64`), matching our `[C | C_f]` partition rule from A.2.
* `degree = np.bincount(np.array(grid).ravel())[1:]` counts how many bars meet at each node so each bar's weight ($0.15\text{ kN}$) is lumped half-and-half onto its two endpoints.
* **Key Takeaway (`fig10_1`):** Even when all 112 bars have identical length $l_j = 1.000\text{ m}$, their forces span a $23\times$ range ($0.12\text{ to } 2.77\text{ kN}$)—uniform geometry does not imply uniform force."""


# %% [g6] G.6 Export computed shapes for figure generation
r"""Write all computed 3D shapes (`fig1`, `fig5_plan`, `fig6_1`..`fig10_3`) to `shapes.json` so `schek_1974_figures.py` can plot them."""
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
out.write_text(json.dumps(shapes))


# %% explain
r"""* `shapes` maps each figure name to its branch list, its $(n_s \times 3)$ coordinate table, and fixed node indices; `json.dumps` serializes the dictionary to `shapes.json`."""
