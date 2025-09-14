from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, Sequence, runtime_checkable

from sqlalchemy import Select, asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.notification_model import Notification


@runtime_checkable
class InterfaceNotificationRepository(Protocol):
    async def list_by_recipient(
        self,
        *,
        recipient_id: int,
        only_read: bool | None = None,
        order: str = "desc",
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Notification]: ...

    async def get_by_id(self, *, notif_id: int) -> Notification | None: ...

    async def get_for_user(
        self, *, notif_id: int, user_id: int
    ) -> Notification | None: ...

    async def mark_read(self, *, notif: Notification) -> Notification: ...


class NotificationSQLAlchemyRepository(InterfaceNotificationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _base_stmt(self) -> Select[tuple[Notification]]:
        return select(Notification).options(
            selectinload(Notification.project),
            selectinload(Notification.task),
        )

    async def list_by_recipient(
        self,
        *,
        recipient_id: int,
        only_read: bool | None = None,
        order: str = "desc",
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Notification]:
        stmt = await self._base_stmt()
        stmt = stmt.where(Notification.recipient_id == recipient_id)
        if only_read is True:
            stmt = stmt.where(Notification.is_read.is_(True))
        elif only_read is False:
            stmt = stmt.where(Notification.is_read.is_(False))

        order_by = (
            desc(Notification.created_at)
            if order.lower() == "desc"
            else asc(Notification.created_at)
        )
        stmt = stmt.order_by(order_by).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def get_by_id(self, *, notif_id: int) -> Notification | None:
        res = await self.session.execute(
            (await self._base_stmt()).where(Notification.id == notif_id)
        )
        return res.scalar_one_or_none()

    async def get_for_user(
        self, *, notif_id: int, user_id: int
    ) -> Notification | None:
        res = await self.session.execute(
            (await self._base_stmt()).where(
                Notification.id == notif_id,
                Notification.recipient_id == user_id,
            )
        )
        return res.scalar_one_or_none()

    async def mark_read(self, *, notif: Notification) -> Notification:
        if not notif.is_read:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            self.session.add(notif)
            await self.session.flush()
            await self.session.refresh(notif)
        return notif
