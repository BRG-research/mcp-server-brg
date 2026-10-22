"""Flag pages where the English translation may omit or add text, by comparing word counts with a Mistral OCR.

  python3 -I tools/mistral_textcheck.py SRCDIR OCRDIR OFFSET OUTDIR [--jobs]

SRCDIR  the book's src/ folder (pages split by the <sub>page N</sub> markers; arabic pages only)
OCRDIR  tools/mistral_ocr.py output of the scan rendered as p####.jpg (PDF page numbers, 1-based)
OFFSET  PDF page = printed page + OFFSET
Per page: words of our English body plus the author footnotes it references (formulas, images, HTML, translator notes,
<details> blocks and italic original-title lines removed) against the words of the OCR page (running head, printer's
signature and formulas removed). Pages whose ratio departs from the book's median, or whose paragraph count differs
strongly, are written to OUTDIR/TEXTCHECK.md and textcheck.json; --jobs writes OUTDIR/textjobs/job_NN.md
(<= 12 pages each, for tools/TEXT_CHECK_BRIEF.md). No model reading.
"""
import json, re, statistics, sys, pathlib
from collections import defaultdict

if len(sys.argv) < 5:
    sys.exit(__doc__)
srcdir, ocrdir, off, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3]), pathlib.Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)
MARK = re.compile(r"<sub>\[?page ([^\]<(]+?)\s*(?:\(end\))?\]?(?:\([^)]*\))?</sub>")
WORD = re.compile(r"[^\W\d_]{2,}")

pages, foot = defaultdict(lambda: {"text": [], "files": set()}), {}
for f in sorted(srcdir.glob("*.md")):
    t = f.read_text()
    for m in re.finditer(r"^\[\^([^\]]+)\]:(.*(?:\n(?!\[\^|\n).*)*)", t, flags=re.M):
        foot[m.group(1)] = m.group(2)
    parts = MARK.split(t)
    for i in range(1, len(parts), 2):
        pages[parts[i].strip()]["text"].append(parts[i + 1])
        pages[parts[i].strip()]["files"].add(f.name)


def ours_clean(t):
    t = re.sub(r"<details>.*?</details>", " ", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    refs = re.findall(r"\[\^([^\]]+)\](?!:)", t)
    t = re.sub(r"^\[\^[^\]]+\]:.*(?:\n(?!\[\^|\n).*)*", " ", t, flags=re.M)
    t = re.sub(r"```math.*?```", " ", t, flags=re.S)
    t = re.sub(r"\$`.*?`\$", " x ", t)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)|<img[^>]*>", " ", t)
    t = re.sub(r"^\s*\*[^*\n]+\*\s*$", " ", t, flags=re.M)  # italic original-title lines
    t = re.sub(r"^\s*\*Original title:.*$", " ", t, flags=re.M)
    t = re.sub(r"\]\([^)]*\)", "]", t)
    t = re.sub(r"<[^>]+>", " ", t)
    notes = [foot[r] for r in dict.fromkeys(refs) if r in foot and not re.match(r"\s*(\*\*)?Translator", foot[r])]
    notes = [re.sub(r"^\s*Author's (foot)?note\.?", " ", n) for n in notes]
    body = t
    return body, " ".join(notes)


def ocr_clean(t, p):
    lines = t.split("\n")
    ne = [k for k, l in enumerate(lines) if l.strip()][:3]
    for k in ne:
        if re.fullmatch(rf"\W*{p}\W*", lines[k].strip()) or (k == ne[0] and len(lines[k]) < 150 and re.fullmatch(rf"(\W*{p}\b.*|.*\b{p}\W*)", lines[k].strip())):
            for j in range(k + 1):
                lines[j] = ""
            nxt = [j for j in range(k + 1, len(lines)) if lines[j].strip()][:1]
            if nxt and len(lines[nxt[0]]) < 120 and re.search(r"Kapitel|^§|Abschnitt|Chapitre|SECTION", lines[nxt[0]].strip()):
                lines[nxt[0]] = ""
            break
    while lines and (not lines[-1].strip() or re.fullmatch(r"[\d*\s]{1,12}", lines[-1].strip())
                     or re.fullmatch(r".{0,40}(Graphische Statik|Graph\. Statik|Henneberg|Poncelet|Mém\.).{0,30}", lines[-1].strip())):
        lines.pop()
    t = "\n".join(lines)
    t = re.sub(r"\$\$.*?\$\$|\\\[.*?\\\]", " ", t, flags=re.S)
    t = re.sub(r"\$[^$]+\$", " x ", t)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)
    return t


def paras(t):
    return len([b for b in re.split(r"\n\s*\n", t) if len(WORD.findall(b)) >= 8])


rows = []
for p, d in pages.items():
    if not p.isdigit():
        continue
    of = ocrdir / f"p{int(p) + off:04d}.md"
    if not of.exists():
        continue
    body, notes = ours_clean("\n".join(d["text"]))
    src = ocr_clean(of.read_text(), p)
    e, s = len(WORD.findall(body + " " + notes)), len(WORD.findall(src))
    rows.append({"page": int(p), "pdf_page": int(p) + off, "files": sorted(d["files"]), "en": e, "src": s,
                 "en_par": paras(body), "src_par": paras(src)})

ratios = [r["en"] / r["src"] for r in rows if r["src"] >= 80]
med = statistics.median(ratios) if ratios else 1.2
flag = []
for r in rows:
    exp = med * r["src"]
    why = []
    if r["src"] >= 30 and r["en"] < 0.75 * exp and exp - r["en"] > 25:
        why.append(f"English short: {r['en']} words vs {exp:.0f} expected")
    if r["en"] > 1.35 * exp + 10 and r["en"] - exp > 30:
        why.append(f"English long: {r['en']} words vs {exp:.0f} expected")
    if r["src"] < 30 and r["en"] > 80:
        why.append(f"English {r['en']} words on a page with {r['src']} source words")
    if abs(r["en_par"] - r["src_par"]) >= 3 and r["src"] >= 30 and not 0.85 * exp <= r["en"] <= 1.2 * exp:
        why.append(f"paragraphs {r['en_par']} vs {r['src_par']}")
    if why:
        r["why"] = why
        flag.append(r)
flag.sort(key=lambda r: r["page"])
json.dump({"median_ratio": med, "pages": len(rows), "flagged": flag}, open(out / "textcheck.json", "w"), indent=1, ensure_ascii=False)
md = [f"# Text check: English vs source word counts\n", f"Pages compared: {len(rows)}; median words EN/source: {med:.2f}; flagged: {len(flag)}\n"]
md += [f"- p. {r['page']} (PDF {r['pdf_page']}, {', '.join(r['files'])}): " + "; ".join(r["why"]) for r in flag]
(out / "TEXTCHECK.md").write_text("\n".join(md) + "\n")
print(f"{len(rows)} pages, median ratio {med:.2f}, flagged {len(flag)}")

if "--jobs" in sys.argv:
    (out / "textjobs").mkdir(exist_ok=True)
    for j in range(0, len(flag), 12):
        lines = []
        for r in flag[j:j + 12]:
            lines.append(f"## p. {r['page']} — OCR source: {ocrdir.resolve()}/p{r['pdf_page']:04d}.md — scan image: p{r['pdf_page']:04d}.jpg — "
                         f"our files: " + ", ".join(f"{srcdir.resolve()}/{f}" for f in r["files"]))
            lines.append("- flag: " + "; ".join(r["why"]) + "\n")
        (out / "textjobs" / f"job_{j // 12 + 1:02d}.md").write_text("\n".join(lines))
    print(len(range(0, len(flag), 12)), "jobs in", out / "textjobs")
