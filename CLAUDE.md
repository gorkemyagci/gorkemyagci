# CLAUDE.md

## Purpose
GitHub profile repo (`gorkemyagci/gorkemyagci`); `README.md` renders on the profile. The art is self-generated SVG: a profile card and a contribution heatmap (each in dark + light variants), refreshed daily by GitHub Actions. No third-party stats services, no tokens.

## GitHub README constraints
- GitHub strips `<script>` and nearly all inline CSS/`style` attributes from READMEs. All motion lives **inside** each SVG (SMIL or CSS `@keyframes` in an embedded `<style>`), referenced via `<img>`/`<picture>`.
- SVGs loaded through `<img>` cannot fetch anything: no external hrefs, no web fonts (system sans stack only, `lib/svg.py:SANS_STACK`).
- Vertical spacing: `<br />` only. Section titles use `<h3>` (h1/h2 draw an underline rule).
- Dark/light: every image ships two SVGs, embedded with `<picture>` + `<source media="(prefers-color-scheme: dark)">` (dark) and a fallback `<img>` (light). Both are 860 wide.
- **Animations play once and freeze** (`fill="freeze"` / `animation-fill-mode: forwards`). No infinite loops.

## Structure
```
README.md                     hand-written page; embeds assets/*.svg
config/profile.json           ALL info-card content (username, title, rows, separators) + heatmap footer config
data/contributions.json       scraped calendar + stats (written by CI)
assets/                       generated SVGs (commit them)
scripts/
  requirements.txt            requests, beautifulsoup4 (CI)
  make-info-card.py           config/profile.json -> assets/info-card{,-light}.svg
  fetch-contributions.py      github.com/users/<u>/contributions -> data/contributions.json
  render-heatmap-svg.py       data/contributions.json -> assets/contrib-heatmap{,-light}.svg
  lib/                        svg.py (root builder, escaping, STATIC flag), theme.py (palettes), config.py (profile + paths)
.github/workflows/update-profile-art.yml   daily fetch + heatmap + card
```

## Conventions
- Files and folders: kebab-case. Importable Python modules: single-word lowercase (`lib/svg.py`, not `svg-utils.py`).
- Entry scripts are run from the repo root as `python scripts/<name>.py`; each inserts its own directory on `sys.path` and imports `from lib import ...`.
- All SVG boilerplate goes through `lib/svg.py`; all colors through `lib/theme.py`. Root `<svg>` always carries explicit `width`/`height`.
- Personal card content lives only in `config/profile.json`; never hardcode it in scripts. A `{"separator": true}` row draws a thin rule between groups.
- Card style is deliberately restrained: theme `fg`/`muted`/`border` only, small uppercase labels, no accent colors, no decorative elements. No ASCII art in the repo.
- Each script prints one summary line; errors go to stderr with a non-zero exit.

## Heatmap
- Footer stats come from `config/profile.json` → `"heatmap": {"footer_stats": [...]}`. Allowed: `total`, `current_streak`, `longest_streak`, `best_day`; rendered in the listed order (packed onto lines that fit). Default `["total", "longest_streak"]`.
- Brightest shade (`#69f0a0`) = level-4 days whose count is ≥ the 95th percentile of non-zero days. Constant `PEAK_PERCENTILE` in `lib/theme.py`; override per run with `--peak-percentile`.

## README content
- Hero (name, title, tagline, contact badges), "What I'm Building", "Beyond Privent" and footer copy are hand-written in `README.md`.
- All info-card content lives in `config/profile.json`.
- The tech stack is shown only in the card. No stack badges in the README.

## Regenerating assets
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
python scripts/fetch-contributions.py
python scripts/render-heatmap-svg.py
python scripts/make-info-card.py
```

## Static preview
`STATIC=1` emits the final frame with no animation. Write to a scratch location so committed assets stay animated:
```
STATIC=1 python scripts/make-info-card.py --out-dir /tmp
STATIC=1 python scripts/render-heatmap-svg.py --out-dir /tmp
open -a Safari /tmp/info-card.svg
```
Open the animated files in `assets/` directly in a browser to watch the one-shot animation.
