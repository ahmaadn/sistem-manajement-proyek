from typing import TYPE_CHECKING

from app.core.domain.events.project import ProjectCreatedEvent
from app.core.domain.events.project_member import (
    ProjectMemberAddedEvent,
    ProjectMemberRemovedEvent,
    ProjectMemberUpdatedEvent,
)
from app.core.domain.policies.project_member import (
    ensure_actor_can_remove_member,
    ensure_can_assign_member_role,
    ensure_can_change_member_role,
)
from app.db.models.project_member_model import ProjectMember, RoleProject
from app.db.models.project_model import Project
from app.db.models.role_model import Role
from app.db.models.task_model import ResourceType, StatusTask
from app.db.repositories.project_repository import InterfaceProjectRepository
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.pagination import PaginationSchema
from app.schemas.project import (
    ProjectCreate,
    ProjectDetailResponse,
    ProjectMemberResponse,
    ProjectPublicResponse,
    ProjectStatsResponse,
    ProjectUpdate,
)
from app.schemas.user import ProjectParticipant, User
from app.utils import exceptions

if TYPE_CHECKING:
    from app.services.task_service import TaskService
    from app.services.user_service import UserService


class ProjectService:
    def __init__(self, uow: UnitOfWork, repo: InterfaceProjectRepository) -> None:
        self.uow = uow
        self.repo = repo

    async def create_project(
        self, project_create: ProjectCreate, user: User
    ) -> Project:
        result = await self.repo.create(
            project_create, extra_fields={"created_by": user.id}
        )
        # auto set owner
        await self.repo.add_member(result.id, user.id, RoleProject.OWNER)

        self.uow.add_event(
            ProjectCreatedEvent(
                user_id=user.id,
                project_id=result.id,
                project_title=result.title,
            )
        )
        return result

    async def delete_project(
        self,
        obj_id: int | None = None,
        obj: Project | None = None,
        soft_delete: bool = True,
    ):
        """
        Menghapus Project

        Args:
            obj_id (int | None, optional): ID proyek. Defaults to None.
            obj (Project | None, optional): Proyek yang akan dihapus.
                Defaults to None.
            soft_delete (bool, optional): Apakah akan dihapus secara lembut.
                Defaults to True.

        Raises:
            exceptions.ProjectNotFoundError: Jika proyek tidak ditemukan.
        """
        try:
            if soft_delete:
                await self.repo.soft_delete(obj_id, obj)
            else:
                await self.repo.hard_delete(obj_id, obj)
        except ValueError as e:
            raise exceptions.ProjectNotFoundError from e
        finally:
            # TODO: disini bisa ditambahkan event delete project
            # Event bisa berbentuk audit atau pemberitahuan email
            # untuk sementara tidak di implementasikan
            pass

    async def update_project(
        self, project: Project, project_update: ProjectUpdate
    ) -> Project:
        """Memperbarui proyek bedasarkan kepemilikan jika user owner dari project
        maka dia berhak mengedit project. akses yang diberikan hanya owener saja

        Args:
            project (Project): Proyek yang akan diperbarui.
            project_update (ProjectUpdate): Data pembaruan proyek.

        Returns:
            Project: Proyek yang diperbarui.
        """

        return await self.repo.update(project, project_update)

    async def add_member(
        self, project_id: int, user_id: int, role: RoleProject
    ) -> ProjectMember:
        """Menambahkan anggota baru ke proyek.

        Args:
            project_id (int): ID proyek.
            user_id (int): ID pengguna.
            role (RoleProject): Peran anggota dalam proyek.

        Raises:
            exceptions.MemberAlreadyExistsError: Jika anggota sudah ada.

        Returns:
            ProjectMember: Anggota proyek yang baru ditambahkan.
        """
        member = await self.repo.get_member(project_id, user_id)
        if member:
            raise exceptions.MemberAlreadyExistsError
        return await self.repo.add_member(project_id, user_id, role)

    async def remove_member(self, project_id: int, user_id: int) -> None:
        """Menghapus anggota dari proyek.

        Args:
            project_id (int): ID proyek.
            user_id (int): ID pengguna.

        Raises:
            exceptions.MemberNotFoundError: Jika anggota tidak ditemukan.
            exceptions.CannotRemoveMemberError: Jika anggota adalah pemilik proyek.
        """
        project = await self.repo.get_by_id(project_id)
        if not project:
            raise exceptions.ProjectNotFoundError

        if project.created_by == user_id:
            raise exceptions.CannotRemoveMemberError(
                "Tidak dapat menghapus owner dari proyek"
            )
        await self.repo.remove_member(project_id, user_id)

    async def get_member(self, project_id: int, member_id: int) -> ProjectMember:
        """Mengambil informasi anggota proyek.

        Args:
            project_id (int): ID proyek.
            member_id (int): ID anggota.

        Raises:
            exceptions.MemberNotFoundError: Jika anggota tidak ditemukan.

        Returns:
            ProjectMember: Informasi anggota proyek.
        """
        member = await self.repo.get_member(project_id, member_id)
        if not member:
            raise exceptions.MemberNotFoundError
        return member

    async def change_role_member(
        self, project_id: int, user: User, role: RoleProject
    ) -> ProjectMember:
        """Mengubah peran anggota proyek.

        Args:
            project_id (int): ID proyek.
            user (User): Pengguna yang perannya akan diubah.
            role (RoleProject): Peran baru untuk anggota.

        Raises:
            exceptions.MemberNotFoundError: Jika anggota tidak ditemukan.
            exceptions.InvalidRoleAssignmentError: Jika peran tidak valid.

        Returns:
            ProjectMember: Anggota proyek dengan peran yang diperbarui.
        """
        member = await self.repo.get_member(project_id, user.id)
        if not member:
            raise exceptions.MemberNotFoundError

        if member.role == role:
            return member

        if (
            user.role in (Role.ADMIN, Role.PROJECT_MANAGER)
        ) and role != RoleProject.OWNER:
            raise exceptions.InvalidRoleAssignmentError(
                "admin dan manager hanya bisa sebagai owner."
            )
        if (user.role == Role.TEAM_MEMBER) and role == RoleProject.OWNER:
            raise exceptions.InvalidRoleAssignmentError(
                "team member tidak bisa sebagai owner project"
            )

        return await self.repo.update_member_role(member, project_id, role)

    async def get_user_project_statistics(self, user_id: int) -> dict[str, int]:
        """Mengambil statistik proyek untuk pengguna.

        Args:
            user_id (int): ID pengguna.

        Returns:
            dict[str, int]: Statistik proyek untuk pengguna.
        """
        return await self.repo.get_user_project_statistics(user_id)

    async def get_user_project_participants(
        self, user_id: int
    ) -> list[ProjectParticipant]:
        """Mengambil daftar partisipan proyek untuk pengguna.

        Args:
            user_id (int): ID pengguna.

        Returns:
            list[ProjectParticipant]: Daftar partisipan proyek untuk pengguna.
        """
        rows = await self.repo.list_user_project_participants_rows(user_id)
        return [
            ProjectParticipant(
                project_id=row.project_id,
                project_name=row.project_name,
                user_role=row.user_role,
            )
            for row in rows
        ]

    async def get_user_projects(
        self, user: User, page: int = 1, per_page: int = 10
    ) -> PaginationSchema[ProjectPublicResponse]:
        """Mengambil daftar proyek untuk pengguna.

        Args:
            user (User): Pengguna yang proyeknya akan diambil.
            page (int, optional): Halaman yang akan diambil. Defaults to 1.
            per_page (int, optional): Jumlah proyek per halaman. Defaults to 10.

        Returns:
            PaginationSchema[ProjectPublicResponse]: Daftar proyek untuk pengguna.
        """
        is_admin_or_pm = user.role in (Role.PROJECT_MANAGER, Role.ADMIN)
        paginate = await self.repo.paginate_user_projects(
            user.id, is_admin_or_pm, page, per_page
        )

        project_ids = [p.id for p in paginate["items"]]
        role_map = await self.repo.get_roles_map_for_user_in_projects(
            user.id, project_ids
        )

        items: list[ProjectPublicResponse] = [
            ProjectPublicResponse(
                id=item.id,
                title=item.title,
                description=item.description,
                start_date=item.start_date,
                end_date=item.end_date,
                status=item.status,
                created_by=item.created_by,
                project_role=role_map[item.id],
            )
            for item in paginate["items"]
        ]
        paginate.update({"items": items})
        return PaginationSchema[ProjectPublicResponse](**paginate)

    async def get_project_detail(
        self,
        user: User,
        project_id: int,
        task_service: "TaskService",
        user_service: "UserService",
    ) -> ProjectDetailResponse:
        is_admin_or_pm = user.role in (Role.PROJECT_MANAGER, Role.ADMIN)
        project = await self.repo.get_project_detail_for_user(
            user.id, is_admin_or_pm, project_id
        )
        if not project:
            raise exceptions.ProjectNotFoundError

        tasks = await task_service.list(
            filters={"project_id": project_id, "resource_type": ResourceType.TASK},
        )
        milestones = await task_service.list(
            filters={
                "project_id": project_id,
                "resource_type": ResourceType.MILESTONE,
            },
        )

        total_tasks = len(tasks)
        total_completed_tasks = sum(
            1 for t in tasks if t.status == StatusTask.COMPLETED
        )
        total_milestones = len(milestones)
        task_milestones_completed = sum(
            1 for m in milestones if m.status == StatusTask.COMPLETED
        )

        members: list[ProjectMemberResponse] = []
        users = await user_service.list_user()
        for team_member in project.members:
            detail_member = next(
                (u for u in users if u.id == team_member.user_id), None
            )
            if detail_member:
                members.append(
                    ProjectMemberResponse(
                        user_id=detail_member.id,
                        name=detail_member.name,
                        email=detail_member.email,
                        project_role=team_member.role,
                    )
                )

        return ProjectDetailResponse(
            id=project.id,
            title=project.title,
            description=project.description,
            start_date=project.start_date,
            end_date=project.end_date,
            status=project.status,
            created_by=project.created_by,
            members=members,
            stats=ProjectStatsResponse(
                total_tasks=total_tasks,
                total_completed_tasks=total_completed_tasks,
                total_milestones=total_milestones,
                task_milestones_completed=task_milestones_completed,
            ),
        )

    async def get_project_by_owner(self, user_id: int, project_id: int) -> Project:
        """Mendapatkan project bedasarkan owner

        Args:
            user_id (int): ID pengguna
            project_id (int): ID proyek

        Raises:
            exceptions.ProjectNotFoundError: Jika proyek tidak ditemukan

        Returns:
            Project: Proyek yang ditemukan
        """
        project = await self.repo.get_project_by_owner(user_id, project_id)
        if not project:
            raise exceptions.ProjectNotFoundError
        return project

    async def add_member_by_actor(
        self, project_id: int, actor: User, member: User, role: RoleProject
    ) -> ProjectMember:
        """Menambahkan anggota ke proyek.

        Args:
            project_id (int): ID proyek
            actor (User): Pengguna yang melakukan aksi
            member (User): Anggota yang akan ditambahkan
            role (RoleProject): Peran anggota yang akan ditambahkan

        Raises:
            exceptions.ProjectNotFoundError: Jika proyek tidak ditemukan
            exceptions.MemberAlreadyExistsError: Jika anggota sudah terdaftar
            exceptions.InvalidRoleAssignmentError: Jika peran anggota tidak valid

        Returns:
            ProjectMember: Anggota proyek yang baru ditambahkan
        """

        # pastikan actor adalah owner project
        project = await self.repo.get_project_by_owner(actor.id, project_id)
        if not project:
            # samakan response dengan "tidak ditemukan/akses"
            raise exceptions.ProjectNotFoundError

        # validasi aturan role
        ensure_can_assign_member_role(member.role, role)

        # tidak boleh duplikat member
        if await self.repo.get_member(project_id, member.id):
            raise exceptions.MemberAlreadyExistsError

        created = await self.repo.add_member(project_id, member.id, role)

        self.uow.add_event(
            ProjectMemberAddedEvent(
                performed_by=actor.id,
                project_id=project.id,
                member_id=member.id,
                member_name=member.name,
                new_role=role,
            )
        )
        return created

    async def remove_member_by_actor(
        self, project_id: int, actor: User, member: User, target_user_id: int
    ) -> None:
        # pastikan actor owner (dan dapatkan owner id)
        project = await self.repo.get_project_by_owner(actor.id, project_id)
        if not project:
            raise exceptions.ProjectNotFoundError

        # validasi aturan penghapusan
        ensure_actor_can_remove_member(
            project_owner_id=project.created_by,
            actor_user_id=actor.id,
            target_user_id=target_user_id,
        )

        # pastikan member ada
        if not await self.repo.get_member(project_id, target_user_id):
            raise exceptions.MemberNotFoundError

        await self.repo.remove_member(project_id, target_user_id)

        self.uow.add_event(
            ProjectMemberRemovedEvent(
                performed_by=actor.id,
                project_id=project.id,
                member_id=target_user_id,
                member_name=member.name,
            )
        )

    async def change_role_member_by_actor(
        self, project_id: int, actor: User, member: User, new_role: RoleProject
    ) -> ProjectMember:
        # pastikan actor owner
        project = await self.repo.get_project_by_owner(actor.id, project_id)
        if not project:
            raise exceptions.ProjectNotFoundError

        current = await self.repo.get_member(project_id, member.id)
        if not current:
            raise exceptions.MemberNotFoundError

        ensure_can_change_member_role(
            member_system_role=member.role,
            target_user_id=member.id,
            project_owner_id=project.created_by,
            actor_user_id=actor.id,
            new_role=new_role,
            current_role=current.role,
        )

        updated = await self.repo.update_member_role(current, project_id, new_role)
        self.uow.add_event(
            ProjectMemberUpdatedEvent(
                performed_by=actor.id,
                project_id=project_id,
                member_id=member.id,
                member_name=member.name,
                after=new_role,
                before=current.role,
            )
        )

        return updated
