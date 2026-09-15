# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any
from urllib.parse import quote

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
from deepset_mcp.api.deployment.protocols import DeploymentResourceProtocol
from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.shared_models import NoContentResponse, PaginatedResponse
from deepset_mcp.api.transport import raise_for_status


class DeploymentResource(DeploymentResourceProtocol):
    """Resource for managing deployments (AI Gateways) in a workspace."""

    def __init__(self, client: AsyncClientProtocol, workspace: str) -> None:
        """Initialize a DeploymentResource.

        :param client: The API client to use for requests.
        :param workspace: The workspace to operate in.
        """
        self._client = client
        self._workspace = workspace

    def _ws_path(self, *parts: str) -> str:
        """Build a workspace-scoped deployment path from URL-safe-quoted parts."""
        segments = "/".join(quote(part, safe="") for part in parts)
        return f"v1/workspaces/{quote(self._workspace, safe='')}/{segments}"

    async def list_tags(self, name: str | None = None, order: str = "ASC") -> list[str]:
        """List distinct tag strings attached to deployments in the workspace.

        :param name: Case-insensitive substring filter on tag names.
        :param order: Sort order for the returned tags (ASC or DESC).
        :returns: List of distinct tag names.
        """
        params = {k: v for k, v in {"name": name, "order": order}.items() if v is not None}
        resp = await self._client.request(
            endpoint=self._ws_path("deployment-tags"), method="GET", response_type=list[str], params=params
        )
        raise_for_status(resp)
        return resp.json or []

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
        """Create a deployment, optionally linked to a pipeline.

        Default service sizing follows Development unless explicit sizing fields are provided.

        :param name: Name of the deployment.
        :param description: Optional description.
        :param group_label: Optional label used to group related deployments.
        :param origin_pipeline_id: ID of the platform pipeline to link, if any.
        :param deployment_mode: Execution mode (MANAGED or SERVERLESS).
        :param service_level: Sizing tier (PRODUCTION, DEVELOPMENT, or CUSTOM).
        :param idle_timeout_in_seconds: Seconds of inactivity before scaling down.
        :param min_query_replica_count: Minimum number of query replicas.
        :param max_query_replica_count: Maximum number of query replicas.
        :param max_index_replica_count: Maximum number of index replicas.
        :param cpu_request: Requested CPU per replica.
        :param cpu_limit: CPU limit per replica.
        :param memory_request: Requested memory per replica.
        :param memory_limit: Memory limit per replica.
        :param gpu_limit_gigabyte: GPU memory limit in gigabytes.
        :returns: The created deployment.
        """
        data = {
            "name": name,
            "description": description,
            "group_label": group_label,
            "origin_pipeline_id": origin_pipeline_id,
            "deployment_mode": deployment_mode,
            "service_level": service_level,
            "idle_timeout_in_seconds": idle_timeout_in_seconds,
            "min_query_replica_count": min_query_replica_count,
            "max_query_replica_count": max_query_replica_count,
            "max_index_replica_count": max_index_replica_count,
            "cpu_request": cpu_request,
            "cpu_limit": cpu_limit,
            "memory_request": memory_request,
            "memory_limit": memory_limit,
            "gpu_limit_gigabyte": gpu_limit_gigabyte,
        }
        data = {k: v for k, v in data.items() if v is not None}

        resp = await self._client.request(
            endpoint=self._ws_path("deployments"), method="POST", data=data, response_type=dict[str, Any]
        )
        raise_for_status(resp)
        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)

        return Deployment(**resp.json)

    async def get(self, deployment_id: str) -> Deployment:
        """Fetch a single deployment by its ID.

        :param deployment_id: ID of the deployment to fetch.
        :returns: The deployment.
        """
        resp = await self._client.request(
            endpoint=self._ws_path("deployments", deployment_id), method="GET", response_type=dict[str, Any]
        )
        raise_for_status(resp)
        if resp.json is None:
            raise ResourceNotFoundError(f"Deployment '{deployment_id}' not found.")

        return Deployment(**resp.json)

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
        """Update a deployment's metadata, sizing, or execution mode.

        Only fields that are provided (not None) are changed.

        :param deployment_id: ID of the deployment to update.
        :returns: The updated deployment.
        """
        data = {
            "name": name,
            "description": description,
            "group_label": group_label,
            "deployment_mode": deployment_mode,
            "service_level": service_level,
            "idle_timeout_in_seconds": idle_timeout_in_seconds,
            "min_query_replica_count": min_query_replica_count,
            "max_query_replica_count": max_query_replica_count,
            "max_index_replica_count": max_index_replica_count,
            "cpu_request": cpu_request,
            "cpu_limit": cpu_limit,
            "memory_request": memory_request,
            "memory_limit": memory_limit,
            "gpu_limit_gigabyte": gpu_limit_gigabyte,
        }
        data = {k: v for k, v in data.items() if v is not None}
        if not data:
            raise ValueError("At least one field must be provided to update a deployment.")

        resp = await self._client.request(
            endpoint=self._ws_path("deployments", deployment_id),
            method="PATCH",
            data=data,
            response_type=dict[str, Any],
        )
        raise_for_status(resp)
        if resp.json is None:
            raise ResourceNotFoundError(f"Deployment '{deployment_id}' not found.")

        return Deployment(**resp.json)

    async def delete(self, deployment_id: str) -> NoContentResponse:
        """Delete a deployment along with all of its revisions.

        :param deployment_id: ID of the deployment to delete.
        :returns: NoContentResponse indicating successful deletion.
        """
        resp = await self._client.request(
            endpoint=self._ws_path("deployments", deployment_id), method="DELETE", response_type=None
        )
        raise_for_status(resp)
        return NoContentResponse(message="Deployment deleted successfully.")

    async def add_tag(self, deployment_id: str, name: str) -> list[str]:
        """Add a tag to a deployment.

        :param deployment_id: ID of the deployment.
        :param name: Tag name to add.
        :returns: The deployment's full tag list after the add.
        """
        resp = await self._client.request(
            endpoint=self._ws_path("deployments", deployment_id, "tags"),
            method="POST",
            data={"name": name},
            response_type=list[str],
        )
        raise_for_status(resp)
        return resp.json or []

    async def delete_tag(self, deployment_id: str, tag_name: str) -> list[str]:
        """Remove a tag from a deployment.

        :param deployment_id: ID of the deployment.
        :param tag_name: Tag name to remove.
        :returns: The deployment's full tag list after removal.
        """
        resp = await self._client.request(
            endpoint=self._ws_path("deployments", deployment_id, "tags", tag_name),
            method="DELETE",
            response_type=list[str],
        )
        raise_for_status(resp)
        return resp.json or []

    async def list_revisions(
        self, deployment_id: str, limit: int = 100, after: str | None = None
    ) -> PaginatedResponse[DeploymentRevision]:
        """List revisions of a deployment.

        :param deployment_id: ID of the deployment.
        :param limit: Maximum number of revisions to return per page.
        :param after: The cursor to fetch the next page of results.
        :returns: A `PaginatedResponse` object containing the first page of revisions.
        """
        request_params = {"limit": limit, "after": after}
        request_params = {k: v for k, v in request_params.items() if v is not None}

        page = await self._list_revisions_api_call(deployment_id, **request_params)

        page._inject_paginator(
            fetch_func=lambda **kwargs: self._list_revisions_api_call(deployment_id, **kwargs),
            base_args={"limit": limit},
        )
        return page

    async def _list_revisions_api_call(
        self, deployment_id: str, **kwargs: Any
    ) -> PaginatedResponse[DeploymentRevision]:
        """A private, stateless method that performs the raw API call."""
        resp = await self._client.request(
            endpoint=self._ws_path("deployments", deployment_id, "revisions"),
            method="GET",
            response_type=dict[str, Any],
            params=kwargs,
        )
        raise_for_status(resp)
        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)

        return PaginatedResponse[DeploymentRevision].create_with_cursor_field(resp.json, "revision_id")

    async def get_revision(self, deployment_id: str, revision_id: str) -> DeploymentRevisionDetail:
        """Fetch a single deployment revision, including its pipeline configuration YAML.

        :param deployment_id: ID of the deployment.
        :param revision_id: ID of the revision to fetch.
        :returns: The revision, including its config YAML.
        """
        resp = await self._client.request(
            endpoint=self._ws_path("deployments", deployment_id, "revisions", revision_id),
            method="GET",
            response_type=dict[str, Any],
        )
        raise_for_status(resp)
        if resp.json is None:
            raise ResourceNotFoundError(f"Revision '{revision_id}' not found on deployment '{deployment_id}'.")

        return DeploymentRevisionDetail(**resp.json)

    async def create_revision(
        self,
        deployment_id: str,
        comment: str,
        config_yaml: str | None = None,
        source_version_id: str | None = None,
        source_type: DeploymentSourceType = DeploymentSourceType.PLATFORM_PIPELINE,
    ) -> DeploymentRevision:
        """Push a new revision onto a deployment.

        :param deployment_id: ID of the deployment.
        :param comment: Comment describing the revision.
        :param config_yaml: Inline pipeline configuration YAML (for externally pushed revisions).
        :param source_version_id: ID of the source pipeline version (for platform pipeline revisions).
        :param source_type: Where the revision's pipeline configuration comes from.
        :returns: The newly created revision.
        """
        data = {
            "comment": comment,
            "config_yaml": config_yaml,
            "source_version_id": source_version_id,
            "source_type": source_type,
        }
        data = {k: v for k, v in data.items() if v is not None}

        resp = await self._client.request(
            endpoint=self._ws_path("deployments", deployment_id, "revisions"),
            method="POST",
            data=data,
            response_type=dict[str, Any],
        )
        raise_for_status(resp)
        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)

        return DeploymentRevision(**resp.json)

    async def activate_revision(self, deployment_id: str, revision_id: str) -> Deployment:
        """Activate a revision, marking it as the deployment's desired served revision.

        :param deployment_id: ID of the deployment.
        :param revision_id: ID of the revision to activate.
        :returns: The updated deployment.
        """
        resp = await self._client.request(
            endpoint=self._ws_path("deployments", deployment_id, "revisions", revision_id, "activate"),
            method="POST",
            response_type=dict[str, Any],
        )
        raise_for_status(resp)
        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)

        return Deployment(**resp.json)

    async def activate(self, deployment_id: str) -> Deployment:
        """Re-activate a deployment's current active revision, marking it as desired to be served.

        :param deployment_id: ID of the deployment.
        :returns: The updated deployment.
        """
        resp = await self._client.request(
            endpoint=self._ws_path("deployments", deployment_id, "activate"),
            method="POST",
            response_type=dict[str, Any],
        )
        raise_for_status(resp)
        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)

        return Deployment(**resp.json)

    async def deactivate(self, deployment_id: str) -> Deployment:
        """Mark a deployment as no longer desired to be served, keeping its active revision.

        :param deployment_id: ID of the deployment.
        :returns: The updated deployment.
        """
        resp = await self._client.request(
            endpoint=self._ws_path("deployments", deployment_id, "deactivate"),
            method="POST",
            response_type=dict[str, Any],
        )
        raise_for_status(resp)
        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)

        return Deployment(**resp.json)

    async def list_activity(
        self, deployment_id: str, limit: int = 100, after: str | None = None
    ) -> PaginatedResponse[DeploymentEvent]:
        """List activation and revision activity for a deployment.

        :param deployment_id: ID of the deployment.
        :param limit: Maximum number of events to return per page.
        :param after: The cursor to fetch the next page of results.
        :returns: A `PaginatedResponse` object containing the first page of events.
        """
        request_params = {"limit": limit, "after": after}
        request_params = {k: v for k, v in request_params.items() if v is not None}

        page = await self._list_activity_api_call(deployment_id, **request_params)

        page._inject_paginator(
            fetch_func=lambda **kwargs: self._list_activity_api_call(deployment_id, **kwargs),
            base_args={"limit": limit},
        )
        return page

    async def _list_activity_api_call(self, deployment_id: str, **kwargs: Any) -> PaginatedResponse[DeploymentEvent]:
        """A private, stateless method that performs the raw API call."""
        resp = await self._client.request(
            endpoint=self._ws_path("deployments", deployment_id, "activity"),
            method="GET",
            response_type=dict[str, Any],
            params=kwargs,
        )
        raise_for_status(resp)
        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)

        return PaginatedResponse[DeploymentEvent].create_with_cursor_field(resp.json, "event_id")

    async def get_metrics(self, deployment_id: str, start_ms: int, end_ms: int) -> DeploymentMetrics:
        """Fetch per-replica CPU/memory usage, resource limits, and replica counts for a deployment.

        :param deployment_id: ID of the deployment.
        :param start_ms: Start of the time range, in unix milliseconds.
        :param end_ms: End of the time range, in unix milliseconds.
        :returns: Deployment metrics for the given time range.
        """
        resp = await self._client.request(
            endpoint=self._ws_path("deployments", deployment_id, "metrics"),
            method="GET",
            response_type=dict[str, Any],
            params={"start": start_ms, "end": end_ms},
        )
        raise_for_status(resp)
        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)

        return DeploymentMetrics(**resp.json)

    async def get_stats(
        self,
        deployment_id: str,
        days: int = 30,
        granularity: DeploymentStatsGranularity = DeploymentStatsGranularity.DAY,
        time_zone: str = "UTC",
    ) -> DeploymentStatistics:
        """Fetch query volume, outcome split and run durations for a deployment.

        :param deployment_id: ID of the deployment.
        :param days: Size of the rolling window, in days (1-90).
        :param granularity: Bucket width for the returned series.
        :param time_zone: IANA time zone used to bucket the series.
        :returns: Deployment statistics for the given window.
        """
        resp = await self._client.request(
            endpoint=self._ws_path("deployments", deployment_id, "stats"),
            method="GET",
            response_type=dict[str, Any],
            params={"days": days, "granularity": granularity, "time_zone": time_zone},
        )
        raise_for_status(resp)
        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)

        return DeploymentStatistics(**resp.json)

    async def list(
        self,
        limit: int = 100,
        after: str | None = None,
        group_label: str | None = None,
        tags: list[str] | None = None,
    ) -> PaginatedResponse[Deployment]:
        """List deployments in the configured workspace.

        :param limit: Maximum number of deployments to return per page.
        :param after: The cursor to fetch the next page of results.
        :param group_label: Filter deployments by group label.
        :param tags: Filter deployments by tags (matches if any tag is present).
        :returns: A `PaginatedResponse` object containing the first page of deployments.
        """
        request_params = {"limit": limit, "after": after, "group_label": group_label, "tags": tags}
        request_params = {k: v for k, v in request_params.items() if v is not None}

        page = await self._list_api_call(**request_params)

        page._inject_paginator(
            fetch_func=self._list_api_call,
            base_args={"limit": limit, "group_label": group_label, "tags": tags},
        )
        return page

    async def _list_api_call(self, **kwargs: Any) -> PaginatedResponse[Deployment]:
        """A private, stateless method that performs the raw API call."""
        resp = await self._client.request(
            endpoint=self._ws_path("deployments"), method="GET", response_type=dict[str, Any], params=kwargs
        )
        raise_for_status(resp)
        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)

        return PaginatedResponse[Deployment].create_with_cursor_field(resp.json, "deployment_id")
