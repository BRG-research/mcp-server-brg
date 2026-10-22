"""A force density application written from Schek (1974), section by section.

Read it top to bottom: each cell (`# %% [id] title`) is one section of the paper, with
the paper's statement as a docstring and the code that adds that section to the program.
Running the file executes every cell in order and prints the results; `build_note.py`
turns the same cells into the tutorial in knowledge/04_form_finding/compas_fd.md.

Only numpy is used.  Nothing here is taken from compas_fd; the application is derived
from the paper and compas_fd is compared with it afterwards in the note.

    python examples/form_finding/schek_app.py
"""

# %% [a1] A.1 Vectors, matrices and the diagonal trick (section 1.4)
r"""**Do this.** Import NumPy, make one vector, turn it into a diagonal matrix.

**THE RULE:** a small letter is a **list**; the same letter capitalised is that list laid on a **diagonal**. Schek never writes "diag" because the capital already says it.

$$
u = \begin{pmatrix} 2 \\ -1 \\ 3 \end{pmatrix}
\qquad\longrightarrow\qquad
U = \mathrm{diag}(u) = \begin{pmatrix} 2 & 0 & 0 \\ 0 & -1 & 0 \\ 0 & 0 & 3 \end{pmatrix}
$$

*Read it as: put the three numbers down the diagonal, zeros everywhere else.*

**Why bother?** Multiplying by a diagonal matrix **scales each entry on its own** — entry 1 by 2, entry 2 by $-1$, entry 3 by 3. Nothing mixes. C.1 uses this to give every cable its own force density.

<details>
<summary><b>The whole alphabet</b> — click to open</summary>

| Symbol | Say it as | What it is | Code | Shape |
|---|---|---|---|---|
| $u$ | "u" | a **list**, one number per branch | `u` | `(12,)` |
| $U$ | "capital U" | that list on a **diagonal** | `np.diag(u)` | `(12, 12)` |
| $C$ | "C" | a **table** of numbers | `C` | `(12, 5)` |
| $C^{t}$ | "C transposed" | the table turned on its side | `C.T` | `(5, 12)` |
| $A B$ | "A times B" | matrix multiplication | `A @ B` | |
| $a_j b_j$ | "a times b, entry by entry" | **not** a matrix product | `a * b` | |
| $L^{-1}$ | "L inverse" | for a diagonal $L$: one over each entry | `np.diag(1.0 / l)` | |

</details>"""
import numpy as np
from typing import TypeAlias

FloatMatrix: TypeAlias = np.ndarray[tuple[int, int], np.dtype[np.float64]]
FloatVector: TypeAlias = np.ndarray[tuple[int], np.dtype[np.float64]]

u_example = np.array([2.0, -1.0, 3.0])
U_example = np.diag(u_example)


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `import numpy as np` — the array library. From here `np.something` is NumPy.
- `FloatMatrix` / `FloatVector` — **labels for the reader only**. They say "2-D array of decimals" and "1-D array". No new kind of array is created.
- `u_example = np.array([2.0, -1.0, 3.0])` — the list, shape `(3,)`.
- `U_example = np.diag(u_example)` — the `(3, 3)` table with those numbers on the diagonal.

</details>"""


# %% [a2] A.2 Numbering the nodes and branches (section 2.1)
r"""**Do this.** Write down the branch list and the two node counts. **Free nodes first, anchors last.** Topology only — no coordinates, no forces yet.

<details>
<summary><b>The counts</b> — click to open</summary>

| Symbol | Say it as | Meaning | Value |
|---|---|---|---|
| $n$ | "n" | **free** nodes (we solve for these) | `5` |
| $n_f$ | "n sub f" | **fixed** nodes (anchors, given) | `4` |
| $n_s$ | "n sub s" | all nodes, $n + n_f$ | `9` |
| $m$ | "m" | branches (cables) | `12` |
| $i(j)$ | "i of j" | **start** node of branch $j$ | $i(1) = 1$ |
| $k(j)$ | "k of j" | **end** node of branch $j$ | $k(1) = 6$ |

</details>

**REASON for free-first:** in A.3 the connectivity table is cut in two by one straight vertical line — free columns left, anchor columns right. Scattered anchors would make that single cut impossible.

![Fig. 2](images/schek_fig2.png)

*Fig. 2, redrawn: the graph and its branch-node matrix.*

<details>
<summary><b>The 12 branches</b> — click to open</summary>

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

</details>

**Every matrix in the rest of the tutorial is this table in another shape.**

#### TWO NUMBERING SYSTEMS — DO NOT MIX

Schek numbers nodes and branches from **1**; Python indexes from **0**. So a node
label becomes a column index by subtracting 1: branch 1 is `branches[0]`."""
branches: list[tuple[int, int]] = [(1, 6), (2, 7), (3, 8), (4, 9),      # 1-4: one branch from each free corner to its anchor
            (1, 4), (1, 2), (2, 3), (3, 4),      # 5-8: the ring
            (4, 5), (1, 5), (2, 5), (3, 5)]      # 9-12: four spokes to the centre node 5
n, n_f = 5, 4                                    # free nodes 1..5, fixed nodes 6..9
m = len(branches)


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `branches = [(1, 6), (2, 7), ...]` — the twelve tuples above, in order. **Position in the list = branch number.** The two entries are node numbers, never coordinates.
- `n, n_f = 5, 4` — five free, four fixed.
- `m = len(branches)` — counts the tuples: `12`.

Not one line here makes geometry or a force. Pure topology.

</details>"""


# %% [a3] A.3 The branch-node matrix and its two column blocks (section 2.1)
r"""**Do this.** Turn the branch list into a table of numbers. One row per branch, one column per node. Then cut the columns into free and anchor blocks.

$$
c(j, i) =
\begin{cases}
+1 & \text{node } i \text{ is the START of branch } j \\
-1 & \text{node } i \text{ is the END of branch } j \\
0 & \text{node } i \text{ is not on branch } j
\end{cases}
$$

*Read it as: the entry in row $j$, column $i$ records how node $i$ sits on branch $j$.* That is all the formula says.

**Why those numbers?** Branch 1 is `(1, 6)`, so its row is $+1$ in column 1 and $-1$ in column 6. Multiply that row by the nine $x$-coordinates:

$$
(+1)x_1 + 0x_2 + 0x_3 + 0x_4 + 0x_5 + (-1)x_6 + 0x_7 + 0x_8 + 0x_9 \;=\; x_1 - x_6
$$

The seven zeros delete seven nodes. **One row measures one cable.**

#### $C_s$ WITH OUR NUMBERS

$$
C_s \;=\;
\begin{array}{r|ccccc|cccc}
 & n_1 & n_2 & n_3 & n_4 & n_5 & n_6 & n_7 & n_8 & n_9 \\
\hline
b_1\ (1,6) & +1 & 0 & 0 & 0 & 0 & -1 & 0 & 0 & 0 \\
b_2\ (2,7) & 0 & +1 & 0 & 0 & 0 & 0 & -1 & 0 & 0 \\
b_3\ (3,8) & 0 & 0 & +1 & 0 & 0 & 0 & 0 & -1 & 0 \\
b_4\ (4,9) & 0 & 0 & 0 & +1 & 0 & 0 & 0 & 0 & -1 \\
b_5\ (1,4) & +1 & 0 & 0 & -1 & 0 & 0 & 0 & 0 & 0 \\
b_6\ (1,2) & +1 & -1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
b_7\ (2,3) & 0 & +1 & -1 & 0 & 0 & 0 & 0 & 0 & 0 \\
b_8\ (3,4) & 0 & 0 & +1 & -1 & 0 & 0 & 0 & 0 & 0 \\
b_9\ (4,5) & 0 & 0 & 0 & +1 & -1 & 0 & 0 & 0 & 0 \\
b_{10}\ (1,5) & +1 & 0 & 0 & 0 & -1 & 0 & 0 & 0 & 0 \\
b_{11}\ (2,5) & 0 & +1 & 0 & 0 & -1 & 0 & 0 & 0 & 0 \\
b_{12}\ (3,5) & 0 & 0 & +1 & 0 & -1 & 0 & 0 & 0 & 0
\end{array}
\;=\;
\begin{bmatrix} C & C_f \end{bmatrix}
$$

12 rows (cables) × 9 columns (nodes). The vertical bar is the cut:

$$
C:\; 12 \times 5 \;\text{(free nodes)}
\qquad
C_f:\; 12 \times 4 \;\text{(anchors)}
$$

**Only rows 1–4 of $C_f$ carry anything** — the ring and spokes join free nodes to free nodes, so they never reach an anchor. **Every row sums to zero:** one $+1$, one $-1$."""
C_s: FloatMatrix = np.zeros((m, n + n_f))
for j, (i, k) in enumerate(branches):
    C_s[j, i - 1] = +1.0                          # node i(j): +1   (Python indices start at 0)
    C_s[j, k - 1] = -1.0                          # node k(j): -1
C: FloatMatrix = C_s[:, :n]                                    # (m, n)   free columns
C_f: FloatMatrix = C_s[:, n:]                                  # (m, n_f) fixed columns

print("C_s shape:", C_s.shape)
print(C_s)


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `C_s = np.zeros((m, n + n_f))` — empty table, 12 rows (branches) by 9 columns (nodes), all `0.0`.
- `for j, (i, k) in enumerate(branches):` — `j` counts branches from `0`; `i`, `k` are the end nodes as **Schek** numbers them (from `1`).
- `C_s[j, i - 1] = +1.0` — row `j`, column of the start node. The `- 1` converts Schek's numbering to Python's.
- `C_s[j, k - 1] = -1.0` — same row, column of the end node.
- `C = C_s[:, :n]` — "all rows, first 5 columns" = free block. `C_f = C_s[:, n:]` — "all rows, from column 5 on" = anchor block. Nothing is copied; the one table is read in two pieces.

**CHECK IT YOURSELF:** row `0` of the printout should read `[1 0 0 0 0 -1 0 0 0]` — branch 1, node 1 to node 6. Row index `j` is branch `j+1`; column index `i` is node `i+1`.

> **Try it.** Change `(1, 6)` to `(6, 1)`. Row 0 flips to `[-1 0 0 0 0 1 0 0 0]`, so it measures $x_6 - x_1$ instead. The final shape the solver finds is **identical** — only the bookkeeping direction changed.

</details>"""



# %% [a4] A.4 The five matrix operations the paper uses
r"""**Read only — no code.** Five operations. Everything the paper does to matrices is one of these.

Trial shape used throughout (free nodes flat, anchors from B.1):

$$
x_s = \begin{pmatrix} -1 & 0 & 1 & 0 & 0 \;\big|\; -2 & 0 & 2 & 0 \end{pmatrix}^{t}
$$

#### 1 — A MATRIX IS A LABELLED TABLE

Row $j$ = branch. Column $i$ = node. Entry = how node $i$ sits on branch $j$.

#### 2 — MATRIX @ VECTOR : MULTIPLY, THEN ADD

$$ u = C_s\, x_s $$

*Read it as: multiply each row by the list, entry by entry, and add the products into one number.*

Row 1 against $x_s$:

$$
\begin{array}{r|ccccccccc}
\text{row 1} & +1 & 0 & 0 & 0 & 0 & -1 & 0 & 0 & 0 \\
x_s & -1 & 0 & 1 & 0 & 0 & -2 & 0 & 2 & 0 \\
\hline
\text{product} & -1 & 0 & 0 & 0 & 0 & +2 & 0 & 0 & 0
\end{array}
\qquad \sum = +1 \;=\; x_1 - x_6
$$

**One row → one number. Twelve rows → twelve numbers:**

$$
C_s x_s = \begin{pmatrix} 1 & 0 & -1 & 0 & -1 & -1 & -1 & 1 & 0 & -1 & 0 & 1 \end{pmatrix}^{t}
$$

$$
(12 \times 9) \;@\; (9,) \;\longrightarrow\; (12,)
\qquad\text{the inner 9's must match}
$$

#### 3 — TRANSPOSE @ VECTOR : ADD UP AT THE NODES

$$ C^{t} f $$

*Read it as: collect the branch values at each node, $+$ if the branch starts there, $-$ if it ends there.*

This is summing forces at a joint. With $f_j = 1$ on every branch:

$$
\begin{array}{r|l|r}
\text{node} & \text{branches meeting it} & C^{t}f \\
\hline
1 & +b_1 +b_5 +b_6 +b_{10} & +4 \\
2 & +b_2 -b_6 +b_7 +b_{11} & +2 \\
3 & +b_3 -b_7 +b_8 +b_{12} & +2 \\
4 & +b_4 -b_5 -b_8 +b_9 & 0 \\
5 & -b_9 -b_{10} -b_{11} -b_{12} & -4
\end{array}
$$

Operation 2 carries information **nodes → branches**; operation 3 carries it **branches → nodes**. Every equilibrium equation below is one of each.

#### 4 — DIAGONAL @ VECTOR : SCALE EACH ENTRY ALONE

$$ Q u \quad\text{where}\quad Q = \mathrm{diag}(q) $$

*Read it as: entry $j$ of the answer is just $q_j$ times $u_j$.*

$$
\begin{array}{r|cccccccccccc}
q & 2 & 2 & 2 & 2 & 1 & 1 & 1 & 1 & 1 & 1 & 1 & 1 \\
u & 1 & 0 & -1 & 0 & -1 & -1 & -1 & 1 & 0 & -1 & 0 & 1 \\
\hline
Qu & 2 & 0 & -2 & 0 & -1 & -1 & -1 & 1 & 0 & -1 & 0 & 1
\end{array}
$$

Each column is the product of the two above it. So the order can swap: $U q = Q u$. **That swap is the whole force density trick.**

#### 5 — SOLVING $D x = b$

$$ D x = b \quad\longrightarrow\quad \texttt{x = np.linalg.solve(D, b)} $$

*Read it as: find the list $x$ that, pushed through $D$, gives back $b$.*

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
\quad\Rightarrow\quad
z = \begin{pmatrix} 0.045 \\ 0.330 \\ 0.045 \\ 0.330 \\ 0.063 \end{pmatrix}
$$

**Check it:** $Dz$ gives back exactly $b$. NumPy never forms $D^{-1}$ to do this, and neither should you.

#### WHERE THIS GOES

$$ D = C^{t} Q C $$

*Read it as: spread the coordinates onto the branches, scale each branch by its force density, sum back at the nodes.* Operations 3, 4 and 2 nested."""


# %% [b1] B.1 The inputs: anchors and loads (section 2.2)
r"""**Do this.** Add the anchor coordinates and the loads. Metres, kilonewtons, $z$ up. Free coordinates stay unknown until C.3.

<details>
<summary><b>What is known, what is not</b> — click to open</summary>

| Symbol | Say it as | Known? | Shape | Holds |
|---|---|---|---|---|
| $x_f, y_f, z_f$ | "x sub f" | **INPUT** | `(4,)` each | one coordinate of each anchor 6–9 |
| $p_x, p_y, p_z$ | "p sub x" | **INPUT** | `(5,)` each | one load component at each free node |
| $x, y, z$ | "x, y, z" | **unknown — the answer** | `(5,)` each | one coordinate of each free node 1–5 |
| $l_j$ | "l sub j" | follows from the shape | `(12,)` | length of branch $j$ |
| $s_j$ | "s sub j" | follows from the shape | `(12,)` | force in branch $j$ |

</details>

**These values are our choice, not measurements from Schek.** Figure 2 gives only the connectivity.

#### WITH OUR NUMBERS — INPUT

| anchor | x (m) | y (m) | z (m) | |
|---|---|---|---|---|
| 6 | −2 | 0 | 0 | ground level |
| 7 | 0 | 2 | **1** | lifted |
| 8 | 2 | 0 | 0 | ground level |
| 9 | 0 | −2 | **1** | lifted |

$$
\begin{array}{r|rrr}
\text{anchor} & x_f & y_f & z_f \\
\hline
6 & -2 & 0 & 0 \\
7 & 0 & 2 & \mathbf{1} \\
8 & 2 & 0 & 0 \\
9 & 0 & -2 & \mathbf{1}
\end{array}
\qquad
p_z = \begin{pmatrix} -0.5 \\ -0.5 \\ -0.5 \\ -0.5 \\ -0.5 \end{pmatrix}
\quad p_x = p_y = 0
$$

Nodes 7 and 9 are the lifted pair. **The minus sign on $p_z$ is the only thing making this net hang instead of rise** — $z$ points up, so gravity is negative.

**Read down a column** across the three arrays to get one anchor point: node 6 is $(-2, 0, 0)$.

**REASON for the minus sign:** $z$ points up, so gravity is a negative $p_z$. That minus is the only thing making this net hang instead of rise."""
x_f: FloatVector = np.array([-2.0, 0.0, 2.0, 0.0], dtype=np.float64)             # anchors 6, 7, 8, 9
y_f: FloatVector = np.array([0.0, 2.0, 0.0, -2.0], dtype=np.float64)
z_f: FloatVector = np.array([0.0, 1.0, 0.0, 1.0], dtype=np.float64)             # two anchors lifted by 1 m
p_x: FloatVector = np.zeros(n, dtype=np.float64)
p_y: FloatVector = np.zeros(n, dtype=np.float64)
p_z: FloatVector = np.full(n, -0.5, dtype=np.float64)                            # 0.5 kN downward at every free node


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `np.array([-2.0, 0.0, 2.0, 0.0], dtype=np.float64)` — one anchor coordinate list. `dtype=np.float64` means ordinary decimals.
- `np.zeros(n)` — five zeros: no sideways load.
- `np.full(n, -0.5)` — five copies of `-0.5`: half a kilonewton down at every free node.

</details>"""


# %% [b2] B.2 Coordinate differences and lengths, equation (1)
r"""**Do this.** Write one function that, **given** node positions, measures every branch: three coordinate differences and a length. It never moves a node.

$$
u = C x + C_f x_f, \qquad v = C y + C_f y_f, \qquad w = C z + C_f z_f
$$

*Read it as: for every branch, subtract the coordinates of its two end nodes — the free end from one product, the anchored end from the other.*

$$
\underbrace{(12,)}_{u} \;=\; \underbrace{(12\times5)}_{C}\,\underbrace{(5,)}_{x} \;+\; \underbrace{(12\times4)}_{C_f}\,\underbrace{(4,)}_{x_f}
$$

**Why two products?** A branch can have one end free and one anchored. $Cx$ collects the free part, $C_f x_f$ the anchored part, and `+` puts the two halves of one subtraction back together.

$$
l_j = \sqrt{u_j^{2} + v_j^{2} + w_j^{2}}
$$

*Read it as: ordinary Pythagoras on each branch alone.* This is **not** a matrix operation.

#### WITH OUR NUMBERS — the flat trial shape of B.3

| branch | $u$ | $v$ | $w$ | $l$ | check |
|---|---|---|---|---|---|
| 1 (1,6) | 1.000 | 0.000 | 0.000 | 1.000 | $-1-(-2)=1$ |
| 2 (2,7) | 0.000 | −3.000 | −1.000 | 3.162 | $\sqrt{0+9+1}$ |
| 3 (3,8) | −1.000 | 0.000 | 0.000 | 1.000 | $1-2=-1$ |
| 4 (4,9) | 0.000 | 3.000 | −1.000 | 3.162 | $1-(-2)=3$ |
| 5 (1,4) | −1.000 | −1.000 | 0.000 | 1.414 | $\sqrt{1+1}$ |
| 6 (1,2) | −1.000 | 1.000 | 0.000 | 1.414 | |
| 7 (2,3) | −1.000 | −1.000 | 0.000 | 1.414 | |
| 8 (3,4) | 1.000 | −1.000 | 0.000 | 1.414 | |
| 9 (4,5) | 0.000 | 1.000 | 0.000 | 1.000 | |
| 10 (1,5) | −1.000 | 0.000 | 0.000 | 1.000 | |
| 11 (2,5) | 0.000 | −1.000 | 0.000 | 1.000 | |
| 12 (3,5) | 1.000 | 0.000 | 0.000 | 1.000 | |

**Row 2 by hand:** branch 2 joins node 2 at $(0,-1,0)$ to anchor 7 at $(0,2,1)$. Start minus end gives $u=0$, $v=-3$, $w=-1$, so $l=\sqrt{10}=3.162$.

$u, v, w$ together are the branch's **direction vector**; divided by $l$ they are the direction cosines B.3 needs."""
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


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `u = C @ x + C_f @ x_f` — `(12,5)@(5,)` gives 12 numbers, `(12,4)@(4,)` gives 12 numbers, added entry by entry. For branch 1 that is $x_1 - x_6$: the $+1$ lives in `C`, the $-1$ in `C_f`.
- `v = ...`, `w = ...` — the identical product with the $y$ and $z$ coordinates.
- `l = np.sqrt(u**2 + v**2 + w**2)` — `u**2` squares **every entry at once**, no loop. `np.sqrt` roots every entry.
- The function takes `C`, `C_f` and the coordinates as **arguments**, so D.1 can reuse it on any network.

**THIS IS WHERE THE DIFFICULTY COMES FROM.** $l$ holds a square root of the unknown coordinates, and B.3 divides by it.

</details>"""



# %% [b3] B.3 Equilibrium with the unknown forces, equation (2)
r"""**Do this.** Write the honest force balance: at every free node the cable pulls must add up to the load. Then test it on a guessed shape and watch it fail.

$$
C^{t} U L^{-1} s = p_x, \qquad C^{t} V L^{-1} s = p_y, \qquad C^{t} W L^{-1} s = p_z
$$

*Read it as: split each cable force into its $x$, $y$ and $z$ shares, add the shares up at every node, and the total must equal the load there.*

#### READ IT RIGHT TO LEFT — FOUR STAGES

| Step | Symbol | Say it as | What it does | Shape of the result |
|---|---|---|---|---|
| 1 | $L^{-1} s$ | "L inverse times s" | divides each force by its own cable length, $s_j / l_j$ | `(12,)` |
| 2 | $U L^{-1} s$ | "U times that" | multiplies by $u_j$: the $x$ part of that pull | `(12,)` |
| 3 | $C^{t}(\ldots)$ | "C transposed times that" | sums those parts at every node | `(5,)` |
| 4 | $-\,p_x$ | "minus p sub x" | subtracts the load. **Zero means balanced** | `(5,)` |

$u_j / l_j$ is the **direction cosine** — how much of branch $j$ points along $x$.

#### WITH OUR NUMBERS — flat shape, 1 kN in every cable, vertical axis

$$
\begin{array}{r|cccccccccccc}
\text{branch} & 1 & 2 & 3 & 4 & 5 & 6 & 7 & 8 & 9 & 10 & 11 & 12 \\
\hline
s & 1 & 1 & 1 & 1 & 1 & 1 & 1 & 1 & 1 & 1 & 1 & 1 \\
l & 1 & 3.162 & 1 & 3.162 & 1.414 & 1.414 & 1.414 & 1.414 & 1 & 1 & 1 & 1 \\
\hline
\textbf{1}\;\; s/l & 1 & 0.316 & 1 & 0.316 & 0.707 & 0.707 & 0.707 & 0.707 & 1 & 1 & 1 & 1 \\
w & 0 & -1 & 0 & -1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
\textbf{2}\;\; w\,s/l & 0 & -0.316 & 0 & -0.316 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0
\end{array}
$$

Only the two cables to the **lifted** anchors pull vertically at all. Stage 3 sums them at the nodes, stage 4 subtracts the load:

$$
\underbrace{\begin{pmatrix} 0 \\ -0.316 \\ 0 \\ -0.316 \\ 0 \end{pmatrix}}_{\textbf{3}\;\;C^{t}(\ldots)}
-
\underbrace{\begin{pmatrix} -0.5 \\ -0.5 \\ -0.5 \\ -0.5 \\ -0.5 \end{pmatrix}}_{p_z}
=
\underbrace{\begin{pmatrix} 0.500 \\ 0.184 \\ 0.500 \\ 0.184 \\ 0.500 \end{pmatrix}}_{\textbf{4}\;\;e_z \;\neq\; 0}
$$

The other two axes give $e_x = (-1.414,\, 0,\, 1.414,\, 0,\, 0)$ and $e_y = (0,\, -3.363,\, 0,\, 3.363,\, 0)$.

**NOT ONE NODE BALANCES.** A flat net has no vertical component anywhere, so it cannot carry a vertical load. Nodes 2 and 4 are less wrong only because their anchors were lifted.

#### WHY THIS EQUATION IS A DEAD END

$u, v, w$ and $l$ **all** depend on the unknown coordinates, and $l$ buries them under a square root. $x$ cannot be isolated. C.1 fixes this with one substitution."""
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


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `L_inv = np.diag(1.0 / l)` — the paper's $L^{-1}$. For a diagonal matrix the inverse is the diagonal of the reciprocals, so `1.0 / l` divides entry by entry.
- `C.T @ np.diag(u) @ L_inv @ s - p_x` — the four stages above, in one line, read from the right.
- The three return values are the three axes; `ez` is the one printed.
- `x_guess`, `y_guess`, `z_guess`, `s_guess` — a deliberately wrong start: free nodes flat, 1 kN everywhere.

</details>"""



# %% [c1] C.1 The force density, equations (4) to (6)
r"""**Do this.** Add one number per branch: its force density. One line of code, and the nonlinear problem of Part B becomes linear.

$$
q_j = \frac{s_j}{l_j}
$$

*Read it as: how hard the cable pulls, per metre of its own length.* Dimension: force / length (kN/m).

$$
\text{one cable:}\quad l = 2.5\ \text{m},\;\; s = 10\ \text{kN} \;\longrightarrow\; q = \tfrac{10}{2.5} = 4\ \text{kN/m}
$$

#### WHY THE LENGTH CANCELS — THE WHOLE TRICK

$$
\text{Force}_{x,\,j} = s_j \cdot \frac{u_j}{l_j}
\qquad\xrightarrow{\;s_j = q_j l_j\;}\qquad
(q_j\,l_j) \cdot \frac{u_j}{l_j} = q_j\,u_j = q_j\,(x_i - x_k)
$$

*Read it as: the $l_j$ on top cancels the $l_j$ underneath, leaving a plain multiple of the coordinates.*

With our branch 1, after the solve of C.3:

$$
\underbrace{2.402 \cdot \frac{1.200}{1.201}}_{\text{the long way}} \;=\; 2.400
\qquad
\underbrace{2.0 \cdot 1.200}_{\text{the short way}} \;=\; 2.400
$$

The square root is gone. $q_j(x_i - x_k)$ is **linear** in the unknown coordinates.

#### THE SWAP (EQUATION 6)

$$
C^{t} U q \;=\; C^{t} Q u \;=\; p_x
$$

*Read it as: the known $q$ and the unknown $u$ can trade places, because both are only scaling entries one at a time.* After the swap the **known** numbers sit in $Q$ and the **unknown** geometry $u$ stands outside, ready to solve for.

#### OUR CHOICE — INPUT

$$
q = \begin{pmatrix} \underbrace{2\;\;2\;\;2\;\;2}_{\text{anchor cables}} & \underbrace{1\;\;1\;\;1\;\;1}_{\text{ring}} & \underbrace{1\;\;1\;\;1\;\;1}_{\text{spokes}} \end{pmatrix}^{t}
\qquad
Q = \mathrm{diag}(q) =
\begin{pmatrix}
2 & & & & \\
 & \ddots & & & \\
 & & 2 & & \\
 & & & \ddots & \\
 & & & & 1
\end{pmatrix}
$$

$Q$ is $12\times12$: 144 entries, only 12 of them non-zero.

**$q$ is NOT a stiffness and NOT a cross-section.** Nothing here knows about steel. It is a ratio you choose; E.1 shows what choosing it controls."""
q = np.array([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1], dtype=float)   # one force density per branch: the design input


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `q = np.array([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1], dtype=float)` — one force density per branch, **in branch order**: entry `0` is branch 1 `(1, 6)`, entry `11` is branch 12 `(3, 5)`.

That is the whole cell.

> **Try it.** Raise $q$ on the four anchor cables from $2.0$ to $10.0$ kN/m. Does centre node 5 end up **higher** or **lower**? Write your answer down — D.2 runs it and prints the number.

</details>"""



# %% [c2] C.2 The matrices D and D_f, equations (7) and (8)
r"""**Do this.** Build the two matrices that turn the net into a linear system, then the right-hand sides.

Put $u = C x + C_f x_f$ from B.2 into $C^{t} Q u = p_x$ from C.1:

$$
\underbrace{(C^{t} Q C)}_{D}\,x + \underbrace{(C^{t} Q C_f)}_{D_f}\,x_f = p_x
\qquad\Longrightarrow\qquad
D x = p_x - D_f x_f
$$

*Read it as: separate the terms with unknown free coordinates from the terms with known anchor coordinates, and move the known ones to the right.*

The same $D$ serves all three axes — $x$ never appears in the $z$ equation:

$$
D x = p_x - D_f x_f, \qquad D y = p_y - D_f y_f, \qquad D z = p_z - D_f z_f
$$

| Step | Symbol | Say it as | What it does | Shape of the result |
|---|---|---|---|---|
| 1 | $C$ | "C" | spreads free coordinates onto the 12 branches | `(12, 5)` |
| 2 | $Q C$ | "Q times that" | scales each branch by its own force density | `(12, 5)` |
| 3 | $C^{t} Q C$ | "C transposed times that" | sums back at the 5 free nodes | `(5, 5)` |

#### HOW TO READ EVERY ENTRY OF $D$

$$
D_{ii} = \sum_{\text{branches at node } i} q_j
\qquad
D_{ik} = -q_j \;\text{ if a branch joins nodes } i,k \;\text{ else } 0
$$

#### TRACEABLE DEMO — give every branch a different $q$

Set $q_j = j$ so you can follow where each number lands. This is Schek's own figure 4.

$$
\begin{array}{r|l|r}
\text{node} & \text{branches at it} & \textstyle\sum q \\
\hline
1 & 1,\,5,\,6,\,10 & 1+5+6+10 = 22 \\
2 & 2,\,6,\,7,\,11 & 2+6+7+11 = 26 \\
3 & 3,\,7,\,8,\,12 & 3+7+8+12 = 30 \\
4 & 4,\,5,\,8,\,9 & 4+5+8+9 = 26 \\
5 & 9,\,10,\,11,\,12 & 9+10+11+12 = 42
\end{array}
\qquad
D = \begin{pmatrix}
22 & -6 & 0 & -5 & -10 \\
-6 & 26 & -7 & 0 & -11 \\
0 & -7 & 30 & -8 & -12 \\
-5 & 0 & -8 & 26 & -9 \\
-10 & -11 & -12 & -9 & 42
\end{pmatrix}
$$

Every number traces to a branch: $-6$ is $-q_6$, and branch 6 joins nodes 1–2. The $0$ at $(1,3)$ means nodes 1 and 3 have no branch between them. **$D$ is symmetric.**

#### WITH OUR ACTUAL $q$

$$
D = \begin{pmatrix}
5 & -1 & 0 & -1 & -1 \\
-1 & 5 & -1 & 0 & -1 \\
0 & -1 & 5 & -1 & -1 \\
-1 & 0 & -1 & 5 & -1 \\
-1 & -1 & -1 & -1 & 4
\end{pmatrix}
\qquad
D_f = \begin{pmatrix}
-2 & 0 & 0 & 0 \\
0 & -2 & 0 & 0 \\
0 & 0 & -2 & 0 \\
0 & 0 & 0 & -2 \\
0 & 0 & 0 & 0
\end{pmatrix}
$$

Node 1: $2+1+1+1 = 5$. Node 5 (centre): $1+1+1+1 = 4$. **The last row of $D_f$ is all zeros — the centre touches no anchor.**

#### THE RIGHT-HAND SIDE

The anchors cannot move, so their pull is a known number and belongs on the right. For the vertical axis, with $z_f = (0,1,0,1)$ and $p_z = -0.5$ everywhere:

$$
\underbrace{\begin{pmatrix} 0 \\ 2 \\ 0 \\ 2 \\ 0 \end{pmatrix}}_{-D_f z_f}
+
\underbrace{\begin{pmatrix} -0.5 \\ -0.5 \\ -0.5 \\ -0.5 \\ -0.5 \end{pmatrix}}_{p_z}
=
\underbrace{\begin{pmatrix} -0.5 \\ 1.5 \\ -0.5 \\ 1.5 \\ -0.5 \end{pmatrix}}_{b_z}
$$

Nodes 2 and 4 get $+1.5$ because they hang from the **lifted** anchors."""
Q = np.diag(q)
D = C.T @ Q @ C                                   # (n, n)   eq. (8)
D_f = C.T @ Q @ C_f                               # (n, n_f)

rhs = np.c_[p_x - D_f @ x_f, p_y - D_f @ y_f, p_z - D_f @ z_f]
print("D (shape 5x5):", D, sep="\n")
print("D_f (shape 5x4):", D_f, sep="\n")
print("right-hand sides (columns x, y, z; shape 5x3):", rhs, sep="\n")


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `Q = np.diag(q)` — the 12 force densities on a `(12, 12)` diagonal.
- `D = C.T @ Q @ C` — equation (8), the three stages above. `(5,12) @ (12,12) @ (12,5)` → `(5, 5)`.
- `D_f = C.T @ Q @ C_f` — same sandwich with the anchor columns → `(5, 4)`.
- `rhs = np.c_[...]` — `np.c_` glues three length-5 columns side by side into one `(5, 3)` table, one column per axis.

**CHECK IT YOURSELF:** node 5's row of `D` must be `[-1, -1, -1, -1, 4]` — four spokes of $q = 1$ pulling it, no anchor term anywhere.

> **Try it.** Change only `p_z` and rerun: `D` and `D_f` print **unchanged**, only `rhs` moves. Change one entry of `q`: `D` changes too. That is the difference between the two loops of D.1.

</details>"""



# %% [c3] C.3 Solving for the free coordinates, equation (9)
r"""**Do this.** Solve the three linear systems. The shape appears here — one direct step, no iteration, no initial guess.

$$
D x = p_x - D_f x_f, \qquad D y = p_y - D_f y_f, \qquad D z = p_z - D_f z_f
$$

*Read it as: three separate problems that happen to share one matrix.*

#### THE VERTICAL SYSTEM IN FULL

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
\quad\Rightarrow\quad
z = \begin{pmatrix} 0.045 \\ 0.330 \\ 0.045 \\ 0.330 \\ 0.063 \end{pmatrix}
$$

All three axes together:

$$
\begin{array}{r|rrr}
\text{node} & x & y & z \\
\hline
1 & -0.800 & 0.000 & 0.045 \\
2 & 0.000 & 0.800 & 0.330 \\
3 & 0.800 & 0.000 & 0.045 \\
4 & 0.000 & -0.800 & 0.330 \\
5 & 0.000 & 0.000 & 0.063
\end{array}
$$

Nodes 2 and 4 are pulled up by the lifted anchors; node 5 is the centre saddle. Compare with the flat guess of B.3, out of balance by up to 0.5 kN everywhere — these coordinates balance to machine precision.

**Why a solution exists.** With all $q_j > 0$ and the net properly anchored, $D$ is **symmetric positive definite**: exactly one solution, no ambiguity. "Properly anchored" means every group of free nodes can reach an anchor through branches with $q > 0$. If part of the net floats free, $D$ is singular and the solve returns `nan` — the method telling you the structure is a mechanism.

**Solve, do not invert.** `np.linalg.solve(D, b)` never forms $D^{-1}$: more accurate and less work."""
x: FloatVector = np.linalg.solve(D, p_x - D_f @ x_f)            # eq. (9)
y: FloatVector = np.linalg.solve(D, p_y - D_f @ y_f)
z: FloatVector = np.linalg.solve(D, p_z - D_f @ z_f)


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `x = np.linalg.solve(D, p_x - D_f @ x_f)` — builds the right-hand side for the $x$ axis and solves. Returns `(5,)`: the $x$ of each free node.
- `y = ...`, `z = ...` — same two lines with the $y$ and $z$ data. **`D` is identical in all three calls**; only the right-hand side changes.

The whole 3-D equilibrium geometry came out of three ordinary linear solves. No starting shape, no tolerance, no risk of the wrong answer. That is the payoff for prescribing $q$ instead of $s$.

> **Try it.** Add 1 m to every anchor height (`z_f + 1.0`) and resolve. Every free node rises by exactly 1 m, shape unchanged — the right-hand side moved, the matrix did not.

</details>"""



# %% [c4] C.4 Lengths, forces and the equilibrium check, equation (10)
r"""**Do this.** Measure the solved net, recover the force in each cable, then check it against Part B's nonlinear equation.

$$
s_j = q_j \, l_j
$$

*Read it as: force density times length gives the force back.* No second solve needed.

| branch | group | $q$ (kN/m) | $l$ (m) | $s = q\,l$ (kN) |
|---|---|---|---|---|
| 1 (1,6) | anchor | 2.0 | 1.201 | 2.402 |
| 2 (2,7) | anchor | 2.0 | 1.374 | 2.748 |
| 3 (3,8) | anchor | 2.0 | 1.201 | 2.402 |
| 4 (4,9) | anchor | 2.0 | 1.374 | 2.748 |
| 5–8 | ring | 1.0 | 1.167 | 1.167 |
| 9, 11 | spoke | 1.0 | 0.844 | 0.844 |
| 10, 12 | spoke | 1.0 | 0.800 | 0.800 |

Branch 2: $2.0 \times 1.374 = 2.748$ kN. **Where $q$ is equal, the longer cable carries the larger force** — the opposite of a spring.

#### THE CHECK

$$
e = C^{t} U L^{-1} s - p \;\approx\; 0
$$

*Read it as: collected cable pulls minus applied load, at every node, must be zero.*

$$
\max |e| = 1.11 \times 10^{-15}\ \text{kN}
$$

Machine zero. **The linear solve of C.3 satisfies the nonlinear equilibrium of B.3 exactly** — Schek's central claim, checked rather than assumed."""
u, v, w, l = coordinate_differences(C, x, y, z, C_f, x_f, y_f, z_f)      # eq. (1) on the solution
s = l * q                                         # eq. (10)

xyz_free = np.c_[x, y, z]
print("free node coordinates (columns x, y, z):", xyz_free, sep="\n")
print("lengths l:", l)
print("forces  s:", s)
print("equilibrium error (2) on the solution:", max(np.abs(e).max() for e in equilibrium_error(x, y, z, s)))


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `u, v, w, l = coordinate_differences(...)` — the B.2 function, now on the **solved** coordinates instead of a guess.
- `s = l * q` — equation (10). `*` is entry by entry, **not** a matrix product.
- `xyz_free = np.c_[x, y, z]` — glues the three `(5,)` answers into one `(5, 3)` table, one row per node.
- `max(np.abs(e).max() for e in equilibrium_error(x, y, z, s))` — B.3's four-stage check on the result, worst node in any direction.

> **Try it.**
> - `p_z = np.full(n, -2.0)` — net sags deeper, forces grow. $D$ untouched, only `rhs` changes.
> - `z_f += 1.0` — whole net rises 1 m, identical shape. Again only `rhs`.
> - `q[:4] = 10.0` — now $D$ itself is rebuilt and the shape genuinely changes.

</details>"""



# %% [d1] D.1 The form-finding loop as one function (figure 3)
r"""**Do this.** Put everything from A.3 to C.4 into one function that builds its own connectivity from its arguments, so it works on any network.

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

| | name | shape | meaning |
|---|---|---|---|
| **in** | `branches` | list of $m$ tuples | `(start, end)`, counting from 1 |
| | `n_free` | int | free nodes, numbered first |
| | `xyz_fixed` | `(n_f, 3)` | anchor coordinates |
| | `q` | `(m,)` | one force density per branch |
| | `p` | `(n_free, 3)` | one load vector per free node |
| **out** | `xyz` | `(n_free, 3)` | equilibrium coordinates |
| | `l`, `s` | `(m,)` | lengths, forces $q\,l$ |
| | `reactions` | `(n_f, 3)` | force the cables apply to each support |

#### ONE CHANGE: THREE AXES AT ONCE

Earlier $x$, $y$, $z$ were three `(5,)` arrays. Here they are one `(5, 3)` table, because a matrix times a 3-column table is three matrix-vector products side by side:

$$
\underbrace{(12\times5)}_{C}\;\underbrace{(5\times3)}_{xyz} \longrightarrow (12\times3)
\qquad\text{column 0 is the old } Cx,\;\text{column 1 } Cy,\;\text{column 2 } Cz
$$

Nothing new happens. The same arithmetic is written once instead of three times."""
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


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

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

</details>"""



# %% [d2] D.2 Using the loop: move the anchors, change the force densities
r"""**Do this.** Call the function with the original data, then change one input at a time. After this cell you own a reusable linear force density solver.

#### THREE RUNS

| run | changed | rebuilt | expect |
|---|---|---|---|
| 1 | nothing | — | reproduces C.3 |
| 2 | every anchor lifted 1 m | right-hand side only | net rises 1 m, same shape |
| 3 | $q = 10$ on branches 1–4 | $D$ and $D_f$ | shape itself changes |

#### WITH OUR NUMBERS

$$
\begin{array}{l|r}
\text{centre node height } z_5 & \\
\hline
\text{base case} & 0.063\ \text{m} \\
\text{all anchors lifted 1 m} & 1.063\ \text{m} \\
\text{anchor cables } q = 10 & 0.313\ \text{m}
\end{array}
$$

Run 2 is the one to stare at: the net moved up by precisely what the anchors moved and kept its shape exactly. $D$ never saw the change.

Run 3 answers the prediction from C.1 — stiffer anchor cables pull the corners out and **up**. **A larger $q$ is not a larger force, it is a larger force per metre**, so the cable settles shorter and straighter.


Run 2 is the one to stare at: the net moved up by precisely what the anchors moved and kept its shape exactly. $D$ never saw the change.

Run 3 answers the prediction from C.1 — stiffer anchor cables pull the corners out and **up**, lifting the centre from 0.063 to 0.313 m. **A larger $q$ is not a larger force, it is a larger force per metre**, so the cable settles shorter and straighter.

#### THE REACTIONS — AND THE GLOBAL CHECK

$$
R_z = \begin{pmatrix} -0.089 \\ \mathbf{1.339} \\ -0.089 \\ \mathbf{1.339} \end{pmatrix}
\qquad \sum R_z = 2.500\ \text{kN} \;=\; \underbrace{5 \times 0.5}_{\text{total load}}
$$

The two **lifted** anchors carry nearly everything; the ground-level pair is pulled slightly **down**. If that sum does not balance the load, something upstream is wrong — the cheapest check there is.

The two ground-level anchors are pulled slightly **down**. If that sum does not balance the load, something upstream is wrong — it is the cheapest check there is."""
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


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `xyz_fixed = np.c_[x_f, y_f, z_f]`, `p = np.c_[p_x, p_y, p_z]` — repackage B.1's separate axis arrays into the `(4,3)` and `(5,3)` tables the function wants.
- `xyz_fixed + np.array([0, 0, 1.0])` — NumPy **broadcasting**: the 3-vector is added to every row, lifting all four anchors 1 m with no loop.
- `np.where(np.arange(m) < 4, 10.0, 1.0)` — a fresh `q`: `10.0` where the branch index is under 4, `1.0` elsewhere. The original `q` is untouched.
- `R1[:, 2]` — column 2 of the reactions: the vertical component at each anchor.

#### MILESTONE

**You have implemented the linear force density method.** Everything up to here is the complete, usable tool. E explains what $q$ means; F adds wishes about lengths and forces. Neither is needed to use what you just built.

</details>"""



# %% [e1] E.1 What the force densities mean geometrically (section 4)
r"""**Do this.** Run the solver with **zero load** and test two statements about what $q$ actually controls.

#### THE QUESTION

C.1 introduced $q$ as a convenient ratio. That is an excuse, not an explanation. **When I choose $q$, what am I choosing geometrically?**

#### EQUATION (40)

Forget forces. Which node positions make this as small as possible?

$$
u^{t} P u + v^{t} P v + w^{t} P w \;\longrightarrow\; \min
$$

*Read it as: make the weighted sum of squared branch lengths as small as possible.*

$$
u^{t} P u = \sum_j P_j\, u_j^{2}
\qquad\text{all three terms together} = \sum_j P_j\, l_j^{2}
$$

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

$$
\begin{array}{r|rrr}
\text{node} & x & y & z \\
\hline
1 & -0.800 & 0.000 & 0.357 \\
2 & 0.000 & 0.800 & 0.643 \\
3 & 0.800 & 0.000 & 0.357 \\
4 & 0.000 & -0.800 & 0.643 \\
5 & 0.000 & 0.000 & \mathbf{0.500}
\end{array}
\qquad
l_0:\;\; \underbrace{1.252}_{\times 4 \text{ anchors}}\;\; \underbrace{1.167}_{\times 4 \text{ ring}}\;\; \underbrace{0.813}_{\times 4 \text{ spokes}}
$$

Node 5 sits exactly midway: no load, perfect symmetry.

**TEST THEOREM 1** — the weighted sum at this shape:

$$
\underbrace{4(2 \cdot 1.252^2)}_{12.540} + \underbrace{4(1 \cdot 1.167^2)}_{5.447} + \underbrace{4(1 \cdot 0.813^2)}_{2.644}
\;=\; \sum_j q_j l_j^{2} \;=\; 20.629
$$

If this is the minimum the gradient must vanish — and it does, to $2.22 \times 10^{-15}$. Move any free node in any direction and 20.629 can only grow.

Move any free node in any direction and 20.629 can only grow.

**TEST THEOREM 2** — set $q_j = 1/l_j$ and compute $s_j = q_j l_j$:

$$
s = \begin{pmatrix} 1 & 1 & 1 & 1 & 1 & 1 & 1 & 1 & 1 & 1 & 1 & 1 \end{pmatrix}^{t}
$$

Twelve ones. Same force in every cable, whatever its length.

Twelve ones. Same force in every cable, whatever its length.

#### THE DESIGN TABLE

| You want a branch… | Choose |
|---|---|
| **short and taut** | **large** $q$ |
| **long and slack** | **small** $q$ |
| **equal force everywhere** | $q_j = c / l_j$, iterated (Part F) |

**REASON the paper uses $q = 100$ on the border and $q = 1$ in the field:** the border is told to stay short and straight while the field is free to drape."""
xyz0, l0, s0, _ = form_finding(branches, n, xyz_fixed, q, np.zeros((n, 3)))      # no load
uvw0 = C @ xyz0 + C_f @ xyz_fixed
gradient = 2 * C.T @ np.diag(q) @ uvw0                                              # d/dx of u^t Q u, per axis
print("Theorem 1: gradient of the weighted squared lengths at the unloaded equilibrium:", np.abs(gradient).max())
q_const = 1.0 / l0                                                               # Theorem 2
print("Theorem 2: forces with q = 1 / l:", l0 * q_const)


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `form_finding(..., np.zeros((n, 3)))` — the D.1 solver with a `(5, 3)` block of zeros as the load: the unloaded, purely prestressed net.
- `uvw0 = C @ xyz0 + C_f @ xyz_fixed` — equation (1) on that solution.
- `gradient = 2 * C.T @ np.diag(q) @ uvw0` — the derivative of $u^{t}Qu$ with respect to the free coordinates (the paper's (37), (38)), one column per axis. Printing its largest entry tests Theorem 1.
- `q_const = 1.0 / l0` — Theorem 2's prescription. `l0 * q_const` gives the forces: twelve exact ones.

**$q$ is the weight you put on a cable in a competition to be short.**

</details>"""



# %% [f1] F.1 Wishes beyond equilibrium (section 3.1)
r"""**Do this.** Pick four branches, say how long you want them, and subtract. The result is a short list of **what is still wrong**.

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

$$
g = \begin{pmatrix} l_1 \\ l_2 \\ l_3 \\ l_4 \end{pmatrix} - \begin{pmatrix} 1.2 \\ 1.2 \\ 1.2 \\ 1.2 \end{pmatrix}
= \begin{pmatrix} 1.20083 \\ 1.37420 \\ 1.20083 \\ 1.37420 \end{pmatrix} - \begin{pmatrix} 1.2 \\ 1.2 \\ 1.2 \\ 1.2 \end{pmatrix}
= \begin{pmatrix} 0.00083 \\ \mathbf{0.17420} \\ 0.00083 \\ \mathbf{0.17420} \end{pmatrix}
$$

Branches 1 and 3 are nearly right; branches 2 and 4 — hanging from the **lifted** anchors — are 17 cm too long.

Four numbers, and all four must become zero. Branches 1 and 3 are nearly right; branches 2 and 4 — the ones hanging from the **lifted** anchors — are badly off.

#### 4 WISHES, 12 KNOBS

$$
\underbrace{4}_{\text{wishes}} \;\text{equations},\qquad \underbrace{12}_{\text{force densities}} \;\text{unknowns}
$$

There is no single answer. F.2 lets SciPy pick one."""
length_rows = [0, 1, 2, 3]                        # the four anchor branches
target_lengths = np.full(4, 1.2)                  # we want all four to be 1.2 m
g_lengths = l[length_rows] - target_lengths       # what is still wrong, one number per wish

print("wanted 1.2 m, got:", l[length_rows])
print("still wrong by:   ", g_lengths)


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `length_rows = [0, 1, 2, 3]` — **array indices** of the constrained branches, so branches 1–4 in Schek's numbering.
- `target_lengths = np.full(4, 1.2)` — four copies of 1.2 m.
- `l[length_rows]` — picks just those four lengths out of the twelve (NumPy "fancy indexing").
- the subtraction gives the error vector, one entry per wish.

</details>"""



# %% [f2] F.2 Finding the force densities with SciPy (sections 3.1 to 3.6)
r"""**Do this.** Hand the wish-error function to SciPy and let it search for the $q$ that zeroes it. The whole constrained solver is **one call**.

#### THE SHAPE OF THE LOOP

$$
\text{guess } q \;\longrightarrow\; \texttt{form\_finding}(q) \;\longrightarrow\; \text{lengths, forces} \;\longrightarrow\; \text{how wrong?}
$$

`least_squares` runs that loop for you, changing $q$ each time. It needs only the function that says **how wrong** the current $q$ is — F.1's $g$.

`least_squares` runs this loop for you. It needs only the function that says **how wrong** the current $q$ is — that is F.1's $g$.

#### THE TWO ARGUMENTS THAT MATTER

| argument | does | replaces |
|---|---|---|
| `still_wrong` | returns one number per wish | Schek's condition vector $g^{\ast}$ |
| `bounds=(1e-9, np.inf)` | keeps every $q_j$ positive — **a cable stays a cable** | Schek's sign guard |

SciPy's trust region does the rest: it takes a cautious step, checks whether things improved, and shortens the step if not. That is the same safeguard as Schek's damping, built in.

#### WITH OUR NUMBERS — WISH 1: four cables of 1.2 m

$$
\begin{array}{l|cccc}
 & q_1 & q_2 & q_3 & q_4 \\
\hline
\text{start} & 2.000 & 2.000 & 2.000 & 2.000 \\
\text{after 12 tries} & 1.972 & \mathbf{2.412} & 1.972 & \mathbf{2.412}
\end{array}
\qquad
l \longrightarrow \begin{pmatrix} 1.200 \\ 1.200 \\ 1.200 \\ 1.200 \end{pmatrix}
$$

Worst error $1.8 \times 10^{-8}$ m. Branches 2 and 4 were **too long**, so their $q$ went **up** to pull them in — Theorem 1 of E.1 at work.

Read what it decided: branches 2 and 4 were **too long**, so their $q$ went **up** (2.000 → 2.412) to pull them in — Theorem 1 of E.1 at work. Branches 1 and 3 drifted slightly down as the net rebalanced.

**$q$ is no longer an input here. It is the answer.**

#### WISH 2: lengths AND forces at the same time

Four spokes of 0.9 m **and** four anchor cables carrying exactly 2 kN:

$$
g = \begin{pmatrix} l_9 - 0.9 \\ l_{10} - 0.9 \\ l_{11} - 0.9 \\ l_{12} - 0.9 \\ s_1 - 2.0 \\ s_2 - 2.0 \\ s_3 - 2.0 \\ s_4 - 2.0 \end{pmatrix}
\begin{matrix} \left. \vphantom{\begin{matrix}a\\b\\c\\d\end{matrix}} \right\} \text{length wishes} \\[1.2em] \left. \vphantom{\begin{matrix}a\\b\\c\\d\end{matrix}} \right\} \text{force wishes} \end{matrix}
$$

After 22 tries: all four spokes at $0.900$ m, all four anchor forces at $2.000$ kN, worst error $7.5 \times 10^{-11}$. **Mixing costs nothing** — `np.r_[...]` just stacks the two kinds into one list.

Eight wishes of two different kinds, granted together. **Mixing costs nothing** — the two kinds are simply stacked into one list by `np.r_[...]`.

#### WHY SCIPY AND NOT THE 1974 METHOD

Schek derived the derivatives by hand and built a damped step, because in 1974 that was the only way. `least_squares` does the same job with a modern trust region. His literal scheme — equations (17) to (25) and the analytic Jacobians (31), (34), (35) — is implemented and checked in `examples/form_finding/schek_equations.py`."""
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


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `from scipy.optimize import least_squares` — the search routine.
- `def still_wrong(q):` — the heart of it. **Given a trial $q$, run the full linear solve of D.1, then report how far every wish is from granted.** All zeros means done.
- `np.r_[l[length_rows] - l_v, s[force_rows] - s_v]` — `np.r_` glues the length errors and the force errors into one list, so mixed wishes need no special handling.
- `least_squares(still_wrong, q_start, bounds=(1e-9, np.inf))` — searches for the $q$ that makes that list zero, never letting any $q_j$ reach zero.
- `found.x` — the $q$ it settled on. `found.nfev` — how many trial $q$ it tried. `found.fun` — the final errors.
- The last `form_finding` call re-runs the solver once on the winning $q$ to return the shape, lengths, forces and reactions.

**ALWAYS READ THE RETURNED ERROR.** A shape comes back whether or not the wishes were granted. Only the error number tells you which happened.

</details>"""



# %% [f3] F.3 The Jacobian: how each wish reacts to each q (sections 3.2 to 3.5)
r"""**Do this.** Look at what the solver feels its way with: a table of **sensitivities**, one row per wish, one column per knob.

$$
G^{t} := \frac{\partial g^{\ast}}{\partial q}
\qquad
\text{row } i,\ \text{column } j: \;\; \frac{\partial\,(\text{wish } i)}{\partial\,q_j}
$$

*Read it as: a table of sensitivities — one row per wish, one column per knob.*

**A Jacobian is nothing more exotic than that.** And you can build it with no calculus at all: nudge one $q_j$, re-solve, see how much each length moved, divide by the nudge.

#### WITH OUR NUMBERS — 4 wishes × 12 branches

$$
G^{t} =
\begin{array}{r|rrrr|rrrr|rrrr}
 & b_1 & b_2 & b_3 & b_4 & b_5 & b_6 & b_7 & b_8 & b_9 & b_{10} & b_{11} & b_{12} \\
\hline
w_1 & \mathbf{-0.313} & 0.002 & 0.073 & 0.002 & 0.139 & 0.139 & 0.023 & 0.023 & 0.000 & 0.109 & 0.000 & 0.051 \\
w_2 & 0.002 & \mathbf{-0.358} & 0.002 & 0.044 & 0.016 & 0.144 & 0.144 & 0.016 & 0.037 & 0.000 & 0.113 & 0.000 \\
w_3 & 0.073 & 0.002 & \mathbf{-0.313} & 0.002 & 0.023 & 0.023 & 0.139 & 0.139 & 0.000 & 0.051 & 0.000 & 0.109 \\
w_4 & 0.002 & 0.044 & 0.002 & \mathbf{-0.358} & 0.144 & 0.016 & 0.016 & 0.144 & 0.113 & 0.000 & 0.037 & 0.000
\end{array}
$$

**Three things to read off it:**

1. **Diagonal is big and negative.** Raise $q_1$ by one unit → branch 1 gets about 0.31 m **shorter**. Negative = shorter = Theorem 1 of E.1, as a number.
2. **Off-diagonal is small and positive.** Tightening one cable lets the others lengthen slightly. Weak coupling.
3. **Some entries are exactly zero** ($w_1$, $b_9$). Branch 9 joins nodes 4 and 5; by symmetry, changing its $q$ does not touch branch 1 at all.

#### WHAT SCHEK DID INSTEAD

He derived this table by hand. Differentiating equilibrium implicitly gives equation (28),

$$
\frac{\partial x}{\partial q} = -D^{-1} C^{t} U
$$

*Read it as: how far every free node moves when one force density is nudged.* For the heights, with our numbers:

$$
\frac{\partial z}{\partial q} =
\begin{array}{r|rrrr}
 & q_1 & q_2 & q_3 & q_4 \\
\hline
n_1 & -0.012 & 0.060 & -0.003 & 0.060 \\
n_2 & -0.004 & \mathbf{0.175} & -0.004 & 0.041 \\
n_3 & -0.003 & 0.060 & -0.012 & 0.060 \\
n_4 & -0.004 & 0.041 & -0.004 & \mathbf{0.175} \\
n_5 & -0.006 & 0.084 & -0.006 & 0.084
\end{array}
\;\cdots
$$

Row $n_2$, column $q_2$ is $+0.175$: raise branch 2's force density by 1 kN/m and node 2 rises about 0.175 m. It is the largest in that column, and branch 2 is the cable node 2 hangs from. Column $q_1$ is all **negative** (branch 1 runs down to anchor 6); column $q_2$ all **positive** (branch 2 runs up to lifted anchor 7). **The table knows the geometry.**

The chain rule turns (28) into the length Jacobian (31), the force Jacobian (34) and the unstrained-length Jacobian (35). **Those analytic formulas agree with the nudging table above to 3 decimals** — checked in `schek_equations.py`. You do not need them to use the method; you need them to understand why it is fast."""
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


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `base = form_finding(...)[1][rows]` — the lengths of the watched branches at the current `q`. The `[1]` picks the second return value, `l`.
- `G_t = np.zeros((len(rows), len(q)))` — the empty `(4, 12)` table.
- `q_nudged = q.copy(); q_nudged[j] += step` — change **one** force density by 0.000001. `.copy()` matters: without it you would damage the original `q`.
- `(... - base) / step` — change in length divided by change in `q`. That is the definition of a derivative, done with numbers.
- `G_t[:, j] = ...` — write it into **column** `j`.

**COST:** one extra solve per branch. For 12 branches that is nothing; for the 112-bar net of G.5 it is still only 112 small solves per step.

</details>"""



# %% [g1] G.1 The network of figure 5 (section 5)
r"""**Do this.** Build the paper's bigger network as data, same free-nodes-first rule. **The solver does not change at all.**

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

| | |
|---|---|
| **Given by the paper** | topology, the three $q$ values, "a small vertical load" |
| **Chosen here** | 0.04 m per pixel of the scan, apex 16 m above the corners, load 0.4 kN down at every free node |

Treat the figures below as faithful **reconstructions**, not reproduced measurements."""

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


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `FIG5_PX` — plan position of each of the 67 nodes read off the printed figure, in pixels. `* np.array([0.04, -0.04])` scales to metres and flips $y$ (image rows count down); `xy -= xy[66]` moves the apex (node 67, index 66) to the origin.
- `ring(nodes)` — turns a node list into the closed chain of branches between consecutive ones. The `seen` loop collects each branch once, giving 110.
- `q5` — `100` to border branches, `0.5` to any branch containing node 67, `1.0` to the rest: the paper's prescription as one list comprehension.
- `p5` — the `(61, 3)` load table, `-0.4` in every $z$. `anchors5(...)` — the `(6, 3)` anchor table.
- `is_spoke`, `is_border`, `touches_border` — **boolean masks** over the 110 branches, arrays of `True`/`False`. `l[is_spoke]` picks out the ten radial lengths.
- `keep(name, ...)` — stores a finished shape for the figure renderer, stacking 61 free + 6 fixed rows into one `(67, 3)` table.

</details>"""



# %% [g2] G.2 Figure 6: different fixed points
r"""**Do this.** Run the same solver with three support layouts. Only $x_f, y_f, z_f$ change, so **only the right-hand side is rebuilt** — D.2's cheap loop, now on a 61-node system.

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

The radial lengths spread wider as the apex slides off centre — cables on the far side must stretch to reach it. But the **apex reaction stays at 38.9 kN in all three**. Dragging the high point sideways redistributes geometry without changing how much total force the apex carries, because $q$ and the loads were never touched."""
# figure 6: different fixed points (the apex moved in plan): only the right-hand sides change
for name, (dx, dy) in zip(["fig6_1", "fig6_2", "fig6_3"], [(0, 0), (6, 2), (12, 4)]):
    xyz, l, s_, R = form_finding(branches5, free5, anchors5(dx, dy), q5, p5)
    keep(name, branches5, xyz, anchors5(dx, dy), fixed5)
    print(f"{name}: apex moved by ({dx}, {dy}) m; radial lengths {l[is_spoke].min():.1f}-{l[is_spoke].max():.1f} m; apex reaction {R[5, 2]:.1f} kN")
keep("fig1", *(lambda r: (branches5, r[0], anchors5(), fixed5))(form_finding(branches5, free5, anchors5(), q5, p5)))


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `form_finding(branches5, free5, anchors5(dx, dy), q5, p5)` — D.1 on the big net. Internally `D` is now `(61, 61)`; nothing else differs.
- `l[is_spoke]` — the boolean mask picks the ten radial lengths out of 110.
- `R[5, 2]` — the $z$ reaction at the sixth fixed node, the apex.
- `keep(name, ...)` — stores each shape so the figures render from computed data.

</details>"""



# %% [g3] G.3 Figures 7 and 8: changing the force densities
r"""**Do this.** Keep supports and loads fixed. Change the **radial** $q$, then the **border** $q$. $D$ is rebuilt each time — D.1's second loop.

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

**BONUS:** with $q = 1$ everywhere, fig. 8.3 is also the net with the minimal sum of squared branch lengths — Theorem 1 of E.1 with all weights equal."""
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


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `np.where(is_spoke, qs, q5)` — builds a **copy** of `q5` with every radial branch replaced by `qs`, everything else untouched.
- `np.where(is_border, qb, q5)` — the same for the border.
- Everything else is the plain D.1 call. Because `q` changed, `form_finding` rebuilds `D` and `D_f` internally.

</details>"""



# %% [g4] G.4 Figure 9: additional distance conditions
r"""**Do this.** Apply length wishes to the big network with F.2's solver. **Read the returned error** — a shape comes back either way.

> **No figure here yet.** The stored fig. 9 images showed the *stalled* shapes of the
> old solver, so they were removed. Regenerate them with
> `python examples/form_finding/schek_app.py` then `bash examples/form_finding/render_figures.sh`.
> The numbers below are current.

#### THE WISHES

Every branch not touching the border gets a prescribed length: 6 m for the radials, a fixed multiple of its fig. 6.1 length for the rings.

$$
\underbrace{62}_{\text{wishes}} \;\text{equations},\qquad \underbrace{110}_{\text{branches}} \;\text{knobs},\qquad D \text{ is } 61 \times 61
$$

#### WITH OUR NUMBERS

| run | radial target | ring factor | tries | worst error |
|---|---|---|---|---|
| fig9_1 | 6.0 m | ×1.25 | 42 | 1.2e-09 |
| fig9_2 | 6.0 m | ×0.85 | 35 | 1.1e-09 |
| fig9_3 | 4.5 m | ×0.70 | 58 | 7.5e-10 |

All three granted, to about a nanometre.

#### A NOTE ON SOLVERS

Schek's own 1974 damped scheme **stalls on runs 9.1 and 9.3**, stopping with a 1.2 m error, and the paper warns that "a damped sequence may stop at a shape which fulfils the conditions as close as physically possible". SciPy's trust region reaches all three.

**The conditions were attainable; the 1974 iteration simply could not get there.** Failure to converge never proves a wish impossible — it only means that solver did not find it."""
# figure 9: distance conditions on all branches not connected with the border (section 3)
base_l = form_finding(branches5, free5, anchors5(), q5, p5)[1]
inner = [j for j in range(len(branches5)) if not touches_border[j]]
for name, (l_radial, ring_factor) in zip(["fig9_1", "fig9_2", "fig9_3"], [(6.0, 1.25), (6.0, 0.85), (4.5, 0.70)]):
    l_v = [l_radial if is_spoke[j] else base_l[j] * ring_factor for j in inner]
    q_k, xyz, l, s_, tries, err = fit_force_densities(branches5, free5, anchors5(), q5, p5, length_rows=inner, l_v=l_v)
    keep(name, branches5, xyz, anchors5(), fixed5)
    print(f"{name}: radial l = {l_radial} m, rings x{ring_factor}: worst length error {err:.1e} after {tries} tries"
          + ("  (NOT solved)" if err > 1e-6 else ""))


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

- `base_l = form_finding(...)[1]` — lengths of the unconstrained fig. 6.1 net, the reference for the ring targets. `[1]` picks `l`.
- `inner = [j for j in range(len(branches5)) if not touches_border[j]]` — indices of every branch touching no border node. These are the wish rows.
- `l_v = [l_radial if is_spoke[j] else base_l[j] * ring_factor for j in inner]` — one target per wish: a flat 6 m for radials, a multiple of the base length for rings.
- `fit_force_densities(..., length_rows=inner, l_v=l_v)` — F.2 with 62 length wishes.
- `err` is the worst remaining wish error; the printed line appends `(NOT solved)` if it exceeds `1e-6`.

</details>"""



# %% [g5] G.5 Figure 10: the grid-shell model of 112 identical bars
r"""**Do this.** Generate a grid topology, renumber so the four supports come last, put half of each bar's weight at each end, then run three cases.

> **No figure here yet.** Case 10.3 changed with the new solver, so the stored fig. 10
> images no longer match all three panels and were removed. Regenerate with
> `python examples/form_finding/schek_app.py` then `bash examples/form_finding/render_figures.sh`.
> The numbers below are current.

#### 8 × 8 NODES, 112 BARS

| case | supports | load | wishes | models |
|---|---|---|---|---|
| **10.1** | 4 corners pulled in to 80 % of span | bar self-weight | all 112 bars = 1.0 m | a **hanging** net of identical bars |
| **10.2** | two opposite corners raised to 3 m | none | none — linear solve only | a **prestressed** net, inner $q=1$, border $q=10$ |
| **10.3** | as 10.2 | none | inner bars one common length; border-touching bars one common force | **mixed** wishes |

#### WITH OUR NUMBERS

| case | result | note |
|---|---|---|
| **10.1** | worst length error $7.5\times10^{-10}$ after 11 tries | bar forces **0.12 – 2.77 kN**, a 23× spread |
| **10.2** | inner lengths 0.65 – 0.81 m | linear solve only |
| **10.3** | worst error $1.3\times10^{-8}$ after 38 tries | both wish kinds at once |

**Case 10.1 is the striking one.** Every bar is exactly 1.0 m — the net is geometrically uniform — yet the forces run from 0.12 to 2.77 kN. Bars near the corners carry everything hanging below them; bars at the free edge carry almost nothing.

**EQUAL GEOMETRY DOES NOT MEAN EQUAL FORCE.** That is exactly why F.2 offers force wishes as well as length wishes — and case 10.3 asks for both at once, on different groups of bars, and gets them."""
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


# %% explain
r"""<details>
<summary><b>Line by line</b> — click to open</summary>

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

</details>"""



# %% [export] Export computed shapes for figure generation
r"""Optional export of computed coordinates and connectivity for figure generation."""
import json
from pathlib import Path
keep("fig5_plan", branches5, np.c_[xy[:61], np.zeros(61)], np.c_[xy[61:], np.zeros(6)], fixed5)
out = Path(__file__).resolve().parent / "viewer_scenes/json/shapes.json" if "__file__" in dir() else Path("viewer_scenes/json/shapes.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(shapes))
print(f"{len(shapes)} shapes written to {out.name}; schek_1974_figures.py draws them")


# %% explain
r"""**Reading the code.** `shapes` maps a figure name to its branch list, its $(n_s \times 3)$ coordinate table and the fixed nodes; `json.dumps` writes it as text. The file is the only link between this program and the drawings."""


