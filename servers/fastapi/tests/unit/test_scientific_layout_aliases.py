from scientific_slide_engine.schema import LockedContent, ScientificSlideSpec
from scientific_slide_engine.visual_slots import authored_layout_boxes


def test_inline_element_map_exposes_renderer_semantic_aliases():
    spec = ScientificSlideSpec(
        source_file="synthetic.md",
        deck_id="99",
        global_id=901,
        local_id=1,
        total_slides=1,
        slide_type="hierarchy",
        locked=LockedContent(title="Synthetic"),
        element_map={
            "element_map": (
                "title x0.7 y0.55 w11.8 h0.8; "
                "hierarchy x1.2 y1.65 w8.8 h4.7; "
                "axis x10.5 y1.85 w1.8 h4.2; "
                "footer x0.7 y7.0 w3.5 h0.2"
            )
        },
    )
    boxes = authored_layout_boxes(spec)

    assert boxes["TITLE"] == boxes["title"]
    assert boxes["T1"] == boxes["title"]
    assert boxes["D1"] == boxes["hierarchy"]
    assert boxes["V1"] == boxes["hierarchy"]
    assert boxes["AXIS"] == boxes["axis"]
    assert boxes["FOOTER"] == boxes["footer"]
    assert boxes["F1"] == boxes["footer"]
    assert boxes["TITLE"]["x"] == 67.2
    assert boxes["D1"]["width"] == 844.8
