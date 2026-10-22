"""Keyword-based structural-typology labels for figures (EN/FR/DE captions).

    python3 structlabels.py papers <papers_dir>        # papers/<name>/paper.md: label every ![..](figures/..) by its alt + caption
    python3 structlabels.py book <book_dir>            # book: label <img> alt texts in src/*.md and add a Labels column to FIGURES.md

Labels (user list): cables, arches, truss, beam, frames, plates or slabs, columns, bracing,
material-specific forms, plastic and stress field models, connections; extras: vaults and shells, graphic statics.
Labels come from caption/description words only (no image inspection). Re-running replaces earlier labels.
"""
import re, sys, pathlib

RULES = [
    ("cables", r"cable|catenar|suspen|hanging|câble|seil|chaînette|membrane|tension(ed)? (net|structure)|cable-net|net\b"),
    ("arches", r"\barch(es|ed)?\b|\barc\b|arcs\b|voussoir|thrust line|line of pressure|ligne de pression|courbe des pressions|bogen|centering|cintre"),
    ("vaults and shells", r"vault|dome|shell|cupola|voûte|coupole|gewölbe|schale|kuppel|thin-tile|gridshell"),
    ("truss", r"truss|lattice|treillis|fachwerk|cremona|roof frame|ferme\b|warren|pratt|howe|fink|bowstring|k[- ]type"),
    ("beam", r"\bbeams?\b|girder|poutre|träger|balken|cantilever|console|bending moment|moment de flexion|biegemoment|elastic curve|influence line|ligne d'influence|span"),
    ("frames", r"\bframes?\b|portal|mill bent|\bbent\b|rahmen|cadre|portique"),
    ("plates or slabs", r"\bslabs?\b|\bplates?\b|floor|dalle|platte|decke|plancher|deck"),
    ("columns", r"column|\bpier|pillar|colonne|pilier|stütze|säule|\bpost\b|strut\b|pile\b|chimney|tower|pylon"),
    ("bracing", r"bracing|brace|wind bracing|contreventement|verband|aussteifung|stabilit"),
    ("material-specific forms", r"masonry|maçonnerie|mauerwerk|brick|stone|tile|timber|wood|bois|holz|steel|acier|stahl|concrete|béton|beton|reinforc|knit|mycel|3d[- ]print|clay|earth"),
    ("plastic and stress field models", r"stress field|strut[- ]and[- ]tie|plastic|limit analysis|yield|lower[- ]bound|upper[- ]bound|spannungsfeld|champ de contraintes|collapse mechanism|hinge mechanism"),
    ("connections", r"connection|joint|\bnode|bolt|rivet|weld|assemblage|verbindung|anschluss|interface|splice|anchor|washer|gusset|bearing"),
    ("graphic statics", r"force (diagram|polygon)|funicular|reciprocal|polygone (des forces|funiculaire)|kräfteplan|seileck|form diagram|graphic statics|thrust network|pole\b|polar distance"),
]
RX = [(n, re.compile(p, re.I)) for n, p in RULES]

def labels_for(text):
    return [n for n, rx in RX if rx.search(text)]

TAG = re.compile(r"\s*\[labels: [^\]]*\]")

def do_papers(root):
    n_img = n_lab = 0
    for p in sorted(pathlib.Path(root).glob("*/paper.md")):
        lines = p.read_text().split("\n"); out = []
        for i, l in enumerate(lines):
            m = re.match(r"^(\s*)!\[([^\]]*)\]\((figures/[^)]+)\)(.*)$", l)
            if m:
                alt = TAG.sub("", m.group(2))
                cap = " ".join(x for x in lines[i + 1:i + 4] if x.strip() and not x.lstrip().startswith("!["))[:600]
                lab = labels_for(alt + " " + cap); n_img += 1
                if lab:
                    n_lab += 1; alt = f"{alt} [labels: {', '.join(lab)}]"
                l = f"{m.group(1)}![{alt}]({m.group(3)}){m.group(4)}"
            out.append(l)
        p.write_text("\n".join(out))
    print("papers: images", n_img, "labelled", n_lab)

def do_book(root):
    root = pathlib.Path(root); n_img = n_lab = 0
    desc = {}
    fig = root / "FIGURES.md"
    if fig.exists():
        for l in fig.read_text().split("\n"):
            m = re.search(r"\((figures/[^)]+)\)", l)
            if m and l.startswith("|"): desc[m.group(1)] = l
    IMG = re.compile(r'<img [^>]*>')
    files = sorted((root / "src").glob("*.md")) + (sorted(f for f in root.glob("*.md") if f.name[:1].isdigit()) if "--built" in sys.argv else [])
    for p in files:
        t = p.read_text(); out = []; pos = 0
        for m in IMG.finditer(t):
            tag = m.group(0); am = re.search(r'alt="([^"]*)"', tag); sm = re.search(r'src="(figures/[^"]+)"', tag)
            out.append(t[pos:m.start()]); pos = m.end()
            if not am or not sm: out.append(tag); continue
            base = TAG.sub("", am.group(1))
            cap = re.sub(r"<[^>]+>", " ", t[m.end():m.end() + 500].split("</p>")[0])
            lab = labels_for(base + " " + cap + " " + desc.get(sm.group(1), ""))
            n_img += 1
            if lab: n_lab += 1; base = f"{base} [labels: {', '.join(lab)}]"
            out.append(tag.replace(am.group(0), f'alt="{base}"'))
        out.append(t[pos:]); p.write_text("".join(out))
    if fig.exists():
        rows = fig.read_text().split("\n"); out = []
        for l in rows:
            if l.startswith("| Figure |") and "Labels" not in l: l = l + " Labels |"
            elif re.match(r"^\|[-| ]+\|$", l) and out and "Labels" in out[-1] and l.count("|") < out[-1].count("|"): l = l + "---|"
            elif l.startswith("| [") and "(figures/" in l:
                l = re.sub(r" [^|]*\|$", lambda m: m.group(0), l)
                parts = l.rstrip().rstrip("|").split("|")
                if len(parts) >= 6:  # already has labels column -> drop it
                    parts = parts[:5]
                l = "|".join(parts) + "| " + ", ".join(labels_for(l)) + " |"
            out.append(l)
        fig.write_text("\n".join(out))
    print(root.name, ": images", n_img, "labelled", n_lab)

if __name__ == "__main__":
    {"papers": do_papers, "book": do_book}[sys.argv[1]](sys.argv[2])
