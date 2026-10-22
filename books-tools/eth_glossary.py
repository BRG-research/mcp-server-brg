"""Merge the reviewers' index data (work/index-parts/NN.json) into GLOSSARY.md and the INDEX.md summaries.

  python3 tools/eth_glossary.py <index-parts-dir>
Writes graphic-statics-student-course/GLOSSARY.md (terms + symbols, with the files that use them) and
graphic-statics-student-course/summaries.json (chapter summaries, used by eth_assemble.py for INDEX.md).
"""
import json, sys, re, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOOK = ROOT / "graphic-statics-student-course"
PARTS = pathlib.Path(sys.argv[1])
units = {u["pos"]: u for u in json.load(open(ROOT / "tools" / "eth_units.json"))}

def norm(s): return re.sub(r"\s+", " ", re.sub(r"[()\[\]]", "", s.lower())).strip()
def get(d, *keys, default=""):
    for k in keys:
        if k in d and d[k]: return str(d[k]).strip()
    return default

terms = collections.defaultdict(lambda: {"de": collections.Counter(), "en": collections.Counter(), "modern": collections.Counter(), "where": []})
symbols = collections.defaultdict(lambda: {"meaning": collections.Counter(), "note": collections.Counter(), "where": []})
summaries = {}
for f in sorted(PARTS.glob("[0-9][0-9].json")):
    pos = int(f.stem)
    try: d = json.load(open(f))
    except Exception as e: print("bad json", f, e); continue
    summaries[pos] = d.get("summary", "")
    for t in d.get("terms", []):
        de = get(t, "de", "german", "term"); en = get(t, "en", "english")
        if not de or not en or "English" in de and "source" in de: continue
        if de.startswith("—") or de.startswith("-"): continue
        if len(de.split()) > 6 or norm(de) == norm(en): continue   # captions/phrases and identical words are not glossary entries
        k = norm(de)
        terms[k]["de"][de] += 1; terms[k]["en"][en] += 1
        m = get(t, "modern")
        if m and norm(m) != norm(en): terms[k]["modern"][m] += 1
        terms[k]["where"].append((pos, get(t, "where")))
    for s in d.get("symbols", []):
        sy = get(s, "symbol"); me = get(s, "meaning")
        if not sy or not me: continue
        k = sy
        symbols[k]["meaning"][me] += 1
        n = get(s, "note", "notes")
        if n: symbols[k]["note"][n] += 1
        symbols[k]["where"].append((pos, get(s, "where")))
json.dump({str(k): v for k, v in summaries.items()}, open(BOOK / "src" / "summaries.json", "w"), ensure_ascii=False, indent=1)

def fname(pos): return units[pos]["file"]
def refs(w, limit=4):
    seen, out = set(), []
    for pos, wh in sorted(w):
        if pos in seen: continue
        seen.add(pos); out.append(f"[{pos:02d}]({fname(pos)})" + (f" {wh}" if wh and len(out) < 2 else ""))
        if len(out) >= limit: break
    more = len({p for p, _ in w}) - len(out)
    return ", ".join(out) + (f" +{more}" if more > 0 else "")

lines = ["# Glossary\n",
 "German terms of the ETH *Tragwerksentwurf* course → the English used in this edition (→ modern equivalent where it differs), and the symbols used. "
 "Compiled from the independent review of every file; the last column links to the files that use the entry (file number, first slide/page). "
 "Where a German term has been rendered in more than one way across the course the alternatives are listed with *also:*; "
 "`(ours)`-style coinages were avoided where the course gives its own English: the course's own bilingual glossary is reproduced in "
 f"[the SD II reference file]({fname(17)}) and its symbol list in [the SD III reference file]({fname(29)}).\n",
 "Conventions that apply throughout: *Lageplan* = form diagram, *Kräfteplan* = force diagram, subscript **d** = design value, **k** = characteristic value, "
 "**Colours:** the course's exercise handouts prescribe *red = tension, blue = compression, green = external forces* for answers; the lecture slides use red and blue the same way in many drawings but carry no legend, so this edition reports colours as drawn and states tension/compression only where the slide or the exercise rule says so.\n"]
lines += ["\n## Terms\n", "| German | English | Modern / note | Files |", "|---|---|---|---|"]
conf = 0
for k in sorted(terms, key=lambda x: x):
    t = terms[k]
    de = t["de"].most_common(1)[0][0]
    ens = t["en"].most_common()
    en = ens[0][0]; alts = [e for e, _ in ens[1:4] if norm(e) != norm(en)]
    note = "; ".join(m for m, _ in t["modern"].most_common(2))
    if alts: note = (note + "; " if note else "") + "*also:* " + " / ".join(alts); conf += 1
    lines.append(f"| {de} | {en} | {note.replace('|','/')} | {refs(t['where'])} |")
lines += ["\n## Symbols\n", "| Symbol | Meaning (as used in the course) | Note | Files |", "|---|---|---|---|"]
def skey(s): return (s.lower(), s)
for k in sorted(symbols, key=skey):
    s = symbols[k]
    ms = s["meaning"].most_common(3)
    meaning = ms[0][0] + ("" if len(ms) == 1 else "; *also:* " + " / ".join(m for m, _ in ms[1:]))
    note = "; ".join(n for n, _ in s["note"].most_common(1))
    lines.append(f"| {k.replace('|','/')} | {meaning.replace('|','/')} | {note.replace('|','/')} | {refs(s['where'])} |")
(BOOK / "GLOSSARY.md").write_text("\n".join(lines) + "\n")
print(len(terms), "terms,", conf, "with alternative renderings;", len(symbols), "symbols;", len(summaries), "summaries")
