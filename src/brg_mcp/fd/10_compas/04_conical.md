Conical membrane with a light eye, fd_conical.py: two opposite edges at the raised centre are removed to open an eye.

Adapted from the COMPAS FormFinder conical example, PDF pages 47-63: https://github.com/BlockResearchGroup/compas-FoFin/blob/main/gitbook/examples-basic/tensile-form-active/mechanically-prestressed/conical.md

Historical precedent: Frei Otto and Rolf Gutbrod's German Pavilion at Expo 1967 in Montreal; see `04_references.md`.

```python
"""Conical membrane: a raised centre, a light eye, and reinforced boundaries."""

from compas.datastructures import Mesh
from compas_fd.solvers import fd_numpy

mesh = Mesh.from_meshgrid(dx=10, nx=10)
center = 60  # x = 5, y = 5
mesh.vertex_attribute(center, "z", 5.0)

removed = []
for u, v in mesh.edges():
    if center in (u, v):
        other = v if u == center else u
        if mesh.vertex_attribute(other, "x") == 5:
            removed.append((u, v))

edges = [edge for edge in mesh.edges() if edge not in removed]
neighbours = set(mesh.vertex_neighbors(center))
forcedensities = [5.0 if mesh.is_edge_on_boundary((u, v)) or u in neighbours or v in neighbours else 1.0 for u, v in edges]
fixed = list(mesh.vertices_on_boundary()) + [center]

result = fd_numpy(vertices=mesh.vertices_attributes("xyz"), fixed=fixed, edges=edges, forcedensities=forcedensities)

print("removed edges:", removed)
print("eye centre and apex:", result.vertices[center])
print("height range:", result.vertices[:, 2].min(), result.vertices[:, 2].max())
print("force range:", result.forces.min(), result.forces.max())
```
