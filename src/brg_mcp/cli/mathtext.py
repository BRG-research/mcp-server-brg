"""Equations in the terminal, written the way an engineer writes them in plain text (or in Typst):

    \\mathbf{C}^T \\mathbf{Q} \\mathbf{C} \\mathbf{x} = \\mathbf{p}   →   C^T Q C x = p
    \\alpha_{max} \\le 30^\\circ                                    →   α_max ≤ 30°
    H = \\frac{w L^2}{8 f}                                          →   H = (w L²)/(8 f)
    \\bar{C}, \\hat{x}, \\sqrt{a + b}                               →   bar(C), hat(x), √(a + b)

Unicode is used only for glyphs every monospace font has: Greek letters, operators (≤ ≥ ≠ ± × · ∑ ∫ ∂ ∇ ∞ →),
and digit exponents (², ⁻¹).  Sub- and superscripts stay as `_i` and `^T`, bold vectors are plain letters:
the tiny Unicode letters and combining accents render badly in terminals, so they are not used.

Inline math `$...$` becomes an inline code span, which keeps Markdown from treating `_` and `*` as emphasis
and shows the expression in the code colour.  Display math (`$$...$$`, `\\[...\\]`) is set on its own line
with a bar, as a block of its own (see `blocks`)."""

from __future__ import annotations

import re

SYMBOLS = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "varepsilon": "ε", "zeta": "ζ", "eta": "η",
    "theta": "θ", "vartheta": "ϑ", "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π",
    "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ", "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ",
    "Omega": "Ω",
    "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠", "approx": "≈", "equiv": "≡", "sim": "∼",
    "propto": "∝", "pm": "±", "mp": "∓", "times": "×", "cdot": "·", "div": "÷", "ast": "∗", "star": "⋆",
    "sum": "∑", "prod": "∏", "int": "∫", "oint": "∮", "partial": "∂", "nabla": "∇", "infty": "∞",
    "to": "→", "rightarrow": "→", "Rightarrow": "⇒", "leftarrow": "←", "Leftarrow": "⇐", "leftrightarrow": "↔",
    "Leftrightarrow": "⇔", "mapsto": "↦", "in": "∈", "notin": "∉", "subset": "⊂", "subseteq": "⊆", "cup": "∪",
    "cap": "∩", "forall": "∀", "exists": "∃", "emptyset": "∅", "cdots": "⋯", "ldots": "…", "dots": "…",
    "vdots": "⋮", "circ": "°", "degree": "°", "prime": "′", "angle": "∠", "perp": "⊥", "parallel": "∥",
    "langle": "⟨", "rangle": "⟩", "lfloor": "⌊", "rfloor": "⌋", "lceil": "⌈", "rceil": "⌉", "mid": "|",
    "|": "‖", "lVert": "‖", "rVert": "‖", "lvert": "|", "rvert": "|", "neg": "¬", "lnot": "¬", "land": "∧", "lor": "∨",
    "top": "T", "intercal": "T", "transpose": "T",
}
SUPERSCRIPT_DIGITS = str.maketrans("0123456789-+()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺⁽⁾")
_FRAC = re.compile(r"\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}")
_ACCENT = re.compile(r"\\(bar|overline|hat|widehat|tilde|widetilde|vec|dot|ddot|underline)\s*\{([^{}]*)\}")
_ACCENT1 = re.compile(r"\\(bar|hat|tilde|vec|dot|ddot)\s*([A-Za-z])")
_FONT = re.compile(r"\\(?:mathbf|mathrm|mathsf|mathit|mathcal|mathbb|mathfrak|boldsymbol|bm|text|textrm|textbf|textit|operatorname|mathop)\s*\{([^{}]*)\}")
_FONT1 = re.compile(r"\\(?:mathbf|mathrm|mathsf|mathit|mathcal|mathbb|boldsymbol|bm)\s+([A-Za-z])")
_SQRT = re.compile(r"\\sqrt\s*(?:\[([^\]]*)\])?\s*\{([^{}]*)\}")
_SCRIPT = re.compile(r"([\^_])\s*\{([^{}]*)\}")
_CMD = re.compile(r"\\([A-Za-z]+|\|)")


def _simple(s: str) -> bool:
    """A token that needs no parentheses when it becomes a numerator, denominator or script."""
    return re.fullmatch(r"[\w°′.]+(\^[\w°]+|²|³|⁻¹)?", s) is not None


def _frac(m: re.Match) -> str:
    a, b = m.group(1).strip(), m.group(2).strip()
    return f"{a if _simple(a) else f'({a})'}/{b if _simple(b) else f'({b})'}"


def _script(m: re.Match) -> str:
    mark, body = m.group(1), re.sub(r"\s*([=+\-])\s*", r"\1", m.group(2).strip())
    if mark == "^" and re.fullmatch(r"[-+]?\d+", body):
        return body.translate(SUPERSCRIPT_DIGITS)
    body = body.replace("\\top", "T").replace("\\mathsf{T}", "T").replace("\\mathsf T", "T").replace("\\intercal", "T")
    return f"{mark}{body}" if _simple(body) else f"{mark}({body})"


def tex_to_plain(tex: str) -> str:
    """One TeX math expression → plain engineering notation."""
    s = tex.strip()
    s = re.sub(r"\\begin\{[bpvB]?matrix\}(.*?)\\end\{[bpvB]?matrix\}",
               lambda m: "[" + " ; ".join(" ".join(c.strip() for c in row.split("&")) for row in m.group(1).split("\\\\")) + "]",
               s, flags=re.S)
    s = re.sub(r"\\begin\{[a-z*]+\}|\\end\{[a-z*]+\}", " ", s)
    s = s.replace("\\\\", " ; ").replace("&", " ")
    s = re.sub(r"\\(?:left|right|bigl|bigr|big|Big|Bigl|Bigr)\s*", "", s)
    s = re.sub(r"\\[,;:!]|\\quad|\\qquad|~", " ", s)
    for _ in range(3):                        # inner constructs first
        s2 = _SQRT.sub(lambda m: (f"{m.group(1)}√" if m.group(1) else "√") + f"({m.group(2).strip()})", s)
        s2 = _FRAC.sub(_frac, s2)
        s2 = _ACCENT.sub(lambda m: f"{m.group(1).replace('overline', 'bar').replace('widehat', 'hat').replace('widetilde', 'tilde')}({m.group(2).strip()})", s2)
        s2 = _ACCENT1.sub(lambda m: f"{m.group(1)}({m.group(2)})", s2)
        s2 = _FONT.sub(r"\1", s2)
        s2 = _FONT1.sub(r"\1", s2)
        if s2 == s:
            break
        s = s2
    s = re.sub(r"\^\\circ", "°", s)
    s = _CMD.sub(lambda m: SYMBOLS.get(m.group(1), m.group(1)), s)
    s = re.sub(r"\s*([=≤≥≠≈±→])\s*", r" \1 ", s)              # air around relations (outside scripts)
    s = _SCRIPT.sub(_script, s)                                 # scripts keep their bodies compact
    s = re.sub(r"\^([-+]?\d)", lambda m: m.group(1).translate(SUPERSCRIPT_DIGITS), s)
    s = s.replace("{", "").replace("}", "").replace("*", "∗")
    s = re.sub(r"(/[\w)²³⁻¹]+)(?=[∑∏∫√(A-Za-zα-ωΑ-Ω])", r"\1 ", s)   # a fraction followed by a term: a space
    return re.sub(r"[ ]{2,}", " ", s).strip()


_DISPLAY = re.compile(r"(?<!\\)\$\$(.+?)\$\$|\\\[(.+?)\\\]", re.S)
_INLINE = re.compile(r"(?<![\\$\w])\$(?!\s)((?:[^$\n]|\\\$)+?)(?<!\s)\$(?!\w)")
_FENCE = re.compile(r"(```.*?```|`[^`\n]*`)", re.S)
_INLINE_PAREN = re.compile(r"\\\((.+?)\\\)")


def mathify(markdown: str) -> str:
    """Inline TeX in a Markdown text → plain notation in an inline code span, outside code spans and fences.
    Display math is left for `blocks`.  Only complete pairs are touched, so a text still streaming is safe."""
    parts = _FENCE.split(markdown)
    for i in range(0, len(parts), 2):
        text = parts[i]
        text = _INLINE.sub(lambda m: "`" + tex_to_plain(m.group(1)) + "`", text)
        text = _INLINE_PAREN.sub(lambda m: "`" + tex_to_plain(m.group(1)) + "`", text)
        parts[i] = text
    return "".join(parts)


def blocks(markdown: str) -> list[tuple[str, str]]:
    """Split a Markdown text into ("md", text) and ("eq", TeX of a display equation) pieces, display math
    on its own, code fences untouched."""
    out: list[tuple[str, str]] = []
    parts = _FENCE.split(markdown)
    for i, part in enumerate(parts):
        if i % 2 == 1:                                   # a code span or fence: Markdown as is
            out.append(("md", part))
            continue
        pos = 0
        for m in _DISPLAY.finditer(part):
            if m.start() > pos:
                out.append(("md", part[pos:m.start()]))
            out.append(("eq", (m.group(1) or m.group(2)).strip()))
            pos = m.end()
        if pos < len(part):
            out.append(("md", part[pos:]))
    # merge adjacent md pieces
    merged: list[tuple[str, str]] = []
    for kind, text in out:
        if merged and kind == "md" and merged[-1][0] == "md":
            merged[-1] = ("md", merged[-1][1] + text)
        else:
            merged.append((kind, text))
    return [(k, t) for k, t in merged if k == "eq" or t.strip()]
