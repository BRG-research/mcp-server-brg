Hypar membrane, fd_hypar_membrane.py: a four-point sail with two raised corners and stronger edge cables.

Adapted from the COMPAS FormFinder hypar example, PDF pages 38-46: https://github.com/BlockResearchGroup/compas-FoFin/blob/main/gitbook/examples-basic/tensile-form-active/mechanically-prestressed/hypar.md

Historical precedent: Frei Otto's mechanically prestressed membrane at Bundesgartenschau Kassel, 1955; see `04_references.md`.

```python
"""Hypar membrane: opposite high supports and boundary cables with q = 5."""

from compas.datastructures import Mesh
from compas_fd.solvers import fd_numpy

mesh = Mesh.from_meshgrid(dx=10, nx=10)
fixed = list(mesh.vertices_where(vertex_degree=2))

for vertex in fixed:
    x, y, _ = mesh.vertex_attributes(vertex, "xyz")
    if x == y:
        mesh.vertex_attribute(vertex, "z", 2.0)

vertices = mesh.vertices_attributes("xyz")
edges = list(mesh.edges())
forcedensities = [5.0 if mesh.is_edge_on_boundary(edge) else 1.0 for edge in edges]

result = fd_numpy(vertices=vertices, fixed=fixed, edges=edges, forcedensities=forcedensities)

print("supports:", [(vertex, vertices[vertex]) for vertex in fixed])
print("height range:", result.vertices[:, 2].min(), result.vertices[:, 2].max())
print("force range:", result.forces.min(), result.forces.max())
```
