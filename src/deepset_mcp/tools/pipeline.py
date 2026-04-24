# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
from typing import Any

import yaml
from pydantic import BaseModel

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.pipeline.models import (
    DeepsetPipeline,
    DeepsetSearchResponse,
    LogLevel,
    PipelineLog,
    PipelineValidationResult,
    PipelineVersion,
)
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.shared_models import PaginatedResponse


async def list_pipelines(
    *, client: AsyncClientProtocol, workspace: str, after: str | None = None
) -> PaginatedResponse[DeepsetPipeline] | str:
    """Retrieves a list of all pipeline available within the currently configured deepset workspace.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param after: The cursor to fetch the next page of results.
        If there are more results to fetch, the cursor will appear as `next_cursor` on the response.
    :returns: List of pipelines or error message.
    """
    try:
        return await client.pipelines(workspace=workspace).list(after=after)
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list pipelines: {e}"


async def get_pipeline(*, client: AsyncClientProtocol, workspace: str, pipeline_name: str) -> DeepsetPipeline | str:
    """Fetches detailed configuration information for a specific pipeline, identified by its unique `pipeline_name`.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: The name of the pipeline to fetch.
    :returns: Pipeline details or error message.
    """
    try:
        return await client.pipelines(workspace=workspace).get(pipeline_name=pipeline_name)
    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to fetch pipeline '{pipeline_name}': {e}"


class PipelineValidationResultWithYaml(BaseModel):
    """Model for pipeline validation result that includes the original YAML."""

    validation_result: PipelineValidationResult
    "Result of validating the pipeline configuration"
    yaml_config: str
    "Original YAML configuration that was validated"


async def validate_pipeline(
    *, client: AsyncClientProtocol, workspace: str, yaml_configuration: str
) -> PipelineValidationResultWithYaml | str:
    """Validates the provided pipeline YAML configuration against the deepset API.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param yaml_configuration: The YAML configuration to validate.
    :returns: Validation result with original YAML or error message.
    """
    if not yaml_configuration or not yaml_configuration.strip():
        return "You need to provide a YAML configuration to validate."

    try:
        yaml.safe_load(yaml_configuration)
    except yaml.YAMLError as e:
        return f"Invalid YAML provided: {e}"

    try:
        response = await client.pipelines(workspace=workspace).validate(yaml_configuration)
        return PipelineValidationResultWithYaml(validation_result=response, yaml_config=yaml_configuration)
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to validate pipeline: {e}"


class PipelineOperationWithErrors(BaseModel):
    """Model for pipeline operations that complete with validation errors."""

    message: str
    "Descriptive message about the pipeline operation"
    validation_result: PipelineValidationResult
    "Validation errors encountered during the operation"
    pipeline: DeepsetPipeline
    "Pipeline object after the operation completed"


async def create_pipeline(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    yaml_configuration: str,
    skip_validation_errors: bool = True,
) -> DeepsetPipeline | PipelineOperationWithErrors | str:
    """Creates a new pipeline within the currently configured deepset workspace.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline to create.
    :param yaml_configuration: YAML configuration for the pipeline.
    :param skip_validation_errors: If True (default), creates the pipeline even if validation fails.
                                  If False, stops creation when validation fails.
    :returns: Created pipeline or error message.
    """
    try:
        validation_response = await client.pipelines(workspace=workspace).validate(yaml_configuration)

        if not validation_response.valid and not skip_validation_errors:
            error_messages = [f"{error.code}: {error.message}" for error in validation_response.errors]
            return "Pipeline validation failed:\n" + "\n".join(error_messages)

        await client.pipelines(workspace=workspace).create(name=pipeline_name, yaml_config=yaml_configuration)

        # Get the full pipeline after creation
        pipeline = await client.pipelines(workspace=workspace).get(pipeline_name)

        # If validation failed but we proceeded anyway, return the special model
        if not validation_response.valid:
            return PipelineOperationWithErrors(
                message="The operation completed with errors", validation_result=validation_response, pipeline=pipeline
            )

        # Otherwise return just the pipeline
        return pipeline

    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except BadRequestError as e:
        return f"Failed to create pipeline '{pipeline_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to create pipeline '{pipeline_name}': {e}"


async def list_pipeline_versions(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    after: str | None = None,
) -> PaginatedResponse[PipelineVersion] | str:
    """Lists all versions of a pipeline, ordered by version number descending (newest first).

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline to list versions for.
    :param after: Cursor (version_id UUID) to fetch the next page of results.
    :returns: Paginated list of pipeline versions or error message.
    """
    try:
        return await client.pipelines(workspace=workspace).list_versions(
            pipeline_name=pipeline_name, after=after
        )
    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list versions for pipeline '{pipeline_name}': {e}"


async def create_pipeline_version(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    yaml_configuration: str,
    description: str | None = None,
    is_draft: bool = False,
) -> PipelineVersion | str:
    """Creates a new version of an existing pipeline with the provided YAML configuration.

    Use this to update a pipeline's configuration. Each call creates a new immutable version,
    preserving the full history of changes.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline to create a version for.
    :param yaml_configuration: The new YAML configuration for this version.
    :param description: Optional description of what changed in this version.
    :param is_draft: If True, the version is created as a draft (default: False).
    :returns: The newly created pipeline version or error message.
    """
    if not yaml_configuration or not yaml_configuration.strip():
        return "You need to provide a YAML configuration to create a version."

    try:
        yaml.safe_load(yaml_configuration)
    except yaml.YAMLError as e:
        return f"Invalid YAML provided: {e}"

    try:
        return await client.pipelines(workspace=workspace).create_version(
            pipeline_name=pipeline_name,
            config_yaml=yaml_configuration,
            description=description,
            is_draft=is_draft,
        )
    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to create version for pipeline '{pipeline_name}': {e}"


async def get_pipeline_version(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    version_id: str,
) -> PipelineVersion | str:
    """Fetches a specific version of a pipeline by its version ID.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param version_id: UUID of the version to fetch.
    :returns: Pipeline version details or error message.
    """
    try:
        return await client.pipelines(workspace=workspace).get_version(
            pipeline_name=pipeline_name, version_id=version_id
        )
    except ResourceNotFoundError:
        return f"There is no version '{version_id}' for pipeline '{pipeline_name}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to fetch version '{version_id}' for pipeline '{pipeline_name}': {e}"


async def restore_pipeline_version(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    version_id: str,
) -> PipelineVersion | str:
    """Restores a pipeline to a previous version, making that version the active configuration.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline to restore.
    :param version_id: UUID of the version to restore.
    :returns: The restored pipeline version or error message.
    """
    try:
        return await client.pipelines(workspace=workspace).restore_version(
            pipeline_name=pipeline_name, version_id=version_id
        )
    except ResourceNotFoundError:
        return f"There is no version '{version_id}' for pipeline '{pipeline_name}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to restore version '{version_id}' for pipeline '{pipeline_name}': {e}"


async def patch_pipeline_version(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    version_id: str,
    yaml_configuration: str | None = None,
    description: str | None = None,
    is_draft: bool | None = None,
) -> PipelineVersion | str:
    """Updates fields of an existing pipeline version in place.

    At least one of yaml_configuration, description, or is_draft must be provided.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param version_id: UUID of the version to update.
    :param yaml_configuration: New YAML configuration for the version (optional).
    :param description: New description for the version (optional).
    :param is_draft: New draft status for the version (optional).
    :returns: The updated pipeline version or error message.
    """
    if yaml_configuration is None and description is None and is_draft is None:
        return "At least one of yaml_configuration, description, or is_draft must be provided."

    if yaml_configuration is not None:
        if not yaml_configuration.strip():
            return "yaml_configuration cannot be empty."
        try:
            yaml.safe_load(yaml_configuration)
        except yaml.YAMLError as e:
            return f"Invalid YAML provided: {e}"

    try:
        return await client.pipelines(workspace=workspace).patch_version(
            pipeline_name=pipeline_name,
            version_id=version_id,
            config_yaml=yaml_configuration,
            description=description,
            is_draft=is_draft,
        )
    except ResourceNotFoundError:
        return f"There is no version '{version_id}' for pipeline '{pipeline_name}' in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to update version '{version_id}' for pipeline '{pipeline_name}': {e}"


async def get_pipeline_logs(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    limit: int = 30,
    level: LogLevel | None = None,
    after: str | None = None,
) -> PaginatedResponse[PipelineLog] | str:
    """Fetches logs for a specific pipeline.

    Retrieves log entries for the specified pipeline, with optional filtering by log level.
    This is useful for debugging pipeline issues or monitoring pipeline execution.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline to fetch logs for.
    :param limit: Maximum number of log entries to return (default: 30).
    :param level: Filter logs by level. If None, returns all levels.
    :param after: The cursor to fetch the next page of results.

    :returns: Pipeline logs or error message.
    """
    try:
        return await client.pipelines(workspace=workspace).get_logs(
            pipeline_name=pipeline_name, limit=limit, level=level, after=after
        )
    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}'."
    except BadRequestError as e:
        return f"Failed to fetch logs for pipeline '{pipeline_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to fetch logs for pipeline '{pipeline_name}': {e}"


async def deploy_pipeline(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    wait_for_deployment: bool = False,
    timeout_seconds: float = 600,
    poll_interval: float = 10,
) -> PipelineValidationResult | str:
    """Deploys a pipeline to production.

    This function attempts to deploy the specified pipeline in the given workspace.
    If the deployment fails due to validation errors, it returns a validation result.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline to deploy.
    :param wait_for_deployment: If True, waits for the pipeline to reach DEPLOYED status.
    :param timeout_seconds: Maximum time to wait for deployment when wait_for_deployment is True (default: 600.0).
    :param poll_interval: Time between status checks in seconds when wait_for_deployment is True (default: 10.0).

    :returns: Deployment validation result or error message.
    """
    try:
        deployment_result = await client.pipelines(workspace=workspace).deploy(pipeline_name=pipeline_name)
    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}'."
    except BadRequestError as e:
        return f"Failed to deploy pipeline '{pipeline_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to deploy pipeline '{pipeline_name}': {e}"

    if not deployment_result.valid:
        return deployment_result

    # If not waiting for deployment, return success immediately
    if not wait_for_deployment:
        return deployment_result

    start_time = asyncio.get_event_loop().time()

    while True:
        current_time = asyncio.get_event_loop().time()
        if current_time - start_time > timeout_seconds:
            return (
                f"Pipeline '{pipeline_name}' deployment initiated successfully, but did not reach DEPLOYED status "
                f"within {timeout_seconds} seconds. You can check the pipeline status manually."
            )

        try:
            # Get the current pipeline status
            pipeline = await client.pipelines(workspace=workspace).get(pipeline_name=pipeline_name, include_yaml=False)

            if pipeline.status == "DEPLOYED":
                return deployment_result  # Return the successful validation result
            elif pipeline.status == "FAILED":
                return f"Pipeline '{pipeline_name}' deployment failed. Current status: FAILED."

            # Wait before next poll
            await asyncio.sleep(poll_interval)

        except Exception as e:
            return f"Pipeline '{pipeline_name}' deployment initiated, but failed to check deployment status: {e}"


async def search_pipeline(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str, query: str
) -> DeepsetSearchResponse | str:
    """Searches using a pipeline.

    Uses the specified pipeline to perform a search with the given query.
    Before executing the search, checks if the pipeline is deployed (status = DEPLOYED).
    Returns search results.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline to use for search.
    :param query: The search query to execute.

    :returns: Search results or error message.
    """
    try:
        # First, check if the pipeline exists and get its status
        pipeline = await client.pipelines(workspace=workspace).get(pipeline_name=pipeline_name)

        # Check if pipeline is deployed
        if pipeline.status != "DEPLOYED":
            return (
                f"Pipeline '{pipeline_name}' is not deployed (current status: {pipeline.status}). "
                f"Please deploy the pipeline first using the deploy_pipeline tool before attempting to search."
            )

        # Execute the search
        return await client.pipelines(workspace=workspace).search(pipeline_name=pipeline_name, query=query)

    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}'."
    except BadRequestError as e:
        return f"Failed to search using pipeline '{pipeline_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to search using pipeline '{pipeline_name}': {e}"
    except Exception as e:
        return f"An unexpected error occurred while searching with pipeline '{pipeline_name}': {str(e)}"


async def search_pipeline_with_filters(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    query: str,
    filters: dict[str, Any] | None = None,
) -> DeepsetSearchResponse | str:
    """Searches using a pipeline with filters.

    Uses the specified pipeline to perform a search with the given query and filters.
    Filters follow the Haystack filter syntax: https://docs.haystack.deepset.ai/docs/metadata-filtering.
    Before executing the search, checks if the pipeline is deployed (status = DEPLOYED).
    Returns search results.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline to use for search.
    :param query: The search query to execute.
    :param filters: The filters to apply to the search.

    :returns: Search results or error message.
    """
    try:
        # First, check if the pipeline exists and get its status
        pipeline = await client.pipelines(workspace=workspace).get(pipeline_name=pipeline_name)

        # Check if pipeline is deployed
        if pipeline.status != "DEPLOYED":
            return (
                f"Pipeline '{pipeline_name}' is not deployed (current status: {pipeline.status}). "
                f"Please deploy the pipeline first using the deploy_pipeline tool before attempting to search."
            )

        # Execute the search
        return await client.pipelines(workspace=workspace).search(
            pipeline_name=pipeline_name, query=query, filters=filters if filters is not None else None
        )

    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}'."
    except BadRequestError as e:
        return f"Failed to search using pipeline '{pipeline_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to search using pipeline '{pipeline_name}': {e}"
    except Exception as e:
        return f"An unexpected error occurred while searching with pipeline '{pipeline_name}': {str(e)}"


async def search_pipeline_with_params(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    query: str,
    params: dict[str, Any] | None = None,
) -> DeepsetSearchResponse | str:
    """Searches using a pipeline with params.

    Uses the specified pipeline to perform a search with the given query and params.
    Params can be arbitrary parameters to customize the search behavior.
    Filters can be used as well under the "filters" key in params.
    Filters follow the Haystack filter syntax: https://docs.haystack.deepset.ai/docs/metadata-filtering.
    Before executing the search, checks if the pipeline is deployed (status = DEPLOYED).
    Returns search results.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline to use for search.
    :param query: The search query to execute.
    :param params: The parameters to customize the search.

    :returns: Search results or error message.
    """
    try:
        # First, check if the pipeline exists and get its status
        pipeline = await client.pipelines(workspace=workspace).get(pipeline_name=pipeline_name)

        # Check if pipeline is deployed
        if pipeline.status != "DEPLOYED":
            return (
                f"Pipeline '{pipeline_name}' is not deployed (current status: {pipeline.status}). "
                f"Please deploy the pipeline first using the deploy_pipeline tool before attempting to search."
            )

        # Execute the search
        return await client.pipelines(workspace=workspace).search(
            pipeline_name=pipeline_name, query=query, params=params if params is not None else None
        )

    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}'."
    except BadRequestError as e:
        return f"Failed to search using pipeline '{pipeline_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to search using pipeline '{pipeline_name}': {e}"
    except Exception as e:
        return f"An unexpected error occurred while searching with pipeline '{pipeline_name}': {str(e)}"
