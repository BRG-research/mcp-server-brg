# Illustration brief — moving, step-by-step constructions

You are illustrating one chapter (or a group of chapters) of one book in this library.
Goal: every subject the chapter teaches that can be drawn is explained by an animated drawing
in the text: each construction, graphical method and solver procedure, and each concept or
proof that rests on a figure (equilibrium of a node, moment of a force, why a construction
works). The animation plays the steps, placed right after the original
figure. Graphic statics and graphical solvers are learned by watching the drawing being
built, line by line; a single finished figure plus paragraphs of "at 2 erect a
perpendicular meeting OL₂ at 2′" is what we are replacing as the way to read.

Tool: `tools/construction.py` (spec format in its docstring). Example to copy:
`graphic-statics-levy/constructions/fig05.json` (Lévy § 10, multiplication of lines).

Write only your own files: `<book>/constructions/*.json`, the outputs the tool makes, your
blocks in `<book>/src/<your chapters>.md`, and your rows in `<book>/constructions/PLAN.md`.

## Algorithm

1. **Read the chapter, not the whole book.** Open `LIBRARY.md`, the chapter's `INDEX.md`
   entry, the chapter source in `src/`, its rows in `FIGURES.md`, and the book's
   `GLOSSARY.md` for notation. For graphic statics, read the book's notation primer if it
   has one (for the ETH course: `GRAPHIC-STATICS-NOTATION.md`).

2. **List the candidates** into `<book>/constructions/PLAN.md`, one row per construction:
   `| § | figure | what is constructed | steps | priority | status |`. A candidate is any
   passage that builds a drawing in three or more actions on named points or lines:
   - geometric constructions (multiplication, powers, roots, centroids, moments, areas);
   - graphic statics procedures: force polygon and funicular (string) polygon, closing
     string, support reactions, resultant of a force system, pressure / thrust line,
     Varignon polygon, Cremona (reciprocal) diagram, Culmann's method, Ritter section,
     moment and shear diagrams read from the funicular polygon, influence lines,
     ellipse of inertia and kern;
   - proofs that rest on a figure (similar triangles, parallel sides of reciprocal figures).
   Priority 1: a method the book reuses later (funicular polygon, Cremona, Culmann) and
   every worked example of it. Priority 2: one-off constructions. Skip single lines,
   photographs, and figures whose meaning is clear at a glance.

3. **Compute the geometry; never eyeball it.** For each candidate, write a few lines of
   Python that perform the construction numerically from example inputs (intersect the
   lines, draw the parallels, close the polygons) and print the point coordinates. Use the
   book's own point names and labels, and the same topology and orientation as the
   original figure. Pick example values that keep every label at least ~30 px apart at the
   380 px drawing width and keep the figure roughly as tall as wide; when the book gives
   numbers in a worked example, use exactly those.

4. **Write the spec.**
   - One step = one action of the text, in the text's order. The step sentence is in your
     own words, at most two sentences, names the new points and says what the new line
     means ("the closing string; its parallel through the pole cuts off the reactions").
   - Style is the eQUILIBRIUM step-by-step viewer's (BRG-teaching/Teaching,
     `2_computational_form_finding/Equilibrium/drawings/web/lib/eqdraw.js`), built into the
     tool: compression navy, tension pink, loads / reactions / resultants green, guides grey,
     zero-force members pale grey; what a step adds flashes black; points are white disks
     with a dark ring; arrows, dashes and line weights in the viewer's proportions. Don't
     restyle per drawing; pick the style name that says what the element is.
   - Colour by meaning and keep it fixed: `compression`, `tension`, `load`, `zero` for
     members and forces (a force keeps its colour in form and force diagram);
     `resultant` (dashed green arrow) for resultants; `ray` / `guide` for construction
     lines and rays of the force diagram; `string` for funicular strings; `perp` (dashed)
     for auxiliary lines; `dim` for dimension lines; `base` for the given geometry;
     `compression_band` / `tension_band` polygons for force-proportional member bands. In
     constructions that are not statics, one `q1…q6` colour per quantity (a length laid
     off again keeps its colour).
   - Forces are `arrow` elements. Draw form diagram and force diagram side by side in one
     spec (offset the force diagram's coordinates) and label both with `text`. When the
     source has a matching eQUILIBRIUM drawing (`drawings/python/ops/view_N.json` there,
     53 views with captions per step), follow its step order and captions.
   - Lengths laid off along an existing line go as offset bars beside it (as in fig05), so
     they don't hide each other.
   - End with a "why it works" step: shade the similar triangles, the closed force polygon,
     or the pair of parallel lines the proof uses.
   - Add `checks` for every claim the construction makes: each intersection point is
     `collinear` with its two lines, every perpendicular is `perp`, every transfer is
     `equal`, every reciprocal pair is `parallel`, and the final result is a `value`
     computed independently (the formula in the text). The tool refuses to write anything
     if a check fails.

5. **Render and look.** `python3 tools/construction.py <spec> --png`, then open every
   `work/steps/<name>-sNN.png`. Fix and re-render until: no label overlaps a line or
   another label; the new element of each step is obvious; the last step matches the
   original figure (same points, same shape); text lines in the animation fit.

6. **Insert after the original figure.** Set `chapter` and `figure` (the original figure's
   image path) in the spec; the animation goes right after that figure, once. Don't put
   step stills in the text and never show a figure twice (only the book's own figures may
   recur, as the book has them). Hatch proof regions grey (`poly`, default style) and
   retire intermediate hatches with `"until"`. Then
   `python3 tools/construction.py <spec> --png --insert` writes the block into `src/`
   (re-running replaces it); rebuild the chapter (`unconverted: 0`) and check that each
   original figure is followed by exactly one animation.

7. **Record and publish.** Set the row's status in `PLAN.md` to done, run
   `python3 tools/library_map.py --check`, and commit one chapter at a time with the
   attribution lines; push.

## Budget

Most of the cost is step 1 and 4. Work chapter by chapter; when a session's context is
filling up, finish the current spec, commit, and leave `PLAN.md` accurate so the next
session continues from the first row that is not done. Several agents can run in
parallel on different chapters; each owns its chapters' rows and files.
