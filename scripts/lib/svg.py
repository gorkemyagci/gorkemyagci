"""Shared SVG helpers: escaping, root element, font stack, static-mode flag."""

from __future__ import annotations

import os
from pathlib import Path
from xml.sax.saxutils import escape

SANS_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"

# Upper-bound estimate of average sans glyph advance relative to font-size.
SANS_CHAR_RATIO = 0.56

# Approximate Helvetica/SF advance widths (em) for per-string measurement.
_NARROW = set("iljI.,:;'!|")
_SEMI = set("ftr()[]- /")
_WIDE = set("mwMW@")


def _advance(ch: str) -> float:
    if ch in _NARROW:
        return 0.26
    if ch in _SEMI:
        return 0.34
    if ch in _WIDE:
        return 0.86
    if ch.isupper():
        return 0.68
    return 0.55


def text_width(text: str, size: float) -> float:
    """Estimated rendered width of sans text; slightly generous so content never overflows."""
    return sum(_advance(c) for c in text) * size


def esc(text: str) -> str:
    return escape(text, {'"': "&quot;"})


def is_static() -> bool:
    return os.environ.get("STATIC") == "1"


def fmt(n: float) -> str:
    """Compact number formatting for attributes."""
    return f"{n:.2f}".rstrip("0").rstrip(".")


def svg_root(width: float, height: float, body: str, style: str = "", title: str = "") -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(width)}" height="{fmt(height)}" '
        f'viewBox="0 0 {fmt(width)} {fmt(height)}" role="img">'
    ]
    if title:
        parts.append(f"<title>{esc(title)}</title>")
    if style and not is_static():
        parts.append(f"<style>{style}</style>")
    parts.append(body)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def write_svg(path: Path, content: str) -> int:
    """Write UTF-8 SVG and return its size in bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path.stat().st_size


def mode_label() -> str:
    return "static" if is_static() else "animated"
