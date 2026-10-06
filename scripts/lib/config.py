"""Load config/profile.json and resolve repo-root paths."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = REPO_ROOT / "config" / "profile.json"


def repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


@dataclass(frozen=True)
class Row:
    key: str
    value: str


@dataclass(frozen=True)
class Separator:
    pass


FOOTER_STATS = ("total", "current_streak", "longest_streak", "best_day")
DEFAULT_FOOTER_STATS = ("total", "longest_streak")


@dataclass(frozen=True)
class Heatmap:
    footer_stats: tuple[str, ...] = DEFAULT_FOOTER_STATS


@dataclass(frozen=True)
class Profile:
    username: str
    title: str
    rows: list[Row | Separator]
    heatmap: Heatmap = Heatmap()


def _parse_row(raw: dict, index: int) -> Row | Separator:
    if raw.get("separator"):
        return Separator()
    try:
        return Row(key=str(raw["key"]), value=str(raw["value"]))
    except KeyError as exc:
        raise SystemExit(f"{PROFILE_PATH}: rows[{index}] missing {exc}") from None


def _parse_heatmap(raw: dict) -> Heatmap:
    stats = tuple(raw.get("footer_stats", DEFAULT_FOOTER_STATS))
    unknown = [s for s in stats if s not in FOOTER_STATS]
    if unknown:
        raise SystemExit(f"{PROFILE_PATH}: heatmap.footer_stats has unknown {unknown}; allowed: {list(FOOTER_STATS)}")
    return Heatmap(footer_stats=stats)


def load_profile(path: Path = PROFILE_PATH) -> Profile:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"profile config not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from None
    try:
        return Profile(
            username=data["username"],
            title=data["title"],
            rows=[_parse_row(r, i) for i, r in enumerate(data["rows"])],
            heatmap=_parse_heatmap(data.get("heatmap", {})),
        )
    except KeyError as exc:
        raise SystemExit(f"{path}: missing top-level key {exc}") from None
