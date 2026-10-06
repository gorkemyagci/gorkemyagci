"""Color palettes shared by every generated SVG."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    fg: str
    muted: str
    border: str
    heat: tuple[str, str, str, str, str, str]


DARK = Theme(
    name="dark",
    bg="#0d1117",
    fg="#c9d1d9",
    muted="#8b949e",
    border="#30363d",
    heat=("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"),
)

LIGHT = Theme(
    name="light",
    bg="#ffffff",
    fg="#1f2328",
    muted="#656d76",
    border="#d0d7de",
    heat=("#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39", "#0e4429"),
)

# Level-4 days at or above this percentile of non-zero days get the brightest shade (heat[5]).
PEAK_PERCENTILE = 95.0
