"""Make contents-table links resolve to the heading anchors GitHub generates.

  python3 -I tools/fix_anchors.py BOOKDIR [--dry]      (fixes BOOKDIR/*.md and BOOKDIR/src/*.md in place)

GitHub drops "§" and "—" from a heading but keeps the spaces, so "## § 634 — Fundamental theorem" gets the anchor
"#-634--fundamental-theorem" (leading hyphen). A broken link "#634--…" or "#593" is repointed to the heading with the
same section number in the target file; links that cannot be matched unambiguously are reported, not changed.
Links into another chapter file ("02-chapter-02.md#…") are checked against that file.
"""
import re, sys, pathlib, unicodedata


def slug(h):
    h = re.sub(r"<[^>]+>", "", h); h = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", h); h = re.sub(r"[*_`]", "", h)
    h = h.strip().lower()
    h = "".join(c for c in h if c.isalnum() or c in " -" or unicodedata.category(c) in ("Mn",) or unicodedata.category(c).startswith("L"))
    return h.replace(" ", "-")


def anchors(text):
    out, cnt = [], {}
    fence = False
    for l in text.split("\n"):
        if l.startswith("```"):
            fence = not fence
        m = None if fence else re.match(r"^#{1,6} (.*)", l)
        if m:
            b = slug(m.group(1)); k = cnt.get(b, 0); cnt[b] = k + 1
            out.append(b if k == 0 else f"{b}-{k}")
    out += re.findall(r'<a (?:id|name)="([^"]+)"', text)  # explicit anchors are valid targets too
    return out


def run(folder, dry):
    files = {f.name: f for f in folder.glob("*.md")}
    anch = {n: anchors(f.read_text()) for n, f in files.items()}
    fixed = bad = 0
    for n, f in files.items():
        t = f.read_text()

        def fix(m):
            nonlocal fixed, bad
            tgt, a = m.group(1) or n, m.group(2)
            if tgt not in anch or a in anch[tgt]:
                return m.group(0)
            norm = lambda s: re.sub(r"-+", "-", s).strip("-")
            c = [x for x in anch[tgt] if norm(x) == norm(a)]
            if not c:
                num = re.search(r"\d+[a-z]?", a)
                first = lambda s: (re.search(r"\d+[a-z]?", s) or [None])[0]
                c = [x for x in anch[tgt] if num and first(x) == num.group(0)]
                if len(c) > 1:
                    c = [x for x in c if norm(x).startswith(norm(a)) or norm(a).startswith(norm(x))] or c
            if len(c) == 1:
                fixed += 1
                return f"]({m.group(1) or ''}#{c[0]})"
            bad += 1
            print("UNRESOLVED", f, f"{tgt}#{a}")
            return m.group(0)

        t2 = re.sub(r"\]\((\d[\w.-]*\.md)?#([\w-]+)\)", fix, t)
        if t2 != t and not dry:
            f.write_text(t2)
    return fixed, bad


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    book = pathlib.Path(sys.argv[1]); dry = "--dry" in sys.argv
    tot = [0, 0]
    for d in (book, book / "src"):
        if d.is_dir():
            f, b = run(d, dry); tot[0] += f; tot[1] += b
    print(f"{book.name}: fixed {tot[0]}, unresolved {tot[1]}" + (" (dry run)" if dry else ""))
