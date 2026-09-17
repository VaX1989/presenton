from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

from .schema import LockedContent, MasterFormat, ScientificSlideSpec

COMPACT_SLIDE_HEADING = re.compile(
    r"^###\s+G(?P<global>\d{3})\s+·\s+(?P<local>\d{1,3})/(?P<total>\d+)\s+—\s+(?P<type>.+?)\s*$",
    re.MULTILINE,
)
RICH_SLIDE_HEADING = re.compile(
    r"^#{1,3}\s*SLIDE\s+(?P<global>\d{3})(?:\s*[-–—]\s*(?P<local>\d{1,3})/(?P<total>\d+))?(?:\s*[-–—]\s*(?P<title>.*?))?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
FIELD_MARKER = re.compile(r"^\*\*(?P<name>[A-Z][A-Z _/-]*):\*\*\s*(?P<value>.*)$")
DECK_ID_PATTERNS = (
    re.compile(r"^-\s*\*\*DECK_ID:\*\*\s*(?P<id>\d{2})\s*$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\s*DECK_ID\s*[:=]\s*(?P<id>\d{2})\s*$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\s*DECK\s*[:=]\s*(?P<id>\d{2})\s*$", re.MULTILINE | re.IGNORECASE),
)
DECLARED_COUNT_PATTERNS = (
    re.compile(r"^-\s*\*\*(?:Numero slide|Total slides):\*\*\s*(?P<count>\d+)\s*$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\s*(?:Numero slide|Total slides|TOTAL_SLIDES)\s*[:=]\s*(?P<count>\d+)\s*$", re.MULTILINE | re.IGNORECASE),
)
RICH_SECTION = re.compile(
    r"^#{1,6}\s+(?P<label>[A-S])\.\s+(?P<name>[^\n]+?)\s*$",
    re.MULTILINE,
)
SECTION_MAP: Mapping[str, str] = {
    "A": "identity", "B": "didactic_function", "C": "final_visible_copy",
    "D": "copy_quality_audit", "E": "visual_concept", "F": "layout_specification",
    "G": "typography", "H": "color_specification", "I": "asset_specification",
    "J": "diagram_specification", "K": "table_specification", "L": "chart_specification",
    "M": "speaker_notes", "N": "instructor_cue", "O": "sources", "P": "accessibility",
    "Q": "animation", "R": "production_constraints", "S": "acceptance_criteria",
}
REQUIRED_RICH = set(SECTION_MAP)
NONE_VALUES = {"", "NONE", "N/A", "NA", "NULL", "—", "-"}


class MasterParseError(ValueError):
    pass


def _norm(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _hash_block(source_file: str, deck_id: str, global_id: int, local_id: int, block: str) -> str:
    canonical = {
        "source_file": source_file.replace("\\", "/"), "deck_id": deck_id,
        "global_id": global_id, "local_id": local_id, "source_block": _norm(block),
    }
    return hashlib.sha256(
        json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def detect_master_format(text: str) -> MasterFormat:
    if RICH_SECTION.search(text) and RICH_SLIDE_HEADING.search(text):
        return MasterFormat.RICH_A_S_MASTER
    return MasterFormat.COMPACT_FINAL_LEGACY


def _split_sections(block: str) -> Dict[str, str]:
    matches = list(RICH_SECTION.finditer(block))
    if not matches:
        return {}
    sections: Dict[str, str] = {}
    for index, match in enumerate(matches):
        label = match.group("label")
        if label in sections:
            raise MasterParseError(f"duplicate rich section {label}")
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
        sections[label] = _norm(block[start:end])
    return sections


def _parse_compact_fields(block: str) -> Dict[str, str]:
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


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2:
        for left, right in (("\"", "\""), ("'", "'"), ("“", "”"), ("‘", "’")):
            if value.startswith(left) and value.endswith(right):
                return value[len(left) : -len(right)]
    return value


def _is_none(value: str) -> bool:
    return value.strip().upper() in NONE_VALUES


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")


def _structured_fields(raw: str) -> Dict[str, object]:
    fields: Dict[str, object] = {}
    current: str | None = None
    list_buffer: List[str] = []

    def flush() -> None:
        nonlocal list_buffer, current
        if current is not None and list_buffer:
            prior = fields.get(current)
            if prior is None or prior == "":
                fields[current] = list(list_buffer)
            elif isinstance(prior, list):
                fields[current] = [*prior, *list_buffer]
            else:
                fields[current] = [str(prior), *list_buffer]
        list_buffer = []

    for source_line in raw.splitlines():
        stripped = source_line.rstrip().strip()
        if not stripped:
            if current is not None and list_buffer:
                list_buffer.append("")
            continue
        if stripped in {"[Sources]", "[/Sources]"}:
            continue
        key_match = re.match(r"^(?P<key>[A-Za-z][A-Za-z0-9 _/\-]+):\s*(?P<value>.*)$", stripped)
        if key_match:
            flush()
            current = _normalize_key(key_match.group("key"))
            if current in fields:
                raise MasterParseError(f"duplicate canonical field {key_match.group('key').strip()}")
            fields[current] = _unquote(key_match.group("value").strip())
            continue
        if stripped.startswith(("- ", "* ", "• ")):
            item = _unquote(stripped[2:].strip())
            if current is None:
                current = "items"
                if current in fields:
                    raise MasterParseError("duplicate implicit items field")
                fields[current] = ""
            list_buffer.append(item)
            continue
        if current is not None:
            prior = fields.get(current, "")
            if isinstance(prior, list):
                list_buffer.append(_unquote(stripped))
            else:
                fields[current] = f"{prior}\n{_unquote(stripped)}".strip()
        else:
            current = "raw"
            fields[current] = _unquote(stripped)
    flush()
    return fields


def _scalar(fields: Mapping[str, object], aliases: Sequence[str], default: str = "") -> str:
    for alias in aliases:
        value = fields.get(_normalize_key(alias))
        if value is None:
            continue
        if isinstance(value, list):
            return "\n".join(str(item) for item in value if str(item).strip())
        value = str(value).strip()
        return "" if _is_none(value) else value
    return default


def _list_value(fields: Mapping[str, object], aliases: Sequence[str]) -> List[str]:
    for alias in aliases:
        value = fields.get(_normalize_key(alias))
        if value is None:
            continue
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip() and not _is_none(str(item))]
        value = str(value).strip()
        if _is_none(value):
            return []
        return [_unquote(part.strip()) for part in re.split(r"\s*;\s*", value) if part.strip()]
    return []


def _plain_list(raw: str) -> List[str]:
    if _is_none(raw):
        return []
    values: List[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped in {"[Sources]", "[/Sources]"}:
            continue
        if stripped.startswith(("- ", "* ", "• ")):
            stripped = stripped[2:].strip()
        values.append(_unquote(stripped))
    return values


def _section_dict(raw: str) -> Dict[str, object]:
    if _is_none(raw):
        return {"raw": "NONE"}
    result = _structured_fields(raw)
    result["raw"] = raw
    return result


def _deck_id(text: str, source_file: str) -> str:
    for pattern in DECK_ID_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group("id")
    path_match = re.search(r"DECK_(\d{2})|(?:^|/)(\d{2})[_-]", source_file)
    if path_match:
        return next(group for group in path_match.groups() if group)
    raise MasterParseError("missing DECK_ID")


def _declared_count(text: str) -> int | None:
    for pattern in DECLARED_COUNT_PATTERNS:
        match = pattern.search(text)
        if match:
            return int(match.group("count"))
    return None


def _extract_notes(section: str) -> str:
    fields = _structured_fields(section)
    value = _scalar(fields, ["SPEAKER_NOTES_FINAL", "speaker_notes", "notes"])
    if value:
        return _unquote(value).strip()
    return _unquote(section.strip()) if not _is_none(section) else ""


def _visible_content(section: str) -> LockedContent:
    fields = _structured_fields(section)
    title = _scalar(fields, ["TITLE"])
    if not title:
        raise MasterParseError("rich slide missing TITLE in section C")
    return LockedContent(
        title=title,
        subtitle=_scalar(fields, ["SUBTITLE"]),
        visible_text=_list_value(fields, ["VISIBLE_TEXT", "TEXT", "NODES", "STEPS", "LABELS"]),
        callouts=_list_value(fields, ["CALLOUTS", "CALLOUT"]),
        caption=_scalar(fields, ["CAPTION"]),
        question=_scalar(fields, ["QUESTION"]),
        raw_visible_copy=section,
    )


def _compact_visible_content(raw: str) -> LockedContent:
    labels = ("TITLE", "SUBTITLE", "TEXT", "NODES", "STEPS", "LABELS", "CALLOUT", "CALLOUTS", "CAPTION", "QUESTION")
    pattern = re.compile(rf"(?P<label>{'|'.join(labels)})\s*:?\s*`(?P<value>[^`]*)`", re.IGNORECASE)
    found: Dict[str, List[str]] = {}
    for match in pattern.finditer(raw):
        found.setdefault(match.group("label").upper(), []).append(match.group("value"))
    if not found.get("TITLE"):
        ticks = re.findall(r"`([^`]*)`", raw)
        if ticks:
            found["TITLE"] = [ticks[0]]
    visible: List[str] = []
    for key in ("TEXT", "NODES", "STEPS", "LABELS"):
        for value in found.get(key, []):
            visible.extend([part.strip() for part in re.split(r"\s*[·;]\s*", value) if part.strip()])
    return LockedContent(
        title=(found.get("TITLE") or [""])[0], subtitle=(found.get("SUBTITLE") or [""])[0],
        visible_text=visible, callouts=found.get("CALLOUT", []) + found.get("CALLOUTS", []),
        caption=(found.get("CAPTION") or [""])[0], question=(found.get("QUESTION") or [""])[0],
        raw_visible_copy=raw,
    )


def _parse_rich(text: str, source_file: str) -> List[ScientificSlideSpec]:
    deck_id = _deck_id(text, source_file)
    declared_count = _declared_count(text)
    headings = list(RICH_SLIDE_HEADING.finditer(text))
    if not headings:
        raise MasterParseError("no rich slide headings found")
    specs: List[ScientificSlideSpec] = []
    seen_global: set[int] = set()
    seen_local: set[int] = set()
    for index, heading in enumerate(headings):
        gid = int(heading.group("global"))
        block = _norm(text[heading.start() : headings[index + 1].start() if index + 1 < len(headings) else len(text)])
        sections = _split_sections(block)
        missing = sorted(REQUIRED_RICH - set(sections))
        if missing:
            raise MasterParseError(f"G{gid:03d}: missing rich sections: {', '.join(missing)}")
        identity = _structured_fields(sections["A"])
        lid = int(_scalar(identity, ["LOCAL", "LOCAL_ID"], heading.group("local") or str(index + 1)))
        total = int(_scalar(identity, ["TOTAL_SLIDES", "TOTAL"], heading.group("total") or str(declared_count or len(headings))))
        identity_global = _scalar(identity, ["GLOBAL", "GLOBAL_ID"])
        if identity_global and int(identity_global) != gid:
            raise MasterParseError(f"G{gid:03d}: identity GLOBAL={identity_global} does not match heading")
        if gid in seen_global:
            raise MasterParseError(f"duplicate global slide id G{gid:03d}")
        if lid in seen_local:
            raise MasterParseError(f"duplicate local slide id {lid}")
        seen_global.add(gid)
        seen_local.add(lid)
        didactic = _structured_fields(sections["B"])
        base = _visible_content(sections["C"])
        locked = LockedContent(
            title=base.title,
            subtitle=base.subtitle,
            visible_text=base.visible_text,
            callouts=base.callouts,
            caption=base.caption,
            question=base.question,
            speaker_notes_final=_extract_notes(sections["M"]),
            raw_visible_copy=base.raw_visible_copy,
        )
        visual = _structured_fields(sections["E"])
        layout = _structured_fields(sections["F"])
        typography = _structured_fields(sections["G"])
        accessibility = _structured_fields(sections["P"])
        specs.append(ScientificSlideSpec(
            source_file=source_file,
            deck_id=deck_id,
            global_id=gid,
            local_id=lid,
            total_slides=total,
            slide_type=_scalar(identity, ["SLIDE_TYPE", "TYPE"]),
            master_format=MasterFormat.RICH_A_S_MASTER,
            narrative_phase=_scalar(identity, ["NARRATIVE_PHASE", "PHASE"]),
            generality_level=_scalar(identity, ["GENERALITY_LEVEL", "GENERALITY", "LEVEL"]),
            priority=_scalar(identity, ["PRIORITY"]),
            blueprint_reference=_scalar(identity, ["BLUEPRINT_REFERENCE", "BLUEPRINT_REF", "BLUEPRINT"]),
            learning_objective=_scalar(didactic, ["LEARNING_OBJECTIVE"]),
            didactic_function=_scalar(didactic, ["DIDACTIC_FUNCTION"]),
            one_key_takeaway=_scalar(didactic, ["ONE_KEY_TAKEAWAY"]),
            link_from_previous=_scalar(didactic, ["LINK_FROM_PREVIOUS"]),
            link_to_next=_scalar(didactic, ["LINK_TO_NEXT"]),
            locked=locked,
            visual_thesis=_scalar(visual, ["VISUAL_THESIS"]),
            visual_type=_scalar(visual, ["VISUAL_TYPE"]),
            composition=_scalar(visual, ["COMPOSITION"]),
            focal_point=_scalar(visual, ["FOCAL_POINT"]),
            secondary_elements=_list_value(visual, ["SECONDARY_ELEMENTS"]),
            visual_hierarchy=_scalar(visual, ["VISUAL_HIERARCHY"]),
            canvas=_scalar(layout, ["CANVAS"]),
            background=_scalar(layout, ["BACKGROUND"]),
            grid=_scalar(layout, ["GRID"]),
            safe_area=_scalar(layout, ["SAFE_AREA"]),
            element_map={**_section_dict(sections["F"]), "element_map": _scalar(layout, ["ELEMENT_MAP"])},
            title_font=_scalar(typography, ["TITLE_FONT"]),
            title_size=_scalar(typography, ["TITLE_SIZE"]),
            title_weight=_scalar(typography, ["TITLE_WEIGHT"]),
            body_font=_scalar(typography, ["BODY_FONT"]),
            body_size=_scalar(typography, ["BODY_SIZE"]),
            label_size=_scalar(typography, ["LABEL_SIZE"]),
            footer_size=_scalar(typography, ["FOOTER_SIZE"]),
            alignment_rules=_scalar(typography, ["ALIGNMENT_RULES"]),
            color_roles=_section_dict(sections["H"]),
            asset_specification=_section_dict(sections["I"]),
            diagram_specification=_section_dict(sections["J"]),
            table_specification=_section_dict(sections["K"]),
            chart_specification=_section_dict(sections["L"]),
            instructor_cue=_scalar(_structured_fields(sections["N"]), ["INSTRUCTOR_CUE"], sections["N"]),
            sources=_plain_list(sections["O"]),
            accessibility=_section_dict(sections["P"]),
            reading_order=_scalar(accessibility, ["READING_ORDER"]),
            contrast=_scalar(accessibility, ["CONTRAST_NOTES", "CONTRAST"]),
            projector_readability=_scalar(accessibility, ["PROJECTOR_READABILITY"]),
            animation=_section_dict(sections["Q"]),
            production_constraints=_plain_list(sections["R"]),
            acceptance_criteria=_plain_list(sections["S"]),
            raw_sections={SECTION_MAP[label]: sections[label] for label in SECTION_MAP},
            unknown_sections={},
            source_hash=_hash_block(source_file, deck_id, gid, lid, block),
            source_block=block,
        ))
    _validate_sequence(specs, declared_count)
    return specs


def _parse_compact(text: str, source_file: str) -> List[ScientificSlideSpec]:
    deck_id = _deck_id(text, source_file)
    declared_count = _declared_count(text)
    matches = list(COMPACT_SLIDE_HEADING.finditer(text))
    if not matches:
        raise MasterParseError("no canonical G### slide headings found")
    specs: List[ScientificSlideSpec] = []
    seen_global: set[int] = set()
    seen_local: set[int] = set()
    for index, match in enumerate(matches):
        block = _norm(text[match.start() : matches[index + 1].start() if index + 1 < len(matches) else len(text)])
        fields = _parse_compact_fields(block)
        missing = [name for name in ("VISIBLE COPY", "VISUAL", "NOTES", "SOURCES") if not fields.get(name)]
        if missing:
            raise MasterParseError(f"G{match.group('global')}: missing required fields: {', '.join(missing)}")
        gid, lid, total = int(match.group("global")), int(match.group("local")), int(match.group("total"))
        if gid in seen_global:
            raise MasterParseError(f"duplicate global slide id G{gid:03d}")
        if lid in seen_local:
            raise MasterParseError(f"duplicate local slide id {lid}")
        seen_global.add(gid)
        seen_local.add(lid)
        base = _compact_visible_content(fields["VISIBLE COPY"])
        locked = LockedContent(
            title=base.title,
            subtitle=base.subtitle,
            visible_text=base.visible_text,
            callouts=base.callouts,
            caption=base.caption,
            question=base.question,
            speaker_notes_final=fields["NOTES"],
            raw_visible_copy=base.raw_visible_copy,
        )
        specs.append(ScientificSlideSpec(
            source_file=source_file,
            deck_id=deck_id,
            global_id=gid,
            local_id=lid,
            total_slides=total,
            slide_type=match.group("type").strip(),
            master_format=MasterFormat.COMPACT_FINAL_LEGACY,
            generality_level=match.group("type").split("·", 1)[0].strip(),
            locked=locked,
            visual_thesis=fields["VISUAL"],
            visual_type=fields["VISUAL"],
            diagram_specification={"canonical_visual": fields["VISUAL"], "raw": fields["VISUAL"]},
            sources=[s.strip() for s in re.split(r"\s*;\s*", fields["SOURCES"]) if s.strip()],
            accessibility={"alt_text_required": True, "no_color_only_meaning": True},
            production_constraints=["no_font_shrinking", "didactic_text>=18pt", "safe_area>=0.55in"],
            acceptance_criteria=["locked_copy_exact", "notes_exact", "editable_text", "projector_readable"],
            raw_sections=fields,
            source_hash=_hash_block(source_file, deck_id, gid, lid, block),
            source_block=block,
        ))
    _validate_sequence(specs, declared_count)
    return specs


def _validate_sequence(specs: List[ScientificSlideSpec], declared_count: int | None = None) -> None:
    if not specs:
        raise MasterParseError("empty slide set")
    expected_count = declared_count or len(specs)
    if len(specs) != expected_count:
        raise MasterParseError(f"declared count {expected_count} != parsed count {len(specs)}")
    if {s.total_slides for s in specs} != {expected_count}:
        raise MasterParseError("inconsistent total slide declarations")
    if set(range(1, expected_count + 1)) != {s.local_id for s in specs}:
        raise MasterParseError("missing local slide ids")
    globals_sorted = [s.global_id for s in sorted(specs, key=lambda s: s.local_id)]
    if globals_sorted != list(range(globals_sorted[0], globals_sorted[0] + expected_count)):
        raise MasterParseError("missing global slide ids")


def validate_corpus(
    spec_groups: Iterable[Sequence[ScientificSlideSpec]],
    *,
    first_global_id: int = 1,
    last_global_id: int = 600,
) -> None:
    specs = [spec for group in spec_groups for spec in group]
    ids = [spec.global_id for spec in specs]
    if len(ids) != len(set(ids)):
        duplicates = sorted(gid for gid in set(ids) if ids.count(gid) > 1)
        raise MasterParseError(f"duplicate global slide ids across corpus: {duplicates}")
    expected = list(range(first_global_id, last_global_id + 1))
    if sorted(ids) != expected:
        missing = sorted(set(expected) - set(ids))
        extras = sorted(set(ids) - set(expected))
        raise MasterParseError(f"corpus global-id mismatch; missing={missing}, extras={extras}")


def parse_master_text(text: str, source_file: str = "<memory>") -> List[ScientificSlideSpec]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return _parse_rich(text, source_file) if detect_master_format(text) is MasterFormat.RICH_A_S_MASTER else _parse_compact(text, source_file)


def parse_master_file(path: Path, root: Path | None = None) -> List[ScientificSlideSpec]:
    if not path.exists():
        raise MasterParseError(f"master not found: {path}")
    source = str(path.relative_to(root)) if root else str(path)
    return parse_master_text(path.read_text(encoding="utf-8"), source)
