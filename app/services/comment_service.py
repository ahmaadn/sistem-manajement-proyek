import logging
from typing import Any, Mapping, Optional, cast

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
from app.schemas.comment import (
    CommentCreate,
    CommentDetail,
    CommentWithAuditRead,
    CommentWithCommentRead,
)
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

    async def list_comments_with_audits(
        self,
        *,
        task_id: int,
        user_id: int,
        is_admin: bool = False,
        include_audits: bool = True,
    ) -> list[CommentWithCommentRead | CommentWithAuditRead]:
        """Menggabungkan komentar dan event audit terpilih untuk suatu task.

        - Akses dibatasi untuk anggota proyek (termasuk owner) atau admin.
        - Jika ``include_audits`` True, event audit akan disertakan.
        - Hasil diurutkan dari yang paling lama ke yang paling baru
          berdasarkan waktu pembuatan.
        """

        # Cek permisi
        if not is_admin:
            is_member = await self.uow.task_repo.is_user_member_of_task_project(
                task_id=task_id, user_id=user_id
            )
            if not is_member:
                raise exceptions.ForbiddenError(
                    "Anda tidak memiliki izin untuk melihat komentar ini"
                )

        # Ambil komentar mentah dan audit terlebih dahulu
        comments = await self.uow.comment_repo.list_by_task_id(task_id=task_id)

        audits = []
        if include_audits:
            audits = await self._get_audits_raw(task_id)

        # Kumpulkan semua id pengguna (penulis komentar + pelaksana audit)
        user_ids: set[int] = {c.user_id for c in comments}
        user_ids.update(
            x.performed_by for x in audits if getattr(x, "performed_by", None)
        )

        # Memperkaya pengguna melalui satu panggilan
        users_by_id = await self._get_users_map(list(user_ids))

        # Membuat komentar
        comment_items: list[CommentWithCommentRead] = []
        for comment in comments:
            u = users_by_id.get(comment.user_id)
            detail = CommentDetail(
                id=comment.id,
                task_id=comment.task_id,
                user_id=comment.user_id,
                content=comment.content,
                created_at=comment.created_at,
                profile_url=(u.profile_url if u else None),
                user_name=(u.name if u else None),
                attachments=list(comment.attachments),  # type: ignore
            )
            comment_items.append(CommentWithCommentRead(type="comment", data=detail))

        # Membuar audit
        audit_items: list[CommentWithAuditRead] = []
        if include_audits:
            for a in audits:
                audit_schema = self._map_audit_to_schema(a, users_by_id)
                audit_items.append(
                    CommentWithAuditRead(type="audit", data=audit_schema)
                )

        # Gabungkan dan urutkan berdasarkan waktu pembuatan
        combined: list[tuple] = []
        for item in comment_items:
            combined.append((item.data.created_at, item))
        for idx in range(len(audits)):
            combined.append((audits[idx].created_at, audit_items[idx]))

        combined.sort(key=lambda x: x[0])
        return [item for _, item in combined]

    async def get_audits(self, *, task_id: int) -> list[TaskAuditSchema]:
        """Mengambil daftar audit bertipe (tanpa enrikmen data user).

        Cocok untuk pemakaian internal atau endpoint terpisah.
        """
        audits = await self._get_audits_raw(task_id)
        out: list[TaskAuditSchema] = []

        for a in audits:
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
                    assignee_name=str((a.details or {}).get("assignee_name", "")),
                )
            else:
                det = TaskAssignRemovedAuditSchama(
                    assignee_id=str((a.details or {}).get("assignee_id", "")),
                    assignee_name=str((a.details or {}).get("assignee_name", "")),
                )

            out.append(
                TaskAuditSchema(
                    audit_id=getattr(a, "id", 0) or 0,
                    user_id=getattr(a, "performed_by", 0) or 0,
                    profile_url=0,
                    user_name="",
                    task_id=str(a.task_id) if a.task_id is not None else "",
                    created_at=(a.created_at.isoformat() if a.created_at else ""),
                    action_type=cast(TaskActionType, atype),
                    details=det,
                )
            )
        return out

    async def _get_users_map(self, user_ids: list[int]):
        if not user_ids:
            return {}
        pegawai_service = PegawaiService()
        users = await pegawai_service.list_user_by_ids(user_ids)
        return {u.id: u for u in users if u}

    async def _get_audits_raw(self, task_id: int):
        event_types = [
            EventType.TASK_STATUS_CHANGED.value,
            EventType.TASK_TITLE_CHANGED.value,
            EventType.TASK_ASSIGNED_ADDED.value,
            EventType.TASK_ASSIGNED_REMOVED.value,
        ]
        return await self.uow.audit_repo.list_task_audits(
            task_id=task_id, event_types=event_types
        )

    def _map_audit_details(self, atype: EventType, details: dict | None):
        d = details or {}
        if atype == EventType.TASK_STATUS_CHANGED:
            return TaskStatusChangeAuditSchema(
                old_status=str(d.get("old_status", "")),
                new_status=str(d.get("new_status", "")),
            )
        if atype == EventType.TASK_TITLE_CHANGED:
            return TaskTitleChangeAuditSchema(
                before=str(d.get("before", "")),
                after=str(d.get("after", "")),
            )
        if atype == EventType.TASK_ASSIGNED_ADDED:
            return TaskAssignAddedAuditSchama(
                assignee_id=str(d.get("assignee_id", "")),
                assignee_name=str(d.get("assignee_name", "")),
            )
        return TaskAssignRemovedAuditSchama(
            assignee_id=str(d.get("assignee_id", "")),
            assignee_name=str(d.get("assignee_name", "")),
        )

    def _map_audit_to_schema(
        self,
        a,
        users_by_id: Mapping[int, Any],
    ) -> TaskAuditSchema:
        atype = EventType(a.action_type)
        det = self._map_audit_details(atype, getattr(a, "details", None))
        performer = users_by_id.get(getattr(a, "performed_by", 0) or 0)
        user_name = getattr(performer, "name", "") if performer else ""
        return TaskAuditSchema(
            audit_id=getattr(a, "id", 0) or 0,
            user_id=getattr(a, "performed_by", 0) or 0,
            profile_url=0,
            user_name=user_name,
            task_id=str(a.task_id) if a.task_id is not None else "",
            created_at=(a.created_at.isoformat() if a.created_at else ""),
            action_type=cast(TaskActionType, atype),
            details=det,
        )

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
