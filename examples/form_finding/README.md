# Form finding examples

Follow [the force density tutorial](../../knowledge/04_form_finding/compas_fd.md)
in order, from vectors and connectivity to equilibrium, the linear solve, and
additional length and force conditions. Each step builds on the preceding steps.

## Numerical programs

| Script | Dependencies | Purpose |
|---|---|---|
| `schek_app.py` | NumPy | Runnable derivation of Schek (1974), with one code cell per tutorial subsection. Computes the small example and the reconstructed networks in part G. |
| `build_note.py` | NumPy | Executes the tutorial cells and updates the note with their explanations, code, and numerical output. |
| `schek_equations.py` | NumPy, SciPy | Checks the equations, analytic Jacobians against finite differences, and constrained iterations. |

Run from the repository root with Python 3.11 or later:

```bash
python -m pip install numpy scipy
python examples/form_finding/schek_app.py
python examples/form_finding/schek_equations.py
```

The derivation uses NumPy arrays directly: `np.diag(u)` constructs a diagonal
matrix, `C.T` transposes a matrix, `@` multiplies matrices, and
`np.linalg.solve(D, b)` solves a linear system. No custom matrix-printing helper
is needed. The `print` calls inspect intermediate values and numerical errors;
they are optional and do not affect the solution.

Figures in the note illustrate the calculations. Generating images is separate
from implementing or running the numerical method.

## Update the tutorial

Edit the explanations and code cells in `schek_app.py`, then regenerate the note:

```bash
python examples/form_finding/build_note.py
```

The generated section lies between `<!-- schek-app:start -->` and
`<!-- schek-app:end -->` in `knowledge/04_form_finding/compas_fd.md`. Changes made
directly inside that section will be overwritten. Edit the introductory theory,
package API comparison, verification, and references directly in the Markdown file.

The generator rounds displayed output for readability; computations retain full
floating-point precision. The application's final figure-data export is excluded
from the tutorial because it is independent of the numerical derivation.

## Four-cable benchmark

The chapter's benchmark has one free node at the origin, four anchors at
`(±1, ±1, 0) m`, force density `1 N/m` on each cable, and a downward load of `1 N`.
The equilibrium free-node position is `(0, 0, -0.25) m`.

The Verification sections of the `compas_fd` and `compas_dr` notes record package
runs for this benchmark. A standalone package benchmark script and its repository
test remain to be added. The runnable derivation and equation checks above are
already present; they do not expose an MCP computation tool.
