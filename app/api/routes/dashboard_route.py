from fastapi import APIRouter, Depends, Query, status
from fastapi_utils.cbv import cbv

from app.api.dependencies.dashboard import get_dashboard_service
from app.api.dependencies.services import get_project_service
from app.api.dependencies.task import get_task_service
from app.api.dependencies.user import (
    get_user_admin,
    get_user_member,
    get_user_pm,
    get_user_service,
)
from app.schemas.dashboard import (
    AdminDashboardResponse,
    PMDashboardResponse,
    UserDashboardResponse,
)
from app.schemas.user import User
from app.services.dashboard_service import DashboardService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.utils.exceptions import AppErrorResponse

r = router = APIRouter(tags=["dashboard"])


@cbv(r)
class _Dashboard:
    dashboard_service: DashboardService = Depends(get_dashboard_service)
    project_service: ProjectService = Depends(get_project_service)
    task_service: TaskService = Depends(get_task_service)

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

    @r.get(
        "/dashboard/pm",
        response_model=PMDashboardResponse,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "model": PMDashboardResponse,
                "description": "Data Dashboard untuk Project Manager",
            }
        },
    )
    async def pm_dashboard(
        self,
        pm: User = Depends(get_user_pm),
        limit_deadline: int = 5,
        skip_deadline: int = 0,
    ) -> PMDashboardResponse:
        return await self.dashboard_service.pm_dashboard(
            project_service=self.project_service,
            skip_deadline=skip_deadline,
            limit_deadline=limit_deadline,
        )

    @r.get(
        "/dashboard/user",
        status_code=status.HTTP_200_OK,
        response_model=UserDashboardResponse,
        responses={
            status.HTTP_200_OK: {
                "model": UserDashboardResponse,
                "description": "Dashboard found",
            },
        },
    )
    async def user_dashboard(
        self,
        user: User = Depends(get_user_member),
        limit_tasks: int = Query(5, ge=1, le=20),
    ) -> UserDashboardResponse:
        return await self.dashboard_service.user_dashboard(
            user.id,
            task_service=self.task_service,
            project_service=self.project_service,
            limit_tasks=limit_tasks,
        )
