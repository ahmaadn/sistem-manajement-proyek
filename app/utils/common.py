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
    PROYEK_NOT_FOUND = auto()
    PROYEK_ALREADY_EXISTS = auto()

    # Auth
    UNAUTHORIZED = auto()

    # User
    USER_NOT_FOUND = auto()

    # Tugas
    TASK_NOT_FOUND = auto()
    TASK_ALREADY_EXISTS = auto()
