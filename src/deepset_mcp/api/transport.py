import json
from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar, cast, overload

import httpx

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError

T = TypeVar("T")


@dataclass
class TransportResponse(Generic[T]):
    """Reponse envelope for HTTP transport."""

    text: str
    status_code: int
    json: T | None = None

    @property
    def success(self) -> bool:
        """Check if the response was successful (status code < 400)."""
        return self.status_code < 400


def raise_for_status(response: TransportResponse[Any]) -> None:
    """Raises the appropriate exception based on the response status code."""
    if response.success:
        return

    # Map status codes to exception classes
    exception_map = {
        400: BadRequestError,
        404: ResourceNotFoundError,
    }

    if isinstance(response.json, dict):
        detail = response.json.get("details") if response.json else None
        message = response.json.get("message") if response.json else response.text
    else:
        detail = json.dumps(response.json) if response.json else None
        message = response.text

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

    @overload
    async def request(
        self, method: str, url: str, *, response_type: type[T], **kwargs: Any
    ) -> TransportResponse[T]: ...

    @overload
    async def request(
        self, method: str, url: str, *, response_type: None = None, **kwargs: Any
    ) -> TransportResponse[Any]: ...

    async def request(
        self, method: str, url: str, *, response_type: type[T] | None = None, **kwargs: Any
    ) -> TransportResponse[Any]:
        """Send an HTTP request and return the response."""
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

    @overload
    async def request(
        self, method: str, url: str, *, response_type: type[T], **kwargs: Any
    ) -> TransportResponse[T]: ...

    @overload
    async def request(
        self, method: str, url: str, *, response_type: None = None, **kwargs: Any
    ) -> TransportResponse[Any]: ...

    async def request(
        self, method: str, url: str, *, response_type: type[T] | None = None, **kwargs: Any
    ) -> TransportResponse[Any]:
        """Send an HTTP request and return the response."""
        response = await self._client.request(method, url, **kwargs)

        if response_type is not None:
            raw = response.json()
            payload: T = cast(T, raw)
            return TransportResponse(text=response.text, status_code=response.status_code, json=payload)

        try:
            untyped_response = response.json()
        except json.decoder.JSONDecodeError:
            untyped_response = None
            pass

        return TransportResponse(text=response.text, status_code=response.status_code, json=untyped_response)

    async def close(self) -> None:
        """Clean up any resources (e.g., close connections)."""
        await self._client.aclose()
