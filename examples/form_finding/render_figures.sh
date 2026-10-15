#!/usr/bin/env bash
# Render the Schek (1974) figure scenes with the session_viewer headless harness.
#   bash examples/form_finding/render_figures.sh
# Requires: the harness binary built with
#   (cd ~/brg/code_rust/session/session_viewer && cargo build --example selftest --release --target x86_64-unknown-linux-gnu)
# and a Python with Pillow for the PPM -> cropped PNG step (PYTHON env var, default: python3).
# Plan views are one scene with the three panels in a row (VIEWER_VIEW=top, orthographic).
# Perspective views are rendered panel by panel (a row recedes from a perspective camera) and
# pasted side by side, which is also how the paper lays them out.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
VIEWER="${VIEWER:-$HOME/brg/code_rust/session/session_viewer}"
BIN="${BIN:-$VIEWER/target/x86_64-unknown-linux-gnu/release/examples/selftest}"
PY="${PYTHON:-python3}"
SCENES="$HERE/viewer_scenes/scenes"
OUT="${OUT:-$HERE/../../knowledge/04_form_finding/images}"
TMP="${TMPDIR:-/tmp}/schek_render"; rm -rf "$TMP"; mkdir -p "$TMP" "$OUT"
export VIEWER_SKIP=grid VIEWER_BG=1,1,1
ORBIT="${ORBIT:-35,-30}"        # yaw, pitch in the harness's mouse units (0.005 rad each)
ORBIT2="${ORBIT2:--200,-10}"

render() { # out.ppm manifest w h [env...]
  local out=$1 man=$2 w=$3 h=$4; shift 4
  env VIEWER_W=$w VIEWER_H=$h "$@" "$BIN" "$TMP/$out.ppm" "$SCENES/$man.toml" | tail -1
}
# single plan drawings
render fig2 fig2 3000 1600 VIEWER_VIEW=top
render fig3 fig3 2400 2800 VIEWER_VIEW=top
render fig4 fig4 3000 1100 VIEWER_VIEW=top
render fig5 fig5 2600 2600 VIEWER_VIEW=top
for ic in icon_split icon_matvec icon_transpose icon_diag icon_D icon_solve icon_rhs; do render $ic $ic 3600 2000 VIEWER_VIEW=top; done
# figure 1: two perspective views of the same net
render fig1_a fig1_net 2000 1600 VIEWER_ORBIT="$ORBIT"
render fig1_b fig1_net 2000 1600 VIEWER_ORBIT="$ORBIT2"
# figures 6-10: plan row in one go, perspective panel by panel
for f in fig6 fig7 fig8 fig9 fig10; do
  render ${f}_plan $f 3600 1400 VIEWER_VIEW=top
  for n in 1 2 3; do render ${f}_p$n ${f}_$n 1600 1300 VIEWER_ORBIT="$ORBIT"; done
done
"$PY" - "$TMP" "$OUT" <<'PYEOF'
import sys
from pathlib import Path
from PIL import Image, ImageChops
tmp, out = Path(sys.argv[1]), Path(sys.argv[2])
def crop(im, m=40):
    box = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    if not box: return im
    return im.crop((max(box[0]-m, 0), max(box[1]-m, 0), min(box[2]+m, im.width), min(box[3]+m, im.height)))
def load(name): return crop(Image.open(tmp / f"{name}.ppm").convert("RGB"))
def row(ims, gap=60):
    h = max(i.height for i in ims); w = sum(i.width for i in ims) + gap * (len(ims) - 1)
    sheet = Image.new("RGB", (w, h), (255, 255, 255)); x = 0
    for i in ims:
        sheet.paste(i, (x, h - i.height)); x += i.width + gap      # bottom-aligned, like the paper
    return sheet
for name in ["fig2", "fig3", "fig4", "fig5"] + [f"fig{k}_plan" for k in range(6, 11)] + ["icon_split", "icon_matvec", "icon_transpose", "icon_diag", "icon_D", "icon_solve", "icon_rhs"]:
    im = load(name); im.save(out / f"schek_{name}.png", optimize=True); print(name, im.size)
row([load("fig1_a"), load("fig1_b")]).save(out / "schek_fig1.png", optimize=True)
for k in range(6, 11):
    im = row([load(f"fig{k}_p{n}") for n in (1, 2, 3)])
    im.save(out / f"schek_fig{k}_persp.png", optimize=True); print(f"fig{k}_persp", im.size)
PYEOF
