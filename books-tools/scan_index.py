"""Build the scanned-page index of a book: resized page images plus a SCANS.md table.

  python3 -I tools/scan_index.py PAGES MAPPING.csv OUT --pdf RAW_PDF_NAME [--colour] [--size 1600]
         [--quality 80] [--missing "TEXT"] [--note "TEXT"] [--no-images]

PAGES      directory with the page images (e.g. work/<key>/pages/sNNNL.jpg, sNNNR.jpg from scan_split.py)
MAPPING    CSV with the header  image,kind,label
             image  page image name without .jpg (e.g. s065R); one image may appear on several rows.
                    A value containing "/" (e.g. plates/PlIII.jpg) is a file already in the book folder:
                    it is linked as given and not exported.
             kind   page   a printed page (label = printed number, arabic or roman, e.g. 117 or xii)
                    plate  a plate or fold-out (label e.g. "Pl. III")
                    other  cover, endpaper, blank leaf, ... (label is free text)
           Rows are written in file order, so sort the CSV in reading order of the book.
OUT        output folder, laid out like the book folder in R2:
             OUT/scans/<image>.jpg   long side SIZE px, JPEG QUALITY, greyscale unless --colour
             OUT/SCANS.md            intro line linking ../RAW/<RAW_PDF_NAME>, then a table
                                     | Printed page | Scan |, then plates/fold-outs and other images,
                                     then a last line for pages not in the scan (--missing).
--note     an extra sentence placed after the intro (e.g. about duplicated or reordered images).
--no-images  write SCANS.md only (images already exported).

Images not named in the CSV are not exported. Upload afterwards, e.g.
  aws s3 sync OUT/scans s3://brg-books/<book>/scans  and  aws s3 cp OUT/SCANS.md s3://brg-books/<book>/SCANS.md
"""
import argparse, csv, os, sys
from PIL import Image


def resize(src, dst, size, quality, colour):
    im = Image.open(src)
    im = im.convert("RGB" if colour else "L")
    s = size / max(im.size)
    if s < 1:
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    im.save(dst, quality=quality, optimize=True, progressive=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pages"); ap.add_argument("mapping"); ap.add_argument("out")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--colour", action="store_true")
    ap.add_argument("--size", type=int, default=1600)
    ap.add_argument("--quality", type=int, default=80)
    ap.add_argument("--missing", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--no-images", action="store_true")
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.mapping, newline="")))
    for r in rows:
        if r["kind"] not in ("page", "plate", "other"):
            sys.exit(f"bad kind in row {r}")
        if "/" not in r["image"] and not os.path.exists(f"{a.pages}/{r['image']}.jpg") and not a.no_images:
            sys.exit(f"missing image {a.pages}/{r['image']}.jpg")
    os.makedirs(f"{a.out}/scans", exist_ok=True)
    if not a.no_images:
        for img in dict.fromkeys(r["image"] for r in rows if "/" not in r["image"]):
            resize(f"{a.pages}/{img}.jpg", f"{a.out}/scans/{img}.jpg", a.size, a.quality, a.colour)

    link = lambda img: f"[{img.rsplit('/', 1)[-1].rsplit('.', 1)[0]}]({img})" if "/" in img else f"[{img}](scans/{img}.jpg)"
    L = ["# Scans", "",
         f"Scanned pages of the printed book, for checking the text. Source scan: [RAW/{a.pdf}](../RAW/{a.pdf})"]
    if a.note:
        L += ["", a.note]
    pages = [r for r in rows if r["kind"] == "page"]
    if pages:
        L += ["", "| Printed page | Scan |", "|---|---|"] + [f"| {r['label']} | {link(r['image'])} |" for r in pages]
    plates = [r for r in rows if r["kind"] == "plate"]
    if plates:
        L += ["", "## Plates and fold-outs", "", "| Plate | Scan |", "|---|---|"]
        L += [f"| {r['label']} | {link(r['image'])} |" for r in plates]
    other = [r for r in rows if r["kind"] == "other"]
    if other:
        L += ["", "## Other scanned images", "", "| Content | Scan |", "|---|---|"]
        L += [f"| {r['label']} | {link(r['image'])} |" for r in other]
    L += ["", f"Pages not in the scan: {a.missing or 'none'}."]
    open(f"{a.out}/SCANS.md", "w").write("\n".join(L) + "\n")
    print(f"{len(dict.fromkeys(r['image'] for r in rows if '/' not in r['image']))} images, {len(pages)} page rows -> {a.out}")


if __name__ == "__main__":
    main()
