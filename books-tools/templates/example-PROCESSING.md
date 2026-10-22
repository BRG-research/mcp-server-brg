# PROCESSING — Föppl, *Vorlesungen über technische Mechanik*, II. Band: *Graphische Statik* (5th ed., 1920)

Folder ID: `graphic-statics-foeppl` · German → English · XII front + 404 text pages · 209 figures in the text.
English title: "Lectures on Engineering Mechanics, Vol. II: Graphic Statics (5th edition)". Public domain (Föppl d. 1924). NOT to be confused with `space-trusses-foeppl` (*Das Fachwerk im Raume*, 1892): do not touch it.

## Paths
- WORK = /home/pv/brg/code_python/Books/work/graphic-statics-foeppl
- Input (read-only): /home/pv/Downloads/RAW/Föppl.pdf — 212 A3 scans (3488 x 4912 px, 300 ppi), each spread rotated; rotate -90 (PIL `rotate(-90)`) to read. Native JPEGs: WORK/work/fp/raw/im-NNN.jpg (NNN = PDF page − 1; pdfimages).
- Split pages: WORK/work/fp/pages/sNNNL.jpg|sNNNR.jpg (NNN = PDF page, 002..212; s001F = cover), made by WORK/tools-lead/split.py (paper mask + gutter detection). OCR deu: WORK/work/fp/ocr/ (tesseract wrapper WORK/bin/tesseract).
- Printed-page view (symlinks to the kept copy): WORK/work/fpp/pages/pNNNN.jpg and ocr/pNNNN.txt (p0001…p0404; front matter fII…fXII).
- Page map: /home/pv/brg/code_python/Books/RAW/scan-maps/foeppl-graphische-statik.csv
- Clean scan: /home/pv/brg/code_python/Books/RAW/Foeppl_Vorlesungen_ueber_technische_Mechanik_II_Graphische_Statik_1920.pdf (419 pages; **PDF page = printed page + 14**; front matter: I = PDF 3 … XII = PDF 14).
- Book output: WORK/out/graphic-statics-foeppl (src/, figures/, build.py copied from the Henneberg book)

## Page map result (2026-10-22)
- 212 scans: scan 1 = closed book (cover), scan 2 = blank endpaper (L) + title page (R, = p. I), scans 3–4 = p. II–V, scans 5–6 = SECOND scan of the same four openings (p. II–V; of each page the sharper copy kept:
  II = s005L, III = s005R, IV = s006L, V = s004R), scan 7 = VI–VII, 8 = VIII–IX, 9 = X–XI, 10 = XII + p. 1, scans 11–212 = pp. 2–404 (printed page = 2·scan − 20 for L, +1 for R).
  s212R is blank (after the index, p. 404).
- Verified: printed numbers from the OCR running heads agree with the map on 356 pages; 45 more were re-read from the header crops (all OCR misreads, neighbours verified on both sides). No page missing, no duplicates except the front-matter openings above.
  Printed pages 1–404 complete; front matter I–XII complete (title I, imprint II, prefaces III–VI, contents VII–XII).
- Scan quality: dark background and a hand at the page edge in some scans (cropped away); text sharp; the gutter side of some pages is slightly curved.

## Structure — see SECTIONS.md (7 chapters = Abschnitte, 67 §§, problems 1–54, index 402–404)

## Translation jobs (page ranges inclusive)
| job | file | pages | status |
|---|---|---|---|
| T00 | 00-front-matter.md (cover, title, imprint, prefaces, contents) | I–XII | |
| T01 | 01-chapter-01.md | 1–11 | |
| T02 | 01-chapter-01-partB.md | 12–23 | |
| T03 | 01-chapter-01-partC.md | 24–35 | |
| T04 | 01-chapter-01-partD.md | 36–46 | |
| T05 | 01-chapter-01-partE.md | 47–57 | |
| T06 | 02-chapter-02.md | 58–68 | |
| T07 | 02-chapter-02-partB.md | 69–79 | |
| T08 | 02-chapter-02-partC.md | 80–90 | |
| T09 | 02-chapter-02-partD.md | 91–101 | |
| T10 | 02-chapter-02-partE.md | 102–112 | |
| T11 | 03-chapter-03.md | 113–123 | |
| T12 | 03-chapter-03-partB.md | 124–134 | |
| T13 | 03-chapter-03-partC.md | 135–145 | |
| T14 | 03-chapter-03-partD.md | 146–156 | |
| T15 | 03-chapter-03-partE.md | 157–166 | |
| T16 | 04-chapter-04.md | 167–178 | |
| T17 | 04-chapter-04-partB.md | 179–190 | |
| T18 | 04-chapter-04-partC.md | 191–201 | |
| T19 | 04-chapter-04-partD.md | 202–212 | |
| T20 | 04-chapter-04-partE.md | 213–223 | |
| T21 | 04-chapter-04-partF.md | 224–234 | |
| T22 | 05-chapter-05.md | 235–246 | |
| T23 | 05-chapter-05-partB.md | 247–258 | |
| T24 | 05-chapter-05-partC.md | 259–270 | |
| T25 | 05-chapter-05-partD.md | 271–281 | |
| T26 | 05-chapter-05-partE.md | 282–292 | |
| T27 | 06-chapter-06.md | 293–303 | |
| T28 | 06-chapter-06-partB.md | 304–314 | |
| T29 | 06-chapter-06-partC.md | 315–325 | |
| T30 | 06-chapter-06-partD.md | 326–336 | |
| T31 | 06-chapter-06-partE.md | 337–347 | |
| T32 | 06-chapter-06-partF.md | 348–357 | |
| T33 | 07-chapter-07.md | 358–368 | |
| T34 | 07-chapter-07-partB.md | 369–379 | |
| T35 | 07-chapter-07-partC.md | 380–390 | |
| T36 | 07-chapter-07-partD.md | 391–401 | |
| T37 | 08-index.md (Sachverzeichnis → "Subject index", entries translated) | 402–404 | |
Proofread jobs P<nn> mirror T<nn> (same page ranges), logs in WORK/reviews/REVIEW-P<nn>.md. Job notes in WORK/jobs/. Temp folders WORK/tools-<job>/.

## Progress
- [x] Extract, rotate, split, OCR deu (2026-10-22)
- [x] Page map, duplicates, clean PDF
- [ ] Translation T00–T37
- [ ] Automatic checks, proofread P00–P37, consistency pass, fix_anchors
- [ ] README, INDEX, GLOSSARY, FIGURES, SCANS, cover
- [ ] Upload
