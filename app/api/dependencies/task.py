from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.sessions import get_async_session
from app.services.task_service import TaskService


def get_task_service(
    session: AsyncSession = Depends(get_async_session),
) -> TaskService:
    """Mendapatkan layanan tugas."""
    return TaskService(session)
