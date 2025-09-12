from app.db.models.role_model import Role
from app.utils import exceptions

EMPLOYEE_TO_APP_ROLE = {
    "admin": Role.ADMIN,
    "hrd": Role.PROJECT_MANAGER,
    "pegawai": Role.TEAM_MEMBER,
    "team_member": Role.TEAM_MEMBER,
}


def map_employee_role_to_app_role(employee_role: str) -> Role:
    """Map role karyawan ke role aplikasi

    Args:
        employee_role (str): Role karyawan

    Returns:
        Role: Role aplikasi yang sesuai
    """
    return EMPLOYEE_TO_APP_ROLE.get(employee_role.lower(), Role.TEAM_MEMBER)


def _name(v) -> str:
    return getattr(v, "name", str(v)).upper()


def ensure_admin_not_change_own_role(
    *, actor_role, actor_id: int, target_user_id: int, new_role
) -> None:
    """
    Larang admin mengganti perannya sendiri menjadi non-ADMIN.
    """
    if (
        _name(actor_role) == "ADMIN"
        and actor_id == target_user_id
        and _name(new_role) != "ADMIN"
    ):
        raise exceptions.InvalidRoleAssignmentError(
            "Admin tidak boleh mengganti perannya sendiri."
        )


def ensure_not_demote_last_admin(
    *, current_target_role, new_role, total_admins: int
) -> None:
    """
    Larang jika target saat ini ADMIN dan akan diubah ke non-ADMIN saat dia admin
        terakhir.
    """
    if (
        _name(current_target_role) == "ADMIN"
        and _name(new_role) != "ADMIN"
        and total_admins <= 1
    ):
        raise exceptions.InvalidRoleAssignmentError(
            "Admin terakhir di sistem tidak boleh diubah."
        )
