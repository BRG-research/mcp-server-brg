---
id: form-finding-compas-dr
title: Dynamic relaxation with compas_dr
status: reviewed
related_domains: [form_finding]
---

# Dynamic relaxation with compas_dr

`compas_dr` implements **dynamic relaxation (DR)** for networks of axial-force
members: the same nodes, branches, loads, and force densities as the force
density method in [compas_fd](compas_fd.md), but solved by pseudo-dynamic
iteration instead of one linear solve. The iteration lets the branch force
densities depend on the current geometry, so prescribed forces, prescribed
lengths, and elastic stiffness can be included, which the linear force density
method cannot do without Schek's nonlinear extension.

- Repository: <https://github.com/BlockResearchGroup/compas_dr>
- Documentation: <https://blockresearchgroup.github.io/compas_dr>
- PyPI: `pip install compas_dr` (version `0.3.1` read and run for this note;
  repository `main` at commit `84a3b4b`, 2024-10-16, with unreleased changes noted below)
- Requires `compas >= 2.1`; NumPy/SciPy for the `*_numpy` solvers. Declared
  dependency of the Rhino plugin in [compas_fofin](compas_fofin.md).

## Concept and assumptions

Dynamic relaxation treats the free nodes as lumped masses, applies the residual
force as a driving force, damps the fictitious motion, and integrates in time
until the residual vanishes. The converged state is a static equilibrium; the
masses, time step, and damping are numerical devices and do not change the
answer, only how fast it is reached.

Model assumptions are those of the force density method (Schek 1974, see
[compas_fd](compas_fd.md)): straight axial members, pinned nodes, nodal loads,
free and fixed nodes. Sign conventions are the same: positive force density and
force are tension, residual *r = p − CᵗQu* is zero at free nodes at convergence
and equals the branch resultant on a support at fixed nodes (reaction = *−r*).

**Where force densities enter.** For every edge the solver composes a force
density from four optional contributions:

$$q_j = q^{pre}_j + \frac{f^{pre}_j}{l_j} + \frac{f_j}{l^{pre}_j} + \frac{E_j A_j\,(l_j − l^{init}_j)}{l^{init}_j\, l_j}$$

| term | input | meaning |
|---|---|---|
| *q^{pre}* | `qpre` | prescribed force density, exactly Schek's *q* |
| *f^{pre} / l* | `fpre` | prescribed force: the density that gives force *f^{pre}* at the current length |
| *f / l^{pre}* | `lpre` | prescribed length: current force divided by target length |
| *EA (l − l^{init}) / (l^{init} l)* | `E`, `radius`, `linit` | linear-elastic bar with cross-section *A = π r²*, unstrained length *l^{init}* (Hooke's law, force *EA (l − l_0)/l_0*, divided by *l*) |

Division by zero (a term not used) is set to zero. With only `qpre` given, every
iteration uses the constant *q* of Schek and DR converges to the force density
solution (verified below). The `fpre`/`lpre`/`EA` terms are the DR counterpart of
Schek's §3 force, distance, and unstrained-length conditions: instead of solving
for a correction *Δq* by damped least squares, DR updates *q* from the current
geometry at every step.

**Units** as commented in the source: coordinates m, loads and forces kN,
`E` in kN/mm² (= GPa), `radius` in mm, so *EA* comes out in kN. The code comments
on `lpre`/`fpre` have the units swapped; `fpre` is a force, `lpre` a length. Any
consistent system works if `E`/`radius` are not used.

## Formulation (compas_dr.solvers.dr_numpy)

Per iteration *k*, with *C* the full branch-node matrix, *C_i* its free columns,
and *Q* the diagonal matrix of the composed *q*:

1. **Stiffness-like matrix and residual.** *D = C_iᵗ Q C* (free rows, all columns), so
   *r_free = p_free − D x* is Schek's eq. (7) rearranged; at the fixed nodes the
   residual is *p − CᵗQ(Cx)*.
2. **Lumped mass.** For every node, *m = ½ dt² Σ_{edges at node}
   (q^{pre} + f^{pre}/l + f/l^{pre} + EA/l^{init})*, i.e. half the time step squared
   times the sum of the edge "stiffness densities" at the node (`Ct2 = (Cᵗ)²`
   element-wise gives the unsigned incidence). This is the usual DR choice that keeps
   the explicit integration stable for *dt = 1*.
3. **Viscous damping** by the coefficients of De Laet et al. (2013):
   *a = (1 − c/2)/(1 + c/2)*, *b = (1 + a)/2*. The velocity carried into the step
   is *a · v*; the acceleration used is *b · r / m*.
4. **Runge–Kutta integration** of *dv = ∫ b r(x(t)) / m dt* over one step, with
   `rk_steps` = 1 (explicit Euler), 2 (default; Butcher weights [0, 1], i.e.
   the midpoint method), or 4 (classic RK4 with weights [1/6, 1/3, 1/3, 1/6]).
   Inside each stage the residual is re-evaluated at the trial position
   *x₀ + v t*, with *D* held fixed for the step.
5. **Update.** *v_free += dv*, *dx = v dt*, *x_free += dx*; then
   *u = Cx*, *l = ‖u‖*, *f = q l*, *r = p − CᵗQu*.
6. **Convergence.** Stop when *‖r_free‖ < tol1* (residual norm over all free
   nodes) **or** *‖dx_free‖ < tol2* (displacement norm), or after `kmax` steps.

Because *q* is recomposed from the new lengths at the start of the next step,
prescribed forces and lengths are approached progressively; with `qpre` only, the
problem is linear and DR behaves as a damped iterative linear solver for
Schek's eq. (8).

## Implementation in compas_dr 0.3.1

```python
from compas_dr.numdata import InputData
from compas_dr.solvers import dr_numpy

indata = InputData(
    vertices=vertices,   # (n_s, 3) all nodes
    edges=edges,         # (i, k) pairs; +1 / -1 columns of C
    fixed=fixed,         # indices of fixed nodes
    loads=loads,         # (n_s, 3)
    qpre=q,              # one value per edge (required)
    fpre=None, lpre=None, linit=None, E=None, radius=None,   # per edge, optional
)
result = dr_numpy(indata, kmax=10000, dt=1.0, tol1=1e-3, tol2=1e-6, c=0.1, rk_steps=2,
                  callback=None, callback_args=None)
result.xyz        # (n_s, 3) equilibrium coordinates
result.q          # (m, 1) composed force densities at the last step
result.forces     # (m, 1) q * l
result.lengths    # (m, 1)
result.residuals  # (n_s, 3)
result.update_mesh(mesh)   # write xyz back to a compas Mesh in vertex order
```

- `InputData.from_mesh(mesh, fixed, loads, qpre, ...)` builds the arrays in
  `mesh.vertices()` / `mesh.edges()` order. `InputData` and `ResultData` are
  `compas.data.Data` objects, so `InputData` serialises to JSON; `ResultData.__data__`
  is empty (not serialisable yet).
- `InputData.linit` all zero (the default) means "use the initial lengths" for the
  elastic term; `q0` (all ones) and `l0` (initial lengths) seed the first
  iteration's *f = q l* for the `lpre` term.
- The `callback(k, x, crit1, crit2, callback_args)` runs every iteration; use it to
  draw intermediate states or log convergence.
- `dr_constrained_numpy(*, indata, constraints, kmax, dt, tol1, tol2, c, rk_steps,
  damping=0.1, callback, callback_args)`: same loop, plus after each step every
  constrained vertex is moved by `damping × tangent residual` along its
  `compas_dr.constraints.Constraint` (Line, Plane, Circle, Curve, Surface; same
  registration mechanism as `compas_fd`) and re-projected. The residual at the
  constrained vertex is replaced by the constraint's residual before the
  convergence check. Constrained vertices must be in `fixed`.
- `compas_dr.solvers.dr` is a pure-Python version (RK4 hard-coded, no `E`/`radius`
  term, `max` instead of norm for the convergence criteria) for environments
  without NumPy, e.g. IronPython.

**Caveats found while reading the source.**

- `dr_constrained_numpy` prints the iteration counter every step (`print(k)`),
  which floods the console in long runs (0.3.1).
- `A = 3.14159 * radius**2` uses a truncated π (relative error 8e−7).
- The default `tol1 = 1e-3` is an absolute norm over all free nodes; scale it with
  the load level and node count. A mesh with hundreds of nodes under kN loads may
  need a smaller tolerance for a visually converged shape, or a larger `kmax`.
- The unreleased `main` branch renames the constraint update parameter from `c` to
  `damping` and changes plane projection to the closest-point method (CHANGELOG).
- `numpy.seterr(divide="ignore")` is set at import time and not restored.

## Verification

Benchmark from the chapter README (four anchors at (±1, ±1, 0), free node at the
origin, *q^{pre} = 1* on all edges, load (0, 0, −1) on the free node, analytical
*z = −0.25*). With `dr_numpy(indata, kmax=10000, tol1=1e-10, tol2=1e-12)` and
defaults `dt = 1`, `c = 0.1`, `rk_steps = 2`:

| quantity | value |
|---|---|
| free node *z* | −0.25, error 9.4e−12 |
| forces | 1.436141 (all four edges), equal to the `compas_fd` result |
| residual at free node | (0, 0, 0) to printed precision |

The result coincides with the one-shot force density solution, as expected when
only `qpre` is given. Run on 2026-10-15 with compas_dr 0.3.1, compas 2.15.1,
numpy 2.4.6, scipy 1.17.1.

## References and provenance

- De Laet, L., Veenendaal, D., Van Mele, T., Mollaert, M., Block, P. (2013).
  *Bending incorporated: designing tension structures by integrating bending-active
  elements.* Proceedings of the TensiNet Symposium 2013, Istanbul. Cited by the
  solver docstring for the damping coefficients and integration scheme.
- Schek, H.-J. (1974). *The force density method for form finding and computation
  of general networks.* CMAME 3, 115–134. Source of the branch-node matrix,
  *q = s / l*, and the equilibrium form *r = p − CᵗQu* reused by DR; see
  [compas_fd](compas_fd.md) for the full derivation.
- Veenendaal, D., Block, P. (2012). *An overview and comparison of structural form
  finding methods for general networks.* Int. J. Solids Struct. 49, 3741–3753.
  Compares DR and FDM on the same parametrisation.
- Source read: `BlockResearchGroup/compas_dr` commit `84a3b4b` (2024-10-16):
  `numdata.py`, `solvers/dr_numpy.py`, `solvers/dr_constrained_numpy.py`,
  `solvers/dr.py`, `constraints/constraint.py`, `CHANGELOG.md`. MIT licence.
  Tutorial and API pages of the online docs are headings only at this revision.
- Verification status: benchmark run as above; no adapter, example, or test in this
  repository yet.

[Chapter README](README.md) · [compas_fd](compas_fd.md) · [compas_fofin](compas_fofin.md)
