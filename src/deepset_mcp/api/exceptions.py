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


class UnexpectedAPIError(DeepsetAPIError):
    """Catch-all exception for unexpected API errors."""

    def __init__(
        self, status_code: int | None = None, message: Any = "Unexpected API error", detail: Any | None = None
    ):
        """Initialize the exception."""
        super().__init__(status_code=status_code, message=message, detail=detail)
