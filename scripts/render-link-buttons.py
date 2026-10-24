"""Render the README contact links as dark + light pill-button SVGs."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib import config, svg
from lib.theme import DARK, LIGHT, Theme

HEIGHT = 36
RADIUS = 6
PAD_X = 16
ICON = 16
ICON_GAP = 8
ARROW = 9
ARROW_GAP = 8
FONT_SIZE = 13
# Figure for mixed-case labels at 13px semibold; svg.SANS_CHAR_RATIO is a looser upper bound.
CHAR_RATIO = 0.58
STROKE = 1.5


def _icon(kind: str, color: str) -> str:
    s = f'fill="none" stroke="{color}" stroke-width="{STROKE}" stroke-linecap="round" stroke-linejoin="round"'
    if kind == "globe":
        return (
            f'<circle cx="8" cy="8" r="6.5" {s}/>'
            f'<ellipse cx="8" cy="8" rx="2.8" ry="6.5" {s}/>'
            f'<path d="M1.5 8h13" {s}/>'
        )
    if kind == "linkedin":
        return (
            f'<rect x="1.5" y="1.5" width="13" height="13" rx="3" {s}/>'
            f'<path d="M5 7v4.5M5 4.75v.01M8 11.5V7M8 9c0-1.4.9-2 1.8-2s1.7.6 1.7 2v2.5" {s}/>'
        )
    return (
        f'<rect x="1.5" y="3" width="13" height="10" rx="2" {s}/>'
        f'<path d="M2 4l6 4.5L14 4" {s}/>'
    )


def _arrow(color: str) -> str:
    return (
        f'<path d="M1 8L8 1M3 1h5v5" fill="none" stroke="{color}" stroke-width="{STROKE}" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )


def render(link: config.Link, theme: Theme) -> str:
    text_w = len(link.label) * FONT_SIZE * CHAR_RATIO
    width = PAD_X + ICON + ICON_GAP + text_w + ARROW_GAP + ARROW + PAD_X
    if link.primary:
        fill, stroke, fg, accent = theme.fg, theme.fg, theme.bg, theme.bg
    else:
        fill, stroke, fg, accent = theme.bg, theme.border, theme.fg, theme.muted
    mid = HEIGHT / 2
    text_x = PAD_X + ICON + ICON_GAP
    arrow_x = width - PAD_X - ARROW
    body = "".join(
        [
            f'<rect x="0.5" y="0.5" width="{svg.fmt(width - 1)}" height="{HEIGHT - 1}" rx="{RADIUS}" '
            f'fill="{fill}" stroke="{stroke}"/>',
            f'<g transform="translate({PAD_X} {svg.fmt(mid - ICON / 2)})">{_icon(link.icon, fg)}</g>',
            f'<text x="{svg.fmt(text_x)}" y="{svg.fmt(mid)}" dominant-baseline="central" '
            f'font-family="{svg.SANS_STACK}" font-size="{FONT_SIZE}" font-weight="600" fill="{fg}">'
            f"{svg.esc(link.label)}</text>",
            f'<g transform="translate({svg.fmt(arrow_x)} {svg.fmt(mid - ARROW / 2)})">{_arrow(accent)}</g>',
        ]
    )
    return svg.svg_root(width, HEIGHT, body, title=link.label)


def main() -> int:
    profile = config.load_profile()
    if not profile.links:
        print("no links in config/profile.json", file=sys.stderr)
        return 1
    total = 0
    for link in profile.links:
        for theme, suffix in ((DARK, ""), (LIGHT, "-light")):
            total += svg.write_svg(config.repo_path("assets", f"link-{link.id}{suffix}.svg"), render(link, theme))
    print(f"wrote {len(profile.links) * 2} link buttons ({total} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
