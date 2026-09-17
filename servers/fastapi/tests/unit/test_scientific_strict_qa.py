from scientific_slide_engine.renderer import _text
from scientific_slide_engine.strict_qa import qa_strict_native_ui


def _ui(element):
    return {
        "id": "synthetic",
        "background": "#FFFFFF",
        "components": [],
        "elements": [element],
    }


def test_safe_area_is_a_hard_gate():
    element = _text(
        "Canonical",
        12,
        100,
        300,
        60,
        font_family="Aptos",
        font_size=28,
        color="#000000",
    )
    report = qa_strict_native_ui(_ui(element))
    assert report["status"] == "FAIL"
    assert report["safe_area_status"] == "FAIL"


def test_minimum_18pt_is_a_hard_gate():
    element = _text(
        "Canonical",
        100,
        100,
        300,
        60,
        font_family="Aptos",
        font_size=20,  # pixels, below 18 pt (=24 px)
        color="#000000",
    )
    report = qa_strict_native_ui(_ui(element))
    assert report["status"] == "FAIL"
    assert report["font_minimum_status"] == "FAIL"


def test_clear_text_overflow_is_a_hard_gate():
    element = _text(
        "A very long canonical sentence that cannot possibly fit inside this tiny box without clipping",
        100,
        100,
        110,
        30,
        font_family="Aptos",
        font_size=28,
        color="#000000",
    )
    report = qa_strict_native_ui(_ui(element))
    assert report["status"] == "FAIL"
    assert report["text_overflow_status"] == "FAIL"
    assert report["text_overflow_errors"]


def test_safe_readable_editable_text_passes():
    element = _text(
        "Canonical label",
        100,
        100,
        320,
        70,
        font_family="Aptos",
        font_size=28,
        color="#000000",
    )
    report = qa_strict_native_ui(_ui(element))
    assert report["status"] == "PASS"
    assert report["safe_area_status"] == "PASS"
    assert report["font_minimum_status"] == "PASS"
    assert report["text_overflow_status"] == "PASS"
