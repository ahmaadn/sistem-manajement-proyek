from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.repositories import (
    get_project_repository,
    get_task_repository,
)
from app.api.dependencies.sessions import get_async_session
from app.api.dependencies.uow import get_uow
from app.db.repositories.project_repository import InterfaceProjectRepository
from app.db.repositories.task_repository import InterfaceTaskRepository
from app.db.uow.sqlalchemy import UnitOfWork
from app.services.dashboard_service import DashboardService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


def get_project_service(
    uow: UnitOfWork = Depends(get_uow),
    repo: InterfaceProjectRepository = Depends(get_project_repository),
) -> ProjectService:
    """Mendapatkan layanan project."""
    return ProjectService(uow, repo)


def get_task_service(
    uow: UnitOfWork = Depends(get_uow),
    repo: InterfaceTaskRepository = Depends(get_task_repository),
) -> TaskService:
    """Mendapatkan layanan task."""
    return TaskService(uow, repo)


def get_dashboard_service(
    session: AsyncSession = Depends(get_async_session),
) -> DashboardService:
    """Mendapatkan layanan dasbor."""
    return DashboardService(session)
