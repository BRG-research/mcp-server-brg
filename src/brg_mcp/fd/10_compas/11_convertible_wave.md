Convertible wave, fd_convertible_wave.py: the ridge and valley wave with three intermediate supports free to slide on line constraints.

Adapted from the COMPAS FormFinder line constraints example, PDF pages 123-126: https://github.com/BlockResearchGroup/compas-FoFin/blob/main/gitbook/examples-advanced/line-constraints-convertible-wave.md

Historical precedent: convertible membrane roofing at Metzgergasse, Buchs; see `04_references.md`.

```python
"""Convertible wave: three supports slide between fixed corner anchors."""

from compas.datastructures import Mesh
from compas.geometry import Line
from compas_fd.constraints import Constraint
from compas_fd.solvers import fd_constrained_numpy

mesh = Mesh.from_meshgrid(dx=10, nx=20)
support_y = {0, 2.5, 5, 7.5, 10}
fixed = [
    vertex
    for vertex in mesh.vertices_on_boundary()
    if mesh.vertex_attribute(vertex, "x") == 0 and mesh.vertex_attribute(vertex, "y") in support_y
]
sliding = [
    vertex
    for vertex in mesh.vertices_on_boundary()
    if mesh.vertex_attribute(vertex, "x") == 10 and mesh.vertex_attribute(vertex, "y") in {2.5, 5, 7.5}
]
fixed += [
    vertex
    for vertex in mesh.vertices_on_boundary()
    if mesh.vertex_attribute(vertex, "x") == 10 and mesh.vertex_attribute(vertex, "y") in support_y
]

for vertex in fixed + sliding:
    if mesh.vertex_attribute(vertex, "y") in {2.5, 7.5}:
        mesh.vertex_attribute(vertex, "z", 2.5)

vertices = mesh.vertices_attributes("xyz")
edges = list(mesh.edges())
forcedensities = [
    10.0 if mesh.vertex_attribute(u, "y") == mesh.vertex_attribute(v, "y") and mesh.vertex_attribute(u, "y") in support_y else 1.0
    for u, v in edges
]
constraints = [None] * len(vertices)
for vertex in sliding:
    x, y, z = vertices[vertex]
    constraints[vertex] = Constraint(Line([x, y, z], [x, y + 1, z]))

result = fd_constrained_numpy(vertices=vertices, fixed=fixed, edges=edges, forcedensities=forcedensities, constraints=constraints, kmax=200)

print("sliding supports:", result.vertices[sliding])
print("height range:", result.vertices[:, 2].min(), result.vertices[:, 2].max())
print("force range:", result.forces.min(), result.forces.max())
```
