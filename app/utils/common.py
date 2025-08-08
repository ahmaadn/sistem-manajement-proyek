from enum import StrEnum, auto


class ErrorCode(StrEnum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values) -> str:
        return name.upper()

    APP_ERROR = auto()
    INTERNAL_SERVER_ERROR = auto()
