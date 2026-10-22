"""Recompute every in-file and cross-file anchor link in graphic-statics-student-course/src/*.md from the real headings
(GitHub slugs: lower-case, punctuation incl. en/em dashes removed, spaces -> '-'). Run before build.py."""
import re, glob, os, difflib, pathlib
BOOK = pathlib.Path(__file__).resolve().parent.parent / "graphic-statics-student-course"
def slug(h):
    s = re.sub(r"<[^>]+>", "", h).lower().strip(); s = re.sub(r"[^\w\- ]", "", s); return s.replace(" ", "-")
def heads(t):
    out, seen = [], {}
    for h in re.findall(r"^#{2,6} (.*)$", t, flags=re.M):
        g = slug(h); n = seen.get(g, 0); seen[g] = n + 1; out.append((h, g if n == 0 else f"{g}-{n}"))
    return out
files = sorted(glob.glob(str(BOOK / "src" / "[0-9]*.md")))
amap = {}
for f in files:
    d = {}
    for h, g in heads(open(f).read()):
        d.setdefault(slug(re.sub(r"[–—]", "-", h)), g); d.setdefault(g, g)
    amap[os.path.basename(f)] = d
def resolve(f, a):
    d = amap[f]
    if a in d: return d[a]
    c = [k for k in d if k.startswith(a) or a.startswith(k)]
    if c: return d[sorted(c, key=len)[0]]
    m = difflib.get_close_matches(a, list(d), n=1, cutoff=0.8)
    return d[m[0]] if m else None
bad = []; fixed = 0
for fp in files:
    f = os.path.basename(fp); t = open(fp).read(); o = t
    def loc(m):
        global fixed
        r = resolve(f, m.group(1))
        if r is None: bad.append((f, m.group(1))); return m.group(0)
        fixed += r != m.group(1); return f"](#{r})"
    t = re.sub(r"\]\(#([^)\s]+)\)", loc, t)
    def xf(m):
        global fixed
        tf = m.group(1)
        if tf not in amap: bad.append((f, tf)); return m.group(0)
        r = resolve(tf, m.group(2))
        if r is None: bad.append((f, tf + "#" + m.group(2))); return m.group(0)
        fixed += r != m.group(2); return f"]({tf}#{r})"
    t = re.sub(r"\]\((\d\d-[a-z0-9\-]+\.md)#([^)\s]+)\)", xf, t)
    if t != o: open(fp, "w").write(t)
print("anchors fixed:", fixed, "unresolved:", bad)
