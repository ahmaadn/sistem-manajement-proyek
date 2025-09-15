from __future__ import annotations

from typing import Iterable, Protocol, Sequence, runtime_checkable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_model import AuditLog


@runtime_checkable
class InterfaceAuditRepository(Protocol):
    async def list_task_audits(
        self, *, task_id: int, event_types: Iterable[str]
    ) -> Sequence[AuditLog]: ...


class AuditSQLAlchemyRepository(InterfaceAuditRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_task_audits(
        self, *, task_id: int, event_types: Iterable[str]
    ) -> Sequence[AuditLog]:
        ev_list = list(event_types)
        if not ev_list:
            return []
        stmt = (
            select(AuditLog)
            .where(AuditLog.task_id == task_id, AuditLog.action_type.in_(ev_list))
            .order_by(AuditLog.created_at)
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()
