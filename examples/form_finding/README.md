# Form finding examples

Scripts behind the figures and printed matrices of
[knowledge/04_form_finding/compas_fd.md](../../knowledge/04_form_finding/compas_fd.md).

| Script | Needs | Does |
|---|---|---|
| `schek_app.py` | numpy | The force density application written from the paper, section by section: one cell per section of Schek (1974), prose docstring plus the code that adds it, including a matrix primer. Run it top to bottom; section 5 computes every shape of figures 1 and 5 to 10 and writes `viewer_scenes/json/shapes.json`. |
| `build_note.py` | numpy | Executes the cells of `schek_app.py` and writes them (prose, code, printed output) into the tutorial section of `knowledge/04_form_finding/compas_fd.md`. |
| `schek_equations.py` | numpy, scipy | Every numbered equation as a separate function with finite-difference checks of all Jacobians; the test bench behind the application. |
| `schek_1974_figures.py` | numpy, fonttools | Draws figures 2 to 4 and turns the tutorial's `shapes.json` into scene descriptions for figures 1 and 5 to 10 (JSON: lines, polylines, points, glyph meshes); it computes nothing itself. Text is filled: glyph outlines from the viewer's JetBrains Mono font, triangulated by the session kernel onto the viewer's text lane. |
| `viewer_scenes.py` | `session_py` matching the viewer's `session_rust` | Converts the JSON scenes into session `.pb` files and `session_viewer` manifests in `viewer_scenes/`. |
| `render_figures.sh` | the viewer's headless harness, Pillow | Renders every manifest to PNG in `knowledge/04_form_finding/images/`. |

## Regenerate the note's tutorial section

```bash
python examples/form_finding/build_note.py
```

## Rebuild the figures

```bash
# 0. the tutorial program computes every shape of figures 1 and 5-10 and writes viewer_scenes/json/shapes.json
python examples/form_finding/schek_app.py

# 1. scene data from those shapes (any Python with numpy + fonttools)
python examples/form_finding/schek_1974_figures.py

# 2. .pb files and manifests (the viewer repository's own Python, so the .pb schema matches)
~/brg/code_rust/session/uvsession/bin/python examples/form_finding/viewer_scenes.py

# 3. headless renders (build the harness once; Pillow is needed for PPM -> PNG and cropping)
(cd ~/brg/code_rust/session/session_viewer && cargo build --example selftest --release --target x86_64-unknown-linux-gnu)
PYTHON=/path/to/python-with-pillow bash examples/form_finding/render_figures.sh
```

Harness knobs used by the render script (all environment variables of
`session_viewer/examples/selftest.rs`): `VIEWER_W`, `VIEWER_H` (pixels),
`VIEWER_VIEW=top` (orthographic plan), `VIEWER_ORBIT="yaw,pitch"` (perspective,
0.005 rad per unit), `VIEWER_SKIP=grid` (no grid and axes), and `VIEWER_BG=1,1,1`
(white background; added to the harness for these figures).

Two things learned about the viewer while doing this:

- A line or polyline width of exactly `1.0` (the kernel default) means "use the
  screen-constant pen", and the headless harness draws that pen far too wide. Every
  stroke in the scenes therefore carries an explicit world-unit width.
- The viewer has no text lane for strings, but it has one for meshes named `text`
  with a zero line width (drawn last, no edge ink). Labels are therefore glyph
  outlines triangulated with `Mesh.from_polygon_with_holes`, one mesh per outer
  contour with its holes; passing two separate outlines in one call turns the
  second into a hole.
- A row of three nets recedes from a perspective camera, so perspective panels are
  rendered one by one and pasted side by side; plan rows are one scene rendered with
  `VIEWER_VIEW=top`.

## Benchmark from the chapter README

The four-cable benchmark (free node at the origin, anchors at (±1, ±1, 0), q = 1,
load −1) is reproduced in the Verification sections of the `compas_fd` and `compas_dr`
notes; a standalone script for it is still to be added here.
