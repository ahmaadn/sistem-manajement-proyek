from typing import TYPE_CHECKING

from app.core.domain.events.user import UserRoleAssignedEvent
from app.core.policies.user_role import (
    ensure_admin_not_change_own_role,
    ensure_not_demote_last_admin,
    map_employee_role_to_app_role,
)
from app.db.models.role_model import Role, UserRole
from app.db.repositories.user_repository import InterfaceUserRepository
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.user import PegawaiInfo, ProjectSummary, User, UserDetail
from app.services.pegawai_service import PegawaiService
from app.utils import exceptions

if TYPE_CHECKING:
    from app.services.project_service import ProjectService
    from app.services.task_service import TaskService


class UserService:
    def __init__(
        self,
        *,
        pegawai_service: PegawaiService,
        uow: UnitOfWork,
        repo: InterfaceUserRepository,
    ) -> None:
        self.pegawai_service = pegawai_service
        self.uow = uow
        self.repo = repo

    async def get_user_role(self, user_id: int) -> UserRole | None:
        """Mendapatkan role pengguna berdasarkan ID.

        Args:
            user_id (int): ID pengguna yang ingin dicari.

        Returns:
            UserRole | None: Role pengguna yang ditemukan atau None jika tidak ada.
        """
        return await self.repo.get_user_role(user_id)

    async def assign_role_to_user(
        self, user_id: int, user: PegawaiInfo, actor_id: int | None = None
    ) -> UserRole:
        """Menetapkan peran kepada pengguna.

        Args:
            user_id (int): ID pengguna yang akan ditetapkan perannya.
            user (PegawaiInfo): Informasi pegawai yang akan digunakan untuk
                menetapkan peran.

        Returns:
            UserRole: Objek UserRole yang berhasil dibuat atau diperbarui.
        """
        # dapatkan role user
        user_role = await self.get_user_role(user_id)
        if user_role:
            return user_role

        role = map_employee_role_to_app_role(user.employee_role)
        user_role = await self.repo.create_user_role(user_id, role)

        # domain event
        if self.uow:
            self.uow.add_event(
                UserRoleAssignedEvent(
                    performed_by=actor_id,
                    assignee_id=user_id,
                    assignee_name=user.name,
                    assignee_role=getattr(role, "name", str(role)),
                )
            )
        return user_role

    async def get_user(self, user_id: int) -> User:
        """Mendapatkan informasi pengguna berdasarkan ID.

        Args:
            user_id (int): ID pengguna yang ingin dicari.

        Raises:
            exceptions.UserNotFoundError: Jika pengguna tidak ditemukan.

        Returns:
            UserRead | None: Informasi pengguna yang ditemukan atau None jika
                tidak ada.
        """
        user_profile = await self.pegawai_service.get_user_info(user_id)
        if not user_profile:
            raise exceptions.UserNotFoundError

        user_role = await self.assign_role_to_user(user_id, user_profile)
        return User(**user_profile.model_dump(), role=user_role.role)

    async def get_user_detail(
        self,
        user_id: int | None = None,
        user_data: User | None = None,
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
            user_data = await self.get_user(user_id)  # type: ignore

        if user_id is None:
            user_id = user_data.id

        project_stats = await project_service.get_user_project_statistics(user_id)
        task_stats = await task_service.get_user_task_statistics(user_id)

        statistics = ProjectSummary(
            total_project=project_stats["total_project"],
            project_active=project_stats["project_active"],
            project_completed=project_stats["project_completed"],
            total_task=task_stats["total_task"],
            task_in_progress=task_stats["task_in_progress"],
            task_completed=task_stats["task_completed"],
            task_cancelled=task_stats["task_cancelled"],
        )

        return UserDetail(
            **user_data.model_dump(),
            statistics=statistics,
        )

    async def get_detail_me(self, *, user: User) -> UserDetail:
        """Mendapatkan detail pengguna.

        Args:
            task_service (TaskService): Layanan untuk mengelola tugas.
            project_service (ProjectService): Layanan untuk mengelola proyek.
            user_id (int | None, optional): ID pengguna. Defaults to None.
            user_data (UserRead | None, optional): Data pengguna. Defaults to None.
        """

        if user.role == Role.ADMIN:
            project_stats = (
                await self.uow.project_repo.get_overall_project_statistics()
            )
            task_stats = await self.uow.task_repo.get_overall_task_statistics()
        else:
            project_stats = await self.uow.project_repo.get_user_project_statistics(
                user_id=user.id
            )
            task_stats = await self.uow.task_repo.get_user_task_statistics(user.id)

        statistics = ProjectSummary(
            total_project=project_stats["total_project"],
            project_active=project_stats["project_active"],
            project_completed=project_stats["project_completed"],
            total_task=task_stats["total_task"],
            task_in_progress=task_stats["task_in_progress"],
            task_completed=task_stats["task_completed"],
            task_cancelled=task_stats["task_cancelled"],
        )

        return UserDetail(
            **user.model_dump(),
            statistics=statistics,
        )

    async def list_user(self) -> list[User]:
        """
        Ambil semua pegawai dari provider eksternal, sinkronkan role jika belum ada
        (tanpa commit), lalu kembalikan daftar User dengan role.
        """
        pegawai_list = await self.pegawai_service.list_user()
        if not pegawai_list:
            return []

        user_ids = [p.id for p in pegawai_list]
        existing_roles = await self.repo.list_roles_for_users(user_ids)

        # siapkan insert untuk yang belum punya role
        to_create: list[tuple[int, Role]] = []
        for p in pegawai_list:
            if p.id not in existing_roles:
                role = map_employee_role_to_app_role(p.employee_role)
                to_create.append((p.id, role))
                existing_roles[p.id] = role

        if to_create:
            await self.repo.bulk_create_user_roles(to_create)
            # commit tetap di boundary router

        return [
            User(**p.model_dump(), role=existing_roles[p.id]) for p in pegawai_list
        ]

    async def change_user_role(
        self, *, actor: User, user_id: int, new_role: Role
    ) -> UserRole:
        """
        Ubah peran user. Jika belum memiliki role, akan dibuat.
        Guard:
            - Admin tidak boleh mengganti perannya sendiri (demote/promote).
            - Admin terakhir di sistem tidak boleh di-demote/diganti dari ADMIN.
        """
        # Validasi user eksis di sumber pegawai
        pegawai = await self.pegawai_service.get_user_info(user_id)
        if not pegawai:
            raise exceptions.UserNotFoundError

        # Guard 1: admin tidak boleh ganti perannya sendiri
        ensure_admin_not_change_own_role(
            actor_role=actor.role,
            actor_id=actor.id,
            target_user_id=user_id,
            new_role=new_role,
        )

        # Ambil role saat ini target
        current = await self.repo.get_user_role(user_id)

        # Admin tidak boleh mengganti perannya sendiri
        if current is not None:
            admin_count = await self.repo.count_users_with_role(Role.ADMIN)
            ensure_not_demote_last_admin(
                current_target_role=current.role,
                new_role=new_role,
                total_admins=admin_count,
            )

        # Cek peran saat ini target user
        current = await self.repo.get_user_role(user_id)

        # Jika target saat ini ADMIN dan akan diubah menjadi non-ADMIN,
        # pastikan bukan admin terakhir.
        if current is not None:
            admin_count = await self.repo.count_users_with_role(Role.ADMIN)
            ensure_not_demote_last_admin(
                current_target_role=current.role,
                new_role=new_role,
                total_admins=admin_count,
            )

        ur = await self.repo.change_user_role(user_id, new_role)

        # Angkat domain event (publish post-commit oleh UoW)
        self.uow.add_event(
            UserRoleAssignedEvent(
                performed_by=actor.id,
                assignee_id=user_id,
                assignee_name=pegawai.name,
                assignee_role=getattr(new_role, "name", str(new_role)),
            )
        )
        return ur
