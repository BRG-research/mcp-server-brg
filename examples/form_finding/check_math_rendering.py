"""Check that every formula in compas_fd.md renders on GitHub without raw dollar signs or stripped row breaks.

Rules enforced:
  1. Do not wrap tutorial sections in HTML <details> blocks (which break multi-line $$...$$ display math in GFM).
  2. Put each matrix row on its own line ending with `\\\\` + newline (`\\\\\\n`), never `\\\\ ` inline.
  3. Never use `\\,` or `\\;` (CommonMark strips `\\` before ASCII punctuation); use `\\quad`, `\\qquad`, or `\\text{ }`.
  4. Never place `$math$` inside `*emphasis*` or glued to a preceding hyphen, or use `}_` in inline math.

    python examples/form_finding/check_math_rendering.py
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "knowledge/04_form_finding/compas_fd.md"
GH = shutil.which("gh") or "/opt/homebrew/bin/gh"
md = PATH.read_text()

# Send in 2 chunks so each request stays well under GitHub's payload limit
mid = md.find("## Part D.")
chunks = [md[:mid], md[mid:]] if mid != -1 else [md]

total_display = 0
total_inline = 0
total_brace_budget = 0
bad = []
broken_rows = []

for n, c in enumerate(chunks):
    if "$" not in c:
        continue
    payload = json.dumps({"text": c, "mode": "gfm"})
    html = subprocess.run(
        [GH, "api", "-X", "POST", "/markdown", "--input", "-"],
        input=payload,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    total_display += html.count('class="js-display-math"')
    total_inline += html.count('class="js-inline-math"')

    # Check if any multi-row matrix inside <math-renderer> had its \\ unescaped to single \
    # or if CommonMark unescaped \_ or \% inside text mode (\text / \texttt)
    # or if CommonMark parsed _emphasis_ across _{ / }_ (which injects \n\n and &amp;amp;)
    # or if raw < / > inside math became &amp;lt; / &amp;gt; (which crashes MathJax/KaTeX)
    for block in re.findall(r"<math-renderer.*?</math-renderer>", html, flags=re.S):
        inner = re.sub(r"^<math-renderer[^>]*>|</math-renderer>$", "", block)
        import html as _html
        raw_tex = _html.unescape(inner)
        brace_cost = len(raw_tex.split("{"))
        total_brace_budget += brace_cost
        if brace_cost > 1000:
            broken_rows.append((n, f"single block exceeds GitHub 1000-brace limit ({brace_cost}): {raw_tex[:80]}"))
        if "\n\n" in block:
            broken_rows.append((n, f"blank line (\\par) inside math-renderer: {block[:80]}"))
        if "&amp;amp;" in block or "&amp;gt;" in block or "&amp;lt;" in block:
            broken_rows.append((n, f"double-escaped entity (&amp;) inside math-renderer: {block[:80]}"))
        if re.search(r"\\text(?:tt|bf|rm)?\{[^}]*_[^}]*\}", block):
            broken_rows.append((n, f"underscore in text mode: {block[:80]}"))
        for env in re.findall(
            r"\\begin\{(?:bmatrix|pmatrix|array|cases|matrix)\}(.*?)\\end\{(?:bmatrix|pmatrix|array|cases|matrix)\}",
            block,
            flags=re.S,
        ):
            lines = [
                ln.strip()
                for ln in env.strip().splitlines()
                if ln.strip() and not ln.strip().startswith("\\hline")
            ]
            if len(lines) > 1 and "\\\\" not in env:
                broken_rows.append((n, env[:100]))
            if len(lines) == 1 and re.search(r"\\(?![a-zA-Z\\])", env):
                broken_rows.append((n, f"single-line matrix with unescaped row break: {env[:80]}"))

    stripped = re.sub(r"<math-renderer.*?</math-renderer>", "", html, flags=re.S)
    stripped = re.sub(r"<code>.*?</code>|<pre>.*?</pre>", "", stripped, flags=re.S)
    for m in re.findall(r"\$+[^$\n]{1,80}\$+", stripped):
        bad.append((n, m))

if total_brace_budget > 2000:
    broken_rows.append((-1, f"page E.total() brace budget {total_brace_budget} exceeds GitHub 2000 limit!"))

print(f"display <math-renderer> blocks : {total_display}")
print(f"inline  <math-renderer> blocks : {total_inline}")
print(f"GitHub brace budget E.total()  : {total_brace_budget} / 2000")
print(f"UNRENDERED formulas (dollar signs shown) : {len(bad)}")
print(f"BROKEN matrix row breaks : {len(broken_rows)}")
for n, m in bad:
    print(f"   unrendered chunk {n}: {m[:76]}")
for n, m in broken_rows:
    print(f"   broken matrix chunk {n}: {m[:76]}")
sys.exit(1 if (bad or broken_rows) else 0)
