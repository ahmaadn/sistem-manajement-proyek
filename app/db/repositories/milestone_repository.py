from typing import Any, Callable, Optional, Protocol, runtime_checkable

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.milestone_model import Milestone

CustomQuery = Callable[[Select], Select]


@runtime_checkable
class InterfaceMilestoneRepository(Protocol):
    async def get_by_id(
        self, *, milestone_id: int, options: list[Any] | None = None
    ) -> Milestone | None:
        """Mendapatkan milestone berdasarkan ID.

        Args:
            milestone_id (int): ID milestone.

        Returns:
            Milestone | None: Milestone yang ditemukan atau None jika tidak ada.
        """
        ...

    async def create(self, *, payload: dict[str, Any]) -> Milestone:
        """Membuat milestone baru

        Args:
            payload (dict[str, Any]): _description_
        """
        ...

    async def delete(
        self, *, milestone_id: int | None = None, milestone: Milestone | None = None
    ) -> bool:
        """Menghapus milestone berdasarkan ID dan project.

        Args:
            milestone_id (int): ID milestone.
            milestone (Milestone): Objek milestone yang akan dihapus.
        """
        ...

    async def list_by_project(
        self,
        *,
        project_id: int,
        custom_query: Optional[CustomQuery] = None,
    ) -> list[Milestone]:
        """List milestone berdasarkan project.

        Args:
            project_id (int): ID project.
            custom_query (Optional[CustomQuery], optional): kustom query untuk
                diterapkan. Defaults to None.

        Returns:
            list[Milestone]: Daftar milestone untuk project yang ditentukan.
        """
        ...

    async def get_by_id_for_project(
        self,
        *,
        project_id: int,
        milestone_id: int,
    ) -> Milestone | None:
        """Mendapatkan milestone berdasarkan ID dan project.

        Args:
            project_id (int): ID project.
            milestone_id (int): ID milestone.

        Returns:
            Milestone | None: Milestone yang ditemukan atau None jika tidak ada.
        """
        ...

    async def next_display_order(self, project_id: int) -> int:
        """
        Menghitung nilai display_order berikutnya untuk sebuah proyek.
        Dipakai untuk menjaga urutan tampilan task.
        """
        ...

    async def validate_display_order(
        self, project_id: int, display_order: Optional[int]
    ) -> int:
        """
        Memvalidasi display_order:
        - Jika None/<=0 atau sudah digunakan task lain dalam proyek yang sama,
          akan mengembalikan nilai display_order berikutnya yang valid.
        - Jika valid, mengembalikan nilai yang diberikan.
        """
        ...


class MilestoneSQLAlchemyRepository(InterfaceMilestoneRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self, *, milestone_id: int, options: list[Any] | None = None
    ) -> Milestone | None:
        return await self.session.get(Milestone, milestone_id, options=options)

    async def create(self, *, payload: dict[str, Any]) -> Milestone:
        milestone = Milestone(**payload)
        self.session.add(milestone)
        await self.session.commit()
        return milestone

    async def delete(
        self, *, milestone_id: int | None = None, milestone: Milestone | None = None
    ) -> bool:
        if milestone_id is None and milestone is None:
            return False

        if milestone is not None:
            await self.session.delete(milestone)
            return True

        stmt = (
            select(Milestone)
            .where(
                Milestone.id == milestone_id,
            )
            .limit(1)
        )
        res = await self.session.execute(stmt)
        milestone = res.scalar_one_or_none()
        if milestone:
            await self.session.delete(milestone)
            return True
        return False

    async def list_by_project(
        self,
        *,
        project_id: int,
        custom_query: Optional[CustomQuery] = None,
    ) -> list[Milestone]:
        stmt = (
            select(Milestone)
            .where(Milestone.project_id == project_id)
            .order_by(Milestone.display_order.desc())
        )
        if custom_query:
            stmt = custom_query(stmt)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_by_id_for_project(
        self, *, project_id: int, milestone_id: int
    ) -> Milestone | None:
        stmt = (
            select(Milestone)
            .where(
                Milestone.id == milestone_id,
                Milestone.project_id == project_id,
            )
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def next_display_order(self, project_id: int) -> int:
        q = await self.session.execute(
            select(Milestone)
            .where(Milestone.project_id == project_id)
            .order_by(Milestone.display_order.desc())
        )
        last = q.scalars().first()
        return 10000 if last is None else (last.display_order + 10000)

    async def validate_display_order(
        self, project_id: int, display_order: Optional[int]
    ) -> int:
        if display_order is None or display_order <= 0:
            return await self.next_display_order(project_id)

        exists_same = await self.session.execute(
            select(Milestone.id)
            .where(
                Milestone.project_id == project_id,
                Milestone.display_order == display_order,
            )
            .limit(1)
        )
        if exists_same.first():
            return await self.next_display_order(project_id)
        return display_order
