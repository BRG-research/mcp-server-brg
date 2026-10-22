# Formula style

How to write formulas in knowledge notes and other explanatory text. Reference example:
[04_form_finding/compas_fd.md](04_form_finding/compas_fd.md). The aim is that a reader who is not fluent in the
notation can still follow every formula: show the formula, then say in plain words what it does, then show it with
real numbers.

Translated books are different: their running text reproduces the author's formulas symbol for symbol (see
`books-tools/TRANSLATE_BRIEF.md`). Use this style there only in clearly separated commentary (README, GLOSSARY,
explanatory notes), never inside the translation.

## Syntax

- Inline math `$...$`, display math in a `$$` block with `$$` on its own lines and a blank line before and after.
  One idea per block; put related equations in one block separated by `\qquad`.
- Words inside formulas: `\text{if }`, `\text{otherwise}`; functions and labels upright: `\mathrm{diag}(u)`.
- Matrices: `pmatrix` for column vectors and small worked matrices, `bmatrix` for block matrices,
  `cases` for piecewise definitions. A transpose is `^{t}` (or `^{\mathsf T}`, but stay consistent in a note).
- Define every symbol the first time it appears, in the sentence that introduces the formula:
  "For branch $j$ with axial force $s_j$ and strained length $l_j$, …"
- State units or dimension right after a physical quantity: "Dimension: force / length (N/m, kN/m)."

## Shape of an explained formula

1. **Lead-in sentence** naming what is computed and defining the symbols.
2. **The formula** as a display block. Number it as in the source when one exists ("Equation (2)").
3. **"Read it as:"** a one-sentence plain-language reading in italics, then "That is all the formula says." when
   the formula is simpler than it looks.
4. **Symbol table** for any formula with more than two symbols:

   | Symbol | Say it as | One entry means | Shape |
   |---|---|---|---|
   | $u$ | "u" | start-node $x$ **minus** end-node $x$, for one branch | `(12,)` |

5. **Dense products are read from the right**, one factor at a time, in a step table
   (Step | Symbol | Say it as | What it does | Shape of the result), because that is the order in which the
   numbers flow.
6. **A worked instance with actual numbers**: the notation on top, the numbers underneath, e.g.

   $$
   u = \begin{pmatrix} 2 \\ -1 \\ 3 \end{pmatrix}
   \qquad\longrightarrow\qquad
   U = \mathrm{diag}(u) = \begin{pmatrix} 2 & 0 & 0 \\ 0 & -1 & 0 \\ 0 & 0 & 3 \end{pmatrix}
   $$

   then, where code is involved, the same values as printed arrays in a ```` ```text ```` block with their shapes.
7. **"Why those numbers?"** when a pattern is not obvious: expand one row or term so the reader sees what survives,
   e.g. $(+1)x_1 + 0x_2 + \dots + (-1)x_6 = x_1 - x_6$, and say the conclusion in bold in one line.

## What GitHub will not render

Verified against GitHub's own `/markdown` API. `examples/form_finding/check_math_rendering.py`
fails the build if any of these creep back in.

- **`$$...$$` display math inside an HTML `<details>` block is never rendered** — it shows
  as literal dollar signs. Inline `$...$` inside `<details>` *is* rendered, so write display
  maths there as a blockquoted inline formula: `> $a = b$`.
- **Inline maths inside `*emphasis*` is never rendered.** Keep the emphasis on the label
  only: `*Read it as:* the sum of $q_j$ …`, not `*Read it as: the sum of $q_j$ …*`.
- **An opening `$` glued to the previous word is not rendered** — write `positive $q$`,
  not `positive-$q$`.
- ` ```math ` fenced blocks render on GitHub but **not** in the VS Code preview, so they are
  not portable; do not use them.

## Tone

- Short sentences, active voice, second person for instructions ("Multiply that row by …").
- Bold only the one key idea per paragraph.
- No new notation without a lead-in; no formula without at least one sentence of reading.
