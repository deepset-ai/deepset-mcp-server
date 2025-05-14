from types import TracebackType
from typing import Any, Protocol, Self

from deepset_mcp.api.pipeline.models import DeepsetPipeline, NoContentResponse, PipelineValidationResult
from deepset_mcp.api.pipeline_template.models import PipelineTemplate
from deepset_mcp.api.transport import TransportResponse


class HaystackServiceProtocol(Protocol):
    """Protocol defining the implementation for HaystackService."""

    async def get_component_schemas(self) -> dict[str, Any]:
        """Fetch the component schema from the API."""
        ...


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

    def pipelines(self, workspace: str) -> "PipelineResourceProtocol":
        """Access pipelines in the specified workspace."""
        ...

    def haystack_service(self) -> "HaystackServiceProtocol":
        """Access the Haystack service."""
        ...

    def pipeline_templates(self, workspace: str) -> "PipelineTemplateResourceProtocol":
        """Access pipeline templates in the specified workspace."""
        ...


class PipelineTemplateResourceProtocol(Protocol):
    """Protocol defining the implementation for PipelineTemplateResource."""

    async def get_template(self, template_name: str) -> PipelineTemplate:
        """Fetch a single pipeline template by its name."""
        ...

    async def list_templates(self, limit: int = 100) -> list[PipelineTemplate]:
        """List pipeline templates in the configured workspace."""
        ...


class PipelineResourceProtocol(Protocol):
    """Protocol defining the implementation for PipelineResource."""

    async def validate(self, yaml_config: str) -> PipelineValidationResult:
        """Validate a pipeline's YAML configuration against the API."""
        ...

    async def get(self, pipeline_name: str) -> DeepsetPipeline:
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
