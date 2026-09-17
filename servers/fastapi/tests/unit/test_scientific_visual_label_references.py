from scientific_slide_engine.schema import LockedContent, ScientificSlideSpec
from scientific_slide_engine.visual_slots import exact_visual_labels


def test_exact_labels_visible_text_is_a_reference_not_literal_copy():
    spec = ScientificSlideSpec(
        source_file="synthetic.md",
        deck_id="99",
        global_id=901,
        local_id=1,
        total_slides=1,
        slide_type="diagram",
        locked=LockedContent(visible_text=["Source", "Barrier", "Receiver"]),
        diagram_specification={"exact_labels": "visible text", "raw": "EXACT_LABELS: visible text"},
    )
    assert exact_visual_labels(spec) == ["Source", "Barrier", "Receiver"]


def test_visible_text_reference_keeps_authored_quoted_extras():
    spec = ScientificSlideSpec(
        source_file="synthetic.md",
        deck_id="99",
        global_id=902,
        local_id=1,
        total_slides=1,
        slide_type="diagram",
        locked=LockedContent(visible_text=["Exposure", "Susceptibility"]),
        diagram_specification={
            "exact_labels": "visible text plus “decision”",
            "raw": "EXACT_LABELS: visible text plus “decision”",
        },
    )
    assert exact_visual_labels(spec) == ["Exposure", "Susceptibility", "decision"]
