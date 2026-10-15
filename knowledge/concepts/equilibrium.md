---
id: equilibrium
title: Structural equilibrium
status: draft
related_domains: [graphic_statics, form_finding, thrust_network_analysis, constructability]
---

# Structural equilibrium

This original starter note demonstrates a cross-domain concept. Add reviewed
references before treating it as course material.

For a pin-jointed structure at a prescribed geometry, write nodal equilibrium as

`A f + p = 0`

Here `A` maps axial member forces `f` to nodal force components, and `p` contains
external nodal forces, including reactions when using the full system. For a
system restricted to free degrees of freedom, support reactions are excluded.
State the sign convention and degrees of freedom when constructing `A`.

This formulation assumes axial members, ideal pins, and nodal loading. The
unknowns here are member forces, not force densities; a force-density formulation
uses a different matrix definition.

Check the residual `r = A f + p` against explicit absolute and load-relative
tolerances. Equilibrium alone does not establish stability or constructability.

## Provenance

Original illustrative text in this repository; no book extraction or verified
package implementation is associated with it yet.
