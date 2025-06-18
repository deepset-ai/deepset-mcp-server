from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import Any, Protocol, Self, TypeVar, overload

from deepset_mcp.api.custom_components.models import CustomComponentInstallationList
from deepset_mcp.api.indexes.models import Index, IndexList
from deepset_mcp.api.pipeline.log_level import LogLevel
from deepset_mcp.api.pipeline.models import (
    DeepsetPipeline,
    DeepsetSearchResponse,
    DeepsetStreamEvent,
    PipelineLogList,
    PipelineValidationResult,
)
from deepset_mcp.api.pipeline_template.models import PipelineTemplate
from deepset_mcp.api.secrets.models import Secret, SecretList
from deepset_mcp.api.shared_models import DeepsetUser, NoContentResponse
from deepset_mcp.api.transport import StreamingResponse, TransportResponse


class HaystackServiceProtocol(Protocol):
    """Protocol defining the implementation for HaystackService."""

    async def get_component_schemas(self) -> dict[str, Any]:
        """Fetch the component schema from the API."""
        ...

    async def get_component_input_output(self, component_name: str) -> dict[str, Any]:
        """Fetch input and output schema for a component from the API."""
        ...


class CustomComponentsProtocol(Protocol):
    """Protocol defining the implementation for CustomComponentsResource."""

    async def list_installations(
        self, limit: int = 20, page_number: int = 1, field: str = "created_at", order: str = "DESC"
    ) -> CustomComponentInstallationList:
        """List custom component installations."""
        ...

    async def get_latest_installation_logs(self) -> str | None:
        """Get the logs from the latest custom component installation."""
        ...


class UserResourceProtocol(Protocol):
    """Protocol defining the implementation for UserResource."""

    async def get(self, user_id: str) -> DeepsetUser:
        """Get user information by user ID."""
        ...


class SecretResourceProtocol(Protocol):
    """Protocol defining the implementation for SecretResource."""

    async def list(
        self,
        limit: int = 10,
        field: str = "created_at",
        order: str = "DESC",
    ) -> SecretList:
        """List secrets with pagination."""
        ...

    async def create(self, name: str, secret: str) -> NoContentResponse:
        """Create a new secret."""
        ...

    async def get(self, secret_id: str) -> Secret:
        """Get a specific secret by ID."""
        ...

    async def delete(self, secret_id: str) -> NoContentResponse:
        """Delete a secret by ID."""
        ...


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


class IndexResourceProtocol(Protocol):
    """Protocol defining the implementation for IndexResource."""

    async def list(self, limit: int = 10, page_number: int = 1) -> IndexList:
        """List indexes in the configured workspace."""
        ...

    async def get(self, index_name: str) -> Index:
        """Fetch a single index by its name."""
        ...

    async def create(self, name: str, yaml_config: str, description: str | None = None) -> Index:
        """Create a new index with the given name and configuration.

        :param name: Name of the index
        :param yaml_config: YAML configuration for the index
        :param description: Optional description for the index
        :returns: Created index details
        """
        ...

    async def update(
        self, index_name: str, updated_index_name: str | None = None, yaml_config: str | None = None
    ) -> Index:
        """Update name and/or configuration of an existing index.

        :param index_name: Name of the index to update
        :param updated_index_name: Optional new name for the index
        :param yaml_config: Optional new YAML configuration
        :returns: Updated index details
        """
        ...

    async def deploy(self, index_name: str) -> PipelineValidationResult:
        """Deploy an index to production.

        :param index_name: Name of the index to deploy.
        :returns: PipelineValidationResult containing deployment status and any errors.
        """
        ...

    async def delete(self, index_name: str) -> None:
        """Delete an index.

        :param index_name: Name of the index to delete.
        """
        ...


class PipelineTemplateResourceProtocol(Protocol):
    """Protocol defining the implementation for PipelineTemplateResource."""

    async def get_template(self, template_name: str) -> PipelineTemplate:
        """Fetch a single pipeline template by its name."""
        ...

    async def list_templates(
        self, limit: int = 100, field: str = "created_at", order: str = "DESC", filter: str | None = None
    ) -> list[PipelineTemplate]:
        """List pipeline templates in the configured workspace."""
        ...


class PipelineResourceProtocol(Protocol):
    """Protocol defining the implementation for PipelineResource."""

    async def validate(self, yaml_config: str) -> PipelineValidationResult:
        """Validate a pipeline's YAML configuration against the API."""
        ...

    async def get(self, pipeline_name: str, include_yaml: bool = True) -> DeepsetPipeline:
        """Fetch a single pipeline by its name."""
        ...

    async def list(
        self,
        page_number: int = 1,
        limit: int = 10,
    ) -> list[DeepsetPipeline]:
        """List pipelines in the configured workspace with optional pagination."""
        ...

    async def create(self, name: str, yaml_config: str) -> NoContentResponse:
        """Create a new pipeline with a name and YAML config."""
        ...

    async def update(
        self,
        pipeline_name: str,
        updated_pipeline_name: str | None = None,
        yaml_config: str | None = None,
    ) -> NoContentResponse:
        """Update name and/or YAML config of an existing pipeline."""
        ...

    async def get_logs(
        self,
        pipeline_name: str,
        limit: int = 30,
        level: LogLevel | None = None,
    ) -> PipelineLogList:
        """Fetch logs for a specific pipeline."""
        ...

    async def deploy(self, pipeline_name: str) -> PipelineValidationResult:
        """Deploy a pipeline."""
        ...

    async def search(
        self,
        pipeline_name: str,
        query: str,
        debug: bool = False,
        view_prompts: bool = False,
        params: dict[str, Any] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> DeepsetSearchResponse:
        """Search using a pipeline."""
        ...

    def search_stream(
        self,
        pipeline_name: str,
        query: str,
        debug: bool = False,
        view_prompts: bool = False,
        params: dict[str, Any] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[DeepsetStreamEvent]:
        """Search using a pipeline with response streaming."""
        ...
