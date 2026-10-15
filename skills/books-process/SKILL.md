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
2. Read workspace `tools/AGENT_BRIEF.md` (ETH variant for course material); follow
   the shared guide. Work in chapter-sized units and resume existing work without overwriting it.
3. Transcribe/translate to `src/` with exact formulas, printed page/section markers,
   footnoted uncertainty, and original cropped figures. Build published chapters.
4. Check every equation against the scan; perform a separate review pass and log
   findings. Claim independent review only if a separate reviewer actually performed it.
5. Create README, INDEX, GLOSSARY, and FIGURES; follow the guide's construction rules.
6. Regenerate `LIBRARY.md` using workspace `tools/library_map.py`; verify map freshness
   and build reports. Keep incomplete chapters explicitly marked unfinished.

## Finish

- Report output folder, completed chapters, review status, and remaining issues in short bullets.
- Default to local processing. Upload only if the user's invocation also requests
  publishing; use existing local R2 credentials and the upload helper, without exposing keys.
- Do not commit, push, delete originals, or replace existing published content unless requested.
- This skill guides the host agent's local tools; MCP itself supplies read-only retrieval.
