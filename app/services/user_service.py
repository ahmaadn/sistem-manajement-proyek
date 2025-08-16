from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.role_model import Role, UserRole
from app.schemas.user import UserProfile, UserRead
from app.services.pegawai_service import PegawaiService
from app.utils import exceptions


class UserService:
    def __init__(
        self, session: AsyncSession, pegawai_service: PegawaiService
    ) -> None:
        self.session = session

        self.pegawai_service = pegawai_service

    async def get_user_role(self, user_id: int) -> UserRole | None:
        """Mendapatkan role pengguna berdasarkan ID.

        Args:
            user_id (int): ID pengguna yang ingin dicari.

        Returns:
            UserRole | None: Role pengguna yang ditemukan atau None jika tidak ada.
        """
        statement = select(UserRole).where(UserRole.user_id == user_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def assign_role_to_user(self, user_id: int, user: UserProfile):
        """Menetapkan peran kepada pengguna."""

        # dapatkan role user
        user_role = await self.get_user_role(user_id)

        # Jika user sudah memiliki role, kembalikan payload
        if user_role:
            return user_role

        # cast role jika employee_role admin maka dia akan manjadi adamin
        role = Role.ADMIN if user.employee_role == "admin" else Role.TEAM_MEMBER

        user_role = UserRole(user_id=user_id, role=role)
        self.session.add(user_role)
        await self.session.commit()
        return user_role

    async def get(self, user_id: int) -> UserRead | None:
        user_profile = await self.pegawai_service.get_user_info(user_id)

        if not user_profile:
            raise exceptions.UserNotFoundError

        user_role = await self.assign_role_to_user(user_id, user_profile)

        return UserRead(**user_profile.model_dump(), role=user_role.role)
