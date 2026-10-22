# Structural library guide

Adapted from the user-supplied Books/CLAUDE.md (2026-10-15).
Book status and review claims belong to that source; they are not independently verified by MCP.

## Reading

- Call `get_book_guide` once per session; it includes `LIBRARY.md`.
- Search first. Read selected chapters, not whole books.
- Use INDEX for topics, GLOSSARY for notation, FIGURES for image references.
- Cite author, §, printed page/slide, and source URL. Line numbers are not printed pages.
- Cite chapter evidence, not map summaries. Preserve footnotes and uncertain readings.
- Check symbols, units, and sign conventions before comparing authors.
- Read published chapters normally; use `representation="source"` for exact LaTeX.
- Inspect figures only when relevant. Resolve relative links against the chapter URL.
- Distinguish original figures, reviewer-computed values, and added animations.
- Do not claim image inspection or independent review unless performed.

## Book conventions

- **Lévy:** “sense” differs from direction; bold force numbers differ from polygon-side numbers.
- Units include metres, tonnes, kilograms, and kg/mm². Check moment μ and shear τ signs in § 189.
- Plate/in-text figure numbers differ. Use README's corrected page references.
- **ETH:** read `GRAPHIC-STATICS-NOTATION.md` first for form/force diagrams and thrust lines.
- Cite lectures by PDF slide; Skripte by printed page/sheet; exercises by printed page.
- Exercises use red=tension, blue=compression, green=external forces. Do not infer slide colours without a legend.
- Diagram blocks describe correspondence and scale; “computed” values are reviewer-derived.
- Consult GLOSSARY for terms such as Lageplan, Kräfteplan, Scheibe, and Platte.

## Processing a new book

Run these steps in a separate, trusted local Books workspace when authoring is requested.

1. Check scan completeness, duplicates, printed numbering, and errata.
2. Split page images with `tools/split.py`; OCR every page with `tools/mistral_ocr.py` (report pages billed and
   cost); inspect formulas against images, not OCR alone. After translating, run `tools/mistral_compare.py` and check
   the mismatches with `tools/CHECK_BRIEF.md`.
3. Translate contents into README; establish chapters and page boundaries.
4. Write `src/<chapter>.md` using `tools/AGENT_BRIEF.md` or `tools/AGENT_BRIEF_ETH.md`.
5. Preserve `<sub>page N</sub>`, slide markers, `## § N`, exact formulas, and equation numbers.
6. Build with `python3 <book>/src/build.py <file>.md`; require `unconverted: 0` and no unknown inline commands.
7. Check rendered equations against scans. Independently review corrections: A=correct, B=fix, C=restore original, D=uncertain/both readings.
8. Add INDEX, GLOSSARY, and FIGURES using `tools/INDEX_BRIEF.md`; record source pages and review notes.
9. Follow `tools/ILLUSTRATION_BRIEF.md` for checked constructions.
10. Rebuild `LIBRARY.md` with `tools/library_map.py`; check with `--check`. Upload only when requested; restart MCP to refresh its cache.

## Formats and figures

- Edit `src/`, then rebuild published files. Source math uses dollar/backtick inline delimiters and fenced `math` blocks.
- Preserve letters, primes, signs, indices, and fractions. Footnote corrected misprints; retain author errors with explanation.
- Crop original figures without redrawing. Keep labels/captions; exclude neighbours.
- Names: `figNNN.png` for plates, `txt-figNNN.png` for in-text, `noteN-figNN.png` for notes.
  Lettered figures add the printed page (`note1-p297-figc.png`); no two names may differ only by letter case.
- Every figure of a structural system carries `[labels: …]` in its alt text (cables, arches, vaults and shells,
  truss, beam, frames, plates or slabs, columns, bracing, material-specific forms, plastic and stress field models,
  connections, graphic statics).
- Contents links use GitHub heading anchors: `## § 634 — Title` → `#-634--title`.
- Figures printed on plates of a separate atlas get a note where they are cited; list the plates as missing.
- ETH figure crops contain drawings only; titles, tasks, and prose stay in Markdown.
- Add one labelled animation after each original figure; track it in `constructions/PLAN.md`.
- Validate geometry and numerical results before rendering with `tools/construction.py`; inspect output and rebuild.
- Added-construction colours: compression #1a1eb2, tension #ce4095, external forces #3f9c20, guides #aaaaaa.
- Use Lévy Chapter I and `constructions/make_ch01.py` as the model.

## Actual capabilities

- MCP: public Markdown retrieval, chapter-summary keyword search, source URLs, and bounded text pagination.
- If truncated, request fewer lines. Use the source URL for a line too long to fit.
- MCP does not run conversion, image inspection, embeddings, uploads, or git operations.
- Books' local `tools/search.py` supports keyword/hybrid/figure search; hybrid requires its embedding index.
- `tools/embed.py` builds the optional local index. This is separate from MCP.
- Do not promise token prices, caching discounts, review status, or unimplemented search features.
