# Proofreading brief — Föppl, *Graphische Statik* (5th ed., 1920), page by page

WORK = /home/pv/brg/code_python/Books/work/graphic-statics-foeppl · TOOLS = /home/pv/brg/code_python/Books/tools · BOOK = WORK/out/graphic-statics-foeppl

Work only inside WORK. Use `/usr/bin/python3 -I` for Python. Absolute paths. Temp files only in WORK/tools-<yourjob>/. Never write anything about AI, models, Claude, Opus or agents in any file (logs included).

You are the proofreader of an existing English translation made by a separate translator pass. Proofread EVERY page of your range (at most 12 printed pages) against the German
(OCR text + scan zooms) — every sentence, number, symbol and equation — and fix what is wrong. Do not rewrite text that is correct. Read WORK/BRIEF-translate.md (conventions, terminology,
figure blocks, labels, Fraktur rule) and WORK/SECTIONS.md first.

Page images: `WORK/work/fpp/pages/pNNNN.jpg`. OCR draft (German): `WORK/work/fpp/ocr/pNNNN.txt`.
Zoom: `BOOKS_WORK=WORK/work /usr/bin/python3 -I TOOLS/pagetool.py zoom fpp p0123 x0 y0 x1 y1 WORK/tools-<job>/z.jpg`, then Read.
Re-crop a bad figure: `BOOKS_WORK=WORK/work /usr/bin/python3 -I TOOLS/pagetool.py crop fpp p0123 x0 y0 x1 y1 BOOK fig034a [--white …]` and Read the preview.

## Per page, check and fix
1. Completeness and faithfulness: every sentence, footnote, table row, equation, problem and list item present, in order, translated faithfully (nothing added or left out, no German left except
   titles/companions), terminology as in BRIEF-translate.md.
2. Equations: every symbol (letters, case, Fraktur vs italic, primes, sub/superscripts, signs, fractions, exponents, equation numbers) against a zoom.
3. Numbers and tables: every value, cell by cell, decimal points.
4. Figures: every figure on the page present, placed after the paragraph that cites it, caption number right; the crop shows the whole figure with all its letters and nothing else.
   Labels `[labels: …]` match the drawing (structural systems must carry them).
5. Page markers: each `<sub>page N</sub>` sits where page N starts.
6. Footnotes and corrections: author's misprints stay as printed with a footnote; silent corrections restored or footnoted; unclear → best reading + "[uncertain reading]".

## Rules
- Edit only your own file/page range with small targeted edits (Edit tool); re-read before each edit; never rewrite a file with a script.
- Build after editing: `/usr/bin/python3 -I BOOK/src/build.py <abs src file>` → `unconverted: 0`, `unknown inline commands: none`; read the equation sheets printed for your file and compare with the scan.
- Report terminology that differs from the brief instead of changing other files.

## Cost rules (mandatory)
- First run `/usr/bin/python3 -I WORK/tools-lead/autocheck.py BOOK/src/<file> FROM TO`; resolve every item (most are OCR noise; some are real omissions).
- Compare wording against the OCR text — no need to look at the image for plain prose. Look at the image only in small ZOOMS of equations, tables, figure labels and doubtful words. Do not Read whole pages repeatedly.
  Read each figure crop preview once (BOOK/figures/figNNN.png).
- Pages with an equation or figure you could not settle with confidence go into the FLAGS section of your log (page, item, why) — one careful second reader will check only those.

## Log and report
Write your log to `WORK/reviews/REVIEW-<job>.md` (not into BOOK), with a section `## FLAGS` (or "FLAGS: none"). Style of /home/pv/brg/code_python/Books/work/graphic-statics-henneberg/model/trefftz/REVIEW-proof-03.md:
pages proofread (list), counts of fixes by kind (text, equation, number/table, figure, marker, footnote, labels), a table of every fix (page, before → after, reason), remaining uncertainties, anything you could NOT check.
Honest and neutral ("Proofread against the scan, October 2026"). Final report to the lead ≤ 10 lines.
