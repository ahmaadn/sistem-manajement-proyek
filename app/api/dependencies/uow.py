from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.sessions import get_async_session
from app.db.uow.sqlalchemy import SQLAlchemyUnitOfWork


async def get_uow(
    session: AsyncSession = Depends(get_async_session),
) -> SQLAlchemyUnitOfWork:
    """Mengambil instance UnitOfWork untuk berinteraksi dengan database."""
    return SQLAlchemyUnitOfWork(session)
