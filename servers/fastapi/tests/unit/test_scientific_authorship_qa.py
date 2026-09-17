import pytest

from scientific_slide_engine.authorship_qa import (
    RICH_SECTION_NAMES,
    assert_rich_authorship,
    audit_rich_authorship,
)
from scientific_slide_engine.schema import LockedContent, MasterFormat, ScientificSlideSpec


def _spec_with_unattributed_grid() -> ScientificSlideSpec:
    raw = {name: "NONE" for name in RICH_SECTION_NAMES}
    raw.update(
        {
            "identity": "SLIDE_TYPE: diagram",
            "didactic_function": "LEARNING_OBJECTIVE: Explain.",
            "final_visible_copy": 'TITLE: "Synthetic"',
            "layout_specification": 'CANVAS: 13.333 × 7.5\nBACKGROUND: #FFFFFF\nSAFE_AREA: 0.55"',
            "typography": "NONE",
            "color_specification": "NONE",
            "asset_specification": "NONE",
            "diagram_specification": "NONE",
            "table_specification": "NONE",
            "chart_specification": "NONE",
            "accessibility": "NONE",
            "animation": "NONE",
        }
    )
    return ScientificSlideSpec(
        source_file="synthetic.md",
        deck_id="99",
        global_id=901,
        local_id=1,
        total_slides=1,
        slide_type="diagram",
        master_format=MasterFormat.RICH_A_S_MASTER,
        locked=LockedContent(title="Synthetic"),
        canvas="13.333 × 7.5",
        background="#FFFFFF",
        grid="12 columns",  # intentionally not authored in section F
        safe_area='0.55"',
        element_map={"raw": raw["layout_specification"]},
        color_roles={"raw": raw["color_specification"]},
        asset_specification={"raw": raw["asset_specification"]},
        diagram_specification={"raw": raw["diagram_specification"]},
        table_specification={"raw": raw["table_specification"]},
        chart_specification={"raw": raw["chart_specification"]},
        accessibility={"raw": raw["accessibility"]},
        animation={"raw": raw["animation"]},
        raw_sections=raw,
        source_block="# SLIDE 901",
    )


def test_rich_authorship_qa_rejects_renderer_friendly_parser_defaults():
    spec = _spec_with_unattributed_grid()
    report = audit_rich_authorship(spec)
    assert report["status"] == "FAIL"
    assert report["inferred_fields"] == ["grid"]
    with pytest.raises(ValueError, match="rich A-S authorship QA failed"):
        assert_rich_authorship(spec)
