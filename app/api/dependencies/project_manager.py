import datetime

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.sessions import get_async_session
from app.db.models.project_model import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.utils.common import ErrorCode


class ProjectManager:
    def __init__(self, session: AsyncSession) -> None:
        if not isinstance(session, AsyncSession):
            raise ValueError("session harus bertipe AsyncSession")
        self.session = session

    async def get(
        self,
        project_id: int,
        *,
        allow_deleted: bool = False,
        return_none_if_not_found: bool = False,
    ) -> Project | None:
        """
        Ambil data proyek berdasarkan ID.

        Args:
            project_id (int): ID proyek
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
        if not isinstance(project_id, int):
            raise ValueError("project_id harus bertipe int")

        proyek_item = await self.session.get(Project, project_id)

        if proyek_item is None:
            if return_none_if_not_found:
                return None
            self._log_not_found(project_id)
            raise self._exception_item_not_found()

        if proyek_item.is_deleted and not allow_deleted:
            if return_none_if_not_found:
                return None
            self._log_deleted(project_id)
            raise self._exception_item_not_found()

        return proyek_item

    async def create(self, user_id: int, data: ProjectCreate):
        """membuat proyek baru

        Args:
            user_id (int): user yang buat proyek
            data (ProjectCreate): data proyek yang akan dibuat

        Returns:
            Project: objek proyek yang telah dibuat
        """
        proyek_item = Project(
            title=data.title,
            description=data.description,
            status=data.status,
            start_date=data.start_date,
            end_date=data.end_date,
            created_by=user_id,
        )

        return await self._asave(proyek_item)

    async def update(self, project_id: int, data: ProjectUpdate):
        """
        Memperbarui data Proyek secara asynchronous dengan data yang diberikan.

        Args:
            project_id (int): ID Proyek yang akan diperbarui.
            data (ProjectUpdate): Objek berisi field yang akan diperbarui.

        Returns:
            Project: Instance Proyek yang telah diperbarui.

        Raises:
            HTTPException: Jika Proyek dengan ID tersebut tidak ditemukan
                atau sudah dihapus.
            ValueError: Jika data yang diberikan tidak valid.
        """

        proyek_item: Project = await self.get(project_id, allow_deleted=False)  # type: ignore

        # update data menggunakan perulangan karena field sama seperti model
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(proyek_item, key, value)

        return await self._asave(proyek_item)

    async def delete(self, project_id: int):
        proyek_item: Project = await self.get(project_id, allow_deleted=False)  # type: ignore
        proyek_item.deleted_at = datetime.datetime.now(datetime.timezone.utc)

        await self._asave(proyek_item)

    async def _asave(self, data: Project):
        """simpan proyek ke database menggunakan async

        Args:
            data (Project): objek proyek yang akan disimpan

        Returns:
            Project: objek proyek yang telah disimpan
        """

        self.session.add(data)
        await self.session.commit()
        await self.session.refresh(data)
        return data

    @staticmethod
    def _log_not_found(project_id: int) -> None:
        print(f"[ProjectManager] Project id={project_id} tidak ditemukan.")

    @staticmethod
    def _log_deleted(project_id: int) -> None:
        print(
            f"[ProjectManager] Project id={project_id} sudah dihapus (soft delete)."
        )

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


async def get_project_manager(
    session: AsyncSession = Depends(get_async_session),
):
    """Depedensi untuk mendapatkan project manager."""
    yield ProjectManager(session=session)
