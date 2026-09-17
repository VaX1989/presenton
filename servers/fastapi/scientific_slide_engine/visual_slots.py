from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Mapping

from .schema import ScientificSlideSpec

PX_PER_INCH = 96.0


@dataclass(frozen=True)
class LayoutBox:
    id: str
    role: str
    x: float
    y: float
    width: float
    height: float

    def as_pixels(self) -> dict[str, float | str]:
        return {
            "id": self.id,
            "role": self.role,
            "x": round(self.x * PX_PER_INCH, 2),
            "y": round(self.y * PX_PER_INCH, 2),
            "width": round(self.width * PX_PER_INCH, 2),
            "height": round(self.height * PX_PER_INCH, 2),
        }


def _raw(mapping: Mapping[str, object] | None) -> str:
    if not mapping:
        return ""
    return str(mapping.get("raw", "") or "")


def _quoted(text: str) -> List[str]:
    values = re.findall(r'[\"“]([^\"”]+)[\"”]', text)
    return [value.strip() for value in values if value.strip()]


def _split_labels(value: str) -> List[str]:
    quoted = _quoted(value)
    if quoted:
        return quoted
    value = value.strip()
    if not value or value.upper() in {"NONE", "N/A", "NA"}:
        return []
    return [
        part.strip(" .")
        for part in re.split(r"\s*(?:;|,|\|)\s*", value)
        if part.strip(" .")
    ]


def field_labels(
    mapping: Mapping[str, object] | None,
    *keys: str,
) -> List[str]:
    if not mapping:
        return []
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, list):
            result = [str(item).strip() for item in value if str(item).strip()]
            if result:
                return result
        if value is not None:
            result = _split_labels(str(value))
            if result:
                return result
    return []


def exact_visual_labels(spec: ScientificSlideSpec) -> List[str]:
    """Return only labels authored in the canonical visual/table/chart specification."""
    labels = field_labels(spec.diagram_specification, "exact_labels")
    if labels:
        return labels
    labels = field_labels(spec.diagram_specification, "nodes")
    if labels:
        return labels
    labels = field_labels(spec.table_specification, "exact_cell_content")
    if labels:
        return labels
    labels = field_labels(spec.chart_specification, "annotations")
    if labels:
        return labels
    return []


def chart_labels(spec: ScientificSlideSpec) -> List[str]:
    labels = field_labels(spec.chart_specification, "annotations")
    return labels or list(spec.locked.visible_text)


def table_cells(spec: ScientificSlideSpec) -> List[str]:
    labels = field_labels(spec.table_specification, "exact_cell_content")
    return labels or list(spec.locked.visible_text)


def _parse_markdown_table(raw: str) -> Dict[str, LayoutBox]:
    boxes: Dict[str, LayoutBox] = {}
    for line in raw.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 6 or cells[0].casefold() in {"id", "---"}:
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells[:6]):
            continue
        try:
            x, y, w, h = (float(cells[index]) for index in range(2, 6))
        except (ValueError, IndexError):
            continue
        box_id = cells[0]
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", box_id):
            continue
        boxes[box_id] = LayoutBox(
            box_id,
            cells[1] or box_id,
            x,
            y,
            w,
            h,
        )
    return boxes


def _parse_inline_boxes(raw: str) -> Dict[str, LayoutBox]:
    boxes: Dict[str, LayoutBox] = {}
    pattern = re.compile(
        r"(?P<id>[A-Za-z][A-Za-z0-9_-]*)\s+"
        r"x\s*(?P<x>\d+(?:\.\d+)?)\s+"
        r"y\s*(?P<y>\d+(?:\.\d+)?)\s+"
        r"w\s*(?P<w>\d+(?:\.\d+)?)\s+"
        r"h\s*(?P<h>\d+(?:\.\d+)?)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(raw):
        box_id = match.group("id")
        boxes[box_id] = LayoutBox(
            box_id,
            box_id,
            float(match.group("x")),
            float(match.group("y")),
            float(match.group("w")),
            float(match.group("h")),
        )
    return boxes


_ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "title": ("TITLE", "T1"),
    "subtitle": ("SUBTITLE", "S1"),
    "footer": ("FOOTER", "F1"),
    "question": ("QUESTION", "Q1"),
    "caption": ("CAPTION",),
    "callout": ("CALLOUT", "B1"),
    "copy": ("COPY", "L1"),
    "text": ("COPY", "L1"),
    "body": ("COPY", "L1"),
    "diagram": ("D1", "V1"),
    "hierarchy": ("D1", "V1"),
    "process": ("D1", "P1"),
    "profile": ("D1", "V1"),
    "network": ("D1", "V1"),
    "timeline": ("D1", "V1"),
    "visual": ("D1", "V1"),
    "flow": ("D1", "P1"),
    "system": ("D1", "V1"),
    "scenario": ("D1", "V1"),
    "layers": ("D1", "V1"),
    "matrix": ("M1", "TABLE"),
    "table": ("M1", "TABLE"),
    "chart": ("CH1",),
    "distribution": ("CH1",),
    "axis": ("AXIS",),
}


def _aliases_for(box: LayoutBox) -> tuple[str, ...]:
    tokens = {
        re.sub(r"[^a-z0-9]+", "", box.id.casefold()),
        re.sub(r"[^a-z0-9]+", "", box.role.casefold()),
    }
    aliases: list[str] = []
    for role, role_aliases in _ROLE_ALIASES.items():
        role_token = re.sub(r"[^a-z0-9]+", "", role)
        if any(
            token == role_token
            or token.startswith(role_token)
            or role_token in token
            for token in tokens
            if token
        ):
            for alias in role_aliases:
                if alias not in aliases:
                    aliases.append(alias)
    return tuple(aliases)


def authored_layout_boxes(
    spec: ScientificSlideSpec,
) -> Dict[str, dict[str, float | str]]:
    raw = ""
    if isinstance(spec.element_map, dict):
        raw = str(
            spec.element_map.get("element_map", "")
            or spec.element_map.get("raw", "")
            or ""
        )
    boxes = _parse_markdown_table(raw)
    if not boxes:
        boxes = _parse_inline_boxes(raw)

    result: Dict[str, dict[str, float | str]] = {}
    for box_id, box in boxes.items():
        pixel_box = box.as_pixels()
        # Preserve authored identifiers verbatim and case-insensitively.
        result[box_id] = pixel_box
        result.setdefault(box_id.upper(), pixel_box)
        result.setdefault(box.role, pixel_box)
        result.setdefault(box.role.upper(), pixel_box)
        # Also expose stable semantic aliases consumed by generic renderers.
        for alias in _aliases_for(box):
            result.setdefault(alias, pixel_box)
    return result


def visual_slot_summary(spec: ScientificSlideSpec) -> dict[str, object]:
    return {
        "authored_labels": exact_visual_labels(spec),
        "chart_labels": chart_labels(spec),
        "table_cells": table_cells(spec),
        "layout_boxes": authored_layout_boxes(spec),
        "diagram_raw": _raw(spec.diagram_specification),
        "table_raw": _raw(spec.table_specification),
        "chart_raw": _raw(spec.chart_specification),
    }
