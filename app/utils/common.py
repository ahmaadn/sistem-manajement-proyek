from enum import StrEnum, auto


class ErrorCode(StrEnum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values) -> str:
        return name.upper()

    APP_ERROR = auto()
    INTERNAL_SERVER_ERROR = auto()
    VALIDATION_ERROR = auto()
    GENERIC_NOT_FOUND = auto()
    ITEM_NOT_FOUND = auto()
    FORBIDDEN = auto()

    # Proyek
    PROJECT_NOT_FOUND = auto()
    PROJECT_ALREADY_EXISTS = auto()
    NOT_A_MEMBER = auto()

    # Auth
    UNAUTHORIZED = auto()

    # User
    USER_NOT_FOUND = auto()
    INVALID_ROLE_ASSIGNMENT = auto()
    USER_NOT_IN_PROJECT = auto()
    CANNOT_CHANGE_ROLE_PROJECT = auto()

    # Tugas
    TASK_NOT_FOUND = auto()
    TASK_ALREADY_EXISTS = auto()

    # Member
    MEMBER_ALREADY_JOIN = auto()
    MEMBER_NOT_FOUND = auto()
    MEMBER_CANNOT_REMOVE = auto()

    # Komentar
    COMMENT_NOT_FOUND = auto()
    COMMENT_NOT_ALLOWED = auto()
    COMMENT_CANNOT_DELETE = auto()

    # Media
    MEDIA_NOT_SUPPORTED = auto()
    FILE_TOO_LARGE = auto()
    ATTACHMENT_NOT_FOUND = auto()

    # milestone
    MILESTONE_NOT_FOUND = auto()

    # Kategori
    CATEGORY_NOT_FOUND = auto()
    INVALID_CATEGORY_ASSIGNMENT = auto()
