"""A small two-dimensional typesetter for display equations, in the spirit of SymPy's pretty printer:
fractions are stacked over a rule, sums and integrals carry their limits above and below, parentheses grow
with their content, accents sit on a line above, matrices are set in brackets.

        \\sum_j \\frac{s_j}{l_j} (x_k - x_i) + p_i = 0        →        sⱼ
                                                               ∑  ──  (xₖ − xᵢ) + pᵢ = 0
                                                               j  lⱼ

Returns None for anything it cannot parse, and the caller falls back to the one-line notation."""

from __future__ import annotations

import re
from dataclasses import dataclass

from brg_mcp.cli.mathtext import SYMBOLS

SUB = str.maketrans("0123456789+-=()aehijklmnoprstuvx", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ")
SUP = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
BINARY = set("=+<>") | {"−", "±", "∓", "×", "·", "≤", "≥", "≠", "≈", "≡", "→", "←", "⇒", "⇔", "∈", "∉", "⊂", "∼", "∝", "∪", "∩", "∧", "∨", "↦"}
BIG_OPS = {"sum": "∑", "prod": "∏", "int": "∫", "oint": "∮", "iint": "∬", "bigcup": "⋃", "bigcap": "⋂", "max": "max", "min": "min", "lim": "lim"}
FENCES = {"(": ("⎛", "⎜", "⎝"), ")": ("⎞", "⎟", "⎠"), "[": ("⎡", "⎢", "⎣"), "]": ("⎤", "⎥", "⎦"),
          "{": ("⎧", "⎨", "⎩"), "}": ("⎫", "⎬", "⎭"), "|": ("│", "│", "│"), "‖": ("║", "║", "║"), "": ("", "", "")}
FENCE_NAMES = {"lbrace": "{", "rbrace": "}", "{": "{", "}": "}", "|": "‖", "lvert": "|", "rvert": "|", "lVert": "‖", "rVert": "‖",
               "langle": "⟨", "rangle": "⟩", "lfloor": "⌊", "rfloor": "⌋", "lceil": "⌈", "rceil": "⌉", ".": ""}
MATRIX_FENCES = {"pmatrix": ("(", ")"), "bmatrix": ("[", "]"), "Bmatrix": ("{", "}"), "vmatrix": ("|", "|"), "Vmatrix": ("‖", "‖"),
                 "matrix": ("", ""), "cases": ("{", ""), "aligned": ("", ""), "gathered": ("", ""), "array": ("", ""), "split": ("", "")}
ACCENTS = {"bar": "‾", "overline": "‾", "hat": "^", "widehat": "^", "tilde": "~", "widetilde": "~", "vec": "→", "dot": "˙", "ddot": "¨"}
FONTS = {"mathbf", "mathrm", "mathsf", "mathit", "mathcal", "mathbb", "mathfrak", "boldsymbol", "bm", "operatorname", "mathop", "textbf", "textit"}


@dataclass
class Box:
    lines: list[str]
    baseline: int

    @property
    def width(self) -> int:
        return len(self.lines[0]) if self.lines else 0

    @property
    def height(self) -> int:
        return len(self.lines)


def atom(text: str) -> Box:
    return Box([text], 0)


def empty() -> Box:
    return Box([""], 0)


def pad_to(box: Box, above: int, below: int) -> list[str]:
    w = box.width
    return [" " * w] * (above - box.baseline) + box.lines + [" " * w] * (below - (box.height - box.baseline))


def hcat(boxes: list[Box], gaps: list[int] | None = None) -> Box:
    boxes = [b for b in boxes if b.width or b.height > 1] or [empty()]
    above = max(b.baseline for b in boxes)
    below = max(b.height - b.baseline for b in boxes)
    cols = [pad_to(b, above, below) for b in boxes]
    gaps = gaps or [1] * (len(boxes) - 1)
    lines = []
    for row in range(above + below):
        parts = []
        for i, col in enumerate(cols):
            if i:
                parts.append(" " * gaps[i - 1])
            parts.append(col[row])
        lines.append("".join(parts))
    return Box(lines, above)


def vstack(boxes: list[Box], baseline: int, align: str = "center") -> Box:
    w = max(b.width for b in boxes)
    lines = []
    for b in boxes:
        for line in b.lines:
            pad = w - len(line)
            if align == "center":
                left = pad // 2
            elif align == "left":
                left = 0
            else:
                left = pad
            lines.append(" " * left + line + " " * (pad - left))
    return Box(lines, baseline)


def center(box: Box, width: int) -> Box:
    pad = width - box.width
    left = pad // 2
    return Box([" " * left + l + " " * (pad - left) for l in box.lines], box.baseline)


# ------------------------------------------------------------------ parsing
Token = tuple[str, str, bool]          # kind, value, preceded by whitespace
_TOKEN = re.compile(r"(\s+)|\\([A-Za-z]+|[\\,;:!{}|(). ]|\[|\])|([{}^_&])|(\d+(?:\.\d+)?|[A-Za-z]+)|(.)", re.S)


def tokenize(tex: str) -> list[Token]:
    out: list[Token] = []
    space = False
    for m in _TOKEN.finditer(tex):
        ws, cmd, special, word, other = m.groups()
        if ws:
            space = True
            continue
        if cmd is not None:
            out.append(("cmd", cmd, space))
        elif special:
            out.append((special, special, space))
        elif word:
            out.append(("word", word, space))
        else:
            out.append(("char", other, space))
        space = False
    return out


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.t = tokens
        self.i = 0

    def peek(self) -> Token | None:
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self) -> Token:
        tok = self.t[self.i]
        self.i += 1
        return tok

    def group(self) -> Box:
        """A {…} group, or a single token, as a Box."""
        tok = self.peek()
        if tok is None:
            return empty()
        if tok[0] == "{":
            self.take()
            box = self.seq(lambda t: t[0] == "}")
            if not (self.peek() and self.peek()[0] == "}"):
                raise ValueError("unbalanced {")
            self.take()
            return box
        return self.base()

    def seq(self, stop) -> Box:
        """Items until `stop(token)`; spacing: binary operators get air, source whitespace becomes a gap."""
        boxes: list[Box] = []
        gaps: list[int] = []
        kinds: list[str] = []
        while True:
            tok = self.peek()
            if tok is None or stop(tok):
                break
            if tok[0] == "}":
                raise ValueError("unbalanced }")
            box, kind = self.item_with_kind()
            if kind == "binary" and box.lines[0] in ("−", "+", "±", "∓") and (not boxes or kinds[-1] == "binary"):
                kind = "unary"                                  # a sign, not an operation: no air after it
            if boxes:
                prev_kind = kinds[-1]
                if prev_kind == "unary":
                    gap = 0
                elif kind == "binary" or prev_kind == "binary":
                    gap = 1
                elif prev_kind == "comma":
                    gap = 1
                elif kind == "comma":
                    gap = 0
                else:
                    gap = 1 if tok[2] else 0
                gaps.append(gap)
            boxes.append(box)
            kinds.append(kind)
        if not boxes:
            return empty()
        return hcat(boxes, gaps)

    def item_with_kind(self) -> tuple[Box, str]:
        tok = self.peek()
        box = self.item()
        text = box.lines[box.baseline] if box.height == 1 else ""
        if box.height == 1 and text in BINARY:
            return box, "binary"
        if box.height == 1 and text in (",", ";"):
            return box, "comma"
        return box, ("word" if tok and tok[0] in ("word", "cmd") else "other")

    def item(self) -> Box:
        box = self.base()
        sub = sup = None
        while self.peek() and self.peek()[0] in ("^", "_"):
            mark = self.take()[0]
            arg = self.group()
            if mark == "^":
                sup = arg
            else:
                sub = arg
        if sub is None and sup is None:
            return box
        if box.height == 1 and box.lines[0] in BIG_OPS.values():
            return limits(box, sub, sup)
        return scripts(box, sub, sup)

    def base(self) -> Box:
        kind, value, _ = self.take()
        if kind == "{":
            box = self.seq(lambda t: t[0] == "}")
            if not (self.peek() and self.peek()[0] == "}"):
                raise ValueError("unbalanced {")
            self.take()
            return box
        if kind == "word":
            return atom(value)
        if kind == "char":
            if value in "([":
                closer = ")" if value == "(" else "]"
                start = self.i
                try:
                    body = self.seq(lambda t: t[0] == "char" and t[1] == closer)
                    if self.peek() and self.peek()[1] == closer:
                        self.take()
                        return fence(value, body, closer)
                except ValueError:
                    pass
                self.i = start
                return atom(value)
            if value == "-":
                return atom("−")
            if value == "*":
                return atom("·")
            if value == "'":
                return atom("′")
            return atom(value)
        if kind == "cmd":
            return self.command(value)
        if kind == "&":
            return atom(" ")
        raise ValueError(f"unexpected {kind}")

    def command(self, name: str) -> Box:
        if name in ("frac", "dfrac", "tfrac"):
            return frac(self.group(), self.group())
        if name == "sqrt":
            index = None
            if self.peek() and self.peek()[0] == "char" and self.peek()[1] == "[":
                self.take()
                index = self.seq(lambda t: t[0] == "char" and t[1] == "]")
                self.take()
            return sqrt(self.group(), index)
        if name in BIG_OPS:
            return atom(BIG_OPS[name])
        if name in ("left", "right"):
            opener = self.take()
            open_char = FENCE_NAMES.get(opener[1], opener[1]) if opener[0] in ("cmd", "char") else "("
            if name == "right":
                raise ValueError("stray \\right")
            body = self.seq(lambda t: t[0] == "cmd" and t[1] == "right")
            self.take()
            closer = self.take()
            close_char = FENCE_NAMES.get(closer[1], closer[1])
            return fence(open_char, body, close_char)
        if name in ("bigl", "bigr", "Bigl", "Bigr", "big", "Big", "biggl", "biggr", "limits", "nolimits", "displaystyle", "textstyle"):
            return self.base() if self.peek() and name.endswith(("l", "r", "g")) and self.peek()[0] == "char" else empty()
        if name in FONTS:
            return self.group()
        if name in ("text", "textrm", "mbox"):
            tok = self.peek()
            if tok and tok[0] == "{":
                depth, j, words = 0, self.i, []
                while j < len(self.t):
                    k, v, sp = self.t[j]
                    if k == "{":
                        depth += 1
                    elif k == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    else:
                        words.append((" " if sp else "") + v)
                    j += 1
                self.i = j + 1
                return atom("".join(words).strip())
            return self.group()
        if name in ACCENTS:
            return accent(self.group(), ACCENTS[name])
        if name in ("underline",):
            body = self.group()
            return Box(body.lines + ["‾" * body.width], body.baseline)
        if name == "begin":
            env = self.env_name()
            return self.matrix(env)
        if name == "end":
            raise ValueError("stray \\end")
        if name in (",", ";", ":", "quad", "qquad", " "):
            return atom(" ")
        if name in ("!",):
            return empty()
        if name == "\\":
            raise ValueError("row break")
        if name in FENCE_NAMES:
            return atom(FENCE_NAMES[name])
        if name in ("top", "intercal", "transpose"):
            return atom("T")
        if name in SYMBOLS:
            return atom(SYMBOLS[name])
        if name in ("cdot",):
            return atom("·")
        return atom(name)

    def env_name(self) -> str:
        tok = self.take()
        if tok[0] != "{":
            raise ValueError("\\begin without a name")
        name = ""
        while self.peek() and self.peek()[0] != "}":
            name += self.take()[1]
        self.take()
        return name.rstrip("*")

    def matrix(self, env: str) -> Box:
        rows: list[list[Box]] = [[]]
        while True:
            tok = self.peek()
            if tok is None:
                raise ValueError("unterminated matrix")
            if tok[0] == "cmd" and tok[1] == "end":
                self.take()
                self.env_name()
                break
            cell = self.seq(lambda t: (t[0] == "&") or (t[0] == "cmd" and t[1] in ("\\", "end")))
            rows[-1].append(cell)
            nxt = self.peek()
            if nxt and nxt[0] == "&":
                self.take()
            elif nxt and nxt[0] == "cmd" and nxt[1] == "\\":
                self.take()
                rows.append([])
        rows = [r for r in rows if any(c.width for c in r)]
        open_char, close_char = MATRIX_FENCES.get(env, ("", ""))
        return matrix(rows, open_char, close_char, align_left=env in ("aligned", "cases", "split", "gathered"))


# ------------------------------------------------------------------ constructions
def frac(num: Box, den: Box) -> Box:
    w = max(num.width, den.width) + 2
    return Box(center(num, w).lines + ["─" * w] + center(den, w).lines, num.height)


def sqrt(body: Box, index: Box | None = None) -> Box:
    w = body.width
    top = " " + "‾" * (w + 1)
    lines = [top] + [("√" if i == body.baseline else " ") + " " + line for i, line in enumerate(body.lines)]
    box = Box([l.ljust(w + 2) for l in lines], body.baseline + 1)
    if index is not None and index.height == 1:
        return hcat([atom(index.lines[0].translate(SUP)), box], [0])
    return box


def fence(open_char: str, body: Box, close_char: str) -> Box:
    if body.height == 1:
        return Box([open_char + body.lines[0] + close_char], 0)
    def column(ch: str) -> Box:
        if ch in FENCES:
            top, mid, bottom = FENCES[ch]
            lines = [top] + [mid] * (body.height - 2) + [bottom]
            if ch in "{}":
                lines[body.baseline] = "⎨" if ch == "{" else "⎬"
            return Box(lines, body.baseline)
        return Box([ch if i == body.baseline else " " * len(ch) for i in range(body.height)], body.baseline)
    parts = [column(open_char)] if open_char else []
    parts.append(body)
    if close_char:
        parts.append(column(close_char))
    return hcat(parts, [0] * (len(parts) - 1))


def limits(op: Box, lower: Box | None, upper: Box | None) -> Box:
    parts = ([upper] if upper else []) + [op] + ([lower] if lower else [])
    baseline = (upper.height if upper else 0)
    return vstack(parts, baseline)


def scripts(base: Box, sub: Box | None, sup: Box | None) -> Box:
    out = base
    if sub is not None:
        text = sub.lines[0] if sub.height == 1 else None
        if text is not None and all(c in "0123456789+-=()aehijklmnoprstuvx ,·" for c in text):
            out = hcat([out, atom(text.translate(SUB))], [0])
        else:
            # lowered: the subscript hangs below the baseline, to the right
            w = out.width
            lines = pad_to(out, out.baseline, out.height - out.baseline) + [" " * w] * sub.height
            for k, line in enumerate(sub.lines):
                lines[out.height + k] = " " * w + line
            lines = [l.ljust(w + sub.width) for l in lines]
            out = Box(lines, out.baseline)
    if sup is not None:
        text = sup.lines[0] if sup.height == 1 else None
        if text is not None and (text == "°" or all(c in "0123456789+-=()n" for c in text)):
            out = hcat([out, atom(text.translate(SUP))], [0])
        else:
            w = out.width
            top = [" " * w + line for line in sup.lines]
            lines = top + out.lines
            lines = [l.ljust(w + sup.width) for l in lines]
            out = Box(lines, out.baseline + sup.height)
    return out


def accent(body: Box, mark: str) -> Box:
    w = body.width
    if mark == "‾":
        top = "‾" * w
    else:
        top = center(atom(mark), w).lines[0]
    return Box([top] + body.lines, body.baseline + 1)


def matrix(rows: list[list[Box]], open_char: str, close_char: str, align_left: bool = False) -> Box:
    if not rows:
        return empty()
    ncols = max(len(r) for r in rows)
    widths = [max((r[c].width for r in rows if c < len(r)), default=0) for c in range(ncols)]
    row_boxes = []
    for r in rows:
        cells = []
        for c in range(ncols):
            cell = r[c] if c < len(r) else empty()
            pad = widths[c] - cell.width
            cells.append(Box([(l + " " * pad) if align_left else (" " * (pad // 2) + l + " " * (pad - pad // 2)) for l in cell.lines], cell.baseline))
        row_boxes.append(hcat(cells, [2] * (ncols - 1)))
    body = vstack(row_boxes, 0, align="left")
    body.baseline = body.height // 2 if body.height > 1 else 0
    return fence(open_char, body, close_char) if (open_char or close_char) else body


# ------------------------------------------------------------------ entry point
def typeset(tex: str) -> list[str] | None:
    """The display equation as lines of equal length, or None when it cannot be parsed."""
    try:
        rows = re.split(r"\\\\(?![^{]*\})", tex.strip()) if not re.search(r"\\begin\{", tex) else [tex.strip()]
        boxes = []
        for row in rows:
            if not row.strip():
                continue
            parser = Parser(tokenize(row))
            box = parser.seq(lambda t: False)
            if parser.peek() is not None:
                return None
            boxes.append(box)
        if not boxes:
            return None
        if len(boxes) == 1:
            box = boxes[0]
        else:
            box = vstack(boxes, 0, align="left")
        lines = [l.rstrip() for l in box.lines]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return lines or None
    except (ValueError, IndexError, RecursionError):
        return None
