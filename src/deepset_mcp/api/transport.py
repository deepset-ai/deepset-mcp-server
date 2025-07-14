# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import json
import time
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from typing import Any, Generic, Literal, Protocol, TypeVar, cast, overload

import httpx

from deepset_mcp.api.exceptions import BadRequestError, RequestTimeoutError, ResourceNotFoundError, UnexpectedAPIError

T = TypeVar("T")


class StreamReaderProtocol(Protocol):
    """Protocol for reading from a stream."""

    async def aread(self) -> bytes:
        """Read the entire response body."""
        ...

    def aiter_lines(self) -> AsyncIterator[str]:
        """Iterate over response lines."""
        ...


@dataclass
class TransportResponse(Generic[T]):
    """Response envelope for regular HTTP transport."""

    text: str
    status_code: int
    json: T | None = None

    @property
    def success(self) -> bool:
        """Check if the response was successful (status code < 400)."""
        return self.status_code < 400


@dataclass
class StreamingResponse:
    """Response envelope for streaming HTTP transport."""

    status_code: int
    headers: dict[str, str]
    _reader: StreamReaderProtocol

    @property
    def success(self) -> bool:
        """Check if the response was successful (status code < 400)."""
        return self.status_code < 400

    async def iter_lines(self) -> AsyncIterator[str]:
        """
        Iterate over response lines.

        For error responses (status >= 400), reads the entire body and yields it.
        For success responses, yields line by line.
        """
        if self.status_code >= 400:
            # For errors, read entire body at once
            body = await self._reader.aread()
            if body:
                yield body.decode()
        else:
            # For success, stream line by line
            async for line in self._reader.aiter_lines():
                if line.startswith("data: "):  # optionally handle SSE 'data: ' prefix
                    yield line[6:]
                yield line

    async def read_body(self) -> str:
        """Read the entire response body. Useful for error handling."""
        body = await self._reader.aread()
        return body.decode() if body else ""


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
    """Protocol for HTTP transport with separate streaming support."""

    @overload
    async def request(
        self,
        method: str,
        url: str,
        *,
        response_type: type[T],
        timeout: float | None | Literal["config"] = "config",
        **kwargs: Any,
    ) -> TransportResponse[T]: ...

    @overload
    async def request(
        self,
        method: str,
        url: str,
        *,
        response_type: None = None,
        timeout: float | None | Literal["config"] = "config",
        **kwargs: Any,
    ) -> TransportResponse[Any]: ...

    async def request(
        self,
        method: str,
        url: str,
        *,
        response_type: type[T] | None = None,
        timeout: float | None | Literal["config"] = "config",
        **kwargs: Any,
    ) -> TransportResponse[Any]:
        """Send a regular HTTP request and return the response."""
        ...

    def stream(self, method: str, url: str, **kwargs: Any) -> AbstractAsyncContextManager[StreamingResponse]:
        """
        Open a streaming HTTP connection.

        Must be used as an async context manager to ensure proper cleanup.
        """
        ...

    async def close(self) -> None:
        """Clean up any resources (e.g., close connections)."""
        ...


class _HttpxStreamReader:
    """Adapter to make httpx.Response conform to StreamReaderProtocol."""

    def __init__(self, response: httpx.Response):
        self._response = response

    async def aread(self) -> bytes:
        """Read the entire response body."""
        return await self._response.aread()

    async def aiter_lines(self) -> AsyncIterator[str]:
        """Iterate over response lines."""
        async for line in self._response.aiter_lines():
            yield line


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
        self,
        method: str,
        url: str,
        *,
        response_type: type[T],
        timeout: float | None | Literal["config"] = "config",
        **kwargs: Any,
    ) -> TransportResponse[T]: ...

    @overload
    async def request(
        self,
        method: str,
        url: str,
        *,
        response_type: None = None,
        timeout: float | None | Literal["config"] = "config",
        **kwargs: Any,
    ) -> TransportResponse[Any]: ...

    async def request(
        self,
        method: str,
        url: str,
        *,
        response_type: type[T] | None = None,
        timeout: float | None | Literal["config"] = "config",
        **kwargs: Any,
    ) -> TransportResponse[Any]:
        """
        Send a regular HTTP request and return the response.

        Parameters
        ----------
        method : str
            HTTP method
        url : str
            URL endpoint
        response_type : type[T], optional
            Expected response type for type checking
        timeout : float | None | Literal["config"], optional
            Request timeout in seconds. If "config", uses transport config timeout.
            If None, disables timeout. If float, uses specific timeout.
        **kwargs : Any
            Additional arguments to pass to httpx

        Returns
        -------
        TransportResponse[T]
            The response with parsed JSON if available
        """
        if timeout != "config":
            kwargs["timeout"] = timeout

        start_time = time.time()
        try:
            response = await self._client.request(method, url, **kwargs)
        except httpx.TimeoutException as e:
            duration = time.time() - start_time
            timeout_value = kwargs.get("timeout", "config default")

            detail = None
            if "search" in url and duration > 60:
                detail = (
                    "Search operations can take longer with large document collections or complex pipelines. "
                    "Consider increasing the timeout for search requests."
                )

            raise RequestTimeoutError(
                method=method, url=url, timeout=timeout_value, duration=duration, detail=detail
            ) from e

        if response_type is not None:
            raw = response.json()
            payload: T = cast(T, raw)
            return TransportResponse(text=response.text, status_code=response.status_code, json=payload)

        try:
            untyped_response = response.json()
        except json.JSONDecodeError:
            untyped_response = None

        return TransportResponse(text=response.text, status_code=response.status_code, json=untyped_response)

    def stream(self, method: str, url: str, **kwargs: Any) -> AbstractAsyncContextManager[StreamingResponse]:
        """
        Open a streaming HTTP connection.

        Parameters
        ----------
        method : str
            HTTP method
        url : str
            URL endpoint
        **kwargs : Any
            Additional arguments to pass to httpx.stream()

        Yields
        ------
        StreamingResponse
            Response object with streaming capabilities

        Examples
        --------
        async with transport.stream("POST", "/api/stream", json=data) as response:
            if response.success:
                async for line in response.iter_lines():
                    process_line(line)
            else:
                error = await response.read_body()
                handle_error(error)
        """

        @asynccontextmanager
        async def _stream() -> AsyncIterator[StreamingResponse]:
            async with self._client.stream(method, url, **kwargs) as response:
                reader = _HttpxStreamReader(response)
                yield StreamingResponse(
                    status_code=response.status_code, headers=dict(response.headers), _reader=reader
                )

        return _stream()

    async def close(self) -> None:
        """Clean up any resources (e.g., close connections)."""
        await self._client.aclose()
