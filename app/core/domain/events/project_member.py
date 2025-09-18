from dataclasses import dataclass

from app.core.domain.event import DomainEvent
from app.schemas.user import User


@dataclass(frozen=True, kw_only=True)
class ProjectMemberAddedEvent(DomainEvent):
    project_id: int
    member_id: int
    member_name: str
    new_role: str
    project_title: None | str = None
    user: User


@dataclass(frozen=True, kw_only=True)
class ProjectMemberUpdatedEvent(DomainEvent):
    project_id: int
    member_id: int
    member_name: str
    before: str
    after: str
    project_title: str
    performed_name: str
    performed_profile_url: str


@dataclass(frozen=True, kw_only=True)
class ProjectMemberRemovedEvent(DomainEvent):
    project_id: int
    member_id: int
    member_name: str
