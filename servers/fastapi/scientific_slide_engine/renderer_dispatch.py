from __future__ import annotations

import re
from typing import Any, Dict

from .advanced_renderer import (
    _begin,
    _diagram_region,
    _finish,
    _labels,
    render_scientific_ui as _render_advanced_ui,
)
from .renderer import SAFE, STAGE_W, _line, _rect, _text
from .schema import ScientificSlideSpec, VisualPlan


def _quoted_values(value: object) -> list[str]:
    if not isinstance(value, str):
        return []
    found: list[str] = []
    for match in re.finditer(r'[“"]([^”"]+)[”"]', value):
        text = match.group(1).strip()
        if text and text not in found:
            found.append(text)
    return found


def _hierarchy_axis_labels(spec: ScientificSlideSpec) -> list[str]:
    if not isinstance(spec.diagram_specification, dict):
        return []
    for key in ("arrows", "annotations", "hierarchy"):
        values = _quoted_values(spec.diagram_specification.get(key))
        if len(values) >= 2:
            return values[:2]
    return []


def _render_hierarchy(
    spec: ScientificSlideSpec,
    plan: VisualPlan,
    theme_id: str,
) -> Dict[str, Any]:
    theme, boxes, dark, background, elements = _begin(spec, plan, theme_id)
    labels = (list(spec.locked.visible_text) or _labels(spec, 7))[:7]
    consumed: set[str] = set()
    x, y, w, h = _diagram_region(boxes)
    axis_labels = _hierarchy_axis_labels(spec)
    axis_space = min(215.0, w * 0.22) if axis_labels else 40.0
    usable_w = max(360.0, w - axis_space)
    if labels:
        gap = 10.0
        band_h = min(66.0, max(42.0, (h - gap * (len(labels) - 1)) / len(labels)))
        widest = min(usable_w * 0.94, 830.0)
        narrowest = widest * 0.60
        for index, label in enumerate(labels):
            fraction = index / max(len(labels) - 1, 1)
            bw = widest - (widest - narrowest) * fraction
            bx = x + (usable_w - bw) / 2
            by = y + index * (band_h + gap)
            fill = (
                theme.colors["teal"]
                if index < 2
                else theme.colors["sage"]
                if index < 4
                else theme.colors["amber"]
            )
            elements.append(_rect(bx, by, bw, band_h, fill, radius=3))
            elements.append(
                _text(
                    label,
                    bx + 20,
                    by + 5,
                    bw - 40,
                    band_h - 10,
                    font_family=spec.body_font or str(theme.typography["body"]),
                    font_size=24.0,
                    color=theme.colors["white"],
                    bold=True,
                    name=(
                        "locked-visible-text"
                        if label in spec.locked.visible_text
                        else "canonical-visual-label"
                    ),
                )
            )
            if label in spec.locked.visible_text:
                consumed.add(label)

        if axis_labels:
            axis_x = min(STAGE_W - SAFE - 155, x + usable_w + 28)
            top = y + 4
            bottom = min(y + h - 4, y + len(labels) * (band_h + gap) - gap)
            elements.append(
                _line(axis_x, top + 30, axis_x, bottom - 30, theme.colors["muted"], width=1.8, arrow=True)
            )
            elements.append(
                _text(
                    axis_labels[0],
                    axis_x + 14,
                    top,
                    145,
                    48,
                    font_family=spec.body_font or str(theme.typography["body"]),
                    font_size=24.0,
                    color=theme.colors["white"] if dark else theme.colors["ink"],
                    name="canonical-visual-label",
                )
            )
            elements.append(
                _text(
                    axis_labels[1],
                    axis_x + 14,
                    max(top + 58, bottom - 58),
                    145,
                    56,
                    font_family=spec.body_font or str(theme.typography["body"]),
                    font_size=24.0,
                    color=theme.colors["white"] if dark else theme.colors["ink"],
                    name="canonical-visual-label",
                )
            )
    return _finish(spec, plan, theme, boxes, dark, background, elements, consumed)


def _render_timeline(
    spec: ScientificSlideSpec,
    plan: VisualPlan,
    theme_id: str,
) -> Dict[str, Any]:
    theme, boxes, dark, background, elements = _begin(spec, plan, theme_id)
    labels = _labels(spec, 10)
    consumed: set[str] = set()
    x, y, w, h = _diagram_region(boxes)
    if labels:
        left = max(x + 34, SAFE + 70)
        right = min(x + w - 34, STAGE_W - SAFE - 70)
        baseline = y + h * 0.50
        elements.append(
            _line(left, baseline, right, baseline, theme.colors["teal"], width=2.6, arrow=True)
        )
        step = (right - left) / max(len(labels) - 1, 1)
        for index, label in enumerate(labels):
            cx = left + index * step
            elements.append(_rect(cx - 7, baseline - 7, 14, 14, theme.colors["amber"], radius=7))
            text_w = min(190.0, max(126.0, step * 0.88 if len(labels) > 1 else 190.0))
            tx = min(max(cx - text_w / 2, SAFE), STAGE_W - SAFE - text_w)
            ty = baseline - 104 if index % 2 == 0 else baseline + 22
            elements.append(
                _text(
                    label,
                    tx,
                    ty,
                    text_w,
                    76,
                    font_family=spec.body_font or str(theme.typography["body"]),
                    font_size=24.0,
                    color=theme.colors["white"] if dark else theme.colors["ink"],
                    bold=True,
                    align="center",
                    name=(
                        "locked-visible-text"
                        if label in spec.locked.visible_text
                        else "canonical-visual-label"
                    ),
                )
            )
            if label in spec.locked.visible_text:
                consumed.add(label)
    return _finish(spec, plan, theme, boxes, dark, background, elements, consumed)


def render_scientific_ui(
    spec: ScientificSlideSpec,
    plan: VisualPlan,
    theme_id: str = "scientific-editorial",
) -> Dict[str, Any]:
    if plan.archetype == "hierarchy":
        return _render_hierarchy(spec, plan, theme_id)
    if plan.archetype == "timeline":
        return _render_timeline(spec, plan, theme_id)
    return _render_advanced_ui(spec, plan, theme_id)


__all__ = ["render_scientific_ui"]
