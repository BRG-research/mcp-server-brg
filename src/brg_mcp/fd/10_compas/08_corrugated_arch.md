Catenary arch with corrugations, fd_corrugated_arch.py: negative force densities invert the hanging cables and alternating values create corrugations.

Adapted from the COMPAS FormFinder corrugated arch example, PDF pages 96-101: https://github.com/BlockResearchGroup/compas-FoFin/blob/main/gitbook/examples-basic/compressive-form-active/catenary-arch-with-corrugations.md

Historical precedents: Poleni's drawing of Hooke's analogy, Ctesiphon Arch, and Eladio Dieste's Navios Corporation Silos; see `04_references.md`.

```python
"""Corrugated arch: compression-only cables with alternating force densities."""

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
        forcedensities.append(-3.5e-6)
    elif y_u in {0, 10}:
        forcedensities.append(-0.175)
    else:
        forcedensities.append(-0.35 * (2.0 if y_u % 2 == 0 else 0.5))

selfweight = SelfweightCalculator(mesh, density=1.0)(vertices)
loads = [[0, 0, -weight[0]] for weight in selfweight]
result = fd_numpy(vertices=vertices, fixed=fixed, edges=edges, forcedensities=forcedensities, loads=loads)

print("midspan rises:", [round(result.vertices[5 * 11 + j, 2], 3) for j in range(1, 10)])
print("height range:", result.vertices[:, 2].min(), result.vertices[:, 2].max())
print("force range:", result.forces.min(), result.forces.max())
```
