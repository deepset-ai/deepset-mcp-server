import os
from types import TracebackType
from typing import Any, Self

from deepset_mcp.api.haystack_service.resource import HaystackServiceResource
from deepset_mcp.api.pipeline.resource import PipelineResource
from deepset_mcp.api.pipeline_template.resource import PipelineTemplateResource
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.transport import AsyncTransport, TransportProtocol, TransportResponse


class AsyncDeepsetClient(AsyncClientProtocol):
    """Async Client for interacting with the deepset API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.cloud.deepset.ai/api",
        transport: TransportProtocol | None = None,
        transport_config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize an instance of the AsyncDeepsetClient.

        Parameters
        ----------
        api_key : str, optional
            API key or token. Falls back to DEEPSET_API_KEY env var.
        base_url : str, optional
            Base URL for the deepset API.
        transport : TransportProtocol, optional
            Custom transport implementation.
        transport_config : dict, optional
            Configuration for default transport (e.g. timeout).
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

    async def request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> TransportResponse:
        """Make a request to the deepset API."""
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
        )

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

    def pipelines(self, workspace: str) -> PipelineResource:
        """Resource to interact with pipelines in the specified workspace."""
        return PipelineResource(client=self, workspace=workspace)

    def haystack_service(self) -> HaystackServiceResource:
        """Resource to interact with the Haystack service API."""
        return HaystackServiceResource(client=self)

    def pipeline_templates(self, workspace: str) -> PipelineTemplateResource:
        """Resource to interact with pipeline templates in the specified workspace."""
        return PipelineTemplateResource(client=self, workspace=workspace)
