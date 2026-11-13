Catenary cables, fd_catenary_cables.py: parallel hanging cables under selfweight with very weak transverse edges.

Adapted from the COMPAS FormFinder catenary cables example, PDF pages 85-94: https://github.com/BlockResearchGroup/compas-FoFin/blob/main/gitbook/examples-basic/tensile-form-active/funicular/catenary-cables.md

Historical precedent: Eero Saarinen's Washington Dulles International Airport, 1962, and Poleni's drawing of Hooke's analogy; see `04_references.md`.

```python
"""Catenary cables: tributary selfweight and half-strength boundary cables."""

from compas.datastructures import Mesh
from compas_fd.loads import SelfweightCalculator
from compas_fd.solvers import fd_numpy

mesh = Mesh.from_meshgrid(dx=10, nx=10)
mesh.update_default_vertex_attributes(t=0.1)
fixed = [vertex for vertex in mesh.vertices_on_boundary() if mesh.vertex_attribute(vertex, "x") in {0, 10}]

vertices = mesh.vertices_attributes("xyz")
edges = list(mesh.edges())
forcedensities = []
for u, v in edges:
    y_u = mesh.vertex_attribute(u, "y")
    y_v = mesh.vertex_attribute(v, "y")
    if y_u != y_v:
        forcedensities.append(3.5e-6)
    else:
        forcedensities.append(0.175 if y_u in {0, 10} else 0.35)

selfweight = SelfweightCalculator(mesh, density=1.0)(vertices)
loads = [[0, 0, -weight[0]] for weight in selfweight]
result = fd_numpy(vertices=vertices, fixed=fixed, edges=edges, forcedensities=forcedensities, loads=loads)

print("lowest node:", result.vertices[result.vertices[:, 2].argmin()])
print("height range:", result.vertices[:, 2].min(), result.vertices[:, 2].max())
print("force range:", result.forces.min(), result.forces.max())
```
