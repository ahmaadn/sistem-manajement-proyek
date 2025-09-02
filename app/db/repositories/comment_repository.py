from typing import Protocol, Sequence, runtime_checkable

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.comment_model import Comment
from app.db.models.project_model import Project, StatusProject
from app.db.models.task_model import Task


@runtime_checkable
class InterfaceCommentRepository(Protocol):
    """
    Interface untuk operasi repository Comment.
    Seluruh metode bersifat asinkron dan tidak melakukan commit; commit/rollback
    dikelola oleh lapisan pemanggil (service/UoW).
    """

    async def create(self, *, task_id: int, user_id: int, content: str) -> "Comment":
        """
        Membuat komentar baru pada sebuah task. Implementasi diharapkan melakukan
        flush/refresh seperlunya.

        Args:
            task_id: ID task yang akan diberi komentar.
            user_id: ID pengguna yang membuat komentar.
            content: Isi/teks komentar.

        Returns:
            Comment: Entitas komentar yang baru dibuat (sudah memiliki ID).
        """
        ...

    async def list_by_task(self, *, task_id: int) -> "Sequence[Comment]":
        """
        Mengambil daftar komentar berdasarkan ID task.

        Args:
            task_id: ID task yang komentarnya ingin diambil.

        Returns:
            Sequence[Comment]: Daftar komentar untuk task terkait, urutan sesuai
                kebijakan implementasi.
        """
        ...

    async def get(self, *, comment_id: int, task_id: int) -> "Comment | None":
        """
        Mengambil satu komentar berdasarkan ID komentar dan ID task-nya.

        Args:
            comment_id: ID komentar yang dicari.
            task_id: ID task pemilik komentar tersebut (untuk memastikan scoping).

        Returns:
            Comment | None: Entitas komentar jika ditemukan, None jika tidak ada.
        """
        ...

    async def get_by_id(self, *, comment_id: int) -> "Comment | None":
        """
        Mengambil satu komentar berdasarkan ID komentar dan ID task-nya.

        Args:
            comment_id: ID komentar yang dicari.
        Returns:
            Comment | None: Entitas komentar jika ditemukan, None jika tidak ada.
        """
        ...

    async def delete_by_id(self, *, comment_id: int, task_id: int) -> bool:
        """
        Menghapus sebuah komentar berdasarkan ID komentar dan ID task-nya.

        Args:
            comment_id: ID komentar yang akan dihapus.
            task_id: ID task pemilik komentar tersebut (untuk memastikan scoping).

        Returns:
            bool: True jika ada baris yang terhapus, False jika tidak ada.
        """
        ...

    async def is_active_task(self, *, task_id: int) -> bool:
        """
        Mengecek apakah task berada pada project yang masih aktif dan tidak dihapus.

        Args:
            task_id: ID task yang akan dicek.

        Returns:
            bool: True jika project aktif, False jika tidak.
        """
        ...


class CommentSQLAlchemyRepository(InterfaceCommentRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, task_id: int, user_id: int, content: str) -> Comment:
        comment = Comment(task_id=task_id, user_id=user_id, content=content)
        self.session.add(comment)
        await self.session.flush()
        await self.session.refresh(comment)
        return comment

    async def list_by_task(self, *, task_id: int) -> Sequence[Comment]:
        result = await self.session.execute(
            select(Comment)
            .where(Comment.task_id == task_id)
            .options(selectinload(Comment.attachments))
        )
        return result.scalars().all()

    async def get(self, *, comment_id: int, task_id: int) -> Comment | None:
        result = await self.session.execute(
            select(Comment).where(
                Comment.id == comment_id,
                Comment.task_id == task_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, *, comment_id: int) -> Comment | None:
        result = await self.session.execute(
            select(Comment).where(
                Comment.id == comment_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_by_id(self, *, comment_id: int, task_id: int) -> bool:
        result = await self.session.execute(
            delete(Comment).where(
                Comment.id == comment_id,
                Comment.task_id == task_id,
            )
        )
        await self.session.flush()
        return (result.rowcount or 0) > 0

    async def is_active_task(self, *, task_id: int) -> bool:
        result = await self.session.execute(
            select(1)
            .select_from(Task)
            .join(Project, Task.project_id == Project.id)
            .where(
                # Pastikan di task sama
                Task.id == task_id,
                # Task berada di project yang aktif
                Project.status == StatusProject.ACTIVE,
                # Task tidak dihapus
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
