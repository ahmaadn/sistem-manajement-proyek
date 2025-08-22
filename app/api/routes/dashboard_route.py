from fastapi import APIRouter, Depends, status
from fastapi_utils.cbv import cbv

from app.api.dependencies.dashboard import get_dashboard_service
from app.api.dependencies.user import get_user_admin, get_user_service
from app.schemas.dashboard import AdminDashboardResponse
from app.schemas.user import User
from app.services.dashboard_service import DashboardService
from app.services.user_service import UserService
from app.utils.exceptions import AppErrorResponse

r = router = APIRouter(tags=["dashboard"])


@cbv(r)
class _Dashboard:
    dashboard_service: DashboardService = Depends(get_dashboard_service)

    @r.get(
        "/dashboard/admin",
        response_model=AdminDashboardResponse,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_404_NOT_FOUND: {
                "model": AppErrorResponse,
                "description": "Dashboard not found",
            }
        },
    )
    async def admin_dashboard(
        self,
        limit_users: int = 10,
        admin: User = Depends(get_user_admin),
        user_service: UserService = Depends(get_user_service),
    ) -> AdminDashboardResponse:
        return await self.dashboard_service.admin_dashboard(
            user_service, limit=limit_users
        )
