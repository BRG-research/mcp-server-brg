"""Render one PDF page/slide of the ETH course material into the book's figures/ folder.

  python3 tools/slidefig.py DOCID PAGE NAME [--w 1000] [--crop x0 y0 x1 y1]

DOCID is the id used under /tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/work/ (e.g. 01-lecture-l1-equilibrium-lecture-slides).
Writes graphic-statics-student-course/figures/NAME.jpg (white background, JPEG q80) and prints its path.
--crop takes fractions (0..1) of the page, to keep only the diagram. Read the result to check it.
"""
import sys, subprocess, pathlib, tempfile, argparse
sys.path.insert(0, "/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad")
from docs import docs
from PIL import Image
ap = argparse.ArgumentParser(); ap.add_argument("doc"); ap.add_argument("page", type=int); ap.add_argument("name")
ap.add_argument("--w", type=int, default=1000); ap.add_argument("--crop", type=float, nargs=4); ap.add_argument("--view", action="store_true", help="scratch copy for reading only, not published")
a = ap.parse_args()
pdf = next(d["path"] for d in docs if d["id"] == a.doc)
out = (pathlib.Path("/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/work/view") if a.view else pathlib.Path("/home/pv/Downloads/Books/graphic-statics-student-course/figures")) / (a.name + ".jpg")
out.parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as t:
    subprocess.run(["pdftoppm", "-f", str(a.page), "-l", str(a.page), "-r", "200", "-png", pdf, t + "/p"], check=True)
    im = Image.open(next(pathlib.Path(t).glob("p*.png"))).convert("RGB")
if a.crop:
    W, H = im.size; x0, y0, x1, y1 = a.crop
    im = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
im = im.resize((a.w, int(im.height * a.w / im.width)), Image.LANCZOS)
im.save(out, quality=80); print(out, im.size)
