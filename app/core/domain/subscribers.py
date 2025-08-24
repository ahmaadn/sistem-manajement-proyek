from app.core.domain.bus import subscribe
from app.core.domain.events.project import ProjectCreatedEvent
from app.core.domain.handlers.project_audit_handlers import on_create_project
from app.core.domain.handlers.project_member_handler import (
    register_event_handlers as register_project_member_handlers,
)


def register_event_handlers():
    subscribe(ProjectCreatedEvent, on_create_project)
    register_project_member_handlers()
