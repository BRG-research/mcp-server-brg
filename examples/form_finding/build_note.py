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

PARTS_TITLES = {
    "a": "Part A. The network as data",
    "b": "Part B. Equilibrium, the nonlinear form",
    "c": "Part C. The force density trick: a linear system",
    "d": "Part D. The form-finding loop",
    "e": "Part E. What the force densities mean",
    "f": "Part F. Asking for lengths and forces",
    "g": "Part G. The paper's examples, recomputed",
}


def sanitize_gfm_math(text: str) -> str:
    """Prevent GFM CommonMark from parsing _emphasis_ or HTML-escaping < > inside TeX math."""
    def _fix(m: re.Match[str]) -> str:
        s = m.group(0)
        s = re.sub(r"([})\]])_", r"\1 _ ", s)
        s = s.replace(">", r"\gt ").replace("<", r"\lt ")
        return s

    return re.sub(r"\$\$.*?\$\$|\$[^$\n]+\$", _fix, text, flags=re.S)


def cells(source: str):
    parts = re.split(r"^# %% \[([a-z0-9]+)\] (.*)$", source, flags=re.M)
    for i in range(1, len(parts), 3):
        cid, title, body = parts[i], parts[i + 1].strip(), parts[i + 2]
        m = re.match(r'\s*r?"""(.*?)"""\s*\n', body, flags=re.S)
        prose = sanitize_gfm_math(m.group(1).strip()) if m else ""
        code = body[m.end():] if m else body
        explain = ""
        if "# %% explain" in code:
            code, tail = code.split("# %% explain", 1)
            e = re.search(r'r?"""(.*?)"""', tail, flags=re.S)
            explain = sanitize_gfm_math(e.group(1).strip()) if e else ""
        yield cid, sanitize_gfm_math(title), prose, code.strip("\n"), explain


def main():
    source = APP.read_text()
    namespace = {"__name__": "schek_app", "__file__": str(APP)}
    sys.path.insert(0, str(HERE))
    all_cells = list(cells(source))
    out = [
        START,
        "",
        "## Build the force density method step by step",
        "",
        "Follow the subsections in order (`examples/form_finding/schek_app.py`). Every equation is paired immediately with an explicit numerical matrix example on the same **9-node, 12-branch saddle cable net** (`n = 5` free nodes, `n_f = 4` fixed anchors, `m = 12` branches).",
        "",
        "| Milestone | What you can do |",
        "|---|---|",
        "| **A.1–A.4** | Define the 9-node, 12-branch cable net, diagonal matrices $U, Q$, connectivity $C_s = [C \\mid C_f]$, and $D = C^T Q C$. |",
        "| **B.1–B.3** | Compute branch coordinate differences, lengths, and the 4-stage nonlinear equilibrium residual on the 9-node net. |",
        "| **C.1–C.4** | Apply $q_j = s_j / l_j$, assemble $D$ and $D_f$, solve the 5 free-node coordinates, and recover all 12 cable forces and cutting lengths. |",
        "| **D.1–D.2** | Package the 3D linear solver and 4-anchor support reactions into a single function and compare 4 load/prestress cases. |",
        "| **E.1** | Interpret $q_j$ geometrically as a weight minimizing $\\sum_{j=1}^{12} q_j l_j^2$ on the unloaded 9-node saddle. |",
        "| **F.1–F.3** | Enforce target branch lengths and forces on the 9-node net via constrained least-squares and the sensitivity Jacobian $G^T$. |",
        "",
    ]
    last_part = None
    for cid, title, prose, code, explain in all_cells:
        if cid[0] != last_part:
            out += ["---", "", f"## {PARTS_TITLES[cid[0]]}", ""]
            last_part = cid[0]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), np.printoptions(precision=3, suppress=True, linewidth=120):
            exec(compile(code, f"{APP.name}[{cid}]", "exec"), namespace)
        printed = buf.getvalue().rstrip()
        out += [f"### {title}", ""]
        if prose:
            out += [prose, ""]
        if code:
            out += ["**Add to your program:**", "", "```python", code, "```", ""]
        if explain:
            out += [explain, ""]
        if printed:
            out += ["**Example output:**", "", "```text", printed, "```", ""]
    out += [END]
    note = NOTE.read_text()
    i, j = note.index(START), note.index(END) + len(END)
    NOTE.write_text(sanitize_gfm_math(note[:i]) + "\n".join(out) + sanitize_gfm_math(note[j:]))
    print(f"wrote {len(all_cells)} subsections into {NOTE.name}")


if __name__ == "__main__":
    main()
