"""Render a scanned PDF of two-page spreads and split every spread into left/right page images.

  python3 -I tools/scan_split.py KEY ROT PDF [WORK]
      -> WORK/KEY/pages/sNNNL.jpg, sNNNR.jpg   (NNN = PDF page; default WORK = $BOOKS_WORK or <Books>/work)

ROT rotates each spread first (0, 90, -90). Check one spread before splitting a whole book: some scans are sideways
(Lévy II/III: -90) and some are not (Lévy IV, Wolfe: 0). The gutter is found as the darkest band in the middle of
the bright paper region, so a dark background around the book does not matter. Needs pdftoppm (poppler).
"""
import os, sys, glob, subprocess, pathlib
import numpy as np
from PIL import Image
from multiprocessing import Pool

if len(sys.argv) < 4:
    sys.exit(__doc__)
key, rot, pdf = sys.argv[1], int(sys.argv[2]), sys.argv[3]
work = sys.argv[4] if len(sys.argv) > 4 else os.environ.get("BOOKS_WORK", str(pathlib.Path(__file__).resolve().parent.parent / "work"))
base = f"{work}/{key}"


def split(f):
    n = int(f.split("-")[-1][:-4]); im = Image.open(f)
    if rot:
        im = im.rotate(rot, expand=True)
    g = np.asarray(im.convert("L").resize((im.width // 4, im.height // 4))).astype(float)
    prof = g[: int(g.shape[0] * 0.6)].mean(0); prof[:8] = 0; prof[-8:] = 0
    bright = np.where(prof > 150)[0]
    if len(bright) < 20:
        bright = np.arange(8, len(prof) - 8)
    x0, x1 = bright.min(), bright.max(); L = x1 - x0; lo, hi = x0 + int(L * 0.35), x0 + int(L * 0.65)
    sm = np.convolve(prof, np.ones(5) / 5, "same"); gx = (lo + int(np.argmin(sm[lo:hi]))) * 4
    im.crop((max(0, x0 * 4 - 30), 0, gx + 20, im.height)).save(f"{base}/pages/s{n:03d}L.jpg", quality=88)
    im.crop((gx - 20, 0, min(im.width, x1 * 4 + 30), im.height)).save(f"{base}/pages/s{n:03d}R.jpg", quality=88)
    os.remove(f)
    return n


if __name__ == "__main__":
    os.makedirs(f"{base}/pages", exist_ok=True); os.makedirs(f"{base}/spreads", exist_ok=True)
    if not glob.glob(f"{base}/spreads/s-*.jpg"):
        subprocess.run(["pdftoppm", "-r", "200", "-jpeg", "-jpegopt", "quality=88", pdf, f"{base}/spreads/s"], check=True)
    fs = sorted(glob.glob(f"{base}/spreads/s-*.jpg"))
    with Pool(8) as p:
        r = p.map(split, fs)
    print(key, len(r), "spreads split into", f"{base}/pages")
