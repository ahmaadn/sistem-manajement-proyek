import logging

from app.api.dependencies.sessions import async_session_maker
from app.db.models.audit_model import AuditEventType, AuditLog

logger = logging.getLogger(__name__)


async def write_audit(
    action_type: AuditEventType,
    performed_by: int | None = None,
    project_id: int | None = None,
    task_id: int | None = None,
    details: dict | None = None,
):
    async with async_session_maker() as session:  # transaksi terpisah (post-commit)
        audit = AuditLog(
            user_id=performed_by,
            project_id=project_id,
            task_id=task_id,
            action_type=action_type,
            detail=details or {},
        )
        session.add(audit)
        await session.commit()

        # Logging
        logger.info(
            "audit.log",
            extra={
                "action": action_type,
                "user_id": performed_by,
                "project_id": project_id,
                "task_id": task_id,
                "details": details,
            },
        )
