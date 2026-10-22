"""Render PDF pages FIRST..LAST (1-based) to OUTDIR/p####.jpg at 200 dpi (same as pdftoppm -r 200; needs PyMuPDF).
  python3 tools/pdf_render.py PDF OUTDIR FIRST LAST        (existing pages are skipped)
"""
import sys, pathlib, pymupdf

pdf, out, a, b = sys.argv[1], pathlib.Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)
d = pymupdf.open(pdf)
for n in range(a, min(b, d.page_count) + 1):
    dst = out / f"p{n:04d}.jpg"
    if not dst.exists():
        d[n - 1].get_pixmap(dpi=200, colorspace=pymupdf.csRGB).save(dst, jpg_quality=85)
print("rendered", a, "-", min(b, d.page_count), "of", d.page_count)
