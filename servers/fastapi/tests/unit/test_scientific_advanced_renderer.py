from scientific_slide_engine.compiler import compile_strict
from scientific_slide_engine.parser import parse_master_text


PROCESS_MASTER = """# DECK 99 — Synthetic process
- **DECK_ID:** 99
- **Numero slide:** 1

### G901 · 01/1 — GENERAL
**VISIBLE COPY:** TITLE `Validated process`. Steps: `Input · Preparation · Process · Verification · Release`.
**VISUAL:** process map with ordered states and handoffs.
**NOTES:** Exact process notes.
**SOURCES:** S01.
"""

CAUSAL_MASTER = """# DECK 99 — Synthetic causal chain
- **DECK_ID:** 99
- **Numero slide:** 1

### G902 · 01/1 — GENERAL
**VISIBLE COPY:** TITLE `Causal chain`. Nodes: `Source · Pathway · Exposure · Effect`.
**VISUAL:** causal continuum from source to effect.
**NOTES:** Exact causal notes.
**SOURCES:** S01.
"""

HIERARCHY_MASTER = """# DECK 99 — Synthetic hierarchy
- **DECK_ID:** 99
- **Numero slide:** 1

### G903 · 01/1 — GENERAL
**VISIBLE COPY:** TITLE `Control hierarchy`. Steps: `Level one · Level two · Level three · Level four · Level five`.
**VISUAL:** hierarchy pyramid ordered by robustness.
**NOTES:** Exact hierarchy notes.
**SOURCES:** S01.
"""

TIMELINE_MASTER = """# DECK 99 — Synthetic timeline
- **DECK_ID:** 99
- **Numero slide:** 1

### G904 · 01/1 — GENERAL
**VISIBLE COPY:** TITLE `Validated timeline`. Steps: `Stage A · Stage B · Stage C · Stage D · Stage E · Stage F`.
**VISUAL:** timeline of ordered events.
**NOTES:** Exact timeline notes.
**SOURCES:** S01.
"""


def test_process_map_uses_differentiated_native_renderer():
    result = compile_strict(parse_master_text(PROCESS_MASTER, "process.md"))
    slide = result.slides[0]
    assert slide["archetype"] == "process-map"
    assert slide["ui"]["scientific"]["renderer_variant"] == "advanced-scientific"
    assert slide["ui_qa"]["status"] == "PASS"
    assert slide["ui_qa"]["editable_text_elements"] > 0
    assert slide["ui_qa"]["editable_vector_elements"] > 0
    assert slide["ui_qa"]["full_slide_raster_count"] == 0
    assert all(element.get("type") != "image" for element in slide["ui"]["elements"])


def test_causal_chain_preserves_exact_locked_copy_without_rasterization():
    result = compile_strict(parse_master_text(CAUSAL_MASTER, "causal.md"))
    slide = result.slides[0]
    assert slide["archetype"] == "causal-continuum"
    assert slide["ui"]["scientific"]["renderer_variant"] == "advanced-scientific"
    rendered_text = "\n".join(
        "".join(run.get("text", "") for run in element.get("runs", []))
        for element in slide["ui"]["elements"]
        if element.get("type") == "text"
    )
    for locked in ("Causal chain", "Source", "Pathway", "Exposure", "Effect"):
        assert locked in rendered_text
    assert slide["speaker_notes_final"] == "Exact causal notes."


def test_hierarchy_is_native_editable_and_safe():
    slide = compile_strict(parse_master_text(HIERARCHY_MASTER, "hierarchy.md")).slides[0]
    assert slide["archetype"] == "hierarchy"
    assert slide["ui"]["scientific"]["renderer_variant"] == "advanced-scientific"
    assert slide["ui_qa"]["status"] == "PASS"
    assert slide["ui_qa"]["safe_area_status"] == "PASS"
    assert slide["ui_qa"]["full_slide_raster_count"] == 0


def test_timeline_clamps_text_inside_safe_area():
    slide = compile_strict(parse_master_text(TIMELINE_MASTER, "timeline.md")).slides[0]
    assert slide["archetype"] == "timeline"
    assert slide["ui"]["scientific"]["renderer_variant"] == "advanced-scientific"
    assert slide["ui_qa"]["status"] == "PASS"
    assert slide["ui_qa"]["safe_area_status"] == "PASS"
    assert not slide["ui_qa"]["out_of_bounds"]
