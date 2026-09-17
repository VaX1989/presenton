import os
import logging
from typing import Literal
from urllib.parse import urlencode
import uuid

from pathvalidate import sanitize_filename
from sqlmodel import select

from models.presentation_and_path import PresentationAndPath
from models.sql.presentation import PresentationModel
from models.sql.slide import SlideModel
from scientific_slide_engine.pptx_finalize import finalize_scientific_pptx
from services.database import async_session_maker
from utils.filename_utils import safe_export_basename
from services.export_task_service import EXPORT_TASK_SERVICE
from utils.runtime_limits import log_memory


LOGGER = logging.getLogger(__name__)


def _get_next_public_url() -> str:
    return (os.getenv("NEXT_PUBLIC_URL") or "").strip() or "http://127.0.0.1"


def _get_next_public_fastapi_url() -> str | None:
    value = (os.getenv("NEXT_PUBLIC_FAST_API") or "").strip()
    return value or None


def _build_presentation_export_url(
    presentation_id: uuid.UUID, cookie_header: str | None = None
) -> tuple[str, str | None]:
    params = {"id": str(presentation_id)}
    fastapi_url = _get_next_public_fastapi_url()
    if fastapi_url:
        params["fastapiUrl"] = fastapi_url
    export_url = f"{_get_next_public_url().rstrip('/')}/pdf-maker?{urlencode(params)}"
    if cookie_header:
        export_url = f"{export_url}#{urlencode({'exportCookie': cookie_header})}"
    return (
        export_url,
        fastapi_url,
    )


async def _finalize_scientific_pptx_if_needed(
    presentation_id: uuid.UUID,
    output_path: str,
) -> None:
    """Complete notes only for strict scientific decks after normal export-core render."""
    async with async_session_maker() as sql_session:
        presentation = await sql_session.get(PresentationModel, presentation_id)
        if presentation is None:
            return
        theme = presentation.theme if isinstance(presentation.theme, dict) else {}
        if theme.get("scientific_strict") is not True:
            return

        slides = list(
            await sql_session.scalars(
                select(SlideModel)
                .where(SlideModel.presentation == presentation_id)
                .order_by(SlideModel.index)
            )
        )
        if len(slides) != presentation.n_slides:
            raise RuntimeError(
                "scientific PPTX finalization refused: persisted slide count "
                f"{len(slides)} != presentation.n_slides {presentation.n_slides}"
            )

        notes = [slide.speaker_note or "" for slide in slides]
        report = finalize_scientific_pptx(output_path, notes)
        LOGGER.info(
            "[scientific_export] exact notes finalized presentation_id=%s slides=%s notes=%s editable_text_runs=%s",
            presentation_id,
            report["slide_count"],
            report["notes_count"],
            report["editable_text_runs"],
        )


async def export_presentation(
    presentation_id: uuid.UUID,
    title: str,
    export_as: Literal["pptx", "pdf"],
    cookie_header: str | None = None,
) -> PresentationAndPath:
    log_memory(
        LOGGER,
        "presentation.export.start",
        presentation_id=str(presentation_id),
        export_as=export_as,
    )
    export_url, fastapi_url = _build_presentation_export_url(
        presentation_id, cookie_header
    )
    name = (title or "").strip() or str(uuid.uuid4())
    export_result = await EXPORT_TASK_SERVICE.export_from_url(
        url=export_url,
        title=safe_export_basename(sanitize_filename(name)),
        export_as=export_as,
        fastapi_url=fastapi_url,
        cookie_header=cookie_header,
    )
    if export_as == "pptx":
        await _finalize_scientific_pptx_if_needed(
            presentation_id,
            export_result.path,
        )
    log_memory(
        LOGGER,
        "presentation.export.finish",
        presentation_id=str(presentation_id),
        export_as=export_as,
    )
    return PresentationAndPath(
        presentation_id=presentation_id,
        path=export_result.path,
    )
