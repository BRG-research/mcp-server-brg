"""Generate the tutorial section of knowledge/04_form_finding/compas_fd.md from schek_app.py.

Each `# %% [id] title` cell of schek_app.py becomes one subsection: its raw docstring is
the prose, the rest of the cell is shown as code and executed, and what it prints is
shown under the code. The result replaces everything between the markers
`<!-- schek-app:start -->` and `<!-- schek-app:end -->` in the note.

    python examples/form_finding/build_note.py
"""

from __future__ import annotations

import contextlib
import io
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
APP = HERE / "schek_app.py"
NOTE = HERE.parents[1] / "knowledge/04_form_finding/compas_fd.md"
START, END = "<!-- schek-app:start -->", "<!-- schek-app:end -->"

PARTS_TITLES = {"a": "Part A. The network as data", "b": "Part B. Equilibrium, the nonlinear form",
                "c": "Part C. The force density trick: a linear system", "d": "Part D. The form-finding loop",
                "e": "Part E. What the force densities mean", "f": "Part F. Asking for lengths and forces",
                "g": "Part G. The paper's examples, recomputed"}


def cells(source: str):
    parts = re.split(r"^# %% \[([a-z0-9]+)\] (.*)$", source, flags=re.M)
    for i in range(1, len(parts), 3):
        cid, title, body = parts[i], parts[i + 1].strip(), parts[i + 2]
        if cid == "export":
            break
        m = re.match(r'\s*r?"""(.*?)"""\s*\n', body, flags=re.S)
        prose = m.group(1).strip() if m else ""
        code = body[m.end():] if m else body
        explain = ""
        if "# %% explain" in code:
            code, tail = code.split("# %% explain", 1)
            e = re.search(r'r?"""(.*?)"""', tail, flags=re.S)
            explain = e.group(1).strip() if e else ""
        yield cid, title, prose, code.strip("\n"), explain



DISPLAY_MATH = re.compile(r"^\$\$\n(.*?)\n\$\$$", re.M | re.S)
ONELINE_MATH = re.compile(r"^\$\$ (.*?) \$\$$", re.M)


def portable_math(text: str) -> str:
    """Rewrite display math so it survives inside an HTML <details> block.

    GitHub wraps `$...$` inline math in a <math-renderer> even inside raw HTML, but it
    does NOT wrap `$$...$$` display math there -- it comes out as literal dollar signs.
    Every subsection of this note lives inside a collapsible part, so display math is
    emitted as a blockquoted inline formula, which both GitHub and the VS Code preview
    render.  Verified against GitHub's own /markdown API and @vscode/markdown-it-katex.
    """
    def collapse(m):
        body = " ".join(ln.strip() for ln in m.group(1).splitlines() if ln.strip())
        return "> $" + body + "$"
    text = ONELINE_MATH.sub(lambda m: "> $" + m.group(1).strip() + "$", DISPLAY_MATH.sub(collapse, text))
    # GitHub also refuses to wrap inline math that sits inside *emphasis*, so keep the
    # emphasis on the label only and let the formula stand outside it.
    text = re.sub(r"(?<!\*)\*(?!\*)([^*\n]*?:)[ ]*([^*\n]*\$[^*\n]*)\*(?!\*)",
                  lambda m: f"*{m.group(1)}* {m.group(2)}", text)
    text = re.sub(r"(?<!\*)\*(?!\*)([^*\n]*\$[^*\n]*)\*(?!\*)", lambda m: m.group(1), text)
    return text


def main():
    source = APP.read_text()
    namespace = {"__name__": "schek_app", "__file__": str(APP)}
    sys.path.insert(0, str(HERE))
    PARTS = PARTS_TITLES
    def anchor(title):
        t = "".join(ch for ch in title.lower() if ch.isalnum() or ch in " -_")
        return t.replace(" ", "-")
    all_cells = list(cells(source))
    out = [START, "", "## Build the force density method step by step", "",
           "Start with an empty Python file or notebook. Follow the subsections in order:",
           "each adds data or a calculation that the following steps need. The complete",
           "program is also available in `examples/form_finding/schek_app.py`.", "",
           "Read each explanation, then append its code to the same Python file or notebook.",
           "Every subsection has the same shape: **what the step does**, the **equation**,",
           "the **stages read right to left**, and **the same thing with our numbers** —",
           "every matrix printed with labelled rows and columns so you can point at any",
           "entry and say where it came from. A.4 has no code: it is the five matrix",
           "operations worked through with real numbers.", "",
           "`@` is matrix multiplication. `*` is entry-by-entry multiplication. Shapes are",
           "written next to every array. Displayed output is rounded; the calculation keeps",
           "full precision. Parts A to E need only NumPy; part F adds `scipy.optimize`.", "",
           "| Milestone | What you can do |",
           "|---|---|",
           "| A.1–A.4 | Represent a network and understand its matrix operations. |",
           "| B.1–B.3 | Compute branch geometry and test nodal equilibrium. |",
           "| C.1–C.4 | Derive and execute the linear force density solve. |",
           "| D.1–D.2 | Reuse a complete linear solver with different supports and force densities. |",
           "| E.1 | Interpret the geometric effect of force densities. |",
           "| F.1–F.3 | Ask for wanted lengths and forces on top of equilibrium. |",
           "| G.1–G.5 | Apply the same solvers to larger reconstructed examples. |", "",
           "**The linear force density method is complete at D.2.** Part F sits on top of it",
           "and is not a prerequisite. Package API details follow the tutorial, for",
           "comparison after implementing the method yourself.", "",
           "This tutorial is generated from the program by `build_note.py`; it executes",
           "each implementation block before updating this Markdown.", "",
           "**Each part below opens on click.** Open one, work through it, close it,",
           "open the next.", ""]
    subs = {}
    for cid, title, *_ in all_cells:
        subs.setdefault(cid[0], []).append(re.sub(r"\s*\((section|sections|figure|equation|equations)[^)]*\)", "", title))
    last_part = None
    for cid, title, prose, code, explain in all_cells:
        if cid[0] != last_part:
            if last_part is not None:
                out += ["</details>", ""]
            ids = " · ".join(subs[cid[0]])
            out += ["<details>",
                    f"<summary><b>{PARTS[cid[0]]}</b> &nbsp;&nbsp; {ids}</summary>",
                    ""]
            last_part = cid[0]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), np.printoptions(precision=3, suppress=True, linewidth=120):
            exec(compile(code, f"{APP.name}[{cid}]", "exec"), namespace)
        printed = buf.getvalue().rstrip()
        out += [f"### {title}", ""]
        if prose:
            out += [portable_math(prose), ""]
        if code:
            out += ["**Add to your program:**", "", "```python", code, "```", ""]
        if explain:
            out += [portable_math(explain), ""]
        if printed:
            out += ["Example output:", "", "```text", printed, "```", ""]
    out += ["</details>", "", END]
    note = NOTE.read_text()
    i, j = note.index(START), note.index(END) + len(END)
    NOTE.write_text(note[:i] + "\n".join(out) + note[j:])
    print(f"wrote {len(all_cells)} subsections into {NOTE.name}")


if __name__ == "__main__":
    main()
