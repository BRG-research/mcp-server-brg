# Brief: English translation of Lévy, *La Statique graphique* (1886), Part I

You are translating part of Maurice Lévy, *La Statique graphique et ses applications aux constructions*,
2nd ed., Part I (Paris, Gauthier-Villars, 1886) from French into English. The book is public domain;
the scans belong to the user. The user wants **extra care that formulas and figures are exactly right**.

All paths below are relative to the scratchpad
`/tmp/claude-1000/-home-pv-Downloads-GraphicsStatics/87e959cb-9494-4553-897d-39560b9f2354/scratchpad/`.
Always use absolute paths in commands.

## Inputs

- `work/pages/pNNNNa.jpg` and `pNNNNb.jpg` — top and bottom half (with overlap) of printed page NNNN
  (e.g. `p0040a.jpg`). Read BOTH halves of every page in your range, in order. If a line is hard to
  read, zoom: `python3 work/figtool.py zoom p0040a x0 y0 x1 y1` and Read the printed file.
  Front matter (00-preface, errata) is in `work/pages/scanNNN{L,R}{a,b}.jpg`.
- `work/plates/PlNN.jpg` — the 26 fold-out plates (NN = 01..26 = Plates I..XXVI). Text references look
  like "(fig. 45, Pl. VII)". Plate XVII (`Pl17`) is scanned sideways (use `--rot 90` or `--rot -90`).
- **The model to copy exactly**: `Books_repo/graphic-statics-levy/src/01-chapter-01.md` (Chapter I, done).
  Read it fully first: header block, § contents table with anchors, `## § N — Title` headings,
  `<sub>page N</sub>` markers, figure blocks, remarks as `>` quotes, theorems as bold-italic quotes,
  footnotes, translator's notes. Match its style, register and conventions.

## Output

One Markdown source file per chapter (or note) in `Books_repo/graphic-statics-levy/src/`, named:
`02-chapter-02.md`, `03-chapter-03.md`, `04-chapter-04.md` … `11-chapter-11.md`, `12-chapter-12.md` … `22-chapter-22.md`,
`23-chapter-23.md` … `25-chapter-25.md`, `26-note-1.md`, `27-note-2.md`, `28-note-3.md`, `29-note-3bis.md`, `30-note-4.md`, `31-note-5.md`,
`00-preface.md`. Write ONLY your own files. Do not edit README.md, build.py, other chapters, or git.

Each file: header block like Chapter I (title, "Chapter N — <English title>", printed page range,
`[← Table of contents](README.md)`), then the § contents table, then the text, then
`<p align="center"><sub>End of Chapter N · <a href="README.md">Table of contents</a></sub></p>`,
then translator's notes / footnotes. Translate **every** sentence — no summarising, no omissions.
Keep the author's footnotes (as `[^name]` footnotes marked "Author's footnote:").

## Mathematics — the critical part

- Inline math: `` $`...`$ ``. Display math: a fenced block ```` ```math ```` … ```` ``` ````.
  The build script converts these: inline → HTML text, display → rendered image (matplotlib mathtext).
- Transcribe every formula **symbol for symbol** from the scan: same letters, case, primes,
  subscripts, superscripts, signs, fraction structure, equation numbers like (1), (2), (A).
  Do not "modernise" notation. Do not silently fix misprints: if you are sure the print is wrong,
  write the corrected form and add a footnote quoting what the scan shows (see `[^ox3]` in Chapter I).
  If you cannot read something, zoom first; if still unsure, keep your best reading and footnote it
  with "[uncertain reading]".
- Inline subset that converts correctly: letters, digits, `_ ^ { }`, `\frac \tfrac \sqrt \overline \times
  \cdot \pm \leq \geq \neq \approx \infty \int \sum \partial \dots \cdots`, Greek letters, `\sin \cos
  \tan \log \text{..}`, `\quad \qquad \; \,`, `\left( \right)`, primes `'`.
- Display blocks: one equation per line; separate lines with `\\`. Multi-line systems: use
  `\begin{aligned} ... \end{aligned}` with `&` and `\\` (the `&` are dropped, lines centred), optional
  `\tag{1}`. NOT supported by mathtext: `cases`, `array`, `matrix`, `\operatorname`, `\dfrac` is fine,
  `\text` is converted to `\mathrm`. Keep each display line reasonably short (wrap long ones with `\\`).
- Long formulas belong in display blocks; short symbols in running text inline.

## Figures — the other critical part

- Every figure the text refers to must appear, cropped, **right after the paragraph that first cites
  it**, in the same block format as Chapter I:
  ```
  <p align="center">
    <img src="figures/fig045.png" width="420" alt="Fig. 45"><br>
    <sub><b>Fig. 45</b> · Plate VII</sub>
  </p>
  ```
  Width 300–650 depending on the figure. If a figure is cited again later, refer to it in words only.
- Find it: `python3 work/figtool.py grid NN` → Read `work/grid/NN.jpg` (plate with a 0.05 grid,
  red = x, blue = y). Locate the figure's label "Fig. 45 (§ …)" and its full extent.
  Zoom with `figtool.py zoom` for precise edges.
- Crop: `python3 work/figtool.py crop NN x0 y0 x1 y1 fig045 [--white x0,y0,x1,y1 ...] [--rot DEG]`
  writes `figures/fig045.png` (background cleaned to white) and a preview `work/grid/check_fig045.png`.
  **Read the preview every time.** It must contain the whole figure — all lines, every letter label,
  and the "Fig. N" caption — and nothing from neighbouring figures (blank those out with `--white`
  boxes, coordinates in full-plate fractions). Iterate until clean.
- File names: `figNNN.png` with 3 digits (fig013, fig105); variants `fig045bis.png`, `fig045a.png`.
  Figures 1–12 already exist — do not overwrite them. If the Notes number their figures separately,
  use `27-note-2-fig03.png` etc. Figures printed inside a text page: crop from the page image
  (`figtool.py crop p0123a ...`).
- If several figures share one plate cluster under one number (e.g. two parts both labelled Fig. 4),
  crop them together.

## Build and verify (mandatory)

1. `python3 Books_repo/graphic-statics-levy/src/build.py <yourfile>.md` (from the scratchpad dir, with
   absolute path). It must report `unconverted: 0` and `unknown inline commands: none`; fix anything
   else. A mathtext error means a display formula uses unsupported syntax — rewrite it.
2. Read every `work/eqpng/sheet-<yourfile>-NN.png` it prints and compare each rendered equation
   against the scan, symbol by symbol. Fix and rebuild until they match.
3. Check every figure preview again, and that every "fig. N" mentioned in your text has an image
   (or, for a repeated citation, a figure shown earlier).

## Report back (short)

For each file: chapter/note, printed pages covered, § range, figure numbers placed, and a list of
every misprint correction or uncertain reading you footnoted (page + what the scan shows). Also report
any page that was unreadable or missing in the scan, and any figure you could not find.
