from dataclasses import dataclass

from app.core.domain.event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserRoleAssignedEvent(DomainEvent):
    assignee_id: int
    assignee_name: str
    assignee_role: str
