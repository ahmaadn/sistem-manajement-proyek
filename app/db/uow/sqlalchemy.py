from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Protocol, runtime_checkable

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.bus import dispatch_pending_events
from app.db.repositories.attachment_repository import (
    AttachmentSQLAlchemyRepository,
    InterfaceAttachmentRepository,
)
from app.db.repositories.audit_repository import (
    AuditSQLAlchemyRepository,
    InterfaceAuditRepository,
)
from app.db.repositories.category_repository import (
    CategorySQLAlchemyRepository,
    InterfaceCategoryRepository,
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
from app.db.repositories.notification_repository import (
    InterfaceNotificationRepository,
    NotificationSQLAlchemyRepository,
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

logger = logging.getLogger(__name__)


@runtime_checkable
class UnitOfWork(Protocol):
    session: AsyncSession

    @property
    def comment_repo(self) -> InterfaceCommentRepository: ...

    @property
    def task_repo(self) -> InterfaceTaskRepository: ...

    @property
    def project_repo(self) -> InterfaceProjectRepository: ...

    @property
    def dashboard_repo(self) -> InterfaceDashboardReadRepository: ...
    @property
    def user_repository(self) -> InterfaceUserRepository: ...

    @property
    def attachment_repo(self) -> InterfaceAttachmentRepository: ...

    @property
    def audit_repo(self) -> InterfaceAuditRepository: ...

    @property
    def milestone_repo(self) -> InterfaceMilestoneRepository: ...

    @property
    def category_repo(self) -> InterfaceCategoryRepository: ...

    @property
    def notification_repo(self) -> InterfaceNotificationRepository: ...

    background_tasks: BackgroundTasks | None

    def add_event(self, event: "DomainEvent") -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    def set_background_tasks(self, background_tasks: BackgroundTasks) -> None: ...


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._events: List["DomainEvent"] = []
        self._closed = False
        self._committed = False

        # init repo
        self._comment_repo: InterfaceCommentRepository | None = None
        self._task_repo: InterfaceTaskRepository | None = None
        self._project_repo: InterfaceProjectRepository | None = None
        self._dashboard_repo: InterfaceDashboardReadRepository | None = None
        self._user_repository: InterfaceUserRepository | None = None
        self._attachment_repo: InterfaceAttachmentRepository | None = None
        self._audit_repo: InterfaceAuditRepository | None = None
        self._milestone_repo: InterfaceMilestoneRepository | None = None
        self._category_repo: InterfaceCategoryRepository | None = None
        self._notification_repo: InterfaceNotificationRepository | None = None

        self.background_tasks = None

    @property
    def comment_repo(self) -> InterfaceCommentRepository:
        if self._comment_repo is None:
            self._comment_repo = CommentSQLAlchemyRepository(self.session)
        return self._comment_repo

    @property
    def task_repo(self) -> InterfaceTaskRepository:
        if self._task_repo is None:
            self._task_repo = TaskSQLAlchemyRepository(self.session)
        return self._task_repo

    @property
    def project_repo(self) -> InterfaceProjectRepository:
        if self._project_repo is None:
            self._project_repo = ProjectSQLAlchemyRepository(self.session)
        return self._project_repo

    @property
    def dashboard_repo(self) -> InterfaceDashboardReadRepository:
        if self._dashboard_repo is None:
            self._dashboard_repo = DashboardSQLAlchemyReadRepository(self.session)
        return self._dashboard_repo

    @property
    def user_repository(self) -> InterfaceUserRepository:
        if self._user_repository is None:
            self._user_repository = UserSQLAlchemyRepository(self.session)
        return self._user_repository

    @property
    def attachment_repo(self) -> InterfaceAttachmentRepository:
        if self._attachment_repo is None:
            self._attachment_repo = AttachmentSQLAlchemyRepository(self.session)
        return self._attachment_repo

    @property
    def audit_repo(self) -> InterfaceAuditRepository:
        if self._audit_repo is None:
            self._audit_repo = AuditSQLAlchemyRepository(self.session)
        return self._audit_repo

    @property
    def milestone_repo(self) -> InterfaceMilestoneRepository:
        if self._milestone_repo is None:
            self._milestone_repo = MilestoneSQLAlchemyRepository(self.session)
        return self._milestone_repo

    @property
    def category_repo(self) -> InterfaceCategoryRepository:
        if self._category_repo is None:
            self._category_repo = CategorySQLAlchemyRepository(self.session)
        return self._category_repo

    @property
    def notification_repo(self) -> InterfaceNotificationRepository:
        if self._notification_repo is None:
            self._notification_repo = NotificationSQLAlchemyRepository(self.session)
        return self._notification_repo

    def add_event(self, event: "DomainEvent") -> None:
        """Menambahkan event ke dalam unit of work.

        Args:
            event (DomainEvent): Event yang akan ditambahkan.
        """
        # Simpan di buffer dan enqueue ke session (agar konsisten dengan bus)
        logger.info("Event enqueued: %s", event.__class__.__name__)
        self._events.append(event)

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()
        try:
            # Publish seluruh pending events yang ter-enqueue di session
            logger.info(
                "Committing transaction and dispatching %d events", len(self._events)
            )
            await dispatch_pending_events(self._events, self.background_tasks)
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

    def set_background_tasks(self, background_tasks: BackgroundTasks) -> None:
        """Set background tasks untuk unit of work.

        Args:
            background_tasks (BackgroundTasks): Background tasks yang akan diset.
        """
        self.background_tasks = background_tasks
