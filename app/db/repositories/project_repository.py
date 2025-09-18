from abc import abstractmethod
from datetime import date
from typing import Any, Sequence

from sqlalchemy import Row, case, exists, func, select
from sqlalchemy.orm import selectinload

from app.db.models.project_member_model import ProjectMember, RoleProject
from app.db.models.project_model import Project, StatusProject
from app.db.models.role_model import Role
from app.db.models.task_model import Task
from app.db.repositories.generic_repository import (
    InterfaceRepository,
    SQLAlchemyGenericRepository,
)
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.utils.pagination import paginate


class InterfaceProjectRepository(
    InterfaceRepository[Project, ProjectCreate, ProjectUpdate]
):
    """Repository untuk entitas Project."""

    @abstractmethod
    async def get_member_by_ids(
        self, project_id: int, member_id: int
    ) -> ProjectMember | None:
        """Mendapatkan anggota proyek berdasarkan ID proyek dan ID anggota.

        Args:
            project_id (int): ID proyek.
            member_id (int): ID anggota.

        Returns:
            ProjectMember | None: Anggota proyek yang ditemukan atau None.
        """

    @abstractmethod
    async def add_project_member(
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

    @abstractmethod
    async def remove_project_member(self, project_id: int, user_id: int) -> None:
        """Menghapus anggota dari proyek.

        Args:
            project_id (int): ID proyek.
            user_id (int): ID pengguna.
        """

    @abstractmethod
    async def update_project_member_role(
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

    @abstractmethod
    async def get_user_project_by_role(
        self,
        user_id: int,
        project_id: int,
        project_role: RoleProject = RoleProject.OWNER,
    ) -> Project | None:
        """Mendapatkan proyek bedasarkan peran user di proyek.

        Args:
            user_id (int): ID user.
            project_id (int): ID proyek.
            project_role (RoleProject, optional): Peran project. Defaults to
                RoleProject.OWNER.

        Returns:
            Project | None: Proyek yang ditemukan atau None.
        """

    @abstractmethod
    async def get_project_statistics_for_user(self, user_id: int) -> dict[str, int]:
        """Statistik proyek untuk user tertentu.

        Args:
            user_id (int): ID user.

        Returns:
            dict[str, int]: Statistik proyek untuk user tertentu.
        """

    @abstractmethod
    async def get_overall_project_statistics(self) -> dict[str, int]:
        """Statistik keseluruhan proyek.

        Returns:
            dict[str, int]: Statistik keseluruhan proyek.
        """

    @abstractmethod
    async def list_user_project_participations(
        self, user_id: int
    ) -> Sequence[Row[tuple[int, str, RoleProject]]]:
        """Mendapatkan daftar partisipasi proyek user.

        Args:
            user_id (int): ID user.

        Returns:
            Sequence[Row[tuple[int, str, RoleProject]]]: Daftar partisipasi proyek
                user.
        """

    @abstractmethod
    async def pagination_projects(
        self,
        *,
        user_id: int,
        user_role: Role,
        page: int,
        per_page: int,
        status_filter: StatusProject | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> dict[str, Any]:
        """Mendapatkan daftar proyek dengan pagination dan filter.
        filter bedasarkan peran user:
            - Admin: semua project (tanpa syarat member, semua status)
            - PM: hanya project yang ia ikuti (tanpa filter status)
            - User biasa: hanya project yang ia ikuti (status ACTIVE/COMPLETED)

        Args:
            user_id (int): ID user.
            user_role (Role): Peran user.
            page (int): Halaman.
            per_page (int): Jumlah item per halaman.
            status_filter (StatusProject | None, optional): filter status project.
                Defaults to None.
            start_year (int | None, optional): Filter tahun awal proyek. Defaults
                to None.
            end_year (int | None, optional): Filter tahun terakhir. Defaults to None.

        Returns:
            dict[str, Any]: Daftar proyek dengan pagination dan filter.
        """

    @abstractmethod
    async def summarize_user_projects(
        self,
        *,
        user_id: int,
        not_admin: bool = True,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> dict[str, int]:
        """Ringkasan proyek untuk user tertentu bedasarkan range tahun.

        Args:
            user_id (int): ID user.
            not_admin (bool, optional): untuk memastikan user bukan admin. Defaults
                to True.
            start_year (int | None, optional): filter tahun awal. Defaults to None.
            end_year (int | None, optional): filter tahun terakhir. Defaults to None.

        Returns:
            dict[str, int]: Ringkasan proyek untuk user tertentu.
        """

    @abstractmethod
    async def get_user_scoped_project_detail(
        self,
        user_id: int,
        project_id: int,
        user_role: Role,
    ) -> Project | None:
        """Mendapatkan detail proyek yang diakses user bedasarkan perannya.

        Args:
            user_id (int): ID user.
            project_id (int): ID proyek.
            user_role (Role): Peran user.

        Returns:
            Project | None: Proyek yang ditemukan atau None.
        """

    @abstractmethod
    async def is_user_owner_of_project(self, project_id: int, user_id: int) -> bool:
        """
        Memeriksa apakah pengguna adalah pemilik proyek yang terkait dengan tugas.

        Args:
            project_id: ID proyek
            user_id: ID pengguna

        Returns:
            bool: True jika pengguna adalah pemilik proyek, False jika tidak
        """

    @abstractmethod
    async def ensure_member_in_project(
        self,
        *,
        user_id: int,
        project_id: int,
        required_role: RoleProject | None = None,
    ) -> bool:
        """
        Memastikan anggota ada di proyek. bisa custom role untuk memastikan juga
        member dengan role tertentu

        Args:
            user_id (int): ID pengguna.
            project_id (int): ID proyek.
            required_role (RoleProject | None): Peran proyek. Defaults to
                None.

        Returns:
            bool: True jika anggota ada di proyek, False jika tidak.
        """

    @abstractmethod
    async def get_project_membership_flags(
        self,
        *,
        user_id: int,
        project_id: int,
        required_role: RoleProject | None = None,
    ) -> tuple[bool, bool]:
        """
        Mengembalikan dua flag:
        - project_exists: proyek ada dan tidak terhapus
        - allowed: user adalah member (dan cocok role jika required_role diisi)

        Args:
            user_id (int): ID pengguna.
            project_id (int): ID proyek.
            required_role (RoleProject | None, optional): Peran yang diperlukan.
                Defaults to None.

        Returns:
            tuple[bool, bool]: (project_exists, allowed)
        """

    @abstractmethod
    async def list_project_members(
        self, project_id: int, role: RoleProject | None = None
    ) -> Sequence[ProjectMember]:
        """List anggota proyek, dengan opsi filter berdasarkan peran.

        Args:
            project_id (int): ID proyek.
            role (RoleProject | None, optional): role peran. Defaults to None.

        Returns:
            Sequence[ProjectMember]: Daftar anggota proyek.
        """

    @abstractmethod
    async def get_project_by_id(
        self,
        *,
        project_id: int,
        allow_deleted: bool = False,
        user_id: int | None = None,
        required_role: RoleProject | None = None,
    ) -> Project | None:
        """Mendapatkan proyek berdasarkan keanggotaan user.

        Args:
            project_id (int): ID proyek.
            allow_deleted (bool, optional): Mengizinkan pengambilan proyek yang
                dihapus. Defaults to False.
            user_id (int | None, optional): ID pengguna untuk memeriksa keanggotaan.
                Defaults to None.
            required_role (RoleProject | None, optional): Peran yang diperlukan
                dalam proyek. Defaults to None.

        Returns:
            Project | None: Proyek yang ditemukan atau None.
        """


class ProjectSQLAlchemyRepository(
    InterfaceProjectRepository,
    SQLAlchemyGenericRepository[Project, ProjectCreate, ProjectUpdate],
):
    """Implementasi SQLAlchemy untuk ProjectRepository."""

    model = Project

    async def get_member_by_ids(
        self, project_id: int, member_id: int
    ) -> ProjectMember | None:
        return await self.session.get(ProjectMember, (project_id, member_id))

    async def add_project_member(
        self, project_id: int, user_id: int, role: RoleProject
    ) -> ProjectMember:
        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        self.session.add(member)
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def remove_project_member(self, project_id: int, user_id: int) -> None:
        member = await self.get_member_by_ids(project_id, user_id)
        if member:
            await self.session.delete(member)
            await self.session.flush()

    async def update_project_member_role(
        self, member: ProjectMember, project_id: int, role: RoleProject
    ) -> ProjectMember:
        member.role = role
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def get_user_project_by_role(
        self,
        user_id: int,
        project_id: int,
        project_role: RoleProject = RoleProject.OWNER,
    ) -> Project | None:
        stmt = select(Project).where(
            Project.id == project_id,
            Project.deleted_at.is_(None),
            exists(
                select(1)
                .select_from(ProjectMember)
                .where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id,
                    ProjectMember.role == project_role,
                )
            ),
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_project_statistics_for_user(self, user_id: int) -> dict[str, int]:
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

    async def get_overall_project_statistics(self) -> dict[str, int]:
        stmt = select(
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
        ).where(
            Project.status.in_([StatusProject.ACTIVE, StatusProject.COMPLETED]),
            Project.deleted_at.is_(None),
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

    async def list_user_project_participations(
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

    async def pagination_projects(
        self,
        *,
        user_id: int,
        user_role: Role,
        page: int,
        per_page: int,
        status_filter: StatusProject | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> dict[str, Any]:
        conditions: list[Any] = [Project.deleted_at.is_(None)]

        # Scope membership
        if user_role != Role.ADMIN:
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
        if status_filter is not None:
            conditions.append(Project.status == status_filter)

        elif user_role == Role.TEAM_MEMBER:
            conditions.append(
                Project.status.in_([StatusProject.ACTIVE, StatusProject.COMPLETED])
            )

        # Filter tahun mulai
        if start_year is not None:
            sy = start_year or 1970
            conditions.append(Project.start_date >= date(sy, 1, 1))

        # Filter tahun akhir
        if end_year:
            conditions.append(Project.start_date <= date(end_year, 12, 31))

        # Subquery untuk menghitung total tugas dalam proyek
        total_tasks_sq = (
            select(func.count())
            .where(Task.project_id == Project.id)
            .correlate(Project)
            .scalar_subquery()
        )
        q = (
            select(Project, total_tasks_sq.label("total_tasks"))
            .where(*conditions)
            .order_by(Project.start_date.desc())
        )

        return await paginate(
            session=self.session, query=q, page=page, per_page=per_page, scalar=False
        )

    async def summarize_user_projects(
        self,
        *,
        user_id: int,
        not_admin: bool = True,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> dict[str, int]:
        conditions: list[Any] = [Project.deleted_at.is_(None)]

        if not_admin:
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

        # Filter range tahun berdasarkan start_date
        if start_year is not None or end_year is not None:
            sy = start_year or 1970
            ey = end_year or date.today().year
            conditions.append(Project.start_date >= date(sy, 1, 1))
            conditions.append(Project.start_date <= date(ey, 12, 31))

        stmt = select(
            func.count().label("total_project"),
            func.sum(
                case((Project.status == StatusProject.ACTIVE, 1), else_=0)
            ).label("project_active"),
            func.sum(
                case((Project.status == StatusProject.COMPLETED, 1), else_=0)
            ).label("project_completed"),
            func.sum(
                case((Project.status == StatusProject.TENDER, 1), else_=0)
            ).label("project_tender"),
            func.sum(
                case((Project.status == StatusProject.CANCEL, 1), else_=0)
            ).label("project_cancel"),
        ).where(*conditions)

        res = await self.session.execute(stmt)
        row = res.first()
        return {
            "total_project": (row.total_project if row else 0) or 0,
            "project_active": (row.project_active if row else 0) or 0,
            "project_completed": (row.project_completed if row else 0) or 0,
            "project_tender": (row.project_tender if row else 0) or 0,
            "project_cancel": (row.project_cancel if row else 0) or 0,
        }

    async def get_user_scoped_project_detail(
        self,
        user_id: int,
        project_id: int,
        user_role: Role,
    ) -> Project | None:
        conditions = [Project.id == project_id, Project.deleted_at.is_(None)]

        # semua project yang diikuti
        if user_role in (Role.PROJECT_MANAGER, Role.TEAM_MEMBER):
            conditions.append(
                exists(
                    select(1)
                    .select_from(ProjectMember)
                    .where(
                        ProjectMember.project_id == project_id,
                        ProjectMember.user_id == user_id,
                    )
                ),
            )

        # member biasa hanya boleh akses project ACTIVE/COMPLETED
        if user_role == Role.TEAM_MEMBER:
            conditions.append(
                Project.status.in_([StatusProject.ACTIVE, StatusProject.COMPLETED])
            )

        stmt = (
            select(Project).options(selectinload(Project.members)).where(*conditions)
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def is_user_owner_of_project(self, project_id: int, user_id: int) -> bool:
        stmt = select(
            exists().where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
                ProjectMember.role == RoleProject.OWNER,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def ensure_member_in_project(
        self,
        *,
        user_id: int,
        project_id: int,
        required_role: RoleProject | None = None,
    ) -> bool:
        conditions = [
            ProjectMember.project_id == Project.id,
            ProjectMember.user_id == user_id,
            Project.id == project_id,
            Project.deleted_at.is_(None),
        ]
        if required_role is not None:
            conditions.append(ProjectMember.role == required_role)

        stmt = select(exists().where(*conditions))
        return (await self.session.execute(stmt)).scalar_one()

    async def get_project_membership_flags(
        self,
        *,
        user_id: int,
        project_id: int,
        required_role: RoleProject | None = None,
    ) -> tuple[bool, bool]:
        role_condition = (
            [ProjectMember.role == required_role]
            if required_role is not None
            else []
        )

        stmt = select(
            exists(
                select(1).where(
                    Project.id == project_id,
                    Project.deleted_at.is_(None),
                )
            ).label("project_exists"),
            exists(
                select(1).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id,
                    *role_condition,
                )
            ).label("allowed"),
        )
        res = await self.session.execute(stmt)
        row = res.one()
        return bool(row.project_exists), bool(row.allowed)

    async def list_project_members(
        self, project_id: int, role: RoleProject | None = None
    ) -> Sequence[ProjectMember]:
        stmt = (
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.role.asc(), ProjectMember.user_id.asc())
        )
        if role is not None:
            stmt = stmt.where(ProjectMember.role == role)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def get_project_by_id(
        self,
        *,
        project_id: int,
        allow_deleted: bool = False,
        user_id: int | None = None,
        required_role: RoleProject | None = None,
    ) -> Project | None:
        q = select(Project).where(Project.id == project_id)
        condition = []
        if not allow_deleted:
            condition.append(Project.deleted_at.is_(None))

        if required_role is not None and user_id is not None:
            condition.append(
                exists(
                    select(1)
                    .select_from(ProjectMember)
                    .where(
                        ProjectMember.project_id == project_id,
                        ProjectMember.user_id == user_id,
                        ProjectMember.role == required_role,
                    )
                )
            )

        q.where(*condition)
        res = await self.session.execute(q)
        return res.scalars().first()
