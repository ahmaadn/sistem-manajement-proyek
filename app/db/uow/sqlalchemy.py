from __future__ import annotations

from typing import TYPE_CHECKING, List, Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.bus import dispatch_pending_events, enqueue_event
from app.db.repositories.attachment_repository import (
    AttachmentSQLAlchemyRepository,
    InterfaceAttachmentRepository,
)
from app.db.repositories.comment_repository import (
    CommentSQLAlchemyRepository,
    InterfaceCommentRepository,
)
from app.db.repositories.dashboard_repository import (
    DashboardSQLAlchemyReadRepository,
    InterfaceDashboardReadRepository,
)
from app.db.repositories.milestone_repository import (
    InterfaceMilestoneRepository,
    MilestoneSQLAlchemyRepository,
)
from app.db.repositories.project_repository import (
    InterfaceProjectRepository,
    ProjectSQLAlchemyRepository,
)
from app.db.repositories.task_repository import (
    InterfaceTaskRepository,
    TaskSQLAlchemyRepository,
)
from app.db.repositories.user_repository import (
    InterfaceUserRepository,
    UserSQLAlchemyRepository,
)

if TYPE_CHECKING:
    from app.core.domain.event import DomainEvent


@runtime_checkable
class UnitOfWork(Protocol):
    session: AsyncSession

    comment_repo: InterfaceCommentRepository
    task_repo: InterfaceTaskRepository
    project_repo: InterfaceProjectRepository
    dashboard_repo: InterfaceDashboardReadRepository
    user_repository: InterfaceUserRepository
    attachment_repo: InterfaceAttachmentRepository
    milestone_repo: InterfaceMilestoneRepository

    def add_event(self, event: "DomainEvent") -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._events: List["DomainEvent"] = []
        self._closed = False
        self._committed = False

        # init repo
        self.comment_repo = CommentSQLAlchemyRepository(self.session)
        self.task_repo = TaskSQLAlchemyRepository(self.session)
        self.project_repo = ProjectSQLAlchemyRepository(self.session)
        self.dashboard_repo = DashboardSQLAlchemyReadRepository(self.session)
        self.user_repository = UserSQLAlchemyRepository(self.session)
        self.attachment_repo = AttachmentSQLAlchemyRepository(self.session)
        self.milestone_repo: InterfaceMilestoneRepository = (
            MilestoneSQLAlchemyRepository(self.session)
        )

    def add_event(self, event: "DomainEvent") -> None:
        """Menambahkan event ke dalam unit of work.

        Args:
            event (DomainEvent): Event yang akan ditambahkan.
        """
        # Simpan di buffer dan enqueue ke session (agar konsisten dengan bus)
        self._events.append(event)
        enqueue_event(event)

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()
        try:
            # Publish seluruh pending events yang ter-enqueue di session
            await dispatch_pending_events()
        finally:
            self._events.clear()
        self._committed = True

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.session.rollback()
        self._events.clear()
        self._committed = False

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
        if exc:
            await self.rollback()
