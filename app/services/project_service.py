from app.db.models.project_member_model import ProjectMember, RoleProject
from app.db.models.project_model import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.base_service import GenericCRUDService
from app.utils.exceptions import ProjectNotFoundError


class ProjectService(GenericCRUDService[Project, ProjectCreate, ProjectUpdate]):
    model = Project
    audit_entity_name = "project"

    def _exception_not_found(self, **extra):
        """
        Membuat exception jika proyek tidak ditemukan.
        """
        return ProjectNotFoundError()

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
            raise ProjectNotFoundError()

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
            raise ProjectNotFoundError()

        member = await self.session.get(ProjectMember, (project.id, user_id))
        if not member:
            raise ProjectNotFoundError()

        if project.created_by == user_id:
            raise ValueError("Cannot remove the project creator from the project.")

        await self.session.delete(member)
        await self.session.commit()

    async def on_created(self, instance: Project, **kwargs) -> None:
        await self.add_member(
            instance.id, instance.created_by, RoleProject.OWNER, commit=False
        )
