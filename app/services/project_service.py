import asyncio
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Sequence

from sqlalchemy.orm import selectinload
from starlette_context import context

from app.core.domain.events.project import (
    ProjectCreatedEvent,
    ProjectStatusChangedEvent,
    ProjectUpdatedEvent,
)
from app.core.domain.events.project_member import (
    ProjectMemberAddedEvent,
    ProjectMemberRemovedEvent,
    ProjectMemberUpdatedEvent,
)
from app.core.policies.project_member import (
    ensure_actor_can_remove_member,
    ensure_can_assign_member_role,
    ensure_can_change_member_role,
)
from app.core.policies.query_policies import (
    normalize_year_range,
    validate_status_by_role,
)
from app.db.models.project_member_model import ProjectMember, RoleProject
from app.db.models.project_model import Project, StatusProject
from app.db.models.role_model import Role
from app.db.models.task_model import PriorityLevel, StatusTask, Task
from app.db.repositories.project_repository import InterfaceProjectRepository
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.project import (
    ProjectCreate,
    ProjectDetail,
    ProjectListPage,
    ProjectMemberRead,
    ProjectPaginationItem,
    ProjectReport,
    ProjectReportAssignee,
    ProjectReportPriority,
    ProjectReportSummary,
    ProjectReportWeekItem,
    ProjectStats,
    ProjectSummary,
    ProjectUpdate,
    TaskEstimationItem,
)
from app.schemas.user import ProjectParticipation, User
from app.services.pegawai_service import PegawaiService
from app.utils import exceptions

logger = logging.getLogger(__name__)


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

        owner, admin_recipients = await asyncio.gather(
            self.repo.add_project_member(result.id, user.id, RoleProject.OWNER),
            self.uow.user_repository.get_admin_user_ids(),
        )

        self.uow.add_event(
            ProjectCreatedEvent(
                performed_by=user.id,
                project_id=result.id,
                project_title=result.title,
                user=user,
                admin_recipients=admin_recipients,
                metadata={
                    "context": context.data.copy(),
                },
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
        self, project_id: int, user: User, project_update: ProjectUpdate
    ) -> Project:
        """Memperbarui proyek bedasarkan kepemilikan jika user owner dari project
        maka dia berhak mengedit project. akses yang diberikan hanya owener saja

        Args:
            project (Project): Proyek yang akan diperbarui.
            project_update (ProjectUpdate): Data pembaruan proyek.

        Returns:
            Project: Proyek yang diperbarui.
        """
        project = await self.get_project_by_owner(user.id, project_id)

        await self._on_update_project(
            user=user, project=project, payload_update=project_update
        )

        await self.repo.update(project, project_update)

        return project

    async def _on_update_project(
        self, user: User, project: Project, payload_update: ProjectUpdate
    ):
        """Mengirimkan notifikasi perubahan kepada member, adamin, atau project member

        Args:
            user (User): User yang melakukan emit notifikasi
            project (Project): Object project yang sebelum di ubah
            payload_update (ProjectUpdate): perubahan data
        """

        # Kontributor hanya dapat notifikasi jika status project sebelumnya adalah
        # TENDER, ACTIVE atau COMPLETED dan status project setelahnya adalah ACTIVE
        # atau COMPLETED
        send_contributor = False
        if project.status in (
            StatusProject.ACTIVE,
            StatusProject.COMPLETED,
            StatusProject.TENDER,
        ) and payload_update.status in (
            StatusProject.ACTIVE,
            StatusProject.COMPLETED,
        ):
            send_contributor = True

        # Mendapatkan admin untuk mendapatkan notifikasi juga walaupun dia bukan
        # member
        admins, members = await asyncio.gather(
            *[
                self.uow.user_repository.get_admin_user_ids(),
                self.uow.project_repo.list_project_members(
                    project_id=project.id,
                    role=None if send_contributor else RoleProject.OWNER,
                ),
            ]
        )

        # menggunakan set agar tidak ada double notifikasi
        recipients = {m.user_id for m in members}
        recipients.update(admins)

        logger.debug("Project update recipients: %s", recipients)

        # Tambah event update
        if payload_update.title and project.title != payload_update.title:
            self.uow.add_event(
                ProjectUpdatedEvent(
                    performed_by=project.created_by,
                    project_id=project.id,
                    project_title=project.title,
                )
            )

        # Tambah event status change
        if payload_update.status and project.status != payload_update.status:
            self.uow.add_event(
                ProjectStatusChangedEvent(
                    performed_by=project.created_by,
                    project_title=project.title,
                    project_id=project.id,
                    before=project.status,
                    after=payload_update.status,
                    user=user,
                    recipients=list(recipients),
                )
            )

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
        member = await self.repo.get_member_by_ids(project_id, user_id)
        if member:
            raise exceptions.MemberAlreadyExistsError
        return await self.repo.add_project_member(project_id, user_id, role)

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
        await self.repo.remove_project_member(project_id, user_id)

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
        member = await self.repo.get_member_by_ids(project_id, member_id)
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
        member = await self.repo.get_member_by_ids(project_id, user.id)
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

        return await self.repo.update_project_member_role(member, project_id, role)

    async def get_user_project_statistics(self, user_id: int) -> dict[str, int]:
        """Mengambil statistik proyek untuk pengguna.

        Args:
            user_id (int): ID pengguna.

        Returns:
            dict[str, int]: Statistik proyek untuk pengguna.
        """
        return await self.repo.get_project_statistics_for_user(user_id)

    async def get_user_project_participants(
        self, user_id: int
    ) -> list[ProjectParticipation]:
        """Mengambil daftar partisipan proyek untuk pengguna.

        Args:
            user_id (int): ID pengguna.

        Returns:
            list[ProjectParticipant]: Daftar partisipan proyek untuk pengguna.
        """
        rows = await self.repo.list_user_project_participations(user_id)
        return [
            ProjectParticipation(
                project_id=row.project_id,
                project_name=row.project_name,
                user_role=row.user_role,
            )
            for row in rows
        ]

    async def list_projects(
        self,
        *,
        user: User,
        page: int = 1,
        per_page: int = 10,
        status_project: StatusProject | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> ProjectListPage:
        """Mengambil daftar proyek untuk pengguna.

        Args:
            user (User): Pengguna yang proyeknya akan diambil.
            page (int, optional): Halaman yang akan diambil. Defaults to 1.
            per_page (int, optional): Jumlah proyek per halaman. Defaults to 10.
            status_project (StatusProject | None, optional): Filter status proyek.
            start_year (int | None, optional): Tahun mulai untuk filter. Defaults
                to None.
            end_year (int | None, optional): Tahun akhir untuk filter. Defaults
                to None.

        Returns:
            ProjectListPage: Daftar proyek untuk pengguna.
        """
        validate_status_by_role(user=user, status_project=status_project)
        normalize_year_range(start_year=start_year, end_year=end_year)

        # Jalankan query paginasi dan ringkasan secara bersamaan
        paginate, summary = await asyncio.gather(
            self.repo.pagination_projects(
                user_id=user.id,
                user_role=user.role,
                page=page,
                per_page=per_page,
                status_filter=status_project,
                start_year=start_year,
                end_year=end_year,
            ),
            self.summarize_user_projects(
                user=user, start_year=start_year, end_year=end_year
            ),
        )

        # Konversi item ke ProjectListItem
        items = [
            ProjectPaginationItem(
                id=item[0].id,
                title=item[0].title,
                description=item[0].description,
                start_date=item[0].start_date,
                end_date=item[0].end_date,
                status=item[0].status,
                created_by=item[0].created_by,
                total_tasks=item[1] or 0,  # Total tasks
            )
            for item in paginate.get("items", [])
        ]

        paginate.update({"items": items})
        return ProjectListPage(**paginate, summary=summary)

    async def summarize_user_projects(
        self,
        *,
        user: User,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> ProjectSummary:
        """Menyediakan ringkasan proyek untuk pengguna.

        Args:
            user (User): Pengguna yang proyeknya akan diringkas.
            start_year (int | None, optional): Tahun awal untuk filter. Defaults to
                None.
            end_year (int | None, optional): Tahun akhir untuk filter. Defaults to
                None.

        Returns:
            ProjectSummary: Ringkasan proyek untuk pengguna.
        """
        raw = await self.repo.summarize_user_projects(
            user_id=user.id,
            not_admin=(user.role != Role.ADMIN),
            start_year=start_year,
            end_year=end_year,
        )
        is_admin_or_pm = user.role in (Role.PROJECT_MANAGER, Role.ADMIN)
        total_project = (
            raw.get("total_project", 0)
            if is_admin_or_pm
            else sum([raw.get("project_active", 0), raw.get("project_completed", 0)])
        )

        return ProjectSummary(
            total_project=total_project,
            project_active=raw.get("project_active", 0),
            project_completed=raw.get("project_completed", 0),
            project_tender=(raw.get("project_tender", 0) if is_admin_or_pm else 0),
            project_cancel=(raw.get("project_cancel", 0) if is_admin_or_pm else 0),
        )

    async def get_project_members(
        self, members: list[ProjectMember]
    ) -> list[ProjectMemberRead]:
        """
        Mengambil detail anggota proyek.

        Args:
            members (list[ProjectMember]): Daftar anggota proyek.

        Returns:
            list[ProjectMemberRead]: Daftar detail anggota proyek.
        """

        pegawai_service = PegawaiService()
        users = await pegawai_service.list_user_by_ids([m.user_id for m in members])

        # TODO: missing user belum di handle. mising user bisa terjadi jika user
        # tidak lagi aktif atau terhapus. handle bisa dilakukan dengan menghapus
        # anggota proyek yang tidak ditemukan. untuk saat ini hanya diabaikan saja

        mapped_members = []
        for user in users:
            if not user:
                continue

            project_role = RoleProject.CONTRIBUTOR
            for m in members:
                if m.user_id == user.id:
                    project_role = m.role
                    break

            # jika user tidak ditemukan, abaikan anggota proyek ini
            mapped_members.append(
                ProjectMemberRead(
                    user_id=user.id,
                    name=user.name,
                    email=user.email,
                    project_role=project_role,
                    profile_url=user.profile_url,
                )
            )

        return mapped_members

    async def get_project_detail(
        self,
        user: User,
        project_id: int,
    ) -> ProjectDetail:
        project = await self.repo.get_user_scoped_project_detail(
            user_id=user.id,
            project_id=project_id,
            user_role=user.role,
        )

        if not project:
            raise exceptions.ProjectNotFoundError

        # Jalankan query task dan member secara bersamaan
        tasks, members = await asyncio.gather(
            self.uow.task_repo.list_by_filters(filters={"project_id": project.id}),
            self.get_project_members(project.members),
        )

        return ProjectDetail(
            id=project.id,
            title=project.title,
            description=project.description,
            start_date=project.start_date,
            end_date=project.end_date,
            status=project.status,
            created_by=project.created_by,
            members=members,
            stats=ProjectStats(
                total_tasks=len(tasks),
                total_completed_tasks=sum(
                    1 for t in tasks if t.status == StatusTask.COMPLETED
                ),
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
        project = await self.repo.get_owned_project_by_user(user_id, project_id)
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

        project = await self.repo.get_project_by_id(
            project_id=project_id,
            user_id=actor.id,
            required_role=None if actor.role == Role.ADMIN else RoleProject.OWNER,
            allow_deleted=False,
        )

        if not project:
            # samakan response dengan "tidak ditemukan/akses"
            raise exceptions.ProjectNotFoundError

        # tidak boleh duplikat member
        if await self.repo.get_member_by_ids(project_id, member.id):
            raise exceptions.MemberAlreadyExistsError

        # validasi aturan role
        ensure_can_assign_member_role(member.role, role)

        created = await self.repo.add_project_member(project_id, member.id, role)

        self.uow.add_event(
            ProjectMemberAddedEvent(
                performed_by=actor.id,
                project_id=project.id,
                member_id=member.id,
                member_name=member.name,
                new_role=role,
                project_title=project.title,
                user=actor,
            )
        )
        return created

    async def remove_member_by_actor(
        self, project_id: int, actor: User, member: User
    ) -> None:
        """Menghapus anggota dari proyek.

        Args:
            project_id (int): ID proyek
            actor (User): Pengguna yang melakukan aksi
            member (User): Anggota yang akan dihapus
            target_user_id (int): ID pengguna target yang akan dihapus

        Raises:
            exceptions.ProjectNotFoundError: Jika proyek tidak ditemukan
            exceptions.MemberNotFoundError: Jika anggota tidak ditemukan
            exceptions.CannotRemoveMemberError: Jika anggota adalah pemilik proyek
        """

        # pastikan actor owner (dan dapatkan owner id)
        project = await self.repo.get_project_by_id(
            project_id=project_id,
            user_id=actor.id,
            required_role=None if actor.role == Role.ADMIN else RoleProject.OWNER,
            allow_deleted=False,
        )
        if not project:
            raise exceptions.ProjectNotFoundError

        # pastikan member ada
        if not await self.repo.get_member_by_ids(project_id, member.id):
            raise exceptions.MemberNotFoundError

        # validasi aturan penghapusan
        ensure_actor_can_remove_member(
            project_owner_id=project.created_by,
            actor_user_id=actor.id,
            target_user_id=member.id,
        )

        await self.repo.remove_project_member(project_id, member.id)

        self.uow.add_event(
            ProjectMemberRemovedEvent(
                performed_by=actor.id,
                project_id=project.id,
                member_id=member.id,
                member_name=member.name,
            )
        )

    async def change_role_member_by_actor(
        self, project_id: int, actor: User, member: User, new_role: RoleProject
    ) -> ProjectMember:
        # pastikan actor owner
        project = await self.repo.get_owned_project_by_user(actor.id, project_id)
        if not project:
            raise exceptions.ProjectNotFoundError

        current = await self.repo.get_member_by_ids(project_id, member.id)
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

        updated = await self.repo.update_project_member_role(
            current, project_id, new_role
        )
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

    async def ensure_member_in_project(
        self,
        *,
        user: User,
        project_id: int,
        project_role: RoleProject | None = None,
    ) -> bool:
        return await self.repo.ensure_member_in_project(
            user_id=user.id,
            project_id=project_id,
            required_role=project_role,
        )

    async def get_project_report_(
        self,
        *,
        user: User,
        project_id: int,
        week_start: date | None = None,
    ) -> ProjectReport:
        # Pastikan user bisa akses (admin atau member)

        if user.role != Role.ADMIN:
            can_access = await self.repo.ensure_member_in_project(
                user_id=user.id,
                project_id=project_id,
                required_role=RoleProject.OWNER,
            )
            if not can_access:
                raise exceptions.ForbiddenError("Tidak punya akses ke proyek ini")

        # Ambil semua task proyek (dengan assignees)
        tasks = await self.uow.task_repo.list_by_filters(
            filters={"project_id": project_id},
            custom_query=lambda q: q.options(selectinload(Task.assignees)),
        )

        # Counters
        task_complete = 0
        task_not_complete = 0

        # Priority counters
        pr_high = pr_medium = pr_low = 0

        # Assignee stats
        assignee_stats: dict[int, dict[str, int]] = defaultdict(
            lambda: {"complete": 0, "not_complete": 0}
        )
        assignee_ids: set[int] = set()

        for t in tasks:
            is_complete = t.status == StatusTask.COMPLETED
            if is_complete:
                task_complete += 1
            else:
                task_not_complete += 1

            # Priority
            if t.priority == PriorityLevel.HIGH:
                pr_high += 1
            elif t.priority == PriorityLevel.MEDIUM:
                pr_medium += 1
            elif t.priority == PriorityLevel.LOW:
                pr_low += 1

            # Assignee counts
            for a in t.assignees:
                assignee_ids.add(a.user_id)
                if is_complete:
                    assignee_stats[a.user_id]["complete"] += 1
                else:
                    assignee_stats[a.user_id]["not_complete"] += 1

        # Ambil data user assignee
        pegawai_service = PegawaiService()
        users = await pegawai_service.list_user_by_ids(sorted(assignee_ids))
        user_map = {u.id: u for u in users if u}

        assignee_items = [
            ProjectReportAssignee(
                user_id=uid,
                email=user_map.get(uid).email if user_map.get(uid) else "",  # type: ignore
                profile_url=user_map.get(uid).profile_url  # type: ignore
                if user_map.get(uid)
                else "",
                task_complete=stats["complete"],
                task_not_complete=stats["not_complete"],
            )
            for uid, stats in assignee_stats.items()
        ]

        # Weekly (7 hari) report
        today = date.today()
        start_day = week_start or (today - timedelta(days=6))
        days = [start_day + timedelta(days=i) for i in range(7)]

        week_items: list[ProjectReportWeekItem] = []
        for d in days:
            wc = 0
            wnc = 0
            for t in tasks:
                # gunakan updated_at jika ada, fallback created_at
                stamp = (t.updated_at or t.created_at or datetime.utcnow()).date()
                if stamp == d:
                    if t.status == StatusTask.COMPLETED:
                        wc += 1
                    else:
                        wnc += 1
            week_items.append(
                ProjectReportWeekItem(
                    date=d,
                    task_complete=wc,
                    task_not_complete=wnc,
                )
            )

        return ProjectReport(
            project_summary=ProjectReportSummary(
                total_task=task_complete + task_not_complete,
                task_complete=task_complete,
                task_not_complete=task_not_complete,
            ),
            assignee=assignee_items,
            priority=ProjectReportPriority(
                high=pr_high, medium=pr_medium, low=pr_low
            ),
            weakly_report=week_items,
            tasks_estimation=[
                TaskEstimationItem(
                    task_id=t.id,
                    milestone_id=t.milestone_id,
                    name=t.name,
                    status=t.status,
                    finish_duration=t.finish_duration,
                    estimated_duration=t.estimated_duration,
                    start_date=t.start_date,
                    due_date=t.due_date,
                    completed_at=t.completed_at,
                )
                for t in tasks
            ],
        )

    async def get_project_report(
        self, *, user: User, project_id: int, week_start: date | None = None
    ) -> ProjectReport:
        if user.role != Role.ADMIN:
            can_access = await self.repo.ensure_member_in_project(
                user_id=user.id,
                project_id=project_id,
                required_role=RoleProject.OWNER,
            )
            if not can_access:
                raise exceptions.ForbiddenError("Tidak punya akses ke proyek ini")

        today = date.today()
        start_day = week_start or (today - timedelta(days=6))
        end_day = start_day + timedelta(days=6)

        summary_data, assignee_rows, weekly_map, tasks = await asyncio.gather(
            self.uow.task_repo.get_report_summary_priority(project_id),
            self.uow.task_repo.get_report_assignee_stats(project_id),
            self.uow.task_repo.get_report_weekly_stats(
                project_id, start_day, end_day
            ),
            self.uow.task_repo.list_by_filters(filters={"project_id": project_id}),
        )

        # Fetch user info (assignee) sekali
        assignee_ids = [r["user_id"] for r in assignee_rows]
        pegawai_service = PegawaiService()
        users = await pegawai_service.list_user_by_ids(sorted(assignee_ids))
        user_map = {u.id: u for u in users if u}

        assignee_items = [
            ProjectReportAssignee(
                user_id=row["user_id"],
                email=getattr(user_map.get(row["user_id"]), "email", "") or "",
                profile_url=getattr(user_map.get(row["user_id"]), "profile_url", "")
                or "",
                task_complete=row["task_complete"],
                task_not_complete=row["task_not_complete"],
            )
            for row in assignee_rows
        ]

        weekly_items: list[ProjectReportWeekItem] = []
        for i in range(7):
            d = start_day + timedelta(days=i)
            c, nc = weekly_map.get(d, (0, 0))
            weekly_items.append(
                ProjectReportWeekItem(
                    date=d,
                    task_complete=c,
                    task_not_complete=nc,
                )
            )

        return ProjectReport(
            project_summary=ProjectReportSummary(
                total_task=summary_data["total_task"],
                task_complete=summary_data["task_complete"],
                task_not_complete=summary_data["task_not_complete"],
            ),
            assignee=assignee_items,
            priority=ProjectReportPriority(
                high=summary_data["high"],
                medium=summary_data["medium"],
                low=summary_data["low"],
            ),
            weakly_report=weekly_items,
            tasks_estimation=[
                TaskEstimationItem(
                    task_id=t.id,
                    milestone_id=t.milestone_id,
                    name=t.name,
                    status=t.status,
                    finish_duration=t.finish_duration,
                    estimated_duration=t.estimated_duration,
                    start_date=t.start_date,
                    due_date=t.due_date,
                    completed_at=t.completed_at,
                )
                for t in tasks
            ],
        )

    async def get_members(self, project_id: int) -> Sequence[ProjectMember]:
        """Mendapatkan anggota proyek berdasarkan ID proyek.

        Args:
            project_id (int): ID proyek.

        Returns:
            Sequence[ProjectMember]: Daftar anggota proyek.
        """
        return await self.repo.list_project_members(project_id)
