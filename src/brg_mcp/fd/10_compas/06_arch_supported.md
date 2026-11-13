Arch supported membrane, fd_arch_supported.py: an open semicylinder with two fixed arches and reinforced free edges.

Adapted from the COMPAS FormFinder arch supported example, PDF pages 71-83: https://github.com/BlockResearchGroup/compas-FoFin/blob/main/gitbook/examples-basic/tensile-form-active/mechanically-prestressed/arch-supported.md

Historical precedent: arch supported membranes at Poruklu Marina; see `04_references.md`.

```python
"""Arch supported membrane: weak longitudinal edges and strong free edge cables."""

from math import cos
from math import pi
from math import sin

from compas_fd.solvers import fd_numpy

nx = 4
ny = 16
radius = 5.0
length = 10.0

vertices = []
for i in range(nx + 1):
    y = length * i / nx
    for j in range(ny + 1):
        angle = pi * j / ny
        vertices.append([radius * cos(angle), y, radius * sin(angle)])

edges = []
forcedensities = []
for i in range(nx + 1):
    for j in range(ny):
        edges.append((i * (ny + 1) + j, i * (ny + 1) + j + 1))
        forcedensities.append(1.0)
for i in range(nx):
    for j in range(ny + 1):
        edges.append((i * (ny + 1) + j, (i + 1) * (ny + 1) + j))
        forcedensities.append(5.0 if j in {0, ny} else 0.1)

fixed = list(range(ny + 1)) + list(range(nx * (ny + 1), (nx + 1) * (ny + 1)))
result = fd_numpy(vertices=vertices, fixed=fixed, edges=edges, forcedensities=forcedensities)

print("height range:", result.vertices[:, 2].min(), result.vertices[:, 2].max())
print("force range:", result.forces.min(), result.forces.max())
print("middle ring:", result.vertices[2 * (ny + 1):3 * (ny + 1)])
```
