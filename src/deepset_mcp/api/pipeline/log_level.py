from enum import StrEnum


class LogLevel(StrEnum):
    """Log level filter options for pipeline logs."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
