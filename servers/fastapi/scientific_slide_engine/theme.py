from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict


@dataclass(frozen=True)
class ScientificTheme:
    id: str
    name: str
    colors: Dict[str, str]
    typography: Dict[str, object]
    stage: Dict[str, int]
    safe_area_px: int
    pptx_safe: bool = True

    def as_dict(self) -> dict:
        return asdict(self)


SCIENTIFIC_EDITORIAL = ScientificTheme(
    id="scientific-editorial",
    name="Scientific Editorial",
    colors={
        "navy": "#17324D", "teal": "#2D7F7A", "amber": "#B56A2E", "sage": "#5C7561",
        "ink": "#23292F", "muted": "#6F777C", "paper": "#F7F8F7", "warm_paper": "#F5F2EA",
        "white": "#FFFFFF", "line": "#D8DEE4",
    },
    typography={
        "display": "Aptos Display", "body": "Aptos", "fallback": "Arial",
        "title_pt": 37, "body_pt": 20, "label_pt": 18, "footer_pt": 11,
    },
    stage={"width": 1280, "height": 720},
    safe_area_px=53,
)

THEMES = {SCIENTIFIC_EDITORIAL.id: SCIENTIFIC_EDITORIAL}
ALIASES = {"unica-scientific-editorial": "scientific-editorial"}


def get_theme(theme_id: str = "scientific-editorial") -> ScientificTheme:
    canonical = ALIASES.get(theme_id, theme_id)
    if canonical not in THEMES:
        raise KeyError(theme_id)
    return THEMES[canonical]
