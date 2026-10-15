"""Generate the tutorial section of knowledge/04_form_finding/compas_fd.md from schek_app.py.

Each `# %% [id] title` cell of schek_app.py becomes one subsection: its raw docstring is
the prose, the rest of the cell is shown as code and executed, and what it prints is
shown under the code.  The result replaces everything between the markers
`<!-- schek-app:start -->` and `<!-- schek-app:end -->` in the note.

    python examples/form_finding/build_note.py
"""

from __future__ import annotations

import contextlib
import io
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE / "schek_app.py"
NOTE = HERE.parents[1] / "knowledge/04_form_finding/compas_fd.md"
START, END = "<!-- schek-app:start -->", "<!-- schek-app:end -->"


def cells(source: str):
    parts = re.split(r"^# %% \[([a-z0-9]+)\] (.*)$", source, flags=re.M)
    for i in range(1, len(parts), 3):
        cid, title, body = parts[i], parts[i + 1].strip(), parts[i + 2]
        m = re.match(r'\s*r?"""(.*?)"""\s*\n', body, flags=re.S)
        prose = m.group(1).strip() if m else ""
        code = body[m.end():] if m else body
        yield cid, title, prose, code.strip("\n")


def main():
    source = APP.read_text()
    namespace = {"__name__": "schek_app", "__file__": str(APP)}
    sys.path.insert(0, str(HERE))
    PARTS = {"a": "Part A. The network as data", "b": "Part B. Equilibrium, the nonlinear form",
             "c": "Part C. The force density trick: a linear system", "d": "Part D. The form-finding loop",
             "e": "Part E. What the force densities mean", "f": "Part F. Additional conditions",
             "g": "Part G. The paper's examples, computed and drawn"}
    def anchor(title):
        t = "".join(ch for ch in title.lower() if ch.isalnum() or ch in " -_")
        return t.replace(" ", "-")
    all_cells = list(cells(source))
    out = [START, "", "## The application, section by section",
           "",
           "This is one program, `examples/form_finding/schek_app.py`, read from top to",
           "bottom. Every subsection is one section of the paper: what the paper says, the",
           "lines that add it to the program, and what those lines print when the file is",
           "run. The program is derived from the paper only (NumPy, nothing else); the",
           "comparison with `compas_fd` comes after it. This section is generated from the",
           "program by `build_note.py`, so code, output and text cannot drift apart.", "",
           "Contents", ""]
    last_part = None
    for cid, title, prose, code in all_cells:
        if cid[0] != last_part:
            out.append(f"- **{PARTS[cid[0]]}**"); last_part = cid[0]
        out.append(f"  - [{title}](#{anchor(title)})")
    out.append("")
    last_part = None
    for cid, title, prose, code in all_cells:
        if cid[0] != last_part:
            out += [f"## {PARTS[cid[0]]}", ""]; last_part = cid[0]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(compile(code, f"{APP.name}[{cid}]", "exec"), namespace)
        printed = buf.getvalue().rstrip()
        out += [f"### {title}", ""]
        if prose:
            out += [prose, ""]
        out += ["```python", code, "```", ""]
        if printed:
            out += ["Printed:", "", "```text", printed, "```", ""]
    out += [END]
    note = NOTE.read_text()
    i, j = note.index(START), note.index(END) + len(END)
    NOTE.write_text(note[:i] + "\n".join(out) + note[j:])
    print(f"wrote {len(all_cells)} subsections into {NOTE.name}")


if __name__ == "__main__":
    main()
