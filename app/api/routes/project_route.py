from datetime import datetime
from types import NoneType

from fastapi import APIRouter, Depends, Query, status
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.services import get_project_service, get_task_service
from app.api.dependencies.sessions import get_async_session
from app.api.dependencies.uow import get_uow
from app.api.dependencies.user import (
    get_current_user,
    get_user_pm,
    get_user_service,
    permission_required,
)
from app.db.models.project_model import StatusProject
from app.db.models.role_model import Role
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.project import (
    ProjectCreate,
    ProjectDetail,
    ProjectListPage,
    ProjectRead,
    ProjectReport,
    ProjectUpdate,
)
from app.schemas.user import User
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.utils import exceptions

r = router = APIRouter(tags=["Projects"])


@cbv(r)
class _Project:
    session: AsyncSession = Depends(get_async_session)
    user: User = Depends(get_current_user)
    uow: UnitOfWork = Depends(get_uow)
    project_service: ProjectService = Depends(get_project_service)

    @r.get(
        "/projects",
        status_code=status.HTTP_200_OK,
        response_model=ProjectListPage,
    )
    async def list_projects(
        self,
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=10, ge=1, le=100),
        status_project: StatusProject | None = Query(default=None),
        start_year: int | None = Query(
            default=None, ge=1970, description="Tahun mulai (mis. 2010)"
        ),
        end_year: int | None = Query(
            default=None,
            ge=1970,
            description=f"Tahun akhir (<= {datetime.now().year})",
        ),
    ):
        """
        Mengambil daftar project yang terkait. **PM/Admin**: semua project yang
        diikuti (kecuali terhapus), ***User***: hanya project yang diikuti dgn
        status ACTIVE/COMPLETED

        **Akses** : User, Project Manajer, Admin
        """

        return await self.project_service.list_user_projects(
            user=self.user,
            page=page,
            per_page=per_page,
            status_project=status_project,
            start_year=start_year,
            end_year=end_year,
        )

    @r.get(
        "/projects/{project_id}",
        response_model=ProjectDetail,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "Proyek ditemukan",
                "model": ProjectDetail,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Proyek tidak ditemukan",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def get_detail_project(
        self,
        project_id: int,
        task_service: TaskService = Depends(get_task_service),
        user_service: UserService = Depends(get_user_service),
    ):
        """
        Mengambil detail project, bedasarkan project yang di ikuti

        **Akses** : User, Project Manajer, Admin
        """

        # terpaksa menggunakan uow karena dimungkinkan beberaapa pegawai belum
        # mendapatkan role atau ada pegawai yang dinonaktifkan
        async with self.uow:
            project = await self.project_service.get_project_detail(
                self.user, project_id, task_service, user_service
            )

            await self.uow.commit()

        return project

    @r.put(
        "/projects/{project_id}",
        status_code=status.HTTP_200_OK,
        response_model=ProjectRead,
        responses={
            status.HTTP_200_OK: {
                "description": "Proyek berhasil diperbarui",
                "model": ProjectRead,
            },
            status.HTTP_401_UNAUTHORIZED: {
                "description": "User tidak memiliki akses.",
                "model": exceptions.AppErrorResponse,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Proyek tidak ditemukan",
                "model": exceptions.AppErrorResponse,
            },
        },
        dependencies=[
            Depends(permission_required([Role.PROJECT_MANAGER, Role.ADMIN]))
        ],
    )
    async def update_project(
        self,
        project_id: int,
        payload: ProjectUpdate,
    ):
        """
        Memperbarui project

        **Akses** : Project Manajer (Owner), Admin (Owner)

        """
        async with self.uow:
            project = await self.project_service.get_project_by_owner(
                self.user.id, project_id
            )
            await self.project_service.update_project(project, payload)
            await self.uow.commit()

        return project

    @r.delete(
        "/projects/{project_id}",
        status_code=status.HTTP_202_ACCEPTED,
        responses={
            status.HTTP_202_ACCEPTED: {
                "description": "Proyek berhasil dihapus",
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Proyek tidak ditemukan",
                "model": exceptions.AppErrorResponse,
            },
        },
        dependencies=[
            Depends(permission_required([Role.PROJECT_MANAGER, Role.ADMIN]))
        ],
    )
    async def delete_proyek(self, project_id: int) -> NoneType:
        """
        Menghapus Proyek

        **Akses** :  Project Manajer (Owner), Admin (Owner)
        """
        async with self.uow:
            project = await self.project_service.get_project_by_owner(
                self.user.id, project_id
            )
            await self.project_service.delete_project(obj=project, soft_delete=True)
            await self.uow.commit()

    @r.post(
        "/projects",
        status_code=status.HTTP_201_CREATED,
        response_model=ProjectRead,
        responses={
            status.HTTP_201_CREATED: {
                "description": "proyek berhasil dibuat",
                "model": ProjectRead,
            }
        },
        dependencies=[Depends(get_user_pm)],
    )
    async def create_project(self, project: ProjectCreate):
        """
        Membuat proyek baru

        **Akses** : Project Manajer
        """
        async with self.uow:
            result = await self.project_service.create_project(project, self.user)
            await self.uow.commit()

        return result

    @r.get(
        "/projects/{project_id}/report",
        response_model=ProjectReport,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "Laporan proyek",
                "model": ProjectReport,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Proyek tidak ditemukan",
                "model": exceptions.AppErrorResponse,
            },
            status.HTTP_403_FORBIDDEN: {
                "description": "Tidak punya akses",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def get_project_report(
        self,
        project_id: int,
        week_start: datetime | None = Query(
            default=None,
            description=(
                "Tanggal mulai minggu (YYYY-MM-DD). Jika kosong, gunakan 6 hari ke "
                "belakang."
            ),
        ),
    ):
        """
        Laporan ringkas proyek:
        - project_summary (total, complete, not_complete)
        - assignee stats
        - priority distribution
        - weakly_report (7 hari)

        **Akses** : Project Manajer (Owner), Admin
        """
        return await self.project_service.get_project_report(
            user=self.user,
            project_id=project_id,
            week_start=week_start.date() if week_start else None,
        )
