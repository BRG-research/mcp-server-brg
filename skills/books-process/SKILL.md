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
- The workspace `tools/` folder is this repo's `books-tools/` (symlink it: `ln -s <repo>/books-tools <Books>/tools`);
  `books-tools/templates/` holds example per-book briefs and a PROCESSING.md from a finished book.
- Check PDF/image tooling and the workspace's trusted conversion scripts/briefs.
  If required tools are missing, report the exact missing dependency and complete
  any feasible scan/contents inspection; do not pretend conversion was completed.
- Preserve the input PDF unchanged. Download remote PDFs into workspace `RAW/`.
- Infer title, author, source language, and a stable author-title folder ID from
  the scan. Default output to English. Ask only when identity or destination is ambiguous.

## Process

1. Check pages, scan quality, contents, and errata. Save scope/progress in the book's `PROCESSING.md`.
   Spread scans: `tools/scan_split.py` (check one spread's rotation first).
   OCR: always `tools/mistral_ocr.py` (Markdown with LaTeX equations and equation numbers, about $0.001/page;
   key in `~/.config/mistral/api_key`; only public-domain scans and BRG's own publications). Render pages first with
   `tools/pdf_render.py` (200 dpi, `p####.jpg` = PDF page) and run several shards in parallel; the per-page cache means
   a rerun never pays twice. Keep the cache until the book is published. Report pages billed and the running cost
   (pages × $0.001) in every progress update. Fall back to `tools/scan_ocr.sh` (tesseract) only without a key or for
   material that must not leave the machine, and say so.
   Map printed pages, detect duplicate scans (same printed number / near-identical image) and gaps with Python, not by reading.
   Cost: translation and proofread sub-agents run on Sonnet, ≤ 12 printed pages per job, working from the OCR draft and
   cropped equation/figure zones (never whole spreads in bulk). Sonnet proofreaders list doubtful pages under FLAGS;
   one Opus pass checks only those pages. Run automatic checks first (KaTeX compiles; every number, equation, figure
   and § number of the OCR appears in the translation; page markers complete).
2. Read workspace `tools/TRANSLATE_BRIEF.md` (or `AGENT_BRIEF.md`; ETH variant for course material);
   follow the shared guide. Work in chapter-sized units and resume existing work without overwriting it.
3. Transcribe/translate to `src/` with exact formulas, printed page/section markers,
   footnoted uncertainty, and original cropped figures (`tools/pagetool.py`). All text in English.
   Merge continuation parts with `tools/merge_parts.py`. Build published chapters.
4. Check every equation against the scan; run a separate page-by-page proofread (`tools/PROOF_BRIEF.md`)
   and log it in `REVIEW-*.md`. Then one book-wide consistency pass (terms, notation, title line)
   and `tools/fix_anchors.py`. Claim independent review only if a separate reviewer actually performed it.
5. Label structural figures (`tools/structlabels.py` as a first pass). Create README, INDEX, GLOSSARY,
   and FIGURES; follow the guide's construction rules. Publish the scanned pages with `tools/scan_index.py`
   (`scans/` images + `SCANS.md`, printed page → scan) and link SCANS.md from README, so every page can be checked.
   Add `cover.jpg` (the scanned cover, or the title page; ≈600 px wide, scanner edges trimmed) for the library shelf.
6. After upload, add the book to R2 `PROCESSED.md` (`| \`<id>/\` | YYYY-MM-DD | done |`; only `done` entries appear
   in LIBRARY.md and on the course website, with that date), then regenerate and upload `LIBRARY.md`
   (`tools/r2_library_map.sh --upload`); verify build reports. Unfinished books get no `done` row.
7. Record what is still missing or unreadable (pages, plates, sources) in the repo's
   `docs/books/books_missing_pages.md`: a short needs-only list; remove items once resolved and books once complete.

## Re-check a published book against the Mistral OCR

Use after translating (step 4) and for books already in R2. Do not reprocess or re-upload the whole book.
1. Download the book's current `*.md` and `src/` from R2; confirm `src/build.py` (or the shared one) rebuilds the
   published files byte for byte before editing anything.
2. Render the scan (`tools/pdf_render.py`), verify the printed-page offset on one page, OCR it (`tools/mistral_ocr.py`).
3. `tools/mistral_compare.py SRC OCR OFFSET OUT --jobs` → `MISMATCHES.md` and job files. Tune nothing by reading pages;
   if noise dominates, fix the normalisation in the script.
4. One Sonnet job per job file with `tools/CHECK_BRIEF.md` (≤ 12 pages, cropped zones only). Re-check every
   `OURS_WRONG`, `AUTHOR_MISPRINT`, `UNCLEAR` and every hedged `OK` on the scan yourself before editing;
   one Opus pass only for what stays unclear.
5. Fix `src/` (author misprints kept as printed with an "as printed" footnote), rebuild only the changed chapters,
   `tools/fix_anchors.py`, check that no new equation images are missing on R2, upload only the changed files to the
   same keys (delete nothing), and append a neutral note to the book's REVIEW log (or the README "Review status"):
   "Equations and numbers re-checked against a second OCR of the scan, <month year>" with the corrections listed.
   Text: `tools/mistral_textcheck.py SRC OCR OFFSET OUT --jobs` flags pages whose English length departs from the
   source (omissions, additions); check them with `tools/TEXT_CHECK_BRIEF.md` (Sonnet, ≤ 12 pages) and verify every
   OURS_WRONG against the source yourself before fixing.
6. Report per book: pages OCR'd, pages billed and cost, mismatches, fixes (page + what), unclear items, files uploaded.
   Delete local work files afterwards.

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
