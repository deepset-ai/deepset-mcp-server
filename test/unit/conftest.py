# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import json
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from types import TracebackType
from typing import Any, Literal, Self, TypeVar, overload

from deepset_mcp.api.custom_components.protocols import CustomComponentsProtocol
from deepset_mcp.api.haystack_service.protocols import HaystackServiceProtocol
from deepset_mcp.api.indexes.protocols import IndexResourceProtocol
from deepset_mcp.api.integrations.protocols import IntegrationResourceProtocol
from deepset_mcp.api.pipeline.protocols import PipelineResourceProtocol
from deepset_mcp.api.pipeline_template.protocols import PipelineTemplateResourceProtocol
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.secrets.protocols import SecretResourceProtocol
from deepset_mcp.api.transport import StreamingResponse, StreamReaderProtocol, TransportResponse
from deepset_mcp.api.user.protocols import UserResourceProtocol
from deepset_mcp.api.workspace.protocols import WorkspaceResourceProtocol

T = TypeVar("T")


class FakeStreamReader(StreamReaderProtocol):
    """Fake stream reader for testing."""

    def __init__(self, lines: list[str] | None = None, body: str | None = None):
        self.lines = lines or []
        self.body = body or "\n".join(self.lines)

    async def aread(self) -> bytes:
        """Read entire body."""
        return self.body.encode()

    def aiter_lines(self) -> AsyncIterator[str]:
        """Iterate over lines."""

        async def generator() -> AsyncGenerator[str, None]:
            for line in self.lines:
                yield line

        return generator()


class BaseFakeClient(AsyncClientProtocol):
    """Dummy client for testing that implements AsyncClientProtocol."""

    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        """
        Initialize with predefined responses.

        Parameters
        ----------
        responses : Dict[str, Any], optional
            Dictionary mapping endpoints to response data.
        """
        self.responses = responses or {}
        self.requests: list[dict[str, Any]] = []
        self.closed = False

    @overload
    async def request(
        self,
        endpoint: str,
        *,
        response_type: type[T],
        method: str = "GET",
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None | Literal["config"] = "config",
        **kwargs: Any,
    ) -> TransportResponse[T]: ...

    @overload
    async def request(
        self,
        endpoint: str,
        *,
        response_type: None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None | Literal["config"] = "config",
        **kwargs: Any,
    ) -> TransportResponse[Any]: ...

    async def request(
        self,
        endpoint: str,
        *,
        response_type: type[T] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None | Literal["config"] = "config",
        **kwargs: Any,
    ) -> TransportResponse[Any]:
        """
        Record the request and return a predefined response.

        Parameters
        ----------
        endpoint : str
            API endpoint.
        method : str, optional
            HTTP method.
        data : Dict[str, Any], optional
            Request data.
        headers : Dict[str, str], optional
            Request headers.

        Returns
        -------
        TransportResponse
            Response object.

        Raises
        ------
        ValueError
            If no response is predefined for the endpoint.
        """
        self.requests.append({"endpoint": endpoint, "method": method, "data": data, "headers": headers, **kwargs})

        # Find the appropriate response
        for resp_key, resp_data in self.responses.items():
            # First try exact match, then fallback to endswith for compatibility
            if endpoint == resp_key or endpoint.endswith(resp_key):
                if isinstance(resp_data, Exception):
                    raise resp_data

                if isinstance(resp_data, TransportResponse):
                    return resp_data

                # Create a real TransportResponse instead of a mock
                if isinstance(resp_data, dict):
                    text = json.dumps(resp_data)
                    return TransportResponse(
                        text=text,
                        status_code=200,  # Default success status code
                        json=resp_data,
                    )
                else:
                    return TransportResponse(
                        text=str(resp_data), status_code=200, json=resp_data if resp_data is not None else None
                    )

        raise ValueError(f"No response defined for endpoint: {endpoint}")

    def stream_request(
        self,
        endpoint: str,
        *,
        method: str = "POST",
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> AbstractAsyncContextManager[StreamingResponse]:
        """
        Record the streaming request and return a predefined streaming response.

        Parameters
        ----------
        endpoint : str
            API endpoint.
        method : str, optional
            HTTP method.
        data : Dict[str, Any], optional
            Request data.
        headers : Dict[str, str], optional
            Request headers.

        Yields
        ------
        StreamingResponse
            Streaming response object.

        Raises
        ------
        ValueError
            If no response is predefined for the endpoint.
        """
        self.requests.append(
            {"endpoint": endpoint, "method": method, "data": data, "headers": headers, "streaming": True, **kwargs}
        )

        @asynccontextmanager
        async def _stream() -> AsyncIterator[StreamingResponse]:
            # Find the appropriate response
            for resp_key, resp_data in self.responses.items():
                # First try exact match, then fallback to endswith for compatibility
                if endpoint == resp_key or endpoint.endswith(resp_key):
                    if isinstance(resp_data, Exception):
                        raise resp_data

                    if isinstance(resp_data, StreamingResponse):
                        yield resp_data
                        return

                    # Handle dict responses for streaming
                    if isinstance(resp_data, dict):
                        # Check if it's a streaming-specific response format
                        if "status_code" in resp_data and ("lines" in resp_data or "body" in resp_data):
                            reader = FakeStreamReader(lines=resp_data.get("lines", []), body=resp_data.get("body"))
                            yield StreamingResponse(
                                status_code=resp_data.get("status_code", 200),
                                headers=resp_data.get("headers", {}),
                                _reader=reader,
                            )
                            return
                        else:
                            # Convert regular dict to streaming response
                            reader = FakeStreamReader(lines=[json.dumps(resp_data)])
                            yield StreamingResponse(status_code=200, headers={}, _reader=reader)
                            return

                    # Handle list responses as lines
                    if isinstance(resp_data, list):
                        reader = FakeStreamReader(lines=resp_data)
                        yield StreamingResponse(status_code=200, headers={}, _reader=reader)
                        return

                    # Default: convert to single line
                    reader = FakeStreamReader(lines=[str(resp_data)])
                    yield StreamingResponse(status_code=200, headers={}, _reader=reader)
                    return

            raise ValueError(f"No response defined for endpoint: {endpoint}")

        return _stream()

    async def close(self) -> None:
        """Close the client."""
        self.closed = True

    async def __aenter__(self) -> Self:
        """Enter the AsyncContextManager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> bool:
        """Exit the AsyncContextmanager and clean up resources."""
        await self.close()
        return False

    def pipelines(self, workspace: str) -> PipelineResourceProtocol:
        """Overwrite this method when testing PipelineResource."""
        raise NotImplementedError

    def haystack_service(self) -> HaystackServiceProtocol:
        """Overwrite this method when testing HaystackService."""
        raise NotImplementedError

    def pipeline_templates(self, workspace: str) -> PipelineTemplateResourceProtocol:
        """Overwrite this method when testing PipelineTemplateResource."""
        raise NotImplementedError

    def indexes(self, workspace: str) -> IndexResourceProtocol:
        """Overwrite this method when testing IndexResource."""
        raise NotImplementedError

    def custom_components(self, workspace: str) -> CustomComponentsProtocol:
        """Overwrite this method when testing CustomComponentsResource."""
        raise NotImplementedError

    def users(self) -> UserResourceProtocol:
        """Overwrite this method when testing UserResource."""
        raise NotImplementedError

    def secrets(self) -> SecretResourceProtocol:
        """Overwrite this method when testing SecretResource."""
        raise NotImplementedError

    def workspaces(self) -> WorkspaceResourceProtocol:
        """Overwrite this method when testing WorkspaceResource."""
        raise NotImplementedError

    def integrations(self) -> IntegrationResourceProtocol:
        """Overwrite this method when testing IntegrationResource."""
        raise NotImplementedError
