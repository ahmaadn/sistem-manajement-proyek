from app.core.domain.events.project import ProjectCreatedEvent
from app.core.domain.handlers.audit_handlers import write_audit
from app.db.models.audit_model import AuditEventType


async def on_create_project(ev: ProjectCreatedEvent):
    await write_audit(
        action_type=AuditEventType.PROJECT_CREATED,
        performed_by=ev.user_id,
        project_id=ev.project_id,
        details={"project_name": ev.project_name},
    )
    print(f"[INFO] Audit log created for project creation: {ev.project_name}")
