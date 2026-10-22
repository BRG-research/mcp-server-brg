"""Rasterize figures/NAME.(svg|png|jpg) to a PNG for viewing (SVG via cairosvg) -> prints the path to Read.
  python3 tools/figview.py NAME [--old]      (--old: the figure as it was in git commit be812a2, i.e. the previous crop)"""
import sys, subprocess, pathlib, io
sys.path.insert(0, "/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/pylib")
from PIL import Image
name = sys.argv[1]; old = "--old" in sys.argv
F = pathlib.Path("/home/pv/Downloads/Books/graphic-statics-student-course/figures")
out = pathlib.Path("/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/work/view") / (name + ("-old" if old else "-view") + ".png"); out.parent.mkdir(parents=True, exist_ok=True)
if old:
    data = subprocess.run(["git", "-C", "/home/pv/Downloads/Books", "show", f"be812a2:graphic-statics-student-course/figures/{name}.jpg"], capture_output=True).stdout
    Image.open(io.BytesIO(data)).convert("RGB").save(out)
else:
    p = next(F.glob(name + ".*"))
    if p.suffix == ".svg":
        import cairosvg; cairosvg.svg2png(url=str(p), write_to=str(out), output_width=1300, background_color="white")
    else: Image.open(p).convert("RGB").save(out)
im = Image.open(out); print(out, im.size)
