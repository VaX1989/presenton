import pytest

from scientific_slide_engine.content_lock import ContentLockViolation, assert_locked_content
from scientific_slide_engine.parser import MasterParseError, parse_master_text

SYNTHETIC = """# DECK 99 — Synthetic
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


def test_parser_detects_slide_boundaries_and_preserves_notes():
    specs = parse_master_text(SYNTHETIC, "synthetic.md")
    assert [s.global_id for s in specs] == [901, 902]
    assert specs[0].locked.title == "First title"
    assert specs[0].locked.speaker_notes_final == "Exact first notes."
    assert specs[0].source_hash


def test_hash_is_stable_across_line_endings():
    assert parse_master_text(SYNTHETIC, "synthetic.md")[0].source_hash == parse_master_text(SYNTHETIC.replace("\n", "\r\n"), "synthetic.md")[0].source_hash


def test_malformed_slide_fails_loudly():
    with pytest.raises(MasterParseError):
        parse_master_text(SYNTHETIC.replace("**NOTES:** Exact second notes.\n", ""), "broken.md")


def test_duplicate_slide_id_detection():
    with pytest.raises(MasterParseError):
        parse_master_text(SYNTHETIC.replace("G902 · 02/2", "G901 · 02/2"), "broken.md")


def test_missing_slide_id_detection():
    with pytest.raises(MasterParseError):
        parse_master_text(SYNTHETIC.replace("02/2", "03/2"), "broken.md")


def test_strict_mode_rejects_content_mutation():
    spec = parse_master_text(SYNTHETIC, "synthetic.md")[0]
    generated = {
        "title": spec.locked.title,
        "subtitle": spec.locked.subtitle,
        "visible_text": spec.locked.visible_text,
        "callouts": spec.locked.callouts,
        "caption": spec.locked.caption,
        "question": spec.locked.question,
        "speaker_notes_final": spec.locked.speaker_notes_final,
        "raw_visible_copy": spec.locked.raw_visible_copy,
    }
    assert_locked_content(spec, generated)
    generated["title"] = "Rewritten"
    with pytest.raises(ContentLockViolation):
        assert_locked_content(spec, generated)


def test_68_slide_synthetic_deck_is_accepted():
    slides = []
    for i in range(68):
        slides.append(f"### G{700+i:03d} · {i+1:02d}/68 — GENERAL\n**VISIBLE COPY:** TITLE `Slide {i+1}`. Text: `Locked {i+1}`.\n**VISUAL:** simple diagram.\n**NOTES:** Notes {i+1}.\n**SOURCES:** S01.\n")
    master = "# synthetic\n- **DECK_ID:** 98\n- **Numero slide:** 68\n\n" + "\n".join(slides)
    assert len(parse_master_text(master, "68.md")) == 68


def test_public_fixture_contains_no_private_identifiers():
    assert "VaX1989" not in SYNTHETIC
    assert "UniCa" not in SYNTHETIC
