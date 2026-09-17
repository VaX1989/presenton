from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Sequence, Tuple

from .schema import ScientificSlideSpec, VisualPlan
from .theme import ScientificTheme, get_theme

STAGE_W = 1280
STAGE_H = 720
SAFE = 53


def _pt_to_px(pt: float) -> float:
    return round(pt * 96.0 / 72.0, 2)


def _parse_pt(value: str, default: float) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)", value or "")
    return float(match.group(1)) if match else default


def _hex(value: str, fallback: str) -> str:
    match = re.search(r"#[0-9A-Fa-f]{6}", value or "")
    return match.group(0).upper() if match else fallback


def _text(text: str, x: float, y: float, w: float, h: float, *, font_family: str, font_size: float, color: str, bold: bool = False, align: str = "left", vertical: str = "middle", name: str | None = None, decorative: bool = False) -> Dict[str, Any]:
    return {
        "type": "text", "name": name, "decorative": decorative,
        "position": {"x": round(x, 2), "y": round(y, 2)},
        "size": {"width": round(w, 2), "height": round(h, 2)},
        "font": {"family": font_family, "size": round(font_size, 2), "color": color, "bold": bold, "line_height": 1.08},
        "alignment": {"horizontal": align, "vertical": vertical},
        "runs": [{"text": text}],
    }


def _rect(x: float, y: float, w: float, h: float, fill: str, *, stroke: str | None = None, radius: float = 0, opacity: float = 1.0) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "type": "vector", "shape": "polygon",
        "points": [{"x": round(x, 2), "y": round(y, 2)}, {"x": round(x + w, 2), "y": round(y, 2)}, {"x": round(x + w, 2), "y": round(y + h, 2)}, {"x": round(x, 2), "y": round(y + h, 2)}],
        "closed": True, "fill": {"color": fill, "opacity": opacity},
    }
    if stroke:
        result["stroke"] = {"color": stroke, "width": 1.2, "opacity": 1}
    if radius:
        result["corner_radii"] = [radius, radius, radius, radius]
    return result


def _line(x1: float, y1: float, x2: float, y2: float, color: str, *, width: float = 2.0, arrow: bool = False, dash: Sequence[int] | None = None) -> Dict[str, Any]:
    return {
        "type": "vector",
        "points": [{"x": round(x1, 2), "y": round(y1, 2)}, {"x": round(x2, 2), "y": round(y2, 2)}],
        "closed": False,
        "stroke": {"color": color, "width": width, "opacity": 1, **({"dash": list(dash)} if dash else {})},
        "end_marker": "arrow" if arrow else "none",
    }


def _body_nodes(spec: ScientificSlideSpec) -> List[str]:
    nodes = [item.strip() for item in spec.locked.visible_text if item.strip()]
    if len(nodes) == 1:
        if " · " in nodes[0]:
            nodes = [item.strip() for item in nodes[0].split(" · ") if item.strip()]
        elif " → " in nodes[0]:
            nodes = [item.strip() for item in nodes[0].split(" → ") if item.strip()]
    if not nodes:
        raw_nodes = spec.diagram_specification.get("nodes") if isinstance(spec.diagram_specification, dict) else None
        if isinstance(raw_nodes, str) and raw_nodes.strip() and raw_nodes.strip().upper() != "NONE":
            nodes = [part.strip(" \"“”") for part in re.split(r"\s*[,;]\s*", raw_nodes) if part.strip()]
    return nodes


def _background(spec: ScientificSlideSpec, theme: ScientificTheme, plan: VisualPlan) -> Tuple[str, bool]:
    requested = _hex(spec.background, "")
    if requested:
        dark = requested.casefold() in {theme.colors["navy"].casefold(), "#000000", "#111111", "#23292f"}
        return requested, dark
    if plan.background == "dark":
        return theme.colors["navy"], True
    return theme.colors["warm_paper"], False


def _title_block(spec: ScientificSlideSpec, theme: ScientificTheme, dark: bool) -> List[Dict[str, Any]]:
    title_color = theme.colors["white"] if dark else theme.colors["navy"]
    subtitle_color = "#D7E3EC" if dark else theme.colors["muted"]
    title_px = _pt_to_px(_parse_pt(spec.title_size, 37))
    title_h = 76 if len(spec.locked.title) <= 88 else 104
    elements = [_text(spec.locked.title, 66, 48, 1148, title_h, font_family=spec.title_font or str(theme.typography["display"]), font_size=max(title_px, _pt_to_px(34)), color=title_color, bold=True, vertical="top", name="locked-title")]
    if spec.locked.subtitle:
        elements.append(_text(spec.locked.subtitle, 68, 48 + title_h, 1120, 44, font_family=spec.body_font or str(theme.typography["body"]), font_size=max(_pt_to_px(18), _pt_to_px(_parse_pt(spec.body_size, 20) - 1)), color=subtitle_color, name="locked-subtitle"))
    return elements


def _footer(spec: ScientificSlideSpec, theme: ScientificTheme, dark: bool) -> Dict[str, Any]:
    return _text(f"G{spec.global_id:03d} · {spec.local_id:02d}/{spec.total_slides}", 66, 681, 320, 22, font_family=spec.body_font or str(theme.typography["body"]), font_size=_pt_to_px(min(_parse_pt(spec.footer_size, 11), 11.5)), color="#C6D3DD" if dark else theme.colors["muted"], name="scientific-footer", decorative=True)


def _node_box(elements: List[Dict[str, Any]], label: str, x: float, y: float, w: float, h: float, *, fill: str, text_color: str, theme: ScientificTheme, font_size: float = 25, stroke: str | None = None) -> None:
    elements.append(_rect(x, y, w, h, fill, stroke=stroke, radius=10))
    elements.append(_text(label, x + 12, y + 7, w - 24, h - 14, font_family=str(theme.typography["body"]), font_size=max(font_size, 24), color=text_color, bold=True, align="center", name="locked-visible-text"))


def _linear(elements: List[Dict[str, Any]], nodes: Sequence[str], theme: ScientificTheme, dark: bool, *, y: float = 350, barrier: bool = False) -> None:
    if not nodes:
        return
    left, right, gap = 86.0, 1194.0, 30.0
    n = len(nodes)
    box_w = min(220.0, max(120.0, (right - left - gap * (n - 1)) / n))
    used = box_w * n + gap * (n - 1)
    x = left + ((right - left) - used) / 2
    for i, node in enumerate(nodes):
        fill = theme.colors["teal"] if dark else (theme.colors["white"] if i % 2 == 0 else "#EDF4F2")
        color = theme.colors["white"] if dark else theme.colors["ink"]
        _node_box(elements, node, x, y, box_w, 86, fill=fill, text_color=color, theme=theme, stroke="#87AAA6" if not dark else "#80B7B2")
        if i < n - 1:
            line_x1, line_x2 = x + box_w + 4, x + box_w + gap - 4
            elements.append(_line(line_x1, y + 43, line_x2, y + 43, theme.colors["amber"], width=2.5, arrow=True))
            if barrier and i == max(0, n - 2):
                bx = (line_x1 + line_x2) / 2
                elements.append(_rect(bx - 4, y - 22, 8, 130, theme.colors["amber"]))
        x += box_w + gap


def _hierarchy(elements: List[Dict[str, Any]], nodes: Sequence[str], theme: ScientificTheme, dark: bool) -> None:
    nodes = list(nodes[:7])
    if not nodes:
        return
    max_w, min_w, top = 820, 470, 188
    band_h = min(70, 360 / max(len(nodes), 1))
    for i, label in enumerate(nodes):
        fraction = i / max(len(nodes) - 1, 1)
        width = max_w - (max_w - min_w) * fraction
        x, y = 92 + (max_w - width) / 2, top + i * (band_h + 8)
        fill = theme.colors["teal"] if i < 2 else (theme.colors["sage"] if i < 4 else theme.colors["amber"])
        elements.append(_rect(x, y, width, band_h, fill, radius=6, opacity=0.98))
        elements.append(_text(label, x + 20, y + 5, width - 40, band_h - 10, font_family=str(theme.typography["body"]), font_size=25, color=theme.colors["white"], bold=True, name="locked-visible-text"))
    axis_x = 1010
    elements.append(_line(axis_x, top + 4, axis_x, top + len(nodes) * (band_h + 8) - 8, "#BFCBD5" if dark else theme.colors["muted"], width=1.5, arrow=True))
    elements.append(_text("più a monte", axis_x + 18, top - 4, 150, 30, font_family=str(theme.typography["body"]), font_size=24, color=theme.colors["white"] if dark else theme.colors["ink"], name="hierarchy-axis"))
    elements.append(_text("maggiore dipendenza\ndall’esecuzione", axis_x + 18, top + 285, 170, 66, font_family=str(theme.typography["body"]), font_size=24, color="#D7E3EC" if dark else theme.colors["muted"], name="hierarchy-axis"))


def _loop(elements: List[Dict[str, Any]], nodes: Sequence[str], theme: ScientificTheme, dark: bool, *, center_label: str = "VERIFICA") -> None:
    nodes = list(nodes[:8])
    if not nodes:
        return
    cx, cy, rx, ry = 640.0, 390.0, 410.0, 190.0
    positions: list[tuple[float, float]] = []
    for i in range(len(nodes)):
        angle = -math.pi / 2 + i * (2 * math.pi / len(nodes))
        positions.append((cx + rx * math.cos(angle), cy + ry * math.sin(angle)))
    for i, ((x, y), label) in enumerate(zip(positions, nodes)):
        nx, ny = positions[(i + 1) % len(positions)]
        elements.append(_line(x, y, nx, ny, theme.colors["teal"] if not dark else "#83BDB8", width=2.0, arrow=True))
        _node_box(elements, label, x - 90, y - 34, 180, 68, fill=theme.colors["white"] if not dark else "#234966", text_color=theme.colors["ink"] if not dark else theme.colors["white"], theme=theme, font_size=24, stroke="#A9C4C1")
    elements.append(_rect(cx - 86, cy - 32, 172, 64, theme.colors["amber"], radius=32))
    elements.append(_text(center_label, cx - 76, cy - 25, 152, 50, font_family=str(theme.typography["body"]), font_size=24, color=theme.colors["white"], bold=True, align="center", name="loop-center"))


def _network(elements: List[Dict[str, Any]], nodes: Sequence[str], theme: ScientificTheme, dark: bool) -> None:
    nodes = list(nodes[:10])
    if not nodes:
        return
    cx, cy = 640.0, 390.0
    radius = 230 if len(nodes) <= 6 else 250
    for i, label in enumerate(nodes):
        angle = -math.pi / 2 + i * (2 * math.pi / len(nodes))
        x, y = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
        elements.append(_line(cx, cy, x, y, "#9EBAB8" if not dark else "#6E9F9B", width=1.6))
        _node_box(elements, label, x - 92, y - 33, 184, 66, fill=theme.colors["white"] if not dark else "#244761", text_color=theme.colors["ink"] if not dark else theme.colors["white"], theme=theme, font_size=24, stroke="#A8C4C1")
    _node_box(elements, "SISTEMA", cx - 92, cy - 40, 184, 80, fill=theme.colors["navy"] if not dark else theme.colors["teal"], text_color=theme.colors["white"], theme=theme, font_size=24)


def _matrix(elements: List[Dict[str, Any]], nodes: Sequence[str], theme: ScientificTheme, dark: bool) -> None:
    nodes = list(nodes[:12])
    if not nodes:
        return
    cols = 2 if len(nodes) <= 4 else 3
    rows = math.ceil(len(nodes) / cols)
    x0, y0, w, h, gx, gy = 92, 196, 1096, 400, 18, 18
    cw, ch = (w - gx * (cols - 1)) / cols, (h - gy * (rows - 1)) / rows
    for i, label in enumerate(nodes):
        row, col = divmod(i, cols)
        x, y = x0 + col * (cw + gx), y0 + row * (ch + gy)
        fill = theme.colors["white"] if not dark else "#244761"
        elements.append(_rect(x, y, cw, ch, fill, stroke="#C9D8D6", radius=8))
        elements.append(_text(label, x + 22, y + 12, cw - 44, ch - 24, font_family=str(theme.typography["body"]), font_size=24, color=theme.colors["ink"] if not dark else theme.colors["white"], bold=True, name="locked-visible-text"))


def _timeline(elements: List[Dict[str, Any]], nodes: Sequence[str], theme: ScientificTheme, dark: bool) -> None:
    nodes = list(nodes[:10])
    if not nodes:
        return
    x1, x2, y = 110, 1170, 385
    elements.append(_line(x1, y, x2, y, theme.colors["teal"] if not dark else "#80B7B2", width=3))
    step = (x2 - x1) / max(len(nodes) - 1, 1)
    for i, label in enumerate(nodes):
        x = x1 + i * step
        elements.append(_rect(x - 8, y - 8, 16, 16, theme.colors["amber"], radius=8))
        ty = y - 122 if i % 2 == 0 else y + 34
        elements.append(_text(label, x - min(95, step * 0.45), ty, min(190, max(130, step * 0.9)), 82, font_family=str(theme.typography["body"]), font_size=24, color=theme.colors["white"] if dark else theme.colors["ink"], bold=True, align="center", name="locked-visible-text"))


def _layered(elements: List[Dict[str, Any]], nodes: Sequence[str], theme: ScientificTheme, dark: bool) -> None:
    nodes = list(nodes[:7])
    if not nodes:
        return
    x, y, w, h = 170.0, 202.0, 940.0, 350.0
    palette = [theme.colors["navy"], theme.colors["teal"], theme.colors["sage"], theme.colors["amber"], "#7D8D9B", "#A98C73", "#8A7AA8"]
    for i, label in enumerate(nodes):
        inset = i * 42
        box_h = max(62, h - i * 48)
        elements.append(_rect(x + inset, y + inset * 0.45, w - 2 * inset, box_h, palette[i % len(palette)], radius=12, opacity=0.94))
        elements.append(_text(label, x + inset + 22, y + inset * 0.45 + 8, w - 2 * inset - 44, 44, font_family=str(theme.typography["body"]), font_size=24, color=theme.colors["white"], bold=True, align="center", name="locked-visible-text"))


def _scenario(elements: List[Dict[str, Any]], nodes: Sequence[str], theme: ScientificTheme, dark: bool) -> None:
    nodes = list(nodes[:6])
    if not nodes:
        return
    cols, rows = min(3, len(nodes)), math.ceil(len(nodes) / min(3, len(nodes)))
    for i, label in enumerate(nodes):
        row, col = divmod(i, cols)
        x, y = 84 + col * 382, 196 + row * 205
        elements.append(_rect(x, y, 350, 172, theme.colors["white"] if not dark else "#244761", stroke="#C8D9D6", radius=14))
        elements.append(_rect(x, y, 11, 172, [theme.colors["teal"], theme.colors["amber"], theme.colors["sage"]][col % 3], radius=5))
        elements.append(_text(label, x + 32, y + 18, 292, 132, font_family=str(theme.typography["body"]), font_size=24, color=theme.colors["ink"] if not dark else theme.colors["white"], bold=True, name="locked-visible-text"))


def _generic(elements: List[Dict[str, Any]], nodes: Sequence[str], theme: ScientificTheme, dark: bool) -> None:
    _linear(elements, nodes, theme, dark, y=350) if len(nodes) <= 5 else _matrix(elements, nodes, theme, dark)


def _callout(elements: List[Dict[str, Any]], spec: ScientificSlideSpec, theme: ScientificTheme, dark: bool) -> None:
    if not spec.locked.callouts:
        return
    elements.append(_rect(760, 585, 444, 70, "#FFF7EA" if not dark else "#274964", stroke=theme.colors["amber"], radius=10))
    elements.append(_text("\n".join(spec.locked.callouts), 780, 596, 404, 48, font_family=spec.body_font or str(theme.typography["body"]), font_size=_pt_to_px(max(18, _parse_pt(spec.label_size, 18))), color=theme.colors["ink"] if not dark else theme.colors["white"], bold=True, name="locked-callout"))


def _question(elements: List[Dict[str, Any]], spec: ScientificSlideSpec, theme: ScientificTheme, dark: bool) -> None:
    if spec.locked.question:
        elements.append(_text(spec.locked.question, 84, 178, 1090, 82, font_family=spec.body_font or str(theme.typography["body"]), font_size=_pt_to_px(22), color=theme.colors["white"] if dark else theme.colors["ink"], bold=True, name="locked-question"))


def render_native_ui(spec: ScientificSlideSpec, plan: VisualPlan, theme_id: str = "scientific-editorial") -> Dict[str, Any]:
    """Compile one spec into editable Template V2 text/vector primitives."""
    theme = get_theme(theme_id)
    bg, dark = _background(spec, theme, plan)
    elements: List[Dict[str, Any]] = [_rect(0, 0, STAGE_W, STAGE_H, bg)]
    elements.extend(_title_block(spec, theme, dark))
    nodes = _body_nodes(spec)
    archetype = plan.archetype
    if archetype in {"risk-chain", "source-pathway", "causal-continuum", "intervention-points", "process-map"}:
        _linear(elements, nodes, theme, dark, y=360, barrier=archetype in {"source-pathway", "intervention-points"})
    elif archetype == "hierarchy":
        _hierarchy(elements, nodes, theme, dark)
    elif archetype in {"verification-loop", "audit-loop", "synthesis"}:
        _loop(elements, nodes, theme, dark, center_label="VERIFICA" if archetype != "synthesis" else "SINTESI")
    elif archetype in {"network", "discipline-map", "system-map"}:
        _network(elements, nodes, theme, dark)
    elif archetype in {"matrix", "comparison"}:
        _matrix(elements, nodes, theme, dark)
    elif archetype == "timeline":
        _timeline(elements, nodes, theme, dark)
    elif archetype == "layered-concept":
        _layered(elements, nodes, theme, dark)
    elif archetype == "scenario":
        _scenario(elements, nodes, theme, dark)
    elif archetype == "gradient-distribution":
        _timeline(elements, nodes, theme, dark)
    elif archetype == "hero-question":
        _linear(elements, nodes[:4], theme, dark, y=420, barrier=True)
    else:
        _generic(elements, nodes, theme, dark)
    _question(elements, spec, theme, dark)
    _callout(elements, spec, theme, dark)
    if spec.locked.caption:
        elements.append(_text(spec.locked.caption, 76, 642, 650, 30, font_family=spec.body_font or str(theme.typography["body"]), font_size=_pt_to_px(18), color="#D7E3EC" if dark else theme.colors["muted"], name="locked-caption"))
    elements.append(_footer(spec, theme, dark))
    return {
        "id": f"scientific-g{spec.global_id:03d}",
        "description": spec.visual_thesis or f"Scientific slide G{spec.global_id:03d}",
        "background": bg, "components": [], "elements": elements,
        "scientific": {
            "source_hash": spec.source_hash, "global_id": spec.global_id, "archetype": plan.archetype,
            "variant": plan.variant, "theme": theme.id, "master_format": spec.master_format.value,
            "accessibility": spec.accessibility, "reading_order": spec.reading_order,
        },
    }


def _element_box(element: Dict[str, Any]) -> Tuple[float, float, float, float] | None:
    pos, size = element.get("position"), element.get("size")
    if isinstance(pos, dict) and isinstance(size, dict):
        return float(pos.get("x", 0)), float(pos.get("y", 0)), float(size.get("width", 0)), float(size.get("height", 0))
    points = element.get("points")
    if isinstance(points, list) and points:
        xs = [float(p.get("x", 0)) for p in points if isinstance(p, dict)]; ys = [float(p.get("y", 0)) for p in points if isinstance(p, dict)]
        if xs and ys:
            return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    return None


def qa_native_ui(ui: Dict[str, Any]) -> Dict[str, Any]:
    elements = [e for e in ui.get("elements", []) if isinstance(e, dict)]
    text_elements = [e for e in elements if e.get("type") in {"text", "text-list"}]
    vector_elements = [e for e in elements if e.get("type") == "vector"]
    out_of_bounds: List[str] = []; unsafe: List[str] = []; min_didactic_px: float | None = None
    for index, element in enumerate(elements):
        box = _element_box(element)
        if not box:
            continue
        x, y, w, h = box
        if x < -0.5 or y < -0.5 or x + w > STAGE_W + 0.5 or y + h > STAGE_H + 0.5:
            out_of_bounds.append(f"element[{index}]")
        if element.get("type") == "text" and not element.get("decorative"):
            if x < SAFE or y < 40 or x + w > STAGE_W - SAFE or y + h > STAGE_H - 40:
                unsafe.append(str(element.get("name") or f"element[{index}]"))
            font = element.get("font") or {}; size = float(font.get("size", 0) or 0)
            if size > 0:
                min_didactic_px = size if min_didactic_px is None else min(min_didactic_px, size)
    minimum_required_px = _pt_to_px(18)
    return {
        "status": "PASS" if not out_of_bounds and (min_didactic_px is None or min_didactic_px >= minimum_required_px) else "FAIL",
        "editable_text_elements": len(text_elements), "editable_vector_elements": len(vector_elements),
        "image_elements": sum(1 for e in elements if e.get("type") == "image"), "full_slide_raster_count": 0,
        "out_of_bounds": out_of_bounds, "safe_area_warnings": sorted(set(unsafe)),
        "minimum_didactic_font_px": min_didactic_px, "minimum_required_font_px": minimum_required_px,
    }
