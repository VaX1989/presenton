from __future__ import annotations

import difflib
import hashlib
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
    expected_hash: str
    actual_hash: str
    unified_diff: str


def _normalize_typographic(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").strip().splitlines())


def _hash(text: str) -> str:
    return hashlib.sha256(_normalize_typographic(text).encode("utf-8")).hexdigest()


def _join(value: object) -> str:
    if isinstance(value, list):
        return "\n".join(str(x) for x in value)
    return str(value or "")


def locked_fields(spec: ScientificSlideSpec) -> Dict[str, str]:
    return {
        "title": spec.locked.title,
        "subtitle": spec.locked.subtitle,
        "visible_text": "\n".join(spec.locked.visible_text),
        "callouts": "\n".join(spec.locked.callouts),
        "caption": spec.locked.caption,
        "question": spec.locked.question,
        "speaker_notes_final": spec.locked.speaker_notes_final,
    }


def compare_locked_fields(spec: ScientificSlideSpec, generated: Dict[str, object]) -> List[ContentDiff]:
    diffs: List[ContentDiff] = []
    for field, wanted in locked_fields(spec).items():
        got = _join(generated.get(field, ""))
        if _normalize_typographic(wanted) != _normalize_typographic(got):
            patch = "\n".join(difflib.unified_diff(wanted.splitlines(), got.splitlines(), fromfile="source", tofile="generated", lineterm=""))
            diffs.append(ContentDiff(spec.global_id, field, wanted, got, _hash(wanted), _hash(got), patch))
    return diffs


def fidelity_record(spec: ScientificSlideSpec, generated: Dict[str, object]) -> Dict[str, object]:
    diffs = compare_locked_fields(spec, generated)
    return {
        "global_id": spec.global_id,
        "source_hash": spec.source_hash,
        "status": "PASS" if not diffs else "FAIL",
        "field_hashes": {name: _hash(value) for name, value in locked_fields(spec).items()},
        "actual_hashes": {name: _hash(_join(generated.get(name, ""))) for name in locked_fields(spec)},
        "diffs": [d.__dict__ for d in diffs],
    }


def assert_locked_content(spec: ScientificSlideSpec, generated: Dict[str, object]) -> None:
    diffs = compare_locked_fields(spec, generated)
    if diffs:
        raise ContentLockViolation(f"G{spec.global_id:03d}: locked content mutated: {', '.join(d.field for d in diffs)}")
