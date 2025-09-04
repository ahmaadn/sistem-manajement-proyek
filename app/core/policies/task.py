from typing import Any

from app.utils import exceptions


def _name(v: Any) -> str:
    return getattr(v, "name", str(v)).upper()


ALLOWED_TASK_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"TODO", "CANCELLED"},
    "TODO": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"BLOCKED", "DONE", "CANCELLED"},
    "BLOCKED": {"IN_PROGRESS", "CANCELLED"},
    "DONE": set(),
    "CANCELLED": set(),
}


# def ensure_task_status_transition(current_status: Any, target_status: Any) -> None:
#     cur = _name(current_status)
#     target = _name(target_status)
#     allowed = ALLOWED_TASK_STATUS_TRANSITIONS.get(cur)
#     if allowed is None or target not in allowed:
#         raise exceptions.InvalidStatusTransitionError(
#             f"Transisi status task {cur} -> {target} tidak diizinkan."
#         )


def ensure_only_assignee_can_change_status(
    *, task_assignee_user_ids: list[int], actor_user_id: int
) -> None:
    """Memastikan bahwa hanya penugasan tugas yang dapat mengubah status.

    Args:
        task_assignee_user_ids (list[int]): Daftar ID pengguna yang ditugaskan
            pada tugas.
        actor_user_id (int): ID pengguna yang mencoba mengubah status tugas.

    Raises:
        exceptions.ForbiddenError: Jika pengguna tidak memiliki izin untuk
            mengubah status tugas.
    """
    if actor_user_id not in task_assignee_user_ids:
        raise exceptions.ForbiddenError


def ensure_assignee_is_project_member(
    *, project_member_user_ids: list[int], target_user_id: int
) -> None:
    """Memastikan bahwa penugasan tugas adalah anggota proyek.

    Args:
        project_member_user_ids (list[int]): Daftar ID pengguna anggota proyek.
        target_user_id (int): ID pengguna yang akan ditugaskan.

    Raises:
        exceptions.UserNotInProjectError: Jika pengguna tidak terdaftar di proyek.
    """

    if target_user_id not in project_member_user_ids:
        raise exceptions.UserNotInProjectError
