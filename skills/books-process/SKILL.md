---
name: books-process
description: Process a scanned structural engineering book from a local PDF path or HTTPS URL into reviewed English Markdown chapters, formulas, figures, and library indexes.
---

# Process a scanned book

Input: a local PDF path or HTTPS URL supplied by the user.

## Start

- Accept a quoted local PDF path or HTTPS URL. Ask for the source only if missing.
- Use `get_book_guide(include_library_map=false)` for conventions; without MCP,
  read `src/brg_mcp/book_guidance.md` from this checkout.
- Find the existing Books workspace from the supplied path, `BRG_BOOKS_DIR`, or a
  sibling `Books/` directory. Otherwise create a separate local workspace beside
  the PDF, or ask for a location when the input is a URL. Keep PDFs outside this code repo.
- Check PDF/image tooling and the workspace's trusted conversion scripts/briefs.
  If required tools are missing, report the exact missing dependency and complete
  any feasible scan/contents inspection; do not pretend conversion was completed.
- Preserve the input PDF unchanged. Download remote PDFs into workspace `RAW/`.
- Infer title, author, source language, and a stable author-title folder ID from
  the scan. Default output to English. Ask only when identity or destination is ambiguous.

## Process

1. Check pages, scan quality, contents, and errata. Save scope/progress in the book's `PROCESSING.md`.
   Spread scans: `tools/scan_split.py` (check one spread's rotation first); OCR draft: `tools/scan_ocr.sh`.
2. Read workspace `tools/TRANSLATE_BRIEF.md` (or `AGENT_BRIEF.md`; ETH variant for course material);
   follow the shared guide. Work in chapter-sized units and resume existing work without overwriting it.
3. Transcribe/translate to `src/` with exact formulas, printed page/section markers,
   footnoted uncertainty, and original cropped figures (`tools/pagetool.py`). All text in English.
   Merge continuation parts with `tools/merge_parts.py`. Build published chapters.
4. Check every equation against the scan; run a separate page-by-page proofread (`tools/PROOF_BRIEF.md`)
   and log it in `REVIEW-*.md`. Then one book-wide consistency pass (terms, notation, title line)
   and `tools/fix_anchors.py`. Claim independent review only if a separate reviewer actually performed it.
5. Label structural figures (`tools/structlabels.py` as a first pass). Create README, INDEX, GLOSSARY,
   and FIGURES; follow the guide's construction rules.
6. Regenerate `LIBRARY.md` (`tools/r2_library_map.sh` for the published library, or `tools/library_map.py`);
   verify build reports. Keep incomplete chapters explicitly marked unfinished.
7. Record what is still missing or unreadable (pages, plates, sources) in the repo's
   `docs/books/books_missing_pages.md`: a short needs-only list; remove items once resolved and books once complete.

## Rescans and photographs

- Copy the originals to `RAW/rescans/<book>-<date>/`; identify the pages with `tools/photo_sheet.py`.
- Update only the affected cells/lines in `src/`, rewrite the footnotes ("read from a photograph of the
  printed page"), keep author misprints as printed, rebuild, append to the REVIEW log, upload the changed files.
- If a detail is hidden in the binding in every photo, say so and close the item instead of asking again.

## Finish

- Report output folder, completed chapters, review status, and remaining issues in short bullets.
- Default to local processing. Upload only if the user's invocation also requests
  publishing; use existing local R2 credentials and the upload helper, without exposing keys.
- Do not commit, push, delete originals, or replace existing published content unless requested.
  When updating published content, download the current R2 version first and change only what is needed.
- Published files never mention AI tools, models, or agents; review notes use neutral wording.
- This skill guides the host agent's local tools; MCP itself supplies read-only retrieval.
