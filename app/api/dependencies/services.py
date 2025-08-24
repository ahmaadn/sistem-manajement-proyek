from fastapi import Depends

from app.api.dependencies.repositories import get_project_repository
from app.api.dependencies.uow import get_uow
from app.db.repositories.project_reepository import ProjectSQLAlchemyRepository
from app.db.uow.sqlalchemy import UnitOfWork
from app.services.project_service import ProjectService


def get_project_service(
    uow: UnitOfWork = Depends(get_uow),
    repo: ProjectSQLAlchemyRepository = Depends(get_project_repository),
) -> ProjectService:
    """Mendapatkan layanan project."""
    return ProjectService(uow, repo)
