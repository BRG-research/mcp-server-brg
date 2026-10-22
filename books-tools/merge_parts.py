"""merge_parts.py <src dir> <stem>: merge stem.md + stem-part*.md (footnote definitions moved to the end); originals moved to src/parts/.
Check first that footnote names are unique across the parts and that links to the part files point to stem.md."""
import sys, re, pathlib, shutil
d = pathlib.Path(sys.argv[1]); stem = sys.argv[2]
files = [d / f"{stem}.md"] + sorted(d.glob(f"{stem}-part*.md"))
def split(t):
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        if re.match(r"\[\^[^\]]+\]:", l):
            return "\n".join(lines[:i]).rstrip("\n"), "\n".join(lines[i:]).strip("\n")
    return "\n".join(lines).rstrip("\n"), ""
bodies, defs = [], []
for f in files:
    b, df = split(f.read_text()); bodies.append(b); defs.append(df)
out = "\n\n".join(bodies) + "\n\n" + "\n\n".join(x for x in defs if x) + "\n"
(d / "parts").mkdir(exist_ok=True)
for f in files: shutil.move(str(f), d / "parts" / f.name)
(d / f"{stem}.md").write_text(out)
print("merged", [f.name for f in files], "->", stem + ".md")
