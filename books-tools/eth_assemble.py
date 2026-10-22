"""Assemble the ETH course book: prev/next navigation in src/, README.md, INDEX.md, FIGURES.md, orphan-figure cleanup.

  python3 tools/eth_assemble.py [--delete-orphans]
Run from the repo root; afterwards run:  EQPNG=/tmp/eqpng python3 graphic-statics-student-course/src/build.py
"""
import json, re, sys, pathlib, html

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOOK = ROOT / "graphic-statics-student-course"
SRC = BOOK / "src"
UNITS = json.load(open(sys.argv[sys.argv.index("--units") + 1])) if "--units" in sys.argv else None
if UNITS is None:
    UNITS = json.load(open(BOOK / "src" / "units.json")) if (BOOK / "src" / "units.json").exists() else json.load(open(BOOK.parent / "tools" / "eth_units.json"))
files = sorted(p for p in SRC.glob("[0-9][0-9]-*.md"))
by_file = {u["file"]: u for u in UNITS}
titles = {p.name: by_file[p.name]["title"] for p in files}

PARTS = [(1, 16, "Part A — Structural Design I: equilibrium, graphic statics, cables, arches, arch-cable structures"),
         (17, 28, "Part B — Structural Design II: trusses, beams, frames, plates, columns and bracing"),
         (29, 55, "Part C — Structural Design III: steel, reinforced concrete, timber, masonry, construction details"),
         (56, 57, "Part D — Structural Design IV: case studies"),
         (58, 62, "Part E — D-BAUG + MIBS: theory of plasticity, stress fields, design project"),
         (63, 75, "Part F — The Skripte (textbook): Skript I & II (German, translated) and Skript III & IV")]
# companion reading in the Skript for each lecture/exercise file (by position)
SK12 = {63: "sheets 1–30", 64: "31–60", 65: "61–90", 66: "91–120", 67: "121–150", 68: "151–176"}
SKR = {4: (2, [63]), 5: (5, [64]), 6: (2, [63]), 7: (2, [63]), 8: (3, [63, 64]), 9: (3, [64]), 10: (6, [64, 65]), 11: (7, [65]),
       12: (8, [65]), 13: (8, [65, 66]), 14: (9, [66]), 15: (3, [63, 64, 65]),
       18: (10, [66, 67]), 19: (11, [67]), 20: (12, [67]), 21: (14, [68]), 22: (12, [67]), 23: (13, [67]),
       24: (12, [67]), 25: (13, [67, 68]), 26: (15, [68]),
       33: ("II", [70]), 34: ("II", [70]), 35: ("II", [70]), 36: ("I", [69]), 37: ("I", [69]), 38: ("VI", [72]), 39: ("VI", [72]),
       40: ("III", [70, 71]), 41: ("III", [70, 71]), 42: ("III", [71]), 43: ("III", [71]),
       44: ("IV", [71]), 45: ("IV", [71]), 46: ("IV", [71]), 47: ("IV", [71]),
       48: ("V–VII", [71, 72]), 49: ("VII–VIII", [72]), 50: ("VIII–IX", [72, 73]), 51: ("IX", [73]), 52: ("X", [73]), 53: ("X", [73, 74])}

# ---- navigation
for i, p in enumerate(files):
    t = p.read_text()
    prev = f"[← {titles[files[i-1].name]}]({files[i-1].name})" if i else ""
    nxt = f"[{titles[files[i+1].name]} →]({files[i+1].name})" if i + 1 < len(files) else ""
    nav = " · ".join(x for x in (prev, "[Contents](README.md)", nxt) if x)
    t, n = re.subn(r"<!--nav-->.*?<!--/nav-->|\[NAV\]", f"<!--nav-->{nav}<!--/nav-->", t, count=1, flags=re.S)
    fp = (f'<a href="{files[i-1].name}">← previous</a> · ' if i else "") + '<a href="README.md">Contents</a>' + (f' · <a href="{files[i+1].name}">next →</a>' if i + 1 < len(files) else "")
    t = re.sub(r'(<sub>End of [^<]*?)(?: · (?:<a href="[^"]*">[^<]*</a> · )*<a href="README.md">Contents</a>(?: · <a href="[^"]*">next →</a>)?)</sub>', lambda m: f"{m.group(1)} · {fp}</sub>", t)
    p.write_text(t)

# ---- "In this file" summary under the header (from the review index data)
SUM0 = json.load(open(SRC / "summaries.json")) if (SRC / "summaries.json").exists() else {}
for p in files:
    pos = by_file[p.name]["pos"]; s = SUM0.get(str(pos), "").strip()
    if not s: continue
    t = p.read_text(); block = f"<!--summary-->\n> **In this file.** {s}\n<!--/summary-->"
    if "<!--summary-->" in t: t = re.sub(r"<!--summary-->.*?<!--/summary-->", lambda m: block, t, count=1, flags=re.S)
    else:
        t = t.replace("\n---\n\n## Contents", f"\n---\n\n{block}\n\n## Contents", 1)
    p.write_text(t)

# ---- parse sections / figures
fig_rows, idx_rows, used = [], {}, set()
for p in files:
    t = p.read_text()
    topics = re.findall(r"^\|\s*([^|\n]+?)\s*\|\s*(?:([^|\n]*?)\s*\|\s*)?\[([^\]]+)\]\(#[^)]*\)[^|\n]*\|?", t, flags=re.M)
    sect = ""
    for line in t.splitlines():
        if line.startswith("## "):
            sect = line[3:].strip()
        for m in re.finditer(r'<img src="figures/([^"]+)"[^>]*alt="([^"]*)"', line):
            used.add(m.group(1)); fig_rows.append((m.group(1), html.unescape(m.group(2)), p.name, sect))
    idx_rows[p.name] = (topics, len(re.findall(r'<img src="figures/', t)))

if "--delete-orphans" in sys.argv:
    for f in (BOOK / "figures").iterdir():
        if f.name not in used:
            f.unlink(); print("deleted orphan", f.name)

# ---- README
def link(name): return f"[{titles[name]}]({name})"
out = ['<div align="center">\n\n# Structural Design\n### ETH Zürich · D-ARCH Tragwerksentwurf I–IV and D-BAUG + MIBS\n\n**Philippe Block · Joseph Schwartz** (Block Research Group, Professur für Tragwerksentwurf)\n\n*Lecture slides, exercises, compendium and Skript — English edition*\n\n</div>\n\n---\n',
       "## How to read this edition\n\n**Follow the files in numeric order (01 → 75): it is one continuous course.** Part A–E go lecture by lecture, each lecture followed by its exercises; Part F holds the two Skripte (the German textbook, translated), and the last column of the tables below points to the Skript chapters that accompany each lecture.\n\n**File names** follow one rule: `NN-<course>-<kind>-<topic>[-pK].md` — `NN` = reading order; `<course>` = `sd1`–`sd4`, `dbaug` or `skript12`/`skript34`; `<kind>` = `lNN` lecture N, `exNN` exercise N, `doc` reference documents, `project`; `-pK` = part K of a long lecture; Skript files carry their sheet range. Figures are named `NN-sNNN.jpg` (file NN, slide NNN) or `NN-pNN.jpg` (file NN, printed page). Example: `ls src/*sd2-l07*`.\n\n**Reading the drawings.** The exercise handouts prescribe *red = tension, blue = compression, green = external forces* for force-flow answers. Lecture slides use red and blue in many drawings without a legend, so the text reports colours as drawn and calls a member tension or compression only where the slide or this rule says so.\n\nThe course material (slides, exercise sheets, formula sheets and the German Skript) is converted to English Markdown. Slides are cited by **slide number** (the PDF page), the Skript by **printed page and sheet**. German-only text is translated; the bilingual slides use their English lines. Diagrams, tables and formula pages are embedded as images next to the text that uses them; photos are described in one line. Formulas are transcribed symbol for symbol; printing slips are footnoted, never silently fixed.\n\n"
       "## Finding things\n\n- [GRAPHIC-STATICS-NOTATION.md](GRAPHIC-STATICS-NOTATION.md) — **start here for the diagrams**: form and force diagrams, reciprocity, the course notation (Roman/Arabic numerals, A/B reactions, pole, rays, closing string, colours), the constructions and how the Diagram blocks are written\n- [INDEX.md](INDEX.md) — every file with its section list\n- [GLOSSARY.md](GLOSSARY.md) — German → English terms and the course's symbols\n- [FIGURES.md](FIGURES.md) — every embedded figure, one line each\n- [review/](review/) — the independent review log of every file (what was checked against the images, every correction, what stays unresolved)\n- Search: `python3 tools/search.py \"funicular polygon\" --book graphic-statics-student-course` (from the repo root)\n\n---\n\n# Table of Contents\n"]
for a, b, name in PARTS:
    out.append(f"\n### {name}\n\n| # | File | Content | Companion reading (Skript) |\n|:-:|---|---|---|")
    for p in files:
        n = by_file[p.name]["n"]
        if a <= n <= b:
            pos = by_file[p.name]["pos"]; rd = ""
            if pos in SKR:
                ch, fl = SKR[pos]; v = "Skript III & IV" if pos >= 33 else "Skript I & II"
                rd = f"{v}, ch. {ch}: " + ", ".join("[sheets %s–%s](%s)" % (re.search(r"sheets-(\d+)-(\d+)", files[k-1].name).group(1).lstrip("0"), re.search(r"sheets-(\d+)-(\d+)", files[k-1].name).group(2).lstrip("0"), files[k-1].name) for k in fl)
            out.append(f"| {pos:02d} | ✅ {link(p.name)} | {by_file[p.name]['kind']} · {len(idx_rows[p.name][0])} sections | {rd} |")
(BOOK / "README.md").write_text("\n".join(out) + "\n")

# ---- INDEX
SUMM = json.load(open(BOOK / "src" / "summaries.json")) if (BOOK / "src" / "summaries.json").exists() else {}
ix = ["# Index\n\nWhat each file contains, so you can find the right file without opening it. Each entry has a short summary, then the file's own section list (slide/page range · topic). Use `FIGURES.md` for diagrams and `GLOSSARY.md` for terms.\n"]
for a, b, name in PARTS:
    ix.append(f"\n## {name}\n")
    for p in files:
        u = by_file[p.name]
        if a <= u["n"] <= b:
            topics, nf = idx_rows[p.name]
            ix.append(f"### {link(p.name)}\n\n*{u['kind']} · {nf} embedded figures*\n")
            if SUMM.get(str(u["pos"])): ix.append(SUMM[str(u["pos"])].strip() + "\n")
            for r in topics[:40]:
                rng, mid, ttl = r
                ix.append(f"- {rng.strip()} {('· ' + mid.strip()) if mid.strip() else ''}— {ttl.strip()}".replace("  ", " "))
            if len(topics) > 40: ix.append(f"- … and {len(topics)-40} more sections")
            ix.append("")
(BOOK / "INDEX.md").write_text("\n".join(ix) + "\n")

# ---- FIGURES
fg = [f"# Figures\n\nAll {len(fig_rows)} embedded figures with a one-line description (taken from the figure's alt text). Slide figures are named `uNN-sNNN` (unit, slide number), page figures `uNN-pNN`. Open the image only when it is relevant.\n", "| Figure | Chapter · section | Description |", "|---|---|---|"]
for f, alt, ch, sect in fig_rows:
    fg.append(f"| [{f}](figures/{f}) | [{ch[:-3]}]({ch}) · {sect.replace('|', '/')[:60]} | {alt.replace('|', '/')} |")
(BOOK / "FIGURES.md").write_text("\n".join(fg) + "\n")
print(len(files), "files;", len(fig_rows), "figures;", len(list((BOOK / 'figures').iterdir())), "on disk")
