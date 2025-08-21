from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.role_model import Role, UserRole
from app.schemas.user import UserDetail, UserProfile, UserProjectSummary, UserRead
from app.services.pegawai_service import PegawaiService
from app.utils import exceptions

if TYPE_CHECKING:
    from app.services.project_service import ProjectService
    from app.services.task_service import TaskService


class UserService:
    def __init__(
        self, session: AsyncSession, pegawai_service: PegawaiService
    ) -> None:
        self.session = session

        self.pegawai_service = pegawai_service

    async def get_user_role(self, user_id: int) -> UserRole | None:
        """Mendapatkan role pengguna berdasarkan ID.

        Args:
            user_id (int): ID pengguna yang ingin dicari.

        Returns:
            UserRole | None: Role pengguna yang ditemukan atau None jika tidak ada.
        """
        statement = select(UserRole).where(UserRole.user_id == user_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def assign_role_to_user(self, user_id: int, user: UserProfile):
        """Menetapkan peran kepada pengguna."""

        # dapatkan role user
        user_role = await self.get_user_role(user_id)

        # Jika user sudah memiliki role, kembalikan payload
        if user_role:
            return user_role

        # cast role jika employee_role admin maka dia akan manjadi adamin
        role = Role.ADMIN if user.employee_role == "admin" else Role.TEAM_MEMBER

        user_role = UserRole(user_id=user_id, role=role)
        self.session.add(user_role)
        await self.session.commit()
        return user_role

    async def get(self, user_id: int) -> UserRead | None:
        """Mendapatkan informasi pengguna berdasarkan ID.

        Args:
            user_id (int): ID pengguna yang ingin dicari.

        Raises:
            exceptions.UserNotFoundError: Jika pengguna tidak ditemukan.

        Returns:
            UserRead | None: Informasi pengguna yang ditemukan atau None jika tidak ada.
        """
        user_profile = await self.pegawai_service.get_user_info(user_id)

        if not user_profile:
            raise exceptions.UserNotFoundError

        user_role = await self.assign_role_to_user(user_id, user_profile)

        return UserRead(**user_profile.model_dump(), role=user_role.role)

    async def get_user_detail(
        self,
        user_id: int | None = None,
        user_data: UserRead | None = None,
        *,
        task_service: "TaskService",
        project_service: "ProjectService",
    ) -> UserDetail:
        """Mendapatkan detail pengguna.

        Args:
            task_service (TaskService): Layanan untuk mengelola tugas.
            project_service (ProjectService): Layanan untuk mengelola proyek.
            user_id (int | None, optional): ID pengguna. Defaults to None.
            user_data (UserRead | None, optional): Data pengguna. Defaults to None.
        """
        if user_id is None and user_data is None:
            raise exceptions.UserNotFoundError("Pengguna tidak ditemukan")

        if user_data is None:
            user_data = await self.get(user_id)  # type: ignore
            assert user_data is not None  # sudah di handle pada waktu get

        if user_id is None:
            user_id = user_data.id

        project_stats = await project_service.get_user_project_statistics(user_id)
        task_stats = await task_service.get_user_task_statistics(user_id)

        # Merge statistics
        statistics = UserProjectSummary(
            total_project=project_stats["total_project"],
            project_active=project_stats["project_active"],
            project_completed=project_stats["project_completed"],
            total_task=task_stats["total_task"],
            task_in_progress=task_stats["task_in_progress"],
            task_completed=task_stats["task_completed"],
            task_cancelled=task_stats["task_cancelled"],
        )

        projects = await project_service.get_user_project_participants(user_id)
        return UserDetail(
            **user_data.model_dump(),
            statistics=statistics,
            projects=projects,
        )
