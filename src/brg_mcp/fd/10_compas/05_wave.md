Ridge and valley wave, fd_wave.py: alternating high and low anchors with integrated ridge and valley cables.

Adapted from the COMPAS FormFinder wave example, PDF pages 64-70: https://github.com/BlockResearchGroup/compas-FoFin/blob/main/gitbook/examples-basic/tensile-form-active/mechanically-prestressed/wave.md

Historical precedent: convertible membrane roofing at Metzgergasse, Buchs; see `04_references.md`.

```python
"""Ridge and valley wave: five cables with q = 10 span between alternating anchors."""

from compas.datastructures import Mesh
from compas_fd.solvers import fd_numpy

mesh = Mesh.from_meshgrid(dx=10, nx=20)
support_y = {0, 2.5, 5, 7.5, 10}
fixed = [
    vertex
    for vertex in mesh.vertices_on_boundary()
    if mesh.vertex_attribute(vertex, "x") in {0, 10} and mesh.vertex_attribute(vertex, "y") in support_y
]

for vertex in fixed:
    if mesh.vertex_attribute(vertex, "y") in {2.5, 7.5}:
        mesh.vertex_attribute(vertex, "z", 2.5)

vertices = mesh.vertices_attributes("xyz")
edges = list(mesh.edges())
forcedensities = [
    10.0 if mesh.vertex_attribute(u, "y") == mesh.vertex_attribute(v, "y") and mesh.vertex_attribute(u, "y") in support_y else 1.0
    for u, v in edges
]

result = fd_numpy(vertices=vertices, fixed=fixed, edges=edges, forcedensities=forcedensities)

print("alternating anchors:", result.vertices[fixed])
print("height range:", result.vertices[:, 2].min(), result.vertices[:, 2].max())
print("force range:", result.forces.min(), result.forces.max())
```
