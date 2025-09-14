import datetime
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    occurred_on: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    metadata: dict[str, Any] = field(default_factory=dict)
    performed_by: int | None = None

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def dump_model(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def json(self) -> str:
        return str(self.dump_model())


class EventType(StrEnum):
    # Task
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_DELETED = "task.deleted"
    TASK_STATUS_CHANGED = "task.status.changed"
    TASK_DUE_DATE_CHANGED = "task.due_date.changed"
    TASK_PRIORITY_CHANGED = "task.priority.changed"
    TASK_TITLE_CHANGED = "task.title.changed"

    # Project
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_REMOVED = "project.removed"
    PROJECT_MEMBER_ADDED = "project.member.added"
    PROJECT_MEMBER_UPDATED = "project.member.updated"
    PROJECT_MEMBER_REMOVED = "project.member.removed"
    PROJECT_STATUS_CHANGED = "project.status.changed"

    # subtask
    SUBTASKS_DETACHED = "subtasks.detached"

    # Assignment
    TASK_ASSIGNED_ADDED = "task.assigned.added"
    TASK_ASSIGNED_REMOVED = "task.assigned.removed"
    USER_ROLE_ASSIGNED = "user.role.assigned"

    # Notification
    NOTIFICATION_SENT = "notification.sent"
