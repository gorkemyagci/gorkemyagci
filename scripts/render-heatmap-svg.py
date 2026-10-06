"""Render data/contributions.json as dark + light animated heatmap SVGs."""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib import config, svg
from lib.theme import DARK, LIGHT, PEAK_PERCENTILE, Theme

WIDTH = 860
CELL = 12
GAP = 3
PITCH = CELL + GAP
LABEL_W = 30
GRID_Y = 34
STEP_S = 0.025
FOOTER_SIZE = 12
FOOTER_LINE_H = 20
FOOTER_SEP = "  ·  "
LEGEND_W = 170  # "Less" + 6 swatches + "More", reserved on the first footer line
DATA_PATH = config.repo_path("data", "contributions.json")
OUTPUTS = ((DARK, "contrib-heatmap.svg"), (LIGHT, "contrib-heatmap-light.svg"))


@dataclass(frozen=True)
class Cell:
    week: int
    weekday: int  # 0 = Sunday
    day: date
    shade: int  # 0..5
    count: int


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"{path} not found; run scripts/fetch-contributions.py first") from None


def percentile(values: list[int], pct: float) -> float:
    """Nearest-rank percentile; inf for an empty list so nothing qualifies."""
    if not values:
        return math.inf
    ordered = sorted(values)
    return ordered[max(math.ceil(pct / 100 * len(ordered)) - 1, 0)]


def build_cells(days: list[dict], peak_pct: float) -> list[Cell]:
    first = date.fromisoformat(days[0]["date"])
    offset = (first.weekday() + 1) % 7
    peak = percentile([d["count"] for d in days if d["count"] > 0], peak_pct)
    cells = []
    for i, d in enumerate(days):
        idx = i + offset
        shade = d["level"]
        if shade == 4 and d["count"] >= peak:
            shade = 5
        cells.append(Cell(idx // 7, idx % 7, date.fromisoformat(d["date"]), shade, d["count"]))
    return cells


def month_labels(cells: list[Cell]) -> list[tuple[int, str]]:
    labels: list[tuple[int, str]] = []
    last_month = None
    for c in cells:
        if c.weekday != 0 and c is not cells[0]:
            continue
        if c.day.month != last_month:
            labels.append((c.week, c.day.strftime("%b")))
            last_month = c.day.month
    # Drop a leading label that would collide with the next one.
    if len(labels) > 1 and labels[1][0] - labels[0][0] < 3:
        labels.pop(0)
    return labels


def text(x: float, y: float, s: str, fill: str, size: int = 10, anchor: str = "start") -> str:
    return (
        f'<text x="{svg.fmt(x)}" y="{svg.fmt(y)}" fill="{fill}" font-size="{size}" '
        f'text-anchor="{anchor}">{svg.esc(s)}</text>'
    )


def fmt_day(d: date) -> str:
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def stat_phrase(name: str, s: dict) -> str:
    if name == "total":
        return f"{s['total']:,} contributions in the last year"
    if name == "current_streak":
        return f"current streak {s['current_streak']}d"
    if name == "longest_streak":
        return f"longest streak {s['longest_streak']}d"
    best = s["best_day"]
    return f"best day {best['count']} on {fmt_day(date.fromisoformat(best['date']))}" if best else "best day —"


def pack(phrases: list[str], first_budget: float, budget: float) -> list[str]:
    """Greedily join phrases into footer lines that fit the pixel budgets."""
    char_w = FOOTER_SIZE * svg.SANS_CHAR_RATIO
    lines: list[str] = []
    for phrase in phrases:
        limit = first_budget if len(lines) <= 1 else budget
        candidate = f"{lines[-1]}{FOOTER_SEP}{phrase}" if lines else phrase
        if lines and len(candidate) * char_w <= limit:
            lines[-1] = candidate
        else:
            lines.append(phrase)
    return lines


def render(data: dict, theme: Theme, footer_stats: tuple[str, ...], peak_pct: float) -> str:
    cells = build_cells(data["days"], peak_pct)
    n_weeks = cells[-1].week + 1
    grid_w = n_weeks * PITCH - GAP
    x0 = (WIDTH - LABEL_W - grid_w) / 2 + LABEL_W
    grid_bottom = GRID_Y + 7 * PITCH - GAP
    s = data["stats"]
    footer = pack([stat_phrase(n, s) for n in footer_stats], grid_w - LEGEND_W, grid_w)
    row1 = grid_bottom + 26
    height = row1 + max(len(footer) - 1, 0) * FOOTER_LINE_H + 22

    parts = [
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="6" '
        f'fill="{theme.bg}" stroke="{theme.border}"/>',
        f'<g font-family="{svg.SANS_STACK}">',
    ]
    for week, name in month_labels(cells):
        parts.append(text(x0 + week * PITCH, GRID_Y - 8, name, theme.muted))
    for weekday, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(text(x0 - 6, GRID_Y + weekday * PITCH + CELL - 2, name, theme.muted, anchor="end"))

    for c in cells:
        parts.append(
            f'<rect class="c d{c.week + c.weekday}" x="{svg.fmt(x0 + c.week * PITCH)}" '
            f'y="{GRID_Y + c.weekday * PITCH}" width="{CELL}" height="{CELL}" rx="2" '
            f'fill="{theme.heat[c.shade]}"/>'
        )

    for i, line in enumerate(footer):
        parts.append(text(x0, row1 + i * FOOTER_LINE_H, line, theme.fg, FOOTER_SIZE))

    # Less ■■■■■■ More, right-aligned to the grid edge.
    right = x0 + grid_w
    lx = right - 28 - len(theme.heat) * PITCH
    parts.append(text(lx - 6, row1, "Less", theme.muted, anchor="end"))
    for i, color in enumerate(theme.heat):
        parts.append(
            f'<rect x="{svg.fmt(lx + i * PITCH)}" y="{row1 - 10}" width="{CELL}" height="{CELL}" '
            f'rx="2" fill="{color}"/>'
        )
    parts.append(text(right, row1, "More", theme.muted, anchor="end"))
    parts.append("</g>")

    max_diag = max(c.week + c.weekday for c in cells)
    style = (
        ".c{opacity:0;transform-box:fill-box;transform-origin:center;"
        "animation:pop .4s ease-out forwards}"
        "@keyframes pop{from{opacity:0;transform:scale(.4)}to{opacity:1;transform:scale(1)}}"
        + "".join(f".d{k}{{animation-delay:{k * STEP_S:.3f}s}}" for k in range(1, max_diag + 1))
    )
    title = f"{data['username']}: {s['total']} contributions in the last year"
    return svg.svg_root(WIDTH, height, "\n".join(parts), style=style, title=title)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    parser.add_argument("--out-dir", type=Path, default=config.repo_path("assets"))
    parser.add_argument(
        "--peak-percentile",
        type=float,
        default=PEAK_PERCENTILE,
        help="level-4 days at/above this percentile of non-zero days use the brightest shade",
    )
    args = parser.parse_args()

    data = load(args.data)
    footer_stats = config.load_profile().heatmap.footer_stats
    sizes = [
        f"{name} {svg.write_svg(args.out_dir / name, render(data, theme, footer_stats, args.peak_percentile)) / 1024:.1f} KB"
        for theme, name in OUTPUTS
    ]
    print(f"wrote {', '.join(sizes)} ({svg.mode_label()}, {len(data['days'])} days)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
