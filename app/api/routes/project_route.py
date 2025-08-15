from types import NoneType

from fastapi import APIRouter, Depends, status
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.project import get_project_service
from app.api.dependencies.sessions import get_async_session
from app.api.dependencies.user import get_current_user
from app.db.models.project_model import Project
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.user import UserProfile
from app.services.project_service import ProjectService
from app.utils.exceptions import AppErrorResponse

r = router = APIRouter(tags=["Project"])


@cbv(r)
class _Project:
    session: AsyncSession = Depends(get_async_session)
    user: UserProfile = Depends(get_current_user)
    project_service: ProjectService = Depends(get_project_service)

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
        """membuat proyek baru"""

        project_item = await self.project_service.create(
            project, extra_fields={"created_by": self.user.id}
        )
        return self._cast_project_to_response(project_item)

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
        proyek_item = await self.project_service.update(project_id, proyek)
        return self._cast_project_to_response(proyek_item)

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
    async def delete_proyek(self, project_id: int) -> NoneType:
        """menghapus proyek"""
        await self.project_service.soft_delete(project_id)

    def _cast_project_to_response(self, proyek: Project) -> ProjectResponse:
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
