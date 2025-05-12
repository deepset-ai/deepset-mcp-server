from types import TracebackType
from typing import Any, Protocol, Self

from deepset_mcp.api.transport import TransportResponse


class AsyncClientProtocol(Protocol):
    """Protocol defining the implementation for AsyncClient."""

    async def request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> TransportResponse:
        """Make a request to the API."""
        ...

    async def close(self) -> None:
        """Close underlying transport resources."""
        ...

    async def __aenter__(self) -> Self:
        """Enter the AsyncContextManager."""
        ...

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> bool:
        """Exit the AsyncContextmanager and clean up resources."""
        ...
