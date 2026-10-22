# Brief: index material for Lévy, *Graphic Statics* (English translation)

The book is fully translated. The chapter sources are Markdown files in
`/tmp/claude-1000/-home-pv-Downloads-GraphicsStatics/87e959cb-9494-4553-897d-39560b9f2354/scratchpad/Books_repo/graphic-statics-levy/src/`
(the French scan pages are in `.../scratchpad/work/pages/pNNNN{a,b}.jpg`, if you need to check the original French term or symbol).
Figures are in `.../graphic-statics-levy/figures/`, referenced in the chapter files by `<img src="figures/NAME.png" ...>` blocks with a caption.

Your job: for YOUR chapter files only, produce index data so that Claude can later find things by search
without loading whole chapters. Do NOT edit any chapter file, README, build script or git.

Write ONE JSON file `work/index-parts/<your-group>.json` (UTF-8, valid JSON), with this shape:

```json
{
  "chapters": [
    {"file": "04-chapter-04.md", "title": "Chapter IV — …", "pages": "33–72", "sections": "§§ 32–45 bis",
     "summary": "4–8 sentences: what the chapter does, its main constructions/theorems and results, in modern engineering language, naming the key §§."}
  ],
  "symbols": [
    {"symbol": "EI", "meaning": "flexural rigidity (E Young's modulus, I second moment of area)", "where": "17-chapter-17 § 188", "notes": "optional: how it differs from modern usage"}
  ],
  "terms": [
    {"french": "effort tranchant", "english": "shear force", "modern": "shear force V", "where": "17-chapter-17 § 188"}
  ],
  "figures": [
    {"file": "fig064.png", "label": "Fig. 64", "source": "Plate XIII", "chapter": "07-chapter-07.md", "section": "§ 96 bis",
     "description": "One line, ≤ 25 words, saying what the drawing shows: structure type, loads, which construction (funicular polygon, Cremona diagram …) and key labelled points."}
  ]
}
```

Rules:
- **Figures:** list EVERY image your chapter files reference (grep `figures/` in them). Read each image file and describe what is
  actually drawn (do not guess from the caption alone). If an image is shared with another chapter, list it under the chapter
  that first shows it. Include the plate or "in the text, p. N" from the caption as `source`.
- **Symbols:** every symbol the author defines and uses (letters for forces, moments, lengths, angles, coefficients, sums,
  special notations such as `r.r+1`, `Σ_g`, `μ`, `τ`, `ϖ`). Give the meaning the way THIS author uses it, and note any clash
  with modern conventions (sign conventions, a letter used for two things, etc.). Write symbols in plain Unicode (μ, τ, Σ, x₁, h″).
- **Terms:** technical French terms with the English used in the translation and the modern engineering equivalent
  (e.g. "polygone funiculaire → funicular polygon → funicular (string) polygon / thrust line", "système réticulaire → trussed system →
  truss", "module de sécurité → working stress → allowable stress"). Only terms whose modern name differs or that need
  explaining. 15–60 per group.
- **Summaries:** accurate and specific; mention the main results and named theorems (Ritter, Culmann, Varignon, Cremona …).
- Be concise. Don't paste text from the chapters.

When done, report: the path of your JSON file and counts (chapters, symbols, terms, figures), and any image you could not read.
