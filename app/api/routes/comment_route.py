import logging

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi_utils.cbv import cbv

from app.api.dependencies.services import get_comment_service
from app.api.dependencies.uow import get_uow
from app.api.dependencies.user import get_current_user
from app.db.models.role_model import Role
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.comment import (
    CommentCreate,
    CommentRead,
    CommentWithAuditRead,
    CommentWithCommentRead,
)
from app.schemas.user import User
from app.services.comment_service import CommentService
from app.utils import exceptions
from app.utils.exceptions import AppErrorResponse

logger = logging.getLogger(__name__)
r = router = APIRouter(tags=["comments"])


@cbv(r)
class _Comment:
    user: User = Depends(get_current_user)
    service: CommentService = Depends(get_comment_service)
    uow: UnitOfWork = Depends(get_uow)

    @r.post(
        "/comments",
        response_model=CommentRead,
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_406_NOT_ACCEPTABLE: {
                "model": AppErrorResponse,
                "description": (
                    "User tidak dapat membuat komentar. error_code : "
                    "COMMENT_NOT_ALLOWED"
                ),
            }
        },
    )
    async def create_comment(self, payload: CommentCreate):
        """Membuat komentar baru.

        **Akses** : Admin, Anggota Proyek
        """
        async with self.uow:
            comment = await self.service.create_comment(
                payload.task_id, self.user.id, payload, self.user.role == Role.ADMIN
            )
            await self.uow.commit()

        return comment

    @r.get(
        "/tasks/{task_id}/comments",
        response_model=list[CommentWithCommentRead | CommentWithAuditRead],
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_403_FORBIDDEN: {
                "model": AppErrorResponse,
                "description": (
                    "User tidak dapat melihat komentar. error_code : FORBIDDEN"
                ),
            }
        },
    )
    async def list_comments(
        self,
        task_id: int,
        include_audits: bool = Query(
            True,
            description="Tampilkan audit (status/title/assignee) bersama komentar",
        ),
    ):
        """Mendapatkan daftar komentar untuk tugas tertentu.

        **Akses** : Anggota Proyek (Termasuk Owner), Admin
        """
        return await self.service.list_comments_with_audits(
            task_id=task_id,
            user_id=self.user.id,
            is_admin=self.user.role == Role.ADMIN,
            include_audits=include_audits,
        )

    @r.delete(
        "/tasks/{task_id}/comments/{comment_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={
            status.HTTP_403_FORBIDDEN: {
                "model": AppErrorResponse,
                "description": ("User tidak punya akses. error_code : FORBIDDEN"),
            },
            status.HTTP_404_NOT_FOUND: {
                "model": AppErrorResponse,
                "description": (
                    "Komentar tidak ditemukan. error_code : COMMENT_NOT_FOUND"
                ),
            },
        },
    )
    async def delete_comment(self, task_id: int, comment_id: int):
        """Menghapus komentar.

        **Akses** : Pembuat Komentar, Owner Proyek, Admin
        """
        async with self.uow:
            deleted = await self.service.delete_comment(
                task_id, comment_id, self.user.id, self.user.role == Role.ADMIN
            )
            await self.uow.commit()

        if not deleted:
            logger.error("Failed to delete comment")
            raise exceptions.InternalServerError("Failed to delete comment")

        return Response(status_code=status.HTTP_204_NO_CONTENT)
