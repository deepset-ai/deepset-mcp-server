from types import TracebackType
from typing import Any, Protocol, Self

from deepset_mcp.api.pipeline.models import DeepsetPipeline, PipelineValidationResult
from deepset_mcp.api.transport import TransportResponse


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


class PipelineResourceProtocol(Protocol):
    """Protocol defining the implementation for PipelineResource."""

    def __init__(self, client: AsyncClientProtocol, workspace: str) -> None:
        """Initialize a PipelineResource."""
        ...

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

    async def create(self, name: str, yaml_config: str) -> Any:
        """Create a new pipeline with a name and YAML config."""
        ...

    async def update(
        self,
        pipeline_name: str,
        updated_pipeline_name: str | None = None,
        yaml_config: str | None = None,
    ) -> Any:
        """Update name and/or YAML config of an existing pipeline."""
        ...
