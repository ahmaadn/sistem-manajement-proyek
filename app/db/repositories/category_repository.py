from typing import Protocol, runtime_checkable

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.category_model import Category
from app.db.models.task_model import Task


@runtime_checkable
class InterfaceCategoryRepository(Protocol):
    async def create(self, *, payload: dict) -> Category: ...
    async def get_by_id(self, *, category_id: int) -> Category | None: ...
    async def list_by_project(self, *, project_id: int) -> list[Category]: ...
    async def update(self, *, category: Category, data: dict) -> Category: ...
    async def delete(self, *, category: Category) -> None: ...
    async def assign_to_task(self, *, task: Task, category: Category) -> Task: ...
    async def unassign_from_task(self, *, task: Task) -> Task: ...


class CategorySQLAlchemyRepository(InterfaceCategoryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, payload: dict) -> Category:
        """Membuat kategori baru.

        Args:
            payload (dict): Data kategori baru.

        Returns:
            Category: Kategori yang telah dibuat.
        """
        category = Category(**payload)
        self.session.add(category)
        await self.session.flush()
        return category

    async def get_by_id(self, *, category_id: int) -> Category | None:
        """Mengambil kategori berdasarkan ID.

        Args:
            category_id (int): ID kategori yang ingin diambil.

        Returns:
            Category | None: Kategori yang ditemukan atau None jika tidak ada.
        """
        res = await self.session.execute(
            select(Category).where(Category.id == category_id)
        )
        return res.scalar_one_or_none()

    async def list_by_project(self, *, project_id: int) -> list[Category]:
        """Mengambil daftar kategori berdasarkan ID proyek.

        Args:
            project_id (int): ID proyek yang ingin diambil kategorinya.

        Returns:
            list[Category]: Daftar kategori yang ditemukan.
        """
        res = await self.session.execute(
            select(Category)
            .where(Category.project_id == project_id)
            .order_by(Category.id.asc())
        )
        return list(res.scalars().all())

    async def update(self, *, category: Category, data: dict) -> Category:
        """Mengupdate kategori yang ada.

        Args:
            category (Category): Kategori yang ingin diupdate.
            data (dict): Data yang ingin diupdate.

        Returns:
            Category: Kategori yang telah diupdate.
        """
        for k, v in data.items():
            if v is not None:
                setattr(category, k, v)
        await self.session.flush()
        return category

    async def delete(self, *, category: Category) -> None:
        """Menghapus kategori yang ada.

        Args:
            category (Category): Kategori yang ingin dihapus.
        """

        # set category_id ke None pada task yang menggunakan category ini
        await self.session.execute(
            update(Task)
            .where(Task.category_id == category.id)
            .values(category_id=None)
        )
        await self.session.delete(category)

    async def assign_to_task(self, *, task: Task, category: Category) -> Task:
        """Menetapkan kategori ke tugas.

        Args:
            task (Task): Tugas yang ingin ditetapkan kategorinya.
            category (Category): Kategori yang ingin ditetapkan.

        Returns:
            Task: Tugas yang telah diperbarui.
        """
        task.category_id = category.id
        await self.session.flush()
        return task

    async def unassign_from_task(self, *, task: Task) -> Task:
        """Menghapus penetapan kategori dari tugas.

        Args:
            task (Task): Tugas yang ingin dihapus penetapan kategorinya.

        Returns:
            Task: Tugas yang telah diperbarui.
        """
        task.category_id = None
        await self.session.flush()
        return task
