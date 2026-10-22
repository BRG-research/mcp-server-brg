#!/usr/bin/env bash
# OCR draft text for every page image of a book key (a cheap first draft; formulas, numbers and tables
# must always be read from the image).
#   bash tools/scan_ocr.sh KEY LANG [WORK]      LANG: fra | deu | eng   -> WORK/KEY/ocr/<page>.txt
# Needs tesseract with the language data. Without root it installs into a user env, e.g.
#   micromamba create -p <dir>/env -c conda-forge tesseract   and   TESSERACT=<dir>/env/bin/tesseract
#   TESSDATA_PREFIX=<dir>/env/share/tessdata   (download fra/deu.traineddata from tessdata_fast if missing).
set -euo pipefail
KEY=$1 LANG_=$2
WORK=${3:-${BOOKS_WORK:-$(cd "$(dirname "$0")/.." && pwd)/work}}
TESS=${TESSERACT:-tesseract}
export OMP_THREAD_LIMIT=1
mkdir -p "$WORK/$KEY/ocr"
export TESS WORK KEY LANG_
ls "$WORK/$KEY/pages/"*.jpg | xargs -P 8 -I{} sh -c 'b=$(basename "{}" .jpg); [ -s "$WORK/$KEY/ocr/$b.txt" ] || "$TESS" "{}" "$WORK/$KEY/ocr/$b" -l "$LANG_" >/dev/null 2>&1'
ls "$WORK/$KEY/ocr" | wc -l
