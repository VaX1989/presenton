from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .renderer import STAGE_H, STAGE_W, _line, _rect, _text, qa_native_ui
from .schema import ScientificSlideSpec, VisualPlan
from .theme import ScientificTheme, get_theme
from .visual_slots import authored_layout_boxes, chart_labels, exact_visual_labels, table_cells


def _pt_px(value: float) -> float:
    return round(value * 96.0 / 72.0, 2)


def _box(
    boxes: Mapping[str, Mapping[str, object]],
    ids: Sequence[str],
    fallback: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    for box_id in ids:
        raw = boxes.get(box_id)
        if raw:
            return (
                float(raw.get("x", fallback[0])),
                float(raw.get("y", fallback[1])),
                float(raw.get("width", fallback[2])),
                float(raw.get("height", fallback[3])),
            )
    return fallback


def _is_dark(background: str, theme: ScientificTheme, plan: VisualPlan) -> bool:
    value = (background or "").casefold()
    return plan.background == "dark" or "17324d" in value or "navy" in value


def _background(spec: ScientificSlideSpec, theme: ScientificTheme, plan: VisualPlan) -> str:
    value = spec.background or ""
    for token in value.split():
        if token.startswith("#") and len(token) == 7:
            return token.upper()
    return theme.colors["navy"] if plan.background == "dark" else theme.colors["warm_paper"]


def _add_title(
    elements: List[Dict[str, Any]], spec: ScientificSlideSpec, theme: ScientificTheme,
    boxes: Mapping[str, Mapping[str, object]], dark: bool,
) -> None:
    x, y, w, h = _box(boxes, ["T1", "TITLE"], (67, 48, 1146, 80))
    title_color = theme.colors["white"] if dark else theme.colors["navy"]
    elements.append(_text(
        spec.locked.title, x, y, w, h,
        font_family=spec.title_font or str(theme.typography["display"]),
        font_size=_pt_px(38 if len(spec.locked.title) < 92 else 35),
        color=title_color, bold=True, vertical="top", name="locked-title",
    ))
    if spec.locked.subtitle:
        sx, sy, sw, sh = _box(boxes, ["S1", "SUBTITLE"], (69, y + h + 6, min(900, w), 42))
        elements.append(_text(
            spec.locked.subtitle, sx, sy, sw, sh,
            font_family=spec.body_font or str(theme.typography["body"]),
            font_size=_pt_px(19), color="#D7E2E1" if dark else theme.colors["muted"],
            name="locked-subtitle",
        ))


def _add_footer(
    elements: List[Dict[str, Any]], spec: ScientificSlideSpec, theme: ScientificTheme,
    boxes: Mapping[str, Mapping[str, object]], dark: bool,
) -> None:
    x, y, w, h = _box(boxes, ["F1", "FOOTER"], (67, 680, 380, 22))
    text = f"G{spec.global_id:03d} · {spec.local_id:02d}/{spec.total_slides}"
    elements.append(_text(
        text, x, y, min(w, 500), max(h, 20), font_family=spec.body_font or str(theme.typography["body"]),
        font_size=_pt_px(10.5), color="#C7D0D7" if dark else theme.colors["muted"],
        name="scientific-footer", decorative=True,
    ))


def _add_question(
    elements: List[Dict[str, Any]], spec: ScientificSlideSpec, theme: ScientificTheme,
    boxes: Mapping[str, Mapping[str, object]], dark: bool,
) -> None:
    if not spec.locked.question:
        return
    x, y, w, h = _box(boxes, ["Q1", "QUESTION"], (70, 560, 720, 72))
    elements.append(_text(
        spec.locked.question, x, y, w, h,
        font_family=spec.body_font or str(theme.typography["body"]), font_size=_pt_px(21),
        color=theme.colors["white"] if dark else theme.colors["navy"], bold=True,
        name="locked-question",
    ))


def _add_caption(
    elements: List[Dict[str, Any]], spec: ScientificSlideSpec, theme: ScientificTheme,
    boxes: Mapping[str, Mapping[str, object]], dark: bool,
) -> None:
    if not spec.locked.caption:
        return
    x, y, w, h = _box(boxes, ["C1", "CAPTION"], (96, 608, 820, 34))
    elements.append(_text(
        spec.locked.caption, x, y, w, max(h, 30),
        font_family=spec.body_font or str(theme.typography["body"]), font_size=_pt_px(18),
        color="#D7E2E1" if dark else theme.colors["muted"], name="locked-caption",
    ))


def _add_callout(
    elements: List[Dict[str, Any]], spec: ScientificSlideSpec, theme: ScientificTheme,
    boxes: Mapping[str, Mapping[str, object]], dark: bool,
) -> None:
    if not spec.locked.callouts:
        return
    x, y, w, h = _box(boxes, ["B1", "C1", "CALLOUT"], (746, 584, 458, 64))
    elements.append(_line(x, y, x, y + h, theme.colors["amber"], width=4))
    elements.append(_text(
        "\n".join(spec.locked.callouts), x + 16, y, w - 16, h,
        font_family=spec.body_font or str(theme.typography["body"]), font_size=_pt_px(18),
        color=theme.colors["white"] if dark else theme.colors["ink"], bold=True,
        name="locked-callout",
    ))


def _node_text(
    elements: List[Dict[str, Any]], label: str, x: float, y: float, w: float, h: float,
    theme: ScientificTheme, dark: bool, *, accent: str | None = None,
) -> None:
    fill = "#244761" if dark else theme.colors["white"]
    line_color = accent or theme.colors["teal"]
    elements.append(_rect(x, y, w, h, fill, stroke=line_color, radius=4))
    elements.append(_text(
        label, x + 12, y + 7, w - 24, h - 14,
        font_family=str(theme.typography["body"]), font_size=_pt_px(18),
        color=theme.colors["white"] if dark else theme.colors["ink"], bold=True,
        align="center", name="canonical-visual-label",
    ))


def _diagram_region(boxes: Mapping[str, Mapping[str, object]]) -> tuple[float, float, float, float]:
    return _box(boxes, ["D1", "M1", "V1", "CH1", "P1"], (92, 178, 1096, 380))


def _render_hero(
    elements: List[Dict[str, Any]], spec: ScientificSlideSpec, plan: VisualPlan,
    theme: ScientificTheme, boxes: Mapping[str, Mapping[str, object]], dark: bool,
) -> set[str]:
    consumed: set[str] = set()
    dx, dy, dw, dh = _diagram_region(boxes)
    labels = exact_visual_labels(spec)
    if not labels:
        labels = [part.strip() for part in " → ".join(spec.locked.visible_text).split("→") if part.strip()][:6]
    labels = labels[:6]
    if labels:
        baseline = dy + dh * 0.48
        left, right = dx + 24, dx + dw - 24
        step = (right - left) / max(len(labels) - 1, 1)
        for index, label in enumerate(labels):
            cx = left + index * step
            if index:
                elements.append(_line(cx - step + 46, baseline, cx - 46, baseline, theme.colors["amber"], width=2.2, arrow=True))
            elements.append(_rect(cx - 9, baseline - 9, 18, 18, theme.colors["teal"] if index not in {2, 3} else theme.colors["amber"], radius=9))
            elements.append(_text(
                label, cx - 72, baseline + 24 if index % 2 == 0 else baseline - 62, 144, 42,
                font_family=str(theme.typography["body"]), font_size=_pt_px(18),
                color=theme.colors["white"] if dark else theme.colors["ink"], bold=True,
                align="center", name="canonical-visual-label",
            ))
    # Preserve authored visible copy independently of the diagram labels.
    if spec.locked.visible_text:
        x, y, w, h = _box(boxes, ["L1", "COPY"], (68, min(600, dy + dh + 8), min(690, dw), 54))
        for index, line in enumerate(spec.locked.visible_text[:3]):
            elements.append(_text(
                line, x, y + index * 26, w, 26,
                font_family=spec.body_font or str(theme.typography["body"]), font_size=_pt_px(18),
                color="#D7E2E1" if dark else theme.colors["muted"], name="locked-visible-text",
            ))
            consumed.add(line)
    return consumed


def _render_linear(
    elements: List[Dict[str, Any]], spec: ScientificSlideSpec, theme: ScientificTheme,
    boxes: Mapping[str, Mapping[str, object]], dark: bool,
) -> set[str]:
    consumed: set[str] = set()
    x, y, w, h = _diagram_region(boxes)
    labels = exact_visual_labels(spec) or list(spec.locked.visible_text)
    labels = labels[:8]
    if not labels:
        return consumed
    gap = 18.0
    node_w = min(190.0, max(104.0, (w - gap * (len(labels) - 1)) / len(labels)))
    used = node_w * len(labels) + gap * (len(labels) - 1)
    cursor = x + (w - used) / 2
    baseline = y + h * 0.46
    for index, label in enumerate(labels):
        _node_text(elements, label, cursor, baseline - 42, node_w, 84, theme, dark, accent=theme.colors["teal"] if index % 2 == 0 else theme.colors["amber"])
        if label in spec.locked.visible_text:
            consumed.add(label)
        if index < len(labels) - 1:
            elements.append(_line(cursor + node_w + 3, baseline, cursor + node_w + gap - 3, baseline, theme.colors["amber"], width=2.0, arrow=True))
        cursor += node_w + gap
    return consumed


def _render_hierarchy(
    elements: List[Dict[str, Any]], spec: ScientificSlideSpec, theme: ScientificTheme,
    boxes: Mapping[str, Mapping[str, object]], dark: bool,
) -> set[str]:
    consumed: set[str] = set()
    x, y, w, h = _diagram_region(boxes)
    labels = list(spec.locked.visible_text) or exact_visual_labels(spec)
    labels = labels[:7]
    if not labels:
        return consumed
    band_h = min(66.0, max(44.0, (h - 12 * (len(labels) - 1)) / len(labels)))
    widest = min(w * 0.86, 830)
    narrowest = widest * 0.58
    for index, label in enumerate(labels):
        fraction = index / max(len(labels) - 1, 1)
        bw = widest - (widest - narrowest) * fraction
        bx = x + (w - bw) / 2
        by = y + index * (band_h + 10)
        fill = theme.colors["teal"] if index < 2 else theme.colors["sage"] if index < 4 else theme.colors["amber"]
        elements.append(_rect(bx, by, bw, band_h, fill, radius=3))
        elements.append(_text(
            label, bx + 20, by + 5, bw - 40, band_h - 10,
            font_family=str(theme.typography["body"]), font_size=_pt_px(18),
            color=theme.colors["white"], bold=True, name="locked-visible-text" if label in spec.locked.visible_text else "canonical-visual-label",
        ))
        if label in spec.locked.visible_text:
            consumed.add(label)
    return consumed


def _render_matrix(
    elements: List[Dict[str, Any]], spec: ScientificSlideSpec, theme: ScientificTheme,
    boxes: Mapping[str, Mapping[str, object]], dark: bool,
) -> set[str]:
    consumed: set[str] = set()
    x, y, w, h = _box(boxes, ["M1", "D1", "TABLE"], (88, 188, 1104, 390))
    cells = list(spec.locked.visible_text) or table_cells(spec)
    cells = cells[:12]
    if not cells:
        return consumed
    cols = 2 if len(cells) <= 4 else 3
    rows = math.ceil(len(cells) / cols)
    gx, gy = 18.0, 16.0
    cw = (w - gx * (cols - 1)) / cols
    ch = (h - gy * (rows - 1)) / rows
    for index, label in enumerate(cells):
        row, col = divmod(index, cols)
        bx, by = x + col * (cw + gx), y + row * (ch + gy)
        # Editorial cells: hairline rules and generous negative space, not pill cards.
        elements.append(_line(bx, by, bx + cw, by, theme.colors["teal"] if index % 2 == 0 else theme.colors["amber"], width=3))
        elements.append(_text(
            label, bx + 6, by + 14, cw - 12, ch - 20,
            font_family=str(theme.typography["body"]), font_size=_pt_px(19),
            color=theme.colors["white"] if dark else theme.colors["ink"], bold=True,
            vertical="top", name="locked-visible-text" if label in spec.locked.visible_text else "canonical-visual-label",
        ))
        if label in spec.locked.visible_text:
            consumed.add(label)
    return consumed


def _render_chart(
    elements: List[Dict[str, Any]], spec: ScientificSlideSpec, theme: ScientificTheme,
    boxes: Mapping[str, Mapping[str, object]], dark: bool,
) -> set[str]:
    consumed: set[str] = set()
    x, y, w, h = _box(boxes, ["CH1", "D1", "CHART"], (98, 195, 1080, 370))
    labels = chart_labels(spec)[:4]
    if not labels:
        return consumed
    row_h = h / len(labels)
    ink = theme.colors["white"] if dark else theme.colors["ink"]
    line_colors = [theme.colors["navy"], theme.colors["teal"], theme.colors["amber"], theme.colors["sage"]]
    for index, label in enumerate(labels):
        cy = y + row_h * index + row_h * 0.52
        label_w = min(250, w * 0.25)
        elements.append(_text(
            label, x, cy - 28, label_w, 56,
            font_family=str(theme.typography["body"]), font_size=_pt_px(18),
            color=ink, bold=True, name="locked-visible-text" if label in spec.locked.visible_text else "canonical-visual-label",
        ))
        if label in spec.locked.visible_text:
            consumed.add(label)
        x0 = x + label_w + 24
        x1 = x + w - 16
        elements.append(_line(x0, cy + 24, x1, cy + 24, "#BFC6CB" if not dark else "#61788A", width=1.0, arrow=True))
        color = line_colors[index % len(line_colors)]
        if index == 0:  # brief peak
            pts = [(x0, cy + 18), (x0 + (x1-x0)*0.28, cy + 18), (x0 + (x1-x0)*0.38, cy - 35), (x0 + (x1-x0)*0.46, cy + 18), (x1, cy + 18)]
        elif index == 1:  # repeated episodes
            pts = [(x0, cy + 18)]
            for step in range(1, 8):
                px = x0 + (x1-x0)*step/8
                pts.extend([(px - 12, cy + 18), (px, cy - 22 if step % 2 else cy - 7), (px + 12, cy + 18)])
            pts.append((x1, cy + 18))
        else:  # prolonged exposure
            pts = [(x0, cy + 18), (x0 + 30, cy - 8), (x1 - 30, cy - 8), (x1, cy + 18)]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            elements.append(_line(ax, ay, bx, by, color, width=2.8))
    return consumed


def _render_network(
    elements: List[Dict[str, Any]], spec: ScientificSlideSpec, theme: ScientificTheme,
    boxes: Mapping[str, Mapping[str, object]], dark: bool,
) -> set[str]:
    consumed: set[str] = set()
    x, y, w, h = _diagram_region(boxes)
    labels = exact_visual_labels(spec) or list(spec.locked.visible_text)
    labels = labels[:10]
    if not labels:
        return consumed
    cx, cy = x + w / 2, y + h / 2
    rx, ry = w * 0.37, h * 0.38
    for index, label in enumerate(labels):
        angle = -math.pi / 2 + index * 2 * math.pi / len(labels)
        nx, ny = cx + rx * math.cos(angle), cy + ry * math.sin(angle)
        elements.append(_line(cx, cy, nx, ny, theme.colors["teal"], width=1.4))
        elements.append(_rect(nx - 78, ny - 30, 156, 60, "#244761" if dark else theme.colors["white"], stroke=theme.colors["teal"], radius=30))
        elements.append(_text(
            label, nx - 66, ny - 23, 132, 46,
            font_family=str(theme.typography["body"]), font_size=_pt_px(18),
            color=theme.colors["white"] if dark else theme.colors["ink"], bold=True,
            align="center", name="locked-visible-text" if label in spec.locked.visible_text else "canonical-visual-label",
        ))
        if label in spec.locked.visible_text:
            consumed.add(label)
    return consumed


def _render_timeline(
    elements: List[Dict[str, Any]], spec: ScientificSlideSpec, theme: ScientificTheme,
    boxes: Mapping[str, Mapping[str, object]], dark: bool,
) -> set[str]:
    consumed: set[str] = set()
    x, y, w, h = _diagram_region(boxes)
    labels = exact_visual_labels(spec) or list(spec.locked.visible_text)
    labels = labels[:10]
    if not labels:
        return consumed
    baseline = y + h * 0.50
    elements.append(_line(x + 20, baseline, x + w - 20, baseline, theme.colors["teal"], width=2.6, arrow=True))
    step = (w - 80) / max(len(labels) - 1, 1)
    for index, label in enumerate(labels):
        cx = x + 40 + index * step
        elements.append(_rect(cx - 7, baseline - 7, 14, 14, theme.colors["amber"], radius=7))
        ty = baseline - 104 if index % 2 == 0 else baseline + 22
        elements.append(_text(
            label, cx - min(100, step * 0.44), ty, min(200, max(130, step * 0.88)), 76,
            font_family=str(theme.typography["body"]), font_size=_pt_px(18),
            color=theme.colors["white"] if dark else theme.colors["ink"], bold=True,
            align="center", name="locked-visible-text" if label in spec.locked.visible_text else "canonical-visual-label",
        ))
        if label in spec.locked.visible_text:
            consumed.add(label)
    return consumed


def _render_loop(
    elements: List[Dict[str, Any]], spec: ScientificSlideSpec, theme: ScientificTheme,
    boxes: Mapping[str, Mapping[str, object]], dark: bool,
) -> set[str]:
    consumed: set[str] = set()
    x, y, w, h = _diagram_region(boxes)
    labels = exact_visual_labels(spec) or list(spec.locked.visible_text)
    labels = labels[:8]
    if not labels:
        return consumed
    cx, cy, rx, ry = x + w/2, y + h/2, w*0.38, h*0.37
    points: List[tuple[float, float]] = []
    for index in range(len(labels)):
        angle = -math.pi/2 + index*2*math.pi/len(labels)
        points.append((cx + rx*math.cos(angle), cy + ry*math.sin(angle)))
    for index, (point, label) in enumerate(zip(points, labels)):
        next_point = points[(index + 1) % len(points)]
        elements.append(_line(point[0], point[1], next_point[0], next_point[1], theme.colors["teal"], width=1.8, arrow=True))
        elements.append(_rect(point[0]-80, point[1]-30, 160, 60, "#244761" if dark else theme.colors["white"], stroke=theme.colors["teal"], radius=4))
        elements.append(_text(
            label, point[0]-68, point[1]-23, 136, 46,
            font_family=str(theme.typography["body"]), font_size=_pt_px(18),
            color=theme.colors["white"] if dark else theme.colors["ink"], bold=True,
            align="center", name="locked-visible-text" if label in spec.locked.visible_text else "canonical-visual-label",
        ))
        if label in spec.locked.visible_text:
            consumed.add(label)
    return consumed


def _add_unconsumed_locked_copy(
    elements: List[Dict[str, Any]], spec: ScientificSlideSpec, consumed: set[str],
    theme: ScientificTheme, boxes: Mapping[str, Mapping[str, object]], dark: bool,
) -> None:
    missing = [item for item in spec.locked.visible_text if item not in consumed]
    if not missing:
        return
    # This rail is deliberate: strict mode never drops authored visible copy even
    # when a richer diagram uses separate EXACT_LABELS from section J/K/L.
    x, y, w, h = _box(boxes, ["COPY", "L1"], (76, 568, 650, 80))
    line_h = max(28.0, min(42.0, h / max(len(missing), 1)))
    for index, item in enumerate(missing[:5]):
        elements.append(_text(
            item, x, y + index * line_h, w, line_h,
            font_family=spec.body_font or str(theme.typography["body"]), font_size=_pt_px(18),
            color="#D7E2E1" if dark else theme.colors["ink"],
            name="locked-visible-text",
        ))


def render_native_ui_v2(
    spec: ScientificSlideSpec, plan: VisualPlan, theme_id: str = "scientific-editorial",
) -> Dict[str, Any]:
    theme = get_theme(theme_id)
    boxes = authored_layout_boxes(spec)
    background = _background(spec, theme, plan)
    dark = _is_dark(spec.background, theme, plan)
    elements: List[Dict[str, Any]] = [_rect(0, 0, STAGE_W, STAGE_H, background)]
    _add_title(elements, spec, theme, boxes, dark)

    archetype = plan.archetype
    if archetype == "hero-question":
        consumed = _render_hero(elements, spec, plan, theme, boxes, dark)
    elif archetype == "hierarchy":
        consumed = _render_hierarchy(elements, spec, theme, boxes, dark)
    elif archetype in {"matrix", "comparison"}:
        consumed = _render_matrix(elements, spec, theme, boxes, dark)
    elif archetype == "gradient-distribution" or spec.visual_type.casefold() == "chart":
        consumed = _render_chart(elements, spec, theme, boxes, dark)
    elif archetype in {"network", "discipline-map", "system-map"}:
        consumed = _render_network(elements, spec, theme, boxes, dark)
    elif archetype == "timeline":
        consumed = _render_timeline(elements, spec, theme, boxes, dark)
    elif archetype in {"verification-loop", "audit-loop", "synthesis"}:
        consumed = _render_loop(elements, spec, theme, boxes, dark)
    else:
        consumed = _render_linear(elements, spec, theme, boxes, dark)

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
            "authored_layout_boxes": boxes,
            "accessibility": spec.accessibility,
            "reading_order": spec.reading_order,
            "strict_copy_policy": "canonical-only",
        },
    }


__all__ = ["render_native_ui_v2", "qa_native_ui"]
