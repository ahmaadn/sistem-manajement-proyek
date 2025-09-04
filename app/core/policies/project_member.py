from typing import TYPE_CHECKING, Any

from app.utils import exceptions

if TYPE_CHECKING:
    from app.db.models.project_member_model import RoleProject
    from app.db.models.role_model import Role


def _name(v: Any) -> str:
    """Mengambil nama dari objek atau mengonversi objek menjadi string.

    Args:
        v (Any): Objek yang akan diambil namanya.

    Returns:
        str: Nama objek dalam huruf kapital.
    """
    return getattr(v, "name", str(v)).upper()


def ensure_can_assign_member_role(
    member_system_role: "Role", desired_project_role: "RoleProject"
) -> None:
    """
    Memastikan bahwa pengguna dapat diberikan peran anggota proyek yang diinginkan.
    """
    actor = _name(member_system_role)
    desired = _name(desired_project_role)
    if actor in ("ADMIN", "PROJECT_MANAGER") and desired != "OWNER":
        raise exceptions.InvalidRoleAssignmentError(
            "admin dan manager hanya bisa menjadi owner."
        )
    if actor == "TEAM_MEMBER" and desired == "OWNER":
        raise exceptions.InvalidRoleAssignmentError(
            "Member tidak dapat diangkat menjadi owner."
        )


def ensure_actor_can_remove_member(
    project_owner_id: int, actor_user_id: int, target_user_id: int
) -> None:
    """
    Memastikan bahwa pengguna dapat dihapus dari proyek.
    """
    # larang hapus diri sendiri dan pemilik proyek
    if target_user_id in (actor_user_id, project_owner_id):
        raise exceptions.CannotRemoveMemberError


def ensure_can_change_member_role(
    member_system_role: Any,
    *,
    target_user_id: int,
    project_owner_id: int,
    actor_user_id: int,
    new_role: "RoleProject",
    current_role: "RoleProject",
) -> None:
    """
    Memastikan bahwa pengguna dapat mengubah peran anggota proyek.
    """

    # larang ubah role owner dan role diri sendiri
    if target_user_id in (project_owner_id, actor_user_id):
        raise exceptions.CannotChangeRoleError
    # jika tidak berubah, oke
    if _name(current_role) == _name(new_role):
        return
    # validasi aturan penugasan role
    ensure_can_assign_member_role(member_system_role, new_role)
