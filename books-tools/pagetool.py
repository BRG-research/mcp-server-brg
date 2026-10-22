"""Page-image helper for transcription and figure crops.

  python3 -I tools/pagetool.py zoom KEY PAGE x0 y0 x1 y1 OUT.jpg
      zoomed crop with a 0.05 grid (coordinates are fractions of the page image); Read OUT.jpg
  python3 -I tools/pagetool.py crop KEY PAGE x0 y0 x1 y1 BOOKDIR NAME [--white x0,y0,x1,y1 ...] [--rot DEG] [--colour]
      -> BOOKDIR/figures/NAME.png and a preview BOOKDIR/.checks/check_NAME.png (Read it every time)

KEY   a book key: page images in $BOOKS_WORK/KEY/pages/PAGE.jpg (default BOOKS_WORK = <Books>/work),
      or an absolute directory of page images (then PAGE is the file name).
BOOKDIR is the book folder (NOT its figures/ folder; the tool adds figures/ itself).
Scans of printed books are whitened (paper tone removed). Use --colour for colour material (photos, PDF renders);
an absolute KEY keeps colour too.
"""
import os, sys, pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

WORK = pathlib.Path(os.environ.get("BOOKS_WORK", pathlib.Path(__file__).resolve().parent.parent / "work"))
a = sys.argv[1:]
if len(a) < 7:
    sys.exit(__doc__)
cmd, key, page = a[0], a[1], a[2]
src = (pathlib.Path(key) / page) if key.startswith("/") else (WORK / key / "pages" / f"{page}.jpg")
if not src.exists() and src.with_suffix(".png").exists():
    src = src.with_suffix(".png")
im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
rot = [float(a[i + 1]) for i in range(len(a) - 1) if a[i] == "--rot"]
W, H = im.size
x0, y0, x1, y1 = [float(v) for v in a[3:7]]
c = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
if cmd == "zoom":
    out = a[7]
    sc = min(2200 / c.width, 2200 / c.height, 3.0)
    c = c.resize((int(c.width * sc), int(c.height * sc)))
    d = ImageDraw.Draw(c)
    for k in range(0, 101, 5):
        f = k / 100
        if x0 <= f <= x1:
            X = int((f - x0) / (x1 - x0) * c.width); d.line([(X, 0), (X, c.height)], fill=(255, 0, 0)); d.text((X + 2, 2), f"{f:.2f}", fill=(255, 0, 0))
        if y0 <= f <= y1:
            Y = int((f - y0) / (y1 - y0) * c.height); d.line([(0, Y), (c.width, Y)], fill=(0, 0, 255)); d.text((2, Y + 2), f"{f:.2f}", fill=(0, 0, 255))
    c.save(out, quality=88)
    print(out, c.size)
else:
    od, name = pathlib.Path(a[7]), a[8]
    if od.name == "figures":
        od = od.parent  # a figures/ folder was passed: avoid figures/figures/
    for i in range(len(a) - 1):
        if a[i] == "--white":
            wx0, wy0, wx1, wy1 = [float(v) for v in a[i + 1].split(",")]
            ImageDraw.Draw(c).rectangle([int((wx0 - x0) / (x1 - x0) * c.width), int((wy0 - y0) / (y1 - y0) * c.height),
                                         int((wx1 - x0) / (x1 - x0) * c.width), int((wy1 - y0) / (y1 - y0) * c.height)], fill=(255, 255, 255))
    if key.startswith("/") or "--colour" in a:
        res = c
    else:
        g = c.convert("L")
        bg = g.filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(25))
        r = np.clip(np.asarray(g, float) / np.maximum(np.asarray(bg, float), 1), 0, 1)
        r = np.clip((r - 0.45) / 0.45, 0, 1)
        res = Image.fromarray((r * 255).astype("uint8")).convert("RGB")
    if rot:
        res = res.rotate(rot[0], expand=True, fillcolor=(255, 255, 255))
    (od / "figures").mkdir(parents=True, exist_ok=True); (od / ".checks").mkdir(exist_ok=True)
    res.save(od / "figures" / f"{name}.png"); res.save(od / ".checks" / f"check_{name}.png")
    print(od / "figures" / f"{name}.png", res.size, "-> Read", od / ".checks" / f"check_{name}.png")
