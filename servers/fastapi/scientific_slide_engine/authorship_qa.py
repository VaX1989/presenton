from __future__ import annotations

import re
from typing import Mapping

from .schema import MasterFormat, ScientificSlideSpec


RICH_SECTION_NAMES = (
    "identity",
    "didactic_function",
    "final_visible_copy",
    "copy_quality_audit",
    "visual_concept",
    "layout_specification",
    "typography",
    "color_specification",
    "asset_specification",
    "diagram_specification",
    "table_specification",
    "chart_specification",
    "speaker_notes",
    "instructor_cue",
    "sources",
    "accessibility",
    "animation",
    "production_constraints",
    "acceptance_criteria",
)

# Convenience fields that historically had renderer-friendly defaults. In a rich
# canonical master those values must be authored. If a non-empty value exists in
# ScientificSlideSpec but the corresponding canonical key is absent, the parser
# has inferred scientific production data and strict mode must refuse it.
AUTHORED_SCALARS: Mapping[str, tuple[str, str]] = {
    "canvas": ("layout_specification", "CANVAS"),
    "background": ("layout_specification", "BACKGROUND"),
    "grid": ("layout_specification", "GRID"),
    "safe_area": ("layout_specification", "SAFE_AREA"),
    "title_font": ("typography", "TITLE_FONT"),
    "title_size": ("typography", "TITLE_SIZE"),
    "title_weight": ("typography", "TITLE_WEIGHT"),
    "body_font": ("typography", "BODY_FONT"),
    "body_size": ("typography", "BODY_SIZE"),
    "label_size": ("typography", "LABEL_SIZE"),
    "footer_size": ("typography", "FOOTER_SIZE"),
    "alignment_rules": ("typography", "ALIGNMENT_RULES"),
    "reading_order": ("accessibility", "READING_ORDER"),
    "projector_readability": ("accessibility", "PROJECTOR_READABILITY"),
}


def _has_key(raw: str, key: str) -> bool:
    return bool(
        re.search(
            rf"^\s*{re.escape(key)}\s*:\s*",
            raw,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )


def _has_any_key(raw: str, keys: tuple[str, ...]) -> bool:
    return any(_has_key(raw, key) for key in keys)


def audit_rich_authorship(spec: ScientificSlideSpec) -> dict[str, object]:
    if spec.master_format is not MasterFormat.RICH_A_S_MASTER:
        return {
            "status": "SKIP",
            "reason": "legacy compact compatibility source",
            "inferred_fields": [],
            "missing_sections": [],
        }

    missing_sections = [
        name for name in RICH_SECTION_NAMES if name not in spec.raw_sections
    ]
    inferred: list[str] = []
    for attribute, (section_name, canonical_key) in AUTHORED_SCALARS.items():
        value = getattr(spec, attribute, "")
        if not str(value or "").strip():
            continue
        raw = spec.raw_sections.get(section_name, "")
        if not _has_key(raw, canonical_key):
            inferred.append(attribute)

    # CONTRAST_NOTES and CONTRAST are canonical aliases; a populated convenience
    # value must be traceable to at least one of them.
    if str(spec.contrast or "").strip():
        raw = spec.raw_sections.get("accessibility", "")
        if not _has_any_key(raw, ("CONTRAST_NOTES", "CONTRAST")):
            inferred.append("contrast")

    # Structured A-S sections that drive renderer semantics must retain their
    # complete authored source alongside parsed fields.
    for attribute, section_name in (
        ("element_map", "layout_specification"),
        ("color_roles", "color_specification"),
        ("asset_specification", "asset_specification"),
        ("diagram_specification", "diagram_specification"),
        ("table_specification", "table_specification"),
        ("chart_specification", "chart_specification"),
        ("accessibility", "accessibility"),
        ("animation", "animation"),
    ):
        value = getattr(spec, attribute, None)
        if isinstance(value, dict):
            raw = value.get("raw")
            expected = spec.raw_sections.get(section_name, "")
            if raw is None or str(raw).strip() != str(expected).strip():
                inferred.append(f"{attribute}.raw")

    status = "PASS" if not missing_sections and not inferred else "FAIL"
    return {
        "status": status,
        "inferred_fields": sorted(set(inferred)),
        "missing_sections": missing_sections,
    }


def assert_rich_authorship(spec: ScientificSlideSpec) -> None:
    report = audit_rich_authorship(spec)
    if report["status"] == "FAIL":
        raise ValueError(
            f"G{spec.global_id:03d}: rich A-S authorship QA failed: {report}"
        )


__all__ = ["audit_rich_authorship", "assert_rich_authorship"]
