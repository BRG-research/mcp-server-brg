---
id: form-finding-compas-fofin
title: COMPAS FormFinder (compas-FoFin) for Rhino 8
status: reviewed
related_domains: [form_finding, computational_design]
---

# COMPAS FormFinder (compas-FoFin) for Rhino 8

COMPAS FormFinder is the Block Research Group's Rhino 8 plugin for form finding of
tension-only, compression-only, and mixed axial-force structures. It is a graphical
front end: the equilibrium is computed by the constrained force density solver of
[compas_fd](compas_fd.md); [compas_dr](compas_dr.md) is a declared dependency but no
dynamic relaxation command is exposed in the current release.

- Repository: <https://github.com/BlockResearchGroup/compas-FoFin>
  (note: `github.com/BlockResearchGroup/compas_fofin` with an underscore now
  redirects to `compas_fd`, the former name of the solver package)
- Documentation (GitBook): <https://blockresearchgroup.gitbook.io/compas-fofin>
- Theory page: <https://blockresearchgroup.gitbook.io/compas-fofin/theoretical-background/force-densities-method>
- Versions read: Python package `compas_fofin` 0.15.3 (commit `9ce50ac`, 2025-07-01);
  Yak package "COMPAS FormFinder" 0.2.75 (pre-release) as stated in the README and
  Getting Started page.

## Scope and installation

- **Rhino 8 only.** The plugin runs on Rhino 8's CPython runtime and is installed
  through Yak: type `PackageManager`, search "FormFinder", install "COMPAS FormFinder".
- On first use the plugin installs its COMPAS dependencies into a separate virtual
  environment named `brg-csd`: `compas >= 2.9`, `compas_dr >= 0.3`, `compas_fd >= 0.5.2`,
  `compas_rui >= 0.5.0`, `compas_session >= 0.4.5`. Rhino may be unresponsive for
  a few seconds while this happens. Pressing the left-most toolbar button (`FF`)
  installs missing packages and shows a splash screen with the legal terms.
- If the toolbar is missing, load it from Rhino's "Toolbars" page.

## Data model: the CableMesh

The pattern is a `compas_fofin.datastructures.CableMesh`, a `compas.datastructures.Mesh`
with these defaults (`datastructures/cablemesh.py`):

| level | attribute | default | role in the solver |
|---|---|---|---|
| mesh | `density` | 1 | material density for selfweight |
| vertex | `is_support` | False | fixed node (anchor) |
| vertex | `constraint` | None | GUID of a geometric constraint; the vertex may slide on it |
| vertex | `px`, `py`, `pz` | 0 | nodal load components |
| vertex | `thickness` | 0 | surface thickness for selfweight (0 = no selfweight) |
| vertex | `_residual` | — | computed residual vector |
| edge | `q` | 1.0 | force density (Schek's *q = s / l*) |
| edge | `f`, `l`, `l0`, `E`, `radius` | 0 | stored for the DR inputs; unused by the FD command |
| edge | `_f` | — | computed force *q · l* |

Constraints are stored on the mesh in a `constraints` dictionary keyed by GUID
and are `compas_fd.constraints.Constraint` objects (line, plane, circle, curve,
surface, vector, frame). The whole model, including constraints, serialises as
COMPAS JSON through `compas_session` for undo/redo and save/open.

## Commands

All commands are Rhino commands (type the name, or use the toolbar):

| command | what it does |
|---|---|
| `FF` | info dialog, installs missing packages |
| `FF_pattern` | create a pattern from a Rhino box, cylinder, mesh, single NURBS surface (U/V resolution), or a MeshGrid (default 10 × 10 units, 10 × 10 faces) |
| `FF_anchors` | add/remove anchors (vertex selection by degree, boundary, manual, …) |
| `FF_anchors_constraints` | attach a geometric constraint to anchors |
| `FF_anchors_update` | re-project constrained anchors onto their constraints |
| `FF_anchors_move` | move anchors (e.g. along Z); equilibrium updates interactively |
| `FF_solve_fd` | "Solve equilibrium with a constrained, iterative variant of the force density method" |
| `FF_edges_q` | set `q` of selected edges to an absolute value, or scale them by a factor (interactive scaling redraws the equilibrium while dragging) |
| `FF_edges_delete` | remove edges from the pattern |
| `FF_vertices_attrs`, `FF_edges_attrs` | edit attributes (loads, thickness, q, …) |
| `FF_loads` | load input (present in the repository `commands/`, not yet in the documented toolbar list) |
| `FF_session_undo/redo/open/save/export` | session management; `autosave` is on by default |
| `FF_scene_clear`, `FF_scene_redraw`, `FF_settings` | scene and settings |

**Settings** (`FF_settings`, `settings.py`): solver `kmax = 100`,
`tol_residuals = 1e-3`, `tol_displacements = 1e-3`, `damping = 0.1`; drawing
options for loads, selfweight, reactions, residuals, forces with scale factors
(reactions 0.1, forces 1e-3) and display thresholds; display `tmax = 10`.

**Display conventions** (tutorial): edge forces are drawn as pipes coloured red
for tension, white near zero, blue for compression, with diameter proportional
to magnitude; reactions are green arrows scaled by `scale_reactions`.

## What `FF_solve_fd` computes

`commands/FF_solve_fd.py` → `compas_fofin.solvers.AutoUpdateFD`:

1. Update every constraint's geometry from the Rhino object and project the
   constrained vertices onto it (`CableMesh.update_constraints`).
2. Build `FDNumericalData.from_params(vertices, fixed, edges, q, loads)` with
   `fixed = vertices where is_support`, `loads = (px, py, pz)`, `q = edge attribute q`.
3. Build a `SelfweightCalculator(cablemesh, density, thickness_attr_name="thickness")`;
   with the default thickness 0 the selfweight is zero.
4. Loop up to `kmax` times: linear force density solve (`_solve_fd`, selfweight
   subtracted from *p_z*), then `_update_constraints` (move each constrained vertex by
   `damping × tangential residual` and re-project), until the tangential residuals
   are below `tol_residuals`. (The displacement test is always satisfied, see the
   caveat in [compas_fd](compas_fd.md).)
5. One final linear solve, then write back `x, y, z`, `_residual` per vertex and
   `_f` per edge; mark the mesh `is_solved`.

So the equilibrium shown in Rhino is exactly Schek's eq. (9) for the current *q*,
anchors, and loads, with anchors on constraints relaxed iteratively. The GitBook
theory page explains the method with a single free node attached to four anchors:
nodal equilibrium with direction cosines is nonlinear because the edge lengths
depend on the unknown coordinates; replacing *F_j / L_j* by a prescribed *q_j*
removes the lengths and leaves the linear system
*Σ q_j (x_j − x_0) = 0* per axis. The page's NumPy snippet is the body of
`fd_numpy` (connectivity matrix in CSR form, `A = Ciᵗ Q Ci`,
`b = p_free − Ciᵗ Q Cf x_fixed`, `spsolve`, then lengths, forces `q · l`, and
residuals `p − Cᵗ Q C x`). The full derivation and the nonlinear extension of the
original paper are in [compas_fd](compas_fd.md).

## Workflow from the tutorial (hypar)

1. `FF_pattern` → MeshGrid, defaults (10 × 10, 10 × 10 faces).
2. `FF_anchors` → Add → "Select By Degree" = 2 (the four corners).
3. `FF_solve_fd` → flat equilibrium with uniform *q = 1*.
4. `FF_anchors_move` → Z → Manual → lift two opposite corners; the mesh updates to a hypar.
5. `FF_edges_q` → scale the force densities of one boundary to straighten or
   curve it (higher *q* in the boundary cables straightens them, as in Schek's
   example with *q = 100* on the border).
6. `FF_anchors_constraints` → constrain a vertex to a line; `FF_solve_fd`.

Documented example families: tensile form-active (mechanically prestressed hypar,
conical, wave, arch-supported; funicular catenary cables), compressive form-active
(catenary arch with corrugations, vault with lips, obtained with negative *q*),
mixed (compressive arch supported), and advanced constraint cases (line constraints
for a convertible wave, curve constraints for geometry generation). Example JSON
sessions are in `gitbook/.gitbook/assets/`.

## Limitations and troubleshooting

- Rhino 8 only; no Grasshopper component in this version.
- Only the force density solver is wired to a command. The README advertises
  "constrained force-density and constrained dynamic relaxation solvers", but
  `compas_fofin` 0.15.3 contains no DR command; `E`, `radius`, `l0` edge attributes
  are stored for future use.
- Compression-only or mixed structures use negative *q*; a wrong sign
  distribution can make the system singular or flip the shape. Inspect the
  residual display and the coloured pipes.
- A free vertex not connected to any anchor through positive-*q* edges has no
  unique position (singular matrix); anchor it or change *q*.
- Constrained vertices must be anchors (`is_support = True`), otherwise the
  constraint is ignored by the solve.
- The solver prints an iteration counter to the Rhino console at each step.
- Python package naming: install the Rhino plugin via Yak, not `pip install
  compas_fofin`; the PyPI/project URLs in `pyproject.toml` still point to the old
  `compas_fofin` repository name, which redirects to `compas_fd`.

## References and provenance

- Block Research Group (2022–2025). *compas-FoFin: Numerical Form Finding for
  Rhinoceros.* <https://github.com/BlockResearchGroup/compas-FoFin>. Suggested
  citation from the GitBook "Citing FormFinder" page:

  ```bibtex
  @misc{compas-FoFin,
      title = {{compas-FoFin}: Numerical Form Finding for Rhinoceros},
      author = {Block Research Group},
      year = {2022},
      url = {https://github.com/BlockResearchGroup/compas-FoFin},
  }
  ```
- GitBook pages read 2026-10-15 (Markdown exports via the `.md` suffix): About,
  Getting Started, Tutorial, User Interface, Settings, Force Densities Method,
  Citing FormFinder. The FAQ and the Features/Limitations sections of About are
  empty at this date.
- Source read: `commands/FF_solve_fd.py`, `src/compas_fofin/solvers/autoupdatefd.py`,
  `solvers/interactivescalefd.py`, `datastructures/cablemesh.py`, `settings.py`,
  `requirements.txt`, `CHANGELOG.md` at commit `9ce50ac`. MIT licence.
- Theory references cited by the GitBook: Schek (1974); Veenendaal & Block (2012);
  Adriaenssens, Block, Veenendaal & Williams (2014). See [compas_fd](compas_fd.md).
- Verification status: documentation and source review only; the plugin was not
  run in Rhino for this note.

[Chapter README](README.md) · [compas_fd](compas_fd.md) · [compas_dr](compas_dr.md)
