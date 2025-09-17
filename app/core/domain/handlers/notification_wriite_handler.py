import logging
from typing import Iterable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification_model import Notification, NotificationType

logger = logging.getLogger(__name__)


def _normalize_recipients(recipients: Iterable[int], actor_id: int) -> list[int]:
    # unik, buang None/0/negatif, dan jangan kirim ke diri sendiri
    uniq = {int(r) for r in recipients if r is not None and int(r) > 0}
    uniq.discard(int(actor_id))
    return list(uniq)


async def write_notifications(
    *,
    recipients: Sequence[int],
    actor_id: int,
    message: str,
    notif_type: NotificationType | str,
    project_id: int | None = None,
    task_id: int | None = None,
    session: AsyncSession,
    send_to_me: bool = True,
) -> list[Notification]:
    """
    Tulis notifikasi ke banyak penerima.
    Returns: jumlah notifikasi yang berhasil dibuat.
    """
    if not send_to_me:
        recips = _normalize_recipients(recipients, actor_id)
    else:
        recips = list({int(r) for r in recipients if r is not None and int(r) > 0})
    if not recips:
        return []

    msg = (message or "").strip()
    ntype = str(notif_type)

    notifications = [
        Notification(
            recipient_id=rid,
            actor_id=actor_id,
            project_id=project_id,
            task_id=task_id,
            type=ntype,
            message=msg,
        )
        for rid in recips
    ]

    # Simpan batc
    session.add_all(notifications)

    # Flush untuk memastikan insert dieksekusi sebelum keluar context
    await session.flush()

    logger.debug(
        (
            "Created %d notifications (type=%s) for recipients=%s project_id=%s "
            "task_id=%s by actor=%s"
        ),
        len(notifications),
        ntype,
        recips,
        project_id,
        task_id,
        actor_id,
    )
    return notifications
