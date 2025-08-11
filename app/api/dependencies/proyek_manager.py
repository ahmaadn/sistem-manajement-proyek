import datetime

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.sessions import get_async_session
from app.db.models.proyek_model import Proyek
from app.schemas.proyek import ProyekCreate, ProyekUpdate
from app.utils.common import ErrorCode


class ProyekManager:
    def __init__(self, session: AsyncSession) -> None:
        if not isinstance(session, AsyncSession):
            raise ValueError("session harus bertipe AsyncSession")
        self.session = session

    async def get(
        self,
        proyek_id: int,
        *,
        allow_deleted: bool = False,
        return_none_if_not_found: bool = False,
    ) -> Proyek | None:
        """
        Ambil data proyek berdasarkan ID.
        Args:
            proyek_id (int): ID proyek
            allow_deleted (bool): Jika True, mengembalikan item yang sudah
                dihapus (soft delete)
            return_none_if_not_found (bool): Jika True, return None jika tidak
                ditemukan
        Returns:
            Proyek | None
        Raises:
            HTTPException: Jika item tidak ditemukan dan
                return_none_if_not_found=False
        """
        if not isinstance(proyek_id, int):
            raise ValueError("proyek_id harus bertipe int")

        proyek_item = await self.session.get(Proyek, proyek_id)

        if proyek_item is None:
            if return_none_if_not_found:
                return None
            self._log_not_found(proyek_id)
            raise self._exception_item_not_found()

        if proyek_item.is_deleted and not allow_deleted:
            if return_none_if_not_found:
                return None
            self._log_deleted(proyek_id)
            raise self._exception_item_not_found()

        return proyek_item

    async def create(self, user_id: int, data: ProyekCreate):
        """membuat proyek baru

        Args:
            user_id (int): user yang buat proyek
            data (ProyekCreate): data proyek yang akan dibuat

        Returns:
            Proyek: objek proyek yang telah dibuat
        """
        proyek_item = Proyek(
            nama=data.nama,
            deskripsi=data.deskripsi,
            status=data.status,
            created_by_id=user_id,
        )

        return await self._asave(proyek_item)

    async def update(self, proyek_id: int, data: ProyekUpdate):
        """
        Memperbarui data Proyek secara asynchronous dengan data yang diberikan.

        Args:
            proyek_id (int): ID Proyek yang akan diperbarui.
            data (ProyekUpdate): Objek berisi field yang akan diperbarui.

        Returns:
            Proyek: Instance Proyek yang telah diperbarui.

        Raises:
            HTTPException: Jika Proyek dengan ID tersebut tidak ditemukan
                atau sudah dihapus.
            ValueError: Jika data yang diberikan tidak valid.
        """

        proyek_item: Proyek = await self.get(proyek_id, allow_deleted=False)  # type: ignore

        # update data menggunakan perulangan karena field sama seperti model
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(proyek_item, key, value)

        return await self._asave(proyek_item)

    async def delete(self, proyek_id: int):
        proyek_item: Proyek = await self.get(proyek_id, allow_deleted=False)  # type: ignore
        proyek_item.deleted_at = datetime.datetime.now(datetime.timezone.utc)

        await self._asave(proyek_item)

    async def _asave(self, data: Proyek):
        """simpan proyek ke database menggunakan async

        Args:
            data (Proyek): objek proyek yang akan disimpan

        Returns:
            Proyek: objek proyek yang telah disimpan
        """
        self.session.add(data)
        await self.session.commit()
        await self.session.refresh(data)
        return data

    @staticmethod
    def _log_not_found(proyek_id: int) -> None:
        print(f"[ProyekManager] Proyek id={proyek_id} tidak ditemukan.")

    @staticmethod
    def _log_deleted(proyek_id: int) -> None:
        print(f"[ProyekManager] Proyek id={proyek_id} sudah dihapus (soft delete).")

    @staticmethod
    def _exception_item_not_found(**extra) -> HTTPException:
        """
        Membuat exception jika item tidak ditemukan.
        """
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": ErrorCode.PROYEK_NOT_FOUND,
                "message": "Item tidak ditemukan.",
                **extra,
            },
        )


async def get_proyek_manager(
    session: AsyncSession = Depends(get_async_session),
):
    """Depedensi untuk mendapatkan proyek manager."""
    yield ProyekManager(session=session)
