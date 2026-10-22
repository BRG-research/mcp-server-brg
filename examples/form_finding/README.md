# Form finding examples

Follow [the force density tutorial](../../knowledge/04_form_finding/compas_fd.md)
in order, from vectors and connectivity to equilibrium, the linear solve, and
additional length and force conditions. Each step builds on the preceding steps.

## Numerical programs

| Script | Dependencies | Purpose |
|---|---|---|
| `schek_app.py` | NumPy, SciPy | Runnable derivation of Schek (1974), with one code cell per tutorial subsection. Computes the small example and the reconstructed networks in part G. |
| `build_note.py` | NumPy, SciPy | Executes the tutorial cells and updates the note with their instructions, code, and numerical output. |
| `schek_equations.py` | NumPy, SciPy | Checks the equations, analytic Jacobians against finite differences, and constrained iterations. |

Run from the repository root with Python 3.11 or later:

```bash
python -m pip install numpy scipy
python examples/form_finding/schek_app.py
python examples/form_finding/schek_equations.py
```

Read each explanation and append its implementation code in order. A.4 has no
code: it works the five matrix operations through with the real numbers of the
example net. D.2 completes the linear solver; F adds length and force wishes on
top of it with `scipy.optimize.least_squares`.
Verification lives in the equation checks, not in repeated assertion blocks in
the tutorial.

The data types are introduced explicitly: `branches` starts as a Python list of
node-pair tuples; the next step constructs `C_s`, a two-dimensional NumPy array.
Node labels start at one, while Python array indices start at zero.

The derivation uses NumPy arrays directly: `np.diag(u)` constructs a diagonal
matrix, `C.T` transposes a matrix, `@` multiplies matrices, and
`np.linalg.solve(D, b)` solves a linear system. No custom matrix-printing helper
is needed. The `print` calls inspect intermediate values and numerical errors;
they are optional and do not affect the solution.

Matrices, vectors and intermediate results are shown in the note as labelled
numbers next to the notation they illustrate, not as diagrams. The images in the
note are the paper's network figures, rendered from what these programs compute;
generating them is separate from implementing or running the numerical method.

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
