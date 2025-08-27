import json
import logging
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import IntegrityError

from app.core.realtime.connection_manager import ConnectionManager, get_manager
from app.db.base import async_session_maker
from app.db.models.role_model import Role
from app.db.repositories.user_repository import UserSQLAlchemyRepository
from app.db.uow.sqlalchemy import SQLAlchemyUnitOfWork
from app.schemas.user import User
from app.services.pegawai_service import PegawaiService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_user_from_token(token: str, pegawai_service: PegawaiService):
    """Memvalidasi token dan mengembalikan data user."""
    try:
        pegawai_info = await pegawai_service.get_user_info_by_token(token)
        if not pegawai_info:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION, reason="Token tidak valid"
            )
    except Exception as e:
        logger.error("websocket Gagal mendapatkan user dari token: %s", e)
        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR, reason="Token tidak valid"
        ) from e

    try:
        async with async_session_maker() as session:
            uow = SQLAlchemyUnitOfWork(session)
            repo = UserSQLAlchemyRepository(session)
            user_service = UserService(
                pegawai_service=pegawai_service, uow=uow, repo=repo
            )

            user_role = await user_service.assign_role_to_user(
                pegawai_info.id, pegawai_info
            )

        return User(**pegawai_info.model_dump(), role=Role(user_role.role))

    except IntegrityError as e:
        logger.error("websotket Gagal mendapatkan user dari token: %s", e)

        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR, reason="Token tidak valid"
        ) from e
    except Exception as e:
        logger.exception("websotket Gagal mendapatkan user dari token")

        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR, reason="Token tidak valid"
        ) from e


class _DevUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


async def get_current_user_ws(
    access_token: str = Query(...),
    pegawai_service: PegawaiService = Depends(PegawaiService),
):
    """Dependency untuk otentikasi koneksi WebSocket."""
    logger.info("WebSocket access_token: %s", access_token)

    if not access_token or not access_token.strip():
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="access_token kosong"
        )

    user = await get_user_from_token(access_token, pegawai_service)
    if not user:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="Token tidak valid"
        )
    return user


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    manager: ConnectionManager = Depends(get_manager),
    user: User = Depends(get_current_user_ws),
) -> None:
    logger.info("WebSocket connection established: %s", user.id)
    if not user:
        await websocket.close(code=4401)
        return

    user_id = user.id
    await manager.connect(websocket, user_id)

    # Kirim salam awal
    await websocket.send_json(
        {"type": "welcome", "data": {"user_id": user_id, "message": "connected"}}
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg: dict[str, Any] = json.loads(raw)
            except Exception:
                await websocket.send_json(
                    {"type": "error", "data": {"message": "invalid_json"}}
                )
                continue

            action = msg.get("action")
            if action == "subscribe":
                pid = int(msg.get("project_id", 0))
                manager.subscribe_project(websocket, pid)
                await websocket.send_json(
                    {"type": "subscribed", "data": {"project_id": pid}}
                )
            elif action == "unsubscribe":
                pid = int(msg.get("project_id", 0))
                manager.unsubscribe_project(websocket, pid)
                await websocket.send_json(
                    {"type": "unsubscribed", "data": {"project_id": pid}}
                )
            elif action == "ping":
                await websocket.send_json({"type": "pong", "data": {}})
            else:
                await websocket.send_json(
                    {"type": "error", "data": {"message": "unknown_action"}}
                )

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.exception("WebSocket error: %s", e)
        await manager.disconnect(websocket)


@router.get("/ws/info", tags=["WebSocket"])
async def ws_info() -> dict[str, Any]:
    """Info cara konek ke WebSocket (muncul di Swagger)."""
    return {
        "url": "/ws",
        "query": {"access_token": "JWT dari PegawaiService"},
        "actions": {
            "subscribe": {"action": "subscribe", "project_id": 123},
            "unsubscribe": {"action": "unsubscribe", "project_id": 123},
            "ping": {"action": "ping"},
        },
        "notes": [
            "Kirim JSON via WS sesuai action di atas.",
            "Server akan push notifikasi per-user/per-project.",
        ],
    }


@router.get(
    "/ws/test",
    tags=["WebSocket"],
    # include_in_schema=False,
    response_class=HTMLResponse,
)
def ws_test() -> str:
    """Halaman sederhana untuk uji WS di browser."""
    return """
<!doctype html>
<html>
  <body>
    <h3>WS Test</h3>
    <input id="token" placeholder="access_token" style="width:320px"/>
    <button id="btn">Connect</button>
    <pre id="log" style="background:#111;color:#0f0;padding:8px;min-height:140px;"></pre>
    <script>
      const logEl = document.getElementById('log');
      const log = (m) => logEl.textContent += m + "\\n";
      document.getElementById('btn').onclick = () => {
        const t = document.getElementById('token').value.trim();
        if (!t) { log("ERROR: access_token kosong"); return; }
        const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
        const url = `${scheme}://${location.host}/ws?access_token=${encodeURIComponent(t)}`;
        log("CONNECT " + url);
        const ws = new WebSocket(url);
        ws.onopen = () => { log("OPEN"); ws.send(JSON.stringify({action:"ping"})); };
        ws.onmessage = (ev) => log("RECV: " + ev.data);
        ws.onerror = (ev) => log("ERROR: WebSocket error (cek token/URL/server)");
        ws.onclose = (ev) => log("CLOSE code=" + ev.code + " reason=" + ev.reason);
      };
    </script>
  </body>
</html>
"""
