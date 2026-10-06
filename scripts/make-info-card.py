"""Render config/profile.json as dark + light profile card SVGs."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib import config, svg
from lib.config import Profile, Row
from lib.theme import DARK, LIGHT, Theme

WIDTH = 860
PAD_X = 32
PAD_Y = 22
LABEL_W = 148
LABEL_SIZE = 11
VALUE_SIZE = 14
ROW_H = 30
SEP_H = 25
STAGGER_S = 0.05
OUTPUTS = ((DARK, "info-card.svg"), (LIGHT, "info-card-light.svg"))


@dataclass(frozen=True)
class Line:
    """One rendered line: a row (label empty on wrapped continuations) or a separator."""

    kind: str  # "row" | "sep"
    label: str = ""
    value: str = ""

    @property
    def height(self) -> int:
        return SEP_H if self.kind == "sep" else ROW_H


def wrap(text: str, max_chars: int) -> list[str]:
    """Greedy word wrap; tokens longer than max_chars are hard-broken."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        while len(word) > max_chars:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:max_chars])
            word = word[max_chars:]
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def layout(profile: Profile) -> list[Line]:
    max_chars = int((WIDTH - 2 * PAD_X - LABEL_W) / (VALUE_SIZE * svg.SANS_CHAR_RATIO))
    lines: list[Line] = []
    for entry in profile.rows:
        if not isinstance(entry, Row):
            lines.append(Line("sep"))
            continue
        for j, chunk in enumerate(wrap(entry.value, max_chars)):
            lines.append(Line("row", label=entry.key.upper() if j == 0 else "", value=chunk))
    return lines


def render_line(line: Line, top: float, theme: Theme) -> str:
    if line.kind == "sep":
        mid = top + SEP_H / 2
        return (
            f'<line x1="{PAD_X}" y1="{svg.fmt(mid)}" x2="{WIDTH - PAD_X}" y2="{svg.fmt(mid)}" '
            f'stroke="{theme.border}"/>'
        )
    baseline = top + ROW_H / 2 + VALUE_SIZE * 0.35
    parts = []
    if line.label:
        parts.append(
            f'<text x="{PAD_X}" y="{svg.fmt(baseline)}" fill="{theme.muted}" font-size="{LABEL_SIZE}" '
            f'font-weight="600" letter-spacing="0.08em">{svg.esc(line.label)}</text>'
        )
    parts.append(
        f'<text x="{PAD_X + LABEL_W}" y="{svg.fmt(baseline)}" fill="{theme.fg}" '
        f'font-size="{VALUE_SIZE}">{svg.esc(line.value)}</text>'
    )
    return "".join(parts)


def render(profile: Profile, theme: Theme) -> str:
    lines = layout(profile)
    height = 2 * PAD_Y + sum(l.height for l in lines)
    body = [
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="6" '
        f'fill="{theme.bg}" stroke="{theme.border}"/>',
        f'<g font-family="{svg.SANS_STACK}">',
    ]
    top = PAD_Y
    for n, line in enumerate(lines):
        body.append(f'<g class="r r{n}">{render_line(line, top, theme)}</g>')
        top += line.height
    body.append("</g>")

    style = (
        ".r{opacity:0;animation:in .5s ease-out forwards}"
        "@keyframes in{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}"
        + "".join(f".r{n}{{animation-delay:{n * STAGGER_S:.2f}s}}" for n in range(1, len(lines)))
    )
    return svg.svg_root(WIDTH, height, "\n".join(body), style=style, title=profile.title)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=config.repo_path("assets"))
    args = parser.parse_args()

    profile = config.load_profile()
    sizes = [
        f"{name} {svg.write_svg(args.out_dir / name, render(profile, theme)) / 1024:.1f} KB"
        for theme, name in OUTPUTS
    ]
    print(f"wrote {', '.join(sizes)} ({svg.mode_label()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
