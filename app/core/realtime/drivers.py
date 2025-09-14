from __future__ import annotations

from typing import Any, Iterable, Optional, Protocol, Set

import pusher
from fastapi import APIRouter, FastAPI, Request
from fastapi.templating import Jinja2Templates

from app.core.config.pusher import get_pusher_config
from app.core.config.settings import get_settings
from app.templates import templates


class RealtimeDriver(Protocol):
    name: str

    def get_router(self) -> Optional[APIRouter]: ...

    async def send_to_user(self, user_id: int, message: dict) -> None: ...

    async def send_to_users(
        self, user_ids: Iterable[int], message: dict
    ) -> None: ...

    async def broadcast_project(
        self,
        project_id: int,
        message: dict,
        exclude_user_ids: Set[int] | None = None,
    ) -> None: ...


class SSEDriver:
    name = "sse"

    def get_router(self) -> Optional[APIRouter]:
        # Import in-function untuk hindari import siklik saat driver tak dipakai
        from app.sse import router

        return router

    async def send_to_user(self, user_id: int, message: dict) -> None:
        from app.core.realtime.sse_manager import sse_manager

        # Konversi message menjadi event/data yang dipakai SSE
        event = message.get("type", "message")
        data: dict[str, Any] = message.get("data", {})
        await sse_manager.send_to_user(user_id, event, data)

    async def send_to_users(self, user_ids: Iterable[int], message: dict) -> None:
        from app.core.realtime.sse_manager import sse_manager

        event = message.get("type", "message")
        data: dict[str, Any] = message.get("data", {})
        await sse_manager.send_to_users(user_ids, event, data)

    async def broadcast_project(
        self,
        project_id: int,
        message: dict,
        exclude_user_ids: Set[int] | None = None,
    ) -> None:
        from app.core.realtime.sse_manager import sse_manager

        event = message.get("type", "message")
        data: dict[str, Any] = message.get("data", {})
        await sse_manager.broadcast_project(
            project_id, event, data, exclude_user_ids=exclude_user_ids or set()
        )


class WebSocketDriver:
    name = "websocket"

    def get_router(self) -> Optional[APIRouter]:
        from app.websocket import router

        return router

    async def _manager(self):
        from app.websocket import get_manager

        return get_manager()

    async def send_to_user(self, user_id: int, message: dict) -> None:
        manager = await self._manager()
        await manager.send_to_user(user_id, message)

    async def send_to_users(self, user_ids: Iterable[int], message: dict) -> None:
        manager = await self._manager()
        await manager.send_to_users(user_ids, message)

    async def broadcast_project(
        self,
        project_id: int,
        message: dict,
        exclude_user_ids: Set[int] | None = None,
    ) -> None:
        manager = await self._manager()
        if exclude_user_ids:
            await manager.broadcast_project_excluding(
                project_id, message, exclude_user_ids
            )
        else:
            await manager.broadcast_project(project_id, message)


class PusherDriver:
    name = "pusher"

    def __init__(self) -> None:
        cfg = get_pusher_config()
        self._client = pusher.Pusher(
            app_id=cfg.PUSHER_APP_ID,
            key=cfg.PUSHER_KEY,
            secret=cfg.PUSHER_SECRET,
            cluster=cfg.PUSHER_CLUSTER,
            ssl=cfg.PUSHER_SSL,
        )

    def get_router(self) -> Optional[APIRouter]:
        """Sediakan endpoint test sederhana untuk Pusher (opsional)."""
        cfg = get_pusher_config()
        if not cfg.PUSHER_TEST_ENABLE:
            return None

        router = APIRouter(tags=["Pusher"])

        path = cfg.PUSHER_TEST_PATH or "/test/pusher/user/{user_id}"
        if "{user_id}" not in path:
            path = "/test/pusher/user/{user_id}"

        @router.get(path)
        async def test_pusher_page(request: Request, user_id: int):
            """Webpage sederhana untuk mengetes Pusher."""
            ctx = {
                "request": request,
                "pusher_key": cfg.PUSHER_KEY,
                "pusher_cluster": cfg.PUSHER_CLUSTER,
                "user_id": user_id,
            }
            template_name = cfg.PUSHER_TEMPLATE_NAME or "pusher_test_notify.html"
            # Use configured template directory when provided; fallback to default
            if (
                cfg.PUSHER_TEMPLATE_DIR
                and cfg.PUSHER_TEMPLATE_DIR != "app/templates"
            ):
                local_templates = Jinja2Templates(directory=cfg.PUSHER_TEMPLATE_DIR)
                return local_templates.TemplateResponse(template_name, ctx)
            return templates.TemplateResponse(template_name, ctx)

        return router

    async def send_to_user(self, user_id: int, message: dict) -> None:
        """
        Mengirim ke channel private milik satu user.
        Channel: 'user-123'
        """
        channel_name = f"user-{user_id}"

        event_name = message.get("type", "message")
        data = message.get("data", {})

        self._client.trigger(channel_name, event_name, data)

    async def send_to_users(self, user_ids: Iterable[int], message: dict) -> None:
        """
        Mengirim ke banyak user. Pusher mendukung 'batch triggering' untuk efisiensi.
        """
        event_name = message.get("type", "message")
        data = message.get("data", {})

        # Buat batch event
        batch_data = []
        for user_id in user_ids:
            batch_data.append(
                {
                    "channel": f"user-{user_id}",
                    "name": event_name,
                    "data": data,
                }
            )

        if batch_data:
            self._client.trigger_batch(batch_data)

    async def broadcast_project(
        self,
        project_id: int,
        message: dict,
        exclude_user_ids: Set[int] | None = None,
    ) -> None:
        """
        Menyiarkan ke channel project.
        Channel: 'presence-project-456'
        Pusher tidak mendukung eksklusi user secara langsung di backend.
        Eksklusi paling umum adalah untuk tidak mengirim notifikasi kembali ke user
        yang memicu event. Ini ditangani dengan 'socket_id'.
        """
        channel_name = f"presence-project-{project_id}"
        event_name = message.get("type", "message")
        data = message.get("data", {})

        # Ambil socket_id dari data jika ada, untuk mengecualikan pengirim.
        # Frontend HARUS mengirim 'socket_id' saat melakukan aksi
        # (misal: via header).
        socket_id_to_exclude = data.pop("socket_id", None)

        self._client.trigger(
            channel_name,
            event_name,
            data,
            socket_id=socket_id_to_exclude,  # Parameter untuk eksklusi
        )


_DRIVERS: list[RealtimeDriver] | None = None


def get_active_drivers() -> list[RealtimeDriver]:
    global _DRIVERS
    if _DRIVERS is not None:
        return _DRIVERS

    enabled = get_settings().get_enabled_drivers()
    drivers: list[RealtimeDriver] = []
    if "websocket" in enabled:
        drivers.append(WebSocketDriver())
    if "sse" in enabled:
        drivers.append(SSEDriver())
    if "pusher" in enabled:
        drivers.append(PusherDriver())

    _DRIVERS = drivers
    return drivers


def include_realtime_routers(app: FastAPI) -> None:
    """
    Sertakan hanya router milik driver yang aktif. Jika hanya pusher, maka tidak ada
    endpoint WS/SSE yang didaftarkan.
    """
    for d in get_active_drivers():
        router = d.get_router()
        if router is not None:
            app.include_router(router)
