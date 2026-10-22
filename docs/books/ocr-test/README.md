# OCR test: Mistral OCR vs. tesseract (and Marker)

Test set: Henneberg, *Die graphische Statik der starren Systeme* (1911), printed pp. 217–228 (Chapter 9, the continuous beam;
many display equations). Public domain.

| File | Content |
|---|---|
| `henneberg-p217-228.pdf` | the 12 scanned pages, 300 dpi |
| `tesseract/p0217.txt` … | current OCR draft (tesseract, German), used today for translation |
| `marker/henneberg-p217-228.md` | Marker 1.x output (local, CPU: 63 min for 12 pages; display equations as LaTeX, inline symbols sometimes wrong, e.g. ϱ read as o) |
| `mistral/` | Mistral OCR output — create it with the steps below |

Reference: the finished English translation of these pages is chapter 9 of the published book
(`graphic-statics-henneberg/09-chapter-09.md` in the library).

## Run Mistral OCR (macOS or Linux)

1. Key from https://console.mistral.ai → API Keys → Create new key (shown once). Save it without putting it in a command line:

   ```
   mkdir -p ~/.config/mistral && read -s "k?Mistral key: " && echo "$k" > ~/.config/mistral/api_key && chmod 600 ~/.config/mistral/api_key && unset k
   ```
   (zsh, the macOS default; in bash use `read -s -p "Mistral key: " k`.)

2. From the repository root:

   ```
   python3 -I scripts/mistral_ocr.py docs/books/ocr-test/mistral docs/books/ocr-test/henneberg-p217-228.pdf
   ```
   Writes `mistral/henneberg-p217-228-p001.md` … `-p012.md` (p001 = printed p. 217). Cost: 12 pages ≈ $0.01.

3. Compare page by page with `tesseract/` and the scan: wording (German umlauts, ß, Fraktur-free Antiqua), reading order,
   footnotes, and above all the equations (fractions, indices, primes ′ ″, ≷, determinants).

The pages are sent to api.mistral.ai, so use the script only for public-domain scans and BRG's own publications.
