# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from collections.abc import AsyncIterator, Sequence
from typing import Any, Protocol

from deepset_mcp.api.pipeline.models import (
    DeepsetPipeline,
    DeepsetSearchResponse,
    DeepsetStreamEvent,
    LogLevel,
    PipelineDebugBreakpoint,
    PipelineDebugResult,
    PipelineLog,
    PipelineValidationResult,
    PipelineVersion,
)
from deepset_mcp.api.shared_models import NoContentResponse, PaginatedResponse


class PipelineResourceProtocol(Protocol):
    """Protocol defining the implementation for PipelineResource."""

    async def validate(self, yaml_config: str) -> PipelineValidationResult:
        """Validate a pipeline's YAML configuration against the API."""
        ...

    async def get(self, pipeline_name: str) -> DeepsetPipeline:
        """Fetch a single pipeline by its name."""
        ...

    async def list(self, limit: int = 100, after: str | None = None) -> PaginatedResponse[DeepsetPipeline]:
        """List pipelines in the configured workspace with optional pagination."""
        ...

    async def create(self, pipeline_name: str, yaml_config: str) -> NoContentResponse:
        """Create a new pipeline with a name and YAML config."""
        ...

    async def list_versions(
        self,
        pipeline_name: str,
        limit: int = 100,
        after: str | None = None,
    ) -> PaginatedResponse[PipelineVersion]:
        """List versions of a pipeline."""
        ...

    async def create_version(
        self,
        pipeline_name: str,
        config_yaml: str,
        description: str | None = None,
        is_draft: bool = False,
    ) -> PipelineVersion:
        """Create a new version of a pipeline."""
        ...

    async def get_version(self, pipeline_name: str, version_id: str, include_yaml: bool = True) -> PipelineVersion:
        """Fetch a specific version of a pipeline."""
        ...

    async def restore_version(self, pipeline_name: str, version_id: str) -> PipelineVersion:
        """Restore a pipeline to a previous version."""
        ...

    async def patch_version(
        self,
        pipeline_name: str,
        version_id: str,
        config_yaml: str | None = None,
        description: str | None = None,
        is_draft: bool | None = None,
    ) -> PipelineVersion:
        """Patch fields of an existing pipeline version."""
        ...

    async def get_logs(
        self,
        pipeline_name: str,
        limit: int = 30,
        level: LogLevel | None = None,
        after: str | None = None,
    ) -> PaginatedResponse[PipelineLog]:
        """Fetch logs for a specific pipeline."""
        ...

    async def deploy(self, pipeline_name: str, version_id: str | None = None) -> PipelineValidationResult:
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

    async def debug(
        self,
        *,
        pipeline_config: dict[str, Any],
        inputs: dict[str, Any] | None = None,
        break_at: PipelineDebugBreakpoint | None = None,
        resume_from: dict[str, Any] | None = None,
        files: Sequence[str] | None = None,
        pipeline_id: str | None = None,
        pipeline_version_id: str | None = None,
        dry_run: bool = False,
    ) -> PipelineDebugResult:
        """Run a pipeline configuration in debug mode: pin a breakpoint, resume a snapshot, or trace a full run."""
        ...
