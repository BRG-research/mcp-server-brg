"""Crop only the relevant figure out of a slide/page of the ETH course PDFs (Levy style: figure only, all text goes to Markdown).

  python3 tools/figcrop.py DOCID PAGE NAME [--auto] [--crop x0 y0 x1 y1] [--white x0,y0,x1,y1 ...] [--full 1300] [--minw 0.0]

  DOCID  id from units.json / work/ folders      PAGE  PDF page (slide number)      NAME  output figures/NAME.jpg
  --auto   remove header/footer text lines (title, slide number, caption/scale lines under the drawing) found in the
           PDF text layer, then trim to the remaining drawing (whitespace trimmed, small margin)
  --crop   fractions (0..1) of the page: keep exactly this rectangle (applied after --auto's text removal)
  --white  fraction box to blank out inside the crop (neighbouring figure, stray text), repeatable
  --full   pixel width of the FULL page render the crop is taken from (default 1300): keeps text legible
Prints: crop box, size, the text lines that were removed (check each is present in the Markdown!) and the width to use in <img>.
"""
import sys, subprocess, pathlib, tempfile, argparse, re, html
sys.path.insert(0, "/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad"); sys.path.insert(0, "/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/pylib")
from docs import docs
import numpy as np
from PIL import Image
ap = argparse.ArgumentParser(); ap.add_argument("doc"); ap.add_argument("page", type=int); ap.add_argument("name")
ap.add_argument("--auto", action="store_true"); ap.add_argument("--crop", type=float, nargs=4)
ap.add_argument("--white", action="append", default=[]); ap.add_argument("--full", type=int, default=1500)
ap.add_argument("--prose", type=int, default=0, help="also blank every text line of at least N words (body text/captions) anywhere on the page")
ap.add_argument("--split", action="store_true", help="write one image per vertical band of ink separated by a blank gap (NAME, NAME-2, ...)")
ap.add_argument("--gap", type=float, default=0.05, help="blank gap (fraction of page height) that separates two bands for --split")
ap.add_argument("--force", action="store_true", help="allow overwriting extra split files that already exist")
ap.add_argument("--notrim", action="store_true", help="do not trim blank margins inside a manual --crop")
ap.add_argument("--lines", action="store_true", help="also print the text lines that are KEPT, with fraction boxes (x0,y0,x1,y1), to choose --white boxes")
ap.add_argument("--grid", action="store_true", help="only write a grid-annotated full-page preview (fractions 0.1 steps) to work/view and exit")
ap.add_argument("--band", type=float, default=0.14, help="height fraction treated as header/footer band for --auto")
a = ap.parse_args()
pdf = next(d["path"] for d in docs if d["id"] == a.doc)
OUT = pathlib.Path("/home/pv/Downloads/Books/graphic-statics-student-course/figures") / (a.name + ".jpg")
# page size in points AFTER rotation (pdftotext reports the displayed page)
bbox = subprocess.run(["pdftotext", "-f", str(a.page), "-l", str(a.page), "-bbox-layout", pdf, "-"], capture_output=True, text=True).stdout
m = re.search(r'<page width="([\d.]+)" height="([\d.]+)"', bbox)
PW, PH = float(m.group(1)), float(m.group(2))
rot = re.search(r"Page\s+%d rot:\s+(\d+)" % a.page, subprocess.run(["pdfinfo", "-f", str(a.page), "-l", str(a.page), pdf], capture_output=True, text=True).stdout)
if rot and int(rot.group(1)) in (90, 270): PW, PH = PH, PW     # line coordinates are in the displayed (rotated) frame
dpi = a.full / PW * 72
with tempfile.TemporaryDirectory() as t:
    subprocess.run(["pdftoppm", "-f", str(a.page), "-l", str(a.page), "-r", f"{dpi:.2f}", "-png", pdf, t + "/p"], check=True)
    im = Image.open(next(pathlib.Path(t).glob("p*.png"))).convert("RGB")
    W, H = im.size
    arr = np.array(im)
    removed = []; kept = []
    keep = []   # drawing/image areas (points, displayed frame): text lines overlapping them are figure labels and are kept
    try:
        import pymupdf
        pg = pymupdf.open(pdf)[a.page - 1]
        rr = pg.rect
        for d in pg.get_drawings():
            r = d["rect"]
            if r.width * r.height > 0.6 * rr.width * rr.height and d.get("fill") in ((1, 1, 1), None): continue   # page background
            if r.height < 2 and r.width > 0.4 * rr.width: continue                                              # header/footer rules
            if r.width < 1 and r.height < 1: continue
            keep.append((r.x0, r.y0, r.x1, r.y1))
        for im_ in pg.get_image_info():
            r = pymupdf.Rect(im_["bbox"])
            if r.width * r.height > 0.85 * rr.width * rr.height: continue                                        # full-slide raster
            keep.append((r.x0, r.y0, r.x1, r.y1))
    except Exception as e:
        print("note: PyMuPDF unavailable, text removal without figure protection:", e)
    def inside_figure(x0, y0, x1, y1):
        area = max((x1 - x0) * (y1 - y0), 1e-6)
        for kx0, ky0, kx1, ky1 in keep:
            ix = min(x1, kx1) - max(x0, kx0); iy = min(y1, ky1) - max(y0, ky0)
            if ix > 0 and iy > 0 and ix * iy > 0.3 * area: return True
        return False
    if a.grid:
        g = im.copy()
        from PIL import ImageDraw
        dr = ImageDraw.Draw(g)
        for k in range(1, 20):
            c = (255, 0, 0) if k % 2 == 0 else (255, 150, 150)
            dr.line([(k * W / 20, 0), (k * W / 20, H)], fill=c, width=1); dr.line([(0, k * H / 20), (W, k * H / 20)], fill=(0, 0, 255) if k % 2 == 0 else (150, 150, 255), width=1)
            dr.text((k * W / 20 + 2, 2), f"{k/20:.2f}", fill=(255, 0, 0)); dr.text((2, k * H / 20 + 2), f"{k/20:.2f}", fill=(0, 0, 255))
        gp = pathlib.Path("/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/work/view") / (a.name + "-grid.jpg"); gp.parent.mkdir(parents=True, exist_ok=True); g.save(gp, quality=80)
        print("grid preview:", gp, f"({W}x{H}); coordinates are fractions of the page, red = x, blue = y"); sys.exit(0)
    if a.auto or a.prose:
        x = bbox
        for ln in re.finditer(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', x, flags=re.S):
            lh = float(ln.group(4)) - float(ln.group(2))
            ws = [(float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), html.unescape(m.group(5)))
                  for m in re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', ln.group(5))]
            segs, cur = [], []
            for w in ws:   # split a text line where a wide gap separates a figure label from prose
                if cur and w[0] - cur[-1][2] > 2.2 * lh: segs.append(cur); cur = []
                cur.append(w)
            if cur: segs.append(cur)
            for sg in segs:
                x0, y0, x1, y1 = min(w[0] for w in sg), min(w[1] for w in sg), max(w[2] for w in sg), max(w[3] for w in sg)
                words = [w[4] for w in sg]
                txt = " ".join(words)
                fy0, fy1 = y0 / PH, y1 / PH
                in_band = fy1 < a.band or fy0 > 1 - a.band
                longish = True
                pagenum = re.fullmatch(r"\d{1,3}", txt) is not None and (fy1 < a.band or fy0 > 1 - a.band)
                prose = a.prose and len(words) >= a.prose
                if (in_band and longish) or pagenum or prose:
                    if inside_figure(x0, y0, x1, y1) and not pagenum:
                        kept.append((txt, x0 / PW, y0 / PH, x1 / PW, y1 / PH)); continue
                    px0, py0, px1, py1 = int((x0 - 4) / PW * W), int((y0 - 4) / PH * H), int((x1 + 5) / PW * W), int((y1 + 5) / PH * H)
                    arr[max(py0, 0):py1, max(px0, 0):px1] = 255; removed.append(txt)
    for wb in a.white:
        x0, y0, x1, y1 = (float(v) for v in wb.split(","))
        arr[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)] = 255
    if a.crop:
        x0, y0, x1, y1 = a.crop; X0, Y0, X1, Y1 = int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)
        if not a.notrim:   # trim blank margins inside the manual crop
            gsub = arr[Y0:Y1, X0:X1].mean(axis=2) < 244; ys_, xs_ = np.where(gsub)
            if len(ys_):
                mg = int(0.01 * W); X0, X1 = max(X0 + xs_.min() - mg, 0), min(X0 + xs_.max() + mg, W); Y0, Y1 = max(Y0 + ys_.min() - mg, 0), min(Y0 + ys_.max() + mg, H)
    else:
        g = arr.mean(axis=2); ink = g < 244
        ys, xs = np.where(ink)
        if len(ys) == 0: X0, Y0, X1, Y1 = 0, 0, W, H
        else:
            mg = int(0.012 * W); X0, X1 = max(xs.min() - mg, 0), min(xs.max() + mg, W); Y0, Y1 = max(ys.min() - mg, 0), min(ys.max() + mg, H)
    pieces = []
    if a.split and not a.crop:
        g = arr.mean(axis=2) < 244
        rows = g[:, X0:X1].any(axis=1); gap = int(a.gap * H); y = 0; start = None; blank = 0
        for yy in range(H):
            if rows[yy]:
                if start is None: start = yy
                blank = 0
            elif start is not None:
                blank += 1
                if blank > gap: pieces.append((start, yy - blank)); start = None; blank = 0
        if start is not None: pieces.append((start, H - 1))
        pieces = [(max(s - int(0.01 * W), 0), min(e + int(0.01 * W), H)) for s, e in pieces if e - s > 0.03 * H and not ((e - s) < 0.07 * H and (s < 0.1 * H or e > 0.9 * H))]
    if not pieces: pieces = [(Y0, Y1)]
    outs = []
    for k, (ya, yb) in enumerate(pieces):
        sub = arr[ya:yb, X0:X1]
        if a.split:   # trim each band horizontally
            gg = (sub.mean(axis=2) < 244).any(axis=0); xs2 = np.where(gg)[0]
            if len(xs2): sub = sub[:, max(xs2.min() - int(0.01 * W), 0):xs2.max() + int(0.01 * W)]
        outs.append(Image.fromarray(sub))
OUT.parent.mkdir(parents=True, exist_ok=True)
for k, o in enumerate(outs):
    fn = OUT if k == 0 else OUT.with_name(OUT.stem + f"-{k+1}.jpg")
    if k > 0 and fn.exists() and not a.force: print(f"SKIPPED {fn.name}: exists (use --force to overwrite)"); continue
    o.save(fn, quality=84)
    fw = o.size[0] / W
    ya, yb = pieces[k]
    print(f"{fn.name}: y {ya/H:.3f}-{yb/H:.3f} -> {o.size[0]}x{o.size[1]} px; use width={max(320, min(760, round(900*fw)))}")
if a.lines:
    # every text line on the page with its box, so --white boxes can be chosen
    for ln in re.finditer(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', bbox, flags=re.S):
        x0, y0, x1, y1 = (float(ln.group(i)) for i in range(1, 5)); wd = " ".join(html.unescape(w) for w in re.findall(r">([^<]+)</word>", ln.group(5)))
        print(f"  line {x0/PW:.3f},{y0/PH:.3f},{x1/PW:.3f},{y1/PH:.3f}: {wd[:70]}")
if removed: print("removed text:", " | ".join(removed))
