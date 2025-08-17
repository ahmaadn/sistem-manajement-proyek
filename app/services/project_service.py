from app.db.models.project_member_model import ProjectMember, RoleProject
from app.db.models.project_model import Project
from app.db.models.role_model import Role
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.user import UserRead
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
        self, project_id: int, user: UserRead, role: RoleProject
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
