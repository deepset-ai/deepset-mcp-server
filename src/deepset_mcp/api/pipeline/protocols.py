# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from collections.abc import AsyncIterator
from typing import Any, Protocol

from deepset_mcp.api.pipeline.log_level import LogLevel
from deepset_mcp.api.pipeline.models import (
    DeepsetPipeline,
    DeepsetSearchResponse,
    DeepsetStreamEvent,
    PipelineList,
    PipelineLogList,
    PipelineValidationResult,
)
from deepset_mcp.api.shared_models import NoContentResponse


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
    ) -> PipelineList:
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

    async def delete(self, pipeline_name: str) -> NoContentResponse:
        """Delete a pipeline."""
        ...
