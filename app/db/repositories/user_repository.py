from abc import ABC, abstractmethod
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.role_model import Role, UserRole


class UserRepository(ABC):
    @abstractmethod
    async def get_user_role(self, user_id: int) -> UserRole | None:
        """Mendapatkan role pengguna berdasarkan ID.

        Args:
            user_id (int): ID pengguna yang ingin dicari.

        Returns:
            UserRole | None: Role pengguna yang ditemukan atau None jika tidak ada.
        """

    @abstractmethod
    async def create_user_role(self, user_id: int, role: Role) -> UserRole:
        """Menetapkan peran kepada pengguna.

        Args:
            user_id (int): ID pengguna yang akan ditetapkan perannya.
            user (PegawaiInfo): Informasi pegawai yang akan digunakan untuk
                menetapkan peran.

        Returns:
            UserRole: Objek UserRole yang berhasil dibuat atau diperbarui.
        """

    @abstractmethod
    async def list_roles_for_users(self, user_ids: Iterable[int]) -> dict[int, Role]:
        """Mendapatkan daftar peran untuk pengguna berdasarkan ID.

        Args:
            user_ids (Iterable[int]): Daftar ID pengguna yang ingin dicari perannya.

        Returns:
            dict[int, Role]: Daftar peran yang ditemukan untuk pengguna.
        """

    @abstractmethod
    async def bulk_create_user_roles(
        self, items: list[tuple[int, Role]]
    ) -> list[UserRole] | None:
        """
        Membuat banyak UserRole sekaligus.

        Args:
            items (list[tuple[int, Role]]): Daftar tuple yang berisi ID pengguna dan
                peran yang akan dibuat.
        """


class UserSQLAlchemyRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_role(self, user_id: int) -> UserRole | None:
        res = await self.session.execute(
            select(UserRole).where(UserRole.user_id == user_id)
        )
        return res.scalar_one_or_none()

    async def create_user_role(self, user_id: int, role: Role) -> UserRole:
        ur = UserRole(user_id=user_id, role=role)
        self.session.add(ur)
        # flush saja, commit di UoW boundary
        await self.session.flush()
        return ur

    async def list_roles_for_users(self, user_ids: Iterable[int]) -> dict[int, Role]:
        if not user_ids:
            return {}
        res = await self.session.execute(
            select(UserRole).where(UserRole.user_id.in_(list(user_ids)))
        )
        return {ur.user_id: ur.role for ur in res.scalars()}

    async def bulk_create_user_roles(
        self, items: list[tuple[int, Role]]
    ) -> list[UserRole] | None:
        if not items:
            return None

        user_role_list = [UserRole(user_id=uid, role=role) for uid, role in items]
        self.session.add_all(user_role_list)
        await self.session.flush()

        return user_role_list
