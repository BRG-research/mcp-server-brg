---
id: form-finding-compas-fd
title: Force density method with compas_fd
status: reviewed
related_domains: [form_finding, thrust_network_analysis]
---

# Force density method with compas_fd

`compas_fd` implements the **force density method (FDM)** of H.-J. Schek (1974):
given the connectivity of a pin-jointed network, the positions of its fixed nodes,
the nodal loads, and one *force density* per branch, the equilibrium coordinates of
all free nodes follow from **one linear system**. A constrained, iterative variant
moves selected anchors along geometric constraints between linear solves.

- Repository: <https://github.com/BlockResearchGroup/compas_fd>
- Documentation: <https://blockresearchgroup.github.io/compas_fd>
- PyPI: `pip install compas_fd` (version `0.5.4` of 2024-11-10 was read and run for this note)
- Used by the Rhino plugin described in [compas_fofin](compas_fofin.md); the same
  force-density parametrisation drives the iterative solver in [compas_dr](compas_dr.md).

## Concept and assumptions

**Force density.** For branch *j* with axial force *s_j* and strained length *l_j*,

$$q_j = \frac{s_j}{l_j}$$

Dimension: force / length (N/m, kN/m). The same force gives a larger *q* in a
shorter branch. Schek calls *q* the "network description parameter": prescribing
*q* for every branch selects exactly one equilibrium shape.

**Model assumptions (Schek 1974, §1).**

- Branches are straight axial members (cables or bars) connected by frictionless pins.
- Loads act only at nodes.
- No material law is needed for the linear method; the branches may be elastic or
  inextensible. Material enters only through the optional *unstrained length*
  constraints of the nonlinear extension (§3.5).
- Nodes are either **free** (unknown coordinates) or **fixed** (prescribed coordinates).
- No geometric restriction is imposed on the shape: the only requirement is
  nodal equilibrium.

**Sign conventions.**

- *q_j > 0* and *s_j > 0*: tension. A net with all *q_j > 0* and no isolated free
  node has a positive-definite equation matrix and a unique solution.
- *q_j < 0*: compression. `compas_fd` accepts negative values (FormFinder uses them
  for compression-only funiculars), but mixed signs can make the matrix singular
  or indefinite; check the residuals.
- Loads *p* are external forces on nodes in global *x, y, z*; gravity is a negative *p_z*
  when *z* points up.
- The **residual** returned by the solver is *r = p − CᵗQCx*. At free nodes it is
  zero at convergence. At a fixed node it equals the resultant force the connected
  branches exert on the support, so the **support reaction** is *−r*.

**Units.** The method is unit-agnostic as long as coordinates, loads, and force
densities are consistent (e.g. m, kN, kN/m). Forces returned are *q · l* in the
load unit; lengths are in the coordinate unit.

## Formulation (Schek 1974)

Notation follows the paper: lower-case bold = column vector, capital = matrix,
and for any vector *a* the capital *A* is the diagonal matrix with *a* on its
diagonal.

### Branch-node matrix (§2.1)

Number the nodes 1…*n_s* with the *n_f* fixed nodes last, so *n_s = n + n_f*
with *n* free nodes, and the branches 1…*m*. Branch *j* runs from node *i(j)* to
node *k(j)*. The branch-node matrix *C_s* (m rows, n_s columns) has

$$c(j,i) = \begin{cases} +1 & i = i(j) \\ -1 & i = k(j) \\ 0 & \text{otherwise}\end{cases}$$

Splitting the columns into free and fixed nodes gives *C_s = [C  C_f]*.
(`compas.matrices.connectivity_matrix` builds *C_s* with the same +1/−1 convention;
`compas_fd` then column-slices it into `Ci` (free) and `Cf` (fixed).)

### Coordinate differences and equilibrium (§2.2)

With free-node coordinate vectors *x, y, z* and fixed-node vectors *x_f, y_f, z_f*,
the per-branch coordinate differences are

$$u = Cx + C_f x_f,\qquad v = Cy + C_f y_f,\qquad w = Cz + C_f z_f \tag{1}$$

With *U, V, W, L* the diagonal matrices of *u, v, w, l*, and *s* the branch forces,
nodal equilibrium (sum of forces zero at every free node) reads

$$C^t U L^{-1} s = p_x,\qquad C^t V L^{-1} s = p_y,\qquad C^t W L^{-1} s = p_z \tag{2}$$

*UL⁻¹s* is the vector of *x*-components of the branch forces (direction cosine
*u_j / l_j* times force *s_j*), and *Cᵗ* sums them per node. The matrices
*CᵗUL⁻¹* etc. are also the Jacobians *∂l/∂x, ∂l/∂y, ∂l/∂z* (eq. 3).

Equation (2) is **nonlinear** in the coordinates because *L* depends on them
(compas-FoFin GitBook, same point written for a single node with four cables:
*Σ F_j (x_j − x_0)/L_j = R_x*, with *L_j* a square root of coordinate differences).

### The linearising substitution (§2.2, eqs. 4–8)

Define the force densities

$$q = L^{-1} s \tag{4}$$

Then (2) becomes

$$C^t U q = p_x,\qquad C^t V q = p_y,\qquad C^t W q = p_z \tag{5}$$

Using the identities *Uq = Qu, Vq = Qv, Wq = Qw* (both sides are the element-wise
product of the same two vectors, eq. 6) and substituting (1):

$$C^t Q C x + C^t Q C_f x_f = p_x,\quad C^t Q C y + C^t Q C_f y_f = p_y,\quad C^t Q C z + C^t Q C_f z_f = p_z \tag{7}$$

With *D = CᵗQC* (n × n) and *D_f = CᵗQC_f* (n × n_f):

$$D x = p_x − D_f x_f,\qquad D y = p_y − D_f y_f,\qquad D z = p_z − D_f z_f \tag{8}$$

Schek's conclusions:

1. (8) is **linear** in the free coordinates. *D* is the "generalised Gaussian
   transformation" of *C*; its diagonal entry for node *i* is the sum of the *q*
   of all branches at *i*, and its off-diagonal entry (*i, k*) is *−q_j* for the
   branch joining *i* and *k* (figure 4 of the paper; reproduced numerically below).
   *D* is positive definite for a prestressed net (*q_j > 0*) without isolated nodes.
2. For given load and fixed points, each vector *q* yields **exactly one** equilibrium:

$$x = D^{-1}(p_x − D_f x_f),\quad y = D^{-1}(p_y − D_f y_f),\quad z = D^{-1}(p_z − D_f z_f) \tag{9}$$

$$s = L q \tag{10}$$

   with *L* evaluated from the solved coordinates.
3. The set of equilibrium shapes for a fixed topology, load, and anchors is in
   one-to-one correspondence with the set of vectors *q*.

The three systems in (8) share the matrix *D*; `compas_fd` solves them as one
system with a 3-column right-hand side. Figure 3 of the paper is the workflow:
input connectivity → build *C* → build *D* and the right-hand sides → solve (9)
→ lengths and forces (10) → plot → change anchors, loads, *q*, or topology and repeat.

### Geometric interpretation (§4)

Minimising the *weighted* sum of squared branch lengths
*uᵗPu + vᵗPv + wᵗPw* with diagonal weights *P* and at least four fixed points in
general position yields the stationarity conditions

$$(C^t P C) x = −(C^t P C_f) x_f \quad\text{(and the same for } y, z) \tag{41}$$

which are (7) with *Q = P* and zero load. Hence:

- **Theorem 1.** Every equilibrium state of an *unloaded* network with force
  densities *q_j* is the net whose sum of squared branch lengths weighted by
  *q_j* is minimal. With all *q_j = 1* it is the net with minimal unweighted
  sum of squared lengths (eq. 39).
- **Theorem 2.** A *minimum way net* (minimal sum of lengths, not squared) is a
  prestressed net with the same force in every branch: choose *q_j = const / l_j*,
  so *s_j = q_j l_j = const*, and *l_j > 0* gives *q_j > 0*.

### Nonlinear extension: additional constraints (§3)

Linear FDM fulfils no condition other than equilibrium (meshes are in general
neither equidistant nor orthogonal). Schek adds *r* conditions

$$g(x, y, z, q) = 0 \tag{11}$$

Since (9) makes *x, y, z* functions of *q*, the conditions depend on *q* alone:
*g\*(q) = 0* (eq. 12). Starting from the linear solution *q⁽⁰⁾*, linearise:

$$g^*(q^{(0)}) + \frac{\partial g^*}{\partial q}\,\Delta q = 0,\qquad G^t := \frac{\partial g^*}{\partial q},\quad r := −g^*(q^{(0)}) \quad\Rightarrow\quad G^t \Delta q = r \tag{13–16}$$

*Gᵗ* is *r × m*. With *r < m* there are *m − r* free directions; pick *Δq* by
a minimum principle:

| variant | condition | minimised | normal-equation matrix *T* |
|---|---|---|---|
| least squares (16, 17) | *Gᵗ Δq = r* | *Δqᵗ Δq* | *GᵗG* |
| damped (18, 19) | *Gᵗ Δq = r + a* | *Δqᵗ Δq + aᵗ P a* | *GᵗG + P⁻¹* |
| modified damped (20, 21) | *Gᵗ Δq = A r* (A = diag of damping factors *a_j*) | *Δqᵗ Δq + (e − a)ᵗ P (e − a)* | *GᵗG + P⁻¹ A²* |

In all cases the Lagrange multipliers *k* solve the small *(r × r)* system
*T k = r* (22–24) and

$$\Delta q = G k,\qquad q^{(0)} := q^{(0)} + \Delta q \tag{25}$$

iterated until *g\** vanishes within tolerance. The number of nonlinear equations
equals the number of constraints, **not** the number of nodes. Schek recommends the
modified damped variant: it converges without oscillation and, when the
constraints are physically unattainable, stops at the closest feasible shape.

**Jacobian via implicit differentiation (§3.2).** By the chain rule

$$G^t = \frac{\partial g}{\partial x}\frac{\partial x}{\partial q} + \frac{\partial g}{\partial y}\frac{\partial y}{\partial q} + \frac{\partial g}{\partial z}\frac{\partial z}{\partial q} + \frac{\partial g}{\partial q} \tag{26}$$

Differentiating the equilibrium *CᵗUq = p_x* at fixed load, with
*∂(CᵗUq)/∂q = CᵗU* and *∂(CᵗUq)/∂x = CᵗQC = D*:

$$\frac{\partial x}{\partial q} = −D^{-1} C^t U,\qquad \frac{\partial y}{\partial q} = −D^{-1} C^t V,\qquad \frac{\partial z}{\partial q} = −D^{-1} C^t W \tag{27–28}$$

**Constraint types** (bars over a symbol = restriction to the first *r* branches):

- *Node distance* (strained length) *g = l̄ − l̄_v = 0* (29). With *∂l/∂x = CᵗUL⁻¹* (3):

$$G_d^t = −\bar L^{-1}\left(\bar U \bar C D^{-1} C^t U + \bar V \bar C D^{-1} C^t V + \bar W \bar C D^{-1} C^t W\right) \tag{31}$$

- *Force* *g = L̄q̄ − s̄_v = Q̄ l̄ − s̄_v = 0* (32). Using *∂g/∂q = L̄* (33):

$$G_f^t = \bar L − \bar Q \bar L^{-1}\left(\bar U \bar C D^{-1} C^t U + \bar V \bar C D^{-1} C^t V + \bar W \bar C D^{-1} C^t W\right) \tag{34}$$

- *Unstrained length* with linear Hooke's law *l_{u,j} = h_j l_j / (h_j + s_j)*
  (*h_j* = axial stiffness):

$$G_u^t = −\bar L_u^2 \bar H^{-1} − \bar L_u^2 \bar L^{-3}\left(\bar U \bar C D^{-1} C^t U + \bar V \bar C D^{-1} C^t V + \bar W \bar C D^{-1} C^t W\right) \tag{35}$$

  which tends to *G_d* as *h → ∞*.
- *Mixed*: stack the class matrices, *G = [G_d | G_f | G_u | …]*.

All three share the kernel *C D⁻¹ Cᵗ* scaled by the diagonal coordinate-difference
matrices, which is why they are cheap to assemble together.

**What `compas_fd` implements of this.** Only the linear method (§2) and a
*geometric* constraint loop that is not Schek's §3: anchors are projected onto
lines, planes, circles, curves, or surfaces and moved by a damped fraction of the
tangential residual between linear solves. Prescribed branch lengths or forces
(Schek §3.3–3.5) are **not** available in `compas_fd` 0.5.4. The iterative solver in
[compas_dr](compas_dr.md) reaches prescribed forces/lengths through its
`fpre`/`lpre` terms instead.

### Schek's worked example (§5)

Radial net with 67 nodes, nodes 62–67 fixed, a small vertical load at every node:

| branches | *q* | effect |
|---|---|---|
| border (main cables) | 100 | borders nearly straight |
| radial branches to the apex (node 67) | 0.5 | radial branches lengthen relative to the rest |
| all others | 1 | — |

Changing the apex position only changes the right-hand side (one matrix
multiplication per variant, fig. 6). Raising the apex *q* to 1.0 / 0.7 / 0.3
(fig. 7) or lowering the border *q* to 10 / 5 / 1 (fig. 8) shortens or lengthens
those branch families; with *q = 1* everywhere the net is also the minimal
squared-length net (Theorem 1). Prescribing 6 m for all radial branches needed
5 damped iterations (fig. 9). A hanging grid-shell model of 112 identical bars was
reproduced from anchor coordinates, bar length, and bar weight alone, then turned
into a prestressed net by moving the anchors (fig. 10).

## Implementation in compas_fd 0.5.4

### Linear solver

```python
from compas_fd.solvers import fd_numpy

result = fd_numpy(
    vertices=vertices,          # (n_s, 3) coordinates of ALL nodes, free and fixed
    fixed=fixed,                # indices of fixed nodes
    edges=edges,                # list of (i, k) index pairs; i -> +1, k -> -1 in C
    forcedensities=q,           # one float per edge
    loads=loads,                # (n_s, 3) nodal loads, optional (defaults to zero)
)
result.vertices    # (n_s, 3) equilibrium coordinates; fixed rows unchanged
result.residuals   # (n_s, 3) p - C^t Q C x  (zero at free nodes; -reaction at supports)
result.forces      # (m, 1)   q * l
result.lengths     # (m, 1)   strained lengths
```

Internally (`solvers/fd_numerical_data.py`, `solvers/fd_numpy.py`):

| symbol in Schek | name in code | construction |
|---|---|---|
| *C_s* | `C` | `connectivity_matrix(edges, "csr")` |
| *C* (free columns) | `Ci` | `C[:, free]` |
| *C_f* | `Cf` | `C[:, fixed]` |
| *Q* | `Q` | `diags([q.flatten()], [0])` |
| *D* | `Ai` | `Ci.T @ Q @ Ci` |
| *D_f* | `Af` | `Ci.T @ Q @ Cf` |
| full *C_sᵗ Q C_s* | `A` | `C.T @ Q @ C` (used only for residuals) |
| right-hand side of (8) | `b` | `p[free] - Af @ xyz[fixed]` |
| (9) | — | `xyz[free] = spsolve(Ai, b)` |
| *l* | `lengths` | `normrow(C @ xyz)` |
| (10) | `forces` | `q * lengths` |
| residual | `residuals` | `p - A @ xyz` |

The compas-FoFin GitBook shows the same lines verbatim as the "matrix formulation".
Node ordering is free: the code selects columns by index, so fixed nodes need not
be last as Schek advises. Vertex and edge ordering of the outputs equals the input
ordering. `Result` is a `NamedTuple`; `vertices` is the same array that was
assembled from the input (a copy of the input list, not the input list itself).

### Constrained solver

```python
from compas.geometry import Line
from compas_fd.constraints import Constraint
from compas_fd.solvers import fd_constrained_numpy

constraints = [None] * len(vertices)
constraints[k] = Constraint(Line([0, 0, 0], [1, 0, 0]))   # vertex k may slide on this line

result = fd_constrained_numpy(
    vertices=vertices, fixed=fixed, edges=edges, forcedensities=q, loads=loads,
    constraints=constraints,   # list aligned with vertices; None = unconstrained
    kmax=100, tol_res=1e-3, tol_disp=1e-3, damping=0.1,
    selfweight=None,           # optional callable xyz -> (n_s, 1) weights, subtracted from p_z
)
```

Each iteration: solve the linear system with the constrained vertices treated as
fixed; compute residuals; for every constrained vertex set `location` and
`residual` on its constraint, call `update(damping)`, which moves the vertex by
`damping × tangent` (the residual component along the constraint) and re-projects
it onto the geometry; collect the tangential residuals. Convergence requires the
largest tangential residual below `tol_res`. Constrained vertices must therefore
be listed in `fixed`; a constraint on a free vertex is ignored by the linear solve.

Constraint geometries are registered on `Constraint(geometry)`: `Vector`,
`Frame`, `Line`, `Plane`, `Circle`, `NurbsCurve`, `NurbsSurface`
(`constraints/__init__.py`). Each subclass defines `project`, `compute_tangent`,
`compute_normal`, `update`, `compute_param`.

`compas_fd.loads.SelfweightCalculator(mesh, density, thickness_attr_name="t")`
returns a callable that multiplies each vertex's tributary area (a quarter of each
adjacent face, from the current coordinates) by thickness × density.

### Caveats found while reading the source

- In `fd_constrained_numpy`, `xyz_prev = numdata.xyz` binds the same array that
  the linear solve then overwrites in place, so the displacement test
  `_is_converged_disp` compares the array with itself and is always true; only
  the tangential-residual test actually stops the loop (0.5.4).
- With `constraints` all `None`, the constrained solver returns the linear
  result after one iteration.
- `fd_numpy` has no input validation: an edge index out of range raises inside
  `connectivity_matrix`, mismatched lengths of `forcedensities` and `edges` raise in
  `diags`/`dot`, and a free node not connected to any fixed node by a positive-*q*
  path makes `Ai` singular (`spsolve` warns and returns `nan`/`inf`).
- `requirements.txt` lists only `compas`; `numpy` and `scipy` arrive through
  `compas`. Tested here with compas 2.15.1, numpy 2.4.6, scipy 1.17.1.

## Verification

**Benchmark from the chapter README.** Four fixed nodes at (±1, ±1, 0), one free
node at the origin connected to all four, *q = 1 N/m* on every edge, load
(0, 0, −1) N on the free node. Vertical equilibrium gives
*4 · q · (0 − z) = 1 → z = −0.25 m* independent of the cable lengths (that is the
whole point of eq. 8).

Run with `compas_fd` 0.5.4 (`fd_numpy`):

| quantity | value |
|---|---|
| free node | (0, 0, −0.25); error < 1e−12 m |
| residual at free node | (0, 0, 0) |
| edge length | 1.436140662 m (= √(1 + 1 + 0.0625)) |
| edge force | 1.436140662 N (= *q l*) |
| residual at support (−1, −1, 0) | (1, 1, −0.25) N = force the cable exerts on the support |

The support residuals sum to (0, 0, −1), i.e. the applied load, as they must.

**Structure of D (Schek fig. 4).** Building *C_s* for the 9-node, 12-branch graph
of figure 2 and setting *q_j = j* gives
*D₁₁ = q₁+q₅+q₆+q₁₀ = 22*, *D₃₃ = q₃+q₇+q₈+q₁₂ = 30*, *D₅₅ = q₉+q₁₀+q₁₁+q₁₂ = 42*
and off-diagonals *−q_j* exactly as printed in the paper. (Branch 5 joins nodes 1
and 4; the scanned figure is ambiguous there, but figure 4 fixes it.)

**Theorem 1.** For random anchors and random *q ∈ [0.5, 3]* on that graph, the
unloaded FDM solution and a BFGS minimiser of *Σ q_j l_j²* agree to 3e−7.

**Jacobian (31) and damped iteration (20–25).** Implemented literally for
*r = 4* prescribed strained lengths on the same graph: the analytic *G_dᵗ* matches
finite differences to 4e−7, and the modified damped scheme with *a_j = 0.8*,
*P⁻¹ = 10⁻⁶ I* reaches the prescribed lengths to 1e−12 in 19 iterations while the
free-node residual stays at machine precision. Script: see the session
scratchpad `bench/verify.py` (not part of the repository); a cleaned version belongs in
`examples/form_finding/` per the chapter README.

## References and provenance

- Schek, H.-J. (1974). *The force density method for form finding and computation
  of general networks.* Computer Methods in Applied Mechanics and Engineering 3,
  115–134. <https://doi.org/10.1016/0045-7825(74)90045-0>. Read in full from the
  publisher PDF (20 pages; OCR text checked against page images for every equation
  cited above). Received 26 June 1973; work done within SFB 64, Stuttgart, for the
  Munich Olympic roofs (refs. 16, 17 of the paper).
- Block Research Group. *Force Densities Method*, compas-FoFin GitBook,
  <https://blockresearchgroup.gitbook.io/compas-fofin/theoretical-background/force-densities-method>
  (read 2026-10-15). Gives the single-node motivation, the rope analogy for *q*,
  and the NumPy/SciPy snippet reproduced above. It cites Schek (1974);
  Veenendaal & Block (2012), *An overview and comparison of structural form finding
  methods for general networks*, Int. J. Solids Struct. 49, 3741–3753,
  <https://doi.org/10.1016/j.ijsolstr.2012.08.008>; and Adriaenssens, Block,
  Veenendaal & Williams (eds., 2014), *Shell Structures for Architecture: Form
  Finding and Optimization*, Routledge.
- Source read: `BlockResearchGroup/compas_fd` at commit `7ee3c5a` (0.5.4, 2024-11-10):
  `solvers/fd_numpy.py`, `solvers/fd_constrained_numpy.py`,
  `solvers/fd_numerical_data.py`, `solvers/result.py`, `constraints/*.py`,
  `loads/selfweight.py`. MIT licence.
- Verification status: benchmark and the four numerical checks above were run on
  2026-10-15 with compas_fd 0.5.4 in a throw-away virtual environment; no adapter,
  example, or test has been added to this repository yet (see chapter README).

[Chapter README](README.md) · [compas_dr](compas_dr.md) · [compas_fofin](compas_fofin.md)
