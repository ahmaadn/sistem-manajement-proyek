from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.sessions import get_async_session
from app.services.project_service import ProjectService


def get_project_service(
    session: AsyncSession = Depends(get_async_session),
) -> ProjectService:
    """Mendapatkan layanan proyek."""
    return ProjectService(session)
