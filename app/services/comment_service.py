import logging
from typing import Optional, cast

from app.core.domain.event import EventType
from app.db.models.comment_model import Comment
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.audit import (
    TaskActionType,
    TaskAssignAddedAuditSchama,
    TaskAssignRemovedAuditSchama,
    TaskAuditSchema,
    TaskStatusChangeAuditSchema,
    TaskTitleChangeAuditSchema,
)
from app.schemas.comment import CommentCreate, CommentDetail, CommentWithEventsRead
from app.services.pegawai_service import PegawaiService
from app.utils import exceptions

logger = logging.getLogger(__name__)


class CommentService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_comment(
        self,
        task_id: int,
        user_id: int,
        payload: CommentCreate,
        is_admin: bool = False,
    ) -> Comment:
        is_active = await self.uow.task_repo.is_task_in_active_project(
            task_id=task_id
        )
        if not is_active:
            logger.debug(
                f"User {user_id} is trying to add comment to inactive task {task_id}"
            )
            raise exceptions.CommentCannotBeAddedError(
                "tidak dapat berkomentar pada proyek yang tidak aktif"
            )

        if not is_admin:
            is_member = await self.uow.task_repo.is_user_member_of_task_project(
                task_id=task_id, user_id=user_id
            )

            logger.debug(
                f"Is user {user_id} member of task {task_id} project? {is_member}"
            )
            if not is_member:
                raise exceptions.CommentCannotBeAddedError(
                    "Anda tidak memiliki izin untuk menambahkan komentar"
                )

        logger.info(f"User {user_id} is adding comment to task {task_id}")
        return await self.uow.comment_repo.create_comment(
            task_id=task_id, user_id=user_id, content=payload.content
        )

    async def list_comments(
        self, task_id: int, user_id: int, is_admin: bool = False
    ):
        """
        Mendapatkan daftar komentar untuk tugas tertentu. komentar yang hanya dapat
        dilihat oleh anggota proyek (termasuk owner) atau admin.

        Args:
            user_id (int): ID pengguna
            task_id (int): ID tugas
            is_admin (bool, optional): Apakah pengguna adalah admin. Defaults to
                False.

        Raises:
            exceptions.ForbiddenError: Jika pengguna tidak memiliki izin.

        Returns:
            Sequence[Comment]: Daftar komentar yang ditemukan.
        """
        if not is_admin:
            is_member = await self.uow.task_repo.is_user_member_of_task_project(
                task_id=task_id, user_id=user_id
            )
            if not is_member:
                raise exceptions.ForbiddenError(
                    "Anda tidak memiliki izin untuk melihat komentar ini"
                )

        comments = await self.uow.comment_repo.list_by_task_id(task_id=task_id)
        user_ids = {comment.user_id for comment in comments}

        pegawai_service = PegawaiService()
        users = await pegawai_service.list_user_by_ids(list(user_ids))

        return [
            CommentDetail(
                id=comment.id,
                task_id=comment.task_id,
                user_id=comment.user_id,
                content=comment.content,
                created_at=comment.created_at,
                profile_url=next(
                    (
                        user.profile_url
                        for user in users
                        if user and user.id == comment.user_id
                    ),
                    None,
                ),
                user_name=next(
                    (
                        user.name
                        for user in users
                        if user and user.id == comment.user_id
                    ),
                    None,
                ),
                attachments=list(comment.attachments),  # type: ignore # auto cast
            )
            for comment in comments
        ]

    async def list_comments_with_events(
        self,
        *,
        task_id: int,
        user_id: int,
        is_admin: bool = False,
        include_events: bool = True,
    ) -> list[CommentWithEventsRead]:
        """Gabungkan komentar dan event audit untuk sebuah task.

        - Akses dibatasi pada anggota project (termasuk owner) atau admin.
        - Jika ``include_events`` True, event audit tertentu akan disertakan.
        - Hasil diurutkan dari yang paling lama ke paling baru
          berdasarkan waktu pembuatan.
        """

        # Reuse permission checks and enrichment from existing list_comments
        comments_detail = await self.list_comments(
            task_id=task_id, user_id=user_id, is_admin=is_admin
        )

        combined: list[tuple] = []

        # Bungkus komentar ke bentuk union output
        for c in comments_detail:
            combined.append(
                (
                    c.created_at,
                    CommentWithEventsRead(type="comment", data=c),
                )
            )

        if include_events:
            # Ambil hanya event yang diminta
            event_types = [
                EventType.TASK_STATUS_CHANGED.value,
                EventType.TASK_TITLE_CHANGED.value,
                EventType.TASK_ASSIGNED_ADDED.value,
                EventType.TASK_ASSIGNED_REMOVED.value,
            ]

            audits = await self.uow.audit_repo.list_task_audits(
                task_id=task_id, event_types=event_types
            )

            for a in audits:
                # Tentukan schema detail berdasarkan tipe event
                atype = EventType(a.action_type)
                if atype == EventType.TASK_STATUS_CHANGED:
                    det = TaskStatusChangeAuditSchema(
                        old_status=str((a.details or {}).get("old_status", "")),
                        new_status=str((a.details or {}).get("new_status", "")),
                    )
                elif atype == EventType.TASK_TITLE_CHANGED:
                    det = TaskTitleChangeAuditSchema(
                        before=str((a.details or {}).get("before", "")),
                        after=str((a.details or {}).get("after", "")),
                    )
                elif atype == EventType.TASK_ASSIGNED_ADDED:
                    det = TaskAssignAddedAuditSchama(
                        assignee_id=str((a.details or {}).get("assignee_id", "")),
                        assignee_name=str(
                            (a.details or {}).get("assignee_name", "")
                        ),
                    )
                else:  # EventType.TASK_ASSIGNED_REMOVED
                    det = TaskAssignRemovedAuditSchama(
                        assignee_id=str((a.details or {}).get("assignee_id", "")),
                        assignee_name=str(
                            (a.details or {}).get("assignee_name", "")
                        ),
                    )

                audit_schema = TaskAuditSchema(
                    task_id=str(a.task_id) if a.task_id is not None else "",
                    create_at=(a.created_at.isoformat() if a.created_at else ""),
                    action_type=cast(TaskActionType, atype),
                    details=det,
                )
                combined.append(
                    (
                        a.created_at,
                        CommentWithEventsRead(type="event", data=audit_schema),
                    )
                )

        # Urutkan dari yang paling lama ke paling baru
        combined.sort(key=lambda x: x[0])

        # Kembalikan hanya payload union-nya
        return [item for _, item in combined]

    async def get_comment(
        self, task_id: int, user_id: int, comment_id: int, is_admin: bool = False
    ) -> Optional[Comment]:
        """Mendapatkan komentar berdasarkan ID. komentar yang hanya dapat dilihat
            oleh anggota proyek (termasuk owner) atau admin.

        Args:
            user_id (int): ID pengguna
            task_id (int): ID tugas
            comment_id (int): ID komentar
            is_admin (bool, optional): Apakah pengguna adalah admin. Defaults to
                False.

        Raises:
            ForbiddenError: Jika pengguna tidak memiliki izin.

        Returns:
            Optional[Comment]: Komentar yang ditemukan, atau None jika tidak ada.
        """
        is_member = await self.uow.task_repo.is_user_member_of_task_project(
            user_id, task_id
        )
        if not is_member and not is_admin:
            logger.debug(
                f"User {user_id} is not allowed to view comment {comment_id}"
            )
            raise exceptions.ForbiddenError(
                "Anda tidak memiliki izin untuk melihat komentar ini"
            )

        return await self.uow.comment_repo.get_by_id_in_task(
            comment_id=comment_id, task_id=task_id
        )

    async def delete_comment(
        self, task_id: int, user_id: int, comment_id: int, is_admin: bool = False
    ) -> bool:
        """Menhapus komentar. komentar bisa di delete hanya oleh admin, owner project
            dan pembuat komentar.

        Args:
            task_id (int): ID tugas
            comment_id (int): ID komentar
            user_id (int): ID pengguna
            is_admin (bool, optional): Apakah pengguna adalah admin. Defaults to
                False.

        Raises:
            CommentNotFoundError: Jika komentar tidak ditemukan.
            ForbiddenError: Jika komentar tidak dapat dihapus.

        Returns:
            bool: True jika komentar berhasil dihapus, False jika tidak.
        """
        # Ambil komentar terlebih dahulu untuk cek kepemilikan
        comment = await self.uow.comment_repo.get_by_id_in_task(
            comment_id=comment_id, task_id=task_id
        )
        if not comment:
            raise exceptions.CommentNotFoundError

        # Admin selalu boleh
        if is_admin:
            logger.info(f"Admin {user_id} is deleting comment {comment_id}")
            return await self.uow.comment_repo.delete_by_id_in_task(
                comment_id=comment_id, task_id=task_id
            )

        # Pembuat komentar boleh
        if comment.user_id == user_id:
            logger.info(f"User {user_id} is deleting their own comment {comment_id}")
            return await self.uow.comment_repo.delete_by_id_in_task(
                comment_id=comment_id, task_id=task_id
            )

        # Owner project tempat task berada juga boleh
        is_owner = await self.uow.task_repo.is_user_owner_of_tasks_project(
            user_id, task_id
        )
        if not is_owner:
            # Tidak memenuhi salah satu kriteria
            raise exceptions.ForbiddenError(
                "Anda tidak memiliki izin untuk menghapus komentar ini"
            )

        logger.info(f"Owner {user_id} is deleting comment {comment_id}")
        return await self.uow.comment_repo.delete_by_id_in_task(
            comment_id=comment_id, task_id=task_id
        )
