"""Scrape the public contribution calendar and write data/contributions.json."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import requests
from bs4 import BeautifulSoup

from lib import config

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
COUNT_RE = re.compile(r"^\s*(\d+|No) contributions?", re.IGNORECASE)
MIN_DAYS = 350
OUT_PATH = config.repo_path("data", "contributions.json")


@dataclass(frozen=True)
class Day:
    date: date
    level: int
    count: int


@dataclass(frozen=True)
class Stats:
    total: int
    current_streak: int
    longest_streak: int
    best_day: Day | None
    monthly: dict[str, int]


def fetch_html(username: str, timeout: float) -> str:
    url = f"https://github.com/users/{username}/contributions"
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def parse_count(text: str) -> int | None:
    match = COUNT_RE.match(text)
    if not match:
        return None
    return 0 if match.group(1).lower() == "no" else int(match.group(1))


def parse(html: str) -> list[Day]:
    soup = BeautifulSoup(html, "html.parser")
    tooltips = {tip.get("for"): tip.get_text(strip=True) for tip in soup.find_all("tool-tip")}
    days: list[Day] = []
    for cell in soup.select("td.ContributionCalendar-day[data-date]"):
        count = parse_count(tooltips.get(cell.get("id"), ""))
        days.append(
            Day(
                date=date.fromisoformat(cell["data-date"]),
                level=int(cell.get("data-level", 0)),
                count=count if count is not None else 0,
            )
        )
    return sorted(days, key=lambda d: d.date)


def longest_run(days: list[Day]) -> int:
    best = run = 0
    for d in days:
        run = run + 1 if d.count > 0 else 0
        best = max(best, run)
    return best


def current_run(days: list[Day]) -> int:
    """Consecutive active days ending today (or yesterday if today is still empty)."""
    seq = list(days)
    if seq and seq[-1].count == 0:
        seq = seq[:-1]
    run = 0
    for d in reversed(seq):
        if d.count == 0:
            break
        run += 1
    return run


def stats(days: list[Day]) -> Stats:
    monthly: dict[str, int] = OrderedDict()
    for d in days:
        key = d.date.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + d.count
    best = max(days, key=lambda d: (d.count, d.date), default=None)
    return Stats(
        total=sum(d.count for d in days),
        current_streak=current_run(days),
        longest_streak=longest_run(days),
        best_day=best if best and best.count > 0 else None,
        monthly=monthly,
    )


def validate(days: list[Day]) -> str | None:
    if len(days) < MIN_DAYS:
        return f"parsed only {len(days)} days (expected >= {MIN_DAYS}); markup may have changed"
    if all(d.count == 0 for d in days) and any(d.level > 0 for d in days):
        return "all counts are zero but levels are non-zero; tooltip parsing failed"
    # Contiguity guard: the calendar must be a gap-free run of dates.
    if days[-1].date - days[0].date != timedelta(days=len(days) - 1):
        return "calendar dates are not contiguous"
    return None


def to_json(username: str, days: list[Day], s: Stats) -> str:
    payload = {
        "username": username,
        "fetched_on": date.today().isoformat(),
        "stats": {
            "total": s.total,
            "current_streak": s.current_streak,
            "longest_streak": s.longest_streak,
            "best_day": (
                {"date": s.best_day.date.isoformat(), "count": s.best_day.count} if s.best_day else None
            ),
            "monthly": s.monthly,
        },
        "days": [{"date": d.date.isoformat(), "level": d.level, "count": d.count} for d in days],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", help="defaults to config/profile.json username")
    parser.add_argument("--html", type=Path, help="parse a saved HTML file instead of fetching")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    username = args.username or config.load_profile().username
    try:
        html = args.html.read_text(encoding="utf-8") if args.html else fetch_html(username, args.timeout)
    except (requests.RequestException, OSError) as exc:
        print(f"error: could not load contributions: {exc}", file=sys.stderr)
        return 1

    days = parse(html)
    problem = validate(days)
    if problem:
        print(f"error: {problem}; {args.out} left unchanged", file=sys.stderr)
        return 1

    s = stats(days)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(to_json(username, days, s), encoding="utf-8")
    print(
        f"wrote {args.out.name}: {len(days)} days, {s.total} contributions, "
        f"streak {s.current_streak} (longest {s.longest_streak})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
