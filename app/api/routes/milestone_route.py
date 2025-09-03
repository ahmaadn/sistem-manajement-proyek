from fastapi import APIRouter, Depends, status
from fastapi_utils.cbv import cbv

from app.api.dependencies.services import get_milestone_service
from app.api.dependencies.uow import get_uow
from app.api.dependencies.user import get_current_user
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.milestone import (
    MilestoneCreate,
    MilestoneResponse,
    MilestoneUpdate,
    SimpleMilestoneResponse,
)
from app.schemas.user import User
from app.services.milestone_service import MilestoneService
from app.utils.exceptions import AppErrorResponse

r = router = APIRouter(tags=["Milestone"])


@cbv(r)
class _Milestone:
    user: User = Depends(get_current_user)
    uow: UnitOfWork = Depends(get_uow)
    milestone_service: MilestoneService = Depends(get_milestone_service)

    @r.get(
        "/projects/{project_id}/milestone",
        response_model=list[MilestoneResponse],
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "Daftar tugas berhasil diambil",
                "model": list[MilestoneResponse],
            },
            status.HTTP_403_FORBIDDEN: {
                "description": "User tidak memiliki akses ke proyek ini",
                "model": AppErrorResponse,
            },
        },
    )
    async def get_milestones(self, project_id: int):
        """
        Mendapatkan daftar milestone untuk proyek tertentu.
        - Hanya user yang terdaftar sebagai anggota proyek yang dapat mengakses
            milestone.
        - Project yang di delete masih bisa lihat milestone
        - Admin dapat melihat semua task

        **Akses** : Anggota Proyek dan Admin
        """

        # pastikan user adalah member project
        return await self.milestone_service.list_milestones(
            project_id=project_id, user=self.user
        )

    @r.post(
        "/projects/{project_id}/milestone",
        response_model=SimpleMilestoneResponse,
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_403_FORBIDDEN: {
                "description": "Hanya pemilik proyek yang dapat membuat milestone",
                "model": AppErrorResponse,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Project tidak ditemukan",
                "model": AppErrorResponse,
            },
        },
    )
    async def create_milestone(self, project_id: int, payload: MilestoneCreate):
        """
        Membuat milestone baru.

        **Akses**: Owner Project
        """
        async with self.uow:
            milestone = await self.milestone_service.create_milestone(
                user=self.user, project_id=project_id, payload=payload
            )
            await self.uow.commit()
        return milestone

    @r.delete(
        "/milestones/{milestone_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={
            status.HTTP_404_NOT_FOUND: {
                "description": "Milestone tidak ditemukan",
                "model": AppErrorResponse,
            },
            status.HTTP_403_FORBIDDEN: {
                "description": "Hanya pemilik proyek yang dapat menghapus milestone",
                "model": AppErrorResponse,
            },
        },
    )
    async def delete_milestone(self, milestone_id: int):
        """
        Menghapus milestone berdasarkan ID.

        **Akses**: Owner Project
        """
        async with self.uow:
            await self.milestone_service.delete_milestone(
                user=self.user, milestone_id=milestone_id
            )
            await self.uow.commit()

    @r.put(
        "/milestones/{milestone_id}",
        status_code=status.HTTP_200_OK,
        response_model=SimpleMilestoneResponse,
        responses={
            status.HTTP_404_NOT_FOUND: {
                "description": "Milestone tidak ditemukan",
                "model": AppErrorResponse,
            },
            status.HTTP_403_FORBIDDEN: {
                "description": "Hanya pemilik proyek yang dapat menghapus milestone",
                "model": AppErrorResponse,
            },
        },
    )
    async def update_milestone(self, milestone_id: int, payload: MilestoneUpdate):
        """
        Menghapus milestone berdasarkan ID.

        **Akses**: Owner Project
        """
        async with self.uow:
            result = await self.milestone_service.update_milestone(
                user=self.user,
                milestone_id=milestone_id,
                payload=payload.model_dump(exclude_unset=True),
            )
            await self.uow.commit()
        return result
