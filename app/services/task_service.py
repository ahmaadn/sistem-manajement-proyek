from sqlalchemy import case, func, select

from app.db.models.project_member_model import ProjectMember
from app.db.models.project_model import Project, StatusProject
from app.db.models.task_assigne_model import TaskAssignee
from app.db.models.task_model import StatusTask, Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.user import User
from app.services.base_service import GenericCRUDService
from app.utils import exceptions
from app.utils.common import ErrorCode


class TaskService(GenericCRUDService[Task, TaskCreate, TaskUpdate]):
    model = Task
    audit_entity_name = "task"
    not_found_error_code = ErrorCode.TASK_NOT_FOUND

    def _exception_not_found(self, **extra):
        """
        Membuat exception jika tugas tidak ditemukan.
        """
        return exceptions.TaskNotFoundError("Task not found")

    async def next_display_order(self, project_id: int):
        """Mengambil urutan tampilan tugas berikutnya.

        Args:
            project_id (int): ID proyek yang terkait dengan tugas.

        Returns:
            int: Urutan tampilan tugas berikutnya.
        """

        # Mengambil urutan tampilan tugas bedasarkan project_id
        quary = await self.session.execute(
            select(self.model)
            .where(self.model.project_id == project_id)
            .order_by(self.model.display_order.desc())
        )

        # Ambil tugas terakhir
        last_task = quary.scalars().first()
        if last_task is None:
            return 10000

        return last_task.display_order + 10000

    async def validate_display_order(self, project_id: int, display_order: int):
        """Validasi urutan tampilan tugas.

        Args:
            project_id (int): ID proyek yang terkait dengan tugas.
            display_order (int): Urutan tampilan yang akan divalidasi.

        Raises:
            ValueError: Jika urutan tampilan tidak valid.
        """
        if display_order is None or display_order <= 0:
            display_order = await self.next_display_order(project_id)

        # Cek apakah ada tugas lain dengan urutan tampilan yang sama
        existing_task = await self.session.execute(
            select(self.model)
            .where(self.model.project_id == project_id)
            .where(self.model.display_order == display_order)
        )

        if existing_task.scalars().first() is not None:
            display_order = await self.next_display_order(project_id)

        return display_order

    async def assign_user(self, task: Task, user_info: User) -> TaskAssignee:
        """Menugaskan pengguna ke tugas tertentu.

        Args:
            task_id (int): ID tugas yang akan ditugaskan.
            user_info (User): Informasi pengguna yang akan ditugaskan.

        Raises:
            exceptions.TaskNotFoundError: Jika tugas tidak ditemukan.
            exceptions.UserNotInProjectError: Jika pengguna tidak terdaftar di proyek.

        Returns:
            TaskAssignee: Objek penugasan tugas yang berhasil dibuat.
        """

        # cek user telah terdaftar
        assign_task = await self.session.get(TaskAssignee, (task.id, user_info.id))
        if assign_task:
            return assign_task

        # Cek user ada di project members
        project_members = await self.session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == task.project_id,
                ProjectMember.user_id == user_info.id,
            )
        )

        # Cek apakah user terdaftar di project members
        if user_info.id not in [
            member.user_id for member in project_members.scalars()
        ]:
            raise exceptions.UserNotInProjectError

        assign_task = TaskAssignee(task_id=task.id, user_id=user_info.id)
        self.session.add(assign_task)

        await self.session.commit()
        await self.session.refresh(assign_task)
        return assign_task

    async def get_user_task_statistics(self, user_id: int) -> dict:
        """Mengambil statistik tugas untuk pengguna tertentu.

        Args:
            user_id (int): ID pengguna yang akan diambil statistik tugasnya.

        Returns:
            dict: Statistik tugas untuk pengguna tertentu.
        """

        task_stats_stmt = (
            select(
                func.count().label("total_task"),
                func.sum(
                    case((Task.status == StatusTask.IN_PROGRESS, 1), else_=0)
                ).label("task_in_progress"),
                func.sum(
                    case((Task.status == StatusTask.COMPLETED, 1), else_=0)
                ).label("task_completed"),
                func.sum(
                    case(
                        (Task.status == StatusTask.CANCELLED, 1),
                        else_=0,
                    )
                ).label("task_cancelled"),
            )
            .join(TaskAssignee, TaskAssignee.task_id == Task.id)
            .join(Project, Project.id == Task.project_id)
            .where(
                TaskAssignee.user_id == user_id,
                # Task tidak termasuk delete
                Task.deleted_at.is_(None),
                # Task tidak boleh pending
                Task.status.not_in([StatusTask.PENDING]),
                # hanya proyek yang aktif atau selesai
                Project.status.in_([StatusProject.ACTIVE, StatusProject.COMPLETED]),
                # tidak termasuk proyek yang dihapus
                Project.deleted_at.is_(None),
            )
        )
        task_stats_res = await self.session.execute(task_stats_stmt)
        ts = task_stats_res.first()
        if not ts:
            return {
                "total_task": 0,
                "task_in_progress": 0,
                "task_completed": 0,
                "task_cancelled": 0,
            }

        return {
            "total_task": ts.total_task or 0,
            "task_in_progress": ts.task_in_progress or 0,
            "task_completed": ts.task_completed or 0,
            "task_cancelled": ts.task_cancelled or 0,
        }
