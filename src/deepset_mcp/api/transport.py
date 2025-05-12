import json
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError


@dataclass
class TransportResponse:
    """Response envelope for HTTP transport."""

    text: str
    status_code: int
    json: dict[str, Any] | None = None

    @property
    def success(self) -> bool:
        """Returns True if the response status code indicates success (< 400)."""
        return self.status_code < 400


def raise_for_status(response: TransportResponse) -> None:
    """Raises the appropriate exception based on the response status code."""
    if response.success:
        return

    # Map status codes to exception classes
    exception_map = {
        400: BadRequestError,
        404: ResourceNotFoundError,
    }

    # Extract error details from response if available
    detail = response.json.get("details") if response.json else None
    message = response.json.get("message") if response.json else response.text

    # Get exception class
    exception_class = exception_map.get(response.status_code)

    if exception_class:
        # For specific exceptions (BadRequestError, ResourceNotFoundError)
        raise exception_class(message=message, detail=detail)
    else:
        # For the catch-all case, include the status code
        raise UnexpectedAPIError(
            status_code=response.status_code, message=message or "Unexpected API error", detail=detail
        )


class TransportProtocol(Protocol):
    """Protocol for HTTP transport."""

    async def request(self, method: str, url: str, **kwargs: Any) -> TransportResponse:
        """Send an HTTP request and return the parsed JSON response."""
        ...

    async def close(self) -> None:
        """Clean up any resources (e.g., close connections)."""
        ...


class AsyncTransport:
    """Asynchronous HTTP transport using httpx.AsyncClient."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize an instance of AsyncTransport.

        Parameters
        ----------
        base_url : str
            Base URL for the API
        api_key : str
            Bearer token for authentication
        config : dict, optional
            Configuration for httpx.AsyncClient, e.g., {'timeout': 10.0}
        """
        config = config or {}
        # Ensure auth header
        headers = config.pop("headers", {})
        headers.setdefault("Authorization", f"Bearer {api_key}")
        # Build client kwargs
        client_kwargs = {
            "base_url": base_url,
            "headers": headers,
            **config,
        }
        self._client = httpx.AsyncClient(**client_kwargs)

    async def request(self, method: str, url: str, **kwargs: Any) -> TransportResponse:
        """Send an HTTP request and return the response."""
        response = await self._client.request(method, url, **kwargs)

        transport_response = TransportResponse(text=response.text, status_code=response.status_code)

        try:
            transport_response.json = response.json()
        except json.decoder.JSONDecodeError:
            pass

        return transport_response

    async def close(self) -> None:
        """Clean up any resources (e.g., close connections)."""
        await self._client.aclose()
