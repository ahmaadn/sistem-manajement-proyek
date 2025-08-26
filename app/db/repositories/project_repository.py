from abc import abstractmethod
from typing import Any, Sequence

from sqlalchemy import Row, case, exists, func, select
from sqlalchemy.orm import selectinload

from app.db.models.project_member_model import ProjectMember, RoleProject
from app.db.models.project_model import Project, StatusProject
from app.db.repositories.generic_repository import (
    InterfaceRepository,
    SQLAlchemyGenericRepository,
)
from app.schemas.project import ProjectCreate, ProjectUpdate


class InterfaceProjectRepository(
    InterfaceRepository[Project, ProjectCreate, ProjectUpdate]
):
    """Repository untuk entitas Project."""

    @abstractmethod
    async def get_member(
        self, project_id: int, member_id: int
    ) -> ProjectMember | None:
        """Mendapatkan anggota proyek berdasarkan ID proyek dan ID anggota."""

    @abstractmethod
    async def add_member(
        self, project_id: int, user_id: int, role: RoleProject
    ) -> ProjectMember:
        """Menambahkan anggota baru ke proyek."""

    @abstractmethod
    async def remove_member(self, project_id: int, user_id: int) -> None:
        """Menghapus anggota dari proyek."""

    @abstractmethod
    async def update_member_role(
        self, member: ProjectMember, project_id: int, role: RoleProject
    ) -> ProjectMember:
        """Memperbarui peran anggota proyek."""

    @abstractmethod
    async def get_project_by_owner(
        self, user_id: int, project_id: int
    ) -> Project | None:
        """Mendapatkan proyek milik pengguna tertentu."""

    @abstractmethod
    async def get_user_project_statistics(self, user_id: int) -> dict[str, int]:
        """Statistik proyek pengguna."""

    @abstractmethod
    async def list_user_project_participants_rows(
        self, user_id: int
    ) -> Sequence[Row[tuple[int, str, RoleProject]]]:
        """Daftar partisipasi proyek pengguna."""

    @abstractmethod
    async def paginate_user_projects(
        self,
        user_id: int,
        is_admin_or_pm: bool,
        page: int,
        per_page: int,
        is_admin: bool = False,
    ) -> dict[str, Any]:
        """Paginasi proyek pengguna."""

    @abstractmethod
    async def get_roles_map_for_user_in_projects(
        self, user_id: int, project_ids: list[int]
    ) -> dict[int, RoleProject]:
        """Peta peran pengguna di beberapa proyek."""

    @abstractmethod
    async def get_project_detail_for_user(
        self, user_id: int, is_admin_or_pm: bool, project_id: int
    ) -> Project | None:
        """Detail proyek untuk pengguna."""


class ProjectSQLAlchemyRepository(
    InterfaceProjectRepository,
    SQLAlchemyGenericRepository[Project, ProjectCreate, ProjectUpdate],
):
    """Implementasi SQLAlchemy untuk ProjectRepository."""

    model = Project

    async def get_member(
        self, project_id: int, member_id: int
    ) -> ProjectMember | None:
        """
        Mendapatkan anggota proyek berdasarkan ID proyek dan ID anggota.
        """
        return await self.session.get(ProjectMember, (project_id, member_id))

    async def add_member(
        self, project_id: int, user_id: int, role: RoleProject
    ) -> ProjectMember:
        """Menambahkan anggota baru ke proyek.

        Args:
            project_id (int): ID proyek.
            user_id (int): ID pengguna.
            role (RoleProject): Peran anggota dalam proyek.

        Returns:
            ProjectMember: Anggota proyek yang baru ditambahkan.
        """
        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        self.session.add(member)
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def remove_member(self, project_id: int, user_id: int) -> None:
        """Menghapus anggota dari proyek.

        Args:
            project_id (int): ID proyek.
            user_id (int): ID pengguna.
        """
        member = await self.get_member(project_id, user_id)
        if member:
            await self.session.delete(member)
            await self.session.flush()

    async def update_member_role(
        self, member: ProjectMember, project_id: int, role: RoleProject
    ) -> ProjectMember:
        """Memperbarui peran anggota proyek.

        Args:
            project_id (int): ID proyek.
            user_id (int): ID pengguna.
            role (RoleProject): Peran baru anggota dalam proyek.

        Returns:
            ProjectMember: Anggota proyek yang diperbarui.
        """
        member.role = role
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def get_project_by_owner(
        self, user_id: int, project_id: int
    ) -> Project | None:
        stmt = select(Project).where(
            Project.id == project_id,
            Project.deleted_at.is_(None),
            exists(
                select(1)
                .select_from(ProjectMember)
                .where(
                    ProjectMember.project_id == Project.id,
                    ProjectMember.user_id == user_id,
                    ProjectMember.role == RoleProject.OWNER,
                )
            ),
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_user_project_statistics(self, user_id: int) -> dict[str, int]:
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
                Project.status.in_([StatusProject.ACTIVE, StatusProject.COMPLETED]),
                Project.deleted_at.is_(None),
            )
        )
        res = await self.session.execute(stmt)
        row = res.first()
        if not row:
            return {"total_project": 0, "project_active": 0, "project_completed": 0}
        return {
            "total_project": row.total_project or 0,
            "project_active": row.project_active or 0,
            "project_completed": row.project_completed or 0,
        }

    async def list_user_project_participants_rows(
        self, user_id: int
    ) -> Sequence[Row[tuple[int, str, RoleProject]]]:
        stmt = (
            select(
                Project.id.label("project_id"),
                Project.title.label("project_name"),
                ProjectMember.role.label("user_role"),
            )
            .join(Project, Project.id == ProjectMember.project_id)
            .where(
                ProjectMember.user_id == user_id,
                Project.status.in_([StatusProject.ACTIVE, StatusProject.COMPLETED]),
                Project.deleted_at.is_(None),
            )
            .order_by(Project.id)
        )
        res = await self.session.execute(stmt)
        return res.all()

    async def paginate_user_projects(
        self,
        user_id: int,
        is_admin_or_pm: bool,
        page: int,
        per_page: int,
        is_admin: bool = False,
    ) -> dict[str, Any]:
        """
        - Admin: semua project (tanpa syarat member, semua status)
        - PM: hanya project yang ia ikuti (tanpa filter status)
        - User biasa: hanya project yang ia ikuti (status ACTIVE/COMPLETED)
        """

        conditions: list[Any] = [Project.deleted_at.is_(None)]

        # Scope membership
        if not is_admin:
            conditions.append(
                exists(
                    select(1)
                    .select_from(ProjectMember)
                    .where(
                        ProjectMember.project_id == Project.id,
                        ProjectMember.user_id == user_id,
                    )
                )
            )

        # Scope status
        if not (is_admin or is_admin_or_pm):
            conditions.append(
                Project.status.in_([StatusProject.ACTIVE, StatusProject.COMPLETED])
            )

        return await self.pagination(
            page=page,
            per_page=per_page,
            custom_query=lambda q: q.where(*conditions).order_by(
                Project.start_date.desc()
            ),
        )

    async def get_roles_map_for_user_in_projects(
        self, user_id: int, project_ids: list[int]
    ) -> dict[int, RoleProject]:
        if not project_ids:
            return {}
        res = await self.session.execute(
            select(ProjectMember.project_id, ProjectMember.role).where(
                ProjectMember.user_id == user_id,
                ProjectMember.project_id.in_(project_ids),
            )
        )
        rows = res.all()
        return {pid: role for pid, role in rows}  # noqa: C416

    async def get_project_detail_for_user(
        self, user_id: int, is_admin_or_pm: bool, project_id: int
    ) -> Project | None:
        conditions = [
            Project.id == project_id,
            Project.deleted_at.is_(None),
            exists(
                select(1)
                .select_from(ProjectMember)
                .where(
                    ProjectMember.project_id == Project.id,
                    ProjectMember.user_id == user_id,
                )
            ),
        ]
        if not is_admin_or_pm:
            conditions.append(
                Project.status.in_([StatusProject.ACTIVE, StatusProject.COMPLETED])
            )

        stmt = (
            select(Project).options(selectinload(Project.members)).where(*conditions)
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()
