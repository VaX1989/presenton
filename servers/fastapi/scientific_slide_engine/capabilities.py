from __future__ import annotations

from constants.presentation import MAX_NUMBER_OF_SLIDES
from .archetypes import ArchetypeRegistry


def scientific_capabilities() -> dict:
    return {
        "max_slides": MAX_NUMBER_OF_SLIDES,
        "strict_materialize_supported": True,
        "speaker_notes_supported": True,
        "native_persistence_supported": True,
        "native_editable_ui_supported": True,
        "supported_generation_modes": ["strict_materialize"],
        "supported_master_formats": ["rich_a_s_master", "compact_final_legacy"],
        "preferred_master_format": "rich_a_s_master",
        "themes": ["scientific-editorial"],
        "render_contract": "presenton_native_template_v2_ui",
        "archetypes": sorted(ArchetypeRegistry().as_dict()),
    }
