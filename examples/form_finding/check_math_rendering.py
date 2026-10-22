"""Check that every formula in compas_fd.md actually renders on GitHub.

GitHub refuses to wrap some maths in a <math-renderer>, so it shows as literal dollar
signs.  Three cases, all found the hard way and all now handled by build_note.py:

  1. `$$...$$` display math inside an HTML <details> block  -> never wrapped.
     Inline `$...$` inside <details> IS wrapped, so display maths is emitted as a
     blockquoted inline formula.
  2. inline maths inside *emphasis*  -> never wrapped.  The emphasis is kept on the
     label only, so the formula sits outside it.
  3. an opening `$` glued to the previous word, e.g. `positive-$q$`  -> not wrapped.

Run after editing the note; it exits non-zero if anything would show as dollar signs.

    python examples/form_finding/check_math_rendering.py
"""
import json, re, subprocess, sys

PATH = "/Users/petras/brg/2_code/mcp-server-brg/knowledge/04_form_finding/compas_fd.md"
md = open(PATH).read()

# chunk on the collapsible part boundaries so each request stays small,
# keeping each <details> wrapper intact because that is what breaks math
chunks, i = [], 0
while True:
    a = md.find("<details>", i)
    if a == -1:
        chunks.append(md[i:]); break
    if a > i: chunks.append(md[i:a])
    b = md.index("</details>", a) + len("</details>")
    chunks.append(md[a:b]); i = b

total_wrapped = 0
bad = []
for n, c in enumerate(chunks):
    if "$" not in c: continue
    json.dump({"text": c, "mode": "gfm"}, open("/tmp/_chunk.json", "w"))
    html = subprocess.run(["gh","api","-X","POST","/markdown","--input","/tmp/_chunk.json"],
                          capture_output=True, text=True).stdout
    total_wrapped += html.count("math-renderer")
    stripped = re.sub(r"<math-renderer.*?</math-renderer>", "", html, flags=re.S)
    stripped = re.sub(r"<code>.*?</code>|<pre>.*?</pre>", "", stripped, flags=re.S)
    for m in re.findall(r"\$[^$\n]{1,80}\$", stripped):
        bad.append((n, m))

print(f"math-renderer wrappers produced : {total_wrapped}")
print(f"UNRENDERED formulas (dollar signs shown) : {len(bad)}")
seen = set()
for n, m in bad:
    if m in seen: continue
    seen.add(m)
    print(f"   chunk {n}: {m[:76]}")
sys.exit(1 if bad else 0)
