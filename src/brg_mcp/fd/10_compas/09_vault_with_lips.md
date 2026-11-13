Vault with lips, fd_vault_with_lips.py: a compression-only vault under selfweight with stronger boundary loops.

Adapted from the COMPAS FormFinder vault example, PDF pages 102-112: https://github.com/BlockResearchGroup/compas-FoFin/blob/main/gitbook/examples-basic/compressive-form-active/vault-with-lips.md

Historical precedent: Heinz Isler's Tennishalle in Allschwil; see `04_references.md`.

```python
"""Vault with lips: q = -3 on the boundaries and q = -1 inside."""

from compas.datastructures import Mesh
from compas_fd.loads import SelfweightCalculator
from compas_fd.solvers import fd_numpy

mesh = Mesh.from_meshgrid(dx=10, nx=10)
mesh.update_default_vertex_attributes(t=0.1)
fixed = list(mesh.vertices_where(vertex_degree=2))

vertices = mesh.vertices_attributes("xyz")
edges = list(mesh.edges())
forcedensities = [-3.0 if mesh.is_edge_on_boundary(edge) else -1.0 for edge in edges]

selfweight = SelfweightCalculator(mesh, density=1.0)(vertices)
loads = [[0, 0, -weight[0]] for weight in selfweight]
result = fd_numpy(vertices=vertices, fixed=fixed, edges=edges, forcedensities=forcedensities, loads=loads)

print("crown:", result.vertices[60])
print("height range:", result.vertices[:, 2].min(), result.vertices[:, 2].max())
print("force range:", result.forces.min(), result.forces.max())
```
