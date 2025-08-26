from app.core.domain.handlers.audits.assignee_task_handlers import (
    register_event_handlers as register_assignee_task_handlers,
)
from app.core.domain.handlers.audits.project_audit_handlers import (
    register_event_handlers as register_project_audit_handlers,
)
from app.core.domain.handlers.audits.project_member_handler import (
    register_event_handlers as register_project_member_handlers,
)
from app.core.domain.handlers.audits.task_audit_handlers import (
    register_event_handlers as register_task_audit_handlers,
)
from app.core.domain.handlers.audits.user_handlers import (
    register_event_handlers as register_user_handlers,
)


def register_event_handlers():
    register_project_audit_handlers()
    register_project_member_handlers()
    register_task_audit_handlers()
    register_assignee_task_handlers()
    register_user_handlers()
