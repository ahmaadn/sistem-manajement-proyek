from typing import List

from fastapi import UploadFile

from app.core.domain.events.attachment import (
    AttachmentDeleteRequestedEvent,
    AttachmentUploadRequestedEvent,
)
from app.db.models.attachment_model import Attachment
from app.db.models.role_model import Role
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.user import User
from app.utils import exceptions

ALLOWED_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
}

MAX_SIZE = 5 * 1024 * 1024  # 5 MB


class AttachmentService:
    """Service untuk operasi terkait attachment."""

    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.repo = self.uow.attachment_repo

    async def get_attachment(self, attachment_id: int) -> Attachment | None:
        """Mendapatkan attachment berdasarkan ID."""
        return await self.repo.get(attachment_id)

    async def get_attachments_by_task(self, task_id: int) -> List[Attachment]:
        """Mendapatkan semua attachment untuk task tertentu."""
        return await self.repo.list(task_id=task_id)

    async def create_task_attachment(
        self,
        *,
        file: UploadFile,
        task_id: int,
        actor: User,
        is_admin: bool = False,
    ) -> Attachment:
        if not is_admin:
            is_member = await self.uow.task_repo.is_member_of_task_project(
                task_id=task_id, user_id=actor.id
            )
            if not is_member:
                raise exceptions.NotAMemberError("Anda bukan anggota proyek ini.")

        if file.content_type not in ALLOWED_EXTENSIONS:
            raise exceptions.MediaNotSupportedError(
                "Tipe file tidak didukung. Hanya PNG, JPG/JPEG, PDF, dan WORD."
            )

        file_bytes = await file.read()
        file_size = len(file_bytes)
        if file_size > MAX_SIZE:
            raise exceptions.FileTooLargeError(
                "Ukuran file melebihi batas yang diizinkan."
            )

        return await self.upload_attachment(
            user=actor,
            file=file,
            file_bytes=file_bytes,
            task_id=task_id,
            file_size=str(file_size),
            comment_id=None,
        )

    async def create_comment_attachment(
        self,
        *,
        file: UploadFile,
        comment_id: int,
        actor: User,
    ) -> Attachment:
        comment = await self.uow.comment_repo.get_by_id(comment_id=comment_id)

        if comment is None:
            raise exceptions.CommentNotFoundError("Komentar tidak ditemukan.")

        if comment.user_id != actor.id:
            raise exceptions.ForbiddenError(
                "Anda tidak memiliki izin untuk mengunggah lampiran ini."
            )

        if file.content_type not in ALLOWED_EXTENSIONS:
            raise exceptions.MediaNotSupportedError(
                "Tipe file tidak didukung. Hanya PNG, JPG/JPEG, PDF, dan WORD."
            )

        file_bytes = await file.read()
        file_size = len(file_bytes)
        if file_size > MAX_SIZE:
            raise exceptions.FileTooLargeError(
                "Ukuran file melebihi batas yang diizinkan."
            )

        return await self.upload_attachment(
            user=actor,
            file=file,
            file_bytes=file_bytes,
            task_id=comment.task_id,
            file_size=str(file_size),
            comment_id=None,
        )

    async def upload_attachment(
        self,
        *,
        user: User,
        file: UploadFile,
        file_bytes: bytes,
        file_size: str,
        task_id: int,
        comment_id: int | None = None,
    ) -> Attachment:
        """Mengupload attachment baru."""
        att: Attachment = await self.repo.create(
            payload={
                "user_id": user.id,
                "task_id": task_id,
                "comment_id": comment_id,
                "file_name": file.filename or "attachment",
                "file_size": file_size,
                "file_path": "Progress Upload ...",
                "mime_type": file.content_type or "application/octet-stream",
            }
        )

        self.uow.add_event(
            AttachmentUploadRequestedEvent(
                attachment_id=att.id,
                task_id=task_id,
                user_id=user.id,
                comment_id=comment_id,
                file_bytes=file_bytes,
                content_type=file.content_type or "application/octet-stream",
                original_filename=file.filename or "attachment",
            )
        )
        return att

    async def delete_attachment(self, attachment_id: int, actor: User) -> None:
        """Menghapus attachment."""

        attachment = await self.get_attachment(attachment_id)
        if not attachment:
            raise exceptions.AttachmentNotFoundError("Attachment tidak ditemukan.")

        if actor.role != Role.ADMIN:
            task = await self.uow.task_repo.get(task_id=attachment.task_id)
            if not task:
                raise exceptions.TaskNotFoundError

            is_owner = await self.uow.project_repo.is_project_owner(
                project_id=task.project_id, user_id=actor.id
            )

            if not is_owner:
                raise exceptions.ForbiddenError("Anda bukan pemilik proyek ini.")

        # Trigger event untuk delete file dari cloudinary di background
        self.uow.add_event(
            AttachmentDeleteRequestedEvent(
                attachment_id=attachment.id,
                file_url=attachment.file_path,
            )
        )

        await self.repo.delete(attachment.id)
