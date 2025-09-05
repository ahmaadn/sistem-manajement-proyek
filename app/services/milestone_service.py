from typing import Any

from sqlalchemy.orm import selectinload

from app.db.models.milestone_model import Milestone
from app.db.models.project_member_model import RoleProject
from app.db.models.role_model import Role
from app.db.models.task_model import Task
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.milestone import (
    MilestoneCreate,
    MilestoneDetail,
    MilestoneSubTaskRead,
    MilestoneTaskRead,
)
from app.schemas.task import TaskAssigneeRead
from app.schemas.user import User, UserBase
from app.services.pegawai_service import PegawaiService
from app.utils import exceptions


class MilestoneService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.repo = self.uow.milestone_repo

    def _eager_options(self):
        """Mendapatkan opsi eager loading untuk query milestone.

        Returns:
            list: Daftar opsi eager loading.
        """
        return [
            selectinload(Milestone.tasks),
            selectinload(Milestone.tasks).selectinload(Task.assignees),
            selectinload(Milestone.tasks).selectinload(Task.sub_tasks),
            selectinload(Milestone.tasks)
            .selectinload(Task.sub_tasks)
            .selectinload(Task.assignees),
        ]

    async def _ensure_member(self, *, user: User, project_id: int) -> None:
        """Memastikan bahwa pengguna adalah anggota proyek.

        Args:
            user (User): Pengguna yang akan diperiksa.
            project_id (int): ID proyek yang akan diperiksa.

        Raises:
            exceptions.ProjectNotFoundError: Jika proyek tidak ditemukan.
            exceptions.ForbiddenError: Jika pengguna tidak memiliki akses ke proyek
                ini.
        """
        (
            project_exists,
            is_member,
        ) = await self.uow.project_repo.get_project_membership_flags(
            user_id=user.id, project_id=project_id
        )
        if not project_exists:
            raise exceptions.ProjectNotFoundError("Project tidak ditemukan")
        if not is_member:
            raise exceptions.ForbiddenError(
                "User tidak memiliki akses ke proyek ini"
            )

    async def _fetch_milestones(self, *, project_id: int) -> list[Milestone]:
        """Mengambil daftar milestone untuk proyek tertentu.

        Args:
            project_id (int): ID proyek yang akan diambil milestone-nya.

        Returns:
            list[Milestone]: Daftar milestone yang terkait dengan proyek.
        """
        opts = self._eager_options()
        milestones = await self.repo.list_by_project(
            project_id=project_id,
            custom_query=lambda q: q.options(*opts).order_by(
                Milestone.display_order.asc()
            ),
        )
        return sorted(milestones, key=lambda m: m.display_order, reverse=True)

    @staticmethod
    def _collect_assignee_ids(milestones: list[Milestone]) -> set[int]:
        """Mengumpulkan ID pengguna yang ditugaskan dari daftar milestone.

        Args:
            milestones (list[Milestone]): Daftar milestone yang akan diproses.

        Returns:
            set[int]: Kumpulan ID pengguna yang ditugaskan.
        """
        ids: set[int] = set()
        for m in milestones:
            for t in m.tasks or []:
                for a in t.assignees or []:
                    uid = getattr(a, "user_id", None)
                    if uid is not None:
                        ids.add(uid)
                for st in t.sub_tasks or []:
                    for a in st.assignees or []:
                        uid = getattr(a, "user_id", None)
                        if uid is not None:
                            ids.add(uid)
        return ids

    async def _get_user_info_map(
        self, assignee_ids: set[int]
    ) -> dict[int, UserBase | None]:
        """Mengambil informasi pegawai berdasarkan ID pengguna yang ditugaskan.

        Args:
            assignee_ids (set[int]): Kumpulan ID pengguna yang ditugaskan.

        Returns:
            dict[int, PegawaiInfo | None]: Peta ID pengguna ke informasi pegawai.
        """
        if not assignee_ids:
            return {}
        pegawai_service = PegawaiService()
        unique_ids = sorted(assignee_ids)
        users = await pegawai_service.list_user_by_ids(unique_ids)
        return dict(zip(unique_ids, users, strict=False))

    @staticmethod
    def _map_assignees(
        task_like: Task, user_info_map: dict[int, UserBase | None]
    ) -> list[TaskAssigneeRead]:
        """Memetakan penugasan pengguna untuk tugas tertentu.

        Args:
            task_like (Task): Tugas yang akan dipetakan.
            user_info_map (dict[int, PegawaiInfo | None]): Peta ID pengguna ke
                informasi pegawai.

        Returns:
            list[UserTaskAssignmentResponse]: Daftar respons penugasan pengguna.
        """
        items: list[TaskAssigneeRead] = []
        for a in task_like.assignees or []:
            info = user_info_map.get(getattr(a, "user_id", 0))
            if info is None:
                continue
            items.append(
                TaskAssigneeRead(
                    user_id=info.id,
                    name=info.name,
                    email=info.email or "",
                    profile_url=info.profile_url or "",
                )
            )
        return items

    def _map_subtask(
        self, st: Task, user_info_map: dict[int, UserBase | None]
    ) -> MilestoneSubTaskRead:
        """Memetakan sub-tugas untuk respons milestone.

        Args:
            st (Task): Sub-tugas yang akan dipetakan.
            user_info_map (dict[int, PegawaiInfo | None]): Peta ID pengguna ke
                informasi pegawai.

        Returns:
            MilestoneSubtaskResponse: Respons sub-tugas yang dipetakan.
        """
        return MilestoneSubTaskRead(
            id=st.id,
            name=st.name,
            status=st.status,
            priority=st.priority,
            display_order=st.display_order,
            due_date=st.due_date,
            start_date=st.start_date,
            assignees=self._map_assignees(st, user_info_map),
        )

    def _map_task(
        self,
        t: Task,
        user_info_map: dict[int, UserBase | None],
        sort_by: str = "display_order",
        descending: bool = False,
    ) -> MilestoneTaskRead:
        """Memetakan tugas untuk respons milestone.

        Args:
            t (Task): Tugas yang akan dipetakan.
            user_info_map (dict[int, PegawaiInfo | None]): Peta ID pengguna ke
                informasi pegawai.

        Returns:
            MilestoneTaskResponse: Respons tugas yang dipetakan.
        """
        sub_tasks_sorted = sorted(
            (t.sub_tasks or []),
            key=lambda st: self._sort_key(st, sort_by, descending),
            reverse=descending,
        )
        sub_tasks_resp = [
            self._map_subtask(st, user_info_map) for st in sub_tasks_sorted
        ]
        return MilestoneTaskRead(
            id=t.id,
            name=t.name,
            status=t.status,
            priority=t.priority,
            display_order=t.display_order,
            due_date=t.due_date,
            start_date=t.start_date,
            assignees=self._map_assignees(t, user_info_map),
            sub_tasks=sub_tasks_resp,
        )

    def _map_milestone(
        self,
        m: Milestone,
        user_info_map: dict[int, UserBase | None],
        sort_by: str = "display_order",
        descending: bool = False,
    ) -> MilestoneDetail:
        """Memetakan milestone untuk respons milestone.

        Args:
            m (Milestone): Milestone yang akan dipetakan.
            user_info_map (dict[int, PegawaiInfo | None]): Peta ID pengguna ke
                informasi pegawai.

        Returns:
            MilestoneResponse: Respons milestone yang dipetakan.
        """
        top_level_tasks = sorted(
            (t for t in (m.tasks or []) if getattr(t, "parent_id", None) is None),
            key=lambda t: self._sort_key(t, sort_by, descending),
            reverse=descending,
        )
        tasks_resp = [
            self._map_task(
                t=t,
                user_info_map=user_info_map,
                sort_by=sort_by,
                descending=descending,
            )
            for t in top_level_tasks
        ]
        return MilestoneDetail(
            id=m.id,
            project_id=m.project_id,
            title=m.title,
            display_order=m.display_order,
            created_at=m.created_at,
            updated_at=m.updated_at,
            tasks=tasks_resp,
        )

    @staticmethod
    def _priority_rank(value: Any) -> int:
        """Custom order: low < medium < high."""
        if value is None:
            return 999
        order = {"low": 0, "medium": 1, "high": 2}
        return order.get(str(value).lower(), 999)

    def _primary_key(self, value: Any, field: str) -> Any:
        if field == "priority":
            return self._priority_rank(value)
        if isinstance(value, str):
            return value.casefold()
        return value

    def _sort_key(self, obj: Any, field: str, descending: bool) -> tuple[int, Any]:
        """Return a key that keeps None at the end for both asc/desc."""
        if field == "title":
            field = "name"
        v = getattr(obj, field, None)
        primary = self._primary_key(v, field)
        is_none = v is None
        # None last on both directions:
        # - asc: none_rank = 1 for None
        # - desc: none_rank = 0 for None (because list.sort(reverse=True) flips the order)
        none_rank = (
            (1 if is_none else 0) if not descending else (0 if is_none else 1)
        )
        return (none_rank, primary)

    async def list_milestones(
        self, *, user: User, project_id: int, sort_by: str, descending: bool
    ) -> list[MilestoneDetail]:
        """Mengambil daftar milestone untuk proyek tertentu.

        Args:
            user (User): Pengguna yang meminta daftar milestone.
            project_id (int): ID proyek yang dimaksud.

        Returns:
            list[MilestoneResponse]: Daftar respons milestone yang dipetakan.
        """
        if user.role != Role.ADMIN:
            await self._ensure_member(user=user, project_id=project_id)

        milestones = await self._fetch_milestones(project_id=project_id)
        assignee_ids = self._collect_assignee_ids(milestones)
        user_info_map = await self._get_user_info_map(assignee_ids)
        return [
            self._map_milestone(
                m=m,
                user_info_map=user_info_map,
                sort_by=sort_by,
                descending=descending,
            )
            for m in milestones
        ]

    async def create_milestone(
        self, *, user: User, project_id: int, payload: MilestoneCreate
    ) -> Milestone:
        """Membuat milestone baru untuk proyek tertentu.

        Args:
            user (User): Pengguna yang membuat milestone.
            project_id (int): ID proyek yang dimaksud.
            payload (MilestoneCreate): Data untuk membuat milestone baru.

        Raises:
            exceptions.ProjectNotFoundError: Jika proyek tidak ditemukan.
            exceptions.ForbiddenError: Jika pengguna tidak memiliki akses ke proyek.

        Returns:
            Milestone: Milestone yang berhasil dibuat.
        """
        (
            project_exists,
            is_owner,
        ) = await self.uow.project_repo.get_project_membership_flags(
            user_id=user.id, project_id=project_id, required_role=RoleProject.OWNER
        )

        if not project_exists:
            raise exceptions.ProjectNotFoundError("Project tidak ditemukan")

        if not is_owner:
            raise exceptions.ForbiddenError(
                "Hanya owner proyek yang dapat membuat milestone"
            )

        milestone_data = payload.model_dump()
        milestone_data["project_id"] = project_id
        milestone_data["display_order"] = await self.repo.validate_display_order(
            project_id=project_id, display_order=None
        )
        return await self.repo.create_milestone(payload=milestone_data)

    async def delete_milestone(self, *, user: User, milestone_id: int) -> bool:
        """Menghapus milestone berdasarkan ID dan project.

        Args:
            user (User): Pengguna yang meminta penghapusan milestone.
            project_id (int): ID proyek yang dimaksud.
            milestone_id (int): ID milestone yang akan dihapus.

        Raises:
            exceptions.ProjectNotFoundError: Jika proyek tidak ditemukan.
            exceptions.ForbiddenError: Jika pengguna tidak memiliki akses ke proyek.

        Returns:
            bool: True jika milestone berhasil dihapus, False jika tidak ditemukan.
        """
        milestone = await self.repo.get_by_id(
            milestone_id=milestone_id, options=[selectinload(Milestone.tasks)]
        )
        if not milestone:
            raise exceptions.MilestoneNotFoundError("Milestone tidak ditemukan")

        is_owner = await self.uow.project_repo.is_user_owner_of_project(
            project_id=milestone.project_id, user_id=user.id
        )

        if not is_owner:
            raise exceptions.ForbiddenError(
                "Hanya owner proyek yang dapat menghapus milestone"
            )

        if milestone.tasks:
            raise exceptions.ForbiddenError(
                "Tidak dapat menghapus milestone yang memiliki task"
            )

        result = await self.repo.delete(milestone=milestone)
        if not result:
            raise exceptions.MilestoneNotFoundError("Milestone tidak ditemukan")
        return result

    async def update_milestone(
        self, *, user: User, milestone_id: int, payload: dict[str, Any]
    ) -> Milestone:
        """Mengupdate milestone berdasarkan ID dan project.

        Args:
            user (User): Pengguna yang meminta penghapusan milestone.
            project_id (int): ID proyek yang dimaksud.
            milestone_id (int): ID milestone yang akan dihapus.

        Raises:
            exceptions.ProjectNotFoundError: Jika proyek tidak ditemukan.
            exceptions.ForbiddenError: Jika pengguna tidak memiliki akses ke proyek.

        Returns:
            bool: True jika milestone berhasil dihapus, False jika tidak ditemukan.
        """
        milestone = await self.repo.get_by_id(
            milestone_id=milestone_id, options=[selectinload(Milestone.tasks)]
        )
        if not milestone:
            raise exceptions.MilestoneNotFoundError("Milestone tidak ditemukan")

        is_owner = await self.uow.project_repo.is_user_owner_of_project(
            project_id=milestone.project_id, user_id=user.id
        )

        if not is_owner:
            raise exceptions.ForbiddenError(
                "Hanya owner proyek yang dapat menghapus milestone"
            )

        return await self.repo.update(milestone=milestone, payload=payload)
