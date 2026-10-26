# Formula style

How to write formulas in knowledge notes and notebooks. Reference example:
[04_form_finding/compas_fd.md](04_form_finding/compas_fd.md) and [04_form_finding/compas_fd.ipynb](04_form_finding/compas_fd.ipynb).
The aim is that every equation is immediately clear with minimal prose: show the general formula in display math (`$$ ... $$`), then immediately show a worked numerical matrix example (`\begin{bmatrix} ... \end{bmatrix}`) with inline labels and shapes.

Translated books are different: their running text reproduces the author's formulas symbol for symbol (see
`books-tools/TRANSLATE_BRIEF.md`). Use this style there only in clearly separated commentary (README, GLOSSARY,
explanatory notes), never inside the translation.

## Syntax & GitHub Flavored Markdown (GFM) Rules

Verified against GitHub's `/markdown` API (`examples/form_finding/check_math_rendering.py`) and KaTeX:

1. **Display math in `$$` blocks**: Put `$$` on its own lines with a blank line before and after.
2. **Never wrap sections containing display math inside HTML `<details>` blocks**: In GitHub Flavored Markdown, multi-line `$$ ... $$` blocks inside `<details>` have their line breaks converted to `<br>` and fail to render (showing literal `$$` dollar signs). Keep sections as standard Markdown headings (`##`, `###`).
3. **Matrix row breaks (`\\`) MUST be at the end of a line**:
   - In GitHub Markdown, `\\ ` in the middle of a single line (e.g. `\begin{bmatrix} 1 \\ 2 \end{bmatrix}`) is unescaped by CommonMark into a single `\` (a space in LaTeX), collapsing the matrix onto one row.
   - Always put each matrix row on its own line ending with `\\` followed immediately by a newline (`\\\n`):

   ```latex
   $$
   \mathbf{u} = \begin{bmatrix}
   2 \\
   -1 \\
   3
   \end{bmatrix}
   \qquad \longrightarrow \qquad
   U = \mathrm{diag}(\mathbf{u}) = \begin{bmatrix}
   2 & 0 & 0 \\
   0 & -1 & 0 \\
   0 & 0 & 3
   \end{bmatrix}
   $$
   ```

4. **Never use `\,` or `\;` (backslash + punctuation) for spacing**: CommonMark treats `\` before ASCII punctuation (`,` or `;`) as a Markdown escape and strips the backslash, turning `C_f\,x_f` into `C_f,x_f` and `\;=\;` into `;=;`. Use alphabetic TeX spacing commands (`\quad`, `\qquad`, `\text{ }`), which CommonMark leaves untouched.
5. **Never put a standalone `=` on its own line inside `$$ ... $$`**: CommonMark parses a line containing only `=` as a Setext `<h1>` heading underline, splitting the math block. Keep `=` at the end of the previous line (`\end{bmatrix} =`) or start of the next (`= \begin{bmatrix}`).
6. **Always space brace-adjacent subscripts (`} _ ` and ` _ {`) and use `\lt` / `\gt` instead of `<` / `>`**:
   - In GitHub Flavored Markdown, `}_` (e.g. `\mathbf{R}_f`) opens `_..._` emphasis and `_{` (e.g. `R_{6x}`) closes it before the math filter runs. When CommonMark parses `<em>` inside `$$ ... $$`, GitHub's `<math-renderer>` serializer inserts `\n\n` (illegal `\par` in TeX) and double-escapes matrix `&` to `&amp;amp;`, causing GitHub to display **"Unable to render expression"**. Writing `} _ ` and ` _ {` makes `_` whitespace-flanked so CommonMark never parses it as emphasis, while TeX ignores spaces around `_`.
   - Never write raw `<` or `>` inside `$ ... $` or `$$ ... $$`: GitHub double-escapes them to `&amp;lt;` and `&amp;gt;`, which decode in the browser to `&lt;` and `&gt;` and crash MathJax/KaTeX on the `&` character ("Unable to render expression"). Always use `\lt` and `\gt` (or `\le` / `\ge`).
7. **Keep `$math$` outside `**bold**` / `*emphasis*`, separated from hyphens, and never end parenthesized inline math with `)$)`**: Write `positive $q$`, not `positive-$q$`, and avoid `($F = q(x_1 - x_2)$)` where `)` immediately precedes `$)`.

## Shape of an Explained Formula

1. **Concise lead-in (1–2 sentences)**: State what is computed, with units and array shapes.
2. **General equation (`$$ ... $$`)**: One clean display block. For multi-factor matrix chains (e.g. $C^T U L^{-1} \mathbf{s} - \mathbf{p}_x$), label the stages from right to left.
3. **Worked numerical matrix example (`$$ ... $$`)**: Immediately follow every general equation with the actual matrices and numbers from the benchmark dataset, using right-hand `\begin{matrix} \leftarrow \text{...} \end{matrix}` annotations to label nodes or branches directly next to the rows.
4. **Minimal code note**: 1–2 bullet points connecting the math symbols to the NumPy/SciPy operations and shapes.
