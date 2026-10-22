"""Search the whole library: keyword (BM25) and, once built, meaning (embeddings).

    python3 tools/search.py "Ritter section method"          # top 10 hits
    python3 tools/search.py "funicular polygon" -n 20
    python3 tools/search.py "EI" --book graphic-statics-levy
    python3 tools/search.py "Cremona" --figures               # figure descriptions only
    python3 tools/search.py "why does an arch push outward" --semantic   # meaning only
    python3 tools/search.py "§ 204" --keyword                 # exact words only

Indexes every book folder that has a README.md: each `## ` section of each chapter
(source files in <book>/src/ when present, so formulas are searched as LaTeX), plus the
book's GLOSSARY.md and FIGURES.md entries. Prints file, section, printed page and a snippet,
so Claude can open only the part it needs. No dependencies beyond the standard library.

Hybrid by default when .index/embeddings.npz exists (build it with tools/embed.py):
the BM25 ranking and the embedding ranking are merged by reciprocal rank fusion, so a
section found by both rises to the top. Keyword search stays in the mix because formulas,
symbols (EI, μ, Σ_g) and section numbers (§ 204) do not survive embeddings well; meaning
search finds sections that say the same thing in other words. Without the index (or without
sentence-transformers installed) it falls back to keyword search with a one-line note.
"""
import argparse, math, pathlib, re, sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKEN = re.compile(r"§\s*\d+|[A-Za-zÀ-ÿα-ωΑ-Ω]+[′″']*(?:_\{?\w+\}?)?|\d+")


def tokens(text):
    text = text.replace("\\", " ")
    out = []
    for t in TOKEN.findall(text):
        t = t.lower()
        if len(t) > 2 and t.endswith("'s"):
            t = t[:-2]                      # possessive: Ritter's -> ritter
        elif len(t) > 2 and t.endswith("'") and t[:-1].isalpha():
            t = t[:-1]                      # plural possessive; keep primes on symbols like h'
        out.append(t)
    return out


def docs():
    for book in sorted(p for p in ROOT.iterdir() if (p / "README.md").exists()):
        src = book / "src" if (book / "src").exists() else book
        for f in sorted(src.glob("*.md")):
            if f.name in ("README.md",):
                continue
            text = f.read_text(encoding="utf-8")
            parts = re.split(r"(?m)^(?=## )", text)
            for part in parts:
                head = part.splitlines()[0] if part.strip() else ""
                if head.strip().lower() in ("## contents", "## table of contents"):
                    continue  # navigation tables would outrank the real sections
                pages = re.findall(r"<sub>pages? ([0-9–-]+)</sub>", part)
                yield {"book": book.name, "file": f.name, "kind": "section",
                       "title": head.lstrip("# ").strip() or "(front matter)",
                       "page": pages[0] if pages else "", "text": part}
        for extra, kind in (("GLOSSARY.md", "glossary"), ("FIGURES.md", "figure")):
            p = book / extra
            if p.exists():
                for line in p.read_text(encoding="utf-8").splitlines():
                    if line.startswith("|") and not set(line) <= set("|-: "):
                        yield {"book": book.name, "file": extra, "kind": kind,
                               "title": line.strip("| ")[:80], "page": "", "text": line}


def doc_key(d):
    return f"{d['book']}/{d['file']}#{d['kind']}#{d['title']}"


def bm25(D, query):
    toks = [tokens(d["text"]) for d in D]
    N = len(D) or 1
    avg = sum(map(len, toks)) / N
    df = Counter(t for ts in toks for t in set(ts))
    q = tokens(query)
    k1, b = 1.4, 0.75
    scored = []
    for i, ts in enumerate(toks):
        tf = Counter(ts)
        s = sum(math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5)) * tf[t] * (k1 + 1)
                / (tf[t] + k1 * (1 - b + b * len(ts) / avg)) for t in q if t in tf)
        if s > 0:
            scored.append((s, i))
    return sorted(scored, reverse=True)


def semantic(D, query):
    """Rank documents by their best-matching passage in the embedding index, or None."""
    index = ROOT / ".index" / "embeddings.npz"
    if not index.exists():
        return None, "no embedding index yet (python3 tools/embed.py): keyword search only"
    try:
        import json, numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None, "sentence-transformers not installed: keyword search only"
    z = np.load(index, allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    want = {doc_key(d): i for i, d in enumerate(D)}
    rows = [r for r, k in enumerate(z["key"].tolist()) if k in want]
    if not rows:
        return [], None
    model = SentenceTransformer(meta["model"])
    q = model.encode(meta["query_prefix"] + query, normalize_embeddings=True)
    sims = z["vec"][rows].astype(np.float32) @ q
    best = {}
    for r, s in zip(rows, sims):
        i = want[z["key"][r]]
        best[i] = max(best.get(i, -1.0), float(s))
    stale = len(set(want) - set(z["key"].tolist()))
    note = f"{stale} sections are not in the embedding index; rerun tools/embed.py" if stale else None
    return sorted(((s, i) for i, s in best.items()), reverse=True), note


def fuse(*rankings, k=60):
    """Reciprocal rank fusion: score = sum 1/(k + rank) over the rankings a document is in."""
    score = Counter()
    for ranking in rankings:
        for rank, (_, i) in enumerate(ranking):
            score[i] += 1 / (k + rank + 1)
    return sorted(((s * 100, i) for i, s in score.items()), reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("-n", type=int, default=10)
    ap.add_argument("--book")
    ap.add_argument("--figures", action="store_true", help="search figure descriptions only")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--keyword", action="store_true", help="BM25 only (exact words, symbols, §)")
    mode.add_argument("--semantic", action="store_true", help="embeddings only (meaning)")
    a = ap.parse_args()
    D = [d for d in docs() if (not a.book or d["book"] == a.book)
         and (not a.figures or d["kind"] == "figure")]
    kw = [] if a.semantic else bm25(D, a.query)
    sem, note = (None, None) if a.keyword else semantic(D, a.query)
    if note:
        print(f"[{note}]\n", file=sys.stderr)
    if a.semantic and sem is None:
        return 1
    ranked = kw if sem is None else sem if a.semantic else fuse(kw, sem)
    q = tokens(a.query)
    for s, i in ranked[: a.n]:
        d = D[i]
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>|```math|```", " ", d["text"]))
        i = min((text.lower().find(t) for t in q if text.lower().find(t) >= 0), default=0)
        snip = text[max(0, i - 80): i + 160]
        page = f" · p. {d['page']}" if d["page"] else ""
        print(f"{s:5.1f}  {d['book']}/{d['file']} · {d['title'][:70]}{page}\n       …{snip}…\n")


if __name__ == "__main__":
    sys.exit(main())
