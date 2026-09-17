from __future__ import annotations

import math
from typing import Any, Dict, List

from .renderer import SAFE, _element_box, _pt_to_px, qa_native_ui


def _element_text(element: Dict[str, Any]) -> str:
    runs = element.get("runs")
    if not isinstance(runs, list):
        return ""
    return "".join(
        str(run.get("text", "")) for run in runs if isinstance(run, dict)
    )


def _estimated_text_fit(element: Dict[str, Any]) -> dict[str, float | int | str] | None:
    if element.get("type") != "text" or element.get("decorative"):
        return None
    box = _element_box(element)
    if not box:
        return None
    _, _, width, height = box
    font = element.get("font") if isinstance(element.get("font"), dict) else {}
    size = float(font.get("size", 0) or 0)
    text = _element_text(element)
    if size <= 0 or width <= 0 or height <= 0 or not text:
        return None

    # Approximation only: export-core performs the authoritative layout. We use
    # a deliberately tolerant estimate to catch clear clipping without forcing
    # font shrinking. 0.52em is a conservative average glyph width for the
    # academic sans/serif fonts used by the scientific theme.
    chars_per_line = max(1, int(width / max(size * 0.52, 1)))
    estimated_lines = 0
    for explicit_line in text.split("\n") or [text]:
        estimated_lines += max(1, math.ceil(len(explicit_line) / chars_per_line))
    line_height = float(font.get("line_height", 1.08) or 1.08) * size
    required_height = estimated_lines * line_height
    ratio = required_height / height
    return {
        "name": str(element.get("name") or "text"),
        "estimated_lines": estimated_lines,
        "required_height": round(required_height, 2),
        "box_height": round(height, 2),
        "fit_ratio": round(ratio, 3),
    }


def qa_strict_native_ui(ui: Dict[str, Any]) -> Dict[str, Any]:
    """Strict structural QA for scientific native UI.

    Hard gates: stage bounds, 18 pt minimum, safe-area violations and clear
    text clipping. Borderline text-fit estimates remain warnings and are
    resolved by the rendered PDF/PNG QA layer.
    """
    report = dict(qa_native_ui(ui))
    elements = [e for e in ui.get("elements", []) if isinstance(e, dict)]
    overflow_errors: List[dict[str, float | int | str]] = []
    overflow_warnings: List[dict[str, float | int | str]] = []
    for element in elements:
        fit = _estimated_text_fit(element)
        if not fit:
            continue
        ratio = float(fit["fit_ratio"])
        if ratio > 1.55:
            overflow_errors.append(fit)
        elif ratio > 1.10:
            overflow_warnings.append(fit)

    safe_area_warnings = list(report.get("safe_area_warnings") or [])
    min_px = report.get("minimum_didactic_font_px")
    min_required = float(report.get("minimum_required_font_px") or _pt_to_px(18))
    font_ok = min_px is None or float(min_px) >= min_required
    hard_fail = bool(
        report.get("out_of_bounds")
        or safe_area_warnings
        or overflow_errors
        or not font_ok
    )
    report.update(
        {
            "status": "FAIL" if hard_fail else "PASS",
            "safe_area_px": SAFE,
            "safe_area_status": "FAIL" if safe_area_warnings else "PASS",
            "font_minimum_status": "PASS" if font_ok else "FAIL",
            "text_overflow_errors": overflow_errors,
            "text_overflow_warnings": overflow_warnings,
            "text_overflow_status": "FAIL" if overflow_errors else (
                "WARN" if overflow_warnings else "PASS"
            ),
        }
    )
    return report


__all__ = ["qa_strict_native_ui"]
