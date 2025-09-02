import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.db.meta import meta

POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "0"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))

engine = create_async_engine(
    str(settings.db_url),
    future=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,
)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base for all models."""

    metadata = meta


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
