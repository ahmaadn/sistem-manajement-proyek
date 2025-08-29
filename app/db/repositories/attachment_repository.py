from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.attachment_model import Attachment


@runtime_checkable
class InterfaceAttachmentRepository(Protocol):
    """Interface untuk operasi data Attachment."""

    async def get(self, attachment_id: int) -> Optional[Attachment]:
        """Ambil satu Attachment berdasarkan ID.

        Args:
            attachment_id: ID attachment.

        Returns:
            Attachment jika ditemukan, jika tidak None.
        """
        ...

    async def list(
        self, *, task_id: Optional[int] = None, comment_id: Optional[int] = None
    ) -> list[Attachment]:
        """Daftar Attachment dengan filter opsional.

        Args:
            task_id: ID task untuk memfilter (opsional).
            comment_id: ID komentar untuk memfilter (opsional).

        Returns:
            List Attachment terurut menurun berdasarkan ID.
        """
        ...

    async def count(
        self, *, task_id: Optional[int] = None, comment_id: Optional[int] = None
    ) -> int:
        """Hitung jumlah Attachment dengan filter opsional.

        Args:
            task_id: ID task untuk memfilter (opsional).
            comment_id: ID komentar untuk memfilter (opsional).

        Returns:
            Jumlah attachment yang cocok dengan filter.
        """
        ...

    async def create(
        self,
        *,
        user_id: int,
        task_id: int,
        comment_id: Optional[int],
        file_name: str,
        file_size: str,
        file_path: str = "",
    ) -> Attachment:
        """Buat Attachment baru.

        Catatan: Penyimpanan permanen bergantung pada commit transaksi
        yang dilakukan oleh pemanggil.

        Args:
            user_id: ID pengguna pengunggah.
            task_id: ID task terkait.
            comment_id: ID komentar terkait (opsional).
            file_name: Nama file.
            file_size: Ukuran file sebagai string.
            file_path: Lokasi penyimpanan file (opsional).

        Returns:
            Instance Attachment yang baru dibuat (ID tersedia setelah flush).
        """
        ...

    async def set_uploaded_result(
        self,
        *,
        attachment_id: int,
        file_path: str,
        file_size: str,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """Perbarui hasil unggah untuk sebuah Attachment dan lakukan commit.

        Args:
            attachment_id: ID attachment yang akan diperbarui.
            file_path: Lokasi file yang telah diunggah.
            file_size: Ukuran file final.
            session: Sesi alternatif; jika None gunakan sesi default repositori.

        Returns:
            None
        """
        ...

    async def delete(self, attachment_id: int) -> None:
        """Hapus Attachment berdasarkan ID.

        Args:
            attachment_id: ID attachment yang akan dihapus.

        Returns:
            None
        """
        ...


class AttachmentSQLAlchemyRepository:
    """Repository sederhana untuk Attachment dengan session per-method."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, attachment_id: int) -> Optional[Attachment]:
        return await self.session.get(Attachment, attachment_id)

    async def list(
        self, *, task_id: Optional[int] = None, comment_id: Optional[int] = None
    ) -> list[Attachment]:
        stmt: Select = select(Attachment)
        if task_id is not None:
            stmt = stmt.where(Attachment.task_id == task_id)
        if comment_id is not None:
            stmt = stmt.where(Attachment.comment_id == comment_id)
        stmt = stmt.order_by(Attachment.id.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def count(
        self, *, task_id: Optional[int] = None, comment_id: Optional[int] = None
    ) -> int:
        stmt = select(func.count(Attachment.id))
        if task_id is not None:
            stmt = stmt.where(Attachment.task_id == task_id)
        if comment_id is not None:
            stmt = stmt.where(Attachment.comment_id == comment_id)
        res = await self.session.execute(stmt)
        return int(res.scalar_one() or 0)

    async def create(
        self,
        *,
        user_id: int,
        task_id: int,
        comment_id: Optional[int],
        file_name: str,
        file_size: str,
        file_path: str = "",
    ) -> Attachment:
        att = Attachment(
            user_id=user_id,
            task_id=task_id,
            comment_id=comment_id,
            file_name=file_name,
            file_path=file_path,
            file_size=file_size,
        )
        self.session.add(att)
        await self.session.flush()
        return att

    async def set_uploaded_result(
        self,
        *,
        attachment_id: int,
        file_path: str,
        file_size: str,
        session: Optional[AsyncSession] = None,
    ) -> None:
        if session is None:
            session = self.session

        await session.execute(
            update(Attachment)
            .where(Attachment.id == attachment_id)
            .values(file_path=file_path, file_size=file_size)
        )
        await session.commit()

    async def delete(self, attachment_id: int) -> None:
        await self.session.execute(
            delete(Attachment).where(Attachment.id == attachment_id)
        )
        await self.session.flush()
