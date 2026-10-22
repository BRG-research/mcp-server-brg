"""OCR page images with the Mistral OCR API into Markdown with LaTeX formulas (a cheap first draft).

    python3 -I tools/mistral_ocr.py OUT_DIR page1.jpg page2.jpg ...
    python3 -I tools/mistral_ocr.py OUT_DIR --glob 'work/<book>/pages/p0[0-1]*.jpg'
    python3 -I tools/mistral_ocr.py OUT_DIR scan.pdf          # a whole PDF in one request

Writes OUT_DIR/<image stem>.md per page (for a PDF: <pdf stem>-p001.md …) and skips inputs already done, so a run
can be resumed without paying twice. API key: env MISTRAL_API_KEY or ~/.config/mistral/api_key.
Only for public-domain scans and BRG's own publications: the pages are sent to api.mistral.ai.
"""
import base64, glob, json, os, pathlib, sys, time, urllib.error, urllib.request

API = "https://api.mistral.ai/v1/ocr"
MODEL = os.environ.get("MISTRAL_OCR_MODEL", "mistral-ocr-latest")


def key():
    k = os.environ.get("MISTRAL_API_KEY")
    if not k:
        f = pathlib.Path.home() / ".config/mistral/api_key"
        k = f.read_text().strip() if f.exists() else ""
    if not k:
        sys.exit("No Mistral API key: set MISTRAL_API_KEY or write it to ~/.config/mistral/api_key")
    return k


def ocr(path, k):
    data = base64.b64encode(path.read_bytes()).decode()
    if path.suffix.lower() == ".pdf":
        doc = {"type": "document_url", "document_url": f"data:application/pdf;base64,{data}"}
    else:
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        doc = {"type": "image_url", "image_url": f"data:{mime};base64,{data}"}
    body = json.dumps({"model": MODEL, "document": doc, "include_image_base64": False}).encode()
    req = urllib.request.Request(API, body, {"Authorization": f"Bearer {k}", "Content-Type": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 4:
                time.sleep(2 ** attempt * 3)
                continue
            sys.exit(f"{path.name}: HTTP {e.code} {e.read()[:300]!r}")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    files = sorted(glob.glob(sys.argv[3])) if sys.argv[2] == "--glob" else sys.argv[2:]
    k, n = key(), 0
    for f in map(pathlib.Path, files):
        pdf = f.suffix.lower() == ".pdf"
        dst = out / (f"{f.stem}-p001.md" if pdf else f.stem + ".md")
        if dst.exists():
            continue
        res = ocr(f, k)
        pages = res.get("pages", [])
        if pdf:
            for p in pages:
                (out / f"{f.stem}-p{p.get('index', 0) + 1:03d}.md").write_text(p.get("markdown", ""), encoding="utf-8")
        else:
            dst.write_text("\n\n".join(p.get("markdown", "") for p in pages), encoding="utf-8")
        n += res.get("usage_info", {}).get("pages_processed", 1)
        print(f"{f.name} -> {dst.name}")
    print(f"done: {n} pages billed")


if __name__ == "__main__":
    main()
