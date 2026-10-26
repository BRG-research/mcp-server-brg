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
from build_note import PARTS_TITLES, cells, sanitize_gfm_math  # noqa: E402

APP = HERE / "schek_app.py"
OUT = HERE.parents[1] / "knowledge/04_form_finding/compas_fd.ipynb"

INTRO = r"""# Force Density Method (FDM) — Schek (1974), Step by Step

A runnable version of [compas_fd.md](compas_fd.md). **Run the cells in order**.

![Physical and geometric foundation of the Force Density Method](images/fd_linkwitz_intuition.png)

* **Force density ($q_j = s_j / l_j$):** Dividing branch tension $s_j$ by branch length $l_j = \sqrt{u_j^2 + v_j^2 + w_j^2}$ cancels $l_j$ out of the direction cosine $u_j / l_j$, turning nonlinear equilibrium into a linear system where each free node $P_0$ settles at the $q$-weighted average of its neighbors (Linkwitz 2014, Sec. 6.2):

$$
q_j = \frac{s_j}{l_j}, \qquad
x_0 = \frac{p_x + q_a x_1 + q_b x_2 + q_c x_3 + q_d x_4}{q_a + q_b + q_c + q_d}, \qquad
l _ {0,j} = \frac{l_j}{1 + s_j / EA_j}
$$

| Symbol | Code | Shape | Meaning |
|---|---|---|---|
| $C_s = [C \mid C_f]$ | `C_s`, `C`, `C_f` | `(12, 9)` = `(12, 5)` \| `(12, 4)` | Branch-node connectivity ($+1$ at start node $i$, $-1$ at end node $k$) |
| $x, y, z$ / $x_f, y_f, z_f$ | `x, y, z` / `x_f, y_f, z_f` | `(5,)` / `(4,)` | Free-node (unknown) and fixed-anchor (known) coordinates ($\text{m}$) |
| $p_x, p_y, p_z$ | `p_x, p_y, p_z` | `(5,)` | External nodal loads at the 5 free nodes ($\text{kN}$) |
| $u, v, w$ / $U, V, W$ | `u` / `np.diag(u)` | `(12,)` / `(12, 12)` | Branch coordinate differences $x_i - x_k,\ y_i - y_k,\ z_i - z_k$ ($\text{m}$) |
| $l, s, q$ / $L, Q$ | `l, s, q` | `(12,)` / `(12, 12)` | Branch lengths $l_j$ ($\text{m}$), forces $s_j = q_j l_j$ ($\text{kN}$), force densities $q_j = s_j / l_j$ ($\text{kN/m}$) |
| $D = C^T Q C$, $D_f = C^T Q C_f$ | `D`, `D_f` | `(5, 5)`, `(5, 4)` | Free-node stiffness matrix and fixed-anchor coupling matrix |
| $l_0, EA$ | `l_cutting, EA` | `(12,)` | Unstressed cutting lengths $l_j / (1 + s_j/EA_j)$ ($\text{m}$) and axial stiffness ($\text{kN}$) |
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
        "source": _lines(sanitize_gfm_math(text)),
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
