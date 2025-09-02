from sqlalchemy.orm import selectinload

from app.db.models.milestone_model import Milestone
from app.db.models.project_member_model import RoleProject
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.milestone import MilestoneCreate
from app.schemas.user import User
from app.utils import exceptions


class MilestoneService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.repo = self.uow.milestone_repo

    async def list_milestones(
        self, *, user: User, project_id: int
    ) -> list[Milestone]:
        """Mendapatkan daftar milestone untuk proyek tertentu.

        Args:
            user (User): Pengguna yang meminta daftar milestone.
            project_id (int): ID proyek yang dimaksud.

        Raises:
            exceptions.ProjectNotFoundError: Jika proyek tidak ditemukan.
            exceptions.ForbiddenError: Jika pengguna tidak memiliki akses ke proyek.

        Returns:
            list[Milestone]: Daftar milestone untuk proyek yang dimaksud.
        """

        project_exists, is_member = await self.uow.project_repo.get_membership_flags(
            user_id=user.id, project_id=project_id
        )

        if not project_exists:
            raise exceptions.ProjectNotFoundError("Project tidak ditemukan")
        if not is_member:
            raise exceptions.ForbiddenError(
                "User tidak memiliki akses ke proyek ini"
            )

        return await self.repo.list_by_project(project_id=project_id)

    async def create_milestone(
        self, *, user: User, project_id: int, payload: MilestoneCreate
    ) -> Milestone:
        """Membuat milestone baru untuk proyek tertentu.

        Args:
            user (User): Pengguna yang membuat milestone.
            project_id (int): ID proyek yang dimaksud.
            payload (MilestoneCreate): Data untuk membuat milestone baru.

        Raises:
            exceptions.ProjectNotFoundError: Jika proyek tidak ditemukan.
            exceptions.ForbiddenError: Jika pengguna tidak memiliki akses ke proyek.

        Returns:
            Milestone: Milestone yang berhasil dibuat.
        """
        project_exists, is_owner = await self.uow.project_repo.get_membership_flags(
            user_id=user.id, project_id=project_id, required_role=RoleProject.OWNER
        )

        if not project_exists:
            raise exceptions.ProjectNotFoundError("Project tidak ditemukan")

        if not is_owner:
            raise exceptions.ForbiddenError(
                "Hanya owner proyek yang dapat membuat milestone"
            )

        milestone_data = payload.model_dump()
        milestone_data["project_id"] = project_id
        milestone_data["display_order"] = await self.repo.validate_display_order(
            project_id=project_id, display_order=None
        )
        return await self.repo.create(payload=milestone_data)

    async def delete_milestone(self, *, user: User, milestone_id: int) -> bool:
        """Menghapus milestone berdasarkan ID dan project.

        Args:
            user (User): Pengguna yang meminta penghapusan milestone.
            project_id (int): ID proyek yang dimaksud.
            milestone_id (int): ID milestone yang akan dihapus.

        Raises:
            exceptions.ProjectNotFoundError: Jika proyek tidak ditemukan.
            exceptions.ForbiddenError: Jika pengguna tidak memiliki akses ke proyek.

        Returns:
            bool: True jika milestone berhasil dihapus, False jika tidak ditemukan.
        """
        milestone = await self.repo.get_by_id(
            milestone_id=milestone_id, options=[selectinload(Milestone.tasks)]
        )
        if not milestone:
            raise exceptions.MilestoneNotFoundError("Milestone tidak ditemukan")

        is_owner = self.uow.project_repo.is_project_owner(
            project_id=milestone.project_id, user_id=user.id
        )

        if not is_owner:
            raise exceptions.ForbiddenError(
                "Hanya owner proyek yang dapat menghapus milestone"
            )

        if milestone.tasks:
            raise exceptions.ForbiddenError(
                "Tidak dapat menghapus milestone yang memiliki task"
            )

        result = await self.repo.delete(milestone=milestone)
        if not result:
            raise exceptions.MilestoneNotFoundError("Milestone tidak ditemukan")
        return result
