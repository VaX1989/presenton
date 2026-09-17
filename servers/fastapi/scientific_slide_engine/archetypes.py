from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class Archetype:
    id: str
    compatible_visual_types: List[str]
    required_slots: List[str]
    optional_slots: List[str] = field(default_factory=list)
    layout_constraints: Dict[str, object] = field(default_factory=dict)
    light_dark: List[str] = field(default_factory=lambda: ["light"])
    min_nodes: int = 0
    max_nodes: int = 24
    variants: List[str] = field(default_factory=lambda: ["default"])
    accessibility: Dict[str, object] = field(default_factory=dict)


class ArchetypeRegistry:
    def __init__(self, archetypes: Iterable[Archetype] | None = None) -> None:
        self._items: Dict[str, Archetype] = {}
        for item in archetypes or DEFAULT_ARCHETYPES:
            self.register(item)

    def register(self, archetype: Archetype) -> None:
        if archetype.id in self._items:
            raise ValueError(f"duplicate archetype {archetype.id}")
        self._items[archetype.id] = archetype

    def get(self, archetype_id: str) -> Archetype:
        if archetype_id not in self._items:
            raise KeyError(archetype_id)
        return self._items[archetype_id]

    def resolve(self, visual_type: str, dark: bool = False, node_count: int = 0) -> Archetype:
        haystack = visual_type.casefold()
        scored: list[tuple[int, Archetype]] = []
        for archetype in self._items.values():
            score = sum(3 if term.casefold() == haystack.strip() else 1 for term in archetype.compatible_visual_types if term.casefold() in haystack)
            if score and archetype.min_nodes <= node_count <= archetype.max_nodes:
                if dark and "dark" in archetype.light_dark:
                    score += 1
                scored.append((score, archetype))
        if scored:
            scored.sort(key=lambda item: (-item[0], item[1].id))
            return scored[0][1]
        return self._items["scientific-diagram"]

    def as_dict(self) -> Dict[str, object]:
        return {key: value.__dict__ for key, value in self._items.items()}


_COMMON_ACCESSIBILITY = {"minimum_didactic_font_pt": 18, "no_color_only_encoding": True, "projector_safe": True}
_COMMON_CONSTRAINTS = {"safe_area_px": 53, "stage": [1280, 720], "font_shrinking": False}

DEFAULT_ARCHETYPES = [
    Archetype("hero-question", ["hero question", "opening", "question field", "hero"], ["title", "question"], ["trajectory"], {**_COMMON_CONSTRAINTS, "max_words": 55}, ["light", "dark"], 0, 8, ["trajectory", "field"], _COMMON_ACCESSIBILITY),
    Archetype("discipline-map", ["discipline map", "concept map", "role map"], ["title", "nodes"], ["center"], _COMMON_CONSTRAINTS, ["light", "dark"], 3, 9, ["radial", "constellation"], _COMMON_ACCESSIBILITY),
    Archetype("layered-concept", ["layered", "nested", "determinant", "concentric", "layers"], ["title", "layers"], ["callout"], _COMMON_CONSTRAINTS, ["light", "dark"], 2, 9, ["nested", "strata"], _COMMON_ACCESSIBILITY),
    Archetype("comparison", ["comparison", "triptych", "split-screen", "before after"], ["title", "items"], ["subtitle", "callout"], _COMMON_CONSTRAINTS, ["light", "dark"], 2, 6, ["split", "columns"], _COMMON_ACCESSIBILITY),
    Archetype("causal-continuum", ["causal continuum", "causal ladder", "continuum", "impact chain", "trajectory"], ["title", "nodes"], ["intervention_marks"], _COMMON_CONSTRAINTS, ["light", "dark"], 3, 9, ["horizontal", "stepped"], _COMMON_ACCESSIBILITY),
    Archetype("gradient-distribution", ["distribution", "gradient", "line chart", "small-multiple chart", "profile diagram"], ["title", "distribution"], ["annotation"], _COMMON_CONSTRAINTS, ["light"], 1, 8, ["distribution", "gradient-field"], _COMMON_ACCESSIBILITY),
    Archetype("timeline", ["timeline", "disease process", "encounter timeline"], ["title", "events"], ["windows"], _COMMON_CONSTRAINTS, ["light", "dark"], 2, 10, ["horizontal", "banded"], _COMMON_ACCESSIBILITY),
    Archetype("matrix", ["matrix", "editorial table", "2x2", "authority stack"], ["title", "cells"], ["headers"], _COMMON_CONSTRAINTS, ["light"], 2, 16, ["editorial", "2x2"], _COMMON_ACCESSIBILITY),
    Archetype("risk-chain", ["risk chain", "hazard", "dose", "effect"], ["title", "nodes"], ["barriers"], _COMMON_CONSTRAINTS, ["light", "dark"], 3, 9, ["chain", "gated"], _COMMON_ACCESSIBILITY),
    Archetype("source-pathway", ["source pathway", "source-pathway", "source→", "pathway", "exposure", "barrier diagram"], ["title", "nodes"], ["barriers", "callout"], _COMMON_CONSTRAINTS, ["light", "dark"], 3, 9, ["linear", "barrier"], _COMMON_ACCESSIBILITY),
    Archetype("intervention-points", ["intervention points", "control comparison", "spectrum"], ["title", "trajectory", "controls"], ["annotation"], _COMMON_CONSTRAINTS, ["light", "dark"], 2, 10, ["trajectory", "spectrum"], _COMMON_ACCESSIBILITY),
    Archetype("hierarchy", ["hierarchy", "controls", "pyramid", "robustness", "ladder"], ["title", "levels"], ["axis", "callout"], _COMMON_CONSTRAINTS, ["light", "dark"], 3, 7, ["bands", "ladder"], _COMMON_ACCESSIBILITY),
    Archetype("verification-loop", ["verification", "audit loop", "governance loop", "closed loop", "cycle", "loop"], ["title", "steps"], ["center"], _COMMON_CONSTRAINTS, ["light", "dark"], 3, 9, ["cycle", "closed-loop"], _COMMON_ACCESSIBILITY),
    Archetype("system-map", ["system map", "systems map", "ecosystem map", "integrated flow", "interface"], ["title", "nodes"], ["interfaces"], _COMMON_CONSTRAINTS, ["light", "dark"], 3, 14, ["system", "layered-system"], _COMMON_ACCESSIBILITY),
    Archetype("process-map", ["process map", "process", "state", "swimlane", "handoff", "funnel"], ["title", "steps"], ["lanes", "handoff"], _COMMON_CONSTRAINTS, ["light", "dark"], 2, 10, ["state-line", "swimlane"], _COMMON_ACCESSIBILITY),
    Archetype("network", ["network", "one health", "network map", "radial"], ["title", "nodes"], ["center"], _COMMON_CONSTRAINTS, ["light", "dark"], 3, 14, ["radial", "ecosystem"], _COMMON_ACCESSIBILITY),
    Archetype("scenario", ["scenario", "case", "small multiples"], ["title", "states"], ["question"], _COMMON_CONSTRAINTS, ["light"], 2, 6, ["small-multiples", "case-path"], _COMMON_ACCESSIBILITY),
    Archetype("audit-loop", ["audit", "feedback", "corrective", "review"], ["title", "steps"], ["evidence"], _COMMON_CONSTRAINTS, ["light", "dark"], 3, 8, ["audit-cycle", "evidence-loop"], _COMMON_ACCESSIBILITY),
    Archetype("synthesis", ["synthesis", "closing", "six-question", "triad", "checkpoint"], ["title", "nodes"], ["callout"], _COMMON_CONSTRAINTS, ["light", "dark"], 3, 10, ["loop", "constellation", "triad"], _COMMON_ACCESSIBILITY),
    Archetype("scientific-diagram", ["diagram", "visual", "map", "model", "concept"], ["title"], ["nodes", "callout"], _COMMON_CONSTRAINTS, ["light", "dark"], 0, 24, ["editorial"], _COMMON_ACCESSIBILITY),
]
