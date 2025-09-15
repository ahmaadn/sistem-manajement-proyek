from typing import Literal

from app.core.domain.event import EventType
from app.schemas.base import BaseSchema

# -----------------------------------------------------------------
# Schemas for Task Audit Events
# -----------------------------------------------------------------


class TaskStatusChangeAuditSchema(BaseSchema):
    old_status: str
    new_status: str


class TaskTitleChangeAuditSchema(BaseSchema):
    before: str
    after: str


class TaskAssignAddedAuditSchama(BaseSchema):
    assignee_id: str
    assignee_name: str


class TaskAssignRemovedAuditSchama(BaseSchema):
    assignee_id: str
    assignee_name: str


type TaskAuditListSchema = (
    TaskAuditSchema
    | TaskStatusChangeAuditSchema
    | TaskTitleChangeAuditSchema
    | TaskAssignAddedAuditSchama
    | TaskAssignRemovedAuditSchama
)

type TaskActionType = Literal[
    EventType.TASK_STATUS_CHANGED,
    EventType.TASK_TITLE_CHANGED,
    EventType.TASK_ASSIGNED_ADDED,
    EventType.TASK_ASSIGNED_REMOVED,
]


class TaskAuditSchema(BaseSchema):
    task_id: str
    create_at: str
    action_type: TaskActionType
    details: TaskAuditListSchema


# [
#     {
#         'type': 'event',
#         'data': ''
#     },
#     {
#         'type': 'comment',
#         'data': ''
#     }
# ]
