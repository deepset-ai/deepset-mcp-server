# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

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
from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.shared_models import NoContentResponse, PaginatedResponse


async def list_deployments(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    after: str | None = None,
    group_label: str | None = None,
    tags: list[str] | None = None,
) -> PaginatedResponse[Deployment] | str:
    """Lists deployments (AI Gateways) in the currently configured deepset workspace.

    A deployment serves a pipeline behind a stable endpoint, independent of the pipeline's own
    draft/version history.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param after: The cursor to fetch the next page of results.
    :param group_label: Filter deployments by group label.
    :param tags: Filter deployments by tags (matches if any tag is present).
    :returns: Paginated list of deployments or error message.
    """
    try:
        return await client.deployments(workspace=workspace).list(after=after, group_label=group_label, tags=tags)
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list deployments: {e}"


async def list_deployment_tags(
    *, client: AsyncClientProtocol, workspace: str, name: str | None = None, order: str = "ASC"
) -> list[str] | str:
    """Lists distinct tag strings attached to deployments in the workspace.

    Useful for autocomplete when adding tags, or to see how deployments are currently grouped.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param name: Case-insensitive substring filter on tag names.
    :param order: Sort order for the returned tags, "ASC" or "DESC" (default "ASC").
    :returns: List of distinct tag names or error message.
    """
    try:
        return await client.deployments(workspace=workspace).list_tags(name=name, order=order)
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list deployment tags: {e}"


async def create_deployment(
    *,
    client: AsyncClientProtocol,
    workspace: str,
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
) -> Deployment | str:
    """Creates a new deployment (AI Gateway), optionally linked to a pipeline.

    A deployment created without an `origin_pipeline_id` has no active revision until you call
    `create_deployment_revision` and `activate_deployment_revision`. Default service sizing follows
    Development unless explicit sizing fields are provided.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param name: Name of the deployment.
    :param description: Optional description.
    :param group_label: Optional label used to group related deployments.
    :param origin_pipeline_id: ID of the platform pipeline to link, if any.
    :param deployment_mode: Execution mode, "MANAGED" or "SERVERLESS" (default "MANAGED").
    :param service_level: Sizing tier, "PRODUCTION", "DEVELOPMENT", or "CUSTOM" (default "DEVELOPMENT").
    :param idle_timeout_in_seconds: Seconds of inactivity before scaling down.
    :param min_query_replica_count: Minimum number of query replicas.
    :param max_query_replica_count: Maximum number of query replicas.
    :param max_index_replica_count: Maximum number of index replicas.
    :param cpu_request: Requested CPU per replica.
    :param cpu_limit: CPU limit per replica.
    :param memory_request: Requested memory per replica.
    :param memory_limit: Memory limit per replica.
    :param gpu_limit_gigabyte: GPU memory limit in gigabytes.
    :returns: The created deployment or error message.
    """
    try:
        return await client.deployments(workspace=workspace).create(
            name=name,
            description=description,
            group_label=group_label,
            origin_pipeline_id=origin_pipeline_id,
            deployment_mode=deployment_mode,
            service_level=service_level,
            idle_timeout_in_seconds=idle_timeout_in_seconds,
            min_query_replica_count=min_query_replica_count,
            max_query_replica_count=max_query_replica_count,
            max_index_replica_count=max_index_replica_count,
            cpu_request=cpu_request,
            cpu_limit=cpu_limit,
            memory_request=memory_request,
            memory_limit=memory_limit,
            gpu_limit_gigabyte=gpu_limit_gigabyte,
        )
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to create deployment '{name}': {e}"


async def get_deployment(*, client: AsyncClientProtocol, workspace: str, deployment_id: str) -> Deployment | str:
    """Fetches details for a specific deployment, including its active revision and runtime status.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param deployment_id: ID of the deployment to fetch.
    :returns: Deployment details or error message.
    """
    try:
        return await client.deployments(workspace=workspace).get(deployment_id=deployment_id)
    except ResourceNotFoundError:
        return f"There is no deployment with ID '{deployment_id}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to fetch deployment '{deployment_id}': {e}"


async def update_deployment(
    *,
    client: AsyncClientProtocol,
    workspace: str,
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
) -> Deployment | str:
    """Updates a deployment's metadata, sizing, or execution mode.

    Only fields you provide are changed; omitted fields keep their current value.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param deployment_id: ID of the deployment to update.
    :param name: New name for the deployment.
    :param description: New description.
    :param group_label: New group label.
    :param deployment_mode: New execution mode, "MANAGED" or "SERVERLESS".
    :param service_level: New sizing tier, "PRODUCTION", "DEVELOPMENT", or "CUSTOM".
    :param idle_timeout_in_seconds: New idle timeout, in seconds.
    :param min_query_replica_count: New minimum number of query replicas.
    :param max_query_replica_count: New maximum number of query replicas.
    :param max_index_replica_count: New maximum number of index replicas.
    :param cpu_request: New requested CPU per replica.
    :param cpu_limit: New CPU limit per replica.
    :param memory_request: New requested memory per replica.
    :param memory_limit: New memory limit per replica.
    :param gpu_limit_gigabyte: New GPU memory limit in gigabytes.
    :returns: The updated deployment or error message.
    """
    try:
        return await client.deployments(workspace=workspace).update(
            deployment_id=deployment_id,
            name=name,
            description=description,
            group_label=group_label,
            deployment_mode=deployment_mode,
            service_level=service_level,
            idle_timeout_in_seconds=idle_timeout_in_seconds,
            min_query_replica_count=min_query_replica_count,
            max_query_replica_count=max_query_replica_count,
            max_index_replica_count=max_index_replica_count,
            cpu_request=cpu_request,
            cpu_limit=cpu_limit,
            memory_request=memory_request,
            memory_limit=memory_limit,
            gpu_limit_gigabyte=gpu_limit_gigabyte,
        )
    except ValueError as e:
        return str(e)
    except ResourceNotFoundError:
        return f"There is no deployment with ID '{deployment_id}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to update deployment '{deployment_id}': {e}"


async def delete_deployment(
    *, client: AsyncClientProtocol, workspace: str, deployment_id: str
) -> NoContentResponse | str:
    """Deletes a deployment along with all of its revisions. This cannot be undone.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param deployment_id: ID of the deployment to delete.
    :returns: Confirmation or error message.
    """
    try:
        return await client.deployments(workspace=workspace).delete(deployment_id=deployment_id)
    except ResourceNotFoundError:
        return f"There is no deployment with ID '{deployment_id}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to delete deployment '{deployment_id}': {e}"


async def add_deployment_tag(
    *, client: AsyncClientProtocol, workspace: str, deployment_id: str, tag_name: str
) -> list[str] | str:
    """Adds a tag to a deployment. Each deployment supports at most three tags.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param deployment_id: ID of the deployment.
    :param tag_name: Tag to add (1-50 characters; letters, digits, spaces, underscores, hyphens).
    :returns: The deployment's full tag list after the add, or error message.
    """
    try:
        return await client.deployments(workspace=workspace).add_tag(deployment_id=deployment_id, name=tag_name)
    except ResourceNotFoundError:
        return f"There is no deployment with ID '{deployment_id}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to add tag '{tag_name}' to deployment '{deployment_id}': {e}"


async def delete_deployment_tag(
    *, client: AsyncClientProtocol, workspace: str, deployment_id: str, tag_name: str
) -> list[str] | str:
    """Removes a tag from a deployment. Tag matching is case-insensitive.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param deployment_id: ID of the deployment.
    :param tag_name: Tag to remove.
    :returns: The deployment's full tag list after removal, or error message.
    """
    try:
        return await client.deployments(workspace=workspace).delete_tag(deployment_id=deployment_id, tag_name=tag_name)
    except ResourceNotFoundError:
        return f"There is no deployment with ID '{deployment_id}' or tag '{tag_name}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to remove tag '{tag_name}' from deployment '{deployment_id}': {e}"


async def list_deployment_revisions(
    *, client: AsyncClientProtocol, workspace: str, deployment_id: str, after: str | None = None
) -> PaginatedResponse[DeploymentRevision] | str:
    """Lists revisions of a deployment, i.e. the history of pipeline configurations it has served.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param deployment_id: ID of the deployment.
    :param after: The cursor to fetch the next page of results.
    :returns: Paginated list of revisions or error message.
    """
    try:
        return await client.deployments(workspace=workspace).list_revisions(deployment_id=deployment_id, after=after)
    except ResourceNotFoundError:
        return f"There is no deployment with ID '{deployment_id}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list revisions for deployment '{deployment_id}': {e}"


async def get_deployment_revision(
    *, client: AsyncClientProtocol, workspace: str, deployment_id: str, revision_id: str
) -> DeploymentRevisionDetail | str:
    """Fetches a single deployment revision, including the pipeline configuration YAML it serves.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param deployment_id: ID of the deployment.
    :param revision_id: ID of the revision to fetch.
    :returns: The revision, including its config YAML, or error message.
    """
    try:
        return await client.deployments(workspace=workspace).get_revision(
            deployment_id=deployment_id, revision_id=revision_id
        )
    except ResourceNotFoundError:
        return f"There is no revision '{revision_id}' on deployment '{deployment_id}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to fetch revision '{revision_id}' for deployment '{deployment_id}': {e}"


async def create_deployment_revision(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    deployment_id: str,
    comment: str,
    config_yaml: str | None = None,
    source_version_id: str | None = None,
    source_type: DeploymentSourceType = DeploymentSourceType.PLATFORM_PIPELINE,
) -> DeploymentRevision | str:
    """Pushes a new revision onto a deployment, e.g. from a platform pipeline version.

    Creating a revision does not serve it automatically; call `activate_deployment_revision`
    to make it the deployment's served revision.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param deployment_id: ID of the deployment.
    :param comment: Comment describing the revision.
    :param config_yaml: Inline pipeline configuration YAML, for an externally pushed revision.
    :param source_version_id: ID of the source pipeline version, for a platform pipeline revision.
    :param source_type: Where the revision's pipeline configuration comes from, "PLATFORM_PIPELINE"
        (default) or "EXTERNAL_PIPELINE".
    :returns: The newly created revision or error message.
    """
    try:
        return await client.deployments(workspace=workspace).create_revision(
            deployment_id=deployment_id,
            comment=comment,
            config_yaml=config_yaml,
            source_version_id=source_version_id,
            source_type=source_type,
        )
    except ResourceNotFoundError:
        return f"There is no deployment with ID '{deployment_id}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to create revision for deployment '{deployment_id}': {e}"


async def activate_deployment_revision(
    *, client: AsyncClientProtocol, workspace: str, deployment_id: str, revision_id: str
) -> Deployment | str:
    """Activates a revision, marking it as the deployment's desired served revision.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param deployment_id: ID of the deployment.
    :param revision_id: ID of the revision to activate.
    :returns: The updated deployment or error message.
    """
    try:
        return await client.deployments(workspace=workspace).activate_revision(
            deployment_id=deployment_id, revision_id=revision_id
        )
    except ResourceNotFoundError:
        return f"There is no revision '{revision_id}' on deployment '{deployment_id}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to activate revision '{revision_id}' for deployment '{deployment_id}': {e}"


async def activate_deployment(*, client: AsyncClientProtocol, workspace: str, deployment_id: str) -> Deployment | str:
    """Re-activates a deployment's current active revision, marking it as desired to be served.

    Use this to bring a deactivated deployment back online without pushing a new revision.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param deployment_id: ID of the deployment.
    :returns: The updated deployment or error message.
    """
    try:
        return await client.deployments(workspace=workspace).activate(deployment_id=deployment_id)
    except ResourceNotFoundError:
        return f"There is no deployment with ID '{deployment_id}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to activate deployment '{deployment_id}': {e}"


async def deactivate_deployment(*, client: AsyncClientProtocol, workspace: str, deployment_id: str) -> Deployment | str:
    """Marks a deployment as no longer desired to be served, keeping its active revision intact.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param deployment_id: ID of the deployment.
    :returns: The updated deployment or error message.
    """
    try:
        return await client.deployments(workspace=workspace).deactivate(deployment_id=deployment_id)
    except ResourceNotFoundError:
        return f"There is no deployment with ID '{deployment_id}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to deactivate deployment '{deployment_id}': {e}"


async def list_deployment_activity(
    *, client: AsyncClientProtocol, workspace: str, deployment_id: str, after: str | None = None
) -> PaginatedResponse[DeploymentEvent] | str:
    """Lists activation and revision activity for a deployment.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param deployment_id: ID of the deployment.
    :param after: The cursor to fetch the next page of results.
    :returns: Paginated list of activity events or error message.
    """
    try:
        return await client.deployments(workspace=workspace).list_activity(deployment_id=deployment_id, after=after)
    except ResourceNotFoundError:
        return f"There is no deployment with ID '{deployment_id}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list activity for deployment '{deployment_id}': {e}"


async def get_deployment_metrics(
    *, client: AsyncClientProtocol, workspace: str, deployment_id: str, start_ms: int, end_ms: int
) -> DeploymentMetrics | str:
    """Fetches per-replica CPU/memory usage, resource limits, and replica counts for a deployment.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param deployment_id: ID of the deployment.
    :param start_ms: Start of the time range, in unix milliseconds.
    :param end_ms: End of the time range, in unix milliseconds.
    :returns: Deployment metrics or error message.
    """
    try:
        return await client.deployments(workspace=workspace).get_metrics(
            deployment_id=deployment_id, start_ms=start_ms, end_ms=end_ms
        )
    except ResourceNotFoundError:
        return f"There is no deployment with ID '{deployment_id}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to fetch metrics for deployment '{deployment_id}': {e}"


async def get_deployment_stats(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    deployment_id: str,
    days: int = 30,
    granularity: DeploymentStatsGranularity = DeploymentStatsGranularity.DAY,
    time_zone: str = "UTC",
) -> DeploymentStatistics | str:
    """Fetches query volume, outcome split, and run durations for a deployment.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param deployment_id: ID of the deployment.
    :param days: Size of the rolling window, in days (1-90, default 30).
    :param granularity: Bucket width for the returned series, "DAY" (default) or "HOUR".
    :param time_zone: IANA time zone used to bucket the series (default "UTC").
    :returns: Deployment statistics or error message.
    """
    try:
        return await client.deployments(workspace=workspace).get_stats(
            deployment_id=deployment_id, days=days, granularity=granularity, time_zone=time_zone
        )
    except ResourceNotFoundError:
        return f"There is no deployment with ID '{deployment_id}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to fetch stats for deployment '{deployment_id}': {e}"
