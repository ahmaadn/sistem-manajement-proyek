from datetime import datetime

from app.db.models.project_model import StatusProject
from app.db.models.role_model import Role
from app.schemas.user import User
from app.utils import exceptions

ALLOWED_STATUS_PROJECT_NON_PM_ADMIN = {StatusProject.ACTIVE, StatusProject.COMPLETED}
MIN_YEAR = 1970
MAX_YEAR = 9999


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

    errors: dict[str, list[str]] = {}
    # validasi range tahun
    if not (MIN_YEAR <= norm_start <= MAX_YEAR):
        errors.setdefault("start_year", []).append(
            f"start_year harus antara {MIN_YEAR} dan {MAX_YEAR}"
        )
    if not (MIN_YEAR <= norm_end <= MAX_YEAR):
        errors.setdefault("end_year", []).append(
            f"end_year harus antara {MIN_YEAR} dan {MAX_YEAR}"
        )

    # jika ingin menolak end_year > current_year, uncomment bagian ini
    # validassi tahun akhir tidak boleh melebihi tahun berjalan
    # if norm_end > current_year:
    #     errors.setdefault("end_year", []).append(
    #         f"end_year tidak boleh melebihi {current_year}"
    #     )

    # validasi tahun awal tidak boleh lebih besar dari tahun akhir
    if norm_start > norm_end:
        errors.setdefault("start_year", []).append("start_year harus <= end_year")

    # trow error jika ada validasi yang gagal
    if errors:
        raise exceptions.ValidationError("Rentang tahun tidak valid.", errors=errors)

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
