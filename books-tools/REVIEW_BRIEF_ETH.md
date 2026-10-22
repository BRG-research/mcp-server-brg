# Brief: independent review of one converted unit (ETH Structural Design course edition)

You are an **independent reviewer**. A different agent converted one source (slides / exercise sheets / Skript pages) into the
English Markdown file you are given. Do not trust it: re-check it against the source images and fix what is wrong. Read
`tools/AGENT_BRIEF_ETH.md` first (formats, tools, conventions: it is the brief the converter followed), then work as below.
Paths: scratchpad `/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/`; book `/home/pv/Downloads/Books/graphic-statics-student-course/`; your unit is the entry with "pos" = NN in `/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/units.json`;
the file is `src/<file>` (edit ONLY `src/<file>` and figures with the file-number prefix `NN-`; never other files, README, git).
Sources: `work/text/DOCID.txt` (pdftotext), `work/sheets/DOCID/` (contact sheets, orientation only), `work/pages/DOCID/`,
and full-size views: `python3 /home/pv/Downloads/Books/tools/slidefig.py DOCID PAGE NN-rv --view --w 1200 [--crop x0 y0 x1 y1]`
→ read `/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/work/view/NN-rv.jpg` (always prefix names with your file number, e.g. 12-rv; the folder is shared).

## What to check (in this order of importance)
1. **Numbers, formulas, labels, credits, quoted values.** Compare every number, unit, symbol, subscript, sign, equation, table cell and
   photo credit with the image at full size. Recompute arithmetic of worked examples; a mismatch is either a transcription slip
   (fix it) or the author's own slip (keep the printed value and footnote it: never "correct" the author silently; over-correction is
   an error too).
2. **Every "read from the drawing", "[uncertain reading]", "not viewed at full size" or contact-sheet-only description** in the file:
   view the slide/page at full size (zoom with --crop for small labels) and resolve it: replace the hedge with the verified statement,
   or keep a short hedge only if the image really cannot settle it. Build-step descriptions: view first/last slide of each build
   and every slide where something new appears; the step list must match what is drawn. Tension/compression or colour meaning may be
   stated only if the slide itself says so.
3. **Completeness and translation.** Every slide/page of the unit's range must be represented and every printed text on it present
   (compare with work/text/DOCID.txt and the image). German-only text: translation must be accurate and complete (technical sense,
   no dropped sentences). Bilingual slides: the English line is authoritative; a German/English mismatch must be footnoted.
4. **Figures.** Each embedded image must exist (ls figures/NN-*) and show what its caption/alt says, with the whole diagram visible
   (page crops: nothing cut off). Fix crop/caption if not. No `<sub>`/`<sup>` inside captions or alt text. Remove dead images only if
   unreferenced.
5. **Markdown/build.** Footnotes referenced and defined, tables well-formed, anchors in the contents table match headings,
   `[NAV]`/nav comment lines untouched. After editing run
   `cd /home/pv/Downloads/Books && EQPNG=/tmp/eqpng python3 graphic-statics-student-course/src/build.py <file>` (must report
   `unconverted: 0 | unknown inline commands: none`).

Be economical: skip full-size viewing of pure photo slides (check their credits/captions against the text layer), but view every
slide with a diagram, table, formula, numbers or a hedge. Edit with the Edit tool in small, targeted changes.

## Review log (required)
Write `/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/work/review/NN.md` (NN = unit number, zero-padded): one line per change: `<location> | FIXED/CLARIFIED/FOOTNOTED/KEPT-HEDGE | was → now | evidence`.
End with counts and anything you could not settle.

## Index data (required)
Write `/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/work/index-parts/NN.json` (valid UTF-8 JSON):
```json
{"n": 7,
 "summary": "5–8 sentences: what this file covers, in modern engineering language: main concepts, constructions, worked examples/results, case studies (named), formulas/rules and which slides/pages carry them (cite slide numbers).",
 "terms": [{"de": "Seilpolygon", "en": "funicular polygon", "modern": "funicular (string) polygon / thrust line", "where": "slide 41"}],
 "symbols": [{"symbol": "H", "meaning": "pole distance = horizontal thrust", "where": "slides 60–66", "note": "optional: clash with modern usage"}]}
```
terms: 15–60 technical German terms actually used in the file (original → the English used in the file → modern equivalent if different);
symbols: all symbols the unit defines or uses with a specific meaning (none for pure case-study decks). Be accurate; use only what is in the file.

## Final report (≤ 15 lines)
Counts of FIXED / CLARIFIED / FOOTNOTED, the 3 most important fixes, items still unresolved, build result.
