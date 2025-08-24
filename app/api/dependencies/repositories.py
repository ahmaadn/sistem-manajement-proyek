from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.sessions import get_async_session
from app.db.repositories.project_reepository import ProjectSQLAlchemyRepository


def get_project_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ProjectSQLAlchemyRepository:
    """Get the project repository."""
    return ProjectSQLAlchemyRepository(session)
