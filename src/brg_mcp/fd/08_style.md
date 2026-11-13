Style of the notebooks and Python examples

# Names

- File: lowercase words joined by underscores, with a number: `exercise_01_forces.ipynb`.
- Title: the file name in words, as the first heading: `# Exercise 01 Forces`.
- No hyphens or dashes anywhere: titles, text, captions, alt text. Write "fixed nodes", "e0 to e3", "Step 1:".

# Cells

- Second cell: the installation of everything the notebook imports, with fixed versions:
  `%pip install -q numpy session-py==0.310.0 session-jupyter==0.2.0`. It runs in the browser and on a laptop.
- One idea per markdown cell, starting with a `#` heading in title case: `# Vector Projections`.
- Then the question: the question in bold, then the given values, the matrix and a figure.
- A line `<hr style="border: none; border-top: 2px solid #555; margin: 2em 0;">` closes the question.
- Then one heading per step, each with its code cell: `# Network`, `# Solve`, `# Sum of Forces`, `# Observation`.

# Text

- Short sentences in plain words.
- Bold for the key words: **Given:**, **Unknown:**, **Equilibrium:**.
- Formulas in LaTeX: `$...$` in a sentence, `$$...$$` on their own line, units with `\text{ kN}`.
- Colours: free nodes red `{\color{#d62828} n_0}`, fixed nodes blue `#2a6fdb`, loads green `#2e9e4a`.

# Figures

- SVG from `https://raw.githubusercontent.com/BRG-teaching/Teaching/main/CAS/logos/`.
- Centred in a `<div align="center">`, `width:100%`, with alt text and an italic caption.

# Code

- numpy for the numbers, matplotlib or session_jupyter to show the result.
- Names as in the formulas: `C`, `C_N`, `C_F`, `x_F`, `q`, `Q`, `p_z`.
- Short lowercase comments that say what a line does: `# fixed node coordinates (n1..n4)`, `# equation 6.32`.
- The notebook runs in the Jupyter of the teaching website (Python in the browser).
- Exercises have no answers and no outputs; the answers keep them.

# Python examples

- Put the examples of a numbered Markdown page in the folder with the same name: `10_compas.md` and `10_compas/`.
- File: lowercase words joined by underscores, with a number for the order: `03_hypar_membrane.md`.
- First line: the title, the Python filename and a one-sentence summary: `Hypar membrane, fd_hypar_membrane.py: ...`.
- Then link the original source and any historical precedent in `04_references.md`.
- One standalone fenced `python` block per page, starting with a short module docstring; the reader can save it as the named `.py` file and run it after installing `compas_fd`.
- Use `compas.datastructures.Mesh` for grid topologies and plain lists for small or parametric networks; import one name per line and keep lines within the Ruff limit.
- Build `vertices`, `fixed`, `edges` and `forcedensities` before calling `fd_numpy`; add `loads` for selfweight or other nodal loads.
- Positive force densities represent tension and negative values compression; gravity loads point in negative Z; use `SelfweightCalculator` for tributary-area loads.
- Use `fd_constrained_numpy` for sliding supports, with one constraint or `None` per vertex; constrained anchors also remain in `fixed`, as in FormFinder, while their tangential updates move them.
- Examples must run outside Rhino without `compas_fofin`, interactive input or hidden geometry backends; use normal `compas_fd` dependencies only.
- Keep examples deterministic and print the defining supports, height range or force range so the result can be checked without a viewer.
- Use short lowercase comments only where an index, topology choice or equation needs clarification.
- Give every historical structure a reference with a source link and a direct relative link to one local image in `04_references/`.
