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

**Force density.** For branch $j$ with axial tension force $s_j$ ($\text{kN}$) and strained geometric length $l_j$ ($\text{m}$), the force density $q_j$ ($\text{kN/m}$) is the force-to-length ratio:

$$
q_j = \frac{s_j}{l_j}
\qquad \Longrightarrow \qquad
\text{Example (1 cable):}\quad l = 2.5\text{ m},\quad s = 10\text{ kN} \implies q = \frac{10\text{ kN}}{2.5\text{ m}} = 4\text{ kN/m}
$$

Prescribing $q_j$ for every branch cancels the nonlinear branch lengths $l_j$ out of nodal equilibrium, transforming 3D form-finding into a direct linear system $D \mathbf{x} = \mathbf{p}_x - D_f \mathbf{x}_f$.

**Model assumptions (Schek 1974, section 1):**

- Branches are straight pin-jointed axial members (cables or bars); loads act only at nodes.
- Nodes are partitioned into **free inner nodes** ($n$ unknown coordinates) and **fixed boundary anchors** ($n_f$ prescribed coordinates).
- **Sign conventions:** $q_j > 0$ and $s_j > 0$ denote tension. When all $q_j > 0$ and every connected free-node component reaches at least one fixed anchor, $D = C^T Q C$ is symmetric positive-definite with a unique equilibrium shape.
- **Units:** Consistent across coordinates ($\text{m}$), loads ($\text{kN}$), and force densities ($\text{kN/m}$).

## Symbol & shape reference (12-branch, 9-node benchmark)

| Symbol | Code | Meaning | Shape |
|---|---|---|---|
| $C_s = [C \mid C_f]$ | `C_s`, `C`, `C_f` | Branch-node connectivity matrix: free block $C$ and fixed anchor block $C_f$ | `(12, 9)` = `(12, 5)` \| `(12, 4)` |
| $x, y, z$ | `x, y, z` | Unknown free-node coordinates ($\text{m}$) | `(5,)` |
| $x_f, y_f, z_f$ | `x_f, y_f, z_f` | Known fixed anchor coordinates ($\text{m}$) | `(4,)` |
| $p_x, p_y, p_z$ | `p_x, p_y, p_z` | Known external loads at free nodes ($\text{kN}$) | `(5,)` |
| $u, v, w$ / $U, V, W$ | `u` / `np.diag(u)` | Branch coordinate differences $Cx + C_f x_f$ / their diagonal matrices | `(12,)` / `(12, 12)` |
| $l$ / $L$ | `l` / `np.diag(l)` | Branch lengths $\sqrt{u_j^2 + v_j^2 + w_j^2}$ / their diagonal matrix | `(12,)` / `(12, 12)` |
| $s$ | `s` | Branch axial forces ($\text{kN}$) | `(12,)` |
| $q$ / $Q$ | `q` / `np.diag(q)` | Prescribed force densities $s_j / l_j$ ($\text{kN/m}$) / their diagonal matrix | `(12,)` / `(12, 12)` |
| $D = C^T Q C$ | `D` | Free-node equilibrium stiffness matrix | `(5, 5)` |
| $D_f = C^T Q C_f$ | `D_f` | Fixed-anchor coupling matrix | `(5, 4)` |
| $G^T = \partial g^* / \partial q$ | `G_t` | Constraint sensitivity Jacobian ($r$ constraints $\times\ m$ branches) | `(r, 12)` |

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

* **Notation Rule**: A lowercase letter ($\mathbf{u}, \mathbf{q}, \mathbf{l}$) is a **1D column vector** of length $m$; the same letter capitalized ($U, Q, L$) is that vector placed on the main diagonal of an $(m \times m)$ **diagonal matrix**.

### General Equation

$$
U = \mathrm{diag}(\mathbf{u}), \qquad U \mathbf{q} = Q \mathbf{u}
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
```

* `u_example` is a 1D vector of shape `(3,)`; `np.diag(u_example)` places its entries on the main diagonal of the `(3, 3)` matrix `U_example`.
* In NumPy, `np.diag(u) @ q`, `np.diag(q) @ u`, and element-wise `u * q` all produce the exact same vector $[8, -5, 18]^T$.

### A.2 Network topology: numbering nodes and branches (section 2.1)

Define the directed graph of the cable net before introducing coordinates or forces. Number **free inner nodes first** ($1 \dots n$) and **fixed outer anchor nodes last** ($n+1 \dots n_s$) so the connectivity matrix splits cleanly with a single vertical cut.

![Fig. 2](images/schek_fig2.png)

### Topological Setup (Schek Fig. 2)

* **Total Nodes** ($n_s = 9$):
  * **Free Inner Nodes** ($n = 5$): Nodes $1, 2, 3, 4, 5$ (unknown coordinates)
  * **Fixed Anchor Nodes** ($n_f = 4$): Nodes $6, 7, 8, 9$ (known boundary supports)
* **Directed Branches** ($m = 12$): from start node $i(j)$ to end node $k(j)$
  * **Branches 1–4 (Anchor cables):** $(1\to 6),\ (2\to 7),\ (3\to 8),\ (4\to 9)$
  * **Branches 5–8 (Inner ring):** $(1\to 4),\ (1\to 2),\ (2\to 3),\ (3\to 4)$
  * **Branches 9–12 (Center spokes):** $(4\to 5),\ (1\to 5),\ (2\to 5),\ (3\to 5)$

**Add to your program:**

```python
branches: list[tuple[int, int]] = [(1, 6), (2, 7), (3, 8), (4, 9),      # 1-4: one branch from each free corner to its anchor
            (1, 4), (1, 2), (2, 3), (3, 4),      # 5-8: the ring
            (4, 5), (1, 5), (2, 5), (3, 5)]      # 9-12: four spokes to the centre node 5
n, n_f = 5, 4                                    # free nodes 1..5, fixed nodes 6..9
m = len(branches)
```

* `branches` is a list of `(start_node, end_node)` tuples for the $m = 12$ directed cables.
* **1-based vs. 0-based indexing:** Schek numbers nodes $1 \dots 9$ and branches $1 \dots 12$; subtract `1` when indexing NumPy arrays (`i - 1`, `k - 1`).

### A.3 Branch-node connectivity matrix and partitioning (section 2.1)

Encode the directed graph as an $(m \times n_s)$ branch-node incidence matrix $C_s$, where each row $j$ represents one cable and each column $i$ represents one node. Partition columns into free nodes $C$ and fixed anchors $C_f$.

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
\leftarrow \text{sum} = 0\ (\text{anchor}) \\
\leftarrow \text{sum} = 0\ (\text{anchor}) \\
\leftarrow \text{sum} = 0\ (\text{anchor}) \\
\leftarrow \text{sum} = 0\ (\text{anchor}) \\
\leftarrow \text{inner ring} \\
\leftarrow \text{inner ring} \\
\leftarrow \text{inner ring} \\
\leftarrow \text{inner ring} \\
\leftarrow \text{center spoke} \\
\leftarrow \text{center spoke} \\
\leftarrow \text{center spoke} \\
\leftarrow \text{center spoke}
\end{matrix}
$$

* **Left block $C\ (12 \times 5)$:** Free inner nodes ($n_1 \dots n_5$).
* **Right block $C_f\ (12 \times 4)$:** Fixed outer anchors ($n_6 \dots n_9$). Rows $5 \dots 12$ are all zero in $C_f$ because ring and spoke cables connect only free nodes.
* **Row sum $= 0$:** Every row has one $+1$ (start) and one $-1$ (end), so multiplying row $j$ by a coordinate vector subtracts end from start: $(+1)x_1 + (-1)x_6 = x_1 - x_6$.

**Add to your program:**

```python
C_s: FloatMatrix = np.zeros((m, n + n_f))
for j, (i, k) in enumerate(branches):
    C_s[j, i - 1] = +1.0                          # node i(j): +1   (Python indices start at 0)
    C_s[j, k - 1] = -1.0                          # node k(j): -1
C: FloatMatrix = C_s[:, :n]                                    # (m, n)   free columns
C_f: FloatMatrix = C_s[:, n:]                                  # (m, n_f) fixed columns

print("C_s shape:", C_s.shape)
print(C_s)
```

* `np.zeros((m, n + n_f))` allocates the `(12, 9)` matrix; `enumerate(branches)` visits each branch `j` (`0..11`) and writes `+1.0` at start column `i - 1` and `-1.0` at end column `k - 1`.
* `C = C_s[:, :n]` slices the first `5` columns (free nodes, shape `(12, 5)`); `C_f = C_s[:, n:]` slices the last `4` columns (fixed anchors, shape `(12, 4)`).

**Example output:**

```text
C_s shape: (12, 9)
[[ 1.  0.  0.  0.  0. -1.  0.  0.  0.]
 [ 0.  1.  0.  0.  0.  0. -1.  0.  0.]
 [ 0.  0.  1.  0.  0.  0.  0. -1.  0.]
 [ 0.  0.  0.  1.  0.  0.  0.  0. -1.]
 [ 1.  0.  0. -1.  0.  0.  0.  0.  0.]
 [ 1. -1.  0.  0.  0.  0.  0.  0.  0.]
 [ 0.  1. -1.  0.  0.  0.  0.  0.  0.]
 [ 0.  0.  1. -1.  0.  0.  0.  0.  0.]
 [ 0.  0.  0.  1. -1.  0.  0.  0.  0.]
 [ 1.  0.  0.  0. -1.  0.  0.  0.  0.]
 [ 0.  1.  0.  0. -1.  0.  0.  0.  0.]
 [ 0.  0.  1.  0. -1.  0.  0.  0.  0.]]
```

### A.4 Step-by-step matrix multiplication for $C^T Q C$

To see exactly how the matrix product $C^T (Q C)$ assembles nodal equilibrium, trace it by hand on a **5-branch, 3-free-node mini-network** (free nodes $1, 2, 3$; fixed supports $4, 5$) with distinct force densities $q = [2, 3, 4, 5, 6]^T$.

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

* **$C$ rows** $=$ cables $(1 \dots 5)$; **$C^T$ rows** $=$ free nodes $(1 \dots 3)$.

### 2. Step 1 — Compute $Q C$ (Force Density per Cable, $5 \times 3$)

Multiply the diagonal matrix $Q = \mathrm{diag}(2, 3, 4, 5, 6)$ by $C$: row $j$ of $C$ is scaled by $q_j$:

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

Multiply $C^T\ (3 \times 5)$ by $Q C\ (5 \times 3)$ to sum cable force densities meeting at each free node:

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

* **Diagonal $D_{ii}$:** Sum of $q_j$ of all branches connected to free node $i$.
* **Off-diagonal $D_{ik}$:** $-q_j$ of the branch directly connecting free nodes $i$ and $k$ ($0$ if not connected).
* **Properties:** Symmetric ($D = D^T$) and strictly positive-definite when all $q_j > 0$.

**Add to your program:**

```python
C_mini = np.array([[1, 0, 0], [0, 1, 0], [1, -1, 0], [-1, 0, 1], [0, 1, -1]], dtype=float)
q_mini = np.array([2.0, 3.0, 4.0, 5.0, 6.0])
D_mini = C_mini.T @ np.diag(q_mini) @ C_mini
print("QC (shape 5x3):", np.diag(q_mini) @ C_mini, sep="\n")
print("D_mini = C^T Q C (shape 3x3):", D_mini, sep="\n")
```

* `C_mini.T` transposes the `(5, 3)` branch-to-node matrix into `(3, 5)` (rows = free nodes).
* `@` is NumPy's matrix multiplication operator: `np.diag(q_mini) @ C_mini` scales each cable row by $q_j$, and `C_mini.T @ ...` sums those weighted rows at each free node.

**Example output:**

```text
QC (shape 5x3):
[[ 2.  0.  0.]
 [ 0.  3.  0.]
 [ 4. -4.  0.]
 [-5.  0.  5.]
 [ 0.  6. -6.]]
D_mini = C^T Q C (shape 3x3):
[[11. -4. -5.]
 [-4. 13. -6.]
 [-5. -6. 11.]]
```

---

## Part B. Equilibrium, the nonlinear form

### B.1 Inputs: fixed anchor coordinates and nodal loads (section 2.2)

Specify the known boundary support coordinates $(\mathbf{x}_f, \mathbf{y}_f, \mathbf{z}_f)$ in $\text{m}$ and external nodal loads $(\mathbf{p}_x, \mathbf{p}_y, \mathbf{p}_z)$ in $\text{kN}$ ($+z$ points up, so gravity is negative).

### Input Vectors & Shapes

* $C\ (12, 5)$ and $C_f\ (12, 4)$: Free and fixed connectivity blocks from A.3.
* $x_f, y_f, z_f\ (4,)$: Known coordinates of fixed anchor nodes $6, 7, 8, 9$ ($\text{m}$).
* $p_x, p_y, p_z\ (5,)$: Known external loads at free nodes $1, 2, 3, 4, 5$ ($\text{kN}$).
* $x, y, z\ (5,)$: Unknown coordinates of free nodes $1 \dots 5$ ($\text{m}$).

### Matrix Example (Inputs)

$$
\begin{bmatrix} \mathbf{x}_f & \mathbf{y}_f & \mathbf{z}_f \end{bmatrix} =
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
\begin{bmatrix} \mathbf{p}_x & \mathbf{p}_y & \mathbf{p}_z \end{bmatrix} =
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
x_f: FloatVector = np.array([-2.0, 0.0, 2.0, 0.0], dtype=np.float64)             # anchors 6, 7, 8, 9
y_f: FloatVector = np.array([0.0, 2.0, 0.0, -2.0], dtype=np.float64)
z_f: FloatVector = np.array([0.0, 1.0, 0.0, 1.0], dtype=np.float64)             # two anchors lifted by 1 m
p_x: FloatVector = np.zeros(n, dtype=np.float64)
p_y: FloatVector = np.zeros(n, dtype=np.float64)
p_z: FloatVector = np.full(n, -0.5, dtype=np.float64)                            # 0.5 kN downward at every free node
```

* `x_f, y_f, z_f` are `(4,)` vectors for fixed anchors $6 \dots 9$ (anchors $7$ and $9$ lifted to $z_f = 1.0\text{ m}$).
* `np.zeros(n)` sets horizontal loads `p_x, p_y` to zero; `np.full(n, -0.5)` sets a downward vertical load of $-0.5\text{ kN}$ on all $n = 5$ free nodes.

### B.2 Coordinate differences and cable lengths, equation (1)

Given node coordinates, compute the branch coordinate differences $(\mathbf{u}, \mathbf{v}, \mathbf{w})$ along $(x, y, z)$ and the Euclidean cable lengths $\mathbf{l}$.

### General Equations (Eq. 1)

$$
\mathbf{u} = C \mathbf{x} + C_f \mathbf{x}_f, \qquad
\mathbf{v} = C \mathbf{y} + C_f \mathbf{y}_f, \qquad
\mathbf{w} = C \mathbf{z} + C_f \mathbf{z}_f, \qquad
l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}
$$

* **Why `+` performs subtraction:** Start node has $+1$ in $C$, end node has $-1$ in $C$ or $C_f$, so $C x + C_f x_f$ computes $x_{\text{start}} - x_{\text{end}}$ for every cable.

### Matrix Example (Evaluated on Flat Trial Coordinates)

Take a flat trial guess for the 5 free nodes: $x = [-1, 0, 1, 0, 0]^T$, $y = [0, -1, 0, 1, 0]^T$, $z = [0, 0, 0, 0, 0]^T$:

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

Collecting all three projection vectors $\mathbf{u}, \mathbf{v}, \mathbf{w}$, cable lengths $l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}$, and the diagonal inverse-length matrix $L^{-1} = \mathrm{diag}(1/\mathbf{l})$:

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
\end{bmatrix},
\qquad
L^{-1} = \mathrm{diag}\left(1,\ \tfrac{1}{\sqrt{10}},\ 1,\ \tfrac{1}{\sqrt{10}},\ \tfrac{1}{\sqrt{2}},\ \dots,\ 1\right)
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
    """Given positions: matrices (m,n)/(m,n_f) times vectors (n,)/(n_f,) -> (m,)."""
    u = C @ x + C_f @ x_f
    v = C @ y + C_f @ y_f
    w = C @ z + C_f @ z_f
    l = np.sqrt(u**2 + v**2 + w**2)
    return u, v, w, l
```

* `u = C @ x + C_f @ x_f` evaluates $(12, 5) \times (5,) + (12, 4) \times (4,) \to (12,)$, computing $x_{\text{start}} - x_{\text{end}}$ for all 12 cables in one vectorized step.
* `np.sqrt(u**2 + v**2 + w**2)` squares each vector element-wise (`**2`), sums them, and takes the square root to get the `(12,)` length vector `l`.
* **Source of nonlinearity:** $l_j$ places the unknown coordinates $\mathbf{x}, \mathbf{y}, \mathbf{z}$ inside a square root.

### B.3 Nonlinear equilibrium in 4 stages, equation (2)

Test nodal force balance on the flat trial shape with unit cable tensions $s = [1, 1, \dots, 1]^T\text{ kN}$. Read the product **right to left** in 4 stages:

### General Equation (Eq. 2)

$$
\mathbf{e}_x = \underbrace{C^T}_{\text{Stage 3: to nodes}} \quad \underbrace{U}_{\text{Stage 2: project } x} \quad \underbrace{L^{-1} \mathbf{s}}_{\text{Stage 1: } q_j = s_j / l_j} \quad - \quad \underbrace{\mathbf{p}_x}_{\text{Stage 4: load}}
$$

### Stage-by-Stage Matrix Breakdown

#### Stage 1 — Force Density Ratios: $\mathbf{q} = L^{-1} \mathbf{s}\ (12 \times 1)$

Divides each cable tension $s_j = 1\text{ kN}$ by its geometric length $l_j$:

$$
\mathbf{q} = L^{-1} \mathbf{s} =
\begin{bmatrix}
1 & \tfrac{1}{\sqrt{10}} & 1 & \tfrac{1}{\sqrt{10}} & \tfrac{1}{\sqrt{2}} & \tfrac{1}{\sqrt{2}} & \tfrac{1}{\sqrt{2}} & \tfrac{1}{\sqrt{2}} & 1 & 1 & 1 & 1
\end{bmatrix}^T
\approx
\begin{bmatrix}
1.000 & 0.316 & 1.000 & 0.316 & 0.707 & 0.707 & 0.707 & 0.707 & 1.000 & 1.000 & 1.000 & 1.000
\end{bmatrix}^T
$$

#### Stage 2 — Projected Branch Force Components: $\mathbf{F}_x = U \mathbf{q},\ \mathbf{F}_y = V \mathbf{q},\ \mathbf{F}_z = W \mathbf{q}\ (12 \times 1)$

Multiplies each cable's $q_j = s_j / l_j$ by its coordinate difference $u_j, v_j, w_j$ to get the $(x, y, z)$ force components in each cable:

$$
\mathbf{F}_x = \mathrm{diag}(\mathbf{u})\mathbf{q} =
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
\mathbf{F}_y = \mathrm{diag}(\mathbf{v})\mathbf{q} =
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
\mathbf{F}_z = \mathrm{diag}(\mathbf{w})\mathbf{q} =
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

#### Stage 3 — Sum Cable Forces at Free Nodes: $C^T \mathbf{F}_x\ (5 \times 1)$

Transposed connectivity $C^T\ (5 \times 12)$ collects cable forces meeting at each free node $1 \dots 5$:

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
\begin{matrix}
\leftarrow \text{Node 1: } b_1 + b_5 + b_6 + b_{10} = 1 - 0.707 - 0.707 - 1 \\
\leftarrow \text{Node 2} \\
\leftarrow \text{Node 3} \\
\leftarrow \text{Node 4} \\
\leftarrow \text{Node 5}
\end{matrix}
$$

#### Stage 4 — Subtract Applied Loads to Check Equilibrium: $\mathbf{e} = C^T \mathbf{F} - \mathbf{p}\ (5 \times 1)$

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
$$

* **Result:** Every free node has a nonzero residual ($e_z \neq 0$) because a flat net has no vertical slope on inner cables to balance the $-0.5\text{ kN}$ downward loads.

**Add to your program:**

```python
def equilibrium_error(x, y, z, s):
    """Eq. (2): C^t U L^-1 s - p for the three axes.  All zeros means the net is in equilibrium."""
    u, v, w, l = coordinate_differences(C, x, y, z, C_f, x_f, y_f, z_f)
    L_inv = np.diag(1.0 / l)
    return (C.T @ np.diag(u) @ L_inv @ s - p_x,
            C.T @ np.diag(v) @ L_inv @ s - p_y,
            C.T @ np.diag(w) @ L_inv @ s - p_z)


x_guess = np.array([-1.0, 0.0, 1.0, 0.0, 0.0])    # a flat guess for the free nodes
y_guess = np.array([0.0, -1.0, 0.0, 1.0, 0.0])
z_guess = np.zeros(n)
s_guess = np.ones(m)                              # 1 kN in every branch
ex, ey, ez = equilibrium_error(x_guess, y_guess, z_guess, s_guess)
print("out of balance at the free nodes for the flat guess, z direction:", ez)
```

* `L_inv = np.diag(1.0 / l)` builds the `(12, 12)` diagonal inverse-length matrix $L^{-1}$, and `C.T @ np.diag(u) @ L_inv @ s - p_x` chains Stages 1–4 right-to-left.
* Solving Eq. (2) directly for $\mathbf{x}, \mathbf{y}, \mathbf{z}$ is nonlinear because $L^{-1}$ divides by $\sqrt{u_j^2 + v_j^2 + w_j^2}$. Part C eliminates $L^{-1}$ with a single substitution.

**Example output:**

```text
out of balance at the free nodes for the flat guess, z direction: [0.5   0.184 0.5   0.184 0.5  ]
```

---

## Part C. The force density trick: a linear system

### C.1 The force density trick and the diagonal swap, equations (4) to (6)

Prescribe the **force density** ratio $q_j = s_j / l_j$ (in $\text{kN/m}$) for each branch instead of the force $s_j$. This cancels the nonlinear cable length $l_j$ out of the equilibrium equations.

### General Equations (Eqs. 4–6)

$$
q_j = \frac{s_j}{l_j} = L^{-1} \mathbf{s}
\qquad \Longrightarrow \qquad
F_{x, j} = s_j \frac{u_j}{l_j} = (q_j l_j) \frac{u_j}{l_j} = q_j u_j = q_j (x_i - x_k)
$$

Using the diagonal commutation rule $U \mathbf{q} = Q \mathbf{u}$ from A.1 swaps the known design parameters $Q$ and the unknown coordinate differences $\mathbf{u}$:

$$
C^T U \mathbf{q} = C^T Q \mathbf{u} = \mathbf{p}_x
$$

### Matrix Example (Prescribed Force Densities)

Assign $q = 2\text{ kN/m}$ to the 4 anchor cables (branches 1–4) and $q = 1\text{ kN/m}$ to the 8 inner ring and spoke cables (branches 5–12):

$$
\mathbf{q} = \begin{bmatrix}
2 & 2 & 2 & 2 & 1 & 1 & 1 & 1 & 1 & 1 & 1 & 1
\end{bmatrix}^T,
\qquad
Q = \mathrm{diag}(\mathbf{q}) =
\begin{bmatrix}
2 & & & & & \\
 & \ddots & & & & \\
 & & 2 & & & \\
 & & & 1 & & \\
 & & & & \ddots & \\
 & & & & & 1
\end{bmatrix}_{(12\times 12)}
$$

**Add to your program:**

```python
q = np.array([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1], dtype=float)   # one force density per branch: the design input
```

* `q` is a 1D NumPy array of shape `(12,)` holding the prescribed force density $q_j$ ($\text{kN/m}$) for each branch.
* **Predict:** If $q$ on the 4 anchor cables is raised from $2.0$ to $10.0\text{ kN/m}$, does center node 5 move higher or sag lower? (Checked in D.2.)

### C.2 System matrices $D$ and $D_f$, equations (7) and (8)

Substitute $\mathbf{u} = C \mathbf{x} + C_f \mathbf{x}_f$ into $C^T Q \mathbf{u} = \mathbf{p}_x$ to separate unknown free coordinates $\mathbf{x}$ from known anchor coordinates $\mathbf{x}_f$.

### General Equations (Eqs. 7–8)

$$
(C^T Q C)\mathbf{x} + (C^T Q C_f)\mathbf{x}_f = \mathbf{p}_x
\qquad \Longrightarrow \qquad
D \mathbf{x} = \mathbf{p}_x - D_f \mathbf{x}_f
$$

where $D = C^T Q C\ (5 \times 5)$ is the free-node system matrix and $D_f = C^T Q C_f\ (5 \times 4)$ is the anchor coupling matrix.

### 1. Traceable Structure of $D$ (Schek Fig. 4, setting $q_j = j$)

To see which branch populates each entry of $D = C^T Q C$, set $q_j = j$:

$$
D_{(q_j = j)} =
\begin{bmatrix}
q_1+q_5+q_6+q_{10} & -q_6 & 0 & -q_5 & -q_{10} \\
-q_6 & q_2+q_6+q_7+q_{11} & -q_7 & 0 & -q_{11} \\
0 & -q_7 & q_3+q_7+q_8+q_{12} & -q_8 & -q_{12} \\
-q_5 & 0 & -q_8 & q_4+q_5+q_8+q_9 & -q_9 \\
-q_{10} & -q_{11} & -q_{12} & -q_9 & q_9+q_{10}+q_{11}+q_{12}
\end{bmatrix} =
\begin{bmatrix}
22 & -6 & 0 & -5 & -10 \\
-6 & 26 & -7 & 0 & -11 \\
0 & -7 & 30 & -8 & -12 \\
-5 & 0 & -8 & 26 & -9 \\
-10 & -11 & -12 & -9 & 42
\end{bmatrix}
$$

### 2. Actual Matrices $D$, $D_f$, and Right-Hand Sides for $\mathbf{q} = [2,2,2,2,1,\dots,1]^T$

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
\leftarrow \text{to Anchor 6} \\
\leftarrow \text{to Anchor 7} \\
\leftarrow \text{to Anchor 8} \\
\leftarrow \text{to Anchor 9} \\
\leftarrow \text{no anchor}
\end{matrix}
$$

Evaluating the right-hand side $b_z = p_z - D_f z_f$ for the vertical axis:

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
\end{bmatrix}
$$

**Add to your program:**

```python
Q = np.diag(q)
D = C.T @ Q @ C                                   # (n, n)   eq. (8)
D_f = C.T @ Q @ C_f                               # (n, n_f)

rhs = np.c_[p_x - D_f @ x_f, p_y - D_f @ y_f, p_z - D_f @ z_f]
print("D (shape 5x5):", D, sep="\n")
print("D_f (shape 5x4):", D_f, sep="\n")
print("right-hand sides (columns x, y, z; shape 5x3):", rhs, sep="\n")
```

* `Q = np.diag(q)` builds the `(12, 12)` diagonal force-density matrix; `D = C.T @ Q @ C` is `(5, 5)` and `D_f = C.T @ Q @ C_f` is `(5, 4)`.
* `np.c_[...]` stacks the three `(5,)` right-hand side vectors $[b_x \mid b_y \mid b_z]$ side-by-side into a `(5, 3)` matrix `rhs`.

**Example output:**

```text
D (shape 5x5):
[[ 5. -1.  0. -1. -1.]
 [-1.  5. -1.  0. -1.]
 [ 0. -1.  5. -1. -1.]
 [-1.  0. -1.  5. -1.]
 [-1. -1. -1. -1.  4.]]
D_f (shape 5x4):
[[-2.  0.  0.  0.]
 [ 0. -2.  0.  0.]
 [ 0.  0. -2.  0.]
 [ 0.  0.  0. -2.]
 [ 0.  0.  0.  0.]]
right-hand sides (columns x, y, z; shape 5x3):
[[-4.   0.  -0.5]
 [ 0.   4.   1.5]
 [ 4.   0.  -0.5]
 [ 0.  -4.   1.5]
 [ 0.   0.  -0.5]]
```

### C.3 Direct linear solve for free node coordinates, equation (9)

Solve the three uncoupled $(5 \times 5)$ linear systems for $\mathbf{x}, \mathbf{y}, \mathbf{z}$ in one direct step—no initial coordinate guess or iteration required.

### General Equations (Eq. 9)

$$
D \mathbf{x} = \mathbf{p}_x - D_f \mathbf{x}_f, \qquad
D \mathbf{y} = \mathbf{p}_y - D_f \mathbf{y}_f, \qquad
D \mathbf{z} = \mathbf{p}_z - D_f \mathbf{z}_f
$$

### Matrix Example (Vertical Equilibrium Solve $D \mathbf{z} = \mathbf{b}_z$ and 3D Solution)

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
\begin{bmatrix} \mathbf{x} & \mathbf{y} & \mathbf{z} \end{bmatrix} =
\begin{bmatrix}
-0.800 & 0.000 & 0.045 \\
0.000 & 0.800 & 0.330 \\
0.800 & 0.000 & 0.045 \\
0.000 & -0.800 & 0.330 \\
0.000 & 0.000 & 0.063
\end{bmatrix}
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
x: FloatVector = np.linalg.solve(D, p_x - D_f @ x_f)            # eq. (9)
y: FloatVector = np.linalg.solve(D, p_y - D_f @ y_f)
z: FloatVector = np.linalg.solve(D, p_z - D_f @ z_f)
```

* `np.linalg.solve(D, b)` solves the $(5 \times 5)$ linear system $D \mathbf{x} = \mathbf{b}$ directly via LU factorization without forming $D^{-1}$.
* All three axes share the exact same left-hand matrix `D`; only the right-hand side vector `p - D_f @ x_f` changes per axis.

### C.4 Recovering cable lengths, forces, and equilibrium verification, equation (10)

Evaluate the branch lengths $\mathbf{l}$ on the solved coordinates, recover the axial cable forces $\mathbf{s} = Q \mathbf{l}$, and verify that Part B's nonlinear equilibrium residual vanishes to machine precision.

### General Equations (Eq. 10)

$$
s_j = q_j l_j \quad (\mathbf{s} = Q \mathbf{l}), \qquad
\mathbf{e}_x = C^T U L^{-1} \mathbf{s} - \mathbf{p}_x = \mathbf{0}
$$

### Matrix Example (Solved Lengths $\mathbf{l}$ and Forces $\mathbf{s}$)

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
\begin{matrix}
\leftarrow \text{Anchor cable 1} \\
\leftarrow \text{Anchor cable 2 (lifted)} \\
\leftarrow \text{Anchor cable 3} \\
\leftarrow \text{Anchor cable 4 (lifted)} \\
\leftarrow \text{Ring cables 5–8} \\
\vdots \\
\leftarrow \text{Spokes 9, 11} \\
\leftarrow \text{Spokes 10, 12}
\end{matrix},
\qquad
\max |\mathbf{e}| = 4.44 \times 10^{-16}\text{ kN} \approx 0
$$

**Add to your program:**

```python
u, v, w, l = coordinate_differences(C, x, y, z, C_f, x_f, y_f, z_f)      # eq. (1) on the solution
s = l * q                                         # eq. (10)

xyz_free = np.c_[x, y, z]
print("free node coordinates (columns x, y, z):", xyz_free, sep="\n")
print("lengths l:", l)
print("forces  s:", s)
print("equilibrium error (2) on the solution:", max(np.abs(e).max() for e in equilibrium_error(x, y, z, s)))
```

* `coordinate_differences` recomputes the equilibrium cable lengths `l` from the solved coordinates `(x, y, z)`.
* `s = l * q` multiplies element-by-element (`*`, equivalent to $Q \mathbf{l}$) to recover axial forces: among branches with equal $q$, **longer branches carry larger tension**.
* Plugging `(x, y, z, s)` into `equilibrium_error` returns `4.44e-16` (machine zero), confirming exact nonlinear 3D equilibrium.

**Example output:**

```text
free node coordinates (columns x, y, z):
[[-0.8    0.     0.045]
 [-0.     0.8    0.33 ]
 [ 0.8   -0.     0.045]
 [-0.    -0.8    0.33 ]
 [ 0.    -0.     0.062]]
lengths l: [1.201 1.374 1.201 1.374 1.167 1.167 1.167 1.167 0.844 0.8   0.844 0.8  ]
forces  s: [2.402 2.748 2.402 2.748 1.167 1.167 1.167 1.167 0.844 0.8   0.844 0.8  ]
equilibrium error (2) on the solution: 4.440892098500626e-16
```

---

## Part D. The form-finding loop

### D.1 Complete linear form-finding function and support reactions (figure 3)

Package A.3 through C.4 into a single reusable function `form_finding` solving all 3 spatial axes simultaneously, and compute the support reaction forces $\mathbf{R}_f$ at the fixed anchors.

![Fig. 3](images/schek_fig3.png)

### General Equations (3-Column Matrix Form & Eq. 5 Reactions)

Stack coordinates into $X = [x \mid y \mid z]\ (n \times 3)$, $X_f\ (n_f \times 3)$, and loads $P\ (n \times 3)$:

$$
D \mathbf{X} = \mathbf{P} - D_f \mathbf{X}_f, \qquad
\mathbf{U}_{xyz} = C \mathbf{X} + C_f \mathbf{X}_f, \qquad
\mathbf{R}_f = C_f^T Q \mathbf{U}_{xyz}
$$

### Matrix Example (Support Reactions $R_f = C_f^T Q U_{xyz}$)

Summing cable pulls at the 4 fixed anchors ($4 \times 3$):

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
\leftarrow \text{Anchor 6 (ground)} \\
\leftarrow \text{Anchor 7 (lifted, carries } 1.339\text{ kN)} \\
\leftarrow \text{Anchor 8 (ground)} \\
\leftarrow \text{Anchor 9 (lifted, carries } 1.339\text{ kN)}
\end{matrix}
$$

**Add to your program:**

```python
def form_finding(branches, n_free, xyz_fixed, q, p):
    """Schek section 2 as one call.  xyz_fixed: (n_f, 3); p: (n_free, 3) loads; q: (m,)."""
    n_s = n_free + len(xyz_fixed)
    C_s = np.zeros((len(branches), n_s))
    for j, (i, k) in enumerate(branches):
        C_s[j, i - 1], C_s[j, k - 1] = 1.0, -1.0                      # section 2.1
    C, C_f = C_s[:, :n_free], C_s[:, n_free:]
    D, D_f = C.T @ np.diag(q) @ C, C.T @ np.diag(q) @ C_f                    # eq. (8)
    xyz = np.vstack([np.linalg.solve(D, p[:, a] - D_f @ xyz_fixed[:, a]) for a in range(3)]).T   # eq. (9)
    uvw = C @ xyz + C_f @ xyz_fixed                                    # eq. (1), three columns
    l = np.linalg.norm(uvw, axis=1)
    s = l * q                                                          # eq. (10)
    reactions = C_f.T @ np.diag(q) @ uvw                               # eq. (5) at the fixed nodes
    return xyz, l, s, reactions
```

* `np.vstack([...]).T` solves axes `a = 0, 1, 2` ($x, y, z$) and stacks them as columns into `xyz` of shape `(n_free, 3)`.
* `uvw = C @ xyz + C_f @ xyz_fixed` computes `[u | v | w]` as an `(m, 3)` matrix, and `np.linalg.norm(uvw, axis=1)` computes the Euclidean length $\sqrt{u_j^2 + v_j^2 + w_j^2}$ of each row.
* **Global Equilibrium Check:** `reactions = C_f.T @ np.diag(q) @ uvw` gives $\sum_{i=6}^9 R_{iz} = +2.500\text{ kN}$, which exactly balances the total downward load $\sum_{i=1}^5 p_{iz} = -2.500\text{ kN}$.

### D.2 Parameter study: moving anchors vs. changing force densities

Compare the computational cost and geometric effect of modifying anchor coordinates $\mathbf{X}_f$ (only the right-hand side changes) versus modifying force densities $\mathbf{q}$ ($D$ and $D_f$ are rebuilt).

### Matrix Comparison Across 3 Runs

$$
\begin{array}{l|cc|c}
\text{Case} & \text{Matrix } D\ (5\times 5) & \text{RHS } \mathbf{P} - D_f \mathbf{X}_f & \text{Center Height } z_5\ (\text{m}) \\
\hline
\text{1. Base case } (q_{\text{anchor}} = 2) & \text{built once} & \text{base} & 0.063 \\
\text{2. All anchors lifted } +1\text{ m} & \textbf{unchanged} & \text{updated} & 1.063 \\
\text{3. Stiffer anchors } (q_{\text{anchor}} = 10) & \textbf{rebuilt} & \text{updated} & 0.313
\end{array}
$$

**Add to your program:**

```python
xyz_fixed = np.c_[x_f, y_f, z_f]
p = np.c_[p_x, p_y, p_z]
xyz1, l1, s1, R1 = form_finding(branches, n, xyz_fixed, q, p)
print("same solution from the function:", np.allclose(xyz1[:, 2], z))
print("reactions at the anchors (sum of z components balances the total load):", R1[:, 2], R1[:, 2].sum())

# a change of fixed points: only the right-hand side changes
xyz2, *_ = form_finding(branches, n, xyz_fixed + np.array([0, 0, 1.0]), q, p)
# a change of force densities: D is rebuilt
xyz3, *_ = form_finding(branches, n, xyz_fixed, np.where(np.arange(m) < 4, 10.0, 1.0), p)
print("centre node height: base %.3f | anchors lifted by 1 m %.3f | anchor branches q = 10: %.3f" % (xyz1[4, 2], xyz2[4, 2], xyz3[4, 2]))
```

* `xyz_fixed + np.array([0, 0, 1.0])` broadcasts $+1.0\text{ m}$ to the $z$ coordinate of all 4 anchors without changing `D`.
* `np.where(np.arange(m) < 4, 10.0, 1.0)` raises $q$ on the first 4 branches from $2$ to $10\text{ kN/m}$ (rebuilding `D`), pulling center node 5 up from $0.063\text{ m}$ to $0.313\text{ m}$.

**Example output:**

```text
same solution from the function: True
reactions at the anchors (sum of z components balances the total load): [-0.089  1.339 -0.089  1.339] 2.5000000000000004
centre node height: base 0.062 | anchors lifted by 1 m 1.062 | anchor branches q = 10: 0.313
```

---

## Part E. What the force densities mean

### E.1 Geometric meaning of force densities (section 4)

Why does increasing $q_j$ shorten branch $j$? For an unloaded net ($\mathbf{P} = \mathbf{0}$), the linear equilibrium equation $D \mathbf{x} + D_f \mathbf{x}_f = \mathbf{0}$ is identical to minimizing the **$q$-weighted sum of squared cable lengths**.

### General Equations (Eqs. 37–40, Theorems 1 & 2)

$$
\Phi(\mathbf{x}, \mathbf{y}, \mathbf{z}) = \mathbf{u}^T Q \mathbf{u} + \mathbf{v}^T Q \mathbf{v} + \mathbf{w}^T Q \mathbf{w} = \sum_{j=1}^m q_j l_j^2 \longrightarrow \min
$$

Setting the gradient with respect to the free coordinates to zero ($\frac{\partial \mathbf{u}}{\partial \mathbf{x}} = C$) recovers the equilibrium equation:

$$
\frac{\partial \Phi}{\partial \mathbf{x}} = 2 C^T Q \mathbf{u} = 2 (C^T Q C \mathbf{x} + C^T Q C_f \mathbf{x}_f) = 2 (D \mathbf{x} + D_f \mathbf{x}_f) = \mathbf{0}
$$

* **Theorem 1:** $q_j$ acts as a penalty weight on $l_j^2$—a **large $q_j$ forces cable $j$ to stay short and taut**; a **small $q_j$ allows it to stretch**.
* **Theorem 2:** Choosing $q_j = c / l_j$ yields constant axial force $s_j = q_j l_j = c$ across every branch (minimal total length net).

### Matrix Example (Unloaded Equilibrium $\mathbf{P} = \mathbf{0}$)

$$
\mathbf{X}_0 = \begin{bmatrix}
-0.800 & 0.000 & 0.357 \\
0.000 & 0.800 & 0.643 \\
0.800 & 0.000 & 0.357 \\
0.000 & -0.800 & 0.643 \\
0.000 & 0.000 & 0.500
\end{bmatrix}
\begin{matrix}
\leftarrow \text{Node 1} \\
\leftarrow \text{Node 2} \\
\leftarrow \text{Node 3} \\
\leftarrow \text{Node 4} \\
\leftarrow \text{Node 5 (exact midpoint } z = 0.5\text{ m)}
\end{matrix},
\qquad
\nabla \Phi(\mathbf{X}_0) = 2 C^T Q \mathbf{U}_0 = \mathbf{0}_{5\times 3}
$$

**Add to your program:**

```python
xyz0, l0, s0, _ = form_finding(branches, n, xyz_fixed, q, np.zeros((n, 3)))      # no load
uvw0 = C @ xyz0 + C_f @ xyz_fixed
gradient = 2 * C.T @ np.diag(q) @ uvw0                                              # d/dx of u^t Q u, per axis
print("Theorem 1: gradient of the weighted squared lengths at the unloaded equilibrium:", np.abs(gradient).max())
q_const = 1.0 / l0                                                               # Theorem 2
print("Theorem 2: forces with q = 1 / l:", l0 * q_const)
```

* Passing `np.zeros((n, 3))` sets external loads $\mathbf{P} = \mathbf{0}$; `gradient = 2 * C.T @ np.diag(q) @ uvw0` evaluates to `8.88e-16` ($\approx 0$), confirming Theorem 1.
* With `q_const = 1.0 / l0`, the recovered forces `l0 * q_const` are `[1, 1, ..., 1]` $\text{kN}$ across all 12 cables, confirming Theorem 2.

**Example output:**

```text
Theorem 1: gradient of the weighted squared lengths at the unloaded equilibrium: 1.3322676295501878e-15
Theorem 2: forces with q = 1 / l: [1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1.]
```

---

## Part F. Asking for lengths and forces

### F.1 Target length and force constraints, equation (11)

The linear solve gives an equilibrium shape for a chosen $q$, but fabricators often require **prescribed cable lengths $l_v$** or **prescribed forces $s_v$**. Because the equilibrium lengths $l(q)$ and forces $s(q)$ depend solely on $q$, we formulate a constraint residual vector $g^*(q) = 0$.

### General Equation (Eq. 11)

$$
\mathbf{g}^*(\mathbf{q}) = \begin{bmatrix}
\mathbf{l}_{\text{constrained}}(\mathbf{q}) - \mathbf{l}_v \\
\mathbf{s}_{\text{constrained}}(\mathbf{q}) - \mathbf{s}_v
\end{bmatrix} = \mathbf{0}
$$

### Matrix Example (Requiring Anchor Cables 1–4 to Have Length $1.200\text{ m}$)

At our initial $q = [2, 2, 2, 2, 1, \dots, 1]^T$, the 4 anchor cables have lengths $l_{1..4} = [1.201, 1.374, 1.201, 1.374]^T$:

$$
\mathbf{g}^*(\mathbf{q}) =
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
\leftarrow \text{Branch 1 (nearly 1.2 m)} \\
\leftarrow \text{Branch 2 (17.4 cm too long)} \\
\leftarrow \text{Branch 3 (nearly 1.2 m)} \\
\leftarrow \text{Branch 4 (17.4 cm too long)}
\end{matrix}
$$

**Add to your program:**

```python
length_rows = [0, 1, 2, 3]                        # the four anchor branches
target_lengths = np.full(4, 1.2)                  # we want all four to be 1.2 m
g_lengths = l[length_rows] - target_lengths       # what is still wrong, one number per wish

print("wanted 1.2 m, got:", l[length_rows])
print("still wrong by:   ", g_lengths)
```

* `l[length_rows] - target_lengths` slices the 4 anchor cable lengths (`[0, 1, 2, 3]`) and subtracts $1.2\text{ m}$ to form the `(4,)` residual vector `g_lengths`.
* Here 4 equations constrain 12 unknown force densities $\mathbf{q}$ ($r = 4 < m = 12$), forming an underdetermined nonlinear system solved by least-squares iteration in F.2.

**Example output:**

```text
wanted 1.2 m, got: [1.201 1.374 1.201 1.374]
still wrong by:    [0.001 0.174 0.001 0.174]
```

### F.2 Iterative solver for prescribed lengths and forces (sections 3.1 to 3.6)

Use `scipy.optimize.least_squares` with positivity bounds $q_j > 0$ to adjust $\mathbf{q}$ iteratively until the constraint residual $\mathbf{g}^*(\mathbf{q}) = \mathbf{0}$ vanishes, calling the linear `form_finding` solver at each trial $\mathbf{q}$.

### Iteration Loop

$$
\mathbf{q}^{(k)} \xrightarrow{\text{linear solve } D(\mathbf{q})\mathbf{X} = \mathbf{B}(\mathbf{q})} \mathbf{l}(\mathbf{q}^{(k)}),\ \mathbf{s}(\mathbf{q}^{(k)}) \xrightarrow{\text{residual}} \mathbf{g}^*(\mathbf{q}^{(k)}) \xrightarrow{\text{update}} \mathbf{q}^{(k+1)}
$$

### Matrix Example (Before vs. After Optimization on Anchor Cables 1–4)

$$
\text{Initial: }
\begin{bmatrix} q_1 \\ q_2 \\ q_3 \\ q_4 \end{bmatrix} =
\begin{bmatrix} 2.000 \\ 2.000 \\ 2.000 \\ 2.000 \end{bmatrix},\
\mathbf{l}_{1..4} = \begin{bmatrix} 1.201 \\ 1.374 \\ 1.201 \\ 1.374 \end{bmatrix}\text{ m}
\qquad \longrightarrow \qquad
\text{Solved: }
\begin{bmatrix} q_1^* \\ q_2^* \\ q_3^* \\ q_4^* \end{bmatrix} =
\begin{bmatrix} 1.972 \\ 2.412 \\ 1.972 \\ 2.412 \end{bmatrix},\
\mathbf{l}_{1..4}^* = \begin{bmatrix} 1.200 \\ 1.200 \\ 1.200 \\ 1.200 \end{bmatrix}\text{ m}
$$

* Because branches 2 and 4 were too long ($1.374 > 1.200\text{ m}$), the solver automatically increased $q_2, q_4$ from $2.000 \to 2.412\text{ kN/m}$ to pull them shorter.

**Add to your program:**

```python
from scipy.optimize import least_squares


def fit_force_densities(branches, n_free, xyz_fixed, q_start, p,
                        length_rows=(), l_v=(), force_rows=(), s_v=()):
    """Search for the q whose equilibrium shape also has the wanted lengths and forces."""
    length_rows, force_rows = list(length_rows), list(force_rows)
    l_v, s_v = np.asarray(l_v, float), np.asarray(s_v, float)

    def still_wrong(q):                                   # one number per wish; all zero = done
        _, l, s, _ = form_finding(branches, n_free, xyz_fixed, q, p)
        return np.r_[l[length_rows] - l_v, s[force_rows] - s_v]

    found = least_squares(still_wrong, q_start, bounds=(1e-9, np.inf))   # q > 0: a cable stays a cable
    xyz, l, s, reactions = form_finding(branches, n_free, xyz_fixed, found.x, p)
    return found.x, xyz, l, s, found.nfev, np.abs(found.fun).max()


q_c, xyz_c, l_c, s_c, tries, err = fit_force_densities(branches, n, xyz_fixed, q, p,
                                                       length_rows=[0, 1, 2, 3], l_v=[1.2] * 4)
print(f"anchor branches asked for 1.2 m -> {np.round(l_c[:4], 3)} after {tries} tries, worst error {err:.1e}")
print(f"the q that does it: {np.round(q_c[:4], 3)}  (we started from {q[:4]})")

q_m, xyz_m, l_m, s_m, tries, err = fit_force_densities(branches, n, xyz_fixed, q, p,
                                                       length_rows=[8, 9, 10, 11], l_v=[0.9] * 4,
                                                       force_rows=[0, 1, 2, 3], s_v=[2.0] * 4)
print(f"mixed wishes -> spokes {np.round(l_m[8:], 3)} m, anchor forces {np.round(s_m[:4], 3)} kN, worst error {err:.1e}")
```

* `still_wrong(q)` runs the linear `form_finding` solver at candidate `q` and concatenates length errors `l[length_rows] - l_v` and force errors `s[force_rows] - s_v` via `np.r_[...]`.
* `scipy.optimize.least_squares` adjusts `q` until `still_wrong(q)` reaches zero (`found.x` is the optimal $\mathbf{q}^*$), while `bounds=(1e-9, np.inf)` enforces $q_j > 0$ so cables never go slack or compressive.

**Example output:**

```text
anchor branches asked for 1.2 m -> [1.2 1.2 1.2 1.2] after 12 tries, worst error 1.8e-08
the q that does it: [1.972 2.412 1.972 2.412]  (we started from [2. 2. 2. 2.])
mixed wishes -> spokes [0.9 0.9 0.9 0.9] m, anchor forces [2. 2. 2. 2.] kN, worst error 8.5e-11
```

### F.3 Sensitivity Jacobian $G^T = \partial \mathbf{g}^* / \partial \mathbf{q}$ (sections 3.2 to 3.5)

The optimizer steers $\mathbf{q}$ using the **Jacobian matrix** $G^T\ (r \times m)$, whose entry $(i, j)$ measures how much constraint $i$ changes when force density $q_j$ is nudged.

### General Equations (Eqs. 28 & 31)

Implicit differentiation of $D(\mathbf{q})\mathbf{x} + D_f(\mathbf{q})\mathbf{x}_f = \mathbf{p}_x$ yields the nodal coordinate sensitivity:

$$
\frac{\partial \mathbf{x}}{\partial \mathbf{q}} = -D^{-1} C^T U, \qquad
\frac{\partial \mathbf{z}}{\partial \mathbf{q}} = -D^{-1} C^T W, \qquad
G^T = \frac{\partial \mathbf{g}^*}{\partial \mathbf{q}}
$$

### Matrix Example (Anchor Length Jacobian $G^T_{1..4,\ 1..4}$ and Height Sensitivity $\partial z / \partial q_{1..4}$)

Leading $(4 \times 4)$ block of $G^T\ (4 \times 12)$ for the 4 anchor lengths with respect to $q_1 \dots q_4$, alongside the $(5 \times 4)$ vertical coordinate sensitivity $\partial z / \partial q_{1..4}$:

$$
G^T_{1..4,\ 1..4} =
\begin{bmatrix}
-0.313 & 0.002 & 0.073 & 0.002 \\
0.002 & -0.358 & 0.002 & 0.044 \\
0.073 & 0.002 & -0.313 & 0.002 \\
0.002 & 0.044 & 0.002 & -0.358
\end{bmatrix},
\qquad
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
\leftarrow \text{Node 2 (rises } +0.175\text{ m per unit } q_2\text{)} \\
\leftarrow \text{Node 3} \\
\leftarrow \text{Node 4 (rises } +0.175\text{ m per unit } q_4\text{)} \\
\leftarrow \text{Node 5}
\end{matrix}
$$

* **Negative diagonal of $G^T$ ($-0.313, -0.358$):** Increasing $q_j$ always shortens branch $j$.
* **Signs of $\partial \mathbf{z} / \partial \mathbf{q}$:** Tightening ground cable $q_1$ pulls nodes **down** ($-0.012$); tightening lifted-anchor cable $q_2$ pulls Node 2 **up** ($+0.175$).

**Add to your program:**

```python
def sensitivity(q, rows, step=1e-6):
    """Row i, column j: how much does length i change when q_j is nudged up by one unit."""
    base = form_finding(branches, n, xyz_fixed, q, p)[1][rows]
    G_t = np.zeros((len(rows), len(q)))
    for j in range(len(q)):
        q_nudged = q.copy()
        q_nudged[j] += step
        G_t[:, j] = (form_finding(branches, n, xyz_fixed, q_nudged, p)[1][rows] - base) / step
    return G_t


G_t = sensitivity(q, [0, 1, 2, 3])
print("sensitivity of the four anchor lengths to all twelve q (shape %s):" % (G_t.shape,))
print(G_t)
```

* Column `j` of `G_t` (`shape (4, 12)`) is computed by copying `q`, nudging `q_nudged[j] += step` (`1e-6`), re-running `form_finding`, and dividing the length change by `step`.
* These finite differences match Schek's analytic Jacobian formulas (Eqs. 31, 34, 35 in `schek_equations.py`) to 3 decimal places.

**Example output:**

```text
sensitivity of the four anchor lengths to all twelve q (shape (4, 12)):
[[-0.313  0.002  0.073  0.002  0.139  0.139  0.023  0.023  0.     0.109  0.     0.051]
 [ 0.002 -0.358  0.002  0.044  0.016  0.144  0.144  0.016  0.037  0.     0.113  0.   ]
 [ 0.073  0.002 -0.313  0.002  0.023  0.023  0.139  0.139  0.     0.051  0.     0.109]
 [ 0.002  0.044  0.002 -0.358  0.144  0.016  0.016  0.144  0.113  0.     0.037  0.   ]]
```

---

## Part G. The paper's examples, recomputed

### G.1 Larger network: the 67-node, 110-branch pointed tent (section 5, figure 5)

Apply the exact same `form_finding` function without modification to Schek's larger pointed-tent network ($n = 61$ free nodes, $n_f = 6$ fixed supports including high apex node 67, $m = 110$ branches).

![Fig. 5](images/schek_fig5.png)

### Problem Dimensions & Prescribed Force Densities

$$
\begin{array}{l|cc}
\text{Matrix / Vector} & \text{Fig. 2 Net (Parts A–F)} & \text{Fig. 5 Tent (Part G)} \\
\hline
\text{Connectivity } C_s = \begin{bmatrix} C & C_f \end{bmatrix} & (12 \times 5)\ \big|\ (12 \times 4) & (110 \times 61)\ \big|\ (110 \times 6) \\
\text{Diagonal Force Density } Q & (12 \times 12) & (110 \times 110) \\
\text{Free System Matrix } D = C^T Q C & (5 \times 5) & (61 \times 61)
\end{array},
\qquad
q_j = \begin{cases}
100.0 & \text{29 border cables (stiff edge)} \\
0.5 & \text{10 radial apex cables (long)} \\
1.0 & \text{71 interior field cables}
\end{cases}
$$

**Add to your program:**

```python
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
```

* Boolean masks `is_spoke`, `is_border`, and `touches_border` (`shape (110,)`) classify each branch so we can selectively modify $q$ or slice lengths `l[is_spoke]`.
* A $200\times$ ratio between border cables ($q = 100$) and radial cables ($q = 0.5$) keeps the boundary scallops taut while letting the radial cables drape steeply to the $16\text{ m}$ apex.

### G.2 Figure 6: shifting fixed support coordinates

Translate the high apex support (node 67) horizontally in plan by $(\Delta x, \Delta y) = (0, 0),\ (6, 2),\ (12, 4)\text{ m}$. Because $\mathbf{q}$ is unchanged, $D\ (61 \times 61)$ is invariant and only the right-hand side $\mathbf{P} - D_f \mathbf{X}_f$ updates.

![Fig. 1](images/schek_fig1.png)

![Fig. 6](images/schek_fig6_persp.png)
![Fig. 6, plan](images/schek_fig6_plan.png)

### Apex Shift Summary

$$
\begin{array}{l|ccc}
\text{Run} & \text{Apex Shift } (\Delta x, \Delta y) & \text{Radial Length Range} & \text{Vertical Apex Reaction } R_{67, z} \\
\hline
\texttt{fig6\_1} & (0, 0)\text{ m} & 8.1\text{–}9.0\text{ m} & 38.9\text{ kN} \\
\texttt{fig6\_2} & (6, 2)\text{ m} & 8.0\text{–}9.3\text{ m} & 38.9\text{ kN} \\
\texttt{fig6\_3} & (12, 4)\text{ m} & 8.4\text{–}10.9\text{ m} & 38.9\text{ kN}
\end{array}
$$

**Add to your program:**

```python
# figure 6: different fixed points (the apex moved in plan): only the right-hand sides change
for name, (dx, dy) in zip(["fig6_1", "fig6_2", "fig6_3"], [(0, 0), (6, 2), (12, 4)]):
    xyz, l, s_, R = form_finding(branches5, free5, anchors5(dx, dy), q5, p5)
    keep(name, branches5, xyz, anchors5(dx, dy), fixed5)
    print(f"{name}: apex moved by ({dx}, {dy}) m; radial lengths {l[is_spoke].min():.1f}-{l[is_spoke].max():.1f} m; apex reaction {R[5, 2]:.1f} kN")
keep("fig1", *(lambda r: (branches5, r[0], anchors5(), fixed5))(form_finding(branches5, free5, anchors5(), q5, p5)))
```

* Shifting the apex horizontally changes only the $x$ and $y$ right-hand sides; the $z$ system $D \mathbf{z} = \mathbf{p}_z - D_f \mathbf{z}_f$ is completely untouched, so the vertical apex reaction stays constant at $38.9\text{ kN}$.

**Example output:**

```text
fig6_1: apex moved by (0, 0) m; radial lengths 8.1-9.0 m; apex reaction 38.9 kN
fig6_2: apex moved by (6, 2) m; radial lengths 8.0-9.3 m; apex reaction 38.9 kN
fig6_3: apex moved by (12, 4) m; radial lengths 8.4-10.9 m; apex reaction 38.9 kN
```

### G.3 Figures 7 and 8: varying radial and border force densities

Vary the radial force density $q_{\text{spoke}} \in \{1.0, 0.7, 0.3\}$ (Fig. 7) and border force density $q_{\text{border}} \in \{10, 5, 1\}$ (Fig. 8), rebuilding $D = C^T Q C$ each time.

![Fig. 7](images/schek_fig7_persp.png)
![Fig. 7, plan](images/schek_fig7_plan.png)

![Fig. 8](images/schek_fig8_persp.png)
![Fig. 8, plan](images/schek_fig8_plan.png)

### Parameter Study Results

$$
\begin{array}{l|cc||l|cc}
\text{Fig. 7 Run} & q_{\text{spoke}} & \text{Radial Lengths} & \text{Fig. 8 Run} & q_{\text{border}} & \text{Border Lengths} \\
\hline
\texttt{fig7\_1} & 1.0 & 5.0\text{–}5.9\text{ m} & \texttt{fig8\_1} & 10.0 & 3.4\text{–}4.8\text{ m} \\
\texttt{fig7\_2} & 0.7 & 6.5\text{–}7.4\text{ m} & \texttt{fig8\_2} & 5.0 & 3.5\text{–}4.9\text{ m} \\
\texttt{fig7\_3} & 0.3 & 10.6\text{–}11.6\text{ m} & \texttt{fig8\_3} & 1.0 & 2.9\text{–}6.5\text{ m}
\end{array}
$$

**Add to your program:**

```python
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
```

* `np.where(is_spoke, qs, q5)` replaces $q$ only on the 10 radial spokes (`is_spoke == True`) and keeps `q5` elsewhere.
* Reducing $q_{\text{spoke}}$ from $1.0 \to 0.3$ doubles the radial cable lengths ($5.5\text{ m} \to 11.1\text{ m}$), making the tent steeper and more pointed.

**Example output:**

```text
fig7_1: radial q = 1.0: radial lengths 5.0-5.9 m
fig7_2: radial q = 0.7: radial lengths 6.5-7.4 m
fig7_3: radial q = 0.3: radial lengths 10.6-11.6 m
fig8_1: border q = 10: border lengths 3.4-4.8 m
fig8_2: border q = 5: border lengths 3.5-4.9 m
fig8_3: border q = 1: border lengths 2.9-6.5 m
```

### G.4 Figure 9: prescribed length constraints on 62 interior branches

Constrain all $r = 62$ interior branches not touching the boundary ($10$ radial cables set to $l_{\text{radial}}$, $52$ ring/field cables scaled by `ring_factor`) across $m = 110$ force densities.

### Constrained Runs (62 Equations in 110 Unknowns)

$$
\begin{array}{l|cc|cc}
\text{Run} & \text{Target } l_{\text{radial}} & \text{Ring Scale Factor} & \text{Evaluations} & \max |\mathbf{g}^*(\mathbf{q})| \\
\hline
\texttt{fig9\_1} & 6.0\text{ m} & 1.25 \times \mathbf{l}_{\text{base}} & 42 & 1.2 \times 10^{-9}\text{ m} \\
\texttt{fig9\_2} & 6.0\text{ m} & 0.85 \times \mathbf{l}_{\text{base}} & 35 & 1.1 \times 10^{-9}\text{ m} \\
\texttt{fig9\_3} & 4.5\text{ m} & 0.70 \times \mathbf{l}_{\text{base}} & 58 & 7.5 \times 10^{-10}\text{ m}
\end{array}
$$

**Add to your program:**

```python
# figure 9: distance conditions on all branches not connected with the border (section 3)
base_l = form_finding(branches5, free5, anchors5(), q5, p5)[1]
inner = [j for j in range(len(branches5)) if not touches_border[j]]
for name, (l_radial, ring_factor) in zip(["fig9_1", "fig9_2", "fig9_3"], [(6.0, 1.25), (6.0, 0.85), (4.5, 0.70)]):
    l_v = [l_radial if is_spoke[j] else base_l[j] * ring_factor for j in inner]
    q_k, xyz, l, s_, tries, err = fit_force_densities(branches5, free5, anchors5(), q5, p5, length_rows=inner, l_v=l_v)
    keep(name, branches5, xyz, anchors5(), fixed5)
    print(f"{name}: radial l = {l_radial} m, rings x{ring_factor}: worst length error {err:.1e} after {tries} tries"
          + ("  (NOT solved)" if err > 1e-6 else ""))
```

* Bounded trust-region least squares satisfies all 62 length constraints to $\sim 10^{-9}\text{ m}$ on all three cases.

**Example output:**

```text
fig9_1: radial l = 6.0 m, rings x1.25: worst length error 3.8e-09 after 35 tries
fig9_2: radial l = 6.0 m, rings x0.85: worst length error 6.3e-12 after 38 tries
fig9_3: radial l = 4.5 m, rings x0.7: worst length error 9.1e-10 after 47 tries
```

### G.5 Figure 10: 8x8 grid-shell of 112 bars

Generate an $8 \times 8$ orthogonal grid ($n = 60$ free nodes, $n_f = 4$ corner supports, $m = 112$ bars) and solve three benchmark problems: (10.1) hanging net of 112 equal-length $1.0\text{ m}$ bars under self-weight, (10.2) prestressed saddle with raised corners, and (10.3) mixed equal-length and equal-force constraints.

### Summary of the Three 112-Bar Cases

$$
\begin{array}{l|lll|l}
\text{Case} & \text{Corner Supports} & \text{Load } \mathbf{P} & \text{Constraints} & \text{Result} \\
\hline
\texttt{fig10\_1} & \text{4 corners at } 80\% \text{ span} & \text{bar weight} & l_j = 1.0\text{ m}\ (\forall j=1..112) & |\mathbf{e}_l| \le 7.5\times 10^{-10}\text{ m},\ s \in [0.12, 2.77]\text{ kN} \\
\texttt{fig10\_2} & \text{2 corners lifted to } 3\text{ m} & \mathbf{0} & \text{linear } (q_{\text{border}}=10, q_{\text{in}}=1) & l_{\text{in}} \in [0.65, 0.81]\text{ m} \\
\texttt{fig10\_3} & \text{2 corners lifted to } 3\text{ m} & \mathbf{0} & \text{equal inner } l \text{ + equal link } s & |\mathbf{g}^*| \le 1.3\times 10^{-8}
\end{array}
$$

**Add to your program:**

```python
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
grid_touch = np.array([any(on_edge(v)[0] or on_edge(v)[1] for v in e) for v in grid for e in [v]])
weight = 0.15                                                                   # kN per bar
degree = np.bincount(np.array(grid).ravel())[1:]
p10 = np.zeros((g * g - 4, 3)); p10[:, 2] = -0.5 * weight * degree[:g * g - 4]    # half of every bar's weight at each end
anchors10 = flat[-4:].copy(); anchors10[:, :2] = (anchors10[:, :2] - 3.5) * 0.8 + 3.5   # anchors pulled in to 80 % of the span
q_k, xyz, l, s_, tries, err = fit_force_densities(grid, g * g - 4, anchors10, np.ones(112), p10, length_rows=range(112), l_v=[1.0] * 112)
keep("fig10_1", grid, xyz, anchors10, [renum[c] for c in corners])
print(f"fig10_1: 112 bars of 1.0 m hanging under their weight: worst length error {err:.1e} after {tries} tries; bar forces {s_.min():.2f}-{s_.max():.2f} kN")
anchors10b = anchors10.copy(); anchors10b[[0, 2], 2] = 3.0                      # two corners raised: prestressed net
q10 = np.where(grid_border, 10.0, 1.0)
xyz, l, s_, R = form_finding(grid, g * g - 4, anchors10b, q10, np.zeros_like(p10))
keep("fig10_2", grid, xyz, anchors10b, [renum[c] for c in corners])
print(f"fig10_2: corners raised, inner q = 1, border q = 10: inner lengths {l[~grid_border].min():.2f}-{l[~grid_border].max():.2f} m")
inner10 = [j for j in range(112) if not grid_border[j] and not grid_touch[j]]
link10 = [j for j in range(112) if not grid_border[j] and grid_touch[j]]
q_k, xyz, l, s_, tries, err = fit_force_densities(grid, g * g - 4, anchors10b, q10, np.zeros_like(p10),
                                                  length_rows=inner10, l_v=[l[inner10].mean()] * len(inner10),
                                                  force_rows=link10, s_v=[s_[link10].mean()] * len(link10))
keep("fig10_3", grid, xyz, anchors10b, [renum[c] for c in corners])
print(f"fig10_3: equidistant inner net and constant force near the border: worst error {err:.1e} after {tries} tries")
```

* `order` renumbers the $8 \times 8$ grid so the $60$ free nodes come first (`1..60`) and the $4$ corner supports come last (`61..64`), matching our `[C | C_f]` partition rule from A.2.
* `degree = np.bincount(np.array(grid).ravel())[1:]` counts how many bars meet at each node so each bar's weight ($0.15\text{ kN}$) is lumped half-and-half onto its two endpoints.
* **Key Takeaway (`fig10_1`):** Even when all 112 bars have identical length $l_j = 1.000\text{ m}$, their forces span a $23\times$ range ($0.12\text{ to } 2.77\text{ kN}$)—uniform geometry does not imply uniform force.

**Example output:**

```text
fig10_1: 112 bars of 1.0 m hanging under their weight: worst length error 7.6e-10 after 11 tries; bar forces 0.12-2.77 kN
fig10_2: corners raised, inner q = 1, border q = 10: inner lengths 0.65-0.81 m
fig10_3: equidistant inner net and constant force near the border: worst error 1.6e-08 after 28 tries
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
$D_{11} = q_1 + q_5 + q_6 + q_{10} = 22$,
$D_{33} = q_3 + q_7 + q_8 + q_{12} = 30$,
$D_{55} = q_9 + q_{10} + q_{11} + q_{12} = 42$
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
