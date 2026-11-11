---
name: force-density-notebooks
description: How a force density method notebook is written so all notebooks stay consistent. Names of nodes and bars, colours, how the question is stated, section order, code conventions and the viewer. Use when writing or changing any notebook in force_density_method/notebooks.
---

# Force density notebooks

Every notebook follows the teaching notebook `05-solvers_05-force-density-linkwitz.ipynb`.
The four exercises in `../notebooks/` are the worked examples of this guide.

## Names

| Thing | Name | Notes |
| --- | --- | --- |
| node | $n_0, n_1, \ldots$ | never `p0`; free nodes first when the net is small |
| bar | $e_0, e_1, \ldots$ | never `a, b, c, d` |
| load | $p$ with $p_x, p_y, p_z$ | on free nodes only |
| force density | $q$, matrix $Q$ | kN/m, one per bar |
| bar force, length | $f$, $l$ | $f = q\,l$ |
| connectivity | $C$, split in $C_N$ (free) and $C_F$ (fixed) | $1$ at the first node of a bar, $-1$ at the second |
| coordinates | $x_N, y_N, z_N$ free and $x_F, y_F, z_F$ fixed | m |
| coordinate differences | $u, v, w$ | $u = C\,x$ |

Units are always written: m, kN, kN/m.

## Colours

The same three colours in formulas, figures and the viewer.

| Meaning | Hex | LaTeX | Viewer |
| --- | --- | --- | --- |
| free node | `#d62828` | `{\color{#d62828} n_0}` | `RED = Color(0.84, 0.16, 0.16, 1.0)` |
| fixed node | `#2a6fdb` | `{\color{#2a6fdb} n_1}` | `BLUE = Color(0.16, 0.44, 0.86, 1.0)` |
| load | `#2e9e4a` | `{\color{#2e9e4a} p}` | `GREEN = Color(0.18, 0.62, 0.29, 1.0)` |

Colour a symbol every time it appears in the text, not only the first time.

## Order of a notebook

1. `# Exercise NN Title`. The title is the file name: `exercise_02_force_densities.ipynb` gives
   `# Exercise 02 Force densities`.
2. `# Question`. One bold question, then the given data, then the figure, then the tasks as a
   short list, then `Needs: pip install numpy session-jupyter`, then a horizontal rule.
3. `# Network`. One code cell with the given data.
4. One section per step. A markdown cell with the formula, then the code cell that computes it.
5. `# Viewer` when there is a picture.
6. `# Observation`. What the numbers show, in two or three sentences.

Section titles are level one headings in title case: `# Sum of Forces`, `# Change the Loads`.

## The question

State the given data exactly like this. One display formula per fixed node and per load, in its colour:

```
Fixed nodes:
$$ \color{#2a6fdb}{n_1 \, (0, 0, 0) \text{ m}} $$
$$ \color{#2a6fdb}{n_2 \, (5, 0, 3) \text{ m}} $$

Load on the free node:
$$ \color{#2e9e4a}{p \, (0, 0, -5) \text{ kN}} $$

The force density:
$$ q = \frac{\text{force in the edge}}{\text{edge length}} = [1, 1, 1, 1] \text{ kN/m} $$
```

The connectivity matrix is shown with its node labels on top and bar labels on the left:

```
$$
\newcommand{\cell}[1]{\hphantom{-}\mathclap{#1}\hphantom{-}}
\begin{array}{rcc}
 & & \begin{matrix} \cell{n_0} & \cell{n_1} & \cell{n_2} \end{matrix} \\[2pt]
C = & \begin{matrix} e_0 \\ e_1 \end{matrix} &
\left[ \;
\begin{matrix}
\cell{1} & \cell{-1} & \cell{0} \\
\cell{1} & \cell{0} & \cell{-1}
\end{matrix}
\; \right]
\end{array}
$$
```

A grid is shown as a text picture with its node names. A big matrix shows its first rows and dots.

## Figures

Figures are the SVG files in `BRG-teaching/Teaching/CAS/logos/`, full width, centred, with a caption:

```html
<div align="center">
  <img src="https://raw.githubusercontent.com/BRG-teaching/Teaching/main/CAS/logos/fd_one_node.svg"
       style="width:100%; height:auto;"
       alt="Free node n0 with bars e0 to e3 to fixed nodes n1 to n4 and load p" />
  <p style="text-align:center;">
    <em>The free node n<sub>0</sub> connected by bars e<sub>0</sub> to e<sub>3</sub> to the fixed nodes.</em>
  </p>
</div>
```

Existing figures: `fd_equilibrium`, `fd_one_node`, `fd_projections`, `fd_1d`,
`fd_coordinate_difference`, `fd_projection_all_axes`. Reuse one before drawing a new one.
The rule between the question and the solution is
`<hr style="border: none; border-top: 2px solid #555; margin: 2em 0;">`.

## Code

Flat numpy, in this order, with these comments:

```python
import numpy as np

# connectivity: rows = bars e0..e3, columns = nodes n0..n4
C = np.array([
    [1, -1,  0,  0,  0],
    [1,  0, -1,  0,  0],
    [1,  0,  0, -1,  0],
    [1,  0,  0,  0, -1],
])

free  = [0]            # n0
fixed = [1, 2, 3, 4]   # n1..n4

C_N = C[:, free]
C_F = C[:, fixed]

# fixed node coordinates (n1..n4)
x_F = np.array([0, 5, 0, 7])
y_F = np.array([0, 0, 7, 5])
z_F = np.array([0, 3, 3, 0])

# force densities, one per bar
q = np.array([1, 1, 1, 1])
Q = np.diag(q)

# loads on the free node
p_x = np.array([0])
p_y = np.array([0])
p_z = np.array([-5])

# equation 6.32
A = C_N.T @ Q @ C_N
x_N = np.linalg.solve(A, p_x - C_N.T @ Q @ C_F @ x_F)
y_N = np.linalg.solve(A, p_y - C_N.T @ Q @ C_F @ y_F)
z_N = np.linalg.solve(A, p_z - C_N.T @ Q @ C_F @ z_F)
```

- The solve is always the three lines under `# equation 6.32` (Linkwitz), never rewritten in another form.
- A grid keeps all nodes in `x, y, z` and writes the result with `x[free] = ...`.
- Bar lengths are `np.sqrt((C @ x)**2 + (C @ y)**2 + (C @ z)**2)`, bar forces `f = q * l`.
- No lambdas, no classes, no type hints. A function only when the same steps run several times,
  with a one line docstring.
- Printed results carry their unit: `print("bar forces =", np.round(f, 2), "kN")`.
- The markdown cell before a code cell shows the formula the code computes.

## Viewer

Pictures come from the session viewer, never matplotlib. See the repository skill
`skills/session-viewer-notebook/SKILL.md` for the call and its rules.

```python
from session_py import Color, Matrix, Session
from session_jupyter import show

session = Session("fdm_exercise_2")
session.add_network(Matrix.from_rows(C.tolist()), Matrix.from_rows(np.column_stack([x, y, z]).tolist()))

# node colours
for k in range(len(x)):
    point = session.objects.points[k]
    point.pointcolor = RED if k in free else BLUE
    point.width = 12.0

show(session, "fdm_exercise_2")
```

- Free nodes red, fixed nodes blue, a load a green line with `Arrowhead.END`.
- Bars are gray or black. When bars show their force, darker means a bigger force. Never colour
  bars red, blue or green: those colours belong to nodes and loads.
- Scene names are `fdm_<notebook>_<step>`, for example `fdm_exercise_4_load`.
- The matrix $C$ can sit beside the net with `session.add_matrix(matrix)`.

## Writing

- Short sentences, plain words. One idea per sentence.
- No em or en dashes anywhere. Use a full stop or a colon.
- Bold only for the question and for one key finding.
- Every number says its unit. Every formula uses the names and colours above.
- State what the reader should try next in the last cell.

## Before a notebook is done

1. Run it top to bottom with the released packages: `pip install numpy session-jupyter`.
2. No error outputs, no dashes, names and colours as above.
3. Open each viewer scene in a browser and look at it.
