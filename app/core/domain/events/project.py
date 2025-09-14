from dataclasses import dataclass, field

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
    project_title: str
    before: str
    after: str
    user: User
    recipients: list[int] = field(default_factory=list)
