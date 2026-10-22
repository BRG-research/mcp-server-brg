"""Figure helper for the Lévy translation.

  python3 figtool.py grid  NN                 -> grid/NN.jpg  (plate NN=1..26, or a page image name like p0040a, with a labelled 0.05 grid)
  python3 figtool.py zoom  NN x0 y0 x1 y1      -> grid/zoom_*.jpg (region of plate, with finer 0.01 grid)
  python3 figtool.py crop  NN x0 y0 x1 y1 NAME [--white x0,y0,x1,y1 ...] [--rot DEG]
                                              -> BOOK/figures/NAME.png (cleaned) + grid/check_NAME.png preview
Coordinates are fractions (0..1) of the full plate image (after --rot, if given).
"""
import sys, pathlib
import numpy as np, cv2
from PIL import Image, ImageDraw

W = pathlib.Path(__file__).resolve().parent
BOOK = W.parent / "Books_repo" / "graphic-statics-levy"
(W / "grid").mkdir(exist_ok=True)


def load(nn, rot=0.0):
    # nn = plate number (1..26) or a page-image name such as p0123a / p0123b (figures printed in the text)
    src = W / "pages" / f"{nn}.jpg" if not str(nn).isdigit() else W / "plates" / f"Pl{int(nn):02d}.jpg"
    g = cv2.imread(str(src))
    if rot:
        h, w = g.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, 1.0)
        if abs(rot) in (90, 270):
            g = cv2.rotate(g, cv2.ROTATE_90_CLOCKWISE if rot == -90 or rot == 270 else cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            g = cv2.warpAffine(g, M, (w, h), borderValue=(255, 255, 255))
    return g


def gridimg(img, x0=0, y0=0, x1=1, y1=1, step=0.05, maxw=2000):
    im = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    w, h = im.size
    im = im.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
    sc = maxw / im.width
    im = im.resize((maxw, int(im.height * sc)))
    d = ImageDraw.Draw(im)
    k = round(x0 / step)
    while k * step <= x1 + 1e-9:
        X = (k * step - x0) / (x1 - x0) * im.width
        d.line((X, 0, X, im.height), fill=(255, 0, 0), width=1)
        d.text((X + 2, 2), f"{k*step:.2f}", fill=(255, 0, 0), font_size=18)
        k += 1
    k = round(y0 / step)
    while k * step <= y1 + 1e-9:
        Y = (k * step - y0) / (y1 - y0) * im.height
        d.line((0, Y, im.width, Y), fill=(0, 0, 255), width=1)
        d.text((2, Y + 2), f"{k*step:.2f}", fill=(0, 0, 255), font_size=18)
        k += 1
    return im


def clean(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    bg = cv2.GaussianBlur(g, (0, 0), 30)
    n = np.clip(g / bg * 255, 0, 255)
    return np.clip((n - 150) * (255 / (235 - 150)), 0, 255)


def main(a):
    cmd = a[0]
    if cmd == "grid":
        gridimg(load(a[1])).save(W / "grid" / f"{a[1]}.jpg", quality=85)
        print(W / "grid" / f"{a[1]}.jpg")
    elif cmd == "zoom":
        x0, y0, x1, y1 = map(float, a[2:6])
        out = W / "grid" / f"zoom_{a[1]}_{x0:.2f}_{y0:.2f}_{x1:.2f}_{y1:.2f}.jpg"
        gridimg(load(a[1]), x0, y0, x1, y1, step=0.01).save(out, quality=88)
        print(out)
    elif cmd == "crop":
        x0, y0, x1, y1 = map(float, a[2:6]); name = a[6]
        whites, rot, i = [], 0.0, 7
        while i < len(a):
            if a[i] == "--white":
                whites.append(tuple(map(float, a[i + 1].split(",")))); i += 2
            elif a[i] == "--rot":
                rot = float(a[i + 1]); i += 2
            else:
                raise SystemExit(f"unknown arg {a[i]}")
        n = clean(load(a[1], rot))
        h, w = n.shape
        for p, q, r, s in whites:
            n[int(q * h):int(s * h), int(p * w):int(r * w)] = 255
        c = n[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)].astype(np.uint8)
        out = BOOK / "figures" / f"{name}.png"
        cv2.imwrite(str(out), c, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        pv = Image.fromarray(c); pv.thumbnail((1400, 1400)); pv.save(W / "grid" / f"check_{name}.png")
        print(out, c.shape, "preview:", W / "grid" / f"check_{name}.png")


if __name__ == "__main__":
    main(sys.argv[1:])
