from fastapi import BackgroundTasks

from app.core.domain.bus import set_event_background


def inject_event_background(background_tasks: BackgroundTasks):
    """
    Dependency global per-route/per-router untuk mengaitkan BackgroundTasks
    ke EventBus. Handler yang didaftarkan sebagai background akan dipush
    ke objek ini.
    """
    set_event_background(background_tasks)
    return background_tasks
