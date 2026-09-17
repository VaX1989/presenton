from __future__ import annotations

from typing import Dict, Iterable, List

from .archetypes import ArchetypeRegistry
from .authorship_qa import assert_rich_authorship, audit_rich_authorship
from .content_lock import assert_locked_content, fidelity_record
from .renderer_dispatch import render_scientific_ui
from .schema import GenerationMode, ScientificGenerationResult, ScientificSlideSpec, VisualPlan
from .strict_qa import qa_strict_native_ui
from .theme import get_theme
from .visual_slots import visual_slot_summary


def _node_count(spec: ScientificSlideSpec) -> int:
    slots = visual_slot_summary(spec)
    authored = slots.get("authored_labels") or []
    return max(len(authored), len(spec.locked.visible_text), len(spec.locked.callouts), 1)


def _visual_descriptor(spec: ScientificSlideSpec) -> str:
    diagram_raw = ""
    if isinstance(spec.diagram_specification, dict):
        diagram_raw = str(spec.diagram_specification.get("raw", ""))
    return " ".join(
        part
        for part in [
            spec.slide_type,
            spec.visual_type,
            spec.visual_thesis,
            spec.composition,
            diagram_raw,
        ]
        if part
    )


def plan_visual(
    spec: ScientificSlideSpec,
    theme: str,
    dark: bool | None = None,
) -> VisualPlan:
    registry = ArchetypeRegistry()
    if dark is None:
        dark = "#17324d" in (spec.background or "").casefold() or "navy" in (
            spec.background or ""
        ).casefold()
    archetype = registry.resolve(
        _visual_descriptor(spec), dark=dark, node_count=_node_count(spec)
    )
    slots = visual_slot_summary(spec)
    return VisualPlan(
        global_id=spec.global_id,
        archetype=archetype.id,
        variant=archetype.variants[0],
        theme=get_theme(theme).id,
        background="dark" if dark else "light",
        geometry={
            "slots": archetype.required_slots + archetype.optional_slots,
            "constraints": archetype.layout_constraints,
            "authored": slots,
        },
    )


def _element_text(element: Dict[str, object]) -> str:
    if element.get("type") != "text":
        return ""
    runs = element.get("runs")
    if not isinstance(runs, list):
        return ""
    return "".join(
        str(run.get("text", "")) for run in runs if isinstance(run, dict)
    )


def _strict_text_audit(spec: ScientificSlideSpec, ui: Dict[str, object]) -> None:
    """Reject visible renderer prose that has no provenance in the canonical master."""
    source = spec.source_block.casefold().replace("\n", " ")
    elements = ui.get("elements")
    if not isinstance(elements, list):
        raise ValueError(f"G{spec.global_id:03d}: native UI has no element list")
    invented: list[str] = []
    for element in elements:
        if (
            not isinstance(element, dict)
            or element.get("type") != "text"
            or element.get("decorative")
        ):
            continue
        text = _element_text(element).strip()
        if not text:
            continue
        if text.casefold().replace("\n", " ") not in source:
            invented.append(text)
    if invented:
        raise ValueError(
            f"G{spec.global_id:03d}: strict renderer emitted unsourced visible text: {invented}"
        )


def _slide_record(
    spec: ScientificSlideSpec,
    plan: VisualPlan,
    theme_id: str,
) -> Dict[str, object]:
    ui = render_scientific_ui(spec, plan, theme_id)
    _strict_text_audit(spec, ui)
    return {
        "source_hash": spec.source_hash,
        "global_id": spec.global_id,
        "local_id": spec.local_id,
        "title": spec.locked.title,
        "subtitle": spec.locked.subtitle,
        "visible_text": list(spec.locked.visible_text),
        "callouts": list(spec.locked.callouts),
        "caption": spec.locked.caption,
        "question": spec.locked.question,
        "speaker_notes_final": spec.locked.speaker_notes_final,
        "theme": get_theme(theme_id).id,
        "archetype": plan.archetype,
        "variant": plan.variant,
        "background": plan.background,
        "render_contract": "presenton_native_template_v2_ui",
        "authorship_qa": audit_rich_authorship(spec),
        "ui": ui,
        "ui_qa": qa_strict_native_ui(ui),
    }


def compile_strict(
    specs: List[ScientificSlideSpec],
    theme_id: str = "scientific-editorial",
    dark_slide_ids: Iterable[int] = (),
) -> ScientificGenerationResult:
    get_theme(theme_id)
    forced_dark = set(dark_slide_ids)
    visual_plans: List[VisualPlan] = []
    slides: List[Dict[str, object]] = []
    for spec in specs:
        # Rich masters are source code. A non-empty production value that cannot
        # be traced to the corresponding A-S section is treated as an inferred
        # default and is forbidden in STRICT_MATERIALIZE.
        assert_rich_authorship(spec)
        plan = plan_visual(
            spec,
            theme_id,
            True if spec.global_id in forced_dark else None,
        )
        visual_plans.append(plan)
        slide = _slide_record(spec, plan, theme_id)
        assert_locked_content(spec, slide)
        if slide["ui_qa"]["status"] != "PASS":
            raise ValueError(
                f"G{spec.global_id:03d}: native UI structural QA failed: {slide['ui_qa']}"
            )
        slides.append(slide)
    return ScientificGenerationResult(
        GenerationMode.STRICT_MATERIALIZE,
        get_theme(theme_id).id,
        slides,
        visual_plans,
        {f"G{s.global_id:03d}": s.source_hash for s in specs},
        "PASS",
        True,
        render_contract="presenton_native_template_v2_ui",
    )


def compile_fidelity(
    specs: List[ScientificSlideSpec],
    slides: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    by_id = {int(slide["global_id"]): slide for slide in slides}
    return [
        fidelity_record(spec, by_id.get(spec.global_id, {})) for spec in specs
    ]
