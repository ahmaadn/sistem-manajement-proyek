from app.core.events.audit_events import ProjectCreatedEvent
from app.core.events.bus import subscribe
from app.core.events.handlers.project_audit_handlers import on_create_project


def register_event_handlers():
    subscribe(ProjectCreatedEvent, on_create_project)
