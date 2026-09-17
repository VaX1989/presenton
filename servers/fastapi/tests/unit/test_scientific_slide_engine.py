import pytest

from scientific_slide_engine.archetypes import ArchetypeRegistry
from scientific_slide_engine.capabilities import scientific_capabilities
from scientific_slide_engine.compiler import compile_strict
from scientific_slide_engine.content_lock import ContentLockViolation, assert_locked_content
from scientific_slide_engine.parser import MasterParseError, detect_master_format, parse_master_text
from scientific_slide_engine.schema import MasterFormat
from scientific_slide_engine.service import build_persisted_slide_content, persisted_locked_view, validate_request_count

COMPACT = """# DECK 99 — Synthetic
- **DECK_ID:** 99
- **Numero slide:** 2

### G901 · 01/2 — GENERAL
**VISIBLE COPY:** TITLE `First title`. SUBTITLE `Sub`. Text: `A · B · C`. Question: `Why?`
**VISUAL:** causal continuum.
**NOTES:** Exact first notes.
**SOURCES:** S01; S02.

### G902 · 02/2 — GENERAL · chiusura
**VISIBLE COPY:** TITLE `Second title`. Nodes: `One · Two`. Callout: `Remember this.`
**VISUAL:** closing loop.
**NOTES:** Exact second notes.
**SOURCES:** S02.
"""

RICH = '''# DECK 98 — Rich Synthetic
DECK_ID: 98
Total slides: 1

# SLIDE 801 — 1/1
## A. Identity
DECK: 98
GLOBAL: 801
LOCAL: 1
BLUEPRINT_REFERENCE: TEST/S01 · hierarchy
SLIDE_TYPE: hierarchy
NARRATIVE_PHASE: controllo
GENERALITY_LEVEL: GENERAL
PRIORITY: FONDAMENTALE
## B. Didactic function
LEARNING_OBJECTIVE: Ordinare i controlli.
DIDACTIC_FUNCTION: Principio preventivo core.
ONE_KEY_TAKEAWAY: Le misure a monte sono più robuste.
LINK_FROM_PREVIOUS: Health protection.
LINK_TO_NEXT: Ridondanza.
## C. Final visible copy
TITLE: "La gerarchia dei controlli ordina le misure per robustezza"
SUBTITLE: NONE
VISIBLE_TEXT:
- "1 · Eliminazione"
- "2 · Sostituzione"
- "3 · Controlli ingegneristici"
- "4 · Controlli organizzativi"
- "5 · DPI"
CALLOUTS: "Priorità alle misure che agiscono sulla sorgente e sul percorso."
CAPTION: NONE
QUESTION: NONE
## D. Copy quality audit
TONE: academic / institutional
AI_CLICHE_CHECK: PASS
## E. Visual concept
VISUAL_THESIS: La gerarchia è un ordine di preferenza.
VISUAL_TYPE: diagram
COMPOSITION: Fondo Navy; cinque bande orizzontali.
FOCAL_POINT: eliminazione/sostituzione top.
SECONDARY_ELEMENTS: dependency axis.
VISUAL_HIERARCHY: bands → axis → callout.
## F. Layout specification
CANVAS: 13.333 × 7.5
BACKGROUND: #17324D
GRID: 12 columns
SAFE_AREA: 0.55"
ELEMENT_MAP: title x0.7 y0.55 w11.8 h0.8; hierarchy x1.2 y1.65 w8.8 h4.7; footer.
## G. Typography
TITLE_FONT: Aptos Display
TITLE_SIZE: 37 pt
TITLE_WEIGHT: Bold
BODY_FONT: Aptos
BODY_SIZE: 21 pt
LABEL_SIZE: 18 pt
FOOTER_SIZE: 11.5 pt
LINE_SPACING: 1.05
ALIGNMENT_RULES: labels left within bands.
## H. Color specification
BACKGROUND: #17324D
PRIMARY: #FFFFFF
SECONDARY: #2D7F7A
ACCENT: #B56A2E
TEXT: #23292F
MUTED: #6F777C
SEMANTIC_COLOR_RULES: upper controls Teal.
## I. Image / photographic asset
ASSET_TYPE: NONE
## J. Diagram specification
PURPOSE: Explain hierarchy.
CONTAINER: x1.2 y1.65 w8.8 h4.7
NODES: Eliminazione, Sostituzione, Controlli ingegneristici, Controlli organizzativi, DPI
CONNECTIONS: ordered top to bottom.
EXACT_LABELS: visible text.
SHAPES: five bands.
ARROWS: axis arrow.
HIERARCHY: upper bands dominant.
COLORS: Teal, Sage, Amber.
LEGEND: NONE
ANNOTATIONS: upstream.
BUILD_ORDER: NONE
ACCESSIBILITY_DESCRIPTION: Five control levels ordered from upstream to PPE.
## K. Table / matrix specification
TABLE: NONE
## L. Chart / data specification
CHART: NONE
## M. Speaker notes — final lecturer script
SPEAKER_NOTES_FINAL:
“Le misure più in alto nella gerarchia riducono l’esposizione a monte.
La seconda riga delle note deve restare identica.”
## N. Instructor cue
INSTRUCTOR_CUE: tempo 2 min; collegare al modello sorgente-percorso.
## O. Sources
[Sources]
S01 — Synthetic source.
S02 — Another source.
[/Sources]
## P. Accessibility
ALT_TEXT_REQUIRED: YES.
READING_ORDER: title → hierarchy → callout → footer.
COLOR_INDEPENDENCE: labels.
CONTRAST_NOTES: high.
PROJECTOR_READABILITY: ≥18 pt.
## Q. Animation / build
NONE
## R. Production constraints
Do not reorder levels. Font shrinking prohibited.
## S. Acceptance criteria
Five levels visible; exact labels; notes preserved.
'''


def test_compact_parser_detects_slide_boundaries_and_preserves_notes():
    specs = parse_master_text(COMPACT, "synthetic.md")
    assert detect_master_format(COMPACT) == MasterFormat.COMPACT_FINAL_LEGACY
    assert [s.global_id for s in specs] == [901, 902]
    assert specs[0].locked.title == "First title"
    assert specs[0].locked.visible_text == ["A", "B", "C"]
    assert specs[0].locked.speaker_notes_final == "Exact first notes."
    assert specs[0].source_hash


def test_realistic_rich_a_s_parser_populates_every_production_dimension():
    spec = parse_master_text(RICH, "rich.md")[0]
    assert detect_master_format(RICH) == MasterFormat.RICH_A_S_MASTER
    assert spec.global_id == 801 and spec.local_id == 1 and spec.total_slides == 1
    assert spec.blueprint_reference == "TEST/S01 · hierarchy"
    assert spec.slide_type == "hierarchy"
    assert spec.narrative_phase == "controllo"
    assert spec.generality_level == "GENERAL"
    assert spec.priority == "FONDAMENTALE"
    assert spec.learning_objective == "Ordinare i controlli."
    assert spec.didactic_function == "Principio preventivo core."
    assert spec.one_key_takeaway == "Le misure a monte sono più robuste."
    assert spec.locked.title.startswith("La gerarchia")
    assert spec.locked.subtitle == ""
    assert len(spec.locked.visible_text) == 5
    assert spec.locked.callouts == ["Priorità alle misure che agiscono sulla sorgente e sul percorso."]
    assert spec.locked.speaker_notes_final == "Le misure più in alto nella gerarchia riducono l’esposizione a monte.\nLa seconda riga delle note deve restare identica."
    assert spec.visual_type == "diagram"
    assert spec.background == "#17324D"
    assert spec.title_font == "Aptos Display" and spec.body_font == "Aptos"
    assert "element_map" in spec.element_map
    assert spec.diagram_specification["nodes"].startswith("Eliminazione")
    assert spec.table_specification["table"] == "NONE"
    assert spec.chart_specification["chart"] == "NONE"
    assert spec.sources == ["S01 — Synthetic source.", "S02 — Another source."]
    assert spec.accessibility["alt_text_required"] == "YES."
    assert spec.projector_readability == "≥18 pt."
    assert spec.production_constraints == ["Do not reorder levels. Font shrinking prohibited."]
    assert spec.acceptance_criteria == ["Five levels visible; exact labels; notes preserved."]
    assert set(spec.raw_sections) == {
        "identity", "didactic_function", "final_visible_copy", "copy_quality_audit", "visual_concept",
        "layout_specification", "typography", "color_specification", "asset_specification",
        "diagram_specification", "table_specification", "chart_specification", "speaker_notes",
        "instructor_cue", "sources", "accessibility", "animation", "production_constraints",
        "acceptance_criteria",
    }


def test_hash_is_stable_across_line_endings():
    assert parse_master_text(RICH, "rich.md")[0].source_hash == parse_master_text(RICH.replace("\n", "\r\n"), "rich.md")[0].source_hash


def test_malformed_rich_sections_and_duplicates_fail_loudly():
    with pytest.raises(MasterParseError):
        parse_master_text(RICH.replace("## M. Speaker notes — final lecturer script", "## T. Speaker notes"), "broken.md")
    with pytest.raises(MasterParseError):
        parse_master_text(RICH.replace("## S. Acceptance criteria", "## A. Acceptance criteria"), "broken.md")
    with pytest.raises(MasterParseError):
        parse_master_text(RICH.replace("GLOBAL: 801", "GLOBAL: 999"), "broken.md")


def test_duplicate_and_missing_slide_detection_compact():
    with pytest.raises(MasterParseError):
        parse_master_text(COMPACT.replace("G902 · 02/2", "G901 · 02/2"), "broken.md")
    with pytest.raises(MasterParseError):
        parse_master_text(COMPACT.replace("02/2", "03/2"), "broken.md")


def test_strict_mode_rejects_content_mutation():
    spec = parse_master_text(COMPACT, "synthetic.md")[0]
    generated = {"title": spec.locked.title, "subtitle": spec.locked.subtitle, "visible_text": spec.locked.visible_text, "callouts": spec.locked.callouts, "caption": spec.locked.caption, "question": spec.locked.question, "speaker_notes_final": spec.locked.speaker_notes_final}
    assert_locked_content(spec, generated)
    generated["title"] = "Rewritten"
    with pytest.raises(ContentLockViolation):
        assert_locked_content(spec, generated)


def test_native_strict_compiler_outputs_editable_text_and_vectors_not_raster():
    spec = parse_master_text(RICH, "rich.md")[0]
    result = compile_strict([spec])
    slide = result.slides[0]
    assert result.render_contract == "presenton_native_template_v2_ui"
    assert slide["archetype"] == "hierarchy"
    assert slide["ui_qa"]["status"] == "PASS"
    assert slide["ui_qa"]["editable_text_elements"] > 0
    assert slide["ui_qa"]["editable_vector_elements"] > 0
    assert slide["ui_qa"]["full_slide_raster_count"] == 0
    assert slide["ui_qa"]["image_elements"] == 0
    assert all(e.get("type") != "image" for e in slide["ui"]["elements"])


def test_native_presenton_persistence_contract_preserves_locked_copy_and_notes():
    spec = parse_master_text(RICH, "rich.md")[0]
    result = compile_strict([spec])
    content = build_persisted_slide_content(spec, result.slides[0])
    view = persisted_locked_view(content, spec.locked.speaker_notes_final)
    assert_locked_content(spec, view)
    assert view["speaker_notes_final"] == spec.locked.speaker_notes_final


def test_68_slide_request_path_is_accepted_by_validation_and_strict_compiler():
    slides = []
    for i in range(68):
        slides.append(f"### G{700+i:03d} · {i+1:02d}/68 — GENERAL\n**VISIBLE COPY:** TITLE `Slide {i+1}`. Text: `Locked {i+1}`.\n**VISUAL:** simple diagram.\n**NOTES:** Notes {i+1}.\n**SOURCES:** S01.\n")
    master = "# synthetic\n- **DECK_ID:** 97\n- **Numero slide:** 68\n\n" + "\n".join(slides)
    specs = parse_master_text(master, "68.md")
    validate_request_count(specs)
    result = compile_strict(specs)
    assert len(result.slides) == 68
    assert result.content_lock_status == "PASS"


def test_archetype_registry_theme_and_capabilities():
    registry = ArchetypeRegistry()
    assert registry.resolve("hierarchy of controls", node_count=5).id == "hierarchy"
    assert registry.resolve("timeline", node_count=4).id == "timeline"
    assert registry.resolve("One Health network map", node_count=5).id in {"network", "system-map"}
    caps = scientific_capabilities()
    assert caps["max_slides"] >= 68
    assert caps["strict_materialize_supported"] is True
    assert caps["speaker_notes_supported"] is True
    assert caps["native_editable_ui_supported"] is True
    assert caps["preferred_master_format"] == "rich_a_s_master"


def test_public_fixture_contains_no_private_identifiers():
    assert "VaX1989" not in COMPACT + RICH
    assert "UniCa" not in COMPACT + RICH
