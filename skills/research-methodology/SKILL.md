---
name: research-methodology
description: Develop or document reproducible BRG computational structural design experiments with explicit assumptions, provenance, and equilibrium checks.
---

# BRG research workflow

Use this for an experiment or research note in this repository.

- Identify the course domain and connect shared ideas through `knowledge/concepts/`.
- Separate cited findings, mathematical assumptions, and untested hypotheses.
- Record geometry, units, supports, loads, sign conventions, method parameters,
  software versions, and the criterion used to judge the result.
- Use `config/packages.yaml` to distinguish planned integrations from tested ones;
  a listed package is not evidence that a solver is available.
- For computational results, report convergence and residual tolerances alongside
  geometry. Distinguish equilibrium verification from stability assessment.
- For source-derived notes, retain source IDs, original page/figure references,
  extraction method, and review status. Use `docs/templates/knowledge-note.md`.

Add experiment artifacts or notes only when the user's request includes saving
work. Skills are client instructions, not server tools or permission to execute
unrequested workflows.
