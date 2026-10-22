# Check the English translation of flagged pages against the source

Brief for one job made by `tools/mistral_textcheck.py --jobs` (≤ 12 printed pages). Each page was flagged because
the English word or paragraph count departs from the source (German or French). Your job: compare our English page
with the source page sentence by sentence and find real translation errors.

## Inputs per page

- **Source text:** the OCR file given (Mistral Markdown of the printed page, original language). It contains the
  running head, footnotes and figure captions of the page. OCR can misread single words; if a source sentence looks
  wrong or a passage is doubtful, zoom into the scan:

      python3 -I tools/pagetool.py zoom /ABS/DIR/pages pNNNN.jpg x0 y0 x1 y1 /ABS/DIR/zoom/<job>_<page>_<k>.jpg

  (fractions 0–1 of the page; then Read the jpg). Never read whole pages in bulk.
- **Our English:** the given src file(s); the page runs from `<sub>page N</sub>` to the next page marker. Footnote
  definitions (`[^id]: …`) are at the end of the file; "Author's footnote" = printed footnote, "Translator's note" =
  ours (not in the source, never an error by itself). A sentence may start on the previous page in one text and on this
  page in the other — check the neighbouring page boundary before calling something missing.

## What counts as an error

- **Omission:** a source sentence, clause, list item, footnote or table row has no English counterpart.
- **Addition:** English content with no source counterpart that is not marked as a translator's note or [bracket].
- **Mistranslation:** meaning changed — negation lost or added, wrong quantifier (all/some, always/sometimes),
  wrong relation (parallel/perpendicular, tension/compression, left/right, greater/smaller), wrong technical term,
  wrong reference (§, Fig., equation, page).
- Not errors: free word order, idiomatic rendering, split or merged sentences, English that is stiff but correct,
  differences only in formulas or numbers (checked separately).

## Verdicts (one per page; list each error found)

    - [PAGE] OK — (one line why the flag is explained, e.g. figure page, long footnote, table)
    - [PAGE] OURS_WRONG — what the source says vs ours — FIX: file | old: `...` | new: `...`
    - [PAGE] UNCLEAR — what is uncertain

For OURS_WRONG give an exact `old` string that occurs once in the file and the corrected English `new` string; keep
our style (terms, notation, italics for original terms). For an omission, `new` is `old` plus the missing English text.
All fixes in English. Do NOT edit any file; write your result to the given verdict file. End your final message with the
counts per verdict. Be terse.
