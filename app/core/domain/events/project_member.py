from dataclasses import dataclass

from app.core.domain.bus import DomainEvent


@dataclass(frozen=True)
class ProjectMemberAddedEvent(DomainEvent):
    performed_by: int
    project_id: int
    member_id: int
    member_name: str
    new_role: str


@dataclass(frozen=True)
class ProjectMemberUpdatedEvent(DomainEvent):
    performed_by: int
    project_id: int
    member_id: int
    member_name: str
    before: str
    after: str


@dataclass(frozen=True)
class ProjectMemberRemovedEvent(DomainEvent):
    performed_by: int
    project_id: int
    member_id: int
    member_name: str
