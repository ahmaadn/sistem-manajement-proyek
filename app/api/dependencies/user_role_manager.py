from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.sessions import get_async_session
from app.db.models.role_model import Role, UserRole
from app.schemas.user import UserProfile
from app.services.pegawai_service import PegawaiService


class UserRoleManager:
    def __init__(
        self, session: AsyncSession, pegawai_service: PegawaiService
    ) -> None:
        self.session = session

    async def create(self, user_id: int, employee_data: UserProfile) -> UserRole:
        """
        Membuat pengguna baru bedasarkan informasi pegawai.
        jika pegawai memiliki role admin, maka role pengguna juga akan di
        set sebagai admin.

        Args:
            user_id (int): ID pengguna yang akan dibuat.
            employee_data (UserProfile): Data pegawai yang digunakan untuk
            membuat pengguna baru.

        Returns:
            UserRole: Role pengguna yang baru dibuat atau mendapatkan role jika
            pengguna sudah memiliki role.
        """

        # dapatkan role user
        user_role = await self.get_user_role(user_id)

        # Jika user sudah memiliki role, kembalikan payload
        if user_role:
            return user_role

        role = (
            Role.ADMIN
            if employee_data.employee_role == "admin"
            else Role.TEAM_MEMBER
        )
        new_user_role = UserRole(user_id=user_id, role=role)
        self.session.add(new_user_role)
        await self.session.commit()
        return new_user_role

    async def get_user_role(self, user_id: int):
        """Mendapatkan role pengguna berdasarkan ID.

        Args:
            user_id (int): ID pengguna yang ingin dicari.

        Returns:
            UserRole | None: Role pengguna yang ditemukan atau None jika tidak ada.
        """
        statement = select(UserRole).where(UserRole.user_id == user_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()


async def get_user_role_manager(
    session: AsyncSession = Depends(get_async_session),
    pegawai_service: PegawaiService = Depends(PegawaiService),
):
    """Depedensi untuk mendapatkan user role manager."""

    yield UserRoleManager(session=session, pegawai_service=pegawai_service)
