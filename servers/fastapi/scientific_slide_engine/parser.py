from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Tuple

from .schema import LockedContent, ScientificSlideSpec

SLIDE_HEADING = re.compile(r"^###\s+G(?P<global>\d{3})\s+·\s+(?P<local>\d{1,2})/(?P<total>\d+)\s+—\s+(?P<type>.+?)\s*$", re.MULTILINE)
FIELD_MARKER = re.compile(r"^\*\*(?P<name>[A-Z][A-Z _/-]*):\*\*\s*(?P<value>.*)$")
DECK_ID = re.compile(r"^-\s*\*\*DECK_ID:\*\*\s*(?P<id>\d{2})\s*$", re.MULTILINE)
DECLARED_COUNT = re.compile(r"^-\s*\*\*Numero slide:\*\*\s*(?P<count>\d+)\s*$", re.MULTILINE)
BACKTICK = re.compile(r"`([^`]*)`")
LABELED_BACKTICK = re.compile(r"(?P<label>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ _/-]*?):?\s*`(?P<value>[^`]*)`")


class MasterParseError(ValueError):
    pass


def _norm(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _hash_block(source_file: str, deck_id: str, global_id: int, local_id: int, block: str) -> str:
    canonical = {"source_file": source_file.replace("\\", "/"), "deck_id": deck_id, "global_id": global_id, "local_id": local_id, "source_block": _norm(block)}
    return hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _parse_fields(block: str) -> Dict[str, str]:
    fields: Dict[str, List[str]] = {}
    current = None
    for line in block.splitlines()[1:]:
        match = FIELD_MARKER.match(line)
        if match:
            current = match.group("name").strip()
            if current in fields:
                raise MasterParseError(f"duplicate structural field {current}")
            fields[current] = [match.group("value").rstrip()]
        elif current is not None:
            fields[current].append(line.rstrip())
    return {key: _norm("\n".join(value)) for key, value in fields.items()}


def _visible_parts(raw: str) -> LockedContent:
    labeled: Dict[str, List[str]] = {}
    for match in LABELED_BACKTICK.finditer(raw):
        labeled.setdefault(match.group("label").strip().upper(), []).append(match.group("value"))

    title = (labeled.get("TITLE") or [""])[0]
    subtitle = (labeled.get("SUBTITLE") or [""])[0]
    question = (labeled.get("QUESTION") or [""])[0]
    caption = (labeled.get("CAPTION") or [""])[0]
    callouts = labeled.get("CALLOUT", []) + labeled.get("CALLOUTS", [])
    visible_text: List[str] = []
    for key, values in labeled.items():
        if key in {"TEXT", "NODES", "NODE", "MATRIX", "LABELS", "STEPS", "FIELDS", "ITEMS"}:
            visible_text.extend(values)
    if not title:
        ticks = BACKTICK.findall(raw)
        if ticks:
            title = ticks[0]
            visible_text.extend(ticks[1:])
    return LockedContent(title=title, subtitle=subtitle, visible_text=visible_text, callouts=callouts, caption=caption, question=question, raw_visible_copy=raw)


def parse_master_text(text: str, source_file: str = "<memory>") -> List[ScientificSlideSpec]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    deck_match = DECK_ID.search(text)
    if not deck_match:
        raise MasterParseError("missing DECK_ID")
    deck_id = deck_match.group("id")
    declared_match = DECLARED_COUNT.search(text)
    declared_count = int(declared_match.group("count")) if declared_match else None
    matches = list(SLIDE_HEADING.finditer(text))
    if not matches:
        raise MasterParseError("no canonical G### slide headings found")

    specs: List[ScientificSlideSpec] = []
    seen_global, seen_local = set(), set()
    for index, match in enumerate(matches):
        block = _norm(text[match.start(): matches[index + 1].start() if index + 1 < len(matches) else len(text)])
        fields = _parse_fields(block)
        missing = [name for name in ("VISIBLE COPY", "VISUAL", "NOTES", "SOURCES") if not fields.get(name)]
        if missing:
            raise MasterParseError(f"G{match.group('global')}: missing required fields: {', '.join(missing)}")
        gid, lid, total = int(match.group("global")), int(match.group("local")), int(match.group("total"))
        if gid in seen_global:
            raise MasterParseError(f"duplicate global slide id G{gid:03d}")
        if lid in seen_local:
            raise MasterParseError(f"duplicate local slide id {lid}")
        seen_global.add(gid); seen_local.add(lid)
        locked = replace(_visible_parts(fields["VISIBLE COPY"]), speaker_notes_final=fields["NOTES"])
        specs.append(ScientificSlideSpec(source_file=source_file, deck_id=deck_id, global_id=gid, local_id=lid, total_slides=total, slide_type=match.group("type").strip(), generality_level=match.group("type").split("·", 1)[0].strip(), locked=locked, visual_thesis=fields["VISUAL"], visual_type=fields["VISUAL"], diagram_specification={"canonical_visual": fields["VISUAL"]}, sources=[s.strip() for s in re.split(r"\s*;\s*", fields["SOURCES"]) if s.strip()], accessibility={"alt_text_required": True, "no_color_only_meaning": True}, production_constraints=["no_font_shrinking", "didactic_text>=18pt", "safe_area>=0.55in"], acceptance_criteria=["locked_copy_exact", "notes_exact", "editable_text", "projector_readable"], source_hash=_hash_block(source_file, deck_id, gid, lid, block), source_block=block))

    if {s.total_slides for s in specs} != {len(specs)}:
        raise MasterParseError("inconsistent total slide declarations")
    if declared_count is not None and declared_count != len(specs):
        raise MasterParseError(f"declared Numero slide {declared_count} != parsed count {len(specs)}")
    if set(range(1, len(specs) + 1)) != seen_local:
        raise MasterParseError("missing local slide ids")
    return specs


def parse_master_file(path: Path, root: Path | None = None) -> List[ScientificSlideSpec]:
    if not path.exists():
        raise MasterParseError(f"master not found: {path}")
    return parse_master_text(path.read_text(encoding="utf-8"), str(path.relative_to(root)) if root else str(path))
