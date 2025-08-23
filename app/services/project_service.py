from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import case, exists, func, select
from sqlalchemy.orm import selectinload

from app.core.events.audit_events import ProjectCreatedEvent
from app.core.events.bus import enqueue_event
from app.db.models.project_member_model import ProjectMember, RoleProject
from app.db.models.project_model import Project, StatusProject
from app.db.models.role_model import Role
from app.db.models.task_model import ResourceType, StatusTask
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
from app.services.base_service import GenericCRUDService
from app.utils import exceptions

if TYPE_CHECKING:
    from app.services.task_service import TaskService
    from app.services.user_service import UserService


class ProjectService(GenericCRUDService[Project, ProjectCreate, ProjectUpdate]):
    model = Project
    audit_entity_name = "project"

    def _exception_not_found(self, **extra):
        """
        Membuat exception jika proyek tidak ditemukan.
        """
        return exceptions.ProjectNotFoundError()

    async def add_member(
        self,
        project_id: int,
        user_id: int,
        role: RoleProject,
        *,
        commit: bool = True,
    ):
        """
        Menambahkan anggota baru ke proyek.
        """
        member = await self.session.get(ProjectMember, (project_id, user_id))
        if member:
            raise exceptions.MemberAlreadyExistsError

        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        self.session.add(member)
        if commit:
            await self.session.commit()
            await self.session.refresh(member)
        return member

    async def remove_member(self, project_id: int, user_id: int):
        """
        Menghapus anggota dari proyek.
        """
        project = await self.get(project_id)
        if not project:
            raise exceptions.MemberNotFoundError

        member = await self.session.get(ProjectMember, (project.id, user_id))
        if not member:
            raise exceptions.MemberNotFoundError

        if project.created_by == user_id:
            raise exceptions.CannotRemoveMemberError(
                "Tidak dapat menhapus owner dari project"
            )

        await self.session.delete(member)
        await self.session.commit()

    async def get_member(self, project_id: int, member_id: int) -> ProjectMember:
        """
        Mendapatkan anggota proyek berdasarkan ID proyek dan ID anggota.
        """
        member = await self.session.get(ProjectMember, (project_id, member_id))
        if not member:
            raise exceptions.MemberNotFoundError
        return member

    async def change_role_member(
        self, project_id: int, user: User, role: RoleProject
    ):
        """
        Mengubah peran anggota proyek.
        """
        member = await self.get_member(project_id, user.id)

        if not member:
            raise exceptions.MemberNotFoundError

        # Jika role masih sama tidak di peroses
        if member.role == role:
            return member

        # get detail user
        if (
            user.role in (Role.ADMIN, Role.PROJECT_MANAGER)
            and role != RoleProject.OWNER
        ):
            raise exceptions.InvalidRoleAssignmentError(
                "admin dan manager hanya bisa sebagai owner."
            )

        if user.role == Role.TEAM_MEMBER and role == RoleProject.OWNER:
            raise exceptions.InvalidRoleAssignmentError(
                "team member tidak bisa sebagai owner project"
            )

        member.role = role
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def on_created(self, instance: Project, **kwargs) -> None:
        await self.add_member(
            instance.id, instance.created_by, RoleProject.OWNER, commit=False
        )

        # Entri Event
        enqueue_event(
            self.session,
            ProjectCreatedEvent(
                user_id=instance.created_by,
                project_id=instance.id,
                project_name=instance.title,
            ),
        )

    async def get_user_project_statistics(self, user_id: int):
        """
        Menghitung total proyek, proyek aktif, dan proyek selesai berdasarkan
        user_id.
        """
        stmt = (
            select(
                func.count().label("total_project"),
                func.sum(
                    case(
                        (Project.status == StatusProject.ACTIVE, 1),
                        else_=0,
                    )
                ).label("project_active"),
                func.sum(
                    case(
                        (Project.status == StatusProject.COMPLETED, 1),
                        else_=0,
                    )
                ).label("project_completed"),
            )
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(
                ProjectMember.user_id == user_id,
                # hanya proyek yang aktif atau selesai
                Project.status.in_([StatusProject.ACTIVE, StatusProject.COMPLETED]),
                # tidak termasuk proyek yang dihapus
                Project.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        row = result.first()

        if not row:
            return {
                "total_project": 0,
                "project_active": 0,
                "project_completed": 0,
            }

        return {
            "total_project": row.total_project or 0,
            "project_active": row.project_active or 0,
            "project_completed": row.project_completed or 0,
        }

    async def get_user_project_participants(
        self, user_id: int
    ) -> list[ProjectParticipant]:
        projects_stmt = (
            select(
                Project.id.label("project_id"),
                Project.title.label("project_name"),
                ProjectMember.role.label("user_role"),
            )
            .join(Project, Project.id == ProjectMember.project_id)
            .where(
                ProjectMember.user_id == user_id,
                # hanya proyek yang aktif atau selesai
                Project.status.in_([StatusProject.ACTIVE, StatusProject.COMPLETED]),
                # tidak termasuk proyek yang dihapus
                Project.deleted_at.is_(None),
            )
            .order_by(Project.id)
        )
        projects_res = await self.session.execute(projects_stmt)
        return [
            ProjectParticipant(
                project_id=row.project_id,
                project_name=row.project_name,
                user_role=row.user_role,
            )
            for row in projects_res
        ]

    async def get_user_projects(self, user: User, page: int = 1, per_page: int = 10):
        """Mengambil daftar proyek yang diikuti oleh pengguna.

        Args:
            user (User): Pengguna yang ingin mengambil proyek.
            page (int, optional): Halaman yang ingin diambil. Defaults to 1.
            per_page (int, optional): Jumlah proyek per halaman. Defaults to 10.
        """

        # PM/Admin: semua project yang diikuti (kecuali terhapus)
        # User biasa: hanya project yang diikuti dgn status ACTIVE/COMPLETED
        conditions: list[Any] = [
            exists(
                select(1)
                .select_from(ProjectMember)
                .where(
                    ProjectMember.project_id == Project.id,
                    ProjectMember.user_id == user.id,
                )
            ),
            Project.deleted_at.is_(None),
        ]

        # project yang diikuti dgn status ACTIVE/COMPLETED
        if user.role not in (Role.PROJECT_MANAGER, Role.ADMIN):
            conditions.append(
                Project.status.in_([StatusProject.ACTIVE, StatusProject.COMPLETED])
            )

        # Fetch project
        paginate = await self.pagination(
            page=page,
            per_page=per_page,
            custom_query=lambda q: q.where(*conditions).order_by(
                Project.start_date.desc()
            ),
        )

        # Cast ke ProjectPublicResponse
        # Ambil role user untuk proyek yang sedang dipaginasi (1 query)
        project_ids = [p.id for p in paginate["items"]]
        role_rows = await self.session.execute(
            select(ProjectMember.project_id, ProjectMember.role).where(
                ProjectMember.user_id == user.id,
                ProjectMember.project_id.in_(project_ids) if project_ids else False,  # type: ignore
            )
        )
        role_map = dict(role_rows.all())  # type: ignore

        # Cast ke ProjectPublicResponse
        items = []
        for item in paginate["items"]:
            items.append(
                ProjectPublicResponse(
                    id=item.id,
                    title=item.title,
                    description=item.description,
                    start_date=item.start_date,
                    end_date=item.end_date,
                    status=item.status,
                    created_by=item.created_by,
                    project_role=cast(RoleProject, role_map.get(item.id)),
                )
            )
        paginate.update({"items": items})
        return PaginationSchema[ProjectPublicResponse](**paginate)

    async def get_project_detail(
        self,
        user: User,
        project_id: int,
        task_service: "TaskService",
        user_service: "UserService",
    ):
        """Get project detail.
        Filter akses berdasarkan role:
        - PM/Admin: semua project yang tidak dihapus
        - Member: hanya project ACTIVE/COMPLETED dan user harus menjadi member

        Args:
            user (User): The user requesting the project details.
            project_id (int): The ID of the project to retrieve.
            task_service (TaskService): The task service instance.
            user_service (UserService): The user service instance.

        Raises:
            exceptions.ProjectNotFoundError: If the project is not found or the user
                does not have access.

        Returns:
            ProjectDetailResponse: The detailed project information.
        """

        conditions: list[Any] = [
            Project.id == project_id,  # ID proyek yang diminta
            Project.deleted_at.is_(None),  # Proyek yang tidak dihapus
            exists(
                select(1)
                .select_from(ProjectMember)
                .where(
                    ProjectMember.project_id == Project.id,
                    ProjectMember.user_id == user.id,
                )
            ),  # Memastikan user adalah anggota proyek
        ]

        if user.role not in (Role.PROJECT_MANAGER, Role.ADMIN):
            conditions.extend(
                [
                    Project.status.in_(
                        [StatusProject.ACTIVE, StatusProject.COMPLETED]
                    ),  # Hanya proyek yang aktif atau selesai
                ]
            )

        stmt = (
            select(Project).options(selectinload(Project.members)).where(*conditions)
        )
        res = await self.session.execute(stmt)
        project = res.scalars().first()

        # mengembalikan error jika projek tidak ditemukan atau
        # user tidak memiliki akses
        if not project:
            raise exceptions.ProjectNotFoundError

        # dapatkan task
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

        # get members
        members = []
        users = await user_service.list_user()
        for team_member in project.members:
            # dapatkan detail member
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
            else:
                print(
                    f"WARNING : User with ID {team_member.user_id} not found in ",
                    f"project {project_id}",
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

    async def get_project_by_owner(self, user_id: int, project_id: int):
        """Mendaptkan project bedasarkan owener

        Args:
            user_id (int): ID unique user
            project_id (int): ID unique Project

        Raises:
            exceptions.ProjectNotFoundError: Project tidak ditemukan

        """
        project = await self.fetch_one(
            filters={"id": project_id},
            condition=[
                exists(
                    select(1)
                    .select_from(ProjectMember)
                    .where(
                        ProjectMember.project_id == project_id,
                        ProjectMember.user_id == user_id,
                        ProjectMember.role == RoleProject.OWNER,
                    )
                ),
                Project.deleted_at.is_(None),
            ],
        )

        if not project:
            raise exceptions.ProjectNotFoundError
        return project
