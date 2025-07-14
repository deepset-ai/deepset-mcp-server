# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any


class DeepsetAPIError(Exception):
    """Base exception for all deepset API errors."""

    def __init__(self, status_code: int | None = None, message: Any | None = None, detail: Any | None = None) -> None:
        """Initialize the exception."""
        self.status_code = status_code
        self.message = message
        self.detail = detail
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return a string representation of the exception."""
        return f"{self.message} (Status Code: {self.status_code})"


class ResourceNotFoundError(DeepsetAPIError):
    """Exception raised when a resource is not found (HTTP 404)."""

    def __init__(self, message: Any = "Resource not found", detail: Any | None = None) -> None:
        """Initialize the exception."""
        super().__init__(status_code=404, message=message, detail=detail)


class BadRequestError(DeepsetAPIError):
    """Exception raised for invalid requests (HTTP 400)."""

    def __init__(self, message: Any = "Bad request", detail: Any | None = None) -> None:
        """Initialize the exception."""
        super().__init__(status_code=400, message=message, detail=detail)


class RequestTimeoutError(Exception):
    """Exception raised when a request times out."""

    def __init__(
        self,
        method: str,
        url: str,
        timeout: float | None | str,
        duration: float | None = None,
        detail: str | None = None,
    ):
        """Initialize the timeout exception with request context."""
        self.method = method
        self.url = url
        self.timeout = timeout
        self.duration = duration
        self.detail = detail

        timeout_display = f"{timeout}s" if isinstance(timeout, int | float) else str(timeout)

        if duration is not None:
            message = f"Request timed out after {duration:.2f}s (limit: {timeout_display}): {method} {url}"
        else:
            message = f"Request timed out (limit: {timeout_display}): {method} {url}"

        super().__init__(message)


class UnexpectedAPIError(DeepsetAPIError):
    """Catch-all exception for unexpected API errors."""

    def __init__(
        self, status_code: int | None = None, message: Any = "Unexpected API error", detail: Any | None = None
    ):
        """Initialize the exception."""
        super().__init__(status_code=status_code, message=message, detail=detail)
