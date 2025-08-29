import logging
from typing import Optional, Sequence

from app.db.models.comment_model import Comment
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.comment import CommentCreate
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
        is_active = await self.uow.task_repo.is_active_task(task_id=task_id)
        if not is_active:
            logger.debug(
                f"User {user_id} is trying to add comment to inactive task {task_id}"
            )
            raise exceptions.CommentCannotBeAddedError(
                "tidak dapat berkomentar pada proyek yang tidak aktif"
            )

        if not is_admin:
            is_member = await self.uow.task_repo.is_member_of_task_project(
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
        return await self.uow.comment_repo.create(
            task_id=task_id, user_id=user_id, content=payload.content
        )

    async def list_comments(
        self, task_id: int, user_id: int, is_admin: bool = False
    ) -> Sequence[Comment]:
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
        is_member = await self.uow.task_repo.is_member_of_task_project(
            user_id, task_id
        )
        if not is_member and not is_admin:
            raise exceptions.ForbiddenError(
                "Anda tidak memiliki izin untuk melihat komentar ini"
            )
        return await self.uow.comment_repo.list_by_task(task_id=task_id)

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
        is_member = await self.uow.task_repo.is_member_of_task_project(
            user_id, task_id
        )
        if not is_member and not is_admin:
            logger.debug(
                f"User {user_id} is not allowed to view comment {comment_id}"
            )
            raise exceptions.ForbiddenError(
                "Anda tidak memiliki izin untuk melihat komentar ini"
            )

        return await self.uow.comment_repo.get(
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
        comment = await self.uow.comment_repo.get(
            comment_id=comment_id, task_id=task_id
        )
        if not comment:
            raise exceptions.CommentNotFoundError

        # Admin selalu boleh
        if is_admin:
            logger.info(f"Admin {user_id} is deleting comment {comment_id}")
            return await self.uow.comment_repo.delete_by_id(
                comment_id=comment_id, task_id=task_id
            )

        # Pembuat komentar boleh
        if comment.user_id == user_id:
            logger.info(f"User {user_id} is deleting their own comment {comment_id}")
            return await self.uow.comment_repo.delete_by_id(
                comment_id=comment_id, task_id=task_id
            )

        # Owner project tempat task berada juga boleh
        is_owner = await self.uow.task_repo.is_owner_of_project_by_task(
            user_id, task_id
        )
        if not is_owner:
            # Tidak memenuhi salah satu kriteria
            raise exceptions.ForbiddenError(
                "Anda tidak memiliki izin untuk menghapus komentar ini"
            )

        logger.info(f"Owner {user_id} is deleting comment {comment_id}")
        return await self.uow.comment_repo.delete_by_id(
            comment_id=comment_id, task_id=task_id
        )
