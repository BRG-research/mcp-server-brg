"""Generate the Jupyter notebook knowledge/04_form_finding/compas_fd.ipynb from schek_app.py.

Same source of truth as build_note.py: each `# %% [id] title` cell of schek_app.py becomes
a markdown cell (its prose), a code cell (the implementation) and a markdown cell (its
line-by-line reading).  The notebook is then executed, so every output is stored in it and
you can read the results without running anything.

    python examples/form_finding/build_notebook.py          # build and execute
    python examples/form_finding/build_notebook.py --fast   # build without executing
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_note import PARTS_TITLES, cells  # noqa: E402

APP = HERE / "schek_app.py"
OUT = HERE.parents[1] / "knowledge/04_form_finding/compas_fd.ipynb"

INTRO = """# Force density method — Schek (1974), step by step

A runnable version of [compas_fd.md](compas_fd.md).  **Run the cells in order**: each one
adds data or a calculation that the next ones need.

Every section has the same shape: **what the step does**, the **equation**, the **stages
read right to left**, and **the same thing with our numbers** — every matrix printed with
labelled rows and columns, so you can point at any entry and say where it came from.

`@` is matrix multiplication.  `*` is entry-by-entry multiplication.  Shapes are written
next to every array.

| Milestone | What you can do |
|---|---|
| A.1–A.4 | Represent a network and understand its matrix operations. |
| B.1–B.3 | Compute branch geometry and test nodal equilibrium. |
| C.1–C.4 | Derive and execute the linear force density solve. |
| D.1–D.2 | Reuse a complete linear solver with different supports and force densities. |
| E.1 | Interpret the geometric effect of force densities. |
| F.1–F.3 | Ask for wanted lengths and forces on top of equilibrium. |
| G.1–G.5 | Apply the same solvers to larger reconstructed examples. |

**The linear force density method is complete at D.2.**  Parts A–E need only NumPy; part F
adds `scipy.optimize`.

## The symbols, once

| Symbol | Say it as | What it is | Code | Shape here |
|---|---|---|---|---|
| $u, v, w$ | "u, v, w" | coordinate differences across each branch, per axis | `u` | `(12,)` |
| $U, V, W$ | "capital U" | those lists on a diagonal | `np.diag(u)` | `(12, 12)` |
| $l$ / $L$ | "l" / "capital L" | branch lengths / their diagonal | `l` | `(12,)` |
| $s$ | "s" | force in each branch | `s` | `(12,)` |
| $q$ / $Q$ | "q" / "capital Q" | **force density** $s_j/l_j$ / its diagonal | `q` | `(12,)` |
| $C_s$ | "C sub s" | branch-node table, one row per cable, one column per node | `C_s` | `(12, 9)` |
| $C$ | "C" | the **free**-node columns of $C_s$ | `C` | `(12, 5)` |
| $C_f$ | "C sub f" | the **anchor** columns of $C_s$ | `C_f` | `(12, 4)` |
| $C^t$ | "C transposed" | $C$ with rows and columns swapped | `C.T` | `(5, 12)` |
| $x, y, z$ | "x, y, z" | free-node coordinates — **the unknowns** | `x` | `(5,)` |
| $x_f, y_f, z_f$ | "x sub f" | anchor coordinates — **given** | `x_f` | `(4,)` |
| $p_x, p_y, p_z$ | "p sub x" | loads at the free nodes — **given** | `p_x` | `(5,)` |
| $D$ | "D" | $C^t Q C$, the matrix that gets solved | `D` | `(5, 5)` |
| $D_f$ | "D sub f" | $C^t Q C_f$, the anchor coupling | `D_f` | `(5, 4)` |

**Small letter = a list.  Capital = that list on a diagonal.**  Schek never writes "diag"
because the capital already says it.
"""

SETUP = """import numpy as np

np.set_printoptions(precision=3, suppress=True, linewidth=120)   # readable output, full precision kept
"""


def main(execute: bool = True) -> None:
    nb = nbf.v4.new_notebook()
    nb.cells.append(nbf.v4.new_markdown_cell(INTRO))
    nb.cells.append(nbf.v4.new_code_cell(SETUP))

    last_part = None
    for cid, title, prose, code, explain in cells(APP.read_text()):
        if cid[0] != last_part:
            nb.cells.append(nbf.v4.new_markdown_cell(f"# {PARTS_TITLES[cid[0]]}"))
            last_part = cid[0]
        nb.cells.append(nbf.v4.new_markdown_cell(f"## {title}\n\n{prose}".rstrip()))
        if code:
            nb.cells.append(nbf.v4.new_code_cell(code))
        if explain:
            nb.cells.append(nbf.v4.new_markdown_cell(explain))

    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb.metadata["language_info"] = {"name": "python", "pygments_lexer": "ipython3"}

    if execute:
        from nbclient import NotebookClient
        print("executing the notebook (this runs the whole derivation) ...")
        NotebookClient(nb, timeout=900, kernel_name="python3",
                       resources={"metadata": {"path": str(HERE)}}).execute()

    OUT.write_text(nbf.writes(nb) + "\n")
    n_code = sum(c.cell_type == "code" for c in nb.cells)
    print(f"wrote {len(nb.cells)} cells ({n_code} code) into {OUT}")


if __name__ == "__main__":
    main(execute="--fast" not in sys.argv)
