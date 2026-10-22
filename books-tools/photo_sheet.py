"""Contact sheet for rescan photos (phone photos, any orientation), to see which pages a batch shows.

  python3 -I tools/photo_sheet.py PHOTO_DIR OUT.jpg [COLUMNS=4]

Applies EXIF rotation, labels each thumbnail with its file name. Read OUT.jpg, then zoom single photos with
  python3 -I tools/pagetool.py zoom PHOTO_DIR NAME.jpg x0 y0 x1 y1 z.jpg
Copy the originals to RAW/rescans/<book>-<date>/ before using them.
"""
import sys, glob, os
from PIL import Image, ImageDraw, ImageOps

if len(sys.argv) < 3:
    sys.exit(__doc__)
d, out = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 4
fs = sorted(f for f in glob.glob(os.path.join(d, "*")) if f.lower().endswith((".jpg", ".jpeg", ".png", ".pgm", ".ppm")))
W, H = 450, 450
sheet = Image.new("RGB", (cols * W, ((len(fs) + cols - 1) // cols) * (H + 20)), "white"); dr = ImageDraw.Draw(sheet)
for i, f in enumerate(fs):
    im = ImageOps.exif_transpose(Image.open(f)); im.thumbnail((W, H))
    x, y = (i % cols) * W, (i // cols) * (H + 20)
    sheet.paste(im, (x, y + 20)); dr.text((x + 5, y + 3), os.path.basename(f), fill="red")
sheet.save(out, quality=80)
print(out, len(fs), "photos")
