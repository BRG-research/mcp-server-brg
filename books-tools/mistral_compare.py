"""Compare a book's src/*.md with a Mistral OCR of the scan, language-independently (no model reading).

  python3 -I tools/mistral_compare.py SRCDIR OCRDIR OFFSET OUTDIR [--jobs]

SRCDIR  the book's src/ folder (pages split by the <sub>page N</sub> markers; arabic pages only)
OCRDIR  tools/mistral_ocr.py output of the scan rendered as p####.jpg (PDF page numbers, 1-based)
OFFSET  PDF page = printed page + OFFSET
Compares display/inline equations (normalised LaTeX), equation numbers, numbers, figure and § numbers, primes and
sub/superscripts. Writes OUTDIR/MISMATCHES.md, OUTDIR/mismatches.json and, with --jobs, OUTDIR/jobs/job_NN.md
(<= 12 pages each, for tools/CHECK_BRIEF.md). Running heads, printer's signatures, German/French words inside
formulas, decimal commas and OCR notation variants (tg/tang, Π for II, ν/v, Unicode sub/superscripts) are normalised.
"""
import json, re, sys, pathlib, difflib
from collections import defaultdict

if len(sys.argv) < 5:
    sys.exit(__doc__)
srcdir, ocrdir, off, book = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3]), pathlib.Path(sys.argv[4])
book.mkdir(parents=True, exist_ok=True)

GREEK = dict(alpha="α", beta="β", gamma="γ", delta="δ", epsilon="ε", varepsilon="ε", zeta="ζ", eta="η", theta="θ",
             vartheta="θ", iota="ι", kappa="κ", lambda_="λ", mu="μ", nu="ν", xi="ξ", pi="π", varpi="π", rho="ρ", varrho="ρ",
             sigma="σ", varsigma="σ", tau="τ", upsilon="υ", phi="φ", varphi="φ", chi="χ", psi="ψ", omega="ω", Gamma="Γ",
             Delta="Δ", Theta="Θ", Lambda="Λ", Xi="Ξ", Pi="Π", Sigma="Σ", Upsilon="Υ", Phi="Φ", Psi="Ψ", Omega="Ω")
GREEK["lambda"] = "λ"
GREEK.update({"var" + k: v for k, v in list(GREEK.items()) if k[0].isupper()})
UNI = {"ϱ": "ρ", "ϑ": "θ", "ϕ": "φ", "ϵ": "ε", "ς": "σ", "′": "'", "″": "''", "‴": "'''", "−": "-", "–": "-",
       "×": r"\times", "·": "", "⋅": "", "…": "...", "≦": "≤", "≧": "≥", "∓": r"\mp", "±": r"\pm", "½": "1/2", "¼": "1/4", "¾": "3/4", "⅓": "1/3", "⅔": "2/3"}
DROP = [r"\\", r"\left.", r"\right.", r"\left\{", r"\right\}", r"\left", r"\right", r"\displaystyle", r"\textstyle", r"\big", r"\Big", r"\bigg", r"\Bigg", r"\limits",
        r"\cdot", r"\,", r"\;", r"\:", r"\!", r"\quad", r"\qquad", r"\ ", "&", "~", r"\nonumber", r"\notag"]
SUBS = [(r"\tfrac", r"\frac"), (r"\dfrac", r"\frac"), (r"\overline", ""), (r"\bar", ""), (r"\cdots", "..."), (r"\ldots", "..."),
        (r"\dots", "..."), (r"\leq", "≤"), (r"\geq", "≥"), (r"\le", "≤"), (r"\ge", "≥"), (r"\neq", "≠"),
        (r"\prime", "'"), (r"\infty", "∞"), (r"\colon", ":"), (r"\lbrace", "("), (r"\rbrace", ")"), (r"\{", "("), (r"\}", ")"),
        ("[", "("), ("]", ")")]


def frak(m):
    c = m.group(1)
    return "\x02" + c + "\x03"


def unfrak_unicode(s):
    out = []
    for ch in s:
        o = ord(ch)
        if 0x1D504 <= o <= 0x1D537 or 0x1D56C <= o <= 0x1D59F:  # fraktur / bold fraktur
            base = 0x1D504 if o <= 0x1D537 else 0x1D56C
            k = o - base
            out.append("\x02" + (chr(65 + k) if k < 26 else chr(97 + k - 26)) + "\x03")
        elif ch in "ℭℌℑℜℨ":
            out.append("\x02" + {"ℭ": "C", "ℌ": "H", "ℑ": "I", "ℜ": "R", "ℨ": "Z"}[ch] + "\x03")
        else:
            out.append(ch)
    return "".join(out)


SUBD = dict(zip("₀₁₂₃₄₅₆₇₈₉ₐₑₒₓₕₖₗₘₙₚₛₜᵢⱼᵣᵤᵥ", "0123456789aeoxhklmnpstijruv"))
SUPD = dict(zip("⁻⁺⁰¹²³⁴⁵⁶⁷⁸⁹ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ", "-+0123456789abcdefghijklmnoprstuvwxyz"))


def uniscripts(t):
    t = re.sub("[" + "".join(SUBD) + "]+", lambda m: "_{" + "".join(SUBD[c] for c in m.group(0)) + "}", t)
    return re.sub("[" + "".join(SUPD) + "]+", lambda m: "^{" + "".join(SUPD[c] for c in m.group(0)) + "}", t)


def norm(t):
    t = unfrak_unicode(uniscripts(t))
    t = re.sub(r"\\(?:mathrm|text|operatorname)\s*\{\s*(t\s*a\s*n\s*g|c\s*o\s*t\s*a\s*n\s*g|s\s*i\s*n|c\s*o\s*s|t\s*a\s*n|t\s*g|l\s*o\s*g|s\s*i\s*n\s*h|c\s*o\s*s\s*h|a\s*r\s*c\s*\w*)\s*\}", lambda m: " " + m.group(1).replace(" ", "") + " ", t)
    t = re.sub(r"\\(tang|cotang)\b", r" \1 ", t)
    t = t.replace("∢", "∠").replace(r"\measuredangle", "∠").replace(r"\sphericalangle", "∠").replace(r"\angle", "∠")
    t = re.sub(r"\\tag\*?\{[^}]*\}", "", t)
    t = re.sub(r"\\(begin|end)\{[a-z*]+\}(\{[^}]*\})?", "", t)
    t = re.sub(r"\\mathfrak\s*\{?\s*([A-Za-z])\s*\}?", frak, t)
    t = re.sub(r"\\(?:text|mathrm|mathit|mathbf|boldsymbol|operatorname|textit|textrm|mbox|mathsf|mathcal|bm)\s*\{([^{}]*)\}", lambda m: " " + " ".join(w for w in m.group(1).replace("~", " ").split() if len(w) <= 3 or re.search(r"\d", w)) if len(m.group(1).replace(" ", "")) > 3 and " " in m.group(1).strip() and not re.fullmatch(r"(\w ){2,}\w", m.group(1).strip()) else re.sub(r"[A-Za-z]{4,}", "", m.group(1).replace(" ", "").replace("~", "")) + " ", t)
    for a, b in UNI.items():
        t = t.replace(a, b)
    t = re.sub(r"\\([A-Za-z]+)", lambda m: GREEK.get(m.group(1), "\\" + m.group(1)) + " ", t)
    t = re.sub(r"\\(?:text|mbox|textrm|textit)\s*\{[^{}]*\}", " ", t)  # words inside equations are language-dependent
    t = re.sub(r"(?<![\\A-Za-z])(?:and|or|therefore|hence|i\.e\.|also|to|give|gives|where|for|und|oder|daher|also|zu|wo|d\.h\.|mit|für|bzw\.?|resp\.?|folglich|somit|mithin|auch|ou|et|donc|the|of|in|at|on|by|is|der|die|das|des|den|im|am|le|la|les|de|du|en|des|etc\.?|usw\.?|u\.s\.w\.|d'où|soit)(?![A-Za-z])", " ", t)
    for d in DROP:
        t = t.replace(d, " ")
    t = re.sub(r"\\?\b(sinh|cosh|tanh|coth|sin|cos|tang|tan|cotang|cot|tg|ctg|cotg|log|lg|ln|exp|arc)\b", lambda m: {"tg": "tan", "tang": "tan", "cotang": "cot", "ctg": "cot", "cotg": "cot", "lg": "log"}.get(m.group(1), m.group(1)) + " ", t)
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)
    t = t.replace("Π", "II").replace("ν", "v")
    for a, b in SUBS:
        t = t.replace(a, b)
    t = t.replace(r"^{''}", "''").replace(r"^{'}", "'").replace("^''", "''").replace("^'", "'")
    G = r"\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}"
    def fr(m):
        a, b = [re.sub(r"[{}\s]", "", x) for x in m.groups()]
        simple = lambda x: x if re.fullmatch(r"[\w.']+", x) else "(" + x + ")"
        return simple(a) + "/" + simple(b)
    for _ in range(3):
        t = re.sub(r"\\frac\s*" + G + r"\s*" + G, fr, t)
    t = re.sub(r"[{}\s]", "", t)
    t = t.replace("^''", "''").replace("^'", "'")
    t = re.sub(r"([_^])(\w)", r"\1\2", t)
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)
    t = t.replace("'^", "'")
    t = t.rstrip(".,;:")
    return t


def tags(t):
    return [re.sub(r"\s", "", x) for x in re.findall(r"\\tag\*?\{([^}]*)\}", t)]


# ---------- our pages ----------
MARK = re.compile(r"<sub>\[?page ([^\]<]+?)(?: \(end\))?\]?(?:\([^)]*\))?</sub>")
ours = defaultdict(lambda: {"text": [], "files": set()})
FOOT = {}
for f in sorted(srcdir.glob("*.md")):
    t = f.read_text()
    FOOT[f.name] = "\n".join(re.findall(r"^\[\^[^\]]+\]:.*$", t, flags=re.M))
    parts = MARK.split(t)
    for i in range(1, len(parts), 2):
        p = parts[i].strip()
        ours[p]["text"].append(parts[i + 1])
        ours[p]["files"].add(f.name)


def our_parts(txt):
    txt = re.sub(r"<!--.*?-->", "", txt, flags=re.S)
    foot = "\n".join(re.findall(r"^\[\^[^\]]+\]:.*$", txt, flags=re.M))
    body = re.sub(r"^\[\^[^\]]+\]:.*$", "", txt, flags=re.M)
    disp = re.findall(r"```math\n(.*?)\n\s*(?:> )?```", body, flags=re.S)
    disp = [re.sub(r"^> ", "", d, flags=re.M) for d in disp]
    body_nm = re.sub(r"```math\n.*?```", " ", body, flags=re.S)
    inl = re.findall(r"\$`(.*?)`\$", body_nm)
    prose = re.sub(r"\$`.*?`\$", " ", body_nm)
    prose = re.sub(r"\]\([^)]*\)", "]", prose)  # link targets
    prose = re.sub(r"<[^>]+>", " ", prose)
    return disp, inl, prose, foot


def ocr_parts(t):
    disp = re.findall(r"\$\$(.*?)\$\$", t, flags=re.S) + re.findall(r"\\\[(.*?)\\\]", t, flags=re.S)
    rest = re.sub(r"\$\$.*?\$\$|\\\[.*?\\\]", " ", t, flags=re.S)
    inl = re.findall(r"\$(.+?)\$", rest) + re.findall(r"\\\((.+?)\\\)", rest)
    prose = re.sub(r"\$(.+?)\$|\\\((.+?)\\\)", " ", rest)
    prose = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", prose)
    return disp, inl, prose


NUM = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?")
FIGL = re.compile(r"(?:Fig(?:ure|ur)?s?\.?|Abb(?:ildung)?(?:en)?\.?|fig\.|pl\.|planche)\s*(\d+[a-z]?(?:\s*(?:,|and|und|to|bis|–|-|or|oder|et|à)\s*\d+[a-z]?)*)", re.I)


class FIG:
    @staticmethod
    def findall(s):
        return [n for g in FIGL.findall(s) for n in re.findall(r"\d+", g)]
SEC = re.compile(r"§§?\s*(\d+)")


def nums(s, ocr=False):
    s = re.sub(r"(?<=\d)[ \u2009\u202f](?=\d{3}\b)", "", s)
    if ocr:
        s = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", s)
    else:
        s = re.sub(r"(?<=\d),(?=\d{3}\b)", "", s)
        s = re.sub(r"(?<=\d),(?=\d)", " ", s)
    return set(x.replace(",", ".") for x in NUM.findall(s) if not re.match(r"0\d", x))


def mnums(eqs):
    return set(x for x in NUM.findall(" ".join(re.sub(r"[_^]", " ", norm(e)) for e in eqs)) if not re.match(r"0\d", x))


def roman_to_int(r):
    v = dict(I=1, V=5, X=10, L=50, C=100)
    try:
        n = 0
        for a, b in zip(r, r[1:] + " "):
            n += -v[a] if b != " " and v[b] > v[a] else v[a]
        return n
    except KeyError:
        return None


report, data = [], {}
for p, d in ours.items():
    if not p.isdigit():
        continue  # roman front matter is checked separately
    pdfp = int(p) + off
    of = ocrdir / f"p{pdfp:04d}.md"
    if not of.exists():
        continue
    mt = uniscripts(of.read_text())
    # drop the running head: everything up to a page-number-only line among the first 3 non-empty lines
    lines = mt.split("\n")
    ne = [k for k, l in enumerate(lines) if l.strip()][:3]
    for k in ne:
        if re.fullmatch(rf"\W*{p}\W*", lines[k].strip()) or (k == ne[0] and len(lines[k]) < 150 and re.fullmatch(rf"(\W*{p}\b.*|.*\b{p}\W*)", lines[k].strip())):
            for j in range(k + 1):
                lines[j] = ""
            nxt = [j for j in range(k + 1, len(lines)) if lines[j].strip()][:1]
            if nxt and len(lines[nxt[0]]) < 120 and re.search(r"Kapitel|^§|Abschnitt|Chapitre|SECTION", lines[nxt[0]].strip()):
                lines[nxt[0]] = ""
            break
    # drop the printer's signature line and bare sheet numbers at the foot of the page
    while lines and (not lines[-1].strip() or re.fullmatch(r"[\d*\s]{1,12}", lines[-1].strip())
                     or re.fullmatch(r".{0,40}(Graphische Statik|Graph\. Statik|Henneberg|Poncelet|Mém\.).{0,30}", lines[-1].strip())):
        lines.pop()
    mt = "\n".join(lines)
    txt = "\n".join(d["text"])
    od, oi, oprose, ofoot = our_parts(txt)
    md, mi, mprose = ocr_parts(mt)
    items = []
    # display equations
    mnd = [norm(x) for x in md]
    mall = norm(" ".join(md + mi)) + "|" + norm(mprose)
    mcands = mnd + [a + b for a, b in zip(mnd, mnd[1:])] + [a + b + c for a, b, c in zip(mnd, mnd[1:], mnd[2:])]
    for e in od:
        ne = norm(e)
        if not ne or ne in mcands or ne in mall:
            continue
        best = max(mcands, key=lambda c: difflib.SequenceMatcher(None, ne, c).ratio(), default="")
        r = difflib.SequenceMatcher(None, ne, best).ratio() if best else 0
        items.append({"kind": "display", "ours": e.strip(), "ocr": md[mcands.index(best) % len(md)].strip() if best and best in mnd else best, "ratio": round(r, 2)})
    # Mistral display equations with nothing similar in ours
    oall = [norm(x) for x in od] + [norm(x) for x in oi]
    ojoin = "|".join(oall) + "|" + norm(oprose)
    for e, ne in zip(md, mnd):
        if len(ne) < 4 or ne in ojoin:
            continue
        best = max([norm(x) for x in od] or [""], key=lambda c: difflib.SequenceMatcher(None, ne, c).ratio())
        if difflib.SequenceMatcher(None, ne, best).ratio() < 0.6:
            items.append({"kind": "ocr-display-unmatched", "ocr": e.strip()})
    # inline math
    for e in [x for y in oi for x in (re.split(r"(?<!\\),", y) if "," in y and "\\frac" not in y and y.count("{") == y.count("}") and all(p.count("{") == p.count("}") for p in re.split(r"(?<!\\),", y)) else [y])]:
        ne = norm(e)
        if len(re.sub("[\x02\x03]", "", ne)) < 3 or ne in mall:
            continue
        items.append({"kind": "inline", "ours": e})
    # equation numbers
    ot, mtg = set(sum((tags(x) for x in od), [])), set(sum((tags(x) for x in md), []))
    anyref = set(re.findall(r"\(\s*(\d+[a-z]?)\s*\)", mt.replace("{", "").replace("}", "")))
    ourref = set(re.findall(r"\(\s*(\d+[a-z]?)\s*\)", txt)) | ot
    if (ot - anyref - mtg) or (mtg - ourref):
        items.append({"kind": "eqno", "ours_only": sorted(ot - anyref - mtg), "ocr_only": sorted(mtg - ourref)})
    # figures, sections
    of_, mf = set(FIG.findall(oprose + ofoot)), set(FIG.findall(mprose))
    if mf - of_ or of_ - mf:
        items.append({"kind": "figure", "ours_only": sorted(of_ - mf, key=int), "ocr_only": sorted(mf - of_, key=int)})
    os_, ms = set(SEC.findall(oprose)), set(SEC.findall(mprose))
    if ms - os_:
        items.append({"kind": "section", "ours_only": sorted(os_ - ms, key=int), "ocr_only": sorted(ms - os_, key=int)})
    # all numbers (text + math)
    on_body = nums(oprose) | mnums(od + oi)
    on = on_body | nums(ofoot) | nums(" ".join(FOOT[f] for f in d["files"]))
    mn = nums(mprose, True) | mnums(md + mi)
    small = {str(k) for k in range(13)}
    small_ours = on & small
    on -= small | {p}; mn -= small | {p}; on_body -= small | {p}
    allours = on | small_ours
    miss = sorted((x for x in mn - on if not ("." in x and set(x.split(".")) <= allours | {y.lstrip("0") or "0" for y in allours})), key=lambda x: float(x))
    extra = sorted(on_body - mn, key=lambda x: float(x))
    if miss or extra:
        items.append({"kind": "numbers", "ocr_only": miss, "ours_only": extra})
    if items:
        data[p] = {"pdf_page": pdfp, "files": sorted(d["files"]), "items": items}

json.dump(data, open(book / "mismatches.json", "w"), ensure_ascii=False, indent=1)
out = [f"# Mismatches: {book.name} (src vs Mistral OCR)\n", f"Pages compared: {sum(1 for p in ours if p.isdigit() and (ocrdir / f'p{int(p)+off:04d}.md').exists())}; pages with items: {len(data)}\n"]
cnt = defaultdict(int)
for p in sorted(data, key=int):
    d = data[p]
    out.append(f"\n## p. {p} (PDF {d['pdf_page']}) — {', '.join(d['files'])}\n")
    for it in d["items"]:
        cnt[it["kind"]] += 1
        k = it["kind"]
        if k == "display":
            out.append(f"- display ({it['ratio']}): ours `{it['ours']}` | ocr `{it['ocr']}`")
        elif k == "ocr-display-unmatched":
            out.append(f"- ocr display not in ours: `{it['ocr']}`")
        elif k == "inline":
            out.append(f"- inline not in ocr: `{it['ours']}`")
        else:
            out.append(f"- {k}: " + "; ".join(f"{a} {b}" for a, b in it.items() if a != "kind"))
out.insert(2, "Items by kind: " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())) + "\n")
(book / "MISMATCHES.md").write_text("\n".join(out) + "\n")
print(book.name, "pages with items:", len(data), dict(cnt))
