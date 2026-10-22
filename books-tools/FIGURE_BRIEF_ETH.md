# Brief: figure-only crops and structured diagram descriptions (ETH course edition)

Goal (as in the Lévy book): the book shows **only the relevant figure**, cropped out of its slide/page; **all text everywhere else is Markdown**.
And every diagram is described so that a future Claude who reads only the Markdown understands it — above all the graphic-statics
diagrams (form diagram / force diagram and their reciprocal correspondence, in the course's own notation).
Read first: `/home/pv/Downloads/Books/graphic-statics-student-course/GRAPHIC-STATICS-NOTATION.md` (notation, constructions, the Diagram-block schema, worked examples),
`tools/AGENT_BRIEF_ETH.md` (formats), the glossary. Book folder: `/home/pv/Downloads/Books/graphic-statics-student-course/`; scratchpad `/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/`.
You get a list of files (by file number NN = "pos" in `/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/units.json`). Edit ONLY `src/<file>` of your files and figures named `NN-…`.
Per-file manifest of the current figures with candidate source documents/pages: `/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/work/fig-manifest/NN.json`.

## Tool
`python3 /home/pv/Downloads/Books/tools/figcrop.py DOCID PAGE NAME [--auto] [--prose N] [--split] [--crop x0 y0 x1 y1] [--white x0,y0,x1,y1 ...]`
renders PDF page PAGE (= slide number; for Skript/handouts the PDF sheet/page) of DOCID (ids in `/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/docs.py`, also the folder names under `/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/work/text`), removes text and
writes `figures/NAME.jpg`. **Read the output file every time.** `--auto` removes title/slide-number/caption lines in the header and footer bands and trims to the drawing;
`--prose 5` also blanks every text line of ≥5 words (body text, captions, task text) so a Skript/handout page shrinks to its figures; `--split` writes one image per vertical band of ink
(NAME, NAME-2, …: then reference each); `--crop`/`--white` (fractions of the page) are for manual control (e.g. keep the diagram, cut a fully transcribed table or a neighbouring figure). It prints the removed text lines:
**every removed line that carries content (loads, scales, labels, task text, captions) must be present in the Markdown** (add it if not). Keep NAME identical to the existing figure so references stay valid
(slides `NN-sNNN`, deck B `NN-bNNN`, pages `NN-pNN`); extra crops of one slide: `NN-sNNN-2`, new figures for slides that had none: `NN-sNNN`.

Tool notes (from the pilots): text removal keeps text lines that overlap a drawing or image (figure labels) and removes header/footer lines, page numbers and (with --prose) body text/captions outside figures.
`--grid` writes a full-page preview with a 0.05 coordinate grid to `/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/work/view/NAME-grid.jpg` (Read it, then pass fractions to --crop/--white). `--split` never overwrites an existing `NAME-k` unless --force and skips thin
footer strips; delete leftover strips yourself. Skript sheets are landscape A4 pages with 2–3 text columns; the `<sub>page N · sheet M</sub>` marker above a figure gives PDF page M (sheet = page index). Dense graphic-statics figures need to stay legible: use the width hint, or up to 760.
Never leave a figure whose labels or arrows are cut off; view every output.

Tool updates (use as is): text lines are split at wide gaps so a figure label next to prose is kept; `--crop` now trims blank margins itself (`--notrim` to keep exact); `--lines` lists every text line with its box; short prose fragments (<5 words) and heading numerals need `--white` boxes; vector-drawn text that is not in the text layer must be blanked with `--white` pixel fractions.
Rules added after the first pilots:
- **Builds:** keep the finished state plus any intermediate step that adds a new element or changes the meaning; describe the other steps in the Diagram block text of the kept figure ("steps 26–30: …"). One slide repeated from another file: no second crop, refer to the earlier figure by file number and name.
- **What stays in a crop:** everything drawn: members, arrows, hatching, dimension values, point labels, load values printed next to arrows, a drawn scale bar. What goes to Markdown: slide titles, slide numbers, bullet text, legends/tables written beside the drawing, captions under it ("Form diagram 1:100" → into the Diagram block's scale), formulas typed next to it. `--auto` handles header/footer bands; bullets, legend text, formula text and tables beside a drawing need your own `--white` boxes (use `--lines` to list every text line with its box).
- Read the notation primer in two parts (it is long): `offset`/`limit` 1–300 and 300–600.

## Per figure (every figure in your files, and every diagram slide that lacks one)
1. Find the source page: slide figures: page = the number in the name (deck from the manifest candidates / the section it sits in). Skript/handout figures: the `<sub>page N · sheet M</sub>` marker just above gives the PDF sheet M;
   exercise sheets: the section heading names the sheet, its PDF is in `/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/docs.py` (one page per sheet; EX handouts have 3–4 pages).
2. Re-crop with figcrop. The result must contain the whole drawing with its in-drawing labels (letters, numbers, arrows, dimension values) and nothing else: no slide title, no slide number, no body text, no caption lines
   that the Markdown already carries, no neighbouring figure. A transcribed table must not be left in the image unless the layout itself matters. Photos: crop to the picture, no caption text.
3. Decide keep/drop/add: keep drawings, diagrams, plans, sections, detail drawings, charts, construction builds (one crop per informative step, as before); drop images of pure text/tables that are fully transcribed; drop duplicates of a build;
   **add** a crop for every slide/page with a structural drawing or graphic-statics diagram that has none yet (not for title slides, dividers, pure photos).
4. Update the `<img>` block: same format as now, `width=` from the tool's "use width" hint (260–680), alt text without `<sub>`/`<sup>`, caption `<sub><b>Slide N</b> · …</sub>`.
5. Rewrite the blockquote description after the figure in the **Diagram schema** (see the primer §4). Include only the lines that apply:
   `> **Diagram** — type: form | force | form + force (reciprocal) | construction step k/n | structure | plan | section | detail | chart; scale: form 1:100, force 1 cm ≙ 1 kN`
   `> **Form diagram (Lageplan):** geometry, supports, loads with values/directions, labelled points`
   `> **Force diagram (Kräfteplan):** load line order and directions, pole, rays, polygon, closure`
   `> **Correspondence (form ↔ force):** each form-diagram member/ray/node ↔ the parallel force-diagram segment/polygon, with the value read off (table when ≥3 pairs)`
   `> **Result:** the values and what the slide demonstrates`  `> **Colours:** as drawn; tension/compression only if the slide or the exercise rule says so`
   For graphic-statics slides this is the priority: name every label as printed (Roman numerals at nodes, Arabic numerals on members, A/B reactions, F/G/Q loads, pole, rays), state which force-diagram line is parallel to which member, check
   closure and equilibrium numerically from the printed values (report mismatches as footnotes, do not alter printed numbers), and for a build give what THIS step adds. Keep every fact the review established; improve precision only from the image.
   Describe only what you see; if something cannot be read, say so.
6. Keep all other text; the Markdown must still contain every printed word of the slide (compare with `/tmp/claude-1000/-home-pv-Downloads-Books/0714b247-5d6c-4317-be13-b8277f0cf3fd/scratchpad/work/text/DOCID.txt`).

## Build and report
After editing run `cd /home/pv/Downloads/Books && EQPNG=/tmp/eqpng python3 graphic-statics-student-course/src/build.py <file>` (must say `unconverted: 0 | unknown inline commands: none`) and check
that every `figures/…` you reference exists and that figures you no longer reference are deleted (`ls figures/NN-*`). Report (≤ 12 lines): files, figures re-cropped / added / dropped, diagram blocks rewritten (how many graphic-statics),
text that had to be added to the Markdown, anything unresolved.
