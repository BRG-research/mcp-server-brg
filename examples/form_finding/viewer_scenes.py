"""Convert the JSON scene descriptions written by schek_1974_figures.py into session .pb files
and session_viewer manifests.  Run with the Python that matches the viewer's session_rust
(the repository's own `uvsession` environment), because the .pb schema is versioned:

    /home/pv/brg/code_rust/session/uvsession/bin/python examples/form_finding/viewer_scenes.py \
        --scenes examples/form_finding/viewer_scenes/json --out examples/form_finding/viewer_scenes
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from session_py import Color, Line, Mesh, Point, Polyline, Session


def to_pb(src: Path, dst: Path):
    d = json.loads(src.read_text())
    s = Session(d["name"])
    for ln in d["lines"]:
        l = Line(*ln["a"], *ln["b"])
        l.width = float(ln["width"])
        l.linecolor = Color(*ln["color"])
        s.add_line(l)
    for pl in d["polylines"]:
        p = Polyline([Point(*xyz) for xyz in pl["pts"]])
        p.linecolor = Color(*pl["color"])
        p.width = float(pl.get("width", 0.02))   # never 1.0: the viewer treats 1.0 as "use the screen pen"
        # and the headless harness renders that pen far too wide (measured 2026-10-15)
        s.add_polyline(p)
    for mesh in d.get("meshes", []):
        # filled text: one mesh per glyph outer contour, holes included; name "text" and a zero line
        # width put it on the viewer's text lane (drawn last, no edge ink)
        contours = [[Point(*xyz) for xyz in c] for c in mesh["contours"]]
        m = Mesh.from_polygon_with_holes(contours, sort_by_bbox=True)
        m.name = "text"
        m.set_linecolors([Color(*mesh["color"])], widths=[0.0])
        m.set_objectcolor(Color(*mesh["color"]))
        s.add_mesh(m)
    for pt in d["points"]:
        p = Point(*pt["p"])
        p.width = float(pt["width"])
        p.pointcolor = Color(*pt["color"])
        s.add_point(p)
    s.pb_dump(str(dst))
    return len(d["lines"]), len(d["polylines"]), len(d["points"]), len(d.get("meshes", []))


def main(scenes: Path, out: Path):
    (out / "pb").mkdir(parents=True, exist_ok=True)
    (out / "scenes").mkdir(parents=True, exist_ok=True)
    layout = json.loads((scenes / "layout.json").read_text())
    for fig, spec in layout.items():
        toml = [f'name = "{fig}"']
        for file, at in spec["panels"]:
            pb = out / "pb" / (Path(file).stem + ".pb")
            nl, npl, npt, nm = to_pb(scenes / file, pb)
            toml += ["", "[[items]]", f'file = "pb/{pb.name}"', f'name = "{Path(file).stem}"',
                     f"at = [{at[0]}, {at[1]}, {at[2]}]"]
            print(f"{pb.name}: {nl} lines, {npl} polylines, {npt} points, {nm} glyph meshes")
        (out / "scenes" / f"{fig}.toml").write_text("\n".join(toml) + "\n")
        # one manifest per panel as well, for perspective views rendered panel by panel
        for file, at in spec["panels"]:
            stem = Path(file).stem
            (out / "scenes" / f"{stem}.toml").write_text(
                f'name = "{stem}"\n\n[[items]]\nfile = "pb/{stem}.pb"\nname = "{stem}"\nat = [0, 0, 0]\n')
    print("manifests in", out / "scenes")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve()
    ap.add_argument("--scenes", type=Path, default=here.parent / "viewer_scenes/json")
    ap.add_argument("--out", type=Path, default=here.parent / "viewer_scenes")
    a = ap.parse_args()
    main(a.scenes, a.out)
