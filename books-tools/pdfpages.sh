#!/usr/bin/env bash
# Render a PDF's pages to PNG for reading: pdfpages.sh <pdf> <outdir> [dpi=110]
set -euo pipefail; mkdir -p "$2"; pdftoppm -r "${3:-110}" -png "$1" "$2/p"; ls "$2" | wc -l
