from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Set

from app.core.realtime.connection_manager import ConnectionManager, get_manager


def _envelope(type_: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": type_,
        "data": data,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


class NotificationService:
    def __init__(self, manager: ConnectionManager) -> None:
        self.manager = manager

    async def notify_user(
        self, user_id: int, type_: str, data: dict[str, Any]
    ) -> None:
        await self.manager.send_to_user(user_id, _envelope(type_, data))

    async def notify_users(
        self, user_ids: Iterable[int], type_: str, data: dict[str, Any]
    ) -> None:
        for uid in user_ids:
            await self.notify_user(uid, type_, data)

    async def notify_project(
        self,
        project_id: int,
        type_: str,
        data: dict[str, Any],
        exclude_user_ids: Set[int] | None = None,
    ) -> None:
        payload = _envelope(type_, {**data, "project_id": project_id})
        if exclude_user_ids:
            await self.manager.broadcast_project_excluding(
                project_id, payload, exclude_user_ids
            )
        else:
            await self.manager.broadcast_project(project_id, payload)


def get_notification_service() -> NotificationService:
    """Mendapatkan instance NotificationService.

    Returns:
        NotificationService: Instance dari NotificationService.
    """
    if not hasattr(get_notification_service, "_instance"):
        get_notification_service._instance = NotificationService(get_manager())  # type: ignore[reportFunctionMemberAccess]  # noqa: SLF001

    return get_notification_service._instance  # type: ignore[reportFunctionMemberAccess]  # noqa: SLF001
