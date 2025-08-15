from sqlalchemy import select

from app.db.models.task_model import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.base_service import GenericCRUDService
from app.utils.common import ErrorCode
from app.utils.exceptions import TaskNotFoundError


class TaskService(GenericCRUDService[Task, TaskCreate, TaskUpdate]):
    model = Task
    audit_entity_name = "task"
    not_found_error_code = ErrorCode.TASK_NOT_FOUND

    def _exception_not_found(self, **extra):
        """
        Membuat exception jika tugas tidak ditemukan.
        """
        return TaskNotFoundError("Task not found")

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
