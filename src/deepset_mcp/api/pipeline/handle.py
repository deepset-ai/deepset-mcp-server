from typing import TYPE_CHECKING

from deepset_mcp.api.pipeline.models import DeepsetPipeline

if TYPE_CHECKING:
    from deepset_mcp.api.pipeline.log_models import PipelineLogList
    from deepset_mcp.api.protocols import PipelineResourceProtocol


class PipelineHandle:
    """Handle for performing operations on a specific pipeline.

    This class provides a convenient interface for interacting with a pipeline,
    combining the pipeline data model with resource operations. It allows both
    direct access to pipeline attributes and future operations like getting logs
    or deployment management.
    """

    def __init__(self, pipeline: DeepsetPipeline, resource: "PipelineResourceProtocol") -> None:
        """Initialize a PipelineHandle.

        :param pipeline: The pipeline data model containing all pipeline information.
        :param resource: The resource interface for performing operations on this pipeline.
        """
        self._pipeline = pipeline
        self._resource = resource

    def __getattr__(self, name: str) -> object:
        """Proxy attribute access to the underlying pipeline."""
        return getattr(self._pipeline, name)

    if TYPE_CHECKING:
        # Help type checkers understand available attributes from the underlying pipeline
        id: str
        name: str
        status: str
        service_level: str
        created_at: object
        last_updated_at: object | None
        created_by: object
        last_updated_by: object | None
        yaml_config: str | None

    @property
    def pipeline(self) -> DeepsetPipeline:
        """Access the full pipeline data model.

        :returns: The underlying DeepsetPipeline instance with all pipeline data.
        """
        return self._pipeline

    async def get_logs(
        self,
        limit: int = 30,
        level: str | None = None,
    ) -> "PipelineLogList":
        """Fetch logs for this pipeline.

        :param limit: Maximum number of log entries to return.
        :param level: Filter logs by level (info, warning, error). If None, returns all levels.

        :returns: A PipelineLogList containing the log entries.
        """
        return await self._resource.get_logs(pipeline_name=self._pipeline.name, limit=limit, level=level)
