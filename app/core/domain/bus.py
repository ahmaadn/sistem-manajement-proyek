from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from contextvars import ContextVar
from enum import StrEnum
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    DefaultDict,
    List,
    Type,
    TypeVar,
)

from fastapi import BackgroundTasks

from app.core.domain.event import DomainEvent

logger = logging.getLogger(__name__)


# ContextVar untuk menyimpan BackgroundTasks saat ada request FastAPI aktif
_BG_TASKS_VAR: ContextVar[BackgroundTasks | None] = ContextVar(
    "event_bg_tasks", default=None
)


def set_event_background(bg_tasks: BackgroundTasks | None) -> None:
    """
    Set BackgroundTasks aktif untuk request saat ini.
    - bg_tasks diharapkan objek fastapi.BackgroundTasks (punya .add_task(fn, *args))
    """
    _BG_TASKS_VAR.set(bg_tasks)


def get_event_background() -> BackgroundTasks | None:
    """
    Get BackgroundTasks aktif untuk request saat ini.
    """
    return _BG_TASKS_VAR.get()


T_contra = TypeVar("T_contra", bound=DomainEvent, contravariant=True)

Handler = (
    Callable[[T_contra], Awaitable[None]]
    | Callable[[T_contra], Coroutine[Any, Any, None]]
)


class HandlerMode(StrEnum):
    IMMEDIATE = "immediate"
    BACKGROUND = "background"


class EventBus:
    """
    EventBus adalah utilitas sederhana untuk membangun arsitektur event-driven dengan
    pola publish-subscribe. Kelas ini menyimpan peta tipe event ke daftar handler dan
    menjalankan handler secara konkuren menggunakan asyncio.
    """

    def __init__(self) -> None:
        self._handlers: DefaultDict[
            Type[DomainEvent], List[tuple[Handler, HandlerMode]]
        ] = defaultdict(list)

    def subscribe(self, event_type: Type[DomainEvent], handler: Handler) -> None:
        self._handlers[event_type].append((handler, HandlerMode.IMMEDIATE))

        logger.info(
            "event.subscribe immediate %s -> %s",
            event_type.__name__,
            getattr(handler, "__name__", str(handler)),
        )

    def subscribe_background(
        self, event_type: Type[DomainEvent], handler: Handler
    ) -> None:
        # daftar sebagai handler background
        self._handlers[event_type].append((handler, HandlerMode.BACKGROUND))
        logger.debug(
            "event.subscribe background %s -> %s",
            event_type.__name__,
            getattr(handler, "__name__", str(handler)),
        )

    async def publish(self, event: DomainEvent) -> None:
        pairs = self._handlers.get(type(event), [])
        if not pairs:
            logger.debug("event.no_handlers", extra={"event": event.name})
            return

        # Pisahkan immediate vs background
        immediate: list[Handler] = []
        background: list[Handler] = []
        for h, mode in pairs:
            if mode is HandlerMode.IMMEDIATE:
                immediate.append(h)
            elif mode is HandlerMode.BACKGROUND:
                background.append(h)
            logger.debug(
                "event.publish",
                extra={
                    "event": event.name,
                    "handler": getattr(h, "__name__", str(h)),
                    "mode": mode,
                },
            )

        # Jalankan immediate secara konkuren dan ditunggu selesai
        if immediate:
            await asyncio.gather(
                *(h(event) for h in immediate), return_exceptions=False
            )

        # Jadwalkan background: pakai FastAPI BackgroundTasks jika ada, kalau tidak
        # fallback ke asyncio.create_task
        if background:
            # background_handlers digunakan untuk menyimpan referensi tugas
            # latar belakang
            background_handlers = set()

            bg_tasks = _BG_TASKS_VAR.get()
            for h in background:
                # FastAPI BackgroundTasks  jika ada
                if bg_tasks is not None and hasattr(bg_tasks, "add_task"):
                    bg_tasks.add_task(h, event)

                else:
                    logger.debug("Using asyncio.create_task for background handler")
                    # fallback: lepas ke event loop
                    task = asyncio.create_task(h(event))  # type: ignore

                    # Tambahkan ke set background_handlers untuk
                    # menciptakan referensi yang kuat.
                    background_handlers.add(task)

                    # Untuk mencegah penyimpanan referensi ke tugas yang telah
                    # selesai selamanya, buat setiap tugas menghapus referensinya
                    # sendiri dari kumpulan setelah selesai:
                    task.add_done_callback(background_handlers.discard)


PENDING_EVENT = []
_event_bus = EventBus()
subscribe = _event_bus.subscribe
subscribe_background = _event_bus.subscribe_background
publish = _event_bus.publish


def enqueue_event(event: DomainEvent) -> None:
    """Entri sebuah event untuk diproses nanti.

    Args:
        session (AsyncSession): Sesi database.
        event (DomainEvent): Event yang akan dimasukkan dalam antrean.
    """
    PENDING_EVENT.append(event)
    logger.info("Event enqueued: %s", event.__class__.__name__)


async def dispatch_pending_events() -> None:
    """
    Menjalankan event yang tertunda.

    Args:
        session (AsyncSession): Sesi database.
    """
    for ev in PENDING_EVENT:
        try:
            await publish(ev)
        except Exception:
            logger.exception("event.handler.error", extra={"event": ev.name})

    PENDING_EVENT.clear()
