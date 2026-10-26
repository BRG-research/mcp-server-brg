"""Generate the Jupyter notebook knowledge/04_form_finding/compas_fd.ipynb from schek_app.py.

Same source of truth as build_note.py: each `# %% [id] title` cell of schek_app.py becomes
a markdown cell (its prose), a code cell (the implementation) and a markdown cell (its
concise code note). The notebook is executed in-process so every output is stored in it
and you can read the results without running anything.

    python examples/form_finding/build_notebook.py          # build and execute
    python examples/form_finding/build_notebook.py --fast   # build without executing
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_note import PARTS_TITLES, cells  # noqa: E402

APP = HERE / "schek_app.py"
OUT = HERE.parents[1] / "knowledge/04_form_finding/compas_fd.ipynb"

INTRO = r"""# Force Density Method (FDM) — Schek (1974) & Linkwitz (2014), Step by Step

A runnable version of [compas_fd.md](compas_fd.md). **Run the cells in order**: each section pairs the general equation with its **physical & geometric meaning on the cable net**, visual diagrams, and an explicit numerical matrix example from our 12-branch, 9-node benchmark net.

![Physical and geometric foundation of the Force Density Method](images/fd_linkwitz_intuition.png)

* **Single-Node Equilibrium & Force Density (Linkwitz 2014, Sec. 6.2, Fig. 6.4):** Projecting 3D cable tension $s_j$ onto the $x$-axis uses the direction cosine $\cos\alpha_j = u_j / l_j = (x_i - x_k) / \sqrt{u_j^2+v_j^2+w_j^2}$. Prescribing the **force density** $q_j = s_j / l_j$ ($\text{kN/m}$) cancels the nonlinear length $l_j$ out of the denominator ($F_{x,j} = q_j u_j = q_j(x_i - x_k)$), so every free node $P_0$ settles at the **$q$-weighted average of its neighbors**:

$$
q_j = \frac{s_j}{l_j}, \qquad x_0 = \frac{p_x + q_a x_1 + q_b x_2 + q_c x_3 + q_d x_4}{q_a + q_b + q_c + q_d}
$$

* **Materialization (Linkwitz Sec. 6.5, Eq. 6.37):** Form-finding solves for geometry $\mathbf{l}$ and forces $\mathbf{s} = Q\mathbf{l}$ without material stiffness $EA$; afterwards, choosing $EA_j$ gives the unstressed workshop **cutting length**:

$$
l_{0,j} = \frac{l_j}{1 + s_j / EA_j}
$$

| Milestone | What you can do |
|---|---|
| **A.1–A.4** | Represent a network as a branch-node matrix and trace $C^T Q C$ step by step. |
| **B.1–B.3** | Compute branch coordinate differences $(u_j, v_j, w_j)$, lengths $l_j$, and the 4-stage nonlinear equilibrium residual. |
| **C.1–C.4** | Apply the force-density substitution $q_j = s_j / l_j$, assemble $D$ and $D_f$, solve coordinates, recover forces, and compute cutting lengths $\mathbf{l}_0$. |
| **D.1–D.2** | Package the 3D linear solver and support reactions $\mathbf{R}_f$, and test anchor shifts, stiffness ratios, and $(\mathbf{q}, \mathbf{p})$ scale invariance. |
| **E.1** | Interpret $q_j$ geometrically as a spring-energy weight minimizing $\sum q_j l_j^2$. |
| **F.1–F.3** | Enforce target branch lengths and forces via constrained least-squares and the sensitivity Jacobian $G^T$. |
| **G.1–G.5** | Apply the same solver to Schek's 67-node pointed tent and 112-bar grid-shell benchmarks. |

## Master symbol, shape & geometric meaning reference

| Symbol | Code | Shape | Physical & Geometric Meaning on the Cable Net |
|---|---|---|---|
| $C_s = [C \mid C_f]$ | `C_s`, `C`, `C_f` | `(12, 9)` = `(12, 5)` \| `(12, 4)` | Branch-node connectivity matrix: row $j$ has $+1$ at start node $i$ and $-1$ at end node $k$ |
| $C^T$ | `C.T` | `(5, 12)` | Nodal force collector: row $i$ sums cable force components meeting at free node $i$ |
| $\mathbf{x}, \mathbf{y}, \mathbf{z}$ | `x, y, z` | `(5,)` | Unknown 3D coordinates ($\text{m}$) of the 5 free interior nodes ($1 \dots 5$) |
| $\mathbf{x}_f, \mathbf{y}_f, \mathbf{z}_f$ | `x_f, y_f, z_f` | `(4,)` | Known 3D coordinates ($\text{m}$) of the 4 fixed boundary anchors ($6 \dots 9$) |
| $\mathbf{p}_x, \mathbf{p}_y, \mathbf{p}_z$ | `p_x, p_y, p_z` | `(5,)` | Known external loads ($\text{kN}$) at the 5 free nodes |
| $\mathbf{u}, \mathbf{v}, \mathbf{w}$ / $U, V, W$ | `u` / `np.diag(u)` | `(12,)` / `(12, 12)` | Cable coordinate spans $x_i - x_k,\ y_i - y_k,\ z_i - z_k$ ($\text{m}$) / their diagonal matrices |
| $\mathbf{l}$ / $L$ / $L^{-1}$ | `l` / `np.diag(l)` | `(12,)` / `(12, 12)` | 3D cable lengths $\sqrt{u_j^2 + v_j^2 + w_j^2}$ ($\text{m}$) / diagonal matrix / inverse $L^{-1}$ |
| $\mathbf{s}$ | `s` | `(12,)` | Physical cable axial tension forces $s_j = q_j l_j$ ($\text{kN}$) |
| $\mathbf{q}$ / $Q$ | `q` / `np.diag(q)` | `(12,)` / `(12, 12)` | Prescribed force densities $s_j / l_j$ ($\text{kN/m}$) / diagonal stiffness matrix |
| $D = C^T Q C$ | `D` | `(5, 5)` | Free-node stiffness matrix ($D_{ii} = \sum q_j$ at node $i$, $D_{ik} = -q_j$ to neighbor $k$) |
| $D_f = C^T Q C_f$ | `D_f` | `(5, 4)` | Fixed-anchor coupling matrix ($-D_f \mathbf{x}_f$ is the pull from fixed anchors) |
| $\mathbf{l}_0, EA$ | `l_cutting, EA` | `(12,)` | Unstressed workshop cutting lengths $l_j / (1 + s_j/EA_j)$ ($\text{m}$) and axial stiffness ($\text{kN}$) |
| $G^T = \partial \mathbf{g}^{\ast} / \partial \mathbf{q}$ | `G_t` | `(r, 12)` | Constraint sensitivity Jacobian ($r$ constraints $\times\ m$ branches) |
"""

SETUP = """import numpy as np

np.set_printoptions(precision=3, suppress=True, linewidth=80)
"""


def _cell_id(tag: str) -> str:
    return hashlib.sha256(tag.encode()).hexdigest()[:8]


def _lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def _md_cell(tag: str, text: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": _cell_id(tag),
        "metadata": {},
        "source": _lines(text),
    }


def _code_cell(tag: str, code: str, exec_count: int | None, stdout: str) -> dict:
    outputs = []
    if stdout:
        outputs.append({
            "name": "stdout",
            "output_type": "stream",
            "text": _lines(stdout),
        })
    return {
        "cell_type": "code",
        "execution_count": exec_count,
        "id": _cell_id(tag),
        "metadata": {},
        "outputs": outputs,
        "source": _lines(code),
    }


def main(execute: bool = True) -> None:
    namespace = {"__name__": "schek_app", "__file__": str(APP)}
    nb_cells = [_md_cell("intro", INTRO)]

    exec_count = 0
    if execute:
        exec_count += 1
        exec(compile(SETUP, "setup", "exec"), namespace)
    nb_cells.append(_code_cell("setup", SETUP.rstrip("\n"), exec_count if execute else None, ""))

    last_part = None
    for cid, title, prose, code, explain in cells(APP.read_text()):
        if cid[0] != last_part:
            nb_cells.append(_md_cell(f"part-{cid[0]}", f"# {PARTS_TITLES[cid[0]]}"))
            last_part = cid[0]
        nb_cells.append(_md_cell(f"prose-{cid}", f"## {title}\n\n{prose}".rstrip()))
        if code:
            stdout = ""
            if execute:
                exec_count += 1
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf), np.printoptions(precision=3, suppress=True, linewidth=120):
                    exec(compile(code, f"{APP.name}[{cid}]", "exec"), namespace)
                stdout = buf.getvalue()
            nb_cells.append(_code_cell(f"code-{cid}", code, exec_count if execute else None, stdout))
        if explain:
            nb_cells.append(_md_cell(f"explain-{cid}", explain))

    nb = {
        "cells": nb_cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    OUT.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
    n_code = sum(c["cell_type"] == "code" for c in nb_cells)
    print(f"wrote {len(nb_cells)} cells ({n_code} code) into {OUT}")


if __name__ == "__main__":
    main(execute="--fast" not in sys.argv)
