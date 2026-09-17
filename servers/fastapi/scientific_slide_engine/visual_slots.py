from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping

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
    values = re.findall(r"[\"“]([^\"”]+)[\"”]", text)
    return [value.strip() for value in values if value.strip()]


def _split_labels(value: str) -> List[str]:
    quoted = _quoted(value)
    if quoted:
        return quoted
    value = value.strip()
    if not value or value.upper() in {"NONE", "N/A", "NA"}:
        return []
    return [part.strip(" .") for part in re.split(r"\s*(?:;|,|\|)\s*", value) if part.strip(" .")]


def field_labels(mapping: Mapping[str, object] | None, *keys: str) -> List[str]:
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
        # Node records sometimes include coordinates after the label. Preserve a
        # quoted authored label when present; otherwise retain the authored node.
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
        boxes[box_id] = LayoutBox(box_id, cells[1] or box_id, x, y, w, h)
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
            box_id, box_id,
            float(match.group("x")), float(match.group("y")),
            float(match.group("w")), float(match.group("h")),
        )
    return boxes


def authored_layout_boxes(spec: ScientificSlideSpec) -> Dict[str, dict[str, float | str]]:
    raw = ""
    if isinstance(spec.element_map, dict):
        raw = str(spec.element_map.get("element_map", "") or spec.element_map.get("raw", "") or "")
    boxes = _parse_markdown_table(raw)
    if not boxes:
        boxes = _parse_inline_boxes(raw)
    return {box_id: box.as_pixels() for box_id, box in boxes.items()}


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
