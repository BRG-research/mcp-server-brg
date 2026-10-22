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

**Force density.** For branch $j$ with axial force $s_j$ and strained length $l_j$,

$$
q_j = \frac{s_j}{l_j}
$$

*Read it as: how hard the cable pulls, per metre of its own length.*

```text
  one cable:   L = 2.5 m ,  N = 10 kN     ->    q = 10 / 2.5 = 4 kN/m
```

Dimension: force / length (N/m, kN/m). The same force gives a larger $q$ in a
shorter branch. Schek calls $q$ the "network description parameter": prescribing
$q$ for every branch selects an equilibrium shape when the resulting free-node
system is nonsingular.

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

- $q_j \gt 0$ and $s_j \gt 0$: tension. A net with all $q_j \gt 0$ has a
  positive-definite free-node matrix and a unique solution if every connected
  component containing free nodes also contains at least one fixed node.
- $q_j \lt 0$: compression. `compas_fd` accepts negative values (FormFinder uses them
  for compression-only funiculars), but mixed signs can make the matrix singular
  or indefinite; check the residuals.
- Loads $p$ are external forces on nodes in global $x, y, z$; gravity is a negative $p_z$
  when $z$ points up.
- The **residual** returned by the solver is $r = p - C^{t} Q C x$. At free nodes it is
  zero at convergence. At a fixed node it includes the applied load and the resultant
  branch force; the **support reaction** acting on the network is $-r$. With
  zero applied loads at supports, $r$ is the force the cables exert on the support.

**Units.** The method is unit-agnostic as long as coordinates, loads, and force
densities are consistent (e.g. m, kN, kN/m). Forces returned are $q \cdot l$ in the
load unit; lengths are in the coordinate unit.

## How to read the mathematics in this tutorial

Every equation below is written twice: once in Schek's notation, then **immediately
as the actual numbers of the 12-branch net**, printed with labelled rows and
columns. If a formula does not click, read the numbers under it instead.

**Three habits.**

1. **Small letter = a list. Capital = that list on a diagonal.** Schek never writes
   "diag" because the capital already says it.
2. **Read a product right to left, in stages.** $C^{t} U L^{-1} s$ is four steps:
   forces in, divide by lengths, project onto an axis, sum at the nodes. Each stage
   is shown with its own numbers.
3. **Check the shapes.** `(5, 12) @ (12,)` works and gives `(5,)` — the inner
   numbers must match, the outer ones are the answer's size.

| Symbol | Say it | What it is | Code | Shape here |
|---|---|---|---|---|
| $u, v, w$ | "u, v, w" | coordinate differences across each branch, per axis | `u` | `(12,)` |
| $U, V, W$ | "capital U" | those lists on a diagonal | `np.diag(u)` | `(12, 12)` |
| $l$ / $L$ | "l" / "capital L" | branch lengths / their diagonal | `l` | `(12,)` |
| $s$ | "s" | force in each branch | `s` | `(12,)` |
| $q$ / $Q$ | "q" / "capital Q" | **force density** $s_j/l_j$ / its diagonal | `q` | `(12,)` |
| $C_s$ | "C sub s" | branch-node table, one row per cable, one column per node | `C_s` | `(12, 9)` |
| $C$ | "C" | the **free**-node columns of $C_s$ | `C` | `(12, 5)` |
| $C_f$ | "C sub f" | the **anchor** columns of $C_s$ | `C_f` | `(12, 4)` |
| $C^{t}$ | "C transposed" | $C$ with rows and columns swapped | `C.T` | `(5, 12)` |
| $x, y, z$ | "x, y, z" | free-node coordinates — **the unknowns** | `x` | `(5,)` |
| $x_f, y_f, z_f$ | "x sub f" | anchor coordinates — **given** | `x_f` | `(4,)` |
| $p_x, p_y, p_z$ | "p sub x" | loads at the free nodes — **given** | `p_x` | `(5,)` |
| $D$ | "D" | $C^{t} Q C$, the matrix that gets solved | `D` | `(5, 5)` |
| $D_f$ | "D sub f" | $C^{t} Q C_f$, the anchor coupling | `D_f` | `(5, 4)` |
| $G^{t}$ | "G transposed" | sensitivity table: each wish vs each $q_j$ | `G_t` | `(r, 12)` |

| Notation | Code | Means |
|---|---|---|
| $A B$ | `A @ B` | matrix multiplication |
| $a_j b_j$ | `a * b` | entry by entry — **not** a matrix product |
| $A^{t}$ | `A.T` | transpose |
| $\mathrm{diag}(a)$ | `np.diag(a)` | put the list `a` on a diagonal |
| solve $Dx = b$ | `np.linalg.solve(D, b)` | find `x`; never form $D^{-1}$ |

<!-- schek-app:start -->

## Build the force density method step by step

Start with an empty Python file or notebook. Follow the subsections in order:
each adds data or a calculation that the following steps need. The complete
program is also available in `examples/form_finding/schek_app.py`.

Read each explanation, then append its code to the same Python file or notebook.
Every subsection has the same shape: **what the step does**, the **equation**,
the **stages read right to left**, and **the same thing with our numbers** —
every matrix printed with labelled rows and columns so you can point at any
entry and say where it came from. A.4 has no code: it is the five matrix
operations worked through with real numbers.

`@` is matrix multiplication. `*` is entry-by-entry multiplication. Shapes are
written next to every array. Displayed output is rounded; the calculation keeps
full precision. Parts A to E need only NumPy; part F adds `scipy.optimize`.

| Milestone | What you can do |
|---|---|
| A.1–A.4 | Represent a network and understand its matrix operations. |
| B.1–B.3 | Compute branch geometry and test nodal equilibrium. |
| C.1–C.4 | Derive and execute the linear force density solve. |
| D.1–D.2 | Reuse a complete linear solver with different supports and force densities. |
| E.1 | Interpret the geometric effect of force densities. |
| F.1–F.5 | Extend the solver to prescribed lengths and forces. |
| G.1–G.5 | Apply the same solvers to larger reconstructed examples. |

**The linear force density method is complete at D.2.** Part F is a nonlinear
extension, not a prerequisite for using the linear method. Package API details
follow the tutorial for comparison after implementing the method yourself.

This tutorial is generated from the program by `build_note.py`; it executes
each implementation block before updating this Markdown.

Contents

- **Part A. The network as data**
  - [A.1 How the paper writes vectors and matrices (section 1.4)](#a1-how-the-paper-writes-vectors-and-matrices-section-14)
  - [A.2 Numbering the nodes and branches (section 2.1)](#a2-numbering-the-nodes-and-branches-section-21)
  - [A.3 The branch-node matrix C_s and its two column blocks (section 2.1)](#a3-the-branch-node-matrix-c_s-and-its-two-column-blocks-section-21)
  - [A.4 Reading matrices: the five operations the paper uses](#a4-reading-matrices-the-five-operations-the-paper-uses)
- **Part B. Equilibrium, the nonlinear form**
  - [B.1 The data: anchors and loads (section 2.2)](#b1-the-data-anchors-and-loads-section-22)
  - [B.2 Coordinate differences and lengths, equation (1)](#b2-coordinate-differences-and-lengths-equation-1)
  - [B.3 Equilibrium with the unknown forces, equation (2)](#b3-equilibrium-with-the-unknown-forces-equation-2)
- **Part C. The force density trick: a linear system**
  - [C.1 The force density, equations (4) to (6)](#c1-the-force-density-equations-4-to-6)
  - [C.2 The matrices D and D_f, equations (7) and (8)](#c2-the-matrices-d-and-d_f-equations-7-and-8)
  - [C.3 Solving for the free coordinates, equation (9)](#c3-solving-for-the-free-coordinates-equation-9)
  - [C.4 Lengths, forces and the equilibrium check, equation (10)](#c4-lengths-forces-and-the-equilibrium-check-equation-10)
- **Part D. The form-finding loop**
  - [D.1 The form-finding loop as one function (figure 3)](#d1-the-form-finding-loop-as-one-function-figure-3)
  - [D.2 Using the loop: move the anchors, change the force densities](#d2-using-the-loop-move-the-anchors-change-the-force-densities)
- **Part E. What the force densities mean**
  - [E.1 What the force densities mean geometrically (section 4)](#e1-what-the-force-densities-mean-geometrically-section-4)
- **Part F. Additional conditions**
  - [F.1 Asking for more than equilibrium (section 3.1)](#f1-asking-for-more-than-equilibrium-section-31)
  - [F.2 Letting SciPy find the force densities (sections 3.1 to 3.6)](#f2-letting-scipy-find-the-force-densities-sections-31-to-36)
  - [F.3 What the solver feels its way with: the Jacobian (sections 3.2 to 3.4)](#f3-what-the-solver-feels-its-way-with-the-jacobian-sections-32-to-34)
- **Part G. The paper's examples, computed and drawn**
  - [G.1 The network of figure 5 (section 5)](#g1-the-network-of-figure-5-section-5)
  - [G.2 Figure 6: different fixed points](#g2-figure-6-different-fixed-points)
  - [G.3 Figures 7 and 8: changing the force densities](#g3-figures-7-and-8-changing-the-force-densities)
  - [G.4 Figure 9: additional distance conditions](#g4-figure-9-additional-distance-conditions)
  - [G.5 Figure 10: the grid-shell model of 112 identical bars](#g5-figure-10-the-grid-shell-model-of-112-identical-bars)

## Part A. The network as data

### A.1 How the paper writes vectors and matrices (section 1.4)

**Do this.** Import NumPy, make one vector, turn it into a diagonal matrix. This fixes the alphabet; nothing is solved yet.

#### THE WHOLE ALPHABET

| Symbol | Say it as | What it is | Code | Shape |
|---|---|---|---|---|
| $u$ | "u" | a **list** of numbers, one per branch | `u` | `(12,)` |
| $U$ | "capital U" | that same list on the **diagonal** of a square table | `np.diag(u)` | `(12, 12)` |
| $C$ | "C" | a **table** of numbers | `C` | `(12, 5)` |
| $C^{t}$ | "C transposed" | the table turned on its side | `C.T` | `(5, 12)` |
| $A B$ | "A times B" | matrix multiplication | `A @ B` | |
| $a_j b_j$ | "a times b, entry by entry" | **not** matrix multiplication | `a * b` | |
| $L^{-1}$ | "L inverse" | for a diagonal $L$: one over each entry | `np.diag(1.0 / l)` | |

**RULE: small letter = a list. Same letter capitalised = that list on a diagonal.** Schek never writes "diag" because the capital already says it.

#### WITH NUMBERS

$$
u = \begin{pmatrix} 2 \\ -1 \\ 3 \end{pmatrix}
\qquad
U = \mathrm{diag}(u) = \begin{pmatrix} 2 & 0 & 0 \\ 0 & -1 & 0 \\ 0 & 0 & 3 \end{pmatrix}
$$

```text
u_example   (3,)      [  2.  -1.   3. ]

U_example   (3, 3)         c1   c2   c3
                     r1 [[  2.   0.   0. ]
                     r2  [  0.  -1.   0. ]
                     r3  [  0.   0.   3. ]]
                                           = 3 rows
```

**REASON:** multiplying by a diagonal matrix scales **each entry on its own** — entry 1 by 2, entry 2 by −1, entry 3 by 3. Nothing mixes between entries. C.1 uses this to give every cable its own force density.

**Add to your program:**

```python
import numpy as np
from typing import TypeAlias

FloatMatrix: TypeAlias = np.ndarray[tuple[int, int], np.dtype[np.float64]]
FloatVector: TypeAlias = np.ndarray[tuple[int], np.dtype[np.float64]]

u_example = np.array([2.0, -1.0, 3.0])
U_example = np.diag(u_example)
```

#### LINE BY LINE

- `import numpy as np` — the array library. From here `np.something` is NumPy.
- `FloatMatrix` / `FloatVector` — **labels for the reader only**. They say "2-D array of decimals" and "1-D array". No new kind of array is created.
- `u_example = np.array([2.0, -1.0, 3.0])` — the list, shape `(3,)`.
- `U_example = np.diag(u_example)` — the `(3, 3)` table with those numbers on the diagonal.

### A.2 Numbering the nodes and branches (section 2.1)

**Do this.** Write down the branch list and the two node counts. **Free nodes first, anchors last.** Topology only — no coordinates, no forces yet.

#### THE COUNTS

| Symbol | Say it as | Meaning | Value |
|---|---|---|---|
| $n$ | "n" | **free** nodes (we solve for these) | `5` |
| $n_f$ | "n sub f" | **fixed** nodes (anchors, given) | `4` |
| $n_s$ | "n sub s" | all nodes, $n + n_f$ | `9` |
| $m$ | "m" | branches (cables) | `12` |
| $i(j)$ | "i of j" | **start** node of branch $j$ | $i(1) = 1$ |
| $k(j)$ | "k of j" | **end** node of branch $j$ | $k(1) = 6$ |

**REASON for free-first:** in A.3 the connectivity table is cut in two by one straight vertical line — free columns left, anchor columns right. Scattered anchors would make that single cut impossible.

![Fig. 2](images/schek_fig2.png)

*Fig. 2, redrawn: the graph and its branch-node matrix.*

#### THE 12 BRANCHES — INPUT

| $j$ | $i(j)$ start | $k(j)$ end | tuple | group |
|---|---|---|---|---|
| 1 | 1 | 6 | `(1, 6)` | anchor cable |
| 2 | 2 | 7 | `(2, 7)` | anchor cable |
| 3 | 3 | 8 | `(3, 8)` | anchor cable |
| 4 | 4 | 9 | `(4, 9)` | anchor cable |
| 5 | 1 | 4 | `(1, 4)` | ring |
| 6 | 1 | 2 | `(1, 2)` | ring |
| 7 | 2 | 3 | `(2, 3)` | ring |
| 8 | 3 | 4 | `(3, 4)` | ring |
| 9 | 4 | 5 | `(4, 5)` | spoke to centre |
| 10 | 1 | 5 | `(1, 5)` | spoke to centre |
| 11 | 2 | 5 | `(2, 5)` | spoke to centre |
| 12 | 3 | 5 | `(3, 5)` | spoke to centre |

**Every matrix in the rest of the tutorial is this table in another shape.**

#### TWO NUMBERING SYSTEMS — DO NOT MIX

```text
  Schek numbers nodes and branches from 1 :  branch 1 is (1, 6)
  Python indexes lists and arrays from 0  :  branches[0] is branch 1

  so a node label becomes a column index by subtracting 1.
```

**Add to your program:**

```python
branches: list[tuple[int, int]] = [(1, 6), (2, 7), (3, 8), (4, 9),      # 1-4: one branch from each free corner to its anchor
            (1, 4), (1, 2), (2, 3), (3, 4),      # 5-8: the ring
            (4, 5), (1, 5), (2, 5), (3, 5)]      # 9-12: four spokes to the centre node 5
n, n_f = 5, 4                                    # free nodes 1..5, fixed nodes 6..9
m = len(branches)
```

#### LINE BY LINE

- `branches = [(1, 6), (2, 7), ...]` — the twelve tuples above, in order. **Position in the list = branch number.** The two entries are node numbers, never coordinates.
- `n, n_f = 5, 4` — five free, four fixed.
- `m = len(branches)` — counts the tuples: `12`.

Not one line here makes geometry or a force. Pure topology.

### A.3 The branch-node matrix C_s and its two column blocks (section 2.1)

**Do this.** Turn the branch list into a table of numbers that can be multiplied. One row per branch, one column per node. Then cut the columns into free and anchor blocks.

#### EQUATION

$$
c(j, i) =
\begin{cases}
+1 & \text{node } i \text{ is the START of branch } j \\
-1 & \text{node } i \text{ is the END of branch } j \\
0 & \text{node } i \text{ is not on branch } j
\end{cases}
$$

*Read it as: the entry in row $j$, column $i$ is $+1$, $-1$ or $0$ depending on how node $i$ sits on branch $j$.* That is all the formula says.

```text
  C_s   ( m  x  n_s )  =  ( 12  x  9 )
          |     |            |     |
        cable  node        cable  node
```

**REASON for +1 and −1:** so that one row **subtracts the two end coordinates**. Branch 1 is `(1, 6)`, so row 1 is $+1$ in column 1, $-1$ in column 6:

$$
(+1)x_1 + 0x_2 + 0x_3 + 0x_4 + 0x_5 + (-1)x_6 + 0x_7 + 0x_8 + 0x_9 \;=\; x_1 - x_6
$$

```text
  row 1 of C_s :   +1    0    0    0    0   -1    0    0    0
  node         :    1    2    3    4    5    6    7    8    9
                    ^                        ^
                   keep                     keep, negated     ->  x_1 - x_6
```

The seven zeros delete seven nodes. **One row measures one cable.** The signs are direction only — not tension/compression, not free/fixed.

**CHECK: every row sums to 0** (one $+1$, one $-1$, rest zero). Every branch has exactly two ends.

#### WITH OUR NUMBERS — $C_s$ (12 × 9)

```text
             n1   n2   n3   n4   n5  |  n6   n7   n8   n9      reads as
  br 1  [[    1    0    0    0    0  |  -1    0    0    0 ]    x1 - x6
  br 2   [    0    1    0    0    0  |   0   -1    0    0 ]    x2 - x7
  br 3   [    0    0    1    0    0  |   0    0   -1    0 ]    x3 - x8
  br 4   [    0    0    0    1    0  |   0    0    0   -1 ]    x4 - x9
  br 5   [    1    0    0   -1    0  |   0    0    0    0 ]    x1 - x4
  br 6   [    1   -1    0    0    0  |   0    0    0    0 ]    x1 - x2
  br 7   [    0    1   -1    0    0  |   0    0    0    0 ]    x2 - x3
  br 8   [    0    0    1   -1    0  |   0    0    0    0 ]    x3 - x4
  br 9   [    0    0    0    1   -1  |   0    0    0    0 ]    x4 - x5
  br10   [    1    0    0    0   -1  |   0    0    0    0 ]    x1 - x5
  br11   [    0    1    0    0   -1  |   0    0    0    0 ]    x2 - x5
  br12   [    0    0    1    0   -1  |   0    0    0    0 ]]   x3 - x5
                                                              = 12 rows
              \__________________/      \______________/
                   C  (12 x 5)             C_f (12 x 4)
                   FREE nodes              ANCHOR nodes
```

#### THE CUT: $C_s = [\,C \;\; C_f\,]$

$$
C_s = \begin{bmatrix} C & C_f \end{bmatrix}
\qquad
C:\; m \times n = 12 \times 5
\qquad
C_f:\; m \times n_f = 12 \times 4
$$

```text
C      (12, 5)   = columns n1..n5, the five free nodes
C_f    (12, 4)   = columns n6..n9, the four anchors
```

Look at the $C_f$ block above: **only rows 1–4 carry anything.** That is the whole structural story — only branches 1–4 reach an anchor. Rows 5–12 are all zero there because the ring and spokes join free nodes to free nodes.

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

#### LINE BY LINE

- `C_s = np.zeros((m, n + n_f))` — empty table, 12 rows (branches) by 9 columns (nodes), all `0.0`.
- `for j, (i, k) in enumerate(branches):` — `j` counts branches from `0`; `i`, `k` are the end nodes as **Schek** numbers them (from `1`).
- `C_s[j, i - 1] = +1.0` — row `j`, column of the start node. The `- 1` converts Schek's numbering to Python's.
- `C_s[j, k - 1] = -1.0` — same row, column of the end node.
- `C = C_s[:, :n]` — "all rows, first 5 columns" = free block. `C_f = C_s[:, n:]` — "all rows, from column 5 on" = anchor block. Nothing is copied; the one table is read in two pieces.

**CHECK IT YOURSELF:** row `0` of the printout should read `[1 0 0 0 0 -1 0 0 0]` — branch 1, node 1 to node 6. Row index `j` is branch `j+1`; column index `i` is node `i+1`.

> **Try it.** Change `(1, 6)` to `(6, 1)`. Row 0 flips to `[-1 0 0 0 0 1 0 0 0]`, so it measures $x_6 - x_1$ instead. The final shape the solver finds is **identical** — only the bookkeeping direction changed.

Example output:

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

### A.4 Reading matrices: the five operations the paper uses

**Read only — no code.** These five operations are everything the paper does to matrices. Each one below is worked with the real numbers of our net.

Trial shape used here (free nodes flat, anchors from B.1):

```text
  node :     1     2     3     4     5  |    6     7     8     9
  x_s  = [ -1.0   0.0   1.0   0.0   0.0 | -2.0   0.0   2.0   0.0 ]   INPUT
```

#### 1 — A MATRIX IS A LABELLED TABLE

Row $j$ = branch $j$. Column $i$ = node $i$. Entry = how node $i$ sits on branch $j$.

#### 2 — MATRIX @ VECTOR : MULTIPLY, THEN ADD

$$ u = C_s\, x_s $$

*Read it as: multiply each row of the table by the list, entry by entry, and add the products into one number.*

Pick **row 1** and lay it against $x_s$:

```text
  row 1 of C_s :   +1     0     0     0     0    -1     0     0     0
  x_s          :   -1.0   0.0   1.0   0.0   0.0  -2.0   0.0   2.0   0.0
                  -----  ----  ----  ----  ----  -----  ----  ----  ----
  multiply     :   -1.0   0.0   0.0   0.0   0.0  +2.0   0.0   0.0   0.0
  add          :   -1.0 + 2.0  =  +1.0                    = x_1 - x_6
```

**One row gives one number. Twelve rows give twelve numbers:**

```text
  C_s @ x_s   (12,)
  branch:   1    2    3    4    5    6    7    8    9   10   11   12
          [ 1.   0.  -1.   0.  -1.  -1.  -1.   1.   0.  -1.   0.   1. ]   = 12
```

```text
  SHAPES:   (12, 9) @ (9,)  ->  (12,)
                  ^     ^
                  these must match         the answer is 12 long
```

#### 3 — TRANSPOSE @ VECTOR : ADD UP AT THE NODES

$$ C^{t} f $$

*Read it as: collect the branch values at each node, $+$ if the branch starts there, $-$ if it ends there.*

$C^{t}$ is $C$ on its side, so the answer has **one number per node**, not per branch. It collects the branch values $f_j$ meeting that node: $+$ if the branch starts there, $-$ if it ends there. This is summing forces at a joint.

Give every branch $f_j = 1$:

```text
  f   (12,)   [ 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. ]

  C.T @ f   (5,)
  node 1: branches  1(+)  5(+)  6(+) 10(+)  =  +1 +1 +1 +1  =   4.
  node 2: branches  2(+)  6(-)  7(+) 11(+)  =  +1 -1 +1 +1  =   2.
  node 3: branches  3(+)  7(-)  8(+) 12(+)  =  +1 -1 +1 +1  =   2.
  node 4: branches  4(+)  5(-)  8(-)  9(+)  =  +1 -1 -1 +1  =   0.
  node 5: branches  9(-) 10(-) 11(-) 12(-)  =  -1 -1 -1 -1  =  -4.
                                        result = [ 4.  2.  2.  0. -4. ]   = 5
```

```text
  SHAPES:   (5, 12) @ (12,)  ->  (5,)
```

**REASON:** operation 2 carries information **nodes → branches**; operation 3 carries it **branches → nodes**. Every equilibrium equation below is one of each.

#### 4 — DIAGONAL @ VECTOR : SCALE EACH ENTRY ALONE

$$ Q u \quad\text{where}\quad Q = \mathrm{diag}(q) $$

*Read it as: entry $j$ of the answer is just $q_j$ times $u_j$.*

Entry $j$ of the answer is just $q_j u_j$. No mixing.

```text
  branch :    1     2     3     4     5     6     7     8     9    10    11    12
  q      = [  2.    2.    2.    2.    1.    1.    1.    1.    1.    1.    1.    1.  ]
  u      = [  1.    0.   -1.    0.   -1.   -1.   -1.    1.    0.   -1.    0.    1.  ]
            ---------------------------------------------------------------------
  Q @ u  = [  2.    0.   -2.    0.   -1.   -1.   -1.    1.    0.   -1.    0.    1.  ]   = 12
```

Each column is the product of the two numbers above it. So the order can be swapped: $U q = Q u$. **That swap is the whole force density trick** — C.1 cashes it in.

#### 5 — SOLVING $D x = b$

$$ D x = b \quad\longrightarrow\quad \texttt{x = np.linalg.solve(D, b)} $$

*Read it as: find the list $x$ that, pushed through the table $D$, gives back $b$.*

Find the list $x$ that, pushed through $D$, gives back $b$. This is the real system of C.3:

```text
        D   (5 x 5)                   z (5)        b_z (5)
         n1   n2   n3   n4   n5
  n1 [[   5.  -1.   0.  -1.  -1. ]     [ z1 ]       [ -0.5 ]
  n2  [  -1.   5.  -1.   0.  -1. ]     [ z2 ]       [  1.5 ]
  n3  [   0.  -1.   5.  -1.  -1. ]  @  [ z3 ]   =   [ -0.5 ]
  n4  [  -1.   0.  -1.   5.  -1. ]     [ z4 ]       [  1.5 ]
  n5  [  -1.  -1.  -1.  -1.   4. ]]    [ z5 ]       [ -0.5 ]

  answer    z = [ 0.045   0.330   0.045   0.330   0.063 ]

  CHECK   D @ z = [ -0.5   1.5  -0.5   1.5  -0.5 ]   <- exactly b
```

NumPy never forms $D^{-1}$ to do this, and neither should you: solving directly is faster and more accurate.

#### WHERE THIS GOES

$$ D = C^{t} Q C $$

*Read it as: spread the coordinates onto the branches, scale each branch by its force density, sum back at the nodes.*

is **operation 3 wrapped around operation 4 wrapped around operation 2**: spread the coordinates onto branches, scale each branch by its force density, sum back at the nodes.

## Part B. Equilibrium, the nonlinear form

### B.1 The data: anchors and loads (section 2.2)

**Do this.** Add the anchor coordinates and the loads. Metres, kilonewtons, $z$ up. Free coordinates stay unknown until C.3.

#### WHAT IS KNOWN, WHAT IS NOT

| Symbol | Say it as | Known? | Shape | Holds |
|---|---|---|---|---|
| $x_f, y_f, z_f$ | "x sub f" | **INPUT** | `(4,)` each | one coordinate of each anchor 6–9 |
| $p_x, p_y, p_z$ | "p sub x" | **INPUT** | `(5,)` each | one load component at each free node |
| $x, y, z$ | "x, y, z" | **unknown — the answer** | `(5,)` each | one coordinate of each free node 1–5 |
| $l_j$ | "l sub j" | follows from the shape | `(12,)` | length of branch $j$ |
| $s_j$ | "s sub j" | follows from the shape | `(12,)` | force in branch $j$ |

**These values are our choice, not measurements from Schek.** Figure 2 gives only the connectivity.

#### WITH OUR NUMBERS — INPUT

| anchor | x (m) | y (m) | z (m) | |
|---|---|---|---|---|
| 6 | −2 | 0 | 0 | ground level |
| 7 | 0 | 2 | **1** | lifted |
| 8 | 2 | 0 | 0 | ground level |
| 9 | 0 | −2 | **1** | lifted |

```text
  anchor:      6      7      8      9
  x_f  (4,) [ -2.0    0.0    2.0    0.0 ]
  y_f  (4,) [  0.0    2.0    0.0   -2.0 ]
  z_f  (4,) [  0.0    1.0    0.0    1.0 ]    <- nodes 7 and 9 are the lifted pair

  free node:   1      2      3      4      5
  p_x  (5,) [  0.0    0.0    0.0    0.0    0.0 ]
  p_y  (5,) [  0.0    0.0    0.0    0.0    0.0 ]
  p_z  (5,) [ -0.5   -0.5   -0.5   -0.5   -0.5 ]   <- negative = DOWN
```

**Read down a column** across the three arrays to get one anchor point: node 6 is $(-2, 0, 0)$.

**REASON for the minus sign:** $z$ points up, so gravity is a negative $p_z$. That minus is the only thing making this net hang instead of rise.

**Add to your program:**

```python
x_f: FloatVector = np.array([-2.0, 0.0, 2.0, 0.0], dtype=np.float64)             # anchors 6, 7, 8, 9
y_f: FloatVector = np.array([0.0, 2.0, 0.0, -2.0], dtype=np.float64)
z_f: FloatVector = np.array([0.0, 1.0, 0.0, 1.0], dtype=np.float64)             # two anchors lifted by 1 m
p_x: FloatVector = np.zeros(n, dtype=np.float64)
p_y: FloatVector = np.zeros(n, dtype=np.float64)
p_z: FloatVector = np.full(n, -0.5, dtype=np.float64)                            # 0.5 kN downward at every free node
```

#### LINE BY LINE

- `np.array([-2.0, 0.0, 2.0, 0.0], dtype=np.float64)` — one anchor coordinate list. `dtype=np.float64` means ordinary decimals.
- `np.zeros(n)` — five zeros: no sideways load.
- `np.full(n, -0.5)` — five copies of `-0.5`: half a kilonewton down at every free node.

### B.2 Coordinate differences and lengths, equation (1)

**Do this.** Write one function that, **given** node positions, measures every branch: three coordinate differences and a length. It never moves a node.

#### EQUATION (1)

$$
u = C x + C_f x_f, \qquad v = C y + C_f y_f, \qquad w = C z + C_f z_f
$$

*Read it as: for every branch, subtract the coordinates of its two end nodes — the free end from one product, the anchored end from the other.*

```text
   u     =      C      @   x    +    C_f     @   x_f
  (12,)      (12 x 5)     (5,)     (12 x 4)      (4,)
             cable x       free     cable x      anchor
              free         coords    anchor      coords
```

$$
l_j = \sqrt{u_j^{2} + v_j^{2} + w_j^{2}}
$$

*Read it as: ordinary Pythagoras on each branch alone.* This is **not** a matrix operation.

```text
  branch 2 :   u = 0.000 ,  v = -3.000 ,  w = -1.000
               l = sqrt( 0.000 + 9.000 + 1.000 ) = 3.162 m
```

**REASON for two products added:** a branch can have one end free and one end anchored. $C x$ collects what comes from free nodes, $C_f x_f$ collects what comes from anchors, and `+` puts the two halves of the same subtraction back together.

```text
  branch 1 (1,6):   from C@x :  x_1      from C_f@x_f : -x_6     sum:  x_1 - x_6
  branch 6 (1,2):   from C@x :  x_1-x_2  from C_f@x_f :  0       sum:  x_1 - x_2
```

$l_j$ is **not** a matrix operation — it is plain Pythagoras on each branch alone.

#### WITH OUR NUMBERS — the flat trial shape of B.3

```text
  free    node 1 (-1, 0, 0)   node 2 ( 0,-1, 0)   node 3 ( 1, 0, 0)
          node 4 ( 0, 1, 0)   node 5 ( 0, 0, 0)
  anchor  node 6 (-2, 0, 0)   node 7 ( 0, 2, 1)
          node 8 ( 2, 0, 0)   node 9 ( 0,-2, 1)
```

```text
  branch         u        v        w        l         check by hand
  ---------------------------------------------------------------------
   1 (1,6)     1.000    0.000    0.000    1.000     x: -1 - (-2) = 1
   2 (2,7)     0.000   -3.000   -1.000    3.162     y: -1 - 2 = -3, z: 0 - 1 = -1
   3 (3,8)    -1.000    0.000    0.000    1.000     x:  1 - 2 = -1
   4 (4,9)     0.000    3.000   -1.000    3.162     y:  1 - (-2) = 3
   5 (1,4)    -1.000   -1.000    0.000    1.414     sqrt(1+1) = 1.414
   6 (1,2)    -1.000    1.000    0.000    1.414
   7 (2,3)    -1.000   -1.000    0.000    1.414
   8 (3,4)     1.000   -1.000    0.000    1.414
   9 (4,5)     0.000    1.000    0.000    1.000
  10 (1,5)    -1.000    0.000    0.000    1.000
  11 (2,5)     0.000   -1.000    0.000    1.000
  12 (3,5)     1.000    0.000    0.000    1.000
                                                    = 12 rows
```

**Row 2 by hand:** branch 2 joins node 2 at $(0,-1,0)$ to anchor 7 at $(0,2,1)$. Start minus end: $u = 0-0 = 0$, $v = -1-2 = -3$, $w = 0-1 = -1$, $l = \sqrt{0+9+1} = 3.162$.

$u, v, w$ together are the branch's **direction vector**; dividing by $l$ gives the direction cosines B.3 needs.

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

#### LINE BY LINE

- `u = C @ x + C_f @ x_f` — `(12,5)@(5,)` gives 12 numbers, `(12,4)@(4,)` gives 12 numbers, added entry by entry. For branch 1 that is $x_1 - x_6$: the $+1$ lives in `C`, the $-1$ in `C_f`.
- `v = ...`, `w = ...` — the identical product with the $y$ and $z$ coordinates.
- `l = np.sqrt(u**2 + v**2 + w**2)` — `u**2` squares **every entry at once**, no loop. `np.sqrt` roots every entry.
- The function takes `C`, `C_f` and the coordinates as **arguments**, so D.1 can reuse it on any network.

**THIS IS WHERE THE DIFFICULTY COMES FROM.** $l$ holds a square root of the unknown coordinates, and B.3 divides by it.

### B.3 Equilibrium with the unknown forces, equation (2)

**Do this.** Write the honest force balance: at every free node the cable pulls must add up to the applied load. Then test it on a guessed shape and watch it fail.

#### EQUATION (2)

$$
C^{t} U L^{-1} s = p_x, \qquad C^{t} V L^{-1} s = p_y, \qquad C^{t} W L^{-1} s = p_z
$$

*Read it as: split each cable force into its $x$, $y$ and $z$ shares, add those shares up at every node, and the total must equal the load there.*

#### READ IT RIGHT TO LEFT — FOUR STAGES

```text
   C.T   @   np.diag(u)   @   L_inv   @   s     -    p_x
   ---       ----------       -----       ---        ---
    3            2              1          1          4

   1  force densities       : divide each force by its cable length,  s_j / l_j
   2  projections           : multiply by u_j -> the x part of that pull
   3  cable force -> nodes  : sum the pulls at each node (transpose)
   4  check equilibrium     : subtract the load.  ZERO = balanced
```

| Step | Symbol | Say it as | What it does | Shape of the result |
|---|---|---|---|---|
| 1 | $L^{-1} s$ | "L inverse times s" | divides each force by its own cable length, $s_j / l_j$ | `(12,)` |
| 2 | $U L^{-1} s$ | "U times that" | multiplies each by $u_j$: the $x$ part of that pull | `(12,)` |
| 3 | $C^{t}(\ldots)$ | "C transposed times that" | sums those parts at every node | `(5,)` |
| 4 | $-\,p_x$ | "minus p sub x" | subtracts the load. **Zero means balanced** | `(5,)` |

**REASON for $u_j / l_j$:** that is the **direction cosine** — how much of branch $j$ points along $x$. Times the force $s_j$ it gives the $x$ share of the pull.

#### WITH OUR NUMBERS — flat shape, 1 kN in every cable

```text
  INPUT    s  (12,)  [ 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. ]
           l  (12,)  [ 1.  3.162  1.  3.162  1.414 1.414 1.414 1.414  1. 1. 1. 1. ]

  STAGE 1   L_inv @ s  = s / l                                       (12,)
  branch:    1      2      3      4      5      6      7      8      9     10     11     12
          [ 1.000  0.316  1.000  0.316  0.707  0.707  0.707  0.707  1.000  1.000  1.000  1.000 ]  = 12

  STAGE 2   np.diag(w) @ (stage 1)   -> the VERTICAL part               (12,)
  w      = [ 0.    -1.     0.    -1.     0.     0.     0.     0.     0.     0.     0.     0.   ]
          [ 0.000 -0.316  0.000 -0.316  0.000  0.000  0.000  0.000  0.000  0.000  0.000  0.000 ]  = 12
                   ^^^^^^        ^^^^^^
                   only the two cables to the LIFTED anchors pull vertically

  STAGE 3   C.T @ (stage 2)                                            (5,)
  node 1: branches  1(+)  5(+)  6(+) 10(+)  =  0 + 0 + 0 + 0            =  0.000
  node 2: branches  2(+)  6(-)  7(+) 11(+)  = -0.316 + 0 + 0 + 0        = -0.316
  node 3: branches  3(+)  7(-)  8(+) 12(+)  =  0 + 0 + 0 + 0            =  0.000
  node 4: branches  4(+)  5(-)  8(-)  9(+)  = -0.316 + 0 + 0 + 0        = -0.316
  node 5: branches  9(-) 10(-) 11(-) 12(-)  =  0 + 0 + 0 + 0            =  0.000
                                     result = [ 0.  -0.316   0.  -0.316   0. ]   = 5

  STAGE 4   (stage 3) - p_z                                            (5,)
          [  0.000  -0.316   0.000  -0.316   0.000 ]
        - [ -0.500  -0.500  -0.500  -0.500  -0.500 ]
          -------------------------------------------
     e_z = [  0.500   0.184   0.500   0.184   0.500 ]   <- NOT ZERO
```

The same four stages on the other two axes give

```text
     e_x = [ -1.414   0.000   1.414   0.000   0.000 ]
     e_y = [  0.000  -3.363   0.000   3.363   0.000 ]
```

**NOT ONE NODE BALANCES.** A flat net has no vertical component anywhere, so it cannot carry a vertical load. Nodes 2 and 4 are less wrong only because their anchors were lifted, giving those two cables something vertical to offer.

#### WHY THIS EQUATION IS A DEAD END

$u, v, w$ and $l$ **all** depend on the unknown coordinates, and $l$ buries them under a square root. $x$ cannot be isolated. There is no formula — only guessing. C.1 fixes this with one substitution.

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

#### LINE BY LINE

- `L_inv = np.diag(1.0 / l)` — the paper's $L^{-1}$. For a diagonal matrix the inverse is the diagonal of the reciprocals, so `1.0 / l` divides entry by entry.
- `C.T @ np.diag(u) @ L_inv @ s - p_x` — the four stages above, in one line, read from the right.
- The three return values are the three axes; `ez` is the one printed.
- `x_guess`, `y_guess`, `z_guess`, `s_guess` — a deliberately wrong start: free nodes flat, 1 kN everywhere.

Example output:

```text
out of balance at the free nodes for the flat guess, z direction: [0.5   0.184 0.5   0.184 0.5  ]
```

## Part C. The force density trick: a linear system

### C.1 The force density, equations (4) to (6)

**Do this.** Add one number per branch: its force density. One line of code, and the nonlinear problem of Part B becomes linear.

#### EQUATION (4)

$$
q_j = \frac{s_j}{l_j}
\qquad\text{force per unit length}
$$

*Read it as: how hard the cable pulls, per metre of its own length.* Dimension: force / length (kN/m).

| Symbol | Say it as | Meaning | Unit |
|---|---|---|---|
| $s_j$ | "s sub j" | force in branch $j$ | kN |
| $l_j$ | "l sub j" | length of branch $j$ | m |
| $q_j$ | "q sub j" | **force density** | kN/m |
| $Q$ | "capital Q" | $\mathrm{diag}(q)$ | kN/m |

**One cable, by hand:**

```text
   L = 2.5 m ,  N = 10 kN        ->    q = 10 / 2.5 = 4 kN/m
```

#### WHY THE LENGTH CANCELS — THE WHOLE TRICK

The $x$ part of branch $j$'s pull is

$$
\text{Force}_{x,\,j} = s_j \cdot \frac{u_j}{l_j}
$$

*Read it as: the axial force times the fraction of the cable that points along $x$.*

```text
  branch 1 :  s_1 = 2.402 kN ,  u_1 = 1.200 m ,  l_1 = 1.201 m
              Force_x = 2.402 * 1.200 / 1.201 = 2.400 kN
```

Substitute $s_j = q_j\,l_j$:

$$
\text{Force}_{x,\,j} = (q_j\,l_j) \cdot \frac{u_j}{l_j} = q_j\,u_j = q_j\,(x_i - x_k)
$$

*Read it as: the $l_j$ on top cancels the $l_j$ underneath, leaving a plain multiple of the coordinates.*

**With our branch 1, after the solve of C.3:**

```text
   s_1 = 2.402 kN     u_1 = 1.200 m     l_1 = 1.201 m     q_1 = 2.0 kN/m

   the long way :  s_1 * u_1 / l_1  =  2.402 * 1.200 / 1.201  =  2.400 kN
   the short way:  q_1 * u_1        =  2.0   * 1.200          =  2.400 kN
                                                                 ^^^^^ same
```

The length cancels. The square root is gone. $q_j(x_i - x_k)$ is a plain multiple of the unknown coordinates — **linear**.

#### THE SWAP $U q = Q u$ (EQUATION 6)

$$
C^{t} U q \;=\; C^{t} Q u \;=\; p_x
$$

*Read it as: the known $q$ and the unknown $u$ can trade places, because both are only scaling entries one at a time.*

**REASON:** a diagonal matrix only scales entries one at a time, and $u_j q_j = q_j u_j$ is ordinary multiplication. So the two can trade places. After the swap the **known** numbers sit in $Q$ and the **unknown** geometry $u$ stands outside, ready to be solved for.

#### WITH OUR NUMBERS — INPUT

$$
q = \begin{pmatrix} 2 \\ 2 \\ 2 \\ 2 \\ 1 \\ \vdots \\ 1 \end{pmatrix}
\qquad\longrightarrow\qquad
Q = \mathrm{diag}(q) = \begin{pmatrix}
2 & 0 & 0 & & \\
0 & 2 & 0 & & \\
0 & 0 & 2 & & \\
 & & & \ddots & \\
 & & & & 1
\end{pmatrix}
$$

and as the printed arrays, with their shapes:

```text
  branch :    1    2    3    4  |   5    6    7    8    9   10   11   12
  q (12,) [  2.   2.   2.   2.  |  1.   1.   1.   1.   1.   1.   1.   1.  ]   = 12
             \______________/      \_____________________________________/
              anchor cables          ring (5-8) + spokes (9-12)
              2.0 kN/m               1.0 kN/m
```

```text
  Q = np.diag(q)    (12 x 12)
        b1 b2 b3 b4 b5 b6 b7 b8 b9 b10 b11 b12
  b1  [[ 2  0  0  0  0  0  0  0  0   0   0   0 ]
  b2   [ 0  2  0  0  0  0  0  0  0   0   0   0 ]
  b3   [ 0  0  2  0  0  0  0  0  0   0   0   0 ]
  b4   [ 0  0  0  2  0  0  0  0  0   0   0   0 ]
  b5   [ 0  0  0  0  1  0  0  0  0   0   0   0 ]
  b6   [ 0  0  0  0  0  1  0  0  0   0   0   0 ]
  b7   [ 0  0  0  0  0  0  1  0  0   0   0   0 ]
  b8   [ 0  0  0  0  0  0  0  1  0   0   0   0 ]
  b9   [ 0  0  0  0  0  0  0  0  1   0   0   0 ]
  b10  [ 0  0  0  0  0  0  0  0  0   1   0   0 ]
  b11  [ 0  0  0  0  0  0  0  0  0   0   1   0 ]
  b12  [ 0  0  0  0  0  0  0  0  0   0   0   1 ]]   = 12 rows
                                                       144 entries, only 12 non-zero
```

**$q$ is NOT a stiffness and NOT a cross-section.** Nothing here knows about steel. It is a ratio you choose; E.1 shows what choosing it actually controls.

**Add to your program:**

```python
q = np.array([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1], dtype=float)   # one force density per branch: the design input
```

#### LINE BY LINE

- `q = np.array([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1], dtype=float)` — one force density per branch, **in branch order**: entry `0` is branch 1 `(1, 6)`, entry `11` is branch 12 `(3, 5)`.

That is the whole cell.

> **Try it.** Raise $q$ on the four anchor cables from $2.0$ to $10.0$ kN/m. Does centre node 5 end up **higher** or **lower**? Write your answer down — D.2 runs it and prints the number.

### C.2 The matrices D and D_f, equations (7) and (8)

**Do this.** Build the two matrices that turn the net into a linear system, then the right-hand sides for the three axes.

#### EQUATIONS (7) AND (8)

Put $u = C x + C_f x_f$ from B.2 into $C^{t} Q u = p_x$ from C.1:

$$
C^{t} Q\,(C x + C_f x_f) = p_x
\qquad\Longrightarrow\qquad
\underbrace{(C^{t} Q C)}_{D}\,x + \underbrace{(C^{t} Q C_f)}_{D_f}\,x_f = p_x
$$

*Read it as: separate the terms that contain unknown free coordinates from the terms that contain known anchor coordinates.*

```text
  D    = C.T @ Q @ C      (5, 12)@(12, 12)@(12, 5)  ->  (5 x 5)   free   x free
  D_f  = C.T @ Q @ C_f    (5, 12)@(12, 12)@(12, 4)  ->  (5 x 4)   free   x anchor
```

$$
D x = p_x - D_f x_f, \qquad
D y = p_y - D_f y_f, \qquad
D z = p_z - D_f z_f
$$

*Read it as: a `(5, 5)` table times the five unknowns of one axis equals the load minus the anchor pull.*

**Three separate problems, one shared matrix.** $x$ never appears in the $z$ equation. $D$ is built once, used three times.

#### STAGES, RIGHT TO LEFT

| Step | Symbol | Say it as | What it does | Shape of the result |
|---|---|---|---|---|
| 1 | $C$ | "C" | spreads the free coordinates onto the 12 branches | `(12, 5)` |
| 2 | $Q C$ | "Q times that" | scales each branch by its own force density | `(12, 5)` |
| 3 | $C^{t} Q C$ | "C transposed times that" | sums back at the 5 free nodes | `(5, 5)` |

```text
   D   =   C.T    @    Q      @    C
           ---         ---         ---
            3           2           1
   SHAPES  (5, 12) @ (12, 12) @ (12, 5)  ->  (5, 5)
   D_f     (5, 12) @ (12, 12) @ (12, 4)  ->  (5, 4)
```

#### HOW TO READ EVERY ENTRY OF $D$

```text
  D[i, i]  (diagonal)     = SUM of q over ALL branches touching free node i+1
  D[i, k]  (off-diagonal) = -q_j  of the branch joining free nodes i+1 and k+1
                            0 if no branch joins them
```

#### TRACEABLE DEMO — give every branch a different $q$

Set $q_j = j$ (branch 1 gets 1, branch 2 gets 2, … branch 12 gets 12) so you can follow where each number lands. This is Schek's own figure 4.

```text
  q = [ 1.  2.  3.  4.  5.  6.  7.  8.  9. 10. 11. 12. ]

  node 1 touches branches  1,  5,  6, 10  ->  1 +  5 +  6 + 10  = 22
  node 2 touches branches  2,  6,  7, 11  ->  2 +  6 +  7 + 11  = 26
  node 3 touches branches  3,  7,  8, 12  ->  3 +  7 +  8 + 12  = 30
  node 4 touches branches  4,  5,  8,  9  ->  4 +  5 +  8 +  9  = 26
  node 5 touches branches  9, 10, 11, 12  ->  9 + 10 + 11 + 12  = 42

        D   (5 x 5)
          n1   n2   n3   n4   n5
  n1 [[  22.  -6.   0.  -5. -10. ]    22 on the diagonal, and -6 = -q_6 (branch 6 joins 1-2)
  n2  [  -6.  26.  -7.   0. -11. ]
  n3  [   0.  -7.  30.  -8. -12. ]    the 0: nodes 1 and 3 have no branch between them
  n4  [  -5.   0.  -8.  26.  -9. ]
  n5  [ -10. -11. -12.  -9.  42. ]]   = 5 rows
```

Every single number is traceable to a branch. **CHECK: $D$ is symmetric** — a branch joins node 1 to node 2 exactly as much as node 2 to node 1.

#### WITH OUR ACTUAL $q$ (2 on anchors, 1 elsewhere)

```text
        D   (5 x 5)                            D_f   (5 x 4)
          n1   n2   n3   n4   n5                 n6   n7   n8   n9
  n1 [[   5.  -1.   0.  -1.  -1. ]      n1 [[  -2.   0.   0.   0. ]
  n2  [  -1.   5.  -1.   0.  -1. ]      n2  [   0.  -2.   0.   0. ]
  n3  [   0.  -1.   5.  -1.  -1. ]      n3  [   0.   0.  -2.   0. ]
  n4  [  -1.   0.  -1.   5.  -1. ]      n4  [   0.   0.   0.  -2. ]
  n5  [  -1.  -1.  -1.  -1.   4. ]]     n5  [   0.   0.   0.   0. ]]
                                                 ^^^^^^^^^^^^^^^^
  node 1: 2+1+1+1 = 5                   the centre touches NO anchor
  node 5: 1+1+1+1 = 4                   -> its whole row is zero
```

#### THE RIGHT-HAND SIDE $b = p - D_f x_f$

**REASON:** the anchors cannot move, so their pull is a known number and belongs on the right with the loads.

```text
  vertical axis,  z_f = [0, 1, 0, 1] ,  p_z = -0.5 everywhere

  - D_f @ z_f  =  [ 2*0,  2*1,  2*0,  2*1,   0 ]  =  [  0.0   2.0   0.0   2.0   0.0 ]
  + p_z        =                                     [ -0.5  -0.5  -0.5  -0.5  -0.5 ]
                                                     -------------------------------
  b_z          =                                     [ -0.5   1.5  -0.5   1.5  -0.5 ]
```

Nodes 2 and 4 get $+1.5$ because they hang from the **lifted** anchors. Stacking the three axes:

```text
  rhs   (5 x 3)        x      y      z
  node 1  [         -4.0    0.0   -0.5 ]
  node 2  [          0.0    4.0    1.5 ]
  node 3  [          4.0    0.0   -0.5 ]
  node 4  [          0.0   -4.0    1.5 ]
  node 5  [          0.0    0.0   -0.5 ]   <- centre: load only, no anchor term
                                              = 5 rows
```

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

#### LINE BY LINE

- `Q = np.diag(q)` — the 12 force densities on a `(12, 12)` diagonal.
- `D = C.T @ Q @ C` — equation (8), the three stages above. `(5,12) @ (12,12) @ (12,5)` → `(5, 5)`.
- `D_f = C.T @ Q @ C_f` — same sandwich with the anchor columns → `(5, 4)`.
- `rhs = np.c_[...]` — `np.c_` glues three length-5 columns side by side into one `(5, 3)` table, one column per axis.

**CHECK IT YOURSELF:** node 5's row of `D` must be `[-1, -1, -1, -1, 4]` — four spokes of $q = 1$ pulling it, no anchor term anywhere.

> **Try it.** Change only `p_z` and rerun: `D` and `D_f` print **unchanged**, only `rhs` moves. Change one entry of `q`: `D` changes too. That is the difference between the two loops of D.1.

Example output:

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

### C.3 Solving for the free coordinates, equation (9)

**Do this.** Solve the three linear systems. The shape of the net appears here — one direct step, no iteration, no initial guess.

#### EQUATION (9)

$$
D x = p_x - D_f x_f, \qquad
D y = p_y - D_f y_f, \qquad
D z = p_z - D_f z_f
$$

*Read it as: three separate problems that happen to share one matrix.*

Everything on the right is already a number. Solve three times, once per axis.

#### WITH OUR NUMBERS — the vertical system in full

$$
\begin{pmatrix}
5 & -1 & 0 & -1 & -1 \\
-1 & 5 & -1 & 0 & -1 \\
0 & -1 & 5 & -1 & -1 \\
-1 & 0 & -1 & 5 & -1 \\
-1 & -1 & -1 & -1 & 4
\end{pmatrix}
\begin{pmatrix} z_1 \\ z_2 \\ z_3 \\ z_4 \\ z_5 \end{pmatrix}
=
\begin{pmatrix} -0.5 \\ 1.5 \\ -0.5 \\ 1.5 \\ -0.5 \end{pmatrix}
$$

and as the printed arrays, with their shapes:

```text
        D   (5 x 5)                   z (5)        b_z (5)
         n1   n2   n3   n4   n5       unknown       known
  n1 [[   5.  -1.   0.  -1.  -1. ]     [ z1 ]       [ -0.5 ]
  n2  [  -1.   5.  -1.   0.  -1. ]     [ z2 ]       [  1.5 ]
  n3  [   0.  -1.   5.  -1.  -1. ]  @  [ z3 ]   =   [ -0.5 ]
  n4  [  -1.   0.  -1.   5.  -1. ]     [ z4 ]       [  1.5 ]
  n5  [  -1.  -1.  -1.  -1.   4. ]]    [ z5 ]       [ -0.5 ]

  np.linalg.solve(D, b_z)  ->

      z = [ 0.045   0.330   0.045   0.330   0.063 ]      = 5
```

All three axes, read **down the columns**:

```text
  free node coordinates   (5 x 3)
                x        y        z
  node 1  [  -0.800    0.000    0.045 ]
  node 2  [   0.000    0.800    0.330 ]   <- pulled up by lifted anchor 7
  node 3  [   0.800    0.000    0.045 ]
  node 4  [   0.000   -0.800    0.330 ]   <- pulled up by lifted anchor 9
  node 5  [   0.000    0.000    0.063 ]   <- centre, a saddle point
                                             = 5 rows
```

Compare with the flat guess of B.3, out of balance by up to 0.5 kN at every node. These coordinates balance to machine precision — C.4 proves it.

#### WHY A SOLUTION EXISTS

With all $q_j > 0$ and the net properly anchored, $D$ is **symmetric positive definite**:

| | means |
|---|---|
| symmetric | $D$ equals its own transpose — visible in the matrix above |
| positive definite | **exactly one** solution exists. No ambiguity, no failure |

"Properly anchored" = every group of free nodes can reach an anchor through branches with $q > 0$. If part of the net floats free, $D$ is singular and the solve returns `nan`. That is the method telling you the structure is a mechanism.

#### SOLVE, DO NOT INVERT

`np.linalg.solve(D, b)` finds $x$ **without ever computing $D^{-1}$**. Writing $x = D^{-1}b$ is correct mathematics and poor numerics — more work, less accuracy.

**Add to your program:**

```python
x: FloatVector = np.linalg.solve(D, p_x - D_f @ x_f)            # eq. (9)
y: FloatVector = np.linalg.solve(D, p_y - D_f @ y_f)
z: FloatVector = np.linalg.solve(D, p_z - D_f @ z_f)
```

#### LINE BY LINE

- `x = np.linalg.solve(D, p_x - D_f @ x_f)` — builds the right-hand side for the $x$ axis and solves. Returns `(5,)`: the $x$ of each free node.
- `y = ...`, `z = ...` — same two lines with the $y$ and $z$ data. **`D` is identical in all three calls**; only the right-hand side changes.

The whole 3-D equilibrium geometry came out of three ordinary linear solves. No starting shape, no tolerance, no risk of the wrong answer. That is the payoff for prescribing $q$ instead of $s$.

> **Try it.** Add 1 m to every anchor height (`z_f + 1.0`) and resolve. Every free node rises by exactly 1 m, shape unchanged — the right-hand side moved, the matrix did not.

### C.4 Lengths, forces and the equilibrium check, equation (10)

**Do this.** Measure the solved net, recover the force in each cable, then go back to Part B's nonlinear equation and check it.

#### EQUATION (10)

$$
s_j = q_j \, l_j
$$

*Read it as: force density times length gives the force back.*

Just $q_j = s_j / l_j$ rearranged. Once the geometry is known, $l_j$ is known, so the force follows with no second solve.

#### WITH OUR NUMBERS

```text
  branch      group          q (kN/m)   l (m)     s = q*l (kN)
  ---------------------------------------------------------------
    1 (1,6)   anchor cable     2.0      1.201        2.402
    2 (2,7)   anchor cable     2.0      1.374        2.748
    3 (3,8)   anchor cable     2.0      1.201        2.402
    4 (4,9)   anchor cable     2.0      1.374        2.748
    5 (1,4)   ring             1.0      1.167        1.167
    6 (1,2)   ring             1.0      1.167        1.167
    7 (2,3)   ring             1.0      1.167        1.167
    8 (3,4)   ring             1.0      1.167        1.167
    9 (4,5)   spoke            1.0      0.844        0.844
   10 (1,5)   spoke            1.0      0.800        0.800
   11 (2,5)   spoke            1.0      0.844        0.844
   12 (3,5)   spoke            1.0      0.800        0.800
                                                       = 12
```

Branch 2: $2.0 \times 1.374 = 2.748$ kN. **Where $q$ is equal, the longer cable carries the larger force** — the opposite of a spring. Worth a pause.

#### THE CHECK

Run B.3's untouched nonlinear equation (2) on this answer:

$$
e = C^{t} U L^{-1} s - p \;\approx\; 0
$$

*Read it as: collected cable pulls minus applied load, at every node, must be zero.*

```text
  max |e|  =  1.11e-15  kN
```

Machine zero. **The linear solve of C.3 satisfies the NONLINEAR equilibrium of B.3 exactly.** That is Schek's central claim, checked rather than assumed. (The last digits depend on your machine; anything near $10^{-15}$ means the same.)

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

#### LINE BY LINE

- `u, v, w, l = coordinate_differences(...)` — the B.2 function, now on the **solved** coordinates instead of a guess.
- `s = l * q` — equation (10). `*` is entry by entry, **not** a matrix product.
- `xyz_free = np.c_[x, y, z]` — glues the three `(5,)` answers into one `(5, 3)` table, one row per node.
- `max(np.abs(e).max() for e in equilibrium_error(x, y, z, s))` — B.3's four-stage check on the result, worst node in any direction.

> **Try it.**
> - `p_z = np.full(n, -2.0)` — net sags deeper, forces grow. $D$ untouched, only `rhs` changes.
> - `z_f += 1.0` — whole net rises 1 m, identical shape. Again only `rhs`.
> - `q[:4] = 10.0` — now $D$ itself is rebuilt and the shape genuinely changes.

Example output:

```text
free node coordinates (columns x, y, z):
[[-0.8   -0.     0.045]
 [-0.     0.8    0.33 ]
 [ 0.8   -0.     0.045]
 [-0.    -0.8    0.33 ]
 [ 0.    -0.     0.063]]
lengths l: [1.201 1.374 1.201 1.374 1.167 1.167 1.167 1.167 0.844 0.8   0.844 0.8  ]
forces  s: [2.402 2.748 2.402 2.748 1.167 1.167 1.167 1.167 0.844 0.8   0.844 0.8  ]
equilibrium error (2) on the solution: 1.1102230246251565e-15
```

## Part D. The form-finding loop

### D.1 The form-finding loop as one function (figure 3)

**Do this.** Put everything from A.3 to C.4 into one function that builds its own connectivity from its arguments, so it works on any network.

![Fig. 3](images/schek_fig3.png)

*Fig. 3, redrawn: the diagram of the form finding.*

#### THE COST OF EACH DESIGN CHANGE

| Change… | Rebuild | Cost |
|---|---|---|
| loads $p$ | right-hand side only | cheapest |
| anchor positions $x_f, y_f, z_f$ | right-hand side only | cheapest |
| force densities $q$ | $D$, $D_f$, right-hand side | medium |
| connectivity | $C_s$ and everything after | everything |

#### SIX STEPS INSIDE THE FUNCTION

| # | does | equation | shapes |
|---|---|---|---|
| 1 | build $C_s$, split into $C$, $C_f$ | §2.1 | `(12,9)` → `(12,5)`, `(12,4)` |
| 2 | build $D$, $D_f$ | (8) | `(5,5)`, `(5,4)` |
| 3 | solve the three axes | (9) | `(5,3)` |
| 4 | measure branch vectors and lengths | (1) | `(12,3)`, `(12,)` |
| 5 | forces $s = q\,l$ | (10) | `(12,)` |
| 6 | sum pulls at the anchors = reactions | (5) | `(4,3)` |

#### IN AND OUT

```text
  IN   branches    list of m tuples   (start, end), counting from 1
       n_free      int                free nodes, numbered first
       xyz_fixed   (n_f, 3)           anchor coordinates
       q           (m,)               one force density per branch
       p           (n_free, 3)        one load vector per free node

  OUT  xyz         (n_free, 3)        equilibrium coordinates
       l           (m,)               branch lengths
       s           (m,)               branch forces, q*l
       reactions   (n_f, 3)           force the cables apply to each support
```

#### ONE CHANGE: THREE AXES AT ONCE

Earlier $x$, $y$, $z$ were three `(5,)` arrays. Here they are one `(5, 3)` table, because a matrix times a 3-column table is three matrix-vector products side by side:

```text
  C @ xyz      (12, 5) @ (5, 3)  ->  (12, 3)
                  column 0 is the old  C @ x
                  column 1 is the old  C @ y
                  column 2 is the old  C @ z
```

Nothing new happens. The same arithmetic is written once instead of three times.

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

#### LINE BY LINE

- First four lines — A.3 with `branches` as an argument.
- `D, D_f = C.T @ np.diag(q) @ C, C.T @ np.diag(q) @ C_f` — equation (8), both on one line.
- `np.vstack([np.linalg.solve(D, p[:, a] - D_f @ xyz_fixed[:, a]) for a in range(3)]).T` — the busiest line, taken apart:
  - `for a in range(3)` runs three times, `a = 0, 1, 2` meaning $x$, $y$, $z$;
  - `p[:, a]` is that axis's loads, `xyz_fixed[:, a]` that axis's anchors;
  - `np.linalg.solve(...)` is equation (9) for that axis → `(5,)`;
  - `np.vstack([...])` stacks the three answers as **rows** → `(3, 5)`;
  - `.T` flips to `(5, 3)`: one row per free node.
- `uvw = C @ xyz + C_f @ xyz_fixed` — equation (1) for all three axes → `(12, 3)`.
- `l = np.linalg.norm(uvw, axis=1)` — length of each **row**. `axis=1` = "across the columns, one answer per row".
- `s = l * q` — equation (10).
- `reactions = C_f.T @ np.diag(q) @ uvw` — the same sandwich as $D$ but summing at the **fixed** nodes.

**CHECK:** `reactions.sum(axis=0) + p.sum(axis=0)` is zero at equilibrium — total pull up equals total load down.

### D.2 Using the loop: move the anchors, change the force densities

**Do this.** Call the function with the original data, then change one input at a time. After this cell you own a reusable linear force density solver.

#### THREE RUNS

| run | changed | rebuilt | expect |
|---|---|---|---|
| 1 | nothing | — | reproduces C.3 |
| 2 | every anchor lifted 1 m | right-hand side only | net rises 1 m, same shape |
| 3 | $q = 10$ on branches 1–4 | $D$ and $D_f$ | shape itself changes |

#### WITH OUR NUMBERS

```text
  centre node height z5

  base case                    0.063 m
  all anchors lifted 1 m       1.063 m    <- exactly 1.000 m higher
  anchor cables q = 10         0.313 m    <- genuinely different shape
```

Run 2 is the one to stare at: the net moved up by precisely what the anchors moved and kept its shape exactly. $D$ never saw the change.

Run 3 answers the prediction from C.1 — stiffer anchor cables pull the corners out and **up**, lifting the centre from 0.063 to 0.313 m. **A larger $q$ is not a larger force, it is a larger force per metre**, so the cable settles shorter and straighter.

#### THE REACTIONS — AND THE GLOBAL CHECK

```text
  anchor:        6        7        8        9        sum
  R_z  (4,)  [ -0.089    1.339   -0.089    1.339 ]   2.500 kN
                          ^^^^^            ^^^^^
                          the two LIFTED anchors carry nearly everything

  CHECK   sum of reactions  2.500 kN  =  total load  5 x 0.5 = 2.500 kN
```

The two ground-level anchors are pulled slightly **down**. If that sum does not balance the load, something upstream is wrong — it is the cheapest check there is.

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

#### LINE BY LINE

- `xyz_fixed = np.c_[x_f, y_f, z_f]`, `p = np.c_[p_x, p_y, p_z]` — repackage B.1's separate axis arrays into the `(4,3)` and `(5,3)` tables the function wants.
- `xyz_fixed + np.array([0, 0, 1.0])` — NumPy **broadcasting**: the 3-vector is added to every row, lifting all four anchors 1 m with no loop.
- `np.where(np.arange(m) < 4, 10.0, 1.0)` — a fresh `q`: `10.0` where the branch index is under 4, `1.0` elsewhere. The original `q` is untouched.
- `R1[:, 2]` — column 2 of the reactions: the vertical component at each anchor.

#### MILESTONE

**You have implemented the linear force density method.** Everything up to here is the complete, usable tool. E explains what $q$ means; F adds wishes about lengths and forces. Neither is needed to use what you just built.

Example output:

```text
same solution from the function: True
reactions at the anchors (sum of z components balances the total load): [-0.089  1.339 -0.089  1.339] 2.5
centre node height: base 0.063 | anchors lifted by 1 m 1.063 | anchor branches q = 10: 0.313
```

## Part E. What the force densities mean

### E.1 What the force densities mean geometrically (section 4)

**Do this.** Run the solver with **zero load** and test two statements about what $q$ actually controls.

#### THE QUESTION

C.1 introduced $q$ as a convenient ratio. That is an excuse, not an explanation. **When I choose $q$, what am I choosing geometrically?**

#### EQUATION (40)

Forget forces. Which node positions make this as small as possible?

$$
u^{t} P u + v^{t} P v + w^{t} P w \;\longrightarrow\; \min
$$

*Read it as: make the weighted sum of squared branch lengths as small as possible.*

```text
  u^t P u  =  sum over branches of  P_j * u_j^2        -> ONE number
  all three terms together  =  sum of  P_j * l_j^2     -> the WEIGHTED SUM
                                                          OF SQUARED LENGTHS
```

Set the derivative to zero, with $\partial u/\partial x = C$:

$$
(C^{t} P C)\, x = -(C^{t} P C_f)\, x_f
$$

*Read it as: the minimiser satisfies exactly the equilibrium equation of C.2, with the weights $P$ playing the part of the force densities $Q$.*

That is **exactly equation (8)** with $P$ in place of $Q$ and no load.

#### THEOREM 1

> An unloaded net with force densities $q$ is **the net whose sum of squared branch lengths, weighted by $q$, is smallest.**

So $q_j$ is a **weight in a length competition.** Big $q$ = "make this one short". Small $q$ = "this one may be long".

#### THEOREM 2

> $q_j = c / l_j$ makes every force equal: $s_j = q_j l_j = c$.

So a **minimum way net** (smallest total length) is the same thing as a net with the same force everywhere.

#### WITH OUR NUMBERS — load removed

```text
  unloaded equilibrium   (5 x 3)
                x        y        z
  node 1  [  -0.800    0.000    0.357 ]
  node 2  [   0.000    0.800    0.643 ]
  node 3  [   0.800    0.000    0.357 ]
  node 4  [   0.000   -0.800    0.643 ]
  node 5  [   0.000    0.000    0.500 ]   <- exactly midway: no load, perfect symmetry

  l0  (12,)
  [ 1.252 1.252 1.252 1.252 | 1.167 1.167 1.167 1.167 | 0.813 0.813 0.813 0.813 ]  = 12
       anchor cables              ring                      spokes
```

**TEST THEOREM 1** — the weighted sum at this shape:

```text
  anchors  4 x ( 2 * 1.252^2 )  =  12.540
  ring     4 x ( 1 * 1.167^2 )  =   5.447
  spokes   4 x ( 1 * 0.813^2 )  =   2.644
                                   -------
  sum q_j * l_j^2               =  20.629

  if this is the MINIMUM, the gradient must vanish:
  largest entry of the gradient  =  2.22e-15     <- zero to machine precision
```

Move any free node in any direction and 20.629 can only grow.

**TEST THEOREM 2** — set $q_j = 1/l_j$ and compute $s_j = q_j l_j$:

```text
  s  (12,)   [ 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. ]   = 12
```

Twelve ones. Same force in every cable, whatever its length.

#### THE DESIGN TABLE

| You want a branch… | Choose |
|---|---|
| **short and taut** | **large** $q$ |
| **long and slack** | **small** $q$ |
| **equal force everywhere** | $q_j = c / l_j$, iterated (Part F) |

**REASON the paper uses $q = 100$ on the border and $q = 1$ in the field:** the border is told to stay short and straight while the field is free to drape.

**Add to your program:**

```python
xyz0, l0, s0, _ = form_finding(branches, n, xyz_fixed, q, np.zeros((n, 3)))      # no load
uvw0 = C @ xyz0 + C_f @ xyz_fixed
gradient = 2 * C.T @ np.diag(q) @ uvw0                                              # d/dx of u^t Q u, per axis
print("Theorem 1: gradient of the weighted squared lengths at the unloaded equilibrium:", np.abs(gradient).max())
q_const = 1.0 / l0                                                               # Theorem 2
print("Theorem 2: forces with q = 1 / l:", l0 * q_const)
```

#### LINE BY LINE

- `form_finding(..., np.zeros((n, 3)))` — the D.1 solver with a `(5, 3)` block of zeros as the load: the unloaded, purely prestressed net.
- `uvw0 = C @ xyz0 + C_f @ xyz_fixed` — equation (1) on that solution.
- `gradient = 2 * C.T @ np.diag(q) @ uvw0` — the derivative of $u^{t}Qu$ with respect to the free coordinates (the paper's (37), (38)), one column per axis. Printing its largest entry tests Theorem 1.
- `q_const = 1.0 / l0` — Theorem 2's prescription. `l0 * q_const` gives the forces: twelve exact ones.

**$q$ is the weight you put on a cable in a competition to be short.**

Example output:

```text
Theorem 1: gradient of the weighted squared lengths at the unloaded equilibrium: 2.220446049250313e-15
Theorem 2: forces with q = 1 / l: [1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1.]
```

## Part F. Additional conditions

### F.1 Asking for more than equilibrium (section 3.1)

**Do this.** Pick four branches, say how long you want them, and subtract. The result is a short list of **what is still wrong**.

#### THE PROBLEM

The linear method of Parts A–D gives equilibrium and **nothing else**. It will happily hand you anchor cables of 1.201 m and 1.374 m when the fabricator needs all four at 1.200 m.

#### THE IDEA IN ONE SENTENCE

For a given $q$, the linear solve gives a shape; the shape gives lengths and forces. So **everything you care about is a function of $q$ alone.** Change $q$ until the wishes come true.

#### EQUATION (11)

$$
g^{\ast}(q) = 0
$$

*Read it as: every wish, written as an error that must become zero, is ultimately a function of $q$ alone.*

| Symbol | Say it as | One entry means | Shape |
|---|---|---|---|
| $g^{\ast}$ | "g star" | the **error** in each wish; zero when granted | `(4,)` |
| $q$ | "q" | the twelve force densities — what we are free to change | `(12,)` |

#### WITH OUR NUMBERS

Ask the four anchor cables to be exactly 1.2 m. After the linear solve of Part C they are not:

```text
  wish   branch     have (m)    want (m)    g = have - want
  ------------------------------------------------------------
   1       1         1.20083      1.200        +0.00083
   2       2         1.37420      1.200        +0.17420     <- 17 cm too long
   3       3         1.20083      1.200        +0.00083
   4       4         1.37420      1.200        +0.17420     <- 17 cm too long

  g  (4,)   [ 0.00083   0.17420   0.00083   0.17420 ]   = 4
```

Four numbers, and all four must become zero. Branches 1 and 3 are nearly right; branches 2 and 4 — the ones hanging from the **lifted** anchors — are badly off.

#### 4 WISHES, 12 KNOBS

```text
  4 equations,  12 unknowns  ->  MANY different q grant the same wishes.
```

There is no single answer. F.2 lets SciPy pick one.

**Add to your program:**

```python
length_rows = [0, 1, 2, 3]                        # the four anchor branches
target_lengths = np.full(4, 1.2)                  # we want all four to be 1.2 m
g_lengths = l[length_rows] - target_lengths       # what is still wrong, one number per wish

print("wanted 1.2 m, got:", l[length_rows])
print("still wrong by:   ", g_lengths)
```

#### LINE BY LINE

- `length_rows = [0, 1, 2, 3]` — **array indices** of the constrained branches, so branches 1–4 in Schek's numbering.
- `target_lengths = np.full(4, 1.2)` — four copies of 1.2 m.
- `l[length_rows]` — picks just those four lengths out of the twelve (NumPy "fancy indexing").
- the subtraction gives the error vector, one entry per wish.

Example output:

```text
wanted 1.2 m, got: [1.201 1.374 1.201 1.374]
still wrong by:    [0.001 0.174 0.001 0.174]
```

### F.2 Letting SciPy find the force densities (sections 3.1 to 3.6)

**Do this.** Hand the wish-error function to SciPy and let it search for the $q$ that zeroes it. The whole constrained solver is **one call**.

#### THE SHAPE OF THE LOOP

```text
   guess q  ->  form_finding(q)  ->  lengths and forces  ->  how wrong?
       ^                                                          |
       +---------------- SciPy changes q --------------------------+
```

`least_squares` runs this loop for you. It needs only the function that says **how wrong** the current $q$ is — that is F.1's $g$.

#### THE TWO ARGUMENTS THAT MATTER

| argument | does | replaces |
|---|---|---|
| `still_wrong` | returns one number per wish | Schek's condition vector $g^{\ast}$ |
| `bounds=(1e-9, np.inf)` | keeps every $q_j$ positive — **a cable stays a cable** | Schek's sign guard |

SciPy's trust region does the rest: it takes a cautious step, checks whether things improved, and shortens the step if not. That is the same safeguard as Schek's damping, built in.

#### WITH OUR NUMBERS — WISH 1: four cables of 1.2 m

```text
  START    q   [ 2.000   2.000   2.000   2.000 ]
           l   [ 1.201   1.374   1.201   1.374 ]      g = [0.001, 0.174, 0.001, 0.174]

  AFTER 12 TRIES
           q   [ 1.972   2.412   1.972   2.412 ]
           l   [ 1.200   1.200   1.200   1.200 ]      worst error  1.8e-08 m
```

Read what it decided: branches 2 and 4 were **too long**, so their $q$ went **up** (2.000 → 2.412) to pull them in — Theorem 1 of E.1 at work. Branches 1 and 3 drifted slightly down as the net rebalanced.

**$q$ is no longer an input here. It is the answer.**

#### WISH 2: lengths AND forces at the same time

Four spokes of 0.9 m **and** four anchor cables carrying exactly 2 kN:

```text
  g  (8,)  =  [ l_9 -0.9,  l_10-0.9,  l_11-0.9,  l_12-0.9,     <- length wishes
                s_1 -2.0,  s_2 -2.0,  s_3 -2.0,  s_4 -2.0 ]    <- force wishes

  AFTER 22 TRIES
      spoke lengths  [ 0.900  0.900  0.900  0.900 ] m
      anchor forces  [ 2.000  2.000  2.000  2.000 ] kN      worst error  7.5e-11
```

Eight wishes of two different kinds, granted together. **Mixing costs nothing** — the two kinds are simply stacked into one list by `np.r_[...]`.

#### WHY SCIPY AND NOT THE 1974 METHOD

Schek derived the derivatives by hand and built a damped step, because in 1974 that was the only way. `least_squares` does the same job with a modern trust region. His literal scheme — equations (17) to (25) and the analytic Jacobians (31), (34), (35) — is implemented and checked in `examples/form_finding/schek_equations.py`.

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

#### LINE BY LINE

- `from scipy.optimize import least_squares` — the search routine.
- `def still_wrong(q):` — the heart of it. **Given a trial $q$, run the full linear solve of D.1, then report how far every wish is from granted.** All zeros means done.
- `np.r_[l[length_rows] - l_v, s[force_rows] - s_v]` — `np.r_` glues the length errors and the force errors into one list, so mixed wishes need no special handling.
- `least_squares(still_wrong, q_start, bounds=(1e-9, np.inf))` — searches for the $q$ that makes that list zero, never letting any $q_j$ reach zero.
- `found.x` — the $q$ it settled on. `found.nfev` — how many trial $q$ it tried. `found.fun` — the final errors.
- The last `form_finding` call re-runs the solver once on the winning $q$ to return the shape, lengths, forces and reactions.

**ALWAYS READ THE RETURNED ERROR.** A shape comes back whether or not the wishes were granted. Only the error number tells you which happened.

Example output:

```text
anchor branches asked for 1.2 m -> [1.2 1.2 1.2 1.2] after 12 tries, worst error 1.8e-08
the q that does it: [1.972 2.412 1.972 2.412]  (we started from [2. 2. 2. 2.])
mixed wishes -> spokes [0.9 0.9 0.9 0.9] m, anchor forces [2. 2. 2. 2.] kN, worst error 7.5e-11
```

### F.3 What the solver feels its way with: the Jacobian (sections 3.2 to 3.4)

**Do this.** Look at what the solver is feeling its way with: a table of **sensitivities**. One row per wish, one column per knob.

#### THE QUESTION SCIPY ASKS

> If I nudge $q_j$ up a little, how much does length $i$ change?

Answer that for every (wish, branch) pair and you have the **Jacobian**, written $G^{t}$ in the paper.

$$
G^{t} := \frac{\partial g^{\ast}}{\partial q}
\qquad
\text{row } i, \text{ column } j: \;\; \frac{\partial\,(\text{wish } i)}{\partial\,q_j}
$$

*Read it as: a table of sensitivities — one row per wish, one column per knob.*

**A Jacobian is nothing more exotic than a table of sensitivities.**

#### HOW TO GET IT WITHOUT CALCULUS

```text
   1  measure the four lengths at the current q           -> base
   2  for each branch j:
         nudge q_j up by 0.000001
         measure the four lengths again
         (new - base) / 0.000001   ->  column j
```

That is all `sensitivity()` does. SciPy does exactly this internally.

#### WITH OUR NUMBERS — $G^{t}$ (4 wishes × 12 branches)

```text
          b1      b2      b3      b4      b5      b6      b7      b8      b9     b10     b11     b12
 w1 [[ -0.313   0.002   0.073   0.002   0.139   0.139   0.023   0.023   0.000   0.109   0.000   0.051 ]
 w2  [  0.002  -0.358   0.002   0.044   0.016   0.144   0.144   0.016   0.037   0.000   0.113   0.000 ]
 w3  [  0.073   0.002  -0.313   0.002   0.023   0.023   0.139   0.139   0.000   0.051   0.000   0.109 ]
 w4  [  0.002   0.044   0.002  -0.358   0.144   0.016   0.016   0.144   0.113   0.000   0.037   0.000 ]]
                                                                                              = 4 rows
```

**THREE THINGS TO READ OFF IT**

```text
  1  DIAGONAL is big and NEGATIVE  (-0.313, -0.358)
     raise q_1 by one unit -> branch 1 gets about 0.31 m SHORTER.
     negative = shorter = Theorem 1 of E.1, as a number.

  2  OFF-DIAGONAL is small and mostly POSITIVE
     tightening one cable lets the others lengthen slightly. Weak coupling.

  3  SOME ENTRIES ARE EXACTLY 0.000   (wish 1, branch 9)
     branch 9 joins nodes 4 and 5. By symmetry, changing its q does not
     change the length of branch 1 at all.
```

#### WHAT SCHEK DID INSTEAD

He derived this table by hand. Differentiating the equilibrium implicitly gives equation (28),

$$
\frac{\partial x}{\partial q} = -D^{-1} C^{t} U
$$

*Read it as: how far every free node moves when one force density is nudged.*

One such table, for the **heights**, with our numbers (first four columns):

```text
  dz/dq   (5 nodes x 12 branches)
                dq1      dq2      dq3      dq4
  node 1  [  -0.012    0.060   -0.003    0.060  ... ]
  node 2  [  -0.004    0.175   -0.004    0.041  ... ]
  node 3  [  -0.003    0.060   -0.012    0.060  ... ]
  node 4  [  -0.004    0.041   -0.004    0.175  ... ]
  node 5  [  -0.006    0.084   -0.006    0.084  ... ]
                                                      = 5 rows

  READ ONE ENTRY:  row "node 2", column dq2 is +0.175
     -> raise the force density of branch 2 by 1 kN/m
        and node 2 rises by about 0.175 m.
     It is the biggest number in that column, and branch 2 is the
     cable node 2 hangs from. The table knows the geometry.

  SIGNS:  column dq1 is all NEGATIVE  (branch 1 runs DOWN to anchor 6)
          column dq2 is all POSITIVE  (branch 2 runs UP to lifted anchor 7)
```

and the chain rule turns that into the length Jacobian (31), the force Jacobian (34) and the unstrained-length Jacobian (35). **Those analytic formulas agree with the nudging table above to 3 decimals** — checked in `schek_equations.py`. You do not need them to use the method; you need them to understand why it is fast.

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

#### LINE BY LINE

- `base = form_finding(...)[1][rows]` — the lengths of the watched branches at the current `q`. The `[1]` picks the second return value, `l`.
- `G_t = np.zeros((len(rows), len(q)))` — the empty `(4, 12)` table.
- `q_nudged = q.copy(); q_nudged[j] += step` — change **one** force density by 0.000001. `.copy()` matters: without it you would damage the original `q`.
- `(... - base) / step` — change in length divided by change in `q`. That is the definition of a derivative, done with numbers.
- `G_t[:, j] = ...` — write it into **column** `j`.

**COST:** one extra solve per branch. For 12 branches that is nothing; for the 112-bar net of G.5 it is still only 112 small solves per step.

Example output:

```text
sensitivity of the four anchor lengths to all twelve q (shape (4, 12)):
[[-0.313  0.002  0.073  0.002  0.139  0.139  0.023  0.023  0.     0.109  0.     0.051]
 [ 0.002 -0.358  0.002  0.044  0.016  0.144  0.144  0.016  0.037  0.     0.113  0.   ]
 [ 0.073  0.002 -0.313  0.002  0.023  0.023  0.139  0.139  0.     0.051  0.     0.109]
 [ 0.002  0.044  0.002 -0.358  0.144  0.016  0.016  0.144  0.113  0.     0.037  0.   ]]
```

## Part G. The paper's examples, computed and drawn

### G.1 The network of figure 5 (section 5)

**Do this.** Build the paper's bigger network as data, same free-nodes-first rule. **The solver does not change at all.**

![Fig. 5](images/schek_fig5.png)

*Fig. 5, redrawn: the graph of the first example.*

#### EVERYTHING GETS BIGGER — THE SOLVER DOES NOT

| | fig. 2 net (A–F) | fig. 5 net | solver changed? |
|---|---|---|---|
| nodes $n_s$ | 9 | **67** | no |
| free $n$ | 5 | **61** | no |
| fixed $n_f$ | 4 | **6** | no |
| branches $m$ | 12 | **110** | no |
| $C_s$ | `(12, 9)` | `(110, 67)` | no |
| $Q$ | `(12, 12)` | `(110, 110)` | no |
| **$D$** | `(5, 5)` | **`(61, 61)`** | no |
| lines of solver code | — | — | **zero** |

#### THE FORCE DENSITIES THE PAPER PRESCRIBES — INPUT

| group | count | $q$ | what it tells the shape |
|---|---|---|---|
| border | 29 | **100** | "stay short and straight" |
| radial to apex | 10 | **0.5** | "you may be long" |
| everything else | 71 | **1** | the ordinary field |

A factor of 200 between border and radials is what makes the tent shape. This is E.1 applied at full scale.

#### GIVEN vs RECONSTRUCTED

```text
  GIVEN by the paper   : topology, the three q values, "a small vertical load"
  CHOSEN here          : 0.04 m per pixel of the scan
                         apex 16 m above the corners
                         load 0.4 kN down at every free node
```

Treat the figures below as faithful **reconstructions**, not reproduced measurements.

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

#### LINE BY LINE

- `FIG5_PX` — plan position of each of the 67 nodes read off the printed figure, in pixels. `* np.array([0.04, -0.04])` scales to metres and flips $y$ (image rows count down); `xy -= xy[66]` moves the apex (node 67, index 66) to the origin.
- `ring(nodes)` — turns a node list into the closed chain of branches between consecutive ones. The `seen` loop collects each branch once, giving 110.
- `q5` — `100` to border branches, `0.5` to any branch containing node 67, `1.0` to the rest: the paper's prescription as one list comprehension.
- `p5` — the `(61, 3)` load table, `-0.4` in every $z$. `anchors5(...)` — the `(6, 3)` anchor table.
- `is_spoke`, `is_border`, `touches_border` — **boolean masks** over the 110 branches, arrays of `True`/`False`. `l[is_spoke]` picks out the ten radial lengths.
- `keep(name, ...)` — stores a finished shape for the figure renderer, stacking 61 free + 6 fixed rows into one `(67, 3)` table.

### G.2 Figure 6: different fixed points

**Do this.** Run the same solver with three support layouts. Only $x_f, y_f, z_f$ change, so **only the right-hand side is rebuilt** — D.2's cheap loop, now on a 61-node system.

![Fig. 1](images/schek_fig1.png)

*Fig. 1, recomputed: two views of the prestressed net of this example.*

![Fig. 6](images/schek_fig6_persp.png)
![Fig. 6, plan](images/schek_fig6_plan.png)

*Fig. 6, recomputed: the apex at the position of fig. 5, then moved by (6, 2) m and (12, 4) m.*

#### WHAT TO WATCH

| run | apex moved | radial lengths | apex reaction |
|---|---|---|---|
| fig6_1 | (0, 0) m | 8.1 – 9.0 m | 38.9 kN |
| fig6_2 | (6, 2) m | 8.0 – 9.3 m | 38.9 kN |
| fig6_3 | (12, 4) m | 8.4 – 10.9 m | 38.9 kN |

The radial lengths spread wider as the apex slides off centre — cables on the far side must stretch to reach it. But the **apex reaction stays at 38.9 kN in all three**. Dragging the high point sideways redistributes geometry without changing how much total force the apex carries, because $q$ and the loads were never touched.

**Add to your program:**

```python
# figure 6: different fixed points (the apex moved in plan): only the right-hand sides change
for name, (dx, dy) in zip(["fig6_1", "fig6_2", "fig6_3"], [(0, 0), (6, 2), (12, 4)]):
    xyz, l, s_, R = form_finding(branches5, free5, anchors5(dx, dy), q5, p5)
    keep(name, branches5, xyz, anchors5(dx, dy), fixed5)
    print(f"{name}: apex moved by ({dx}, {dy}) m; radial lengths {l[is_spoke].min():.1f}-{l[is_spoke].max():.1f} m; apex reaction {R[5, 2]:.1f} kN")
keep("fig1", *(lambda r: (branches5, r[0], anchors5(), fixed5))(form_finding(branches5, free5, anchors5(), q5, p5)))
```

#### LINE BY LINE

- `form_finding(branches5, free5, anchors5(dx, dy), q5, p5)` — D.1 on the big net. Internally `D` is now `(61, 61)`; nothing else differs.
- `l[is_spoke]` — the boolean mask picks the ten radial lengths out of 110.
- `R[5, 2]` — the $z$ reaction at the sixth fixed node, the apex.
- `keep(name, ...)` — stores each shape so the figures render from computed data.

Example output:

```text
fig6_1: apex moved by (0, 0) m; radial lengths 8.1-9.0 m; apex reaction 38.9 kN
fig6_2: apex moved by (6, 2) m; radial lengths 8.0-9.3 m; apex reaction 38.9 kN
fig6_3: apex moved by (12, 4) m; radial lengths 8.4-10.9 m; apex reaction 38.9 kN
```

### G.3 Figures 7 and 8: changing the force densities

**Do this.** Keep supports and loads fixed. Change the **radial** $q$, then the **border** $q$. $D$ is rebuilt each time — D.1's second loop.

![Fig. 7](images/schek_fig7_persp.png)
![Fig. 7, plan](images/schek_fig7_plan.png)

*Fig. 7, recomputed: radial force densities 1.0, 0.7, 0.3.*

![Fig. 8](images/schek_fig8_persp.png)
![Fig. 8, plan](images/schek_fig8_plan.png)

*Fig. 8, recomputed: border force densities 10, 5, 1.*

#### FIG 7 — THE RADIAL BRANCHES

| run | radial $q$ | radial lengths |
|---|---|---|
| fig7_1 | 1.0 | 5.0 – 5.9 m |
| fig7_2 | 0.7 | 6.5 – 7.4 m |
| fig7_3 | 0.3 | 10.6 – 11.6 m |

Lower the weight, the cable is allowed to grow: ~5.5 m to ~11 m as $q$ falls 1.0 → 0.3. Roughly, **halving $q$ doubles the length.** The tent gets taller and more pointed.

#### FIG 8 — THE BORDER BRANCHES

| run | border $q$ | border lengths |
|---|---|---|
| fig8_1 | 10 | 3.4 – 4.8 m |
| fig8_2 | 5 | 3.5 – 4.9 m |
| fig8_3 | 1 | 2.9 – 6.5 m |

Here watch the **spread**, not the average. At $q = 10$ the lengths sit in a tight band — the border is stiff relative to the field and stays a near-straight polygon. At $q = 1$ the band widens to 2.9–6.5 m: the border now has no more say than the field pulling on it, so it sags inward between the corners.

**BONUS:** with $q = 1$ everywhere, fig. 8.3 is also the net with the minimal sum of squared branch lengths — Theorem 1 of E.1 with all weights equal.

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

#### LINE BY LINE

- `np.where(is_spoke, qs, q5)` — builds a **copy** of `q5` with every radial branch replaced by `qs`, everything else untouched.
- `np.where(is_border, qb, q5)` — the same for the border.
- Everything else is the plain D.1 call. Because `q` changed, `form_finding` rebuilds `D` and `D_f` internally.

Example output:

```text
fig7_1: radial q = 1.0: radial lengths 5.0-5.9 m
fig7_2: radial q = 0.7: radial lengths 6.5-7.4 m
fig7_3: radial q = 0.3: radial lengths 10.6-11.6 m
fig8_1: border q = 10: border lengths 3.4-4.8 m
fig8_2: border q = 5: border lengths 3.5-4.9 m
fig8_3: border q = 1: border lengths 2.9-6.5 m
```

### G.4 Figure 9: additional distance conditions

**Do this.** Apply length wishes to the big network with F.2's solver. **Read the returned error** — a shape comes back either way.

![Fig. 9](images/schek_fig9_persp.png)
![Fig. 9, plan](images/schek_fig9_plan.png)

*Fig. 9, recomputed: additional distance conditions.*

#### THE WISHES

Every branch not touching the border gets a prescribed length: 6 m for the radials, a fixed multiple of its fig. 6.1 length for the rings.

```text
  62 wishes,  110 knobs  ->  D is (61 x 61),  the wish list is 62 long
```

#### WITH OUR NUMBERS

| run | radial target | ring factor | tries | worst error |
|---|---|---|---|---|
| fig9_1 | 6.0 m | ×1.25 | 42 | 1.2e-09 |
| fig9_2 | 6.0 m | ×0.85 | 35 | 1.1e-09 |
| fig9_3 | 4.5 m | ×0.70 | 58 | 7.5e-10 |

All three granted, to about a nanometre.

#### A NOTE ON SOLVERS

Schek's own 1974 damped scheme **stalls on runs 9.1 and 9.3**, stopping with a 1.2 m error, and the paper warns that "a damped sequence may stop at a shape which fulfils the conditions as close as physically possible". SciPy's trust region reaches all three.

**The conditions were attainable; the 1974 iteration simply could not get there.** Failure to converge never proves a wish impossible — it only means that solver did not find it.

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

#### LINE BY LINE

- `base_l = form_finding(...)[1]` — lengths of the unconstrained fig. 6.1 net, the reference for the ring targets. `[1]` picks `l`.
- `inner = [j for j in range(len(branches5)) if not touches_border[j]]` — indices of every branch touching no border node. These are the wish rows.
- `l_v = [l_radial if is_spoke[j] else base_l[j] * ring_factor for j in inner]` — one target per wish: a flat 6 m for radials, a multiple of the base length for rings.
- `fit_force_densities(..., length_rows=inner, l_v=l_v)` — F.2 with 62 length wishes.
- `err` is the worst remaining wish error; the printed line appends `(NOT solved)` if it exceeds `1e-6`.

Example output:

```text
fig9_1: radial l = 6.0 m, rings x1.25: worst length error 1.2e-09 after 42 tries
fig9_2: radial l = 6.0 m, rings x0.85: worst length error 1.1e-09 after 35 tries
fig9_3: radial l = 4.5 m, rings x0.7: worst length error 7.5e-10 after 58 tries
```

### G.5 Figure 10: the grid-shell model of 112 identical bars

**Do this.** Generate a grid topology, renumber so the four supports come last, put half of each bar's weight at each end, then run three cases.

![Fig. 10](images/schek_fig10_persp.png)
![Fig. 10, plan](images/schek_fig10_plan.png)

*Fig. 10, recomputed: hanging and prestressed net with the same structure.*

#### 8 × 8 NODES, 112 BARS

| case | supports | load | wishes | models |
|---|---|---|---|---|
| **10.1** | 4 corners pulled in to 80 % of span | bar self-weight | all 112 bars = 1.0 m | a **hanging** net of identical bars |
| **10.2** | two opposite corners raised to 3 m | none | none — linear solve only | a **prestressed** net, inner $q=1$, border $q=10$ |
| **10.3** | as 10.2 | none | inner bars one common length; border-touching bars one common force | **mixed** wishes |

#### WITH OUR NUMBERS

```text
  10.1   112 bars of 1.0 m hanging under their own weight
         worst length error  7.5e-10   after 11 tries
         bar forces  0.12 - 2.77 kN            <- a 23x spread!

  10.2   corners raised, inner q = 1, border q = 10
         inner lengths  0.65 - 0.81 m

  10.3   equidistant inner net, constant force near the border
         worst error  1.3e-08   after 38 tries
```

**Case 10.1 is the striking one.** Every bar is exactly 1.0 m — the net is geometrically uniform — yet the forces run from 0.12 to 2.77 kN. Bars near the corners carry everything hanging below them; bars at the free edge carry almost nothing.

**EQUAL GEOMETRY DOES NOT MEAN EQUAL FORCE.** That is exactly why F.2 offers force wishes as well as length wishes — and case 10.3 asks for both at once, on different groups of bars, and gets them.

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
grid_touch = np.array([any(on_edge(v)[0] or on_edge(v)[1] for v in e) for e in grid])
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

#### LINE BY LINE

**Building the grid**

- `gid[(i, k)]` numbers grid nodes row by row; `grid` lists the horizontal and vertical bars, 112 in all; `corners` are the four to be fixed.
- `order` and `renum` renumber every node so the corners come **last** — A.2's rule, now on a generated topology. `flat` holds the coordinates in that order at 1 m spacing.
- `on_edge(v)` — is this node on an outer row or column? `grid_border` marks bars on the outline, `grid_touch` bars with at least one node on it.

**The loads**

- `degree = np.bincount(np.array(grid).ravel())[1:]` — how many bars meet at each node.
- `p10[:, 2] = -0.5 * weight * degree[...]` — **half of every bar's weight at each of its two ends**, the standard way to turn member self-weight into nodal loads.

**The three runs**

- `anchors10` pulls the corners in to 80 % of the flat span; with every bar wished to 1 m the net must sag: fig. 10.1.
- `anchors10b[[0, 2], 2] = 3.0` raises two opposite corners; `q10` puts 10 on border bars, 1 elsewhere; `form_finding` with zero load gives the prestressed net, fig. 10.2.
- `inner10` and `link10` split the non-border bars into those away from the border and those touching it. The last call asks the first group for one common length and the second for one common force, both the mean of the 10.2 values: fig. 10.3.

#### WHERE YOU HAVE ARRIVED

From a Python list of node pairs in A.2 to a constrained form-finding method handling 112 bars with mixed length and force wishes — **one linear solver, built once, never modified.**

Example output:

```text
fig10_1: 112 bars of 1.0 m hanging under their weight: worst length error 7.5e-10 after 11 tries; bar forces 0.12-2.77 kN
fig10_2: corners raised, inner q = 1, border q = 10: inner lengths 0.65-0.81 m
fig10_3: equidistant inner net and constant force near the border: worst error 1.3e-08 after 38 tries
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
