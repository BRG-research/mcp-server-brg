"""Build the embedding (meaning-based) index for hybrid search.

    pip install sentence-transformers numpy      # once
    python3 tools/embed.py                       # build or update .index/embeddings.npz
    python3 tools/embed.py --model BAAI/bge-base-en-v1.5   # a larger model (rebuilds everything)

What it does: cuts every section, glossary line and figure description that tools/search.py
indexes into passages of about 200 words, and turns each passage into a vector (a list of
384 numbers) with a small open embedding model that runs on this computer. Passages with
similar meaning get similar vectors even when they share no words ("thrust line" and
"line of pressure"), which keyword search cannot do. tools/search.py then merges both
rankings.

Runs on whatever the machine has: NVIDIA GPU (cuda), Apple GPU (mps) or CPU. The model
(~130 MB) is downloaded from Hugging Face on first use and cached. Nothing is sent to any
service; the text never leaves the computer.

Incremental: each passage is keyed by a hash of its text, so after adding or editing a book
only new or changed passages are embedded. The index lives in .index/ (git-ignored; it is
rebuilt from the Markdown, which stays the source of truth).
"""
import argparse, hashlib, json, pathlib, re, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from search import ROOT, docs, doc_key  # noqa: E402

INDEX = ROOT / ".index" / "embeddings.npz"
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = {  # some models are trained to see an instruction before the query
    "BAAI/bge-small-en-v1.5": "Represent this sentence for searching relevant passages: ",
    "BAAI/bge-base-en-v1.5": "Represent this sentence for searching relevant passages: ",
    "BAAI/bge-large-en-v1.5": "Represent this sentence for searching relevant passages: ",
}
WORDS, OVERLAP = 200, 40


def clean(text):
    """Markdown/HTML to plain prose; LaTeX kept (symbols still carry some meaning)."""
    text = re.sub(r"<img[^>]*alt=\"([^\"]*)\"[^>]*>", r" \1 ", text)   # keep alt text
    text = re.sub(r"<[^>]+>|```math|```|\$`|`\$", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def passages(d):
    """Split one search document into overlapping word windows, each prefixed with its
    title so a passage from the middle of a section still says what it is about."""
    words = clean(d["text"]).split()
    head = f"{d['book']} · {d['title']}"
    if len(words) <= WORDS + OVERLAP:
        yield f"{head}\n{' '.join(words)}"
        return
    for i in range(0, len(words) - OVERLAP, WORDS - OVERLAP):
        yield f"{head}\n{' '.join(words[i:i + WORDS])}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", help=f"embedding model (default: the one in the index, else {DEFAULT_MODEL})")
    ap.add_argument("--batch", type=int, default=64)
    a = ap.parse_args()

    import numpy as np
    from sentence_transformers import SentenceTransformer

    old = {}
    model_name = a.model
    if INDEX.exists():
        z = np.load(INDEX, allow_pickle=False)
        meta = json.loads(str(z["meta"]))
        if model_name in (None, meta["model"]):
            model_name = meta["model"]
            old = dict(zip(z["hash"].tolist(), z["vec"]))
        else:
            print(f"model changed ({meta['model']} -> {model_name}): re-embedding everything")
    model_name = model_name or DEFAULT_MODEL

    keys, texts, hashes = [], [], []
    for d in docs():
        for p in passages(d):
            keys.append(doc_key(d))
            texts.append(p)
            hashes.append(hashlib.sha1(p.encode()).hexdigest()[:16])
    todo = [i for i, h in enumerate(hashes) if h not in old]
    print(f"{len(texts)} passages, {len(texts) - len(todo)} unchanged, {len(todo)} to embed")

    model = SentenceTransformer(model_name)
    print(f"model {model_name} on {model.device}")
    new = {}
    if todo:
        t = time.time()
        vecs = model.encode([texts[i] for i in todo], batch_size=a.batch, normalize_embeddings=True,
                            show_progress_bar=True, convert_to_numpy=True)
        new = {hashes[i]: v for i, v in zip(todo, vecs)}
        print(f"embedded {len(todo)} passages in {time.time() - t:.0f} s")
    vec = np.stack([new.get(h, old.get(h)) for h in hashes]).astype(np.float16)

    INDEX.parent.mkdir(exist_ok=True)
    (INDEX.parent / ".gitignore").write_text("*\n")
    meta = {"model": model_name, "query_prefix": QUERY_PREFIX.get(model_name, ""),
            "words": WORDS, "overlap": OVERLAP}
    np.savez_compressed(INDEX, vec=vec, key=np.array(keys), hash=np.array(hashes), meta=np.array(json.dumps(meta)))
    print(f"wrote {INDEX.relative_to(ROOT)} ({vec.shape[0]} × {vec.shape[1]}, "
          f"{INDEX.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    sys.exit(main())
