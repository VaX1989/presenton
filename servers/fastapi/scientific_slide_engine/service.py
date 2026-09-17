from __future__ import annotations

import uuid
from typing import Any, Dict, List, Sequence

from constants.presentation import MAX_NUMBER_OF_SLIDES
from .compiler import compile_fidelity
from .schema import ScientificGenerationResult, ScientificSlideSpec


def validate_request_count(specs: Sequence[ScientificSlideSpec]) -> None:
    if not specs:
        raise ValueError("strict materialization requires at least one slide")
    if len(specs) > MAX_NUMBER_OF_SLIDES:
        raise ValueError(f"Too many slides: {len(specs)} > {MAX_NUMBER_OF_SLIDES}")


def build_persisted_slide_content(spec: ScientificSlideSpec, rendered: Dict[str, object]) -> Dict[str, Any]:
    return {
        "scientific": {
            "source_hash": spec.source_hash,
            "global_id": spec.global_id,
            "local_id": spec.local_id,
            "master_format": spec.master_format.value,
            "archetype": rendered["archetype"],
            "variant": rendered["variant"],
        },
        "title": spec.locked.title,
        "subtitle": spec.locked.subtitle,
        "visible_text": list(spec.locked.visible_text),
        "callouts": list(spec.locked.callouts),
        "caption": spec.locked.caption,
        "question": spec.locked.question,
        "speaker_notes_final": spec.locked.speaker_notes_final,
    }


def persisted_locked_view(content: Dict[str, Any], speaker_note: str | None) -> Dict[str, object]:
    return {
        "title": content.get("title", ""),
        "subtitle": content.get("subtitle", ""),
        "visible_text": content.get("visible_text", []),
        "callouts": content.get("callouts", []),
        "caption": content.get("caption", ""),
        "question": content.get("question", ""),
        "speaker_notes_final": speaker_note or "",
    }


async def persist_strict_presentation(
    sql_session: Any,
    specs: List[ScientificSlideSpec],
    result: ScientificGenerationResult,
    *,
    title: str | None = None,
    language: str = "en",
):
    """Persist strict native UI as normal Presenton rows, atomically gated by fidelity."""
    from models.sql.presentation import PresentationModel, PresentationVersion
    from models.sql.slide import SlideModel

    validate_request_count(specs)
    if len(result.slides) != len(specs):
        raise ValueError(f"strict result count mismatch: {len(result.slides)} != {len(specs)}")

    presentation_id = uuid.uuid4()
    presentation = PresentationModel(
        id=presentation_id,
        version=PresentationVersion.V2_STANDARD,
        content="scientific strict materialization",
        n_slides=len(specs),
        language=language,
        title=title or specs[0].locked.title,
        include_table_of_contents=False,
        include_title_slide=False,
        generation_mode="standard",
        instructions="STRICT_MATERIALIZE: canonical copy is immutable",
        theme={"id": result.theme, "name": "Scientific Editorial", "scientific_strict": True},
    )
    sql_session.add(presentation)

    slides: List[SlideModel] = []
    for index, (spec, rendered) in enumerate(zip(specs, result.slides)):
        content = build_persisted_slide_content(spec, rendered)
        slides.append(
            SlideModel(
                presentation=presentation_id,
                layout_group="scientific-editorial",
                layout=str(rendered["archetype"]),
                index=index,
                content=content,
                speaker_note=spec.locked.speaker_notes_final,
                properties={
                    "scientific": {
                        "source_hash": spec.source_hash,
                        "global_id": spec.global_id,
                        "local_id": spec.local_id,
                        "theme": result.theme,
                        "render_contract": result.render_contract,
                    }
                },
                ui=rendered["ui"],
            )
        )
    sql_session.add_all(slides)

    # Flush creates/validates database rows inside the current transaction without
    # making an invalid strict deck durable. Compare the exact fields that the
    # editor/export pipeline will read before committing anything.
    await sql_session.flush()
    persisted_views = [persisted_locked_view(slide.content, slide.speaker_note) for slide in slides]
    fidelity = compile_fidelity(specs, persisted_views)
    if any(record["status"] != "PASS" for record in fidelity):
        await sql_session.rollback()
        raise RuntimeError("strict content lock failed before Presenton commit")

    await sql_session.commit()
    await sql_session.refresh(presentation)
    for slide in slides:
        await sql_session.refresh(slide)

    # A post-commit readback is still verified. At this point a failure indicates
    # an unexpected persistence-layer mutation and is surfaced as a hard error.
    readback = [persisted_locked_view(slide.content, slide.speaker_note) for slide in slides]
    readback_fidelity = compile_fidelity(specs, readback)
    if any(record["status"] != "PASS" for record in readback_fidelity):
        raise RuntimeError("strict content lock failed after Presenton commit readback")
    return presentation, slides, readback_fidelity
