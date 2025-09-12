from datetime import datetime

from app.db.models.project_model import StatusProject
from app.db.models.role_model import Role
from app.schemas.user import User
from app.utils import exceptions

ALLOWED_STATUS_PROJECT_NON_PM_ADMIN = {StatusProject.ACTIVE, StatusProject.COMPLETED}


def validate_status_by_role(
    *, user: User, status_project: StatusProject | None = None
) -> None:
    """Validasi status berdasarkan role.

    Args:
        user (User): Pengguna yang melakukan permintaan.
        status_project (StatusProject): Status proyek yang diminta.

    Raises:
        exceptions.ForbiddenError: Jika pengguna tidak memiliki akses ke status
        proyek.
    """
    if status_project is None:
        return

    if (
        user.role not in (Role.ADMIN, Role.PROJECT_MANAGER)
        and status_project not in ALLOWED_STATUS_PROJECT_NON_PM_ADMIN
    ):
        raise exceptions.ForbiddenError("Akses ditolak untuk status proyek ini.")


def normalize_year_range(
    *, start_year: int | None, end_year: int | None
) -> tuple[int, int]:
    """Normalisasi rentang tahun.

    Args:
        start_year (int | None): Tahun mulai.
        end_year (int | None): Tahun akhir.

    Raises:
        HTTPException: Jika end_year melebihi tahun berjalan.
        HTTPException: Jika start_year > end_year.

    Returns:
        tuple[int | None, int | None]: Rentang tahun yang dinormalisasi.
    """
    current_year = datetime.now().year

    norm_start = start_year if start_year is not None else 1970
    norm_end = end_year if end_year is not None else current_year

    if norm_end > current_year:
        raise exceptions.ValidationError(
            "end_year tidak boleh melebihi tahun berjalan.",
            errors={"end_year": [f"end_year tidak boleh melebihi {current_year}"]},
        )

    if norm_start > norm_end:
        raise exceptions.ValidationError(
            "start_year harus <= end_year",
            errors={"start_year": ["start_year harus <= end_year"]},
        )

    return norm_start, norm_end


def apply_project_list_policies(
    *,
    user: User,
    status_project: StatusProject,
    start_year: int | None,
    end_year: int | None,
) -> tuple[StatusProject, int | None, int | None]:
    """
    Wrapper yang memvalidasi status berdasarkan role dan normalisasi rentang tahun.
    """
    validate_status_by_role(user=user, status_project=status_project)
    norm_start, norm_end = normalize_year_range(
        start_year=start_year, end_year=end_year
    )
    return status_project, norm_start, norm_end
