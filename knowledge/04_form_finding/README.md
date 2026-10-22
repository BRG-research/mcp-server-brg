# Form Finding

## Sub-chapters

| Note | Package | Repository |
|---|---|---|
| [Force density method with compas_fd](compas_fd.md) | `compas_fd` — linear and constrained force density solvers; full derivation of Schek (1974) | <https://github.com/BlockResearchGroup/compas_fd> |
| [The same tutorial as a notebook](compas_fd.ipynb) | runnable cells with their outputs already stored | generated from `examples/form_finding/schek_app.py` |
| [Dynamic relaxation with compas_dr](compas_dr.md) | `compas_dr` — iterative solver with prescribed forces, lengths, and elastic bars | <https://github.com/BlockResearchGroup/compas_dr> |
| [COMPAS FormFinder (compas-FoFin)](compas_fofin.md) | Rhino 8 plugin that drives `compas_fd` interactively | <https://github.com/BlockResearchGroup/compas-FoFin> |

Theory source for all three: Schek, H.-J. (1974), *The force density method for
form finding and computation of general networks*, CMAME 3, 115–134, and the
[compas-FoFin GitBook theory page](https://blockresearchgroup.gitbook.io/compas-fofin/theoretical-background/force-densities-method).

## Walkthrough

Follow [the force density tutorial](compas_fd.md) in order:

1. **Part A:** vectors, matrices, node and branch numbering, and connectivity.
2. **Part B:** coordinates, branch lengths, and nodal equilibrium.
3. **Part C:** prescribed force densities and the linear equilibrium solve.
4. **Part D:** combine the steps into a reusable form-finding function.
5. **Part E:** understand the geometric meaning of force densities.
6. **Part F:** search for the force densities that also give wanted lengths and forces.
7. **Part G:** apply the method to the paper's reconstructed examples.

Each subsection has the same shape: what the step does, the equation, the stages
read right to left, and the same thing with the actual numbers of the 12-branch
net — every matrix printed with labelled rows and columns. Append each
implementation block in order; A.4 has no code. **D.2 completes the linear force
density method**; part F adds wishes about lengths and forces on top of it.

The tutorial exists in two forms, both generated from the same
`examples/form_finding/schek_app.py`: the Markdown note above, and
[compas_fd.ipynb](compas_fd.ipynb), a Jupyter notebook whose cells you can run and
change. The notebook ships with every output already stored, so it reads without
running anything.

The derivation uses NumPy directly, plus `scipy.optimize` in part F. Printed output
provides optional numerical checks. Matrices are shown as labelled numbers in the text rather than as diagrams;
the only images are the network figures of the paper. See the
[example README](../../examples/form_finding/README.md) for commands and how to
regenerate the tutorial. Compare with `compas_fd` after understanding the linear
solve; continue to `compas_dr` and other methods afterwards.

## Package integration to add

The NumPy derivation (`schek_app.py`), equation checks (`schek_equations.py`), and
tutorial generator (`build_note.py`) already exist in `examples/form_finding/`.
The package benchmark, reusable adapter, and MCP computation tool below remain
to be implemented.
Paths are relative to the repository root.

| File | Purpose |
|---|---|
| `knowledge/04_form_finding/compas_fd.md` | Explain the method, API, inputs/outputs, and limitations (written) |
| `examples/form_finding/force_density.py` | Run a small example with visible inputs and outputs |
| `tests/test_force_density.py` | Verify the result and invalid inputs |
| `src/brg_mcp/adapters/force_density.py` | Reusable computation and input validation |
| `src/brg_mcp/tools/form_finding.py` | Expose the adapter through MCP |

## Package integration workflow

1. **Inspect the package.**
   Read [the source](https://github.com/BlockResearchGroup/compas_fd/tree/main/src/compas_fd/solvers)
   and its examples. Record the tested version. Verify the import, solver signature,
   vertex/edge ordering, dependencies, and returned fields.

2. **Write the knowledge note.**
   Done: [compas_fd.md](compas_fd.md) follows the
   [note template](../../docs/templates/knowledge-note.md) and explains
   `q = force / length`, units, sign conventions, supports, loads, the verified API
   (0.5.4), common failures, and references. Extend it rather than adding a second
   force density note. Short explanatory snippets belong here; runnable programs
   belong in `examples/`.

3. **Run one standalone example.**
   Create `examples/form_finding/force_density.py` calling the package directly.
   Use the benchmark below. Keep its small input arrays in the script.
   Print coordinates, forces, and residuals. Add an example README with the
   dependency versions, installation command, and exact command to run it.

4. **Verify it.**
   Compare actual and expected results. Record tolerances and package version.
   Add `tests/test_force_density.py`, including invalid indices and mismatched arrays.
   First get this example and test working; then continue.

5. **Extract reusable code.**
   Put the calculation in `src/brg_mcp/adapters/force_density.py`.
   Validate inputs and return named results with documented units.
   Update the example and tests to use the adapter. It must work without MCP.

6. **Connect MCP.**
   Add a typed wrapper in `src/brg_mcp/tools/form_finding.py`.
   Register it in `src/brg_mcp/server.py`.
   Test the MCP call using the same benchmark.

7. **Register and link.**
   Add the note to `config/knowledge.yaml` as shown below.
   After tests pass, update `compas_fd` in `config/packages.yaml` with the tested
   version and only the implemented capabilities. Link the finished note and
   example from this chapter README. Restart MCP after catalog changes.

## First benchmark

- Units: metres and newtons; positive z points upward.
- Fixed nodes: `(-1,-1,0)`, `(1,-1,0)`, `(1,1,0)`, `(-1,1,0)`.
- Free node: `(0,0,0)`; connect it to each fixed node.
- Force densities: `1 N/m` on all four edges.
- Loads: `(0,0,-1) N` on the free node; zero elsewhere.
- Expected free-node position: `(0,0,-0.25) m`; supports unchanged.
- Check position error below `1e-9 m` and free-node equilibrium residual below
  `1e-9 N`. Support residuals need not vanish; check the package's reaction convention.

The benchmark was reproduced with `compas_fd` 0.5.4 and `compas_dr` 0.3.1 in a
throw-away environment (see the Verification sections of the sub-chapters).
The standalone package benchmark, adapter, and repository test remain to be added;
the NumPy tutorial programs already run independently.

## Register the note

The notes are already registered in `config/knowledge.yaml`. Maintain the
existing entries rather than appending duplicates; the structure is:

```yaml
- id: form-finding-compas-fd
  title: Force density method with compas_fd
  domain: form_finding
  path: knowledge/04_form_finding/compas_fd.md
  sources: [...]
```

- The three sub-chapter notes are already registered; keep their `sources`
  entries in step with the tested source revision.
- Ask MCP to search for “force density” and read the returned resource.
- Register the note as soon as it is useful; you need not wait for an executable MCP tool.

## Done when

- **Knowledge:** the explanation is searchable, with API usage and references.
- **Example:** a documented Python command reproduces the benchmark.
- **Tool:** adapter and MCP checks pass; package status reflects what works.

[Main README](../../README.md) · [Contribution guide](../../docs/contributing/README.md)
