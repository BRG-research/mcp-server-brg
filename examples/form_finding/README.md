# Form finding examples

Scripts behind the figures and printed matrices of
[knowledge/04_form_finding/compas_fd.md](../../knowledge/04_form_finding/compas_fd.md).

| Script | Needs | Does |
|---|---|---|
| `schek_1974_walkthrough.py` | numpy, scipy (compas_fd optional) | Prints every matrix of the force density derivation on Schek's figure 2 network, checks Theorem 1, the Jacobian (31) and the damped iteration, and cross-checks `compas_fd.fd_numpy`. |
| `schek_1974_figures.py` | numpy, fonttools | Rebuilds the paper's figures 1 to 10 as scene descriptions (JSON: lines, polylines, points). Text is glyph outlines from the viewer's JetBrains Mono font. |
| `viewer_scenes.py` | `session_py` matching the viewer's `session_rust` | Converts the JSON scenes into session `.pb` files and `session_viewer` manifests in `viewer_scenes/`. |
| `render_figures.sh` | the viewer's headless harness, Pillow | Renders every manifest to PNG in `knowledge/04_form_finding/images/`. |

## Rebuild the figures

```bash
# 1. scene data (any Python with numpy + fonttools)
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
- A row of three nets recedes from a perspective camera, so perspective panels are
  rendered one by one and pasted side by side; plan rows are one scene rendered with
  `VIEWER_VIEW=top`.

## Benchmark from the chapter README

The four-cable benchmark (free node at the origin, anchors at (±1, ±1, 0), q = 1,
load −1) is reproduced in the Verification sections of the `compas_fd` and `compas_dr`
notes; a standalone script for it is still to be added here.
