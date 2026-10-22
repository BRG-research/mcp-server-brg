# Proofreading brief — BRG publications (full proofread)

> Reusable brief (October 2026). WORK = the processing folder (default `<Books>/work`, or a session scratch folder); tools are in `<Books>/tools/`. Replace the placeholders, copy the brief next to the work, and add a row for the book to the table.

Work only inside WORK (the PDFs are read-only in <Books>/RAW/brg-publications/). Use `/usr/bin/python3 -I` for Python.

Each paper folder `WORK/pubout/papers/<name>/` holds `paper.md` (automatic PyMuPDF extraction) and `figures/`. The original is
`<Books>/RAW/brg-publications/<name>.pdf`. Your job: turn each `paper.md` into a faithful, clean, proofread Markdown
version of the published paper.

## Procedure, per paper
1. Render the pages: `<Books>/tools/pdfpages.sh <pdf> WORK/ppages/<name>` (110 dpi PNG, files p-01.png …). Read every page image.
   For small print or equations zoom: `/usr/bin/python3 -I <Books>/tools/pagetool.py zoom WORK/ppages/<name> p-03.png x0 y0 x1 y1 WORK/z_<batch>_<name>_<n>.jpg` (ALWAYS prefix temp files with your batch id — other agents run in parallel)
   (or re-render one page at higher dpi with `pdftoppm -r 220 -f N -l N -png <pdf> WORK/ppages/<name>/hi`). The text layer itself is reliable for wording;
   use `pdftotext -layout -f N -l N <pdf> -` to check a passage.
2. Metadata: never invent or infer a DOI or bibliographic detail. Change one only if you confirm it (e.g. `curl -sL -H "Accept: application/vnd.citationstyles.csl+json" https://doi.org/<doi>` returns this title/authors); otherwise keep it and note the doubt in the log.
   Keep the metadata header at the top of `paper.md` (title, authors, venue, links, abstract) unchanged except for factual errors; replace the
   "Automatic text extraction …" quote with:
   `> Proofread against the published PDF, October 2026. Check the original PDF before citing.`
3. Below the `---`, make the body match the paper:
   - Remove running headers/footers, page numbers, line numbers, journal boilerplate repeated on every page, and the duplicated title/author block
     (affiliations may stay once, as a short line).
   - Correct reading order (multi-column layouts, text split around figures), paragraph joins, hyphenation across lines, ligatures.
   - Headings: the paper's own section numbering and titles as `##`/`###`.
   - **Equations:** rewrite every equation as LaTeX — inline `$...$`, display in fenced ```` ```math ```` blocks — symbol for symbol with the
     paper's equation numbers (`\tag{3}`). Check each against the page image.
   - **Tables:** Markdown tables, every cell checked.
   - **Figures:** each figure as `![Fig. N](figures/<file>)` followed by its caption line `*Figure N: …*` (verbatim), placed after the paragraph
     that first cites it. Delete images that are not figures (logos, publisher icons, decorative strips, fragments) — remove the file too.
     If a figure is missing or broken (vector drawings are often lost), crop it from the page render (crops from PDF renders keep their colour):
     `/usr/bin/python3 -I <Books>/tools/pagetool.py crop WORK/ppages/<name> p-04.png x0 y0 x1 y1 WORK/pubout/papers/<name> fig04` (writes
     figures/fig04.png; Read the preview) — use a 220-dpi render for crops.
   - Footnotes as `[^n]`; references list as a numbered or author–year list exactly as printed; keep DOIs/URLs.
   - Never summarise, shorten or add content. Keep the authors' spelling. Unclear spots: best reading + `[uncertain reading]`.
4. Check: every `figures/` link resolves, no orphan image files remain, every page of the PDF is represented.

## Log and report
Append one section per paper to `WORK/pubout/REVIEW/<batch>.md` (create the folder): pages, equations/tables/figures counts, main fixes, remaining
uncertainties, what you could not check. Report to the lead in ≤ 10 lines for the whole batch.
Delete your `WORK/ppages/<name>` renders when a paper is finished.
