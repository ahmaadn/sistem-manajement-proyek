from dataclasses import dataclass

from app.core.domain.event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class TaskAssignedAddedEvent(DomainEvent):
    task_id: int
    task_name: str
    project_id: int
    project_title: str
    user_id: int
    assignee_id: int
    assignee_name: str
    performed_name: str
    performed_profile_url: str


@dataclass(frozen=True, kw_only=True)
class TaskAssignedRemovedEvent(DomainEvent):
    task_id: int
    project_id: int
    user_id: int
    assignee_id: int
    assignee_name: str
