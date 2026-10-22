"""Rebuild every figure of graphic-statics-student-course/figures from its source PDF at full quality (vector where the PDF is vector).

Pipeline per figure: (1) locate the existing crop on its source page by multi-scale template matching,
(2) regenerate that region from the PDF: SVG (true vector, text as paths) if the region is vector artwork,
native-resolution PNG/JPEG if it is an embedded raster, else a high-resolution PNG render, (3) re-apply the white boxes that
were blanked in the old crop (titles, captions, transcribed tables) by diffing old crop against a fresh render,
(4) rewrite the <img src> references in src/*.md.   Needs PyMuPDF (pip install --target <dir> pymupdf), OpenCV, Pillow.

  python3 tools/figrebuild.py map   [--files 4 20 63]      -> work/fig_map.json (location per figure, match score)
  python3 tools/figrebuild.py build [--files ...] [--min 0.80] -> writes new assets, updates the Markdown, keeps old file if the match is poor
"""
import sys, os, re, json, pathlib, argparse, time, math
sys.path.insert(0, "/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad"); sys.path.insert(0, "/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/pylib")
import numpy as np, cv2, pymupdf
from PIL import Image
from multiprocessing import Pool
from docs import docs
D = {d["id"]: d["path"] for d in docs}
ROOT = pathlib.Path("/home/pv/Downloads/Books"); BOOK = ROOT / "graphic-statics-student-course"; FIG = BOOK / "figures"
WORK = pathlib.Path("/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/work"); MAPF = WORK / "fig_map.json"
UNITS = {u["pos"]: u for u in json.load(open(ROOT / "tools" / "eth_units.json"))}
VT = 0.90
RW = 1400   # page width (px) of the matching render

def candidates(pos, name, ctx):
    """(docid, page) candidates for a figure"""
    u = UNITS[pos]; out = []
    srcs = []
    for s in u["src"]:
        p = s.rsplit(" ", 1)
        if len(p) == 2 and re.fullmatch(r"\d+-\d+", p[1]): srcs.append((p[0], int(p[1].split("-")[0]), int(p[1].split("-")[1])))
        else: srcs.append((s, 1, None))
    m = re.match(r"\d\d-([sb])(\d+)", name)
    if m:
        page = int(m.group(2))
        for d, a, b in srcs:
            n = len(pymupdf.open(D[d])) if b is None else b
            q = (page + 1) // 2 if d.endswith('teil-4') else page      # 2-up handout PDF
            if a <= q <= n: out.append((d, q))
        if m.group(1) == "b" and len(out) > 1: out = out[1:] + out[:1]
        return out
    sheets = [int(x) for x in re.findall(r"sheet (\d+)", ctx)]
    for d, a, b in srcs:
        n = len(pymupdf.open(D[d])) if b is None else b
        if sheets:
            for s in sheets[-1:]: 
                for q in (s, s - 1, s + 1):
                    if a <= q <= n: out.append((d, q))
        else:
            for q in range(a, n + 1): out.append((d, q))
    return out

def prep(a, sig=1.2): return cv2.GaussianBlur(255 - a, (0, 0), sig)
def try_scale(f, p, s):
    t = cv2.resize(f, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    H, W = p.shape
    if t.shape[0] >= H or t.shape[1] >= W or t.shape[0] < 24 or t.shape[1] < 24: return None
    r = cv2.matchTemplate(p, t, cv2.TM_CCOEFF_NORMED); _, mx, _, loc = cv2.minMaxLoc(r)
    return (mx, s, (loc[0], loc[1], t.shape[1], t.shape[0]))
def best_scale(f, p, grid):
    best = (0, None, None)
    for s in grid:
        r = try_scale(f, p, s)
        if r and r[0] > best[0]: best = r
    return best
def refine(f, p, best):
    if best[1]:
        for s in np.linspace(best[1] * 0.96, best[1] * 1.04, 17):
            r = try_scale(f, p, s)
            if r and r[0] > best[0]: best = r
    return best
def render_gray(doc, pno, W=RW):
    pg = doc[pno - 1]; z = W / pg.rect.width
    pm = pg.get_pixmap(matrix=pymupdf.Matrix(z, z), colorspace=pymupdf.csGRAY, alpha=False)
    return np.frombuffer(pm.samples, np.uint8).reshape(pm.height, pm.width)

def locate(job):
    pos, name, ctx = job
    path = FIG / name
    fig = cv2.imread(str(path), 0)
    if fig is None: return dict(figure=name, error="unreadable")
    f = prep(fig); res = dict(figure=name, pos=pos, score=0)
    cands = candidates(pos, name, ctx); many = len(cands) > 3
    grid = np.geomspace(0.35, 1.7, 22) if many else np.geomspace(0.2, 2.0, 60)
    best = None
    docs_open = {}
    for d, pno in cands:
        doc = docs_open.setdefault(d, pymupdf.open(D[d]))
        page = prep(render_gray(doc, pno))
        r = best_scale(f, page, grid)
        if best is None or r[0] > best[0][0]: best = (r, d, pno, page)
        if not many and r[0] > 0.9: break
    if best is None: return dict(figure=name, error="no candidates")
    r, d, pno, page = best
    if many: r = best_scale(f, page, np.geomspace(0.35, 1.7, 40))
    r = refine(f, page, r)
    mx, s, box = r
    res.update(doc=d, page=pno, score=float(mx), scale=float(s) if s else 0, box=[int(v) for v in box] if box else None, figsize=[fig.shape[1], fig.shape[0]])
    return res

def figures_of(files):
    jobs = []
    for pos in files:
        t = (BOOK / "src" / UNITS[pos]["file"]).read_text(); lines = t.split("\n")
        for m in re.finditer(r'<img src="figures/([^"]+)"', t):
            name = m.group(1)
            ln = t[:m.start()].count("\n")
            ctx = "\n".join(lines[max(0, ln - 40):ln])
            jobs.append((pos, name, ctx))
    # unique by name
    seen = set(); out = []
    for j in jobs:
        if j[1] in seen: continue
        seen.add(j[1]); out.append(j)
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["map", "build", "composite"]); ap.add_argument("--files", type=int, nargs="*"); ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--min", type=float, default=0.80)
    ap.add_argument("--vt", type=float, default=0.90, help="verification threshold")
    ap.add_argument("--only-kept", action="store_true", help="only figures that a previous build kept")
    a = ap.parse_args()
    files = a.files or sorted(UNITS)
    if a.cmd == "map":
        jobs = figures_of(files); t0 = time.time()
        old = json.load(open(MAPF)) if MAPF.exists() else {}
        with Pool(a.procs) as pl: res = pl.map(locate, jobs, chunksize=2)
        for r in res: old[r["figure"]] = r
        json.dump(old, open(MAPF, "w"), indent=0)
        sc = [r.get("score", 0) for r in res]
        print(len(res), "figures located in %.0fs" % (time.time() - t0), "| score>=0.9:", sum(s >= 0.9 for s in sc), " 0.8-0.9:", sum(0.8 <= s < 0.9 for s in sc), " <0.8:", sum(s < 0.8 for s in sc))

# ---------------------------------------------------------------- build
def extra_mask(old_gray, new_gray):
    """binary mask (old crop's size) of ink that the fresh render has but the old crop does not (neighbouring figures, titles,
    captions that were blanked); tolerant to 2 px misalignment of thin lines"""
    h, w = old_gray.shape
    if new_gray.shape != old_gray.shape: new_gray = cv2.resize(new_gray, (w, h), interpolation=cv2.INTER_AREA)
    allowed = cv2.dilate((old_gray < 215).astype(np.uint8), np.ones((7, 7), np.uint8))
    extra = ((new_gray < 190) & (allowed == 0)).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(extra)
    keep = np.zeros_like(extra)
    for i in range(1, n):
        if stats[i][4] >= 10: keep[lab == i] = 1
    return keep

def white_boxes(old_gray, new_gray):
    """tight rectangles (fractions) around clusters of extra ink, for SVG"""
    keep = extra_mask(old_gray, new_gray); h, w = keep.shape
    m = cv2.dilate(keep, np.ones((11, 11), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        out.append(((x - 2) / w, (y - 2) / h, (x + bw + 2) / w, (y + bh + 2) / h))
    return out, keep

def clip_of(entry, pg):
    z0 = RW / pg.rect.width; x, y, tw, th = entry["box"]
    return pymupdf.Rect(x / z0, y / z0, (x + tw) / z0, (y + th) / z0) & pg.rect

def classify(pg, clip):
    nvec = 0
    for d in pg.get_drawings():
        r = d["rect"]
        if r.width * r.height > 0.6 * pg.rect.width * pg.rect.height and d.get("fill") in ((1, 1, 1), None): continue
        if (r & clip).is_empty: continue
        if r.width < 0.5 and r.height < 0.5: continue
        nvec += 1
    cov = 0.0; best = None; nimg = 0
    for im in pg.get_image_info(xrefs=True):
        b = pymupdf.Rect(im["bbox"]); inter = b & clip
        if inter.is_empty: continue
        c = inter.get_area() / max(clip.get_area(), 1e-6)
        if c > 0.005: nimg += 1
        if c > cov: cov, best = c, im
    return nvec, cov, best, nimg

def blank(arr, mask):
    """white out the pixels of 'mask' (given at the old crop's resolution) on arr"""
    if mask is None or not mask.any(): return arr
    m = cv2.resize(mask.astype(np.uint8), (arr.shape[1], arr.shape[0]), interpolation=cv2.INTER_NEAREST)
    k = max(3, int(round(arr.shape[1] / mask.shape[1] * 2)) | 1)
    m = cv2.dilate(m, np.ones((k, k), np.uint8))
    arr[m > 0] = 255
    return arr

def bump_strokes(svg, minw=0.3):
    """hairlines (< minw pt) are almost invisible at figure size: raise them to minw (white mask strokes are left alone)"""
    def fix(m):
        el = m.group(0)
        if "stroke=\"rgb(100%, 100%, 100%)\"" in el: return el
        return re.sub(r'stroke-width="([\d.]+)"', lambda w: 'stroke-width="%s"' % (w.group(1) if float(w.group(1)) >= minw else minw), el)
    return re.sub(r"<path[^>]*>", fix, svg)

def make_svg(doc, entry, clip, boxes, mask, base):
    """true vector crop: cut the region out of the page (PyMuPDF), render it with poppler's pdftocairo (honours clipping/hidden layers),
    then append white rectangles over blanked neighbours and an opaque background (dark mode)"""
    import subprocess, tempfile
    tmp = pymupdf.open(); tmp.insert_pdf(doc, from_page=entry["page"] - 1, to_page=entry["page"] - 1); pg2 = tmp[0]
    mb = pg2.rect
    for rr in (pymupdf.Rect(mb.x0, mb.y0, mb.x1, clip.y0), pymupdf.Rect(mb.x0, clip.y1, mb.x1, mb.y1), pymupdf.Rect(mb.x0, clip.y0, clip.x0, clip.y1), pymupdf.Rect(clip.x1, clip.y0, mb.x1, clip.y1)):
        if rr.width > 0.5 and rr.height > 0.5: pg2.add_redact_annot(rr)
    pg2.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_REMOVE, graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED, text=pymupdf.PDF_REDACT_TEXT_REMOVE)
    pg2.set_cropbox(clip)
    with tempfile.TemporaryDirectory() as td:
        tmp.save(td + "/c.pdf"); tmp.close()
        r = subprocess.run(["pdftocairo", "-svg", td + "/c.pdf", td + "/c.svg"], capture_output=True, text=True)
        if r.returncode: raise ValueError("pdftocairo " + r.stderr[:40])
        svg = open(td + "/c.svg").read()
    m = re.search(r'<svg[^>]*width="([\d.]+)(?:pt)?"[^>]*height="([\d.]+)(?:pt)?"', svg)
    if not m: raise ValueError("svg header")
    wpt, hpt = float(m.group(1)), float(m.group(2))
    rects = "".join(f'<rect x="{b[0]*wpt:.2f}" y="{b[1]*hpt:.2f}" width="{(b[2]-b[0])*wpt:.2f}" height="{(b[3]-b[1])*hpt:.2f}" fill="#ffffff"/>' for b in boxes)
    svg = bump_strokes(svg)
    svg = svg.replace("</svg>", rects + "</svg>")
    svg = re.sub(r"(<svg[^>]*>)", r'\1<rect x="-1" y="-1" width="%.2f" height="%.2f" fill="#ffffff"/>' % (wpt + 2, hpt + 2), svg, count=1)
    svg = re.sub(r"<\?xml[^>]*\?>\s*", "", svg)
    if len(svg) > 1_000_000: raise ValueError("svg too large %d" % len(svg))
    p = FIG / (base + ".svg"); p.write_text(svg); return p

def make_raster(doc, entry, clip, boxes, mask, base, imbest):
    from io import BytesIO
    ex = doc.extract_image(imbest["xref"])
    im = Image.open(BytesIO(ex["image"])).convert("RGB"); iw, ih = im.size
    b = pymupdf.Rect(imbest["bbox"]); sx, sy = iw / b.width, ih / b.height
    X0, Y0 = int(round((clip.x0 - b.x0) * sx)), int(round((clip.y0 - b.y0) * sy)); X1, Y1 = int(round((clip.x1 - b.x0) * sx)), int(round((clip.y1 - b.y0) * sy))
    canvas = Image.new("RGB", (X1 - X0, Y1 - Y0), "white")
    cx0, cy0, cx1, cy1 = max(X0, 0), max(Y0, 0), min(X1, iw), min(Y1, ih)
    if cx1 > cx0 and cy1 > cy0: canvas.paste(im.crop((cx0, cy0, cx1, cy1)), (cx0 - X0, cy0 - Y0))
    canvas = Image.fromarray(blank(np.array(canvas), mask))
    if canvas.width > 1800: canvas = canvas.resize((1800, round(canvas.height * 1800 / canvas.width)), Image.LANCZOS)
    line = (np.array(canvas.convert('L')) > 245).mean() > 0.55
    p = FIG / (base + ".jpg"); canvas.save(p, quality=84, subsampling=0 if line else 2, optimize=True); return p

def make_hires(doc, entry, clip, boxes, mask, base):
    pg = doc[entry["page"] - 1]
    zz = min(max(1.3, 1600 / clip.width), 1800 / clip.width)
    pm2 = pg.get_pixmap(matrix=pymupdf.Matrix(zz, zz), clip=clip, alpha=False)
    arr = blank(np.array(Image.frombytes("RGB", (pm2.width, pm2.height), pm2.samples)), mask)
    im = Image.fromarray(arr)
    if (arr.mean(axis=2) > 245).mean() > 0.55:      # line art: small palette PNG (crisp, no JPEG ringing)
        p = FIG / (base + ".png"); im.quantize(colors=48, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(p, optimize=True)
    else:                                           # photo-like: JPEG
        p = FIG / (base + ".jpg"); im.save(p, quality=80, subsampling=2, optimize=True)
    return p

def verify(old, path):
    try:
        if path.suffix == ".svg":
            import cairosvg
            png = cairosvg.svg2png(url=str(path), output_width=old.shape[1], background_color="white")
            v = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_GRAYSCALE)
        else:
            v = cv2.imread(str(path), 0)
        v = cv2.resize(v, (old.shape[1], old.shape[0]), interpolation=cv2.INTER_AREA)
        sg = 3.0 if path.suffix == ".svg" else 1.5     # vector output strokes are heavier than the old anti-aliased raster: compare coarser structure
        a1 = cv2.GaussianBlur((255 - old > 40).astype(np.float32) * 255, (0, 0), sg); a2 = cv2.GaussianBlur((255 - v > 40).astype(np.float32) * 255, (0, 0), sg)
        return float(np.corrcoef(a1.ravel(), a2.ravel())[0, 1])
    except Exception:
        return -1.0

def build_one(args):
    entry, minscore, vt = args
    name = entry["figure"]; res = dict(figure=name)
    if entry.get("error") or entry.get("score", 0) < minscore or not entry.get("box"):
        res.update(status="kept", reason="score %.2f" % entry.get("score", 0)); return res
    old = cv2.imread(str(FIG / name), 0)
    doc = pymupdf.open(D[entry["doc"]]); pg = doc[entry["page"] - 1]
    clip = clip_of(entry, pg)
    if clip.width < 5 or clip.height < 5: res.update(status="kept", reason="empty clip"); return res
    zf = old.shape[1] / clip.width, old.shape[0] / clip.height
    pm = pg.get_pixmap(matrix=pymupdf.Matrix(*zf), clip=clip, colorspace=pymupdf.csGRAY, alpha=False)
    new = np.frombuffer(pm.samples, np.uint8).reshape(pm.height, pm.width)
    boxes, mask = white_boxes(old, new)
    nvec, cov, imbest, nimg = classify(pg, clip)
    base = name.rsplit(".", 1)[0]
    mode0 = "svg" if (nvec >= 3 and nimg == 0 and pg.rotation == 0) else ("raster" if (nimg == 1 and cov > 0.45 and nvec <= 3 and imbest) else "hires")
    order = {"svg": ["svg", "hires"], "raster": ["raster", "hires"], "hires": ["hires"]}[mode0]
    last = None; fails = []
    for mode in order:
        try:
            path = make_svg(doc, entry, clip, boxes, mask, base) if mode == "svg" else (make_raster(doc, entry, clip, boxes, mask, base, imbest) if mode == "raster" else make_hires(doc, entry, clip, boxes, mask, base))
        except Exception as e:
            last = f"{mode}: {str(e)[:40]}"; fails.append(last); continue
        corr = verify(old, path)
        if corr >= vt:
            res.update(fails=fails, vec0=mode0, status="rebuilt", mode=mode, new=path.name, bytes=path.stat().st_size, corr=round(corr, 3), boxes=len(boxes), vec=nvec, imgcov=round(cov, 2)); return res
        last = f"{mode} verify {corr:.2f}"; fails.append(last)
        if path.name != name and path.exists(): path.unlink()
    res.update(status="kept", reason=last or "failed", mode=mode0); return res

if __name__ == "__main__" and a.cmd == "build":
    VT = a.vt
    m = json.load(open(MAPF)); names = [j[1] for j in figures_of(files)]
    if a.only_kept: kept = {r['figure'] for r in json.load(open(WORK / 'fig_build.json')) if r['status'] == 'kept'}; names = [n for n in names if n in kept]
    jobs = [(m[n], a.min, a.vt) for n in names if n in m]; t0 = time.time()
    with Pool(a.procs) as pl: results = pl.map(build_one, jobs, chunksize=2)
    ren = {r["figure"]: r["new"] for r in results if r["status"] == "rebuilt"}
    for pos in files:
        p = BOOK / "src" / UNITS[pos]["file"]; t = p.read_text(); o = t
        for old_n, new_n in ren.items():
            if old_n != new_n: t = t.replace(f"figures/{old_n}", f"figures/{new_n}")
        if t != o: p.write_text(t)
    for old_n, new_n in ren.items():
        if old_n != new_n and (FIG / old_n).exists(): (FIG / old_n).unlink()
    if a.only_kept:
        prev = {r['figure']: r for r in json.load(open(WORK / 'fig_build.json'))}
        for r in results: prev[r['figure']] = r
        results_all = list(prev.values())
    else: results_all = results
    json.dump(results_all, open(WORK / "fig_build.json", "w"), indent=0)
    from collections import Counter
    c = Counter((r["status"], r.get("mode")) for r in results)
    print("built in %.0fs" % (time.time() - t0), dict(c), "kept reasons:", Counter(r.get("reason", "")[:16] for r in results if r["status"] == "kept").most_common(6))
    print("bytes new:", sum(r.get("bytes", 0) for r in results) // 1024, "KB")

# ---------------------------------------------------------------- composites
def panels_of(old):
    """split an old composite crop into ink panels: [(x0,y0,x1,y1)] in old px"""
    h, w = old.shape
    ink = (old < 200).astype(np.uint8)
    k = max(21, int(0.04 * w) | 1)
    big = cv2.dilate(ink, np.ones((k, k), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(big)
    out = []
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        sub = ink[y:y + bh, x:x + bw]
        ys, xs = np.where(sub > 0)
        if len(ys) < 60: continue
        out.append((x + xs.min(), y + ys.min(), x + xs.max() + 1, y + ys.max() + 1))
    return out

def locate_panel(old_panel, page, s0):
    f = prep(old_panel)
    grid = np.linspace(s0 * 0.88, s0 * 1.12, 25) if s0 else np.geomspace(0.3, 1.6, 30)
    r = best_scale(f, page, grid)
    return refine(f, page, r)

def prefix_ids(svg, pre):
    ids = set(re.findall(r'id="([^"]+)"', svg))
    for i in sorted(ids, key=len, reverse=True):
        svg = svg.replace(f'id="{i}"', f'id="{pre}{i}"').replace(f'#{i}"', f'#{pre}{i}"').replace(f'#{i})', f'#{pre}{i})').replace(f"#{i}'", f"#{pre}{i}'")
    return svg

def composite_one(args):
    entry, = args
    name = entry["figure"]; res = dict(figure=name, status="kept")
    old = cv2.imread(str(FIG / name), 0)
    if old is None or not entry.get("doc"): res["reason"] = "no old/doc"; return res
    h, w = old.shape
    doc = pymupdf.open(D[entry["doc"]]); pg = doc[entry["page"] - 1]; z0 = RW / pg.rect.width
    page = prep(render_gray(doc, entry["page"]))
    panels = panels_of(old)
    if not (2 <= len(panels) <= 9): res["reason"] = f"{len(panels)} panels"; return res
    located = []
    for (x0, y0, x1, y1) in panels:
        pad = 6; px0, py0, px1, py1 = max(x0 - pad, 0), max(y0 - pad, 0), min(x1 + pad, w), min(y1 + pad, h)
        sub = old[py0:py1, px0:px1]
        sc, s, box = locate_panel(sub, page, entry.get("scale"))
        if sc < 0.6 or not box: res["reason"] = "panel score %.2f" % sc; return res
        bx, by, tw, th = box
        clip = pymupdf.Rect(bx / z0, by / z0, (bx + tw) / z0, (by + th) / z0) & pg.rect
        located.append(((px0, py0, px1, py1), clip))
    # build every panel as raster (hi-res) or svg, then compose
    all_vec = True; parts = []
    for (px0, py0, px1, py1), clip in located:
        sub = old[py0:py1, px0:px1]
        zf = sub.shape[1] / clip.width, sub.shape[0] / clip.height
        pm = pg.get_pixmap(matrix=pymupdf.Matrix(*zf), clip=clip, colorspace=pymupdf.csGRAY, alpha=False)
        new = np.frombuffer(pm.samples, np.uint8).reshape(pm.height, pm.width)
        boxes, mask = white_boxes(sub, new)
        nvec, cov, imbest, nimg = classify(pg, clip)
        parts.append((px0, py0, px1, py1, clip, boxes, mask, nvec, nimg))
        if not (nvec >= 3 and nimg == 0 and pg.rotation == 0): all_vec = False
    base = name.rsplit(".", 1)[0]
    if all_vec:
        try:
            body = []
            for i, (px0, py0, px1, py1, clip, boxes, mask, nvec, nimg) in enumerate(parts):
                tmp_entry = dict(entry); tmp_entry["page"] = entry["page"]
                p = make_svg(doc, tmp_entry, clip, boxes, mask, f"__cmp{i}")
                s = p.read_text(); p.unlink()
                s = prefix_ids(s, f"p{i}_")
                s = re.sub(r"<\?xml[^>]*\?>\s*", "", s)
                m = re.search(r'<svg[^>]*width="([\d.]+)(?:pt)?"[^>]*height="([\d.]+)(?:pt)?"', s)
                sw, sh = float(m.group(1)), float(m.group(2))
                s = re.sub(r"<svg[^>]*>", f'<svg x="{px0}" y="{py0}" width="{px1-px0}" height="{py1-py0}" viewBox="0 0 {sw} {sh}" preserveAspectRatio="none">', s, count=1)
                body.append(s)
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="{w}" height="{h}" fill="#fff"/>' + "".join(body) + "</svg>"
            if len(svg) > 1_600_000: raise ValueError("svg too large")
            out = FIG / (base + ".svg"); out.write_text(svg); mode = "svg"
        except Exception as e:
            all_vec = False; res["note"] = str(e)[:40]
    if not all_vec:
        S = 2
        canvas = Image.new("RGB", (w * S, h * S), "white")
        for (px0, py0, px1, py1, clip, boxes, mask, nvec, nimg) in parts:
            pw, ph = (px1 - px0) * S, (py1 - py0) * S
            zz = pw / clip.width, ph / clip.height
            pm2 = pg.get_pixmap(matrix=pymupdf.Matrix(*zz), clip=clip, alpha=False)
            arr = blank(np.array(Image.frombytes("RGB", (pm2.width, pm2.height), pm2.samples)), mask)
            canvas.paste(Image.fromarray(arr), (px0 * S, py0 * S))
        out = FIG / (base + ".png"); canvas.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(out, optimize=True) if (np.array(canvas.convert("L")) > 245).mean() > 0.55 else None
        if not out.exists():
            out = FIG / (base + ".jpg"); canvas.save(out, quality=84, subsampling=0, optimize=True)
        mode = "png"
    # checks: structure correlation and no lost ink
    corr = verify(old, out)
    try:
        if out.suffix == ".svg":
            import cairosvg
            v = cv2.imdecode(np.frombuffer(cairosvg.svg2png(url=str(out), output_width=w, background_color="white"), np.uint8), cv2.IMREAD_GRAYSCALE)
        else: v = cv2.imread(str(out), 0)
        v = cv2.resize(v, (w, h), interpolation=cv2.INTER_AREA)
        oi = old < 150; ni = cv2.dilate((v < 205).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
        miss = float((oi & ~ni).sum() / max(oi.sum(), 1))
    except Exception: miss = 1.0
    if corr < 0.80 or miss > 0.05:
        if out.name != name and out.exists(): out.unlink()
        res.update(reason=f"check corr {corr:.2f} miss {miss:.3f} ({mode})", panels=len(panels)); return res
    res.update(status="rebuilt", mode="composite-" + mode, new=out.name, bytes=out.stat().st_size, corr=round(corr, 3), miss=round(miss, 3), panels=len(panels)); return res

if __name__ == "__main__" and a.cmd == "composite":
    m = json.load(open(MAPF)); rev = json.load(open(WORK / "fig_reverted.json")); names = [r[0] for r in rev]
    kept = [r["figure"] for r in json.load(open(WORK / "fig_build.json")) if r["status"] == "kept"]
    names = sorted(set(names) | set(kept))
    if a.files: names = [n for n in names if int(n[:2]) in a.files]
    jobs = [(m[n],) for n in names if n in m and m[n].get("doc") and m[n].get("score", 0) >= 0.45]
    t0 = time.time()
    with Pool(a.procs) as pl: results = pl.map(composite_one, jobs, chunksize=1)
    ren = {r["figure"]: r["new"] for r in results if r["status"] == "rebuilt"}
    for pos in sorted(UNITS):
        p = BOOK / "src" / UNITS[pos]["file"]; t = p.read_text(); o = t
        for old_n, new_n in ren.items():
            if old_n != new_n: t = t.replace(f"figures/{old_n}", f"figures/{new_n}")
        if t != o: p.write_text(t)
    for old_n, new_n in ren.items():
        if old_n != new_n and (FIG / old_n).exists(): (FIG / old_n).unlink()
    json.dump(results, open(WORK / "fig_composite.json", "w"), indent=0)
    from collections import Counter
    print("composite pass %.0fs" % (time.time() - t0), Counter((r["status"], r.get("mode")) for r in results), Counter(r.get("reason", "")[:22] for r in results if r["status"] == "kept").most_common(6))
