from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal


class GenerationMode(str, Enum):
    STRICT_MATERIALIZE = "strict_materialize"
    VISUAL_ENHANCE = "visual_enhance"


class MasterFormat(str, Enum):
    RICH_A_S_MASTER = "rich_a_s_master"
    COMPACT_FINAL_LEGACY = "compact_final_legacy"


@dataclass(frozen=True)
class LockedContent:
    title: str = ""
    subtitle: str = ""
    visible_text: List[str] = field(default_factory=list)
    callouts: List[str] = field(default_factory=list)
    caption: str = ""
    question: str = ""
    speaker_notes_final: str = ""
    raw_visible_copy: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScientificSlideSpec:
    source_file: str
    deck_id: str
    global_id: int
    local_id: int
    total_slides: int
    slide_type: str
    master_format: MasterFormat = MasterFormat.COMPACT_FINAL_LEGACY
    narrative_phase: str = ""
    generality_level: str = ""
    priority: str = ""
    blueprint_reference: str = ""
    learning_objective: str = ""
    didactic_function: str = ""
    one_key_takeaway: str = ""
    link_from_previous: str = ""
    link_to_next: str = ""
    locked: LockedContent = field(default_factory=LockedContent)
    visual_thesis: str = ""
    visual_type: str = ""
    composition: str = ""
    focal_point: str = ""
    secondary_elements: List[str] = field(default_factory=list)
    visual_hierarchy: str = ""
    # Production fields deliberately have no plausible-looking defaults. Rich
    # canonical values must come from A-S source sections. Legacy compact decks
    # may still be rendered through renderer-level compatibility fallbacks.
    canvas: str = ""
    background: str = ""
    grid: str = ""
    safe_area: str = ""
    element_map: Dict[str, Any] = field(default_factory=dict)
    title_font: str = ""
    title_size: str = ""
    title_weight: str = ""
    body_font: str = ""
    body_size: str = ""
    label_size: str = ""
    footer_size: str = ""
    alignment_rules: str = ""
    color_roles: Dict[str, str] = field(default_factory=dict)
    asset_specification: Dict[str, Any] = field(default_factory=dict)
    diagram_specification: Dict[str, Any] = field(default_factory=dict)
    table_specification: Dict[str, Any] = field(default_factory=dict)
    chart_specification: Dict[str, Any] = field(default_factory=dict)
    instructor_cue: str = ""
    sources: List[str] = field(default_factory=list)
    accessibility: Dict[str, Any] = field(default_factory=dict)
    reading_order: str = ""
    contrast: str = ""
    projector_readability: str = ""
    animation: Dict[str, Any] = field(default_factory=dict)
    production_constraints: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    raw_sections: Dict[str, str] = field(default_factory=dict)
    unknown_sections: Dict[str, str] = field(default_factory=dict)
    source_hash: str = ""
    source_block: str = ""

    def as_dict(self, include_source_block: bool = False) -> Dict[str, Any]:
        data = asdict(self)
        data["master_format"] = self.master_format.value
        if not include_source_block:
            data.pop("source_block", None)
        return data


@dataclass(frozen=True)
class VisualPlan:
    global_id: int
    archetype: str
    variant: str
    theme: str
    background: Literal["light", "dark"]
    geometry: Dict[str, Any] = field(default_factory=dict)
    notes_supported: bool = True

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScientificGenerationResult:
    mode: GenerationMode
    theme: str
    slides: List[Dict[str, Any]]
    visual_plans: List[VisualPlan]
    source_hashes: Dict[str, str]
    content_lock_status: str
    speaker_notes_supported: bool
    render_contract: str = "presenton_native_strict_ir"

    def as_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["mode"] = self.mode.value
        data["visual_plans"] = [p.as_dict() for p in self.visual_plans]
        return data
