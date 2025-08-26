from app.core.domain.handlers.assignee_task_handlers import (
    register_event_handlers as register_assignee_task_handlers,
)
from app.core.domain.handlers.project_audit_handlers import (
    register_event_handlers as register_project_audit_handlers,
)
from app.core.domain.handlers.project_member_handler import (
    register_event_handlers as register_project_member_handlers,
)
from app.core.domain.handlers.task_audit_handlers import (
    register_event_handlers as register_task_audit_handlers,
)


def register_event_handlers():
    register_project_audit_handlers()
    register_project_member_handlers()
    register_task_audit_handlers()
    register_assignee_task_handlers()
