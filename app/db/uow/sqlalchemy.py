from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.bus import dispatch_pending_events, enqueue_event

if TYPE_CHECKING:
    from app.core.domain.bus import DomainEvent


@runtime_checkable
class UnitOfWork(Protocol):
    session: AsyncSession

    def add_event(self, event: Any) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._events: List["DomainEvent"] = []
        self._closed = False

    def add_event(self, event: "DomainEvent") -> None:
        """Menambahkan event ke dalam unit of work.

        Args:
            event (DomainEvent): Event yang akan ditambahkan.
        """
        # Simpan di buffer dan enqueue ke session (agar konsisten dengan bus)
        self._events.append(event)
        enqueue_event(self.session, event)

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()
        try:
            # Publish seluruh pending events yang ter-enqueue di session
            await dispatch_pending_events(self.session)
        finally:
            self._events.clear()
        self._closed = True

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.session.rollback()
        self._events.clear()

    async def close(self) -> None:
        """Close the database session."""
        if not self._closed:
            await self.session.close()
            self._closed = True

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        """Masuk ke dalam konteks unit of work."""
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Keluar dari konteks unit of work.

        Args:
            exc_type (type): Tipe exception yang terjadi, jika ada.
            exc (Exception): Exception yang terjadi, jika ada.
            tb (Traceback): Traceback dari exception yang terjadi, jika ada.
        """
        if exc or not self._closed:
            await self.rollback()
        await self.close()
