from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from scientific_slide_engine.capabilities import scientific_capabilities
from scientific_slide_engine.compiler import compile_fidelity, compile_strict
from scientific_slide_engine.parser import MasterParseError, parse_master_text
from scientific_slide_engine.service import persist_strict_presentation, validate_request_count
from services.database import get_async_session

SCIENTIFIC_ROUTER = APIRouter(prefix="/scientific", tags=["Scientific Slide Engine"])


class ScientificGenerateRequest(BaseModel):
    mode: str = Field(default="strict_materialize")
    theme: str = Field(default="scientific-editorial")
    master_markdown: str
    source_file: str = Field(default="<request>")
    slide_ids: Optional[List[int]] = None
    dark_slide_ids: List[int] = Field(default_factory=list)
    title: Optional[str] = None
    language: str = Field(default="it")
    persist: bool = Field(default=True)


@SCIENTIFIC_ROUTER.get("/capabilities")
async def get_scientific_capabilities() -> dict:
    return scientific_capabilities()


@SCIENTIFIC_ROUTER.post("/generate")
async def generate_scientific_presentation(
    request: ScientificGenerateRequest,
    sql_session: AsyncSession = Depends(get_async_session),
) -> dict:
    if request.mode != "strict_materialize":
        raise HTTPException(status_code=400, detail="Only strict_materialize is enabled in M0")
    try:
        specs = parse_master_text(request.master_markdown, request.source_file)
    except MasterParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if request.slide_ids:
        requested = list(dict.fromkeys(request.slide_ids))
        by_id = {spec.global_id: spec for spec in specs}
        missing = [gid for gid in requested if gid not in by_id]
        if missing:
            raise HTTPException(status_code=422, detail=f"missing requested slide ids: {missing}")
        specs = [by_id[gid] for gid in requested]

    try:
        validate_request_count(specs)
        result = compile_strict(specs, request.theme, request.dark_slide_ids)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    pre_persistence_fidelity = compile_fidelity(specs, result.slides)
    if any(record["status"] != "PASS" for record in pre_persistence_fidelity):
        raise HTTPException(status_code=500, detail="strict content lock failed before persistence")

    if not request.persist:
        return {
            **result.as_dict(),
            "presentation_id": None,
            "content_fidelity": pre_persistence_fidelity,
            "persisted": False,
        }

    try:
        presentation, slides, post_persistence_fidelity = await persist_strict_presentation(
            sql_session,
            specs,
            result,
            title=request.title,
            language=request.language,
        )
    except Exception as exc:
        await sql_session.rollback()
        raise HTTPException(status_code=500, detail=f"strict persistence failed: {exc}") from exc

    return {
        "presentation_id": str(presentation.id),
        "presentation": presentation.model_dump(exclude={"layout", "structure"}),
        "slides": [slide.model_dump() for slide in slides],
        "mode": result.mode.value,
        "theme": result.theme,
        "render_contract": result.render_contract,
        "content_lock_status": result.content_lock_status,
        "speaker_notes_supported": True,
        "source_hashes": result.source_hashes,
        "visual_plans": [plan.as_dict() for plan in result.visual_plans],
        "content_fidelity": post_persistence_fidelity,
        "ui_qa": [slide["ui_qa"] for slide in result.slides],
        "persisted": True,
    }
