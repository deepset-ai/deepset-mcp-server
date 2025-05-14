import json
from types import TracebackType
from typing import Any, Self

from deepset_mcp.api.protocols import (
    AsyncClientProtocol,
    HaystackServiceProtocol,
    PipelineResourceProtocol,
    PipelineTemplateResourceProtocol,
)
from deepset_mcp.api.transport import TransportResponse


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

    async def request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> TransportResponse:
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
        self.requests.append({"endpoint": endpoint, "method": method, "data": data, "headers": headers})

        # Find the appropriate response
        for resp_key, resp_data in self.responses.items():
            if endpoint.endswith(resp_key):
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
                    return TransportResponse(text=str(resp_data), status_code=200, json=None)

        raise ValueError(f"No response defined for endpoint: {endpoint}")

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
