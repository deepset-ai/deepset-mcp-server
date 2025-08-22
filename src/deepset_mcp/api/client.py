# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import os
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from types import TracebackType
from typing import Any, Literal, Self, TypeVar, overload

from deepset_mcp.api.custom_components.resource import CustomComponentsResource
from deepset_mcp.api.haystack_service.resource import HaystackServiceResource
from deepset_mcp.api.indexes.resource import IndexResource
from deepset_mcp.api.integrations.resource import IntegrationResource
from deepset_mcp.api.pipeline.resource import PipelineResource
from deepset_mcp.api.pipeline_template.resource import PipelineTemplateResource
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.secrets.resource import SecretResource
from deepset_mcp.api.transport import (
    AsyncTransport,
    StreamingResponse,
    TransportProtocol,
    TransportResponse,
)
from deepset_mcp.api.user.resource import UserResource
from deepset_mcp.api.workspace.resource import WorkspaceResource

T = TypeVar("T")


class AsyncDeepsetClient(AsyncClientProtocol):
    """Async Client for interacting with the deepset API.

    This client provides asynchronous access to most deepset API endpoints
    and resources through a convenient interface.

    **Example usage:**

    ```python
    from deepset_mcp.api import AsyncDeepsetClient

    async with AsyncDeepsetClient() as client:
        pipes = await client.pipelines(workspace="example-workspace")
        all_pipelines = await pipes.list()
        example_pipeline = await pipes.get(pipeline_name="example-pipeline")
        await pipes.create(pipeline_name="example-pipeline-v2", yaml_config="...")

        indexes = await client.indexes(workspace="example-workspace")
        all_indexes = await indexes.list()
        example_index = await indexes.get(index_name="example-index")
    ```
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.cloud.deepset.ai/api",
        transport: TransportProtocol | None = None,
        transport_config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an instance of the AsyncDeepsetClient.

        :param api_key: API key or token. Falls back to DEEPSET_API_KEY env var
        :param base_url: Base URL for the deepset API
        :param transport: Custom transport implementation
        :param transport_config: Configuration for default transport (e.g. timeout). All configuration parameters are
            forwarded to httpx.AsyncClient.
        """
        self.api_key = api_key or os.environ.get("DEEPSET_API_KEY")
        if not self.api_key:
            raise ValueError("API key not provided and DEEPSET_API_KEY environment variable not set")
        self.base_url = base_url
        if transport is not None:
            self._transport = transport
        else:
            self._transport = AsyncTransport(
                base_url=self.base_url,
                api_key=self.api_key,
                config=transport_config,
            )

    def pipelines(self, workspace: str) -> PipelineResource:
        """Resource to interact with pipelines in the specified workspace.

        :param workspace: Workspace identifier
        :returns: Pipeline resource instance
        """
        return PipelineResource(client=self, workspace=workspace)

    def indexes(self, workspace: str) -> IndexResource:
        """Resource to interact with indexes in the specified workspace.

        :param workspace: Workspace identifier
        :returns: Index resource instance
        """
        return IndexResource(client=self, workspace=workspace)

    def pipeline_templates(self, workspace: str) -> PipelineTemplateResource:
        """Resource to interact with pipeline templates in the specified workspace.

        :param workspace: Workspace identifier
        :returns: Pipeline template resource instance
        """
        return PipelineTemplateResource(client=self, workspace=workspace)

    def haystack_service(self) -> HaystackServiceResource:
        """Resource to interact with the Haystack service API.

        :returns: Haystack service resource instance
        """
        return HaystackServiceResource(client=self)

    def integrations(self) -> IntegrationResource:
        """Resource to interact with integrations.

        :returns: Integration resource instance
        """
        return IntegrationResource(client=self)

    def custom_components(self, workspace: str) -> CustomComponentsResource:
        """Resource to interact with custom components in the specified workspace.

        :param workspace: Workspace identifier
        :returns: Custom components resource instance
        """
        return CustomComponentsResource(client=self)

    def secrets(self) -> SecretResource:
        """Resource to interact with secrets.

        :returns: Secret resource instance
        """
        return SecretResource(client=self)

    def workspaces(self) -> WorkspaceResource:
        """Resource to interact with workspaces.

        :returns: Workspace resource instance
        """
        return WorkspaceResource(client=self)

    def users(self) -> UserResource:
        """Resource to interact with users.

        :returns: User resource instance
        """
        return UserResource(client=self)

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
        method: str = "GET",
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        response_type: type[T] | None = None,
        timeout: float | None | Literal["config"] = "config",
        **kwargs: Any,
    ) -> TransportResponse[Any]:
        """Make a regular (non-streaming) request to the deepset API.

        :param endpoint: API endpoint path
        :param method: HTTP method
        :param data: JSON data to send in request body
        :param headers: Additional headers to include
        :param response_type: Expected response type for type checking
        :param timeout: Request timeout in seconds. If "config", uses transport config timeout.
            If None, disables timeout. If float, uses specific timeout
        :param kwargs: Additional arguments to pass to transport
        :returns: Response with parsed JSON if available
        """
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        url = self.base_url + endpoint

        # Default headers
        request_headers: dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json,text/plain,*/*",
        }
        if data is not None:
            request_headers["Content-Type"] = "application/json"
        # Merge custom headers
        if headers:
            headers.setdefault("Authorization", request_headers["Authorization"])
            request_headers.update(headers)

        return await self._transport.request(
            method,
            url,
            json=data,
            headers=request_headers,
            response_type=response_type,
            timeout=timeout,
            **kwargs,
        )

    def stream_request(
        self,
        endpoint: str,
        *,
        method: str = "POST",
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> AbstractAsyncContextManager[StreamingResponse]:
        """Make a streaming request to the deepset API.

        Must be used as an async context manager to ensure proper cleanup.

        Example::

            async with client.stream_request("/pipelines/search-stream", data={"query": "AI"}) as response:
                if response.success:
                    async for line in response.iter_lines():
                        # Process each line of the stream
                        data = json.loads(line)
                        print(data)
                else:
                    # Handle error
                    error_body = await response.read_body()
                    print(f"Error {response.status_code}: {error_body}")

        :param endpoint: API endpoint path
        :param method: HTTP method (usually POST for streaming)
        :param data: JSON data to send in request body
        :param headers: Additional headers to include
        :param kwargs: Additional arguments to pass to transport
        :returns: Response object with streaming capabilities
        """

        @asynccontextmanager
        async def _stream() -> AsyncIterator[StreamingResponse]:
            if not endpoint.startswith("/"):
                full_endpoint = f"/{endpoint}"
            url = self.base_url + full_endpoint

            # Default headers for streaming
            request_headers: dict[str, str] = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "text/event-stream,application/json,text/plain,*/*",
            }
            if data is not None:
                request_headers["Content-Type"] = "application/json"
            # Merge custom headers
            if headers:
                headers.setdefault("Authorization", request_headers["Authorization"])
                request_headers.update(headers)

            async with self._transport.stream(
                method,
                url,
                json=data,
                headers=request_headers,
                **kwargs,
            ) as response:
                yield response

        return _stream()

    async def close(self) -> None:
        """Close underlying transport resources."""
        await self._transport.close()

    async def __aenter__(self) -> Self:
        """Enter the AsyncContextManager."""
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> bool:
        """Exit the AsyncContextmanager and clean up resources."""
        await self.close()
        return False
