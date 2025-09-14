from __future__ import annotations

import asyncio
from typing import Any, Iterable, Set

from .drivers import get_active_drivers


async def send_to_user(user_id: int, type_: str, data: dict[str, Any]) -> None:
    message = {"type": type_, "data": data}

    await asyncio.gather(
        *[d.send_to_user(user_id, message) for d in get_active_drivers()]
    )


async def send_to_users(
    user_ids: Iterable[int], type_: str, data: dict[str, Any]
) -> None:
    message = {"type": type_, "data": data}
    await asyncio.gather(
        *[d.send_to_users(user_ids, message) for d in get_active_drivers()]
    )


async def broadcast_project(
    project_id: int,
    type_: str,
    data: dict[str, Any],
    exclude_user_ids: Set[int] | None = None,
) -> None:
    message = {"type": type_, "data": data}

    await asyncio.gather(
        *[
            d.broadcast_project(
                project_id, message, exclude_user_ids=exclude_user_ids or set()
            )
            for d in get_active_drivers()
        ]
    )
