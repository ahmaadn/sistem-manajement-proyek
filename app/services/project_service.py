from sqlalchemy import case, func, select

from app.db.models.project_member_model import ProjectMember, RoleProject
from app.db.models.project_model import Project, StatusProject
from app.db.models.role_model import Role
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.user import ProjectParticipant, User
from app.services.base_service import GenericCRUDService
from app.utils import exceptions


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
        if user.role in (Role.ADMIN, Role.MANAGER) and role != RoleProject.OWNER:
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
