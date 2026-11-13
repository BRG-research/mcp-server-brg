Hypar, fd_hypar.py: one free node between four supports, solved with fd_numpy.

Source: https://github.com/BlockResearchGroup/compas_fd/blob/main/tests/test_hypar.py

```python
"""Force density: one free node hangs between four supports at the corners of a hypar."""

from compas_fd.solvers import fd_numpy

vertices = [
    [0, 0, 0],  # 0: free node, the start position does not matter
    [0, 0, 1],  # 1: support
    [1, 0, 0],  # 2: support
    [1, 1, 1],  # 3: support
    [0, 1, 0],  # 4: support
]
edges = [(0, 1), (0, 2), (0, 3), (0, 4)]
forcedensities = [1, 1, 1, 1]  # q = force / length of each cable

result = fd_numpy(vertices=vertices, fixed=[1, 2, 3, 4], edges=edges, forcedensities=forcedensities)

print("free node:", result.vertices[0])  # equal q: the average of the supports, [0.5 0.5 0.5]
print("forces:", result.forces.ravel())
print("lengths:", result.lengths.ravel())
```
