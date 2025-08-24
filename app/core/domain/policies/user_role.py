from app.db.models.role_model import Role

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
