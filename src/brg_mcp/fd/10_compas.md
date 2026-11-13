COMPAS

compas_fd is the force density package of COMPAS. Install it with `pip install compas_fd`, or `uv add compas_fd`.

The original compas_fd examples and standalone Python versions of every topology in the COMPAS FormFinder PDF are collected here.

Original compas_fd examples:

- [Hypar: one free node and four supports](10_compas/01_hypar.md)
- [Selfweight: nodal loads from tributary areas](10_compas/02_selfweight.md)

Mechanically prestressed and funicular topologies:

- [Hypar membrane](10_compas/03_hypar_membrane.md)
- [Conical membrane with a light eye](10_compas/04_conical.md)
- [Ridge and valley wave](10_compas/05_wave.md)
- [Arch supported membrane](10_compas/06_arch_supported.md)
- [Catenary cables](10_compas/07_catenary_cables.md)
- [Catenary arch with corrugations](10_compas/08_corrugated_arch.md)
- [Vault with lips](10_compas/09_vault_with_lips.md)
- [Compressive arch supported net](10_compas/10_compressive_arch.md)

Constrained topologies:

- [Convertible wave with line constraints](10_compas/11_convertible_wave.md)
- [Net with curve constrained boundaries](10_compas/12_curve_constraints.md)

Each example names its Python file, links its source, and can run without Rhino. The historical structures and their local images are in `04_references.md` and `04_references/`.

- compas_fd package and original commands: mcp_brg_compas_fd
- Original hypar command: mcp_brg_compas_fd_hypar
- Original selfweight command: mcp_brg_compas_fd_selfweight
- Historical references and images: mcp_brg_fd_references
