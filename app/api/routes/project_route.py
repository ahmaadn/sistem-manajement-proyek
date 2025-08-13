from fastapi import APIRouter, Depends, status
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.authentication import get_current_user
from app.api.dependencies.project_manager import ProjectManager
from app.api.dependencies.sessions import get_async_session
from app.db.models.project_model import Project
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.user import UserInfo
from app.utils.exceptions import AppErrorResponse

r = router = APIRouter(tags=["Project"])


@cbv(r)
class _Project:
    session: AsyncSession = Depends(get_async_session)
    user: UserInfo = Depends(get_current_user)

    def __init__(self) -> None:
        self.project_manager = ProjectManager(self.session)

    @r.post(
        "/project",
        status_code=status.HTTP_201_CREATED,
        response_model=ProjectResponse,
        responses={
            status.HTTP_201_CREATED: {
                "description": "proyek berhasil dibuat",
                "model": ProjectResponse,
            }
        },
    )
    async def create_project(self, project: ProjectCreate):
        project_item = await self.project_manager.create(1, project)
        return self._map_project_to_response(project_item)

    @r.put(
        "/project/{project_id}",
        status_code=status.HTTP_200_OK,
        response_model=ProjectResponse,
        responses={
            status.HTTP_200_OK: {
                "description": "Proyek berhasil diperbarui",
                "model": ProjectResponse,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Proyek tidak ditemukan",
                "model": AppErrorResponse,
            },
        },
    )
    async def update_proyek(self, project_id: int, proyek: ProjectUpdate):
        """memperbarui proyek"""
        proyel_item = await self.project_manager.update(project_id, proyek)
        return self._map_project_to_response(proyel_item)

    @r.delete(
        "/project/{project_id}",
        status_code=status.HTTP_202_ACCEPTED,
        responses={
            status.HTTP_202_ACCEPTED: {
                "description": "Proyek berhasil dihapus",
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Proyek tidak ditemukan",
                "model": AppErrorResponse,
            },
        },
    )
    async def delete_proyek(self, project_id: int):
        """menghapus proyek"""

        await self.project_manager.delete(project_id)

    def _map_project_to_response(self, proyek: Project) -> ProjectResponse:
        """
        Mengonversi objek Proyek menjadi objek ProjectResponse.

        Args:
            proyek (Proyek): Objek proyek yang akan dikonversi.

        Returns:
            ProjectResponse: Objek response yang berisi data proyek.
        """

        return ProjectResponse(
            id=proyek.id,
            title=proyek.title,
            description=proyek.description,
            status=proyek.status,
            owner_id=proyek.created_by,
            start_date=proyek.start_date,
            end_date=proyek.end_date,
        )
