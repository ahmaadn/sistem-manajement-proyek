from app.core.domain.bus import subscribe
from app.core.domain.events.project import ProjectCreatedEvent
from app.core.domain.handlers.project_audit_handlers import on_create_project


def register_event_handlers():
    subscribe(ProjectCreatedEvent, on_create_project)
