from __future__ import annotations

from typing import Any, Dict, List, Mapping

from .native_renderer_v2 import (
    _add_callout,
    _add_caption,
    _add_footer,
    _add_question,
    _add_title,
    _add_unconsumed_locked_copy,
    _background,
    _diagram_region,
    _is_dark,
    _node_text,
    _pt_px,
    render_native_ui_v2,
)
from .renderer import STAGE_H, STAGE_W, _line, _rect, _text
from .schema import ScientificSlideSpec, VisualPlan
from .theme import ScientificTheme, get_theme
from .visual_slots import authored_layout_boxes, exact_visual_labels


ADVANCED_ARCHETYPES = {
    "causal-continuum",
    "risk-chain",
    "source-pathway",
    "intervention-points",
    "process-map",
    "layered-concept",
    "scenario",
}


def _labels(spec: ScientificSlideSpec, limit: int = 10) -> list[str]:
    return (exact_visual_labels(spec) or list(spec.locked.visible_text))[:limit]


def _begin(
    spec: ScientificSlideSpec,
    plan: VisualPlan,
    theme_id: str,
) -> tuple[ScientificTheme, Mapping[str, Mapping[str, object]], bool, str, List[Dict[str, Any]]]:
    theme = get_theme(theme_id)
    boxes = authored_layout_boxes(spec)
    background = _background(spec, theme, plan)
    dark = _is_dark(spec.background, theme, plan)
    elements: List[Dict[str, Any]] = [_rect(0, 0, STAGE_W, STAGE_H, background)]
    _add_title(elements, spec, theme, boxes, dark)
    return theme, boxes, dark, background, elements


def _finish(
    spec: ScientificSlideSpec,
    plan: VisualPlan,
    theme: ScientificTheme,
    boxes: Mapping[str, Mapping[str, object]],
    dark: bool,
    background: str,
    elements: List[Dict[str, Any]],
    consumed: set[str],
) -> Dict[str, Any]:
    _add_unconsumed_locked_copy(elements, spec, consumed, theme, boxes, dark)
    _add_question(elements, spec, theme, boxes, dark)
    _add_callout(elements, spec, theme, boxes, dark)
    _add_caption(elements, spec, theme, boxes, dark)
    _add_footer(elements, spec, theme, boxes, dark)
    return {
        "id": f"scientific-g{spec.global_id:03d}",
        "description": spec.visual_thesis or f"Scientific slide G{spec.global_id:03d}",
        "background": background,
        "components": [],
        "elements": elements,
        "scientific": {
            "source_hash": spec.source_hash,
            "global_id": spec.global_id,
            "archetype": plan.archetype,
            "variant": plan.variant,
            "theme": theme.id,
            "master_format": spec.master_format.value,
            "authored_layout_boxes": dict(boxes),
            "accessibility": spec.accessibility,
            "reading_order": spec.reading_order,
            "strict_copy_policy": "canonical-only",
            "renderer_variant": "advanced-scientific",
        },
    }


def _render_causal_chain(
    spec: ScientificSlideSpec,
    plan: VisualPlan,
    theme_id: str,
) -> Dict[str, Any]:
    theme, boxes, dark, background, elements = _begin(spec, plan, theme_id)
    labels = _labels(spec, 8)
    consumed: set[str] = set()
    x, y, w, h = _diagram_region(boxes)
    if labels:
        node_w = min(176.0, max(116.0, (w - 34.0 * (len(labels) - 1)) / len(labels)))
        gap = (w - node_w * len(labels)) / max(len(labels) - 1, 1)
        cursor = x
        for index, label in enumerate(labels):
            offset = 0 if index % 2 == 0 else 62
            ny = y + h * 0.28 + offset
            _node_text(
                elements,
                label,
                cursor,
                ny,
                node_w,
                82,
                theme,
                dark,
                accent=theme.colors["teal"] if index < len(labels) - 1 else theme.colors["amber"],
            )
            if label in spec.locked.visible_text:
                consumed.add(label)
            if index < len(labels) - 1:
                elements.append(
                    _line(
                        cursor + node_w,
                        ny + 41,
                        cursor + node_w + gap,
                        y + h * 0.28 + (62 if (index + 1) % 2 else 0) + 41,
                        theme.colors["amber"],
                        width=2.2,
                        arrow=True,
                    )
                )
            cursor += node_w + gap
    return _finish(spec, plan, theme, boxes, dark, background, elements, consumed)


def _render_process_map(
    spec: ScientificSlideSpec,
    plan: VisualPlan,
    theme_id: str,
) -> Dict[str, Any]:
    theme, boxes, dark, background, elements = _begin(spec, plan, theme_id)
    labels = _labels(spec, 10)
    consumed: set[str] = set()
    x, y, w, h = _diagram_region(boxes)
    if labels:
        columns = min(5, max(2, (len(labels) + 1) // 2))
        rows = 1 if len(labels) <= columns else 2
        cell_w = (w - 30 * (columns - 1)) / columns
        row_h = min(112.0, (h - 62 * (rows - 1)) / rows)
        for index, label in enumerate(labels):
            row, col = divmod(index, columns)
            if row >= rows:
                break
            bx = x + col * (cell_w + 30)
            by = y + row * (row_h + 62)
            _node_text(
                elements,
                label,
                bx,
                by,
                cell_w,
                row_h,
                theme,
                dark,
                accent=theme.colors["teal"] if row == 0 else theme.colors["sage"],
            )
            if label in spec.locked.visible_text:
                consumed.add(label)
            next_index = index + 1
            if next_index < len(labels):
                nrow, ncol = divmod(next_index, columns)
                if nrow == row:
                    elements.append(
                        _line(
                            bx + cell_w,
                            by + row_h / 2,
                            bx + cell_w + 24,
                            by + row_h / 2,
                            theme.colors["amber"],
                            width=2.0,
                            arrow=True,
                        )
                    )
                elif nrow < rows:
                    elements.append(
                        _line(
                            bx + cell_w / 2,
                            by + row_h,
                            x + ncol * (cell_w + 30) + cell_w / 2,
                            y + nrow * (row_h + 62),
                            theme.colors["amber"],
                            width=2.0,
                            arrow=True,
                        )
                    )
    return _finish(spec, plan, theme, boxes, dark, background, elements, consumed)


def _render_barrier_path(
    spec: ScientificSlideSpec,
    plan: VisualPlan,
    theme_id: str,
) -> Dict[str, Any]:
    theme, boxes, dark, background, elements = _begin(spec, plan, theme_id)
    labels = _labels(spec, 8)
    consumed: set[str] = set()
    x, y, w, h = _diagram_region(boxes)
    if labels:
        node_w = min(168.0, max(108.0, (w - 42 * (len(labels) - 1)) / len(labels)))
        gap = (w - node_w * len(labels)) / max(len(labels) - 1, 1)
        baseline = y + h * 0.48
        cursor = x
        for index, label in enumerate(labels):
            _node_text(elements, label, cursor, baseline - 42, node_w, 84, theme, dark)
            if label in spec.locked.visible_text:
                consumed.add(label)
            if index < len(labels) - 1:
                start = cursor + node_w
                end = start + gap
                mid = (start + end) / 2
                elements.append(_line(start, baseline, end, baseline, theme.colors["amber"], width=2.0, arrow=True))
                # A barrier is visual-only and carries no invented prose.
                elements.append(_line(mid, baseline - 58, mid, baseline + 58, theme.colors["teal"], width=4.0))
            cursor += node_w + gap
    return _finish(spec, plan, theme, boxes, dark, background, elements, consumed)


def _render_layered(
    spec: ScientificSlideSpec,
    plan: VisualPlan,
    theme_id: str,
) -> Dict[str, Any]:
    theme, boxes, dark, background, elements = _begin(spec, plan, theme_id)
    labels = _labels(spec, 7)
    consumed: set[str] = set()
    x, y, w, h = _diagram_region(boxes)
    if labels:
        for index, label in enumerate(labels):
            inset_x = index * min(58.0, w / max(len(labels) * 4, 1))
            inset_y = index * min(35.0, h / max(len(labels) * 4, 1))
            bw = w - inset_x * 2
            bh = h - inset_y * 2
            if bw < 260 or bh < 80:
                break
            stroke = theme.colors["teal"] if index % 2 == 0 else theme.colors["amber"]
            fill = "#244761" if dark and index == len(labels) - 1 else "transparent"
            elements.append(_rect(x + inset_x, y + inset_y, bw, bh, fill, stroke=stroke, radius=8))
            elements.append(
                _text(
                    label,
                    x + inset_x + 18,
                    y + inset_y + 10,
                    min(320, bw - 36),
                    40,
                    font_family=str(theme.typography["body"]),
                    font_size=_pt_px(18),
                    color=theme.colors["white"] if dark else theme.colors["ink"],
                    bold=True,
                    name="locked-visible-text" if label in spec.locked.visible_text else "canonical-visual-label",
                )
            )
            if label in spec.locked.visible_text:
                consumed.add(label)
    return _finish(spec, plan, theme, boxes, dark, background, elements, consumed)


def _render_scenario(
    spec: ScientificSlideSpec,
    plan: VisualPlan,
    theme_id: str,
) -> Dict[str, Any]:
    theme, boxes, dark, background, elements = _begin(spec, plan, theme_id)
    labels = _labels(spec, 6)
    consumed: set[str] = set()
    x, y, w, h = _diagram_region(boxes)
    if labels:
        cols = 2 if len(labels) <= 4 else 3
        rows = (len(labels) + cols - 1) // cols
        gap_x, gap_y = 28.0, 24.0
        cw = (w - gap_x * (cols - 1)) / cols
        ch = (h - gap_y * (rows - 1)) / rows
        for index, label in enumerate(labels):
            row, col = divmod(index, cols)
            bx, by = x + col * (cw + gap_x), y + row * (ch + gap_y)
            elements.append(_rect(bx, by, cw, ch, "#244761" if dark else theme.colors["white"], stroke=theme.colors["sage"], radius=5))
            elements.append(_line(bx, by, bx + cw, by, theme.colors["amber"], width=4))
            elements.append(
                _text(
                    label,
                    bx + 18,
                    by + 20,
                    cw - 36,
                    ch - 40,
                    font_family=str(theme.typography["body"]),
                    font_size=_pt_px(19),
                    color=theme.colors["white"] if dark else theme.colors["ink"],
                    bold=True,
                    vertical="top",
                    name="locked-visible-text" if label in spec.locked.visible_text else "canonical-visual-label",
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
    if plan.archetype in {"causal-continuum", "risk-chain"}:
        return _render_causal_chain(spec, plan, theme_id)
    if plan.archetype == "process-map":
        return _render_process_map(spec, plan, theme_id)
    if plan.archetype in {"source-pathway", "intervention-points"}:
        return _render_barrier_path(spec, plan, theme_id)
    if plan.archetype == "layered-concept":
        return _render_layered(spec, plan, theme_id)
    if plan.archetype == "scenario":
        return _render_scenario(spec, plan, theme_id)
    return render_native_ui_v2(spec, plan, theme_id)


__all__ = ["ADVANCED_ARCHETYPES", "render_scientific_ui"]
