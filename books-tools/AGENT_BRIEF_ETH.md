# Brief: English Markdown edition of the ETH "Structural Design" course (Block · Schwartz)

Source: ETH Zürich D-ARCH *Tragwerksentwurf / Structural Design* I–IV (+ D-BAUG/MIBS): lecture slides, exercise sheets,
the Skript (German), formula sheets. Slides are mostly **bilingual** (German line, English line in italics): use the English
line; translate German-only text yourself. The Skript, formula sheets, Lasten/Kennwerte and a few lectures are German only:
translate them completely. The user wants the result as clean, searchable **English Markdown** with **exact formulas** and
the original figures, in the same shape as the Lévy book (`graphic-statics-levy/`).

All paths below are under the scratchpad `/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/` (use absolute paths). Book folder: `/home/pv/Downloads/Books/graphic-statics-student-course/`.
You are given ONE UNIT (from `/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/units.json`): an output file name and a list of sources "DOCID first-last" (page/slide range).
Write ONLY your own file `graphic-statics-student-course/src/<file>` and your own figures. Never touch other files, README or git.

## Inputs (per DOCID)
- `work/text/DOCID.txt` — pdftotext of every page, with `===== PAGE n =====` markers. Cheap; read your range first.
  Text is reliable for words, **not** for formulas, symbols, diagram labels: check those in the images.
- Slide decks: `work/sheets/DOCID/sheet-AAA-BBB.jpg` = contact sheet of slides AAA..BBB with the slide number in red at the
  top-left of each slide. Read the sheets of your range in order. Many consecutive slides are animation builds of one diagram:
  describe the whole build in ONE section (name the steps) and keep only the key slide(s).
- Document-type PDFs (exercise sheets, Skript, formula sheets): `work/pages/DOCID/p-NNN.jpg` (110 dpi, NNN = page, zero-padded
  to the width pdftoppm used; `ls` the folder). For formulas read the image; zoom with
  `pdftoppm -f N -l N -r 220 -x X -y Y -W W -H H -jpeg "<pdf path from /tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/docs.py>" /tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/work/zoom` or re-render the page.
- Slide numbers: the PDF page index = the red number = the slide number printed in the corner. Cite that.

## Reading tips (from the pilot)
- Contact sheets are for orientation and photos only. **Diagram labels, numbers and construction steps are too small there**: for every
  diagram/construction/table/formula slide, look at the slide at full size first:
  `python3 /home/pv/Downloads/Books/tools/slidefig.py DOCID PAGE NN-view --view --w 1100` → read `.../work/view/NN-view.jpg` (the view folder is shared: ALWAYS prefix the name with your unit number, e.g. u30-view) (not published, name MUST start with your unit prefix; same call without `--view` publishes).
  For animation builds, view the first and last slide of the build at full size and describe the intermediate steps from their text/differences.
- Describe only what you see; never guess (e.g. tension vs compression from colours, load directions). If inferred, footnote "(read from the drawing)".
- Do NOT use `<sub>`/`<sup>` inside figure captions or alt text (the caption already sits in a `<sub>`); write R1-2 as plain text there.
- Slides have no real maths; do not invent formulas. Leave `[NAV]` as is.
- One bold line per build group (`**Slides 26–30 — topic.**`) followed by one `<sub>slide N</sub>` paragraph per step is the accepted pattern.

- Math builder limits: use `\leq`/`\geq` (not `\le`), `\frac` (not `\dfrac` inline); inside display blocks write units outside `\text`, e.g. `30\;\mathrm{kN}`.
- Exercise PDFs: the text layer is scrambled; read the images. Cite the **printed** page number when one exists, otherwise the PDF page. Sheet/exercise
  contents-table anchors use the GitHub slug of the heading. Blank answer forms: embed the page, say the answer areas are empty.
- Image size: line drawings may be up to ~200 KB; photos ≤ 40 KB (use `--w 700`).

- **Skript units** (German running text, landscape A4, 2–3 text columns per sheet; read column order from the image): the unit range is in *sheets*
  (PDF page index); the printed page number is in the bottom corner (front matter may be unnumbered). Use `<sub>page N · sheet M</sub>`, keep the Skript's
  own numbered headings (`## 4.1 — Cable nets`), translate every sentence, captions `Bild 4.1` → `Fig. 4.1`, formulas exactly (footnote printed errors).
  The contents table has columns Sheets | Printed pages | Topic. Figure names `NN-pXX` (printed page, `a`/`b` if two on a page). A finished example:
  `graphic-statics-student-course/src/18-skript-te-1-2-sheets-001-030.md` (read its first 100 lines). Text running on to the next sheet: stop mid-sentence
  at the unit boundary and note "continues on sheet N+1" — except finish a sentence if it ends on the next sheet's first line.

## Output format (copy exactly)
1. Header (no nav; I add prev/next later):
```
<div align="center">

# Structural Design — ETH Zürich
### <course part>, <unit title>

*Block · Schwartz · English edition of the course material* · <source kind: slides / exercise sheets / Skript> · slides|pages|sheets A–B

[NAV]

</div>

---

## Contents

| Slides | Topic |
|:-:|:--|
| 3–7 | [Topic](#slides-3-7--topic-slug) |
```
2. Then sections, one per topic (group 1–10 consecutive slides): `## Slides 3–7 — Title` (single slide: `## Slide 5 — Title`; Skript/
   exercise pages: `## Pages …`/`## Sheet …` or the Skript's own numbered headings `## 4.1 — Seilnetze`). Put `<sub>slide N</sub>`
   (or `<sub>page N</sub>`) at the start of each slide's content so every statement can be cited and checked.
3. Content: **translate/transcribe every piece of text on every slide** (titles, bullet text, labels that carry meaning, captions,
   quoted sources, credits e.g. "Alvaro Siza, Expo Pavilion, Lisbon, 1998"). Do not summarise a slide away. For image-only slides
   write one blockquote line: `> *Photo: …*` saying what is shown (building, designer, year if printed). For diagrams add a
   short factual description of what is drawn (structure, loads, labelled points, which construction step) in a blockquote
   `> *Diagram: …*`. Text and descriptions must be English only; keep German original terms in parentheses on first use
   when they are technical (e.g. "force diagram (Kräfteplan)").
4. Formulas: inline `` $`F = q\,l`$ ``, display blocks ```math … ``` (one equation per line, `\\` between; supported subset in
   `tools/AGENT_BRIEF.md` § Mathematics; no cases/array/matrix/\operatorname). Transcribe symbol for symbol from the image;
   do not modernise. If you correct an obvious misprint, footnote it ("Printed: …"). Uncertain reading → footnote "[uncertain reading]".
   Numbers in worked examples: copy exactly, with units.
5. Figures: embed a slide/page image where the diagram, table or formula layout matters (anything you could not fully capture in
   words/LaTeX: construction drawings, force/form diagrams, tables, sections). Not for pure photos, title slides or text-only slides.
   Make it: `python3 /home/pv/Downloads/Books/tools/slidefig.py DOCID PAGE NAME [--w 900] [--crop x0 y0 x1 y1]`
   → `figures/NAME.jpg`; read the output to verify. NAME = `NN-sNNN` for slides (NN = the number of the file you edit, e.g. `07-s063` for slide 63 in file 07-…), `NN-pNN` for printed pages. For an animation build keep only the final (or most informative) slide. Use `--crop` to cut
   headers/blank margins when it makes the figure clearer. ~900 px width for slides; formulas-heavy pages ~1100.
   Place right after the text it belongs to:
   `<p align="center"><img src="figures/07-s063.jpg" width="600" alt="Slide 63: <short description>"><br><sub><b>Slide 63</b> · Stiffening through prestress</sub></p>`
   Keep the number of embedded images reasonable (about 1 per 2–3 slides on average); never more than ~40 KB per photo-like image.
6. Footer: `<p align="center"><sub>End of <unit title> · <a href="README.md">Contents</a></sub></p>`, then footnotes.
7. Keep one consistent English term per technical term. Terms are in the glossary: Tragwerk=structure (load-bearing structure), Seil=cable,
   Bogen=arch, Stützlinie=thrust line, Seilpolygon/Seillinie=funicular polygon, Lageplan=form diagram, Kräfteplan=force diagram,
   Auflager=support, Fachwerk=truss, Balken=beam, Rahmen=frame, Platte/Scheibe=slab (plate action)/wall (shear panel),
   Knicken=buckling, Aussteifung=bracing/stiffening, Bemessung=dimensioning (design), Stahlbeton=reinforced concrete,
   Mauerwerk=masonry, Holz=timber, Lasteinflusszone=tributary area. Add your own new terms to your report.

## Quality bar
- Complete: every slide/page of your range appears in the file (as its own section or inside a build-group section).
- Exact: numbers, formulas, labels, credits. Never invent content; if a slide is unreadable say so in a footnote.
- Build check (formulas): `cd /home/pv/Downloads/Books && EQPNG=/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/work/eqpng python3 graphic-statics-student-course/src/build.py <file>`
  must report `unconverted: 0` and `unknown inline commands: none` (it writes the published file to the book root; that is fine).
  Look at the equation sheets it prints and compare against the page, symbol by symbol (only if you wrote display equations).

## Report back (SHORT, ≤ 25 lines)
File written; slide/page range covered; number of figures embedded; footnoted corrections/uncertain readings; unreadable pages;
10–30 symbols/terms worth putting in the course glossary (German → English); nothing else.
