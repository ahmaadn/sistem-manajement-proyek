from fastapi import BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.sessions import get_async_session
from app.db.uow.sqlalchemy import SQLAlchemyUnitOfWork


async def get_uow(
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
) -> SQLAlchemyUnitOfWork:
    """Mengambil instance UnitOfWork untuk berinteraksi dengan database."""
    uow = SQLAlchemyUnitOfWork(session)
    uow.set_background_tasks(background_tasks)
    return uow
