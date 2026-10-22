# Brief — translate one part of Föppl, *Vorlesungen über technische Mechanik*, Zweiter Band: *Graphische Statik* (5th ed., 1920), into English Markdown

WORK = /home/pv/brg/code_python/Books/work/graphic-statics-foeppl · TOOLS = /home/pv/brg/code_python/Books/tools
BOOK = WORK/out/graphic-statics-foeppl (sources in BOOK/src/, figures in BOOK/figures/)

Work only inside WORK. Use `/usr/bin/python3 -I` for Python. Put ALL your temp files (zooms, scripts) in WORK/tools-<yourjob>/ and never
delete or edit files outside it except your own source file in BOOK/src/ and your own figures in BOOK/figures/. Absolute paths always.
Never edit another job's file. Never write anything about AI, models, Claude, agents or "OCR draft" provenance beyond what this brief says into any published file.

## The book
August Föppl, *Vorlesungen über technische Mechanik*, Zweiter Band: *Graphische Statik*, fünfte Auflage, mit 209 Abbildungen im Text (Dr. phil. Dr.-Ing. Aug. Föppl,
Prof. a. d. Techn. Hochschule in München). Leipzig und Berlin: B. G. Teubner, 1920. English title: *Lectures on Engineering Mechanics, Vol. II: Graphic Statics (5th edition)*.
German, Antiqua/Fraktur forces. Read WORK/PROCESSING.md and **WORK/SECTIONS.md for the fixed English chapter and § titles** — use them exactly (headings
and contents tables) so parallel jobs produce matching anchors. If the printed heading differs from the contents wording, keep the SECTIONS.md English title and
quote the printed German heading in the `*Original title: « … ».*` line. Chapters = the book's seven Abschnitte (Erster … Siebenter Abschnitt).

**All output text is English.** Translate every sentence faithfully; no summarising, nothing added, nothing left out. This includes footnotes, figure captions
(Abb. → Fig.), table headings, problems, and any Latin/French quotations (give the original in a footnote only if the wording matters). Keep original German titles in
italics beside the English ones (chapter/§ titles). Give German terms only as companions where useful (first use of a key term: "funicular polygon (*Seileck*)").

## Inputs (find pages by PRINTED page number — duplicates already removed; page N = pN, front matter fIII…fXII)
- Page images: `WORK/work/fpp/pages/pNNNN.jpg` (p0001 … p0404), 1464 x 2192 px, one printed page each.
- OCR draft (tesseract deu): `WORK/work/fpp/ocr/pNNNN.txt`. **Use the OCR text as your source of the German wording** and fix it with your reading; it is
  reliable for plain prose and unreliable for formulas, Fraktur letters, Greek letters, fractions, sub/superscripts, primes, numbers, tables and figure lettering.
  COST RULE: do not Read whole page images. Look at the image only through small zooms of equations, tables, figure labels and doubtful words (each zone once).
- Zoom: `BOOKS_WORK=WORK/work /usr/bin/python3 -I TOOLS/pagetool.py zoom fpp p0123 x0 y0 x1 y1 WORK/tools-<job>/z1.jpg` (fractions of the page image, grid every 0.05), then Read it.
- Crop a figure: `BOOKS_WORK=WORK/work /usr/bin/python3 -I TOOLS/pagetool.py crop fpp p0123 x0 y0 x1 y1 BOOK fig034a [--white x0,y0,x1,y1] [--rot 90]`
  → BOOK/figures/fig034a.png and a preview BOOK/.checks/check_fig034a.png. Read the preview EVERY time: the whole figure with all its letters, nothing of the neighbouring
  text, and the printed caption ("Abb. 34a.") left OUT of the crop (it goes into the Markdown caption). Use `--white` to blank intruding text lines.

## Model to copy
`/home/pv/brg/code_python/Books/work/graphic-statics-henneberg/model/trefftz/src/02-chapter-02.md` (header, contents table, page markers, footnotes, figure blocks; first 150 lines are enough).

## Output
Your file(s) in BOOK/src/ with exactly the names given in your task (e.g. `03-chapter-03.md`; continuation files `03-chapter-03-partB.md`, `…-partC.md`, …).
- Header block (first file of a chapter only):
  ```
  <div align="center">

  # Lectures on Engineering Mechanics, Vol. II: Graphic Statics

  *Vorlesungen über technische Mechanik, Zweiter Band: Graphische Statik*

  **August Föppl**

  *Fifth edition (fünfte Auflage), with 209 figures in the text (mit 209 Abbildungen im Text) · Leipzig und Berlin, B. G. Teubner, 1920*

  English translation · Chapter N · printed pages a–b

  [← Previous](PREV.md) · [Contents](README.md) · [Next →](NEXT.md)

  </div>

  ---

  ## Contents

  **Chapter N — English title**
  *Erster Abschnitt — Deutscher Titel*

  | § | Topic | Page |
  |:-:|:--|:-:|
  | 2 | [English § title](#-2--english--title-slug) | 5 |

  ---
  ```
  Then `<sub>page a</sub>`, `# Chapter N — Title` + italic German title, and `## § N — Title` + `*Original title: « … ».*` for every §. The chapter's problem block gets
  `## Problems 1–10 (*Aufgaben 1–10*)` and `### Problem N` / `**Solution.**`. Unnumbered printed sub-headings (Föppl's margin or italic headings) become `### English (*German*)`.
- Continuation files (`…-partB.md` …): no header block and no contents table; start directly with `<sub>page N</sub>`. The first-file job lists ALL §§ of the chapter (incl. those in later parts)
  in its contents table, linking `#-N--slug` (parts are merged later). Chapter 1's job T01 lists all of chapter 1 etc.
- `<sub>page N</sub>` on its own line where each printed page starts (split a paragraph if needed). A page shared by two jobs appears in both; each translates only its own range.
- Math: inline `` $`...`$ ``, display in ```` ```math ```` blocks, symbol for symbol, with printed equation numbers (`\tag{12}`); Föppl numbers equations in running series (1), (2) … per chapter or §;
  copy what is printed. Supported: letters, digits, `_ ^ { }`, `\frac \sqrt \overline \times \div \cdot \pm \leq \geq \neq \approx \infty \int \sum \partial \dots`, Greek, `\sin \cos \tan \cot \log`,
  `\text{..}`, spaces, primes, `\begin{aligned}…\end{aligned}`, `\mathfrak{P}` in display math only. NOT supported: `\phantom \textit \displaystyle cases array matrix \operatorname`, `\text` inside `\tag`,
  nested braces in `\tag`, inline `\mathfrak` (use Unicode 𝔓 𝔖 ℜ …). Do not use `\left( \right)` (stray glyphs); use plain brackets. Determinants/matrices: Markdown table or aligned rows with a footnote.
  **Fraktur:** Föppl prints forces (vectors with magnitude, direction and line of action) in Fraktur letters (𝔓, 𝔖, 𝔎, 𝔗, ℜ, …) and the magnitude in italic Latin; keep that distinction.
- Tables: Markdown, every cell from the image. Decimal POINTS in numbers (3.5, not 3,5).
- Figures: numbered Abb. 1 … 209 in the text (some lettered 34a, 34b). Crop every figure on your pages, place after the paragraph that cites it (or where it sits in the page flow). Names `figNNN.png`
  (3 digits; "Abb. 34a" → `fig034a.png`; several sub-figures on one block cropped together → `fig034a-b.png`; "Abb. 206 bis 209" → `fig206-209.png`). Block:
  ```
  <p align="center">
    <img src="figures/fig034a.png" width="480" alt="Fig. 34a — one-line description of what is drawn [labels: truss, graphic statics]"><br>
    <sub><b>Fig. 34a</b> · translated caption</sub>
  </p>
  ```
  width 300–620 by size. Figures printed sideways: crop and rotate upright (`--rot`), alt text says "printed sideways".
- **Structural labels (required):** every figure showing a structural system gets `[labels: …]` in its alt text, from: cables, arches, vaults and shells, truss, beam, frames, plates or slabs,
  columns, bracing, material-specific forms, plastic and stress field models, connections, graphic statics — plus specific tags where they apply: force diagram, funicular polygon, reciprocal figure,
  Cremona diagram, displacement diagram, influence line, moment diagram, space truss, dome, null system, catenary, three-hinged arch. Several allowed; pure geometry that is a statics construction gets `[labels: graphic statics]`.
- Author misprints: keep as printed + footnote "As printed: … ; … is meant." Unclear: best reading + footnote ending "[uncertain reading]". Own notes start "Translator's note:". Footnote names page-based and
  unique across the book: prefix with the chapter number, e.g. `[^c03-p123a]`; the author's own footnotes `[^c03-fn-p123-1]`.

## Terminology (use consistently; companions sparingly)
force diagram (Kräfteplan) · space diagram / layout (Lageplan) · reciprocal force diagram (reziproker Kräfteplan) · funicular polygon (Seileck) · funicular curve (Seilkurve) · pole (Pol) · pole ray (Polstrahl) ·
closing line (Schlußlinie) · resultant (Resultierende, Mittelkraft) · line of action (Richtungslinie, Wirkungslinie) · couple (Kräftepaar) · moment vector (Momentenvektor) · force cross (Kraftkreuz — Föppl's reduction
of a force group to two skew forces; footnote the term at first use) · null system (Nullsystem) · skew forces (windschiefe Kräfte) · central axis (Zentralachse) · truss (Fachwerk) · roof truss (Dachbinder) · truss girder (Fachwerkträger) ·
bar (Stab) · bar force (Stabspannung) · joint (Knotenpunkt; Gelenk = hinge/joint as the text requires) · basic figure (Grundfigur) · bar substitution (Stabvertauschung) · substitute bar (Ersatzstab) · imaginary joint (imaginäres Gelenk) ·
exceptional case / exceptional truss (Ausnahmefall / Ausnahmefachwerk) · braced network (Flechtwerk) · network dome (Netzwerkkuppel) · Schwedler dome (Schwedlersche Kuppel) · barrel braced-network roof (Tonnenflechtwerkdach) ·
statically indeterminate (statisch unbestimmt) · redundant bar (überzähliger Stab) · main system (Hauptnetz) · displacement diagram (Verschiebungsplan) · reciprocity of displacements (Gegenseitigkeit der Verschiebungen) ·
temperature stresses (Temperaturspannungen) · erection stresses (Montierungsspannungen) · influence line (Einflußlinie) · moment diagram (Momentenfläche) · loading diagram (Belastungsfläche) · indirect loading (mittelbare Belastung) ·
Gerber cantilever girder (Gerberscher Kragträger) · three-hinged arch (Dreigelenkbogen) · continuous girder (durchlaufender Träger) · equation of three moments (Gleichung der drei Momente) · support, support condition (Auflager, Auflagerbedingung) ·
elastic line (elastische Linie) · moment of inertia (Trägheitsmoment) · barrel vault (Tonnengewölbe) · line of resistance (Stützlinie) · pressure line (Drucklinie) · edge pressure (Kantenpressung) · springing / joint of the vault (Fuge) ·
catenary (Kettenlinie) · wire rope (Drahtseil) · telegraph wire (Telegraphendraht) · method of moments (Momentenverfahren, Momentenmethode) · trestle frame (Bockgerüst) · crane framework (Krangerüst) · derrick crane (Derrickkran) ·
Wiegmann truss / Polonceau truss (Wiegmannbinder / Polonceau-Binder). Personal names are printed normally (Culmann, Müller-Breslau, Bow, Henneberg, Maxwell, Mohr, Schwedler, Zimmermann, Clapeyron, Winkler, Moseley).
Keep the author's letters and symbols exactly. In §§ with units: m, t, kg, cm² … as printed.

## Build and check (mandatory)
`/usr/bin/python3 -I BOOK/src/build.py <abs path of your src file>` → must report `unconverted: 0` and `unknown inline commands: none`. Read every equation preview sheet it prints
(`BOOK/.eqpng/sheet-<stem>-NN.png`) and compare each equation with a zoom of the page. Check every `figures/` link exists. Then run the cheap automatic check:
`/usr/bin/python3 -I WORK/tools-lead/autocheck.py BOOK/src/<file> FROM TO` (lists numbers, equation, figure and § numbers present in the OCR but missing from your translation, missing page markers, footnote problems) and resolve every item (most are OCR noise; some are real omissions).

## Job boundaries
- An author's footnote that starts on the LAST page of your range and runs over: translate it completely (read the next page's foot). A footnote continuation at the foot of the FIRST page of your range belongs to the previous job: skip it.
- Printer's signature marks at the page foot (e.g. "Föppl, Graph. Statik. 12*") are not reproduced.
- If a figure runs into the binding gutter or off the scan: crop what is visible and footnote what is hidden.

## Report (final message, ≤ 12 lines)
Pages covered, § range, figures cropped (numbers; how many labelled), every correction/uncertain reading footnoted, where your range really ends (page/§), anything not checked. Also append the same lines to WORK/jobs/<yourjob>.md.
- Never write `$$` after inline math (inline math is $`...`$ exactly). Problem blocks: heading `## Problems N–M (*Aufgaben N–M*)` exactly (slug `problems-nm-aufgaben-nm`) — first problem page per SECTIONS.md (p. 45, 101, 152, 219, 288, 341, 394).
