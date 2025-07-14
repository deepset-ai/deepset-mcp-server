# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import Any, Literal, Protocol, Self, TypeVar, overload

from deepset_mcp.api.custom_components.protocols import CustomComponentsProtocol
from deepset_mcp.api.haystack_service.protocols import HaystackServiceProtocol
from deepset_mcp.api.indexes.protocols import IndexResourceProtocol
from deepset_mcp.api.integrations.protocols import IntegrationResourceProtocol
from deepset_mcp.api.pipeline.protocols import PipelineResourceProtocol
from deepset_mcp.api.pipeline_template.protocols import PipelineTemplateResourceProtocol
from deepset_mcp.api.secrets.protocols import SecretResourceProtocol
from deepset_mcp.api.transport import StreamingResponse, TransportResponse
from deepset_mcp.api.user.protocols import UserResourceProtocol
from deepset_mcp.api.workspace.protocols import WorkspaceResourceProtocol

T = TypeVar("T")


class AsyncClientProtocol(Protocol):
    """Protocol defining the implementation for AsyncClient."""

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
        """Make a request to the API."""
        ...

    def stream_request(
        self,
        endpoint: str,
        *,
        method: str = "POST",
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> AbstractAsyncContextManager[StreamingResponse]:
        """Make a streaming request to the API."""
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

    def pipelines(self, workspace: str) -> "PipelineResourceProtocol":
        """Access pipelines in the specified workspace."""
        ...

    def haystack_service(self) -> "HaystackServiceProtocol":
        """Access the Haystack service."""
        ...

    def pipeline_templates(self, workspace: str) -> "PipelineTemplateResourceProtocol":
        """Access pipeline templates in the specified workspace."""
        ...

    def indexes(self, workspace: str) -> "IndexResourceProtocol":
        """Access indexes in the specified workspace."""
        ...

    def custom_components(self, workspace: str) -> "CustomComponentsProtocol":
        """Access custom components in the specified workspace."""
        ...

    def users(self) -> "UserResourceProtocol":
        """Access users."""
        ...

    def secrets(self) -> "SecretResourceProtocol":
        """Access secrets."""
        ...

    def workspaces(self) -> "WorkspaceResourceProtocol":
        """Access workspaces."""
        ...

    def integrations(self) -> "IntegrationResourceProtocol":
        """Access integrations."""
        ...
