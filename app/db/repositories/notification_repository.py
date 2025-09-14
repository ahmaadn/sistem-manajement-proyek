from typing import Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession


@runtime_checkable
class InterfaceNotificationRepository(Protocol):
    pass


class NotificationSQLAlchemyRepository(InterfaceNotificationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
