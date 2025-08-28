from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, DefaultDict, Dict, Iterable, Set

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class SseSubscriber:
    user_id: int
    projects: Set[int] = field(default_factory=set)
    queue: asyncio.Queue[dict] = field(
        default_factory=lambda: asyncio.Queue(maxsize=256)
    )

    # Gunakan identity hash agar bisa disimpan di set
    __hash__ = object.__hash__


class SseManager:
    """Sederhana: simpan subscriber per-user dan per-project, kirim via queue."""

    def __init__(self) -> None:
        self._user_subs: DefaultDict[int, Set[SseSubscriber]] = defaultdict(set)
        self._project_subs: DefaultDict[int, Set[SseSubscriber]] = defaultdict(set)
        self._all_subs: Set[SseSubscriber] = set()
        self._lock = asyncio.Lock()

    async def subscribe(
        self, user_id: int, projects: Iterable[int] | None = None
    ) -> SseSubscriber:
        """Subscribe a user to SSE events.

        Args:
            user_id (int): The ID of the user to subscribe.
            projects (Iterable[int] | None, optional): The IDs of the projects to subscribe to. Defaults to None.

        Returns:
            SseSubscriber: The created subscriber.
        """
        subs_projects = set(projects or [])
        sub = SseSubscriber(user_id=user_id, projects=subs_projects)

        logger.info(f"User {user_id} subscribed to projects: {subs_projects}")

        async with self._lock:
            self._all_subs.add(sub)
            self._user_subs[user_id].add(sub)
            for pid in subs_projects:
                self._project_subs[pid].add(sub)

        # Beri salam awal agar klien tahu koneksi OK
        await self._enqueue(
            sub, "ready", {"user_id": user_id, "projects": list(subs_projects)}
        )

        return sub

    async def unsubscribe(self, sub: SseSubscriber) -> None:
        """
        Unsubscribe a user from SSE events.

        Args:
            sub (SseSubscriber): The subscriber to unsubscribe.
        """

        async with self._lock:
            self._all_subs.discard(sub)
            self._user_subs[sub.user_id].discard(sub)
            for pid in list(sub.projects):
                self._project_subs[pid].discard(sub)

    async def send_to_user(
        self, user_id: int, event: str, data: Dict[str, Any]
    ) -> None:
        """Send an SSE event to a specific user.

        Args:
            user_id (int): The ID of the user to send the event to.
            event (str): The name of the event.
            data (Dict[str, Any]): The data to include in the event.
        """
        subs = list(self._user_subs.get(user_id, []))
        for sub in subs:
            await self._enqueue(sub, event, data)

    async def send_to_users(
        self, user_ids: Iterable[int], event: str, data: Dict[str, Any]
    ) -> None:
        for uid in user_ids:
            await self.send_to_user(uid, event, data)

    async def broadcast_project(
        self,
        project_id: int,
        event: str,
        data: Dict[str, Any],
        exclude_user_ids: Set[int] | None = None,
    ) -> None:
        """Broadcast an SSE event to all subscribers of a project.

        Args:
            project_id (int): The ID of the project to broadcast the event to.
            event (str): The name of the event.
            data (Dict[str, Any]): The data to include in the event.
            exclude_user_ids (Set[int] | None, optional): The user IDs to exclude
                from the broadcast. Defaults to None.
        """
        exclude = exclude_user_ids or set()
        subs = list(self._project_subs.get(project_id, []))
        for sub in subs:
            if sub.user_id in exclude:
                continue
            await self._enqueue(sub, event, data)

    async def _enqueue(
        self, sub: SseSubscriber, event: str, data: Dict[str, Any]
    ) -> None:
        """Enqueue an SSE event for a subscriber.

        Args:
            sub (SseSubscriber): The subscriber to send the event to.
            event (str): The name of the event.
            data (Dict[str, Any]): The data to include in the event.
        """
        msg = {"event": event, "data": data}
        try:
            sub.queue.put_nowait(msg)
        except asyncio.QueueFull:
            # Jaga agar tidak menggantung; drop jika penuh
            _ = sub.queue.get_nowait()
            sub.queue.put_nowait(msg)


sse_manager = SseManager()
