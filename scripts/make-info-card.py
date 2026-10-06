"""Render config/profile.json as dark + light profile card SVGs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib import config, svg
from lib.config import Card
from lib.theme import DARK, LIGHT, Theme

WIDTH = 860
PAD = 32
LEFT_W = 252
DIVIDER_X = PAD + LEFT_W + 28
RIGHT_X = DIVIDER_X + 28
RIGHT_W = WIDTH - PAD - RIGHT_X

HEADLINE_SIZE = 22
ORG_SIZE = 15
BODY_SIZE = 13
LABEL_SIZE = 10.5
BODY_LINE_H = 19

STACK_SIZE = 14
STACK_LINE_H = 22
STACK_SEP = " · "
GROUP_GAP = 18
STAGGER_S = 0.06
OUTPUTS = ((DARK, "info-card.svg"), (LIGHT, "info-card-light.svg"))


def wrap(text: str, max_w: float, size: float) -> list[str]:
    """Greedy word wrap by estimated pixel width; deterministic for a given input."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}" if current else word
        if not current or svg.text_width(candidate, size) <= max_w:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def join_items(items: tuple[str, ...], max_w: float, size: float) -> list[str]:
    """Join items with STACK_SEP, breaking lines only between items."""
    lines: list[str] = []
    for item in items:
        candidate = f"{lines[-1]}{STACK_SEP}{item}" if lines else item
        if lines and svg.text_width(candidate, size) <= max_w:
            lines[-1] = candidate
        else:
            lines.append(item)
    return lines


def text(x: float, y: float, s: str, fill: str, size: float, extra: str = "") -> str:
    return (
        f'<text x="{svg.fmt(x)}" y="{svg.fmt(y)}" fill="{fill}" font-size="{svg.fmt(size)}"{extra}>'
        f"{svg.esc(s)}</text>"
    )


def label(x: float, y: float, s: str, theme: Theme) -> str:
    return text(x, y, s.upper(), theme.muted, LABEL_SIZE, ' font-weight="600" letter-spacing="0.09em"')


def left_column(card: Card, theme: Theme) -> tuple[list[str], float]:
    """Identity block + facts. Returns (groups, bottom y)."""
    groups = []
    y = PAD + HEADLINE_SIZE
    groups.append(text(PAD, y, card.headline, theme.fg, HEADLINE_SIZE, ' font-weight="600"'))
    y += 26
    groups.append(text(PAD, y, card.organization, theme.fg, ORG_SIZE))
    y += 8
    summary = []
    for line in wrap(card.summary, LEFT_W, BODY_SIZE):
        y += BODY_LINE_H
        summary.append(text(PAD, y, line, theme.muted, BODY_SIZE))
    groups.append("".join(summary))

    y += 14
    for fact in card.facts:
        y += 24
        parts = [label(PAD, y, fact.key, theme)]
        for line in wrap(fact.value, LEFT_W, BODY_SIZE):
            y += BODY_LINE_H
            parts.append(text(PAD, y, line, theme.fg, BODY_SIZE))
        groups.append("".join(parts))
    return groups, y


def right_column(card: Card, theme: Theme, gap: float = GROUP_GAP) -> tuple[list[str], float]:
    """Stack groups as a label over plain-text items. Returns (groups, bottom y)."""
    groups = []
    y = PAD
    for i, group in enumerate(card.stack):
        if i:
            y += gap
        y += LABEL_SIZE
        parts = [label(RIGHT_X, y, group.key, theme)]
        for line in join_items(group.items, RIGHT_W, STACK_SIZE):
            y += STACK_LINE_H
            parts.append(text(RIGHT_X, y, line, theme.fg, STACK_SIZE))
        groups.append("".join(parts))
    return groups, y


def render(profile: config.Profile, theme: Theme) -> str:
    left, left_bottom = left_column(profile.card, theme)
    right, right_bottom = right_column(profile.card, theme)
    target = left_bottom + 6
    if right_bottom < target and len(profile.card.stack) > 1:
        # Spread stack groups so both columns end on the same line.
        gap = GROUP_GAP + (target - right_bottom) / (len(profile.card.stack) - 1)
        right, right_bottom = right_column(profile.card, theme, gap)
    height = round(max(target, right_bottom) + PAD)

    body = [
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="6" '
        f'fill="{theme.bg}" stroke="{theme.border}"/>',
        f'<line x1="{DIVIDER_X}" y1="{PAD}" x2="{DIVIDER_X}" y2="{height - PAD}" stroke="{theme.border}"/>',
        f'<g font-family="{svg.SANS_STACK}">',
    ]
    # Left column reveals first, then the stack groups.
    for n, group in enumerate(left + right):
        body.append(f'<g class="r r{n}">{group}</g>')
    body.append("</g>")

    count = len(left) + len(right)
    style = (
        ".r{opacity:0;animation:in .5s ease-out forwards}"
        "@keyframes in{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}"
        + "".join(f".r{n}{{animation-delay:{n * STAGGER_S:.2f}s}}" for n in range(1, count))
    )
    title = f"{profile.card.headline}, {profile.card.organization}"
    return svg.svg_root(WIDTH, height, "\n".join(body), style=style, title=title)


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
