"""Make one figure directly from a page region of the source PDF, in the best format (SVG for vector art, native-resolution crop for an
embedded picture, hi-res render otherwise). Needs PyMuPDF + cairosvg (see figrebuild.py).

  python3 tools/figmake.py NAME DOCID PAGE x0 y0 x1 y1 [--white x0,y0,x1,y1 ...] [--mode auto|svg|raster|hires]
  python3 tools/figmake.py NAME DOCID PAGE --grid          -> grid preview of the page (fractions 0..1) in work/view/NAME-grid.jpg

x0..y1 and --white boxes are fractions of the displayed page. NAME is the figure name without extension (figures/NAME.svg|png|jpg);
an existing figures/NAME.* is replaced and the <img src> in src/*.md is rewritten if the extension changes.
"""
import sys, re, glob, pathlib, argparse
sys.argv_saved = sys.argv; sys.argv = ["figrebuild.py", "map"]
sys.path.insert(0, "/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad"); sys.path.insert(0, "/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/pylib"); sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import figrebuild as fr
sys.argv = sys.argv_saved
import numpy as np, pymupdf
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser(); ap.add_argument("name"); ap.add_argument("doc"); ap.add_argument("page", type=int)
ap.add_argument("box", type=float, nargs="*"); ap.add_argument("--white", action="append", default=[]); ap.add_argument("--mode", default="auto"); ap.add_argument("--grid", action="store_true")
a = ap.parse_args()
doc = pymupdf.open(fr.D[a.doc]); pg = doc[a.page - 1]; R = pg.rect
if a.grid:
    z = 1500 / R.width; pm = pg.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False)
    im = Image.frombytes("RGB", (pm.width, pm.height), pm.samples); d = ImageDraw.Draw(im); W, H = im.size
    for k in range(1, 20):
        d.line([(k * W / 20, 0), (k * W / 20, H)], fill=(255, 0, 0) if k % 2 == 0 else (255, 170, 170)); d.line([(0, k * H / 20), (W, k * H / 20)], fill=(0, 0, 255) if k % 2 == 0 else (170, 170, 255))
        d.text((k * W / 20 + 2, 2), f"{k/20:.2f}", fill=(255, 0, 0)); d.text((2, k * H / 20 + 2), f"{k/20:.2f}", fill=(0, 0, 255))
    out = pathlib.Path("/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/work/view") / (a.name + "-grid.jpg"); out.parent.mkdir(parents=True, exist_ok=True); im.save(out, quality=80)
    print("grid:", out, im.size); sys.exit(0)
x0, y0, x1, y1 = a.box
clip = pymupdf.Rect(R.x0 + x0 * R.width, R.y0 + y0 * R.height, R.x0 + x1 * R.width, R.y0 + y1 * R.height) & R
boxes = []
for w in a.white:
    bx0, by0, bx1, by1 = (float(v) for v in w.split(","))
    boxes.append(((bx0 * R.width + R.x0 - clip.x0) / clip.width, (by0 * R.height + R.y0 - clip.y0) / clip.height, (bx1 * R.width + R.x0 - clip.x0) / clip.width, (by1 * R.height + R.y0 - clip.y0) / clip.height))
mask = np.zeros((400, max(1, int(400 * clip.width / clip.height))), np.uint8)
for b in boxes: mask[max(int(b[1] * mask.shape[0]), 0):int(b[3] * mask.shape[0]) + 1, max(int(b[0] * mask.shape[1]), 0):int(b[2] * mask.shape[1]) + 1] = 1
nvec, cov, imbest, nimg = fr.classify(pg, clip)
mode = a.mode
if mode == "auto": mode = "svg" if (nvec >= 3 and nimg == 0 and pg.rotation == 0) else ("raster" if (nimg == 1 and cov > 0.45 and nvec <= 3 and imbest) else "hires")
entry = {"page": a.page}
for tryMode in ([mode, "hires"] if mode != "hires" else ["hires"]):
    try:
        path = fr.make_svg(doc, entry, clip, boxes, mask, a.name) if tryMode == "svg" else (fr.make_raster(doc, entry, clip, boxes, mask, a.name, imbest) if tryMode == "raster" else fr.make_hires(doc, entry, clip, boxes, mask, a.name))
        mode = tryMode; break
    except Exception as e: print("mode", tryMode, "failed:", e)
FIG = fr.FIG
for old in glob.glob(str(FIG / (a.name + ".*"))):
    if pathlib.Path(old).name != path.name: pathlib.Path(old).unlink(); oldname = pathlib.Path(old).name; 
for p in glob.glob(str(fr.BOOK / "src" / "[0-9]*.md")):
    t = pathlib.Path(p).read_text(); n = re.sub(r"figures/" + re.escape(a.name) + r"\.(?:jpg|png|svg)", "figures/" + path.name, t)
    if n != t: pathlib.Path(p).write_text(n)
print(f"{path.name}: {mode}, {path.stat().st_size//1024} KB (vec={nvec}, images={nimg}); view it with Read: {path}")
