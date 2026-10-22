# Brief — translate one chapter of a scanned book into English Markdown

> Reusable brief (October 2026). WORK = the processing folder (default `<Books>/work`, or a session scratch folder); tools are in `<Books>/tools/`. Replace the placeholders, copy the brief next to the work, and add a row for the book to the table.

Work only inside WORK. Use `/usr/bin/python3 -I` for Python. Put ALL your temp files (zooms, scripts) in WORK/tools-<yourjob>/ and never
delete files outside it. Absolute paths always.

## Books
| key | out dir | book | source language |
|---|---|---|---|
| levy4 | WORK/out/graphic-statics-levy-part-4 | Maurice Lévy, *La Statique graphique et ses applications aux constructions*, 2nd ed., **Part IV** (IVᵉ partie): *Ouvrages en maçonnerie. Systèmes réticulaires à lignes surabondantes. Index alphabétique des matières contenues dans les quatre parties.* Texte. Paris, Gauthier-Villars, 1888 | French |
| levy3 | WORK/out/graphic-statics-levy-part-3 | Maurice Lévy, *La Statique graphique et ses applications aux constructions*, 2nd ed., **Part III** (IIIᵉ partie): *Arcs. Ponts suspendus. Corps de révolution.* Texte. Paris, Gauthier-Villars, 1887 | French |
| faust | WORK/out_private/faustformel-tragwerksentwurf | Philippe Block, Christoph Gengnagel, Stefan Peters, *Faustformel Tragwerksentwurf* (expanded and updated edition), Deutsche Verlags-Anstalt (DVA) | German |

**All output text is English** (translate every sentence faithfully; no summarising, nothing added). Keep original titles in italics beside the
English ones (chapter/section titles, book title). Never write anything about AI, models, Claude or agents in any file.

## Inputs
- Page images: `WORK/work/<key>/pages/sNNNL.jpg`, `sNNNR.jpg` (left/right page of spread NNN). Locate pages by the printed page number in the header
  (levy3: P ≈ s{(P+12)//2} early in the book, s{(P+14)//2} from about p. 180; levy4: P ≈ s{(P+14)//2}, even P on L, odd P on R; faust: read the page numbers).
- OCR draft text (tesseract): `WORK/work/<key>/ocr/sNNNL.txt` — a cheap DRAFT of the wording. Use it to speed up reading, but verify against the
  page image. OCR is unreliable for formulas, Greek letters, fractions, sub/superscripts, numbers and tables — always take those from the image.
- Zoom: `/usr/bin/python3 -I <Books>/tools/pagetool.py zoom <key> <page> x0 y0 x1 y1 WORK/tools-<yourjob>/z1.jpg` (fractions of the page image; Read it).
- Crop a figure: levy3/levy4 (black on paper, whitened): `/usr/bin/python3 -I <Books>/tools/pagetool.py crop <key> <page> x0 y0 x1 y1 <out dir> <name> [--white x0,y0,x1,y1] [--rot 90]`;
  faust (colour figures, keep colour): `... crop WORK/work/faust/pages <page>.jpg x0 y0 x1 y1 <out dir> <name>`. Read the printed preview every time.

## Output
`<out dir>/src/<NN>-<slug>.md` (name given in your task). Model to copy (structure, header, contents table, footnotes, figure blocks):
`WORK/out/graphic-statics-levy-part-3/src/03-chapter-03.md` — read it first (and use Part III's terminology: mean fibre, elastic force, pressure polygon, line of thrust, closing line, surcharge, polar distance; *rotule* = ball joint, *tourillon* = pivot; decimal POINTS in text, tables and math; figures go to <out dir>/figures/, never src/figures). Conventions:
- Header block: English book title + original title in italics, author(s), edition/imprint, "English translation · Chapter N · printed pages a–b",
  nav links `[← Previous](...) · [Contents](README.md) · [Next →](...)`, then a contents table of the chapter's §§ / sections with page numbers.
- `<sub>page N</sub>` on its own line where each printed page starts (split a paragraph if needed). Headings `## § N — Title` (Lévy) or the book's own
  section headings (Faustformel).
- Math: inline `` $`...`$ ``, display in ```` ```math ```` blocks, symbol for symbol with equation numbers (`\tag{12}`). Supported by build.py:
  letters, digits, `_ ^ { }`, `\frac \tfrac \sqrt \overline \times \div \cdot \pm \leq \geq \neq \approx \infty \int \sum \partial \dots`, Greek, `\sin \cos \tan \log`,
  `\text{..}`, spaces, `\left( \right)`, primes, `\begin{aligned}…\end{aligned}`. NOT supported: `\phantom \textit \displaystyle cases array matrix \operatorname`,
  `\text` inside `\tag`, inline `\mathfrak` (use Unicode 𝔐).
- Tables: Markdown tables, every cell from the image. (Faustformel has many design tables and charts: tables as Markdown, charts as figures.)
- Figures: crop every figure; place after the paragraph that cites it (Faustformel: where it sits in the page flow):
  ```
  <p align="center">
    <img src="figures/<name>.png" width="520" alt="Fig. N — one-line description [labels: truss, beam]"><br>
    <sub><b>Fig. N</b> · translated caption</sub>
  </p>
  ```
  Names: levy3 `fig NNN` as printed (`fig123.png`, `fig123bis.png`); faust `<NN>-p<page>-<k>.png` (NN = file number). Figures cited on plates
  ("Pl. XXXIII …") are NOT in the scan: add a short note where they belong ("Fig. N is on Plate X of the separate atlas, not in this scan").
- **Structural labels (required):** every figure showing a structural system gets `[labels: …]` in its alt text, chosen from: cables, arches, vaults and
  shells, truss, beam, frames, plates or slabs, columns, bracing, material-specific forms, plastic and stress field models, connections, graphic statics
  (several allowed; based on what the drawing shows).
- Author misprints: keep as printed + footnote "As printed: … ; … is meant". Unclear: best reading + `[uncertain reading]` footnote. Footnotes `[^name]`.

## Build and check (mandatory)
`/usr/bin/python3 -I <out dir>/src/build.py <abs path of your src file>` → must report `unconverted: 0` and `unknown inline commands: none`.
Read every equation preview sheet it prints and compare each equation with the page image. Check every `figures/` link exists.
(Continuation files `…-partB.md`: no header/contents table; start with the `<sub>page N</sub>` marker; build them too.)

## Report (final message, ≤ 15 lines)
Pages covered, §/section range, figures (with labels count), every correction/uncertain reading footnoted, plates/figures not in the scan, anything not checked.

## Lessons from Lévy III/IV and Faustformel (October 2026)
- `pagetool.py crop` takes the BOOK folder, not `figures/` (it adds `figures/` itself).
- Figure names must stay unique when letter case is ignored (Mac/Windows): lettered figures of a note get the printed page,
  e.g. `note1-p297-figc.png`, `note1-p275-figC.png`.
- Contents-table anchors follow GitHub: `## § 634 — Title` → `#-634--title` (leading hyphen). Run `tools/fix_anchors.py <book>` after merging.
- Continuation files (`…-partB.md`) are merged with `tools/merge_parts.py`; before merging make footnote names unique across the parts
  and point links to the part files at the merged file.
- Chapter boundaries in a brief are estimates: check the running heads and § numbers and report where the chapter really ends.
- `\tag{}` cannot hold nested braces; tall `\right)` may render as "!" in the equation previews (use square brackets, footnoted).
- After all parts are in: one consistency pass over terminology (keep a term table), notation (e.g. ϖ → π) and the shared title line.
