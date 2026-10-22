"""Turn a geometric construction described in words into moving, step-by-step figures.

    python3 tools/construction.py graphic-statics-levy/constructions/fig05.json
    python3 tools/construction.py <spec> --png      # also write PNG previews for checking
    python3 tools/construction.py <spec> --insert   # also put the blocks into the chapter source

Reads one construction spec (JSON, format below), checks its geometry, and writes:

- `figures/steps/<name>.webp`: the animation as an animated WebP, which is what the chapter
  shows: it plays wherever images play (GitHub web and app, editors, most viewers).
- `figures/steps/<name>.svg`: the same animation as a sharp vector drawing (linked under the
  WebP). Each step draws its new lines in, highlights them, and shows the step's sentence
  underneath. It is a plain SVG image animated with SMIL, so it moves inside Markdown
  (GitHub web, GitHub app, most viewers) with no script; viewers that ignore animation
  show the finished construction.
- `figures/steps/<name>-sNN.svg`: one still picture per step (everything so far; what the
  step adds is drawn black, as in the eQUILIBRIUM viewer). For reading at your own pace.
- `constructions/<name>.html`: a self-contained interactive page (Back/Next, slider,
  arrow keys, swipe). GitHub does not run scripts in Markdown, so this page is opened
  directly: locally, through GitHub Pages, or published as an artifact.
- `--png`: `work/steps/<name>-sNN.png` previews to look at before committing.
- the Markdown blocks, IN THE TEXT: the animated drawing right after the original figure,
  and each group of step stills right after the paragraph that describes those steps
  ("place" in the spec), so the reader sees each step where the text explains it.
  `--insert` writes them into the chapter source (re-running replaces them; they are
  wrapped in `<!-- construction:<name> … -->` markers); without it they are printed.

The original figure is never replaced: these are added teaching drawings, computed from
the text with example values, and the block says so.

Style: the eQUILIBRIUM step-by-step viewer (BRG-teaching/Teaching,
2_computational_form_finding/Equilibrium/drawings/web/lib/eqdraw.js, PAL): white
background, hairline strokes, compression navy #1a1eb2, tension pink #ce4095, external
loads / reactions / resultants green #3f9c20, guides and construction lines grey #aaaaaa,
zero-force members pale grey #b9b9bd. Whatever the current step adds is drawn black
(#111111) and takes its proper colour from the next step on; points are white disks with a
dark edge (pale grey face while current). A force keeps its colour in the form and the
force diagram. Helvetica Neue, pink accent.

Spec format:
{
  "name": "fig05", "title": "...", "source": "Lévy, § 10, Fig. 5, pp. 6–8",
  "note": "Example lengths: d = 2, ...",            # shown under the drawings
  "chapter": "src/01-chapter-01.md",                # chapter source, relative to the book
  "figure": "figures/fig05.png",                    # the original figure: animation goes after it
  "place": [                                        # step stills go after these paragraphs
    {"after": "forming the indefinite lines", "steps": [1, 2, 3]},   # a unique text snippet
    {"after": "meeting $`OL_3`$ at", "steps": [4, 5, 6]}
  ],
  "points": {"O": [0, 0], "1": [2, 0], ...},        # world coordinates, y up
  "offsets": {"O": [-12, 14], ...},                 # label offset in px (default [6, -6])
  "styles": {"y1": "#2196EA", ...},                 # extra colours by name (optional)
  "checks": [                                        # verified before anything is written
    {"collinear": ["O", "l₂", "2′"]},                # three points on one line
    {"perp": [["2", "2′"], ["O", "1"]]},            # two directions at right angles
    {"parallel": [["a", "b"], ["c", "d"]]},         # (force diagram ∥ form diagram)
    {"equal": [["2", "2′"], ["O", "3"]]},           # two lengths equal
    {"value": [["5", "5′"], 2.592]},                # a length has a known value
    {"area_equal": [["A", "B", "C"], ["B", "A′", "K"]]}   # two polygons, same area
  ],
  "steps": [
    {"text": "Lay off O1 = d along OX.",            # one or two sentences, own words
     "draw": [
       {"seg": ["O", "1"], "style": "base", "label": "d"},   # segment between two points
       {"ray": ["O", "l2"], "to_x": 2.6},                    # line from A through B, to x
       {"line": [[0, 0], [4, 0]], "label": "X",              # free segment (coordinates);
        "label_at": "end"},                                  # label at its end, not middle
       {"arrow": ["A", "B"], "style": "load", "label": "P₁"},# force: arrowhead at B
       {"poly": ["O", "1", "l2"], "style": "y2"},            # shaded polygon
       {"text": "form diagram", "at": [0, 4]},               # free text at coordinates
       {"pt": ["O", "1"]},                                   # show and label these points
       {"poly": [...], "until": 5}                           # any element: hidden from step 5 on
     ]}
  ]
}
Elements also include {"path": [p, q, r, ...]} (polyline or sampled curve through points
or coordinates) and {"arc": {"c": "O", "r": 1.5, "from": 0, "to": 90}} (circle arc,
degrees, counter-clockwise); both are drawn in like lines.
Built-in styles: hatch (default for "poly": grey fill for equal-area or proof regions),
base (given geometry, member weight), ray / guide (construction lines,
ray weight), perp (dashed guide), dim (dashed dimension line), string (funicular string),
compression, tension, load, zero, resultant (green, dashed shaft, solid head; use with
"arrow"), compression_band / tension_band (pale fills for force-proportional bands), and
q1…q6 (one colour per quantity in non-statics constructions, e.g. per length). Arrows,
points and dashes use the viewer's own proportions (`M` below). Any other style name is
looked up in "styles".
"""
import json, math, pathlib, sys
from html import escape

# eQUILIBRIUM viewer palette (BRG-teaching/Teaching, Equilibrium/drawings/web/lib/eqdraw.js)
EQ = {"compression": "#1a1eb2", "tension": "#ce4095", "load": "#3f9c20", "guide": "#aaaaaa",
      "zero": "#b9b9bd", "current": "#111111", "currentFace": "#e8e8e8", "edge": "#3c3f46",
      "redBand": "#f0bcdb", "blueBand": "#bdbfe8", "orange": "#e07a26", "amber": "#e8ac00",
      "text": "#27272a", "muted": "#71717a", "border": "#e4e4e7", "track": "#d4d4d8",
      "card": "#f7f8f9"}
STYLES = {"base": EQ["text"], "ray": EQ["guide"], "guide": EQ["guide"], "perp": EQ["guide"],
          "compression": EQ["compression"], "tension": EQ["tension"], "load": EQ["load"],
          "zero": EQ["zero"], "compression_band": EQ["blueBand"], "tension_band": EQ["redBand"],
          "q1": EQ["compression"], "q2": EQ["orange"], "q3": EQ["load"], "q4": EQ["tension"],
          "q5": EQ["amber"], "q6": "#2a9d8f", "resultant": EQ["load"], "string": EQ["text"],
          "dim": EQ["muted"], "q7": "#8c564b", "hatch": EQ["guide"]}
# House stroke metrics of the viewer (eqdraw.js `this.W`, ratios of the drawing frame, times
# LINE_SCALE 0.72), applied to our 380 px frame and enlarged by MAG so hairlines stay
# visible on a phone. Proportions between members, rays, dashes, arrows and disks are
# exactly the viewer's.
MAG = 1.75
_u = 380 * 0.72 * MAG
M = {"bar": 0.00316 * _u, "thin": 0.00150 * _u, "str": 0.00232 * _u, "ray": 0.00148 * _u,
     "dim": 0.00105 * _u, "dash": 0.00590 * 380 * MAG, "disk": 0.00740 * 380 * 0.72 * MAG,
     "arrow": tuple(1.6 * v for v in (0.00380 * _u, 0.01310 * _u, 0.00506 * _u))}
# arrow = shaft width, head length, head half-width: the viewer's ratios, 1.6 × larger so
# heads read at phone size (forces are the subject; they must not look like ticks)
WIDTH = {"base": M["bar"], "ray": M["ray"], "guide": M["ray"], "perp": M["thin"], "zero": M["thin"],
         "dim": M["dim"], "string": M["str"]}                       # quantities and forces: 1.5 × bar
DASHED = {"perp", "dim", "resultant"}   # guides, and resultants (dashed start to end, solid head)
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"
W, PAD, STEP_S, LAST_S, DRAW_S = 380, 34, 3.4, 6.0, 1.1
BEGIN = "0.4s"   # animations start a moment late: until then (and in any viewer that pauses or
                 # ignores SMIL) the static attributes show the finished construction


def wrap(text, n=54):
    lines, cur = [], ""
    for w in text.split():
        if len(cur) + len(w) + 1 > n and cur:
            lines.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + [cur] if cur else lines


class Scene:
    def __init__(self, spec):
        self.spec = spec
        self.progress = 1.0   # < 1 while rendering the draw-in frames of the WebP animation
        self.P = {k: tuple(v) for k, v in spec["points"].items()}
        self.colors = {**STYLES, **spec.get("styles", {})}
        xs, ys = [], []
        for st in spec["steps"]:
            for el in st["draw"]:
                for p in self.coords(el):
                    xs.append(p[0]); ys.append(p[1])
        xs += [p[0] for p in self.P.values()]; ys += [p[1] for p in self.P.values()]
        self.x0, self.y1 = min(xs), max(ys)
        self.s = (W - 2 * PAD) / ((max(xs) - self.x0) or 1)
        self.H = round((self.y1 - min(ys)) * self.s + 2 * PAD) + 14
        self.cap_lines = max(len(wrap(st["text"])) for st in spec["steps"])

    # ---- geometry ----
    def xy(self, p):
        return PAD + (p[0] - self.x0) * self.s, PAD + 14 + (self.y1 - p[1]) * self.s

    def pt(self, ref):
        return tuple(ref) if isinstance(ref, list) else self.P[ref]

    def coords(self, el):
        for k in ("seg", "line", "poly", "arrow"):
            if k in el:
                return [self.pt(r) for r in el[k]]
        if "pt" in el: return [self.P[r] for r in el["pt"]]
        if "path" in el: return [self.pt(r) for r in el["path"]]
        if "arc" in el:   # {"c": point, "r": radius, "from": deg, "to": deg}, counter-clockwise
            a = el["arc"]; cx, cy = self.pt(a["c"]); n = 48
            return [(cx + a["r"] * math.cos(math.radians(a["from"] + (a["to"] - a["from"]) * i / n)),
                     cy + a["r"] * math.sin(math.radians(a["from"] + (a["to"] - a["from"]) * i / n)))
                    for i in range(n + 1)]
        if "text" in el: return [tuple(el["at"])]
        if "ray" in el:
            (ax, ay), (bx, by) = self.pt(el["ray"][0]), self.pt(el["ray"][1])
            x = el.get("to_x", bx)
            return [(ax, ay), (x, ay + (by - ay) * (x - ax) / ((bx - ax) or 1e-9))]
        return []

    def check(self):
        """Verify the spec's geometric claims; return a list of failures."""
        bad, P = [], self.pt
        vec = lambda a, b: (P(b)[0] - P(a)[0], P(b)[1] - P(a)[1])
        length = lambda a, b: math.hypot(*vec(a, b))
        for c in self.spec.get("checks", []):
            (kind, args), = c.items()
            if kind == "collinear":
                (ux, uy), (vx, vy) = vec(args[0], args[1]), vec(args[0], args[2])
                err = abs(ux * vy - uy * vx) / ((math.hypot(ux, uy) * math.hypot(vx, vy)) or 1)
            elif kind in ("perp", "parallel"):
                (ux, uy), (vx, vy) = vec(*args[0]), vec(*args[1])
                n = (math.hypot(ux, uy) * math.hypot(vx, vy)) or 1
                err = abs(ux * vx + uy * vy) / n if kind == "perp" else abs(ux * vy - uy * vx) / n
            elif kind == "equal":
                a, b = length(*args[0]), length(*args[1])
                err = abs(a - b) / (max(a, b) or 1)
            elif kind == "area_equal":   # two polygons (point lists) with the same area
                area = lambda ps: abs(sum(P(u)[0] * P(v)[1] - P(v)[0] * P(u)[1]
                                          for u, v in zip(ps, ps[1:] + ps[:1]))) / 2
                a, b = area(args[0]), area(args[1])
                err = abs(a - b) / (max(a, b) or 1)
            elif kind == "value":
                a = length(*args[0])
                err = abs(a - args[1]) / (abs(args[1]) or 1)
            else:
                bad.append(f"unknown check {kind}"); continue
            if err > 2e-3:
                bad.append(f"{kind} {args}: off by {err:.4f}")
        return bad

    # ---- drawing ----
    def element(self, el, new, anim=None):
        """SVG for one element. anim = (t0, t1, T): draw the new line in between t0 and t1."""
        style = el.get("style", "ray" if "ray" in el else "load" if "arrow" in el
                       else "hatch" if "poly" in el else "base")
        c = self.colors.get(style, EQ["text"])
        ink = EQ["current"] if new else c          # the current step's additions are black
        out = []
        if "poly" in el:
            pts = " ".join("%.1f,%.1f" % self.xy(p) for p in self.coords(el))
            band = style.endswith("_band")
            if style == "hatch":    # equal-area / proof regions: grey fill, darker while current
                op = 0.55 if new else 0.32
            else:
                op = (0.9 if band else 0.3) if new else (0.75 if band else 0.14)
            out.append(f'<polygon points="{pts}" fill="{c}" fill-opacity="{op}" stroke="none"/>')
        elif "text" in el:
            x, y = self.xy(el["at"])
            out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{EQ["muted"]}" font-size="12">'
                       f'{escape(el["text"])}</text>')
        elif "pt" in el:
            if new and self.progress < 1:   # new points appear once their lines have arrived
                return out
            for name in el["pt"]:
                x, y = self.xy(self.P[name])
                dx, dy = self.spec.get("offsets", {}).get(name, [6, -6])
                r = M["disk"]   # viewer disk: dark outer circle, white face at 0.68 r
                out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="{EQ["current"] if new else EQ["edge"]}"/>'
                           f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r * 0.68:.2f}" '
                           f'fill="{EQ["currentFace"] if new else "#ffffff"}"/>')
                out.append(f'<text x="{x + dx:.1f}" y="{y + dy:.1f}" fill="{EQ["current"] if new else EQ["text"]}" '
                           f'font-weight="{700 if new else 400}">{escape(name)}</text>')
        elif "path" in el or "arc" in el:
            pts = [self.xy(p) for p in self.coords(el)]
            f = self.progress if new else 1.0
            if f < 1:   # raster draw-in: keep the first fraction f of the length
                seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
                left, keep = sum(seg) * f, [pts[0]]
                for (a, b), d in zip(zip(pts, pts[1:]), seg):
                    if left >= d:
                        keep.append(b); left -= d
                    else:
                        t = left / (d or 1); keep.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)); break
                pts = keep
            w = WIDTH.get(style, 1.5 * M["bar"]) * (1.35 if new else 1)
            dashed = style in DASHED
            dash = f' stroke-dasharray="{M["dash"]:.2f} {M["dash"] * 0.8:.2f}"' if dashed else ""
            ptxt = " ".join("%.1f,%.1f" % q for q in pts)
            attrs = (f'points="{ptxt}" fill="none" stroke="{ink}" stroke-width="{w:.2f}" '
                     f'stroke-linejoin="round"' + ("" if dashed else ' stroke-linecap="round"'))
            if new and anim and not dashed:
                t0, t1, T = anim
                ez = "0.42 0 0.58 1"
                vals, keys, spl = (("1;0;0", f"0;{t1:.4f};1", f"{ez};0 0 1 1") if t0 == 0 else
                                   ("1;1;0;0", f"0;{t0:.4f};{t1:.4f};1", f"0 0 1 1;{ez};0 0 1 1"))
                out.append(f'<polyline {attrs} pathLength="1" stroke-dasharray="1" stroke-dashoffset="0">'
                           f'<animate attributeName="stroke-dashoffset" values="{vals}" keyTimes="{keys}" '
                           f'calcMode="spline" keySplines="{spl}" dur="{T:.2f}s" begin="{BEGIN}" '
                           f'repeatCount="indefinite"/></polyline>')
            else:
                out.append(f'<polyline {attrs}{dash}/>')
            if el.get("label") and f >= 1:
                lx, ly = pts[-1] if el.get("label_at") == "end" else pts[len(pts) // 2]
                dx, dy = el.get("label_offset", [6, -6])
                out.append(f'<text x="{lx + dx:.1f}" y="{ly + dy:.1f}" fill="{ink}" '
                           f'font-style="italic" font-weight="700">{escape(el["label"])}</text>')
        else:
            (x1, y1), (x2, y2) = (self.xy(p) for p in self.coords(el))
            f = self.progress if new else 1.0     # raster animation: new lines grow from their first point
            if f < 1:
                x2, y2 = x1 + (x2 - x1) * f, y1 + (y2 - y1) * f
            arrow = "arrow" in el and f >= 1
            if arrow:   # viewer arrow: shaft stops at the head's base; head is a solid triangle
                aw, hl, hw = M["arrow"]
                L = math.hypot(x2 - x1, y2 - y1) or 1
                ux, uy = (x2 - x1) / L, (y2 - y1) / L
                hl = min(hl, 0.45 * L)
                bx, by = x2 - ux * hl, y2 - uy * hl
                head = (f'<polygon points="{x2:.1f},{y2:.1f} {bx - uy * hw:.1f},{by + ux * hw:.1f} '
                        f'{bx + uy * hw:.1f},{by - ux * hw:.1f}" fill="{EQ["current"] if new else self.colors.get(style, EQ["load"])}"/>')
                tipx, tipy = x2, y2
                x2, y2 = bx, by
            w = (M["arrow"][0] if arrow else WIDTH.get(style, 1.5 * M["bar"])) * (1.35 if new else 1)
            dashed = style in DASHED
            gap = M["dash"] * 0.8
            dash = f' stroke-dasharray="{M["dash"]:.2f} {gap:.2f}" stroke-linecap="butt"' if dashed else ""
            attrs = (f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{ink}" '
                     f'stroke-width="{w:.2f}"' + ("" if dashed else ' stroke-linecap="round"'))
            if new and anim and not dashed:   # draw the new line in, from its first point
                t0, t1, T = anim
                ez = "0.42 0 0.58 1"   # ease-in-out, like the WebP
                if t0 == 0:
                    vals, keys, spl = "1;0;0", f"0;{t1:.4f};1", f"{ez};0 0 1 1"
                else:
                    vals, keys, spl = "1;1;0;0", f"0;{t0:.4f};{t1:.4f};1", f"0 0 1 1;{ez};0 0 1 1"
                out.append(f'<line {attrs} pathLength="1" stroke-dasharray="1" stroke-dashoffset="0">'
                           f'<animate attributeName="stroke-dashoffset" values="{vals}" keyTimes="{keys}" '
                           f'calcMode="spline" keySplines="{spl}" dur="{T:.2f}s" begin="{BEGIN}" '
                           f'repeatCount="indefinite"/></line>')
            else:
                out.append(f'<line {attrs}{dash}/>')
            if arrow:
                out.append(head)
                x2, y2 = tipx, tipy
            if el.get("label"):
                at_end = el.get("label_at") == "end"
                lx, ly = (x2, y2) if at_end else ((x1 + x2) / 2, (y1 + y2) / 2)
                dx, dy = el.get("label_offset", [6, 5] if at_end else [6, -6])
                out.append(f'<text x="{lx + dx:.1f}" y="{ly + dy:.1f}" fill="{ink}" '
                           f'font-style="italic" font-weight="700">{escape(el["label"])}</text>')
        return out

    def frame(self, k, anim=None, caption=False):
        """Inner SVG for steps 0..k with step k highlighted. Polygons, then lines, then points."""
        layers = {"poly": [], "line": [], "pt": []}
        for i, st in enumerate(self.spec["steps"][: k + 1]):
            for el in st["draw"]:
                if el.get("until") and k + 1 >= el["until"]:   # retired from step "until" on
                    continue
                kind = "poly" if "poly" in el else "pt" if ("pt" in el or "text" in el) else "line"
                layers[kind] += self.element(el, i == k, anim if i == k else None)
        n = len(self.spec["steps"])
        head = (f'<text x="12" y="20" font-size="12" fill="{EQ["muted"]}">Step {k + 1} of {n}</text>'
                + "".join(f'<rect x="{W - 12 - (n - i) * 9:.0f}" y="12" width="6" height="6" rx="3" '
                          f'fill="{EQ["tension"] if i <= k else EQ["track"]}"/>' for i in range(n)))
        cap = ""
        if caption:
            y0 = self.H + 6
            cap = (f'<rect x="0" y="{y0 - 4}" width="{W}" height="{self.cap_lines * 18 + 14}" fill="{EQ["card"]}"/>'
                   f'<line x1="0" y1="{y0 - 4}" x2="{W}" y2="{y0 - 4}" stroke="{EQ["border"]}"/>'
                   + "".join(f'<text x="14" y="{y0 + 14 + i * 18}" font-size="13.5" fill="{EQ["text"]}">{escape(t)}</text>'
                             for i, t in enumerate(wrap(self.spec["steps"][k]["text"]))))
        return head + "".join(layers["poly"] + layers["line"] + layers["pt"]) + cap

    def svg(self, k):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {self.H}" width="{W}" '
                f'font-family="{FONT}" font-size="13.5">'
                f'<rect width="100%" height="100%" fill="#ffffff"/>{self.frame(k)}</svg>')

    def webp(self, path, scale=1.5, fps=24):
        """The same animation as a looping animated WebP (raster): for each step a few frames in
        which the new lines grow, then a hold with the step's text. For viewers that show
        images but don't run SVG animation."""
        import io
        import cairosvg
        from PIL import Image
        n = len(self.spec["steps"])
        Hc = self.H + self.cap_lines * 18 + 14
        frames, durations = [], []

        def render(k):
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {Hc}" width="{W}" height="{Hc}" '
                   f'font-family="{FONT}" font-size="13.5"><rect width="100%" height="100%" fill="#ffffff"/>'
                   f'{self.frame(k, caption=True)}</svg>')
            png = cairosvg.svg2png(bytestring=svg.encode(), scale=scale)
            return Image.open(io.BytesIO(png)).convert("RGB")

        draw_frames = max(2, round(DRAW_S * fps))
        ease = lambda t: t * t * (3 - 2 * t)     # smoothstep: lines start and land softly
        for k in range(n):
            for i in range(1, draw_frames + 1):
                self.progress = ease(i / draw_frames)
                frames.append(render(k))
                durations.append(round(1000 / fps))
            durations[-1] = int(((LAST_S if k == n - 1 else STEP_S) - DRAW_S) * 1000 + durations[-1])
        self.progress = 1.0
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations, loop=0,
                       lossless=False, quality=88, method=6, minimize_size=True, kmax=12)

    def animated(self):
        """All steps in one looping SVG: each frame visible in its time slot, new lines drawn in."""
        n = len(self.spec["steps"])
        dur = [STEP_S] * (n - 1) + [LAST_S]
        T = sum(dur)
        start = [sum(dur[:i]) for i in range(n)]
        Hc = self.H + self.cap_lines * 18 + 14
        frames = []
        for k in range(n):
            t0, t1 = start[k] / T, (start[k] + DRAW_S) / T
            end = (start[k] + dur[k]) / T
            if k == 0:
                vis = f'values="1;0" keyTimes="0;{end:.4f}"'
            elif k == n - 1:
                vis = f'values="0;1" keyTimes="0;{t0:.4f}"'
            else:
                vis = f'values="0;1;0" keyTimes="0;{t0:.4f};{end:.4f}"'
            frames.append(f'<g opacity="{1 if k == n - 1 else 0}"><animate attributeName="opacity" {vis} '
                          f'calcMode="discrete" dur="{T:.2f}s" begin="{BEGIN}" repeatCount="indefinite"/>'
                          f'{self.frame(k, anim=(t0, t1, T), caption=True)}</g>')
        # without SMIL support only the static opacity counts: the finished construction shows
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {Hc}" width="{W}" '
                f'font-family="{FONT}" font-size="13.5">'
                f'<rect width="100%" height="100%" fill="#ffffff"/>' + "".join(frames) + "</svg>")


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --bg:#ffffff; --ink:#27272a; --mute:#71717a; --line:#e4e4e7; --accent:#ce4095; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#16181d; --ink:#d5d7db; --mute:#8a8f98; --line:#33373f; --accent:#e06aae; }} }}
:root[data-theme="dark"] {{ --bg:#16181d; --ink:#d5d7db; --mute:#8a8f98; --line:#33373f; --accent:#e06aae; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:16px/1.55 'Helvetica Neue', Helvetica, Arial, sans-serif; -webkit-font-smoothing:antialiased; }}
main {{ max-width:560px; margin:0 auto; padding:20px 16px 40px; }}
h1 {{ font-size:21px; margin:0 0 2px; font-weight:500; }}
.src {{ color:var(--mute); font-size:14px; margin-bottom:14px; }}
.fig {{ border-radius:6px; overflow:hidden; border:1px solid var(--line); background:#fff; }}
.fig svg {{ display:block; width:100%; height:auto; }}
.step {{ min-height:5.4em; margin:12px 0 10px; }}
.step b {{ color:var(--accent); font-weight:500; font-size:13px; letter-spacing:.06em; text-transform:uppercase; }}
.bar {{ display:flex; gap:10px; align-items:center; }}
button {{ font:inherit; font-size:15px; padding:8px 14px; border-radius:4px; border:1px solid var(--mute);
  background:transparent; color:var(--ink); cursor:pointer; min-width:84px; }}
button:disabled {{ opacity:.35; cursor:default; }}
input[type=range] {{ flex:1; accent-color:var(--accent); }}
.note {{ color:var(--mute); font-size:13.5px; margin-top:16px; }}
</style></head>
<body><main>
<h1>{title}</h1><div class="src">{source}</div>
<div class="fig" id="fig"></div>
<div class="step" id="step"></div>
<div class="bar"><button id="prev">◀ Back</button><input type="range" id="slider" min="0" max="{last}" value="0"><button id="next">Next ▶</button></div>
<div class="note">{note} Arrow keys or swipe to step. Drawn from the text as a teaching aid; the original figure is in the book.</div>
</main>
<script>
const SVG = {svgs}, TEXT = {texts};
let k = 0;
const fig = document.getElementById('fig'), step = document.getElementById('step'),
      slider = document.getElementById('slider'), prev = document.getElementById('prev'), next = document.getElementById('next');
function show(i) {{
  k = Math.max(0, Math.min(SVG.length - 1, i));
  fig.innerHTML = SVG[k];
  step.innerHTML = '<b>Step ' + (k + 1) + ' of ' + SVG.length + '</b><br>' + TEXT[k];
  slider.value = k; prev.disabled = k === 0; next.disabled = k === SVG.length - 1;
}}
prev.onclick = () => show(k - 1); next.onclick = () => show(k + 1);
slider.oninput = () => show(+slider.value);
document.addEventListener('keydown', e => {{ if (e.key === 'ArrowRight') show(k + 1); if (e.key === 'ArrowLeft') show(k - 1); }});
let x0 = null;
fig.addEventListener('touchstart', e => {{ x0 = e.touches[0].clientX; }}, {{passive: true}});
fig.addEventListener('touchend', e => {{ if (x0 === null) return; const dx = e.changedTouches[0].clientX - x0;
  if (Math.abs(dx) > 40) show(k + (dx < 0 ? 1 : -1)); x0 = null; }});
show(0);
</script></body></html>
"""


def main(path, png=False, insert=False):
    spec_path = pathlib.Path(path).resolve()
    book = spec_path.parent.parent
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    sc, name, steps = Scene(spec), spec["name"], spec["steps"]
    bad = sc.check()
    if bad:
        sys.exit("geometry checks failed:\n  " + "\n  ".join(bad))
    out = book / "figures" / "steps"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob(f"{name}-s*.svg"):
        old.unlink()
    stills = [sc.svg(k) for k in range(len(steps))]
    for k, s in enumerate(stills):
        (out / f"{name}-s{k + 1:02d}.svg").write_text(s, encoding="utf-8")
    (out / f"{name}.svg").write_text(sc.animated(), encoding="utf-8")
    sc.webp(out / f"{name}.webp")
    page = PAGE.format(title=escape(spec["title"]), source=escape(spec["source"]),
                       note=escape(spec.get("note", "")), last=len(steps) - 1,
                       svgs=json.dumps(stills), texts=json.dumps([escape(st["text"]) for st in steps]))
    (spec_path.parent / f"{name}.html").write_text(page, encoding="utf-8")
    if png:
        import cairosvg
        prev = book.parent / "work" / "steps"
        prev.mkdir(parents=True, exist_ok=True)
        for k, s in enumerate(stills):
            cairosvg.svg2png(bytestring=s.encode(), write_to=str(prev / f"{name}-s{k + 1:02d}.png"), scale=1.5)

    blocks = markdown_blocks(spec)
    print(f"checks passed ({len(spec.get('checks', []))}); wrote {name}.svg (animated), "
          f"{len(steps)} stills and {name}.html")
    if insert:
        insert_blocks(book, spec, blocks)
    else:
        for where, md in blocks:
            print(f"\n--- {where}\n{md}")


def markdown_blocks(spec):
    """[(where, markdown)]: the animated drawing after the original figure, then each group of
    step stills right after the paragraph of the text that describes those steps."""
    name, steps = spec["name"], spec["steps"]
    tag = lambda what: (f"<!-- construction:{name} {what} -->", f"<!-- /construction:{name} -->")
    o, c = tag("animated")
    out = [(f"figure {spec.get('figure', '?')}",
            f'{o}\n<p align="center"><img src="figures/steps/{name}.webp" width="380" '
            f'alt="{escape(spec["title"])}: animated construction, {len(steps)} steps"><br>'
            f'<sub><b>{escape(spec["title"])}</b> · drawn step by step ({len(steps)} steps) · added drawing, '
            f'not in the original · {escape(spec.get("note", ""))} · '
            f'<a href="constructions/{name}.html">step through it</a> · '
            f'<a href="figures/steps/{name}.svg">sharp vector version</a></sub></p>\n{c}')]
    for g in spec.get("place", []):
        ks = g["steps"]
        o, c = tag(f"steps {ks[0]}-{ks[-1]}")
        w = 380 if len(ks) == 1 else 250
        imgs = " ".join(f'<img src="figures/steps/{name}-s{k:02d}.svg" width="{w}" '
                        f'alt="Step {k}: {escape(steps[k - 1]["text"])}">' for k in ks)
        label = f"Step {ks[0]}" if len(ks) == 1 else f"Steps {ks[0]}–{ks[-1]}"
        caps = " ".join(f"<b>{k}.</b> {escape(steps[k - 1]['text'])}" for k in ks)
        out.append((f"after the paragraph containing {g['after']!r}",
                    f'{o}\n<p align="center">{imgs}<br><sub><b>{label}</b> (added drawing) · {caps}</sub></p>\n{c}'))
    return out


def insert_blocks(book, spec, blocks):
    """Write the blocks into the chapter source: old blocks of this construction are removed
    first (so re-running is safe), then each block goes after its paragraph."""
    import re
    path = book / spec["chapter"]
    text = path.read_text(encoding="utf-8")
    name = spec["name"]
    text = re.sub(rf"\n*<!-- construction:{re.escape(name)} [^>]*-->.*?<!-- /construction:{re.escape(name)} -->",
                  "", text, flags=re.S)
    paras = re.split(r"(\n\s*\n)", text)          # keep the separators
    anchors = [spec["figure"]] + [g["after"] for g in spec.get("place", [])]
    for (where, md), anchor in zip(blocks, anchors):
        hits = [i for i in range(0, len(paras), 2) if anchor in paras[i]]
        if len(hits) != 1:
            sys.exit(f"anchor {anchor!r} found in {len(hits)} paragraphs of {path.name}; make it unique")
        paras[hits[0]] += "\n\n" + md
    path.write_text("".join(paras), encoding="utf-8")
    print(f"inserted {len(blocks)} blocks into {path.relative_to(book.parent)}; rebuild the chapter")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        sys.exit(__doc__)
    main(args[0], png="--png" in sys.argv, insert="--insert" in sys.argv)
