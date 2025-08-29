from __future__ import annotations

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Query,
    UploadFile,
    status,
)
from fastapi_utils.cbv import cbv

from app.api.dependencies.services import get_attachment_service
from app.api.dependencies.uow import get_uow
from app.api.dependencies.user import get_current_user
from app.core.domain.bus import set_event_background
from app.db.models.role_model import Role
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.attachment import AttachmentResponse
from app.schemas.user import User
from app.services.attachment_service import AttachmentService
from app.utils.exceptions import AppErrorResponse

r = router = APIRouter(tags=["attachments"])


@cbv(r)
class _Attachment:
    uow: UnitOfWork = Depends(get_uow)
    user: User = Depends(get_current_user)
    attachment_service: AttachmentService = Depends(get_attachment_service)

    @r.post(
        "/attachment",
        response_model=AttachmentResponse,
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_201_CREATED: {
                "description": (
                    "Membuat lampiran. url tidak akan langsung muncul disebabkan "
                    "proses latar belakang. setelah upoload selesai sistem akan "
                    "mengirim ke event sse dan pusher. "
                    "type event: **attachment.uploaded**"
                ),
                "model": AttachmentResponse,
            },
            status.HTTP_403_FORBIDDEN: {
                "description": "User is not a member of the project",
                "model": AppErrorResponse,
            },
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {
                "description": "Invalid file type",
                "model": AppErrorResponse,
            },
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
                "description": "File too large",
                "model": AppErrorResponse,
            },
        },
    )
    async def upload_attachment(
        self,
        bg_tasks: BackgroundTasks,  # FastAPI auto-injects this
        task_id: int = Query(..., description="Task ID"),
        comment_id: int | None = Query(
            default=None, description="Comment ID (opsional)"
        ),
        file: UploadFile = File(...),
    ):
        """
        Upload file. extensi yang di ijinkan pdf, word, png, jpeg. masksimal 5MB.
        komentar dapat di sisipkan di task atau comment (tambahkan commen_id)

        **Akses**: Project Member, Admin
        """
        set_event_background(bg_tasks)

        async with self.uow:
            att = await self.attachment_service.create_attachment(
                file=file,
                task_id=task_id,
                actor=self.user,
                comment_id=comment_id,
                is_admin=self.user.role == Role.ADMIN,
            )
            await self.uow.commit()
        return att

    @r.delete(
        "/attachment/{attachment_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={
            status.HTTP_204_NO_CONTENT: {"description": "Attachment deleted"},
            status.HTTP_404_NOT_FOUND: {
                "description": "Attachment not found",
                "model": AppErrorResponse,
            },
        },
    )
    async def delete_attachment(self, attachment_id: int, bg_tasks: BackgroundTasks):
        """
        Menghapus file lampiran.

        **Akses**: Owner Project, Admin
        """
        set_event_background(bg_tasks)

        async with self.uow:
            await self.attachment_service.delete_attachment(
                attachment_id=attachment_id, actor=self.user
            )
            await self.uow.commit()
