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

    # Proyek
    PROJECT_NOT_FOUND = auto()
    PROJECT_ALREADY_EXISTS = auto()

    # Auth
    UNAUTHORIZED = auto()

    # User
    USER_NOT_FOUND = auto()

    # Tugas
    TASK_NOT_FOUND = auto()
    TASK_ALREADY_EXISTS = auto()

    # Member
    MEMBER_ALREADY_JOIN = auto()
    MEMBER_NOT_FOUND = auto()
    MEMBER_CANNOT_REMOVE = auto()
