"""Generate knowledge/04_form_finding/force_density_linkwitz.ipynb from linkwitz_app.py.

Each `# %% ID title` cell of linkwitz_app.py becomes a markdown cell (the book section, its equation and the
numbers of the single node) followed by a code cell. The notebook is executed so every output is stored.

    python examples/form_finding/build_linkwitz_notebook.py          # build and execute
    python examples/form_finding/build_linkwitz_notebook.py --fast   # build without executing
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE / "linkwitz_app.py"
OUT = HERE.parents[1] / "knowledge/04_form_finding/force_density_linkwitz.ipynb"

INTRO = r"""# Force Density Method

A runnable walk through K. Linkwitz, *Force density method: design of a timber shell*, Chapter 6 of
*Shell Structures for Architecture* (Routledge 2014), in the order of the book's sections, with every equation
computed on the chapter's own example: one free node $P_0$ held by four bars $a, b, c, d$ to the anchors of
exercise 2 (p. 68),

$$
P_1 (0, 0, 0), \quad P_2 (5, 0, 3), \quad P_3 (0, 7, 3), \quad P_4 (7, 5, 0), \qquad q = 1 \text{ kN/m in every bar}, \qquad p_z = -5 \text{ kN}.
$$

**Run the cells in order.** Each section first states the book's equation, then the same equation with the
numbers, then the code and its output. The companion in Schek's notation (9-node net) is [compas_fd.ipynb](compas_fd.ipynb).

| Linkwitz | Schek / compas_fd | meaning |
|---|---|---|
| $\mathbf C = [\mathbf C _ N \ \mathbf C _ F]$ | $C_s = [C \mid C_f]$ | branch-node matrix, free and fixed columns |
| $\mathbf x _ N, \mathbf x _ F$ | $\mathbf x, \mathbf x _ f$ | free and fixed coordinates |
| $\mathbf f$, $\mathbf q = \mathbf L^{-1} \mathbf f$ | $\mathbf s$, $\mathbf q = \mathbf s / \mathbf l$ | bar forces and force densities |
| $\mathbf D _ N$, $\mathbf D _ F$ | $D$, $D_f$ | the two tables of force densities that make up the system of equations (one row per free node): $\mathbf D _ N$ free–free (diagonal = $q$'s at the node, off-diagonal = $-q$ of the bar between two free nodes), $\mathbf D _ F$ free–anchor ($-q$ of the bar to that anchor) |
| $\mathbf D _ N \mathbf x _ N = \mathbf p - \mathbf D _ F \mathbf x _ F$ (6.31) | $D \mathbf x = \mathbf p _ x - D_f \mathbf x _ f$ | the linear system |
"""

# Markdown text per cell id: the book's equation and the single-node numbers.
MD = {
"A.1": r"""## § 6.2.1 A single node in equilibrium

Fig. 6.4 of the book: node $P_0$ connected to four fixed points $P_1 \ldots P_4$ by bars $a, b, c, d$, with a load $p_z$.
The numbers are those of exercise 2 (p. 68). The load vector is $\mathbf p = (0, 0, -5)$ kN: gravity acts in $-z$.
$P_0$ is unknown; the method will find $P_0 = (3, 3, 0.25)$.

![Fig. 6.4 — the single node P0 with the four bars a, b, c, d to P1 … P4 and the load p_z](https://pub-c082064d3c234b25bcb6abd4240e637c.r2.dev/force-density-linkwitz/notes/images/fig6-4-node.jpg)

*Figure 6.4 of the book: a single node with four forces and a load.*""",
"B.1": r"""## § 6.2.2 Translation to equations

**Equation (6.2)** — every bar is as long as the distance between its end points, so the four lengths are a function of the unknown $P_0$:

$$
l_i = \sqrt{(x_k - x_0)^2 + (y_k - y_0)^2 + (z_k - z_0)^2}, \qquad k = 1, 2, 3, 4
$$

At a guess $P_0 = (3, 3, 1)$: $l_a = \sqrt{9 + 9 + 1} = 4.359$ m.""",
"B.2": r"""**Equations (6.4)–(6.6)** — the pull $F_i$ of a bar acts along the bar; its $x$-part is $F_i \cos \alpha_i$ with the direction cosine
"coordinate difference ÷ distance in space". Equilibrium of the four parts and the load, in each direction:

$$
\frac{x_1 - x_0}{l_a} F_a + \frac{x_2 - x_0}{l_b} F_b + \frac{x_3 - x_0}{l_c} F_c + \frac{x_4 - x_0}{l_d} F_d + p_x = 0
$$

The code evaluates the left side as a residual: zero means equilibrium. At the guess with $F = 1$ kN (exercise 1) it is $-4.59$ kN in $z$: four pulls of 1 kN lift only $0.41$ kN against 5 kN.""",
"B.3": r"""## § 6.2.3 Force densities

$x_0$ sits inside the square roots: (6.6) is nonlinear. **Equation (6.10)** defines the force density $q_i := F_i / l_i$; then (6.6) becomes **(6.11)**, linear in $x_0$, and **(6.13)** solves it:

$$
(x_1 - x_0) q_a + \ldots + (x_4 - x_0) q_d + p_x = 0
\qquad \Longrightarrow \qquad
x_0 = \frac{p_x + x_1 q_a + x_2 q_b + x_3 q_c + x_4 q_d}{q_a + q_b + q_c + q_d}
$$

$$
x_0 = \frac{0 + 0 + 5 + 0 + 7}{4} = 3, \qquad y_0 = \frac{0 + 0 + 0 + 7 + 5}{4} = 3, \qquad z_0 = \frac{-5 + 0 + 3 + 3 + 0}{4} = 0.25
$$

Afterwards the pulls follow from the shape, $F_k = q_k l_k$ (6.33), and the residual of (6.6) is exactly zero.""",
"B.4": r"""Doubling $q$ in bars $b$ and $d$ moves the node towards $P_2$ and $P_4$; the formula is unchanged, only the weights:

$$
x_0 = \frac{0 + 0 \cdot 1 + 5 \cdot 2 + 0 \cdot 1 + 7 \cdot 2}{1 + 2 + 1 + 2} = 4
$$""",
"B.5": r"""If the *forces* are prescribed instead (exercise 1), $q_k = F_k / l_k$ changes with the geometry and (6.13) must be iterated.
With $F = 2$ kN it converges; with $F = 1$ kN it never does — four forces of 1 kN pull upwards with at most 4 kN together,
so no position balances 5 kN. That is the observation the exercise asks for, and the reason the chapter prescribes $q$.""",
"C.1": r"""## § 6.4 Notation

A vector is a one-column matrix; $\mathbf A = \mathrm{diag}(\mathbf a)$ puts it on a diagonal. The only purpose of the diagonal
matrices in this chapter is to write an element-by-element product of two vectors as a matrix product:

$$
\mathbf U \mathbf q = \mathbf Q \mathbf u = (u_k q_k)
$$""",
"C.2": r"""## § 6.4.1 Branch-node matrix

**Equation (6.14)** — one row per bar, one column per node; $+1$ at the node where the bar ends, $-1$ where it begins.
**Equations (6.16)–(6.17)** — $\mathbf u = \mathbf C \mathbf x$ subtracts, for every bar, the coordinates of its two end nodes:

$$
\begin{bmatrix}
+1 & -1 & 0 & 0 & 0 \\
+1 & 0 & -1 & 0 & 0 \\
+1 & 0 & 0 & -1 & 0 \\
+1 & 0 & 0 & 0 & -1
\end{bmatrix}
\begin{bmatrix}
3 \\
0 \\
5 \\
0 \\
7
\end{bmatrix} =
\begin{bmatrix}
3 \\
-2 \\
3 \\
-4
\end{bmatrix}
\begin{matrix}
\leftarrow a: \ x_0 - x_1 \\
\leftarrow b: \ x_0 - x_2 \\
\leftarrow c: \ x_0 - x_3 \\
\leftarrow d: \ x_0 - x_4
\end{matrix}
$$

The columns sum to zero, so $\mathbf C$ has rank $n - 1 = 4$ (the book prints "$m - 1$"). The book's (6.15) lists $x_k - x_0$, the
opposite sign of what (6.14) gives; the solution (6.32) does not depend on it.""",
"C.3": r"""**Equations (6.18)–(6.20)** — the first column of $\mathbf C$ belongs to the unknown node, the others to the fixed nodes:

$$
\mathbf C = [\mathbf C _ N \quad \mathbf C _ F], \qquad \mathbf x = [\mathbf x _ N \quad \mathbf x _ F], \qquad
\mathbf u = \mathbf C _ N \mathbf x _ N + \mathbf C _ F \mathbf x _ F = \begin{bmatrix}
1 \\
1 \\
1 \\
1
\end{bmatrix} [3] + (-\mathbf I) \begin{bmatrix}
0 \\
5 \\
0 \\
7
\end{bmatrix} = \begin{bmatrix}
3 \\
-2 \\
3 \\
-4
\end{bmatrix}
$$""",
"C.4": r"""**Equation (6.21)** — squaring a diagonal matrix squares its diagonal, so this is Pythagoras for all bars at once:

$$
\mathbf L = (\mathbf U^2 + \mathbf V^2 + \mathbf W^2)^{1/2} = \mathrm{diag}(4.250, \ 4.535, \ 5.706, \ 4.479)
$$""",
"D.1": r"""## § 6.4.2 Jacobian

**Equation (6.22)** names a function: feed in $x_0$, get out the four bar lengths,

$$
\mathbf f(x_0) = \begin{bmatrix}
l_a \\
l_b \\
l_c \\
l_d
\end{bmatrix}
$$

The Jacobian is the table of its derivatives: "stretch of each bar per metre of push of $x_0$". Before any formula the code
measures it: move $x_0$ by $\pm h$, divide the change of each length by $2h$.""",
"D.2": r"""**Equation (6.23)** — the chain rule on the square root gives the same numbers without pushing:

$$
\frac{\partial l_k}{\partial x_0} = \frac{-(x_k - x_0)}{l_k}, \qquad
\left( \frac{\partial \mathbf f}{\partial x_0} \right)^{\mathrm T} =
\begin{bmatrix} \dfrac{-(0 - 3)}{4.250} & \dfrac{-(5 - 3)}{4.535} & \dfrac{-(0 - 3)}{5.706} & \dfrac{-(7 - 3)}{4.479} \end{bmatrix} =
\begin{bmatrix} 0.706 & -0.441 & 0.526 & -0.893 \end{bmatrix}
$$

Each entry is the direction cosine of (6.4) with the sign flipped: moving $P_0$ towards $P_k$ shortens bar $k$.""",
"D.3": r"""**Equation (6.24)** — the same row assembled from the branch-node matrix:

$$
\left( \frac{\partial \mathbf f}{\partial \mathbf x} \right)^{\mathrm T} = \mathbf C _ N^{\mathrm T} \mathbf U \mathbf L^{-1} =
\begin{bmatrix} 1 & 1 & 1 & 1 \end{bmatrix} \mathrm{diag}\!\left( \frac{3}{4.250}, \frac{-2}{4.535}, \frac{3}{5.706}, \frac{-4}{4.479} \right)
$$

$\mathbf U \mathbf L^{-1}$ is "difference ÷ length" per bar; $\mathbf C _ N^{\mathrm T}$ collects the bars meeting at the free node into its row.
For $n_N$ free nodes this gives $n_N$ rows in one line. "The Jacobian corresponds exactly to the direction cosines of (6.6)."
""",
"D.4": r"""## § 6.4.3 Solution in matrix form

**Equation (6.25)** — (6.6) written with the Jacobian: force × direction cosine = force component, summed, plus the load:

$$
- \left( \frac{\partial \mathbf f}{\partial x_0} \right)^{\mathrm T} \begin{bmatrix}
F_a \\
F_b \\
F_c \\
F_d
\end{bmatrix} + p_x = 0
$$

The code checks it in $z$, where the load acts: bars $b$ and $c$ rise to $z = 3$ and carry $2.75$ kN each, bars $a$ and $d$ pull
$0.25$ kN the wrong way; net $5$ kN up against $5$ kN down.""",
"E.1": r"""**Equations (6.26)–(6.28)** — write the row as (6.24), then replace the forces by force densities (6.27), $\mathbf q = \mathbf L^{-1} \mathbf f$:
the lengths cancel.

$$
\mathbf C _ N^{\mathrm T} \mathbf W \mathbf L^{-1} \mathbf f \ \longrightarrow \ \mathbf C _ N^{\mathrm T} \mathbf W \mathbf q =
\begin{bmatrix} 1 & 1 & 1 & 1 \end{bmatrix} \begin{bmatrix}
0.25 \\
-2.75 \\
-2.75 \\
0.25
\end{bmatrix} = -5 = p_z
$$

Sign: with $\mathbf w = \mathbf C \mathbf z$ from (6.14) the sum equals $+\mathbf p$, so the equation reads $\ldots - \mathbf p = \mathbf 0$ (Schek's form), which leads to the
printed (6.31). The "$+ \mathbf p$" printed in (6.26)–(6.30) belongs to the other sign of $\mathbf u$ (6.15). The solution is the same either way.""",
"E.2": r"""**Equations (6.29)–(6.30)** — $\mathbf W \mathbf q = \mathbf Q \mathbf w = \mathbf Q \mathbf C \mathbf z$ (the diagonal swap), and the split of $\mathbf C \mathbf z$ into a free and a fixed part:

$$
\mathbf C _ N^{\mathrm T} \mathbf Q \mathbf C \mathbf z = \mathbf C _ N^{\mathrm T} \mathbf Q \mathbf C _ N \mathbf z _ N + \mathbf C _ N^{\mathrm T} \mathbf Q \mathbf C _ F \mathbf z _ F = -5
$$""",
"E.3": r"""**Equations (6.31)–(6.33)** — name the two matrices and move the known part to the right:

$$
\mathbf D _ N = \mathbf C _ N^{\mathrm T} \mathbf Q \mathbf C _ N = [4], \qquad
\mathbf D _ F = \mathbf C _ N^{\mathrm T} \mathbf Q \mathbf C _ F = [-1 \ \ -1 \ \ -1 \ \ -1]
$$

$$
\mathbf D _ N \mathbf z _ N = \mathbf p _ z - \mathbf D _ F \mathbf z _ F : \qquad 4 z_0 = -5 - (-1)(0 + 3 + 3 + 0) = 1 \qquad \Longrightarrow \qquad z_0 = 0.25
$$

This is the page-63 formula (6.13) in matrix clothes: the diagonal of $\mathbf D _ N$ collects the force densities meeting at each free node, $-\mathbf D _ F \mathbf x _ F$ the
neighbours' coordinates weighted by $q$. `np.linalg.solve` is the "$\mathbf A \mathbf x = \mathbf b$" of the book. (6.33) returns the forces, $\mathbf f = \mathbf L \mathbf q$.""",
"G.1": r"""## § 6.4.4 Generalization

Equation (6.32) holds for any net as long as $\mathbf C$ describes its topology. The book's exercise 3: the standard grid of Fig. 6.12,
$6 \times 6$ nodes at 2 m spacing, 60 bars. $\mathbf C$ is built from the list of bars exactly as in (6.14): $60 \times 36$, rank $35 = n - 1$.""",
"G.2": r"""The whole method as one function: split $\mathbf C$ by the list of fixed nodes, form $\mathbf D _ N$ and $\mathbf D _ F$, solve once per coordinate.
Checked first on the single node, where it must reproduce $P_0 = (3, 3, 0.25)$. A second function recomputes
$\sum_k q_k (x_k - x_i) + p_i$ at every node: zero at the free nodes, minus the support reaction at the fixed ones.""",
"G.3": r"""Exercise 4, three shapes: (a) boundary fixed flat, $q = 1$, $1$ kN down at the 16 interior nodes — a hanging net, $\mathbf D _ N$ is $16 \times 16$
with 4 on the diagonal and $-1$ for each bar between two free nodes; (b) only the four corners fixed, two of them at $z = 4$ m, edge bars $q = 5$
(the 5:1 ratio of Fig. 6.6a), no load — an anticlastic saddle; (c) as (b) with $1$ kN down at all 32 free nodes — a hanging net, upside down a shell.
Scaling $\mathbf q$ and $\mathbf p$ together leaves the shape unchanged (§ 6.7).""",
"G.4": r"""The solved node of § 6.2.3 and the three grids.""",
"F.1": r"""## § 6.5 Materialization

**Equations (6.34)–(6.37)** — the shape is independent of the material. Afterwards, for a chosen axial stiffness $EA$, the cutting length
of every bar follows from Hooke's law; all matrices are diagonal, so per bar

$$
\mathbf l _ 0 = (\mathbf I + (\mathbf{EA})^{-1} \mathbf Q \mathbf L)^{-1} \mathbf l \qquad \Longrightarrow \qquad
l _ {0,k} = \frac{l_k}{1 + q_k l_k / EA_k}, \qquad l _ {0,a} = \frac{4.250}{1 + 4.250 / 500} = 4.214 \text{ m}
$$

Each bar is cut about 1 % short; stretched into place it carries exactly $F = q l$. (The printed "$l_0 \lt 1$" on p. 66 means $l_0 \lt l$.)""",
}

OUTRO = r"""## Exercises (pp. 68–69), answered above

1. Forces of 1 kN with a 5 kN load: no equilibrium exists (§ 6.2.3, third cell).
2. $q = 1$: $P_0 = (3, 3, 0.25)$, forces $4.25, 4.53, 5.71, 4.48$ kN; $q = 2$ in $b, d$: $P_0 = (4, 2.83, 0.67)$ (§ 6.2.3).
3. Branch-node matrix of Fig. 6.12: $60 \times 36$ (§ 6.4.4, first cell).
4. Shaping a shell: raise the corners, change the edge-to-interior ratio of $\mathbf q$, add $\mathbf p _ z$ (§ 6.4.4, third cell).
"""


def _cell_id(tag: str) -> str:
    return hashlib.sha256(tag.encode()).hexdigest()[:8]


def md_cell(tag: str, text: str) -> dict:
    return {"cell_type": "markdown", "id": _cell_id(tag), "metadata": {}, "source": text.strip("\n") + "\n"}


def code_cell(tag: str, code: str) -> dict:
    return {"cell_type": "code", "id": _cell_id(tag), "metadata": {}, "execution_count": None, "outputs": [],
            "source": code.strip("\n") + "\n"}


def cells() -> list[tuple[str, str, str]]:
    text = APP.read_text()
    out = []
    for chunk in re.split(r"^# %% ", text, flags=re.M)[1:]:
        head, body = chunk.split("\n", 1)
        cid, title = head.split(" ", 1)
        out.append((cid, title.strip(), body.strip("\n")))
    return out


def build() -> dict:
    nb_cells = [md_cell("intro", INTRO)]
    for cid, title, code in cells():
        nb_cells.append(md_cell("md-" + cid, MD[cid] + f"\n\n*Cell {cid} — {title}*"))
        nb_cells.append(code_cell("code-" + cid, code))
    nb_cells.append(md_cell("outro", OUTRO))
    return {
        "cells": nb_cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    import json
    nb = build()
    if "--fast" not in sys.argv:
        import nbformat
        from nbclient import NotebookClient
        node = nbformat.from_dict(nb)
        NotebookClient(node, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(HERE)}}).execute()
        nb = json.loads(nbformat.writes(node))
    OUT.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
    n_out = sum(len(c.get("outputs", [])) for c in nb["cells"] if c["cell_type"] == "code")
    print(f"wrote {OUT} ({len(nb['cells'])} cells, {n_out} outputs)")


if __name__ == "__main__":
    main()
