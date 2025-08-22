from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.role_model import Role
from app.schemas.dashboard import AdminDashboardResponse

if TYPE_CHECKING:
    from app.services.user_service import UserService


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def admin_dashboard(
        self, user_service: "UserService", limit: int
    ) -> AdminDashboardResponse:
        """Get admin dashboard data.

        Args:
            user_service (UserService): User service instance.
            limit (int): Limit for top users.

        Returns:
            AdminDashboardResponse: Admin dashboard response.
        """

        users = await user_service.list_user()
        role_counts = dict.fromkeys(Role, 0)

        for user in users:
            role_counts[user.role] = role_counts.get(user.role, 0) + 1

        top_users = sorted(users, key=lambda u: u.name, reverse=True)[:limit]

        return AdminDashboardResponse(top_users=top_users, role_counts=role_counts)
