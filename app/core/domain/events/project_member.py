from dataclasses import dataclass

from app.core.domain.event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ProjectMemberAddedEvent(DomainEvent):
    project_id: int
    member_id: int
    member_name: str
    new_role: str


@dataclass(frozen=True, kw_only=True)
class ProjectMemberUpdatedEvent(DomainEvent):
    project_id: int
    member_id: int
    member_name: str
    before: str
    after: str


@dataclass(frozen=True, kw_only=True)
class ProjectMemberRemovedEvent(DomainEvent):
    project_id: int
    member_id: int
    member_name: str
