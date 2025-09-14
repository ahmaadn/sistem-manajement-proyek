from dataclasses import dataclass

from app.core.domain.event import DomainEvent
from app.schemas.user import User


@dataclass(frozen=True, kw_only=True)
class ProjectCreatedEvent(DomainEvent):
    project_id: int
    project_title: str
    user: User
    admin_recipients: list[int]


@dataclass(frozen=True, kw_only=True)
class ProjectUpdatedEvent(DomainEvent):
    project_id: int
    project_title: str


@dataclass(frozen=True, kw_only=True)
class ProjectStatusChangedEvent(DomainEvent):
    project_id: int
    before: str
    after: str
