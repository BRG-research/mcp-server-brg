---
name: session-viewer-notebook
description: Embed the live session viewer in a Jupyter notebook - build a session_py Session, show it with session_jupyter.show(session, name). Use when a notebook needs a 3D picture of a net, mesh, lines, points or a matrix, or when replacing matplotlib plots.
---

# Embed the session viewer in a notebook

A notebook shows geometry with the session viewer, never with matplotlib. One import, one call,
no paths and no helper file beside the notebook.

```python
from session_py import Color, Matrix, Point, Session
from session_jupyter import show

session = Session("my_net")
session.add_network(Matrix.from_rows(C.tolist()), Matrix.from_rows(np.column_stack([x, y, z]).tolist()))

show(session, "my_net")          # last line of the cell
```

`show` uploads the session to the viewer's storage (Cloudflare R2, bucket `session-viewer-data`)
and returns a frame with `https://petrasvestartas.github.io/session/?scene=view_<name>.yaml`.

## Steps

1. Compute with numpy as usual. Keep the calculation flat and readable.
2. Build one `Session` per picture.
   - A net from matrices: `session.add_network(connectivity, coordinates, colors, widths)`.
     `connectivity` is the branch-node matrix (one row per bar: `1` at its first node, `-1` at its
     second), `coordinates` has one row `x, y, z` per node. Both are kernel `Matrix` objects:
     `Matrix.from_rows(array.tolist())`. `colors` and `widths` are optional, one per bar.
   - Single objects: `session.add_line(Line(...))`, `session.add_point(Point(...))`.
   - A matrix as a picture: `session.add_matrix(matrix)`; set `matrix.name`, `matrix.cell` (size of
     one square) and place it with `session.set_xform(matrix.guid, Xform.translation(x, y, z))`.
3. End the cell with `show(session, "<scene_name>")`. Options: `view="top"` (or `front`, `iso`, …),
   `height=700`, `upload=False` to show what is already published without uploading.
4. Inside a function, `return show(session, name)` and call the function on the last line.

## Rules

- **Scene names are public addresses.** Use `<topic>_<notebook>_<step>`, letters, digits and
  underscores, e.g. `fdm_exercise_4_load`. Publishing a name again replaces what it showed; the
  storage keeps no history. Never reuse `live`, `local` or a name you did not create.
- **Widths are pixels.** `line.width = 3.0`, `point.width = 14.0`. Exactly `1.0` means "default".
- **Colours are 0 to 1.** `Color(0.84, 0.16, 0.16, 1.0)`.
- **No text labels from a session.** The viewer does not draw a kernel `Text` stored in a `.pb`.
  Explain numbering in the markdown cell, or use the object names (`n0`, `e12`) that
  `add_network` gives.
- **No helper modules, no shell lines, no hard-coded paths or URLs in the notebook.** If something
  is missing, add it to `session_jupyter` or the kernel, not to the notebook.
- Uploading needs the `[r2]` profile in `~/.aws/credentials`. Without it the stored frames still
  show the published scenes; a reader's own re-run raises a clear error from `show`.
- Always check the result: open the returned address in a WebGPU browser and look at it before
  reporting the notebook as done.

## Environment

```bash
pip install numpy session-jupyter        # brings session-py with it
```

Both packages are released from the `session` repository on every push to `main`
(`session_py`, `session_jupyter`). Say so in the notebook's first cell: `Needs: pip install numpy session-jupyter`.
To try unreleased kernel code, install the local copies instead:
`--with-editable <session>/session_py --with-editable <session>/session_jupyter`.

The viewer needs WebGPU in the program that shows the notebook (Chrome; VS Code on Linux needs the
WebGPU launch flags).

## Example

`knowledge/04_form_finding/force_density_method/notebooks/`: four force density exercises, each
picture one `Session` and one `show`.
