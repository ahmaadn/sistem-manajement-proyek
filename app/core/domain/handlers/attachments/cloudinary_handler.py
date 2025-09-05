from __future__ import annotations

import logging

from app.core.domain.bus import subscribe_background
from app.core.domain.events.attachment import (
    AttachmentDeleteRequestedEvent,
    AttachmentUploadRequestedEvent,
)
from app.db.base import async_session_maker
from app.db.repositories.attachment_repository import AttachmentSQLAlchemyRepository
from app.utils.cloudinary import destroy_by_url, upload_bytes

logger = logging.getLogger(__name__)


async def on_attachment_upload_requested(ev: AttachmentUploadRequestedEvent) -> None:
    """Menangani permintaan unggahan file.

    Args:
        ev (AttachmentUploadRequestedEvent): Event yang berisi detail unggahan.
    """

    logger.info("attachment.upload.start", extra={"attachment_id": ev.attachment_id})
    try:
        result = upload_bytes(
            file_bytes=ev.file_bytes, filename=ev.original_filename
        )
        url = result.get("secure_url") or result.get("url") or ""
        bytes_size = result.get("bytes") or len(ev.file_bytes)

        async with async_session_maker() as session:
            repo = AttachmentSQLAlchemyRepository(session)
            await repo.finalize_upload(
                attachment_id=ev.attachment_id,
                file_path=url,
                file_size=str(bytes_size),
                session=session,
            )
        logger.info(
            "attachment.upload.done", extra={"attachment_id": ev.attachment_id}
        )
    except Exception as e:
        logger.exception("attachment.upload.failed", extra={"error": str(e)})
        async with async_session_maker() as session:
            repo = AttachmentSQLAlchemyRepository(session)
            await repo.finalize_upload(
                attachment_id=ev.attachment_id,
                file_path="Error Uploading",
                file_size=str(0),
                session=session,
            )


async def on_attachment_delete_requested(ev: AttachmentDeleteRequestedEvent) -> None:
    logger.info(
        "attachment.delete.provider", extra={"attachment_id": ev.attachment_id}
    )
    try:
        if ev.file_url:
            destroy_by_url(ev.file_url)
    except Exception:
        logger.exception("attachment.delete.provider_failed")


def register_event_handlers() -> None:
    subscribe_background(
        AttachmentUploadRequestedEvent, on_attachment_upload_requested
    )
    subscribe_background(
        AttachmentDeleteRequestedEvent, on_attachment_delete_requested
    )
