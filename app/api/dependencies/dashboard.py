from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.sessions import get_async_session
from app.services.dashboard_service import DashboardService


def get_dashboard_service(
    session: AsyncSession = Depends(get_async_session),
) -> DashboardService:
    """Mendapatkan layanan dasbor."""
    return DashboardService(session)
