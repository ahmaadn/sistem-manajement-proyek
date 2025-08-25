from dataclasses import dataclass

from app.core.domain.bus import DomainEvent  # gunakan base event Anda


@dataclass(frozen=True, kw_only=True)
class TaskAssignedAddedEvent(DomainEvent):
    task_id: int
    project_id: int
    user_id: int
    assignee_id: int
    assignee_name: str


@dataclass(frozen=True, kw_only=True)
class TaskAssignedRemovedEvent(DomainEvent):
    task_id: int
    project_id: int
    user_id: int
    assignee_id: int
    assignee_name: str
