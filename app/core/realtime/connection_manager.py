import datetime as dt
import json
import logging
from asyncio import Lock
from collections import defaultdict
from typing import Any, Dict, Iterable, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        # user_id -> set(WebSocket)
        # 1 user dapat memiliki banyak websocket hal, ini bisa terjadi dikarenakan
        # user melakukan koneksi dari beberapa tab atau perangkat
        self._user_sockets: Dict[int, Set[WebSocket]] = defaultdict(set)

        # project_id -> set(WebSocket)
        # 1 project dapat memiliki banyak websocket, hal ini bisa terjadi dikarenakan
        # beberapa user dapat terhubung ke project yang sama
        self._project_rooms: Dict[int, Set[WebSocket]] = defaultdict(set)

        # socket -> user_id
        # 1 socket hanya dapat terhubung ke 1 user
        self._socket_to_user: Dict[WebSocket, int] = {}

        self._lock = Lock()

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        """Terima koneksi WebSocket dan daftarkan ke user."""
        await websocket.accept()

        async with self._lock:
            self._socket_to_user[websocket] = user_id
            self._user_sockets.setdefault(user_id, set()).add(websocket)

            logger.info(
                "User %s connected. Active sockets for user=%d",
                user_id,
                len(self._user_sockets[user_id]),
            )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Bersihkan socket dari semua struktur (tanpa asumsi project)."""
        user_id = self._socket_to_user.pop(websocket, None)

        if user_id is not None:
            # Hapus socket dari daftar socket milik user
            sockets = self._user_sockets.get(user_id)
            if sockets is not None:
                sockets.discard(websocket)

                # Jika tidak ada socket yang tersisa, hapus user dari daftar
                if not sockets:
                    self._user_sockets.pop(user_id, None)

        # Hapus socket dari semua room project
        for project_id, room in list(self._project_rooms.items()):
            # Hapus socket dari semua room project
            if websocket in room:
                room.discard(websocket)

                # Jika tidak ada socket yang tersisa, hapus room dari daftar
                if not room:
                    self._project_rooms.pop(project_id, None)

        # Tutup socket jika masih open
        try:
            if websocket.application_state != WebSocketState.DISCONNECTED:
                await websocket.close()
        except Exception:
            pass

        if user_id is not None:
            logger.info("Socket disconnected for user %s", user_id)
        else:
            logger.info("Socket disconnected (unknown user)")

    def subscribe_project(self, websocket: WebSocket, project_id: int) -> None:
        """Tambahkan socket ini ke room project tertentu."""
        self._project_rooms[project_id].add(websocket)
        uid = self._socket_to_user.get(websocket)

        logger.info("User %s subscribed to project %s", uid, project_id)

    def unsubscribe_project(self, websocket: WebSocket, project_id: int) -> None:
        """Lepas socket dari room project tertentu."""
        room = self._project_rooms.get(project_id)
        if room:
            room.discard(websocket)
            if not room:
                self._project_rooms.pop(project_id, None)
        uid = self._socket_to_user.get(websocket)

        logger.info("User %s unsubscribed from project %s", uid, project_id)

    async def send_to_user(self, user_id: int, message: dict) -> None:
        """Kirim pesan ke semua socket milik 1 user."""
        payload = self._encode(message)
        sockets = list(self._user_sockets.get(user_id, []))
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                # Jika gagal kirim, anggap socket rusak dan bersihkan
                await self.disconnect(ws)

    async def send_to_users(self, user_ids: Iterable[int], message: dict) -> None:
        """Kirim pesan ke banyak user (deduplikasi socket otomatis per user)."""
        for uid in user_ids:
            await self.send_to_user(uid, message)

    async def broadcast_project(self, project_id: int, message: dict) -> None:
        """Kirim pesan ke semua socket yang subscribe ke project."""
        payload = self._encode(message)
        sockets = list(self._project_rooms.get(project_id, []))
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                await self.disconnect(ws)

    async def broadcast_project_excluding(
        self,
        project_id: int,
        message: dict,
        exclude_user_ids: Set[int] | None = None,
    ) -> None:
        """Kirim ke semua socket di room project, kecuali user tertentu."""
        exclude = exclude_user_ids or set()
        sockets = list(self._project_rooms.get(project_id, []))
        for ws in sockets:
            uid = self._socket_to_user.get(ws)
            if uid in exclude:
                continue
            try:
                payload = self._encode(message)
                await ws.send_json(payload)
            except Exception:
                await self.disconnect(ws)

    def sockets_count_for_user(self, user_id: int) -> int:
        return len(self._user_sockets.get(user_id, []))

    def room_size(self, project_id: int) -> int:
        return len(self._project_rooms.get(project_id, []))

    def _encode(self, message: Dict[str, Any]) -> str:
        # standar payload
        base = {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat() + "Z",
            **message,
        }
        return json.dumps(base)


def get_manager() -> ConnectionManager:
    """Mendapatkan instance ConnectionManager.

    Returns:
        ConnectionManager: Instance dari ConnectionManager.
    """
    print("get_manager called")
    if not hasattr(get_manager, "_instance"):
        get_manager.instance = ConnectionManager()  # type: ignore[reportFunctionMemberAccess]

    return get_manager.instance  # type: ignore[reportFunctionMemberAccess]
