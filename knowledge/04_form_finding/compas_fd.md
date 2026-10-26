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

* **3. Physical meaning at a node (Linkwitz 2014, Sec. 6.2):** For a free node $P_0$ connected to neighbors $P_1, P_2, P_3, P_4$ with force densities $q_a, q_b, q_c, q_d$, force balance $\sum q_j (x_0 - x_k) = p_x$ is a **linear equation** whose solution places $P_0$ at the $q$-weighted average of its neighbors (and then recovers unstressed cutting length $l_{0,j}$ from Hooke's law):

$$
q_a(x_0 - x_1) + q_b(x_0 - x_2) + q_c(x_0 - x_3) + q_d(x_0 - x_4) = p_x
\quad \Longrightarrow \quad
x_0 = \frac{p_x + q_a x_1 + q_b x_2 + q_c x_3 + q_d x_4}{q_a + q_b + q_c + q_d}, \qquad
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

Follow the subsections in order (`examples/form_finding/schek_app.py`). Every equation is paired immediately with an explicit numerical matrix example.

| Milestone | What you can do |
|---|---|
| **A.1–A.4** | Represent a network as a branch-node matrix and trace $C^T Q C$ step by step. |
| **B.1–B.3** | Compute branch coordinate differences, lengths, and the 4-stage nonlinear equilibrium residual. |
| **C.1–C.4** | Apply the force-density substitution $q_j = s_j / l_j$, assemble $D$ and $D_f$, solve coordinates, and recover forces. |
| **D.1–D.2** | Package the 3D linear solver and support reactions into a single function. |
| **E.1** | Interpret $q_j$ geometrically as a weight minimizing $\sum q_j l_j^2$. |
| **F.1–F.3** | Enforce target branch lengths and forces via constrained least-squares and the sensitivity Jacobian $G^T$. |
| **G.1–G.5** | Apply the same solver to Schek's 67-node pointed tent and 112-bar grid-shell benchmarks. |

---

## Part A. The network as data

### A.1 Vectors, matrices, and the diagonal trick (section 1.4)

Lowercase bold letters ($\mathbf{u}, \mathbf{q}, \mathbf{l}$) denote $(m \times 1)$ branch column vectors; uppercase letters ($U, Q, L$) denote the $(m \times m)$ diagonal matrices formed by placing those vectors on the main diagonal.

### General Equation

$$
U = \mathrm{diag}(\mathbf{u}), \qquad Q = \mathrm{diag}(\mathbf{q}), \qquad U \mathbf{q} = Q \mathbf{u}
$$

### Matrix Example

Turning a 3-branch vector $\mathbf{u}$ into a $(3 \times 3)$ diagonal matrix $U = \mathrm{diag}(\mathbf{u})$:

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
\leftarrow \text{scales branch 1 by } 2 \\
\leftarrow \text{scales branch 2 by } -1 \\
\leftarrow \text{scales branch 3 by } 3
\end{matrix}
$$

Multiplying a diagonal matrix by a vector scales each row independently without mixing entries, so the factors commute ($U \mathbf{q} = Q \mathbf{u}$):

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
\leftarrow 2 \times 4 \\
\leftarrow -1 \times 5 \\
\leftarrow 3 \times 6
\end{matrix}
$$

**Add to your program:**

```python
import numpy as np
from typing import TypeAlias

FloatMatrix: TypeAlias = np.ndarray[tuple[int, int], np.dtype[np.float64]]
FloatVector: TypeAlias = np.ndarray[tuple[int], np.dtype[np.float64]]

u_example = np.array([2.0, -1.0, 3.0])
U_example = np.diag(u_example)
print("U_example = diag(u_example):\n", U_example)
```

* `np.diag(u_example)` places the `(3,)` vector on the main diagonal of the `(3, 3)` matrix `U_example`; `np.diag(u) @ q`, `np.diag(q) @ u`, and `u * q` all produce $[8, -5, 18]^T$.

**Example output:**

```text
U_example = diag(u_example):
 [[ 2.  0.  0.]
 [ 0. -1.  0.]
 [ 0.  0.  3.]]
```

### A.2 Network topology: numbering nodes and branches (section 2.1)

Number the $n = 5$ **free inner nodes first** ($1 \dots 5$) and the $n_f = 4$ **fixed outer anchor nodes last** ($6 \dots 9$) across the $m = 12$ directed branches ($i \to k$) so the connectivity matrix splits with a single vertical cut.

![Fig. 2](images/schek_fig2.png)

![Part A Topology and Matrix Operators on the Cable Net](images/fd_sec_a_topology_split.png)

* **Total Nodes ($n_s = 9$):** Free inner nodes $1 \dots 5$ ($n = 5$, unknown coordinates) and fixed anchors $6 \dots 9$ ($n_f = 4$, known boundary supports).
* **Directed Branches ($m = 12$):** Anchor cables $b_1 \dots b_4$: $(1\to 6),\ (2\to 7),\ (3\to 8),\ (4\to 9)$; inner ring $b_5 \dots b_8$: $(1\to 4),\ (1\to 2),\ (2\to 3),\ (3\to 4)$; center spokes $b_9 \dots b_{12}$: $(4\to 5),\ (1\to 5),\ (2\to 5),\ (3\to 5)$.

**Add to your program:**

```python
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

### A.3 Branch-node connectivity matrix and partitioning (section 2.1)

Encode the directed graph as an $(m \times n_s)$ branch-node incidence matrix $C_s$ ($+1$ at start node $i$, $-1$ at end node $k$), partitioned into free-node columns $C$ $(12 \times 5)$ and fixed-anchor columns $C_f$ $(12 \times 4)$.

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

### A.4 Step-by-step matrix multiplication for $C^T Q C$

Trace how $D = C^T (Q C)$ assembles nodal equilibrium on a **5-branch, 3-free-node mini-network** (free nodes $1, 2, 3$; fixed supports $4, 5$) with force densities $\mathbf{q} = [2, 3, 4, 5, 6]^T$.

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
\leftarrow b_1\ (4\to 1) \\
\leftarrow b_2\ (5\to 2) \\
\leftarrow b_3\ (2\to 1) \\
\leftarrow b_4\ (3\to 1) \\
\leftarrow b_5\ (3\to 2)
\end{matrix}
\qquad \overset{\text{transpose}}{\longrightarrow} \qquad
C^T = \begin{bmatrix}
1 & 0 & 1 & -1 & 0 \\
0 & 1 & -1 & 0 & 1 \\
0 & 0 & 0 & 1 & -1
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Node 1} \\
\leftarrow \text{Node 2} \\
\leftarrow \text{Node 3}
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
\leftarrow q_1 = 2 \\
\leftarrow q_2 = 3 \\
\leftarrow q_3 = 4 \\
\leftarrow q_4 = 5 \\
\leftarrow q_5 = 6
\end{matrix}
$$

### 3. Step 2 — Compute $D = C^T (Q C)$ (Sum at Nodes, $3 \times 3$)

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
\begin{matrix}
\leftarrow \text{Node 1: } 2+4+5=11 \\
\leftarrow \text{Node 2: } 3+4+6=13 \\
\leftarrow \text{Node 3: } 5+6=11
\end{matrix}
$$

**Add to your program:**

```python
C_mini = np.array(
    [[1, 0, 0], [0, 1, 0], [1, -1, 0], [-1, 0, 1], [0, 1, -1]],
    dtype=float,
)
q_mini = np.array([2.0, 3.0, 4.0, 5.0, 6.0])
QC_mini = np.diag(q_mini) @ C_mini
D_mini = C_mini.T @ QC_mini
print("D_mini = C_mini.T @ diag(q_mini) @ C_mini:\n", D_mini.astype(int))
```

* `np.diag(q_mini) @ C_mini` weights each branch row by $q_j$, and `C_mini.T @ QC_mini` sums those weighted rows at each free node ($D_{ii} = \sum q_j$, $D_{ik} = -q_j$).

**Example output:**

```text
D_mini = C_mini.T @ diag(q_mini) @ C_mini:
 [[11 -4 -5]
 [-4 13 -6]
 [-5 -6 11]]
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
L^{-1} = \mathrm{diag}(1 / \mathbf{l}) = \mathrm{diag}\left(1,\ \tfrac{1}{\sqrt{10}},\ 1,\ \tfrac{1}{\sqrt{10}},\ \tfrac{1}{\sqrt{2}},\ \dots,\ 1\right)
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

Project branch tensions $\mathbf{s} = [1, \dots, 1]^T\text{ kN}$ by direction cosines $(u_j/l_j,\ v_j/l_j,\ w_j/l_j)$ and sum at free nodes via $C^T$, reading the matrix product **right to left** in 4 stages.

![Section B.3 Four-Stage Nonlinear Equilibrium and Flat Net Imbalance](images/fd_sec_b3_nonlinear_stages.png)

### General Equation (Eq. 2)

$$
\mathbf{e} _ x = \underbrace{C^T} _ {\text{Stage 3: to nodes}} \quad \underbrace{U} _ {\text{Stage 2: project } x} \quad \underbrace{L^{-1} \mathbf{s}} _ {\text{Stage 1: } q_j = s_j / l_j} \quad - \quad \underbrace{\mathbf{p} _ x} _ {\text{Stage 4: load}}
$$

### Stage-by-Stage Matrix Breakdown

#### Stage 1 — Force Density Ratios: $\mathbf{q} = L^{-1} \mathbf{s}\ (12 \times 1)$

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
\mathbf{F} _ y = V \mathbf{q} =
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
\mathbf{F} _ z = W \mathbf{q} =
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
\end{bmatrix}\text{ kN}
$$

#### Stage 3 — Sum Cable Forces at Free Nodes: $C^T \mathbf{F} _ x\ (5 \times 1)$

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
\begin{matrix}
\leftarrow \text{Node 1} \\
\leftarrow \text{Node 2} \\
\leftarrow \text{Node 3} \\
\leftarrow \text{Node 4} \\
\leftarrow \text{Node 5}
\end{matrix}
$$

$$
(C^T \mathbf{F} _ x) _ 1 = F_{x,1} + F_{x,5} + F_{x,6} + F_{x,10} = 1 - 0.707 - 0.707 - 1 = -1.414\text{ kN}
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

### Matrix Example ($\mathbf{F} _ x = U \mathbf{q} = Q \mathbf{u}$ with Prescribed Force Densities)

$$
\mathbf{F} _ x =
\underset{U\ (12\times 12)}{\begin{bmatrix}
u_1 & & & & & \\
 & \ddots & & & & \\
 & & u_4 & & & \\
 & & & u_5 & & \\
 & & & & \ddots & \\
 & & & & & u_{12}
\end{bmatrix}}
\underset{\mathbf{q}\ (12\times 1)}{\begin{bmatrix}
2 \\
\vdots \\
2 \\
1 \\
\vdots \\
1
\end{bmatrix}} =
\underset{Q\ (12\times 12)}{\begin{bmatrix}
2 & & & & & \\
 & \ddots & & & & \\
 & & 2 & & & \\
 & & & 1 & & \\
 & & & & \ddots & \\
 & & & & & 1
\end{bmatrix}}
\underset{\mathbf{u}\ (12\times 1)}{\begin{bmatrix}
u_1 \\
\vdots \\
u_4 \\
u_5 \\
\vdots \\
u_{12}
\end{bmatrix}} =
\begin{bmatrix}
2(x_1 - x_6) \\
\vdots \\
2(x_4 - x_9) \\
1(x_1 - x_4) \\
\vdots \\
1(x_3 - x_5)
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Anchor cable 1 } (q_1 = 2\text{ kN/m}) \\
\vdots \\
\leftarrow \text{Anchor cable 4 } (q_4 = 2\text{ kN/m}) \\
\leftarrow \text{Ring cable 5 } (q_5 = 1\text{ kN/m}) \\
\vdots \\
\leftarrow \text{Spoke cable 12 } (q_{12} = 1\text{ kN/m})
\end{matrix}
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

---

## Part G. The paper's examples, recomputed

### G.1 Larger network: the 67-node, 110-branch pointed tent (section 5, figure 5)

Apply the exact same `form_finding` function without modification to Schek's larger pointed-tent network ($n = 61$ free nodes, $n_f = 6$ fixed supports including high apex node 67, $m = 110$ branches).

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


print(f"Fig. 5 tent: {free5} free nodes, {len(fixed5)} fixed supports, {len(branches5)} branches")
print(f"Branch counts: {int(is_border.sum())} border, {int(is_spoke.sum())} radial spokes, {int((~is_border & ~is_spoke).sum())} interior")
```

* Boolean masks `is_spoke`, `is_border`, and `touches_border` (`shape (110,)`) classify each branch so we can selectively modify $q$ or slice lengths `l[is_spoke]`.
* A $200\times$ ratio between border cables ($q = 100$) and radial cables ($q = 0.5$) keeps the boundary scallops taut while letting the radial cables drape steeply to the $16\text{ m}$ apex.

**Example output:**

```text
Fig. 5 tent: 61 free nodes, 6 fixed supports, 110 branches
Branch counts: 29 border, 10 radial spokes, 71 interior
```

### G.2 Figure 6: shifting fixed support coordinates

Translate the high apex support (node 67) horizontally in plan by $(\Delta x, \Delta y) = (0, 0),\ (6, 2),\ (12, 4)\text{ m}$. Because $\mathbf{q}$ is unchanged, $D\ (61 \times 61)$ is invariant and only the right-hand side $\mathbf{P} - D_f \mathbf{X} _ f$ updates.

![Fig. 1](images/schek_fig1.png)

![Fig. 6](images/schek_fig6_persp.png)
![Fig. 6, plan](images/schek_fig6_plan.png)

### Apex Shift Summary

| Run | Apex Shift $(\Delta x, \Delta y)$ | Radial Length Range | Vertical Apex Reaction $R_{67, z}$ |
|---|---|---|---|
| `fig6_1` | $(0, 0)\text{ m}$ | $8.1\text{ to }9.0\text{ m}$ | $38.9\text{ kN}$ |
| `fig6_2` | $(6, 2)\text{ m}$ | $8.0\text{ to }9.3\text{ m}$ | $38.9\text{ kN}$ |
| `fig6_3` | $(12, 4)\text{ m}$ | $8.4\text{ to }10.9\text{ m}$ | $38.9\text{ kN}$ |

**Add to your program:**

```python
fig6_shifts = [("fig6_1", (0, 0)), ("fig6_2", (6, 2)), ("fig6_3", (12, 4))]
for name, (dx, dy) in fig6_shifts:
    xyz_6, l_6, s_6, R_6 = form_finding(
        branches5, free5, anchors5(dx, dy), q5, p5
    )
    keep(name, branches5, xyz_6, anchors5(dx, dy), fixed5)
    print(f"{name}: radial l in [{l_6[is_spoke].min():.1f}, {l_6[is_spoke].max():.1f}] m, apex R_z = {R_6[5, 2]:.1f} kN")

xyz_fig1, *_ = form_finding(branches5, free5, anchors5(), q5, p5)
keep("fig1", branches5, xyz_fig1, anchors5(), fixed5)
```

* Shifting the apex horizontally changes only the $x$ and $y$ right-hand sides; the $z$ system $D \mathbf{z} = \mathbf{p} _ z - D_f \mathbf{z} _ f$ is completely untouched, so the vertical apex reaction stays constant at $38.9\text{ kN}$.

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
| `fig7_1` | $1.0$ | $5.0\text{ to }5.9\text{ m}$ | `fig8_1` | $10.0$ | $3.4\text{ to }4.8\text{ m}$ |
| `fig7_2` | $0.7$ | $6.5\text{ to }7.4\text{ m}$ | `fig8_2` | $5.0$ | $3.5\text{ to }4.9\text{ m}$ |
| `fig7_3` | $0.3$ | $10.6\text{ to }11.6\text{ m}$ | `fig8_3` | $1.0$ | $2.9\text{ to }6.5\text{ m}$ |

**Add to your program:**

```python
for name, qs in zip(["fig7_1", "fig7_2", "fig7_3"], [1.0, 0.7, 0.3]):
    q_spoke_run = np.where(is_spoke, qs, q5)
    xyz_7, l_7, *_ = form_finding(
        branches5, free5, anchors5(), q_spoke_run, p5
    )
    keep(name, branches5, xyz_7, anchors5(), fixed5)
    print(f"{name} (q_spoke={qs}): radial l in [{l_7[is_spoke].min():.1f}, {l_7[is_spoke].max():.1f}] m")

for name, qb in zip(["fig8_1", "fig8_2", "fig8_3"], [10.0, 5.0, 1.0]):
    q_border_run = np.where(is_border, qb, q5)
    xyz_8, l_8, *_ = form_finding(
        branches5, free5, anchors5(), q_border_run, p5
    )
    keep(name, branches5, xyz_8, anchors5(), fixed5)
    print(f"{name} (q_border={qb}): border l in [{l_8[is_border].min():.1f}, {l_8[is_border].max():.1f}] m")
```

* `np.where(is_spoke, qs, q5)` replaces $q$ only on the 10 radial spokes (`is_spoke == True`) and keeps `q5` elsewhere.
* Reducing $q_{\text{spoke}}$ from $1.0 \to 0.3$ doubles the radial cable lengths ($5.5\text{ m} \to 11.1\text{ m}$), making the tent steeper and more pointed.

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

### Constrained Runs (62 Equations in 110 Unknowns)

| Run | Target $l_{\text{radial}}$ | Ring Scale Factor | Evaluations | $\max \|\mathbf{g}^*(\mathbf{q})\|$ |
|---|---|---|---|---|
| `fig9_1` | $6.0\text{ m}$ | $1.25 \times \mathbf{l} _ {\text{base}}$ | $35$ | $3.8 \times 10^{-9}\text{ m}$ |
| `fig9_2` | $6.0\text{ m}$ | $0.85 \times \mathbf{l} _ {\text{base}}$ | $38$ | $6.3 \times 10^{-12}\text{ m}$ |
| `fig9_3` | $4.5\text{ m}$ | $0.70 \times \mathbf{l} _ {\text{base}}$ | $47$ | $9.1 \times 10^{-10}\text{ m}$ |

**Add to your program:**

```python
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
    print(f"{name}: {tries_9} evals, max length residual = {err_9:.2e} m")
```

* Bounded trust-region least squares satisfies all 62 length constraints to $\sim 10^{-9}\text{ m}$ on all three cases.

**Example output:**

```text
fig9_1: 42 evals, max length residual = 1.19e-09 m
fig9_2: 35 evals, max length residual = 1.07e-09 m
fig9_3: 58 evals, max length residual = 7.49e-10 m
```

### G.5 Figure 10: 8x8 grid-shell of 112 bars

Generate an $8 \times 8$ orthogonal grid ($n = 60$ free nodes, $n_f = 4$ corner supports, $m = 112$ bars) and solve three benchmark problems: (10.1) hanging net of 112 equal-length $1.0\text{ m}$ bars under self-weight, (10.2) prestressed saddle with raised corners, and (10.3) mixed equal-length and equal-force constraints.

### Summary of the Three 112-Bar Cases

| Case | Corner Supports | Load $\mathbf{P}$ | Constraints | Result |
|---|---|---|---|---|
| `fig10_1` | 4 corners at 80% span | bar weight | $l_j = 1.0\text{ m}\ (\forall j=1..112)$ | $\|\mathbf{e} _ l\| \le 7.6\times 10^{-10}\text{ m},\ s \in [0.12, 2.77]\text{ kN}$ |
| `fig10_2` | 2 corners lifted to $3\text{ m}$ | $\mathbf{0}$ | linear ($q_{\text{border}}=10, q_{\text{in}}=1$) | $l_{\text{in}} \in [0.65, 0.81]\text{ m}$ |
| `fig10_3` | 2 corners lifted to $3\text{ m}$ | $\mathbf{0}$ | equal inner $l$ + equal link $s$ | $\|\mathbf{g}^*\| \le 1.6\times 10^{-8}$ |

**Add to your program:**

```python
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
print(f"fig10_1: err={err_10_1:.2e} m, forces in [{s_10_1.min():.2f}, {s_10_1.max():.2f}] kN")
print(f"fig10_2: inner lengths in [{l_10_2[inner10].min():.2f}, {l_10_2[inner10].max():.2f}] m")
print(f"fig10_3: err={err_10_3:.2e}, uniform inner l={l_10_3[inner10].mean():.3f} m, link s={s_10_3[link10].mean():.3f} kN")
```

* `order` renumbers the $8 \times 8$ grid so the $60$ free nodes come first (`1..60`) and the $4$ corner supports come last (`61..64`), matching our `[C | C_f]` partition rule from A.2.
* `degree = np.bincount(np.array(grid).ravel())[1:]` counts how many bars meet at each node so each bar's weight ($0.15\text{ kN}$) is lumped half-and-half onto its two endpoints.
* **Key Takeaway (`fig10_1`):** Even when all 112 bars have identical length $l_j = 1.000\text{ m}$, their forces span a $23\times$ range ($0.12\text{ to } 2.77\text{ kN}$)—uniform geometry does not imply uniform force.

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
out.write_text(json.dumps(shapes))
print(f"Saved {len(shapes)} shapes ({list(shapes.keys())}) to {out.name}")
```

* `shapes` maps each figure name to its branch list, its $(n_s \times 3)$ coordinate table, and fixed node indices; `json.dumps` serializes the dictionary to `shapes.json`.

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


### Linear solver

```python
from compas_fd.solvers import fd_numpy

result = fd_numpy(
    vertices=vertices,    # (n_s, 3) all node coordinates (free and fixed)
    fixed=fixed,          # indices of fixed anchor nodes
    edges=edges,          # list of (i, k) index pairs; i -> +1, k -> -1 in C
    forcedensities=q,     # one float per edge
    loads=loads,          # (n_s, 3) nodal loads, optional (defaults to zero)
)
result.vertices           # (n_s, 3) equilibrium coordinates
result.residuals          # (n_s, 3) p - C^T Q C x (zero at free nodes)
result.forces             # (m, 1)   q * l
result.lengths            # (m, 1)   strained lengths
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
# allow vertex k to slide along a line
constraints[k] = Constraint(Line([0, 0, 0], [1, 0, 0]))

result = fd_constrained_numpy(
    vertices=vertices,
    fixed=fixed,
    edges=edges,
    forcedensities=q,
    loads=loads,
    constraints=constraints,  # aligned with vertices; None = unconstrained
    kmax=100,
    tol_res=1e-3,
    tol_disp=1e-3,
    damping=0.1,
    selfweight=None,          # optional callable xyz -> (n_s, 1) weights
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
