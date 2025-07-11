"""Structured logging configuration for benchmark operations."""

import logging
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler


class BenchmarkLogger:
    """Enhanced logger for benchmark operations with structured context."""

    def __init__(self, name: str, debug: bool = False):
        """
        Initialize the benchmark logger.

        Args:
            name: Logger name (typically module name)
            debug: Enable debug logging level
        """
        self.logger = logging.getLogger(name)
        self.console = Console(stderr=True)
        self._setup_logger(debug)

    def _setup_logger(self, debug: bool) -> None:
        """Set up the logger with appropriate handlers and formatters."""
        # Clear any existing handlers
        self.logger.handlers.clear()

        # Set log level
        level = logging.DEBUG if debug else logging.INFO
        self.logger.setLevel(level)

        # Create rich handler for pretty console output
        rich_handler = RichHandler(
            console=self.console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            markup=True,
        )
        rich_handler.setLevel(level)

        # Create formatter
        formatter = logging.Formatter(
            fmt="%(message)s",
            datefmt="[%X]",
        )
        rich_handler.setFormatter(formatter)

        # Add handler to logger
        self.logger.addHandler(rich_handler)

        # Prevent propagation to root logger
        self.logger.propagate = False

    def _format_context(self, context: dict[str, Any] | None) -> str:
        """Format context dictionary for logging."""
        if not context:
            return ""

        # Format context as key=value pairs
        context_parts = []
        for key, value in context.items():
            # Truncate long values
            str_value = str(value)
            if len(str_value) > 100:
                str_value = str_value[:97] + "..."
            context_parts.append(f"{key}={str_value}")

        return f" [{', '.join(context_parts)}]"

    def info(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Log info message with optional context."""
        full_message = message + self._format_context(context)
        self.logger.info(full_message)

    def debug(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Log debug message with optional context."""
        full_message = message + self._format_context(context)
        self.logger.debug(full_message)

    def warning(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Log warning message with optional context."""
        full_message = message + self._format_context(context)
        self.logger.warning(full_message)

    def error(self, message: str, context: dict[str, Any] | None = None, exc_info: bool = False) -> None:
        """Log error message with optional context and exception info."""
        full_message = message + self._format_context(context)
        self.logger.error(full_message, exc_info=exc_info)

    def exception(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Log exception with full traceback and context."""
        full_message = message + self._format_context(context)
        self.logger.exception(full_message)


def get_benchmark_logger(name: str, debug: bool = False) -> BenchmarkLogger:
    """
    Get a configured benchmark logger.

    Args:
        name: Logger name (typically __name__)
        debug: Enable debug logging

    Returns:
        Configured BenchmarkLogger instance
    """
    return BenchmarkLogger(name, debug)


def setup_file_logging(log_file: Path, debug: bool = False) -> None:
    """
    Set up additional file logging for benchmark runs.

    Args:
        log_file: Path to log file
        debug: Enable debug logging
    """
    # Ensure directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)

    # Create detailed formatter for file logs
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    # Add to root logger so all benchmark loggers use it
    root_logger = logging.getLogger("deepset_mcp.benchmark")
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
