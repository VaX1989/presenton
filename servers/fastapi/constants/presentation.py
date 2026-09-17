import os
from pathlib import Path

DEFAULT_MAX_NUMBER_OF_SLIDES = 100
DEFAULT_MAX_OUTLINE_WORDS = 100


def _read_positive_int_env(name: str, default: int) -> int:
    raw_value = (os.getenv(name) or "").strip()
    if not raw_value:
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc

    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def get_max_number_of_slides() -> int:
    return _read_positive_int_env("PRESENTON_MAX_SLIDES", DEFAULT_MAX_NUMBER_OF_SLIDES)


def get_max_outline_words() -> int:
    return _read_positive_int_env("MAX_OUTLINE_WORDS", DEFAULT_MAX_OUTLINE_WORDS)


MAX_NUMBER_OF_SLIDES = get_max_number_of_slides()
MAX_OUTLINE_CONTENT_WORDS = get_max_outline_words()

_PREFERRED_TEMPLATE_ORDER = [
    "momentum",
    "dynamic",
    "executive",
    "general",
    "modern",
    "standard",
    "swift",
]


def _discover_default_templates() -> list[str]:
    templates_dir = Path(__file__).resolve().parents[3] / "templates"

    if not templates_dir.is_dir():
        return []

    discovered = {
        entry.name
        for entry in templates_dir.iterdir()
        if entry.is_dir() and (entry / "template.json").is_file()
    }

    ordered = [name for name in _PREFERRED_TEMPLATE_ORDER if name in discovered]
    extras = sorted(discovered - set(ordered))
    return ordered + extras


DEFAULT_TEMPLATES = _discover_default_templates()
