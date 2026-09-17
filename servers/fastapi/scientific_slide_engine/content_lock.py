from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Dict, List

from .schema import ScientificSlideSpec


class ContentLockViolation(ValueError):
    pass


@dataclass(frozen=True)
class ContentDiff:
    global_id: int
    field: str
    expected: str
    actual: str
    unified_diff: str


def _normalize_typographic(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def compare_locked_fields(spec: ScientificSlideSpec, generated: Dict[str, object]) -> List[ContentDiff]:
    expected = {
        "title": spec.locked.title,
        "subtitle": spec.locked.subtitle,
        "visible_text": "\n".join(spec.locked.visible_text),
        "callouts": "\n".join(spec.locked.callouts),
        "caption": spec.locked.caption,
        "question": spec.locked.question,
        "speaker_notes_final": spec.locked.speaker_notes_final,
        "raw_visible_copy": spec.locked.raw_visible_copy,
    }
    diffs: List[ContentDiff] = []
    for field, wanted in expected.items():
        got = generated.get(field, "")
        if isinstance(got, list):
            got = "\n".join(str(x) for x in got)
        got = str(got)
        if _normalize_typographic(wanted) != _normalize_typographic(got):
            patch = "\n".join(difflib.unified_diff(wanted.splitlines(), got.splitlines(), fromfile="source", tofile="generated", lineterm=""))
            diffs.append(ContentDiff(spec.global_id, field, wanted, got, patch))
    return diffs


def assert_locked_content(spec: ScientificSlideSpec, generated: Dict[str, object]) -> None:
    diffs = compare_locked_fields(spec, generated)
    if diffs:
        raise ContentLockViolation(f"G{spec.global_id:03d}: locked content mutated: {', '.join(d.field for d in diffs)}")
