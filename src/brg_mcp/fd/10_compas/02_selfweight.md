Selfweight, fd_selfweight.py: the selfweight of every node of a grid, from its tributary area.

Source: https://github.com/BlockResearchGroup/compas_fd/blob/main/tests/test_selfweight.py

```python
"""Selfweight: the load of every node of a 10 x 10 grid, from its tributary area."""

from compas.datastructures import Mesh
from compas_fd.loads import SelfweightCalculator

mesh = Mesh.from_meshgrid(dx=10, nx=10)  # 10 by 10 faces of 1 by 1
mesh.update_default_vertex_attributes(t=1.0)  # thickness

density = 1
calculator = SelfweightCalculator(mesh, density=density)
selfweight = calculator(mesh.vertices_attributes("xyz"))

# A corner node carries 1/4 of a face, an edge node 1/2, an inner node 1.
for vertex in [0, 1, 12]:
    print("node", vertex, "degree", mesh.vertex_degree(vertex), "selfweight", selfweight[vertex, 0])
print("total:", selfweight.sum())  # 10 x 10 x thickness x density = 100
```
