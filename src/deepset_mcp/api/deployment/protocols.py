# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Protocol

from deepset_mcp.api.deployment.models import (
    Deployment,
    DeploymentEvent,
    DeploymentMetrics,
    DeploymentMode,
    DeploymentRevision,
    DeploymentRevisionDetail,
    DeploymentServiceLevel,
    DeploymentSourceType,
    DeploymentStatistics,
    DeploymentStatsGranularity,
)
from deepset_mcp.api.shared_models import NoContentResponse, PaginatedResponse


class DeploymentResourceProtocol(Protocol):
    """Protocol defining the implementation for DeploymentResource."""

    async def list_tags(self, name: str | None = None, order: str = "ASC") -> list[str]:
        """List distinct tag strings attached to deployments in the workspace."""
        ...

    async def create(
        self,
        name: str,
        description: str | None = None,
        group_label: str | None = None,
        origin_pipeline_id: str | None = None,
        deployment_mode: DeploymentMode = DeploymentMode.MANAGED,
        service_level: DeploymentServiceLevel = DeploymentServiceLevel.DEVELOPMENT,
        idle_timeout_in_seconds: int | None = None,
        min_query_replica_count: int | None = None,
        max_query_replica_count: int | None = None,
        max_index_replica_count: int | None = None,
        cpu_request: str | None = None,
        cpu_limit: str | None = None,
        memory_request: str | None = None,
        memory_limit: str | None = None,
        gpu_limit_gigabyte: int | None = None,
    ) -> Deployment:
        """Create a deployment, optionally linked to a pipeline."""
        ...

    async def get(self, deployment_id: str) -> Deployment:
        """Fetch a single deployment by its ID."""
        ...

    async def update(
        self,
        deployment_id: str,
        name: str | None = None,
        description: str | None = None,
        group_label: str | None = None,
        deployment_mode: DeploymentMode | None = None,
        service_level: DeploymentServiceLevel | None = None,
        idle_timeout_in_seconds: int | None = None,
        min_query_replica_count: int | None = None,
        max_query_replica_count: int | None = None,
        max_index_replica_count: int | None = None,
        cpu_request: str | None = None,
        cpu_limit: str | None = None,
        memory_request: str | None = None,
        memory_limit: str | None = None,
        gpu_limit_gigabyte: int | None = None,
    ) -> Deployment:
        """Update a deployment's metadata, sizing, or execution mode."""
        ...

    async def delete(self, deployment_id: str) -> NoContentResponse:
        """Delete a deployment along with all of its revisions."""
        ...

    async def add_tag(self, deployment_id: str, name: str) -> list[str]:
        """Add a tag to a deployment, returning the deployment's full tag list."""
        ...

    async def delete_tag(self, deployment_id: str, tag_name: str) -> list[str]:
        """Remove a tag from a deployment, returning the deployment's full tag list."""
        ...

    async def list_revisions(
        self, deployment_id: str, limit: int = 100, after: str | None = None
    ) -> PaginatedResponse[DeploymentRevision]:
        """List revisions of a deployment."""
        ...

    async def get_revision(self, deployment_id: str, revision_id: str) -> DeploymentRevisionDetail:
        """Fetch a single deployment revision, including its pipeline configuration YAML."""
        ...

    async def create_revision(
        self,
        deployment_id: str,
        comment: str,
        config_yaml: str | None = None,
        source_version_id: str | None = None,
        source_type: DeploymentSourceType = DeploymentSourceType.PLATFORM_PIPELINE,
    ) -> DeploymentRevision:
        """Push a new revision onto a deployment."""
        ...

    async def activate_revision(self, deployment_id: str, revision_id: str) -> Deployment:
        """Activate a revision, marking it as the deployment's desired served revision."""
        ...

    async def activate(self, deployment_id: str) -> Deployment:
        """Re-activate a deployment's current active revision."""
        ...

    async def deactivate(self, deployment_id: str) -> Deployment:
        """Mark a deployment as no longer desired to be served."""
        ...

    async def list_activity(
        self, deployment_id: str, limit: int = 100, after: str | None = None
    ) -> PaginatedResponse[DeploymentEvent]:
        """List activation and revision activity for a deployment."""
        ...

    async def get_metrics(self, deployment_id: str, start_ms: int, end_ms: int) -> DeploymentMetrics:
        """Fetch per-replica CPU/memory usage, resource limits, and replica counts for a deployment."""
        ...

    async def get_stats(
        self,
        deployment_id: str,
        days: int = 30,
        granularity: DeploymentStatsGranularity = DeploymentStatsGranularity.DAY,
        time_zone: str = "UTC",
    ) -> DeploymentStatistics:
        """Fetch query volume, outcome split and run durations for a deployment."""
        ...

    async def list(
        self,
        limit: int = 100,
        after: str | None = None,
        group_label: str | None = None,
        tags: list[str] | None = None,
    ) -> PaginatedResponse[Deployment]:
        """List deployments in the configured workspace."""
        ...
