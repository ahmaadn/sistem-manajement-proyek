from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from app.core.realtime.sse_manager import SseSubscriber, sse_manager


class SseTestPayload(BaseModel):
    event: str = "test"
    data: Dict[str, Any] = {}
    user_id: Optional[int] = None
    users: Optional[List[int]] = None
    project_id: Optional[int] = None
    exclude_user_ids: Optional[List[int]] = None


router = APIRouter()


def _format_sse(event: str, data: Any) -> bytes:
    # Format SSE: event: <type>\n data: <json>\n\n
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


@router.get("/sse", tags=["SSE"])
async def sse_stream(
    request: Request,
    user_id: int,  # TODO: ganti dengan dependency auth untuk ambil user.id dari JWT
    projects: Optional[List[int]] = Query(default=None),
):
    """
    Contoh: GET /sse?user_id=123&projects=1&projects=2
    Satu koneksi SSE per-tab. Untuk update daftar project, klien reconnect dengan
    query baru.
    """
    sub: SseSubscriber = await sse_manager.subscribe(
        user_id=user_id, projects=projects or []
    )

    async def event_generator():
        # Prelude 2KB agar proxy/CDN segera buka stream dan flush
        yield b": sse-prelude " + (b"x" * 2048) + b"\n\n"
        try:
            # Keep-alive tiap 15 detik
            while True:
                # Tunggu pesan atau timeout keepalive
                try:
                    msg = await asyncio.wait_for(sub.queue.get(), timeout=15)
                    yield _format_sse(msg["event"], msg["data"])
                except asyncio.TimeoutError:
                    yield b": keep-alive\n\n"  # komentar SSE (tidak diproses klien)
                # Stop jika klien menutup koneksi
                if await request.is_disconnected():
                    break
        except asyncio.CancelledError:
            pass
        finally:
            await sse_manager.unsubscribe(sub)

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # untuk Nginx
        "x-vercel-ai-data-stream": "v1",  # untuk Vercel
    }
    return StreamingResponse(
        event_generator(), media_type="text/event-stream", headers=headers
    )


@router.get("/sse/info", tags=["SSE"])
async def sse_info():
    """Info singkat tentang subscriber SSE saat ini."""
    total = len(getattr(sse_manager, "_all_subs", []))
    user_map = getattr(sse_manager, "_user_subs", {}) or {}
    project_map = getattr(sse_manager, "_project_subs", {}) or {}
    return {
        "status": "ok",
        "subscribers": total,
        "users_tracked": len(user_map),
        "projects_tracked": len(project_map),
    }


@router.post("/sse/test", tags=["SSE"])
async def sse_test_send(payload: SseTestPayload):
    """Kirim event uji ke user/users atau project tertentu."""
    if payload.user_id is not None:
        await sse_manager.send_to_user(payload.user_id, payload.event, payload.data)
        return {"target": "user", "user_id": payload.user_id, "event": payload.event}
    if payload.users:
        await sse_manager.send_to_users(payload.users, payload.event, payload.data)
        return {
            "target": "users",
            "count": len(payload.users),
            "event": payload.event,
        }
    if payload.project_id is not None:
        exclude = set(payload.exclude_user_ids or [])
        await sse_manager.broadcast_project(
            payload.project_id, payload.event, payload.data, exclude_user_ids=exclude
        )
        return {
            "target": "project",
            "project_id": payload.project_id,
            "excluded": list(exclude),
            "event": payload.event,
        }
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Specify user_id, users, or project_id",
    )


@router.get(
    "/sse/test",
    tags=["SSE"],
    response_class=HTMLResponse,
)
def sse_test_page() -> str:
    """Halaman sederhana untuk uji SSE di browser."""
    return """
<!doctype html>
<html>
  <body>
    <h3>SSE Test</h3>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <input id="userId" placeholder="user_id (integer)" style="width:180px"/>
      <input id="projects" placeholder="projects (comma separated, optional)" style="width:320px"/>
      <button id="connect">Connect</button>
      <button id="disconnect">Disconnect</button>
    </div>
    <div style="margin-top:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <input id="projectId" placeholder="project_id untuk test kirim" style="width:180px"/>
      <button id="sendUser">Send Test ke User</button>
      <button id="sendProject">Send Test ke Project</button>
    </div>
    <pre id="log" style="background:#111;color:#0f0;padding:8px;min-height:180px;margin-top:8px;"></pre>
    <script>
      const logEl = document.getElementById('log');
      const log = (m) => { logEl.textContent += m + "\\n"; logEl.scrollTop = logEl.scrollHeight; };

      let es = null;

      function buildUrl() {
        const uid = document.getElementById('userId').value.trim();
        const projs = document.getElementById('projects').value.trim();
        if (!uid) { log("ERROR: user_id kosong"); return null; }
        const url = new URL('/sse', location.origin);
        url.searchParams.set('user_id', uid);
        if (projs) {
          projs.split(',').map(s => s.trim()).filter(Boolean).forEach(p => {
            url.searchParams.append('projects', p);
          });
        }
        return url.toString();
      }

      function attach(es) {
        const known = [
          'ready',
          'project.updated',
          'project.status_changed',
          'project.member_added',
          'project.member_role_changed',
          'project.test',
          'test',
          'me.added_to_project',
        ];

        es.onmessage = (e) => {
          try { log("message: " + e.data); } catch {}
        };
        known.forEach(name => {
          es.addEventListener(name, (e) => {
            log(name + ": " + e.data);
          });
        });
        es.onerror = (e) => {
          log("ERROR: SSE connection error/disconnected");
        };
      }

      document.getElementById('connect').onclick = () => {
        const url = buildUrl();
        if (!url) return;
        if (es) { es.close(); es = null; }
        log("CONNECT " + url);
        es = new EventSource(url);
        attach(es);
      };

      document.getElementById('disconnect').onclick = () => {
        if (es) { es.close(); es = null; log("CLOSED"); }
      };

      // Uji kirim event
      document.getElementById('sendUser').onclick = async () => {
        const uid = document.getElementById('userId').value.trim();
        if (!uid) { log("ERROR: user_id kosong"); return; }
        const res = await fetch('/sse/test', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ user_id: Number(uid), event: 'test', data: { msg: 'hello user ' + uid } })
        });
        log("POST /sse/test user -> " + res.status);
      };

      document.getElementById('sendProject').onclick = async () => {
        const pid = document.getElementById('projectId').value.trim();
        if (!pid) { log("ERROR: project_id kosong"); return; }
        const res = await fetch('/sse/test', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ project_id: Number(pid), event: 'project.test', data: { msg: 'hello project ' + pid } })
        });
        log("POST /sse/test project -> " + res.status);
      };
    </script>
  </body>
</html>
"""


# ...existing code...
