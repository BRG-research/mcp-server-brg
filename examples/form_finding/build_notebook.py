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

INTRO = r"""# Force Density Method (FDM) — Schek (1974), Step by Step

A runnable version of [compas_fd.md](compas_fd.md). **Run the cells in order**: each section pairs the general equation with an explicit numerical matrix example from our 12-branch, 9-node benchmark net.

$$
q_j = \frac{s_j}{l_j}
\qquad \Longrightarrow \qquad
\text{Example (1 cable):}\quad l = 2.5\text{ m},\quad s = 10\text{ kN} \implies q = \frac{10\text{ kN}}{2.5\text{ m}} = 4\text{ kN/m}
$$

| Milestone | What you can do |
|---|---|
| **A.1–A.4** | Represent a network as a branch-node matrix and trace $C^T Q C$ step by step. |
| **B.1–B.3** | Compute branch coordinate differences, lengths, and the 4-stage nonlinear equilibrium residual. |
| **C.1–C.4** | Apply the force-density substitution $q_j = s_j / l_j$, assemble $D$ and $D_f$, solve coordinates, and recover forces. |
| **D.1–D.2** | Package the 3D linear solver and support reactions into a single function. |
| **E.1** | Interpret $q_j$ geometrically as a weight minimizing $\sum q_j l_j^2$. |
| **F.1–F.3** | Enforce target branch lengths and forces via constrained least-squares and the sensitivity Jacobian $G^T$. |
| **G.1–G.5** | Apply the same solver to Schek's 67-node pointed tent and 112-bar grid-shell benchmarks. |

## Symbol & shape reference

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
