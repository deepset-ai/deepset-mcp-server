# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import asyncio

import yaml

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.pipeline.log_level import LogLevel
from deepset_mcp.api.pipeline.models import (
    DeepsetPipeline,
    DeepsetSearchResponse,
    PipelineList,
    PipelineLogList,
    PipelineOperationWithErrors,
    PipelineValidationResult,
    PipelineValidationResultWithYaml,
)
from deepset_mcp.api.protocols import AsyncClientProtocol


async def list_pipelines(*, client: AsyncClientProtocol, workspace: str) -> PipelineList | str:
    """Retrieves a list of all pipeline available within the currently configured deepset workspace.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :returns: List of pipelines or error message.
    """
    try:
        return await client.pipelines(workspace=workspace).list()
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


async def update_pipeline(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    original_config_snippet: str,
    replacement_config_snippet: str,
    skip_validation_errors: bool = True,
) -> DeepsetPipeline | PipelineOperationWithErrors | str:
    """
    Updates a pipeline configuration in the specified workspace with a replacement configuration snippet.

    This function validates the replacement configuration snippet before applying it to the pipeline.
    If the validation fails and skip_validation_errors is False, it returns error messages.
    Otherwise, the replacement snippet is used to update the pipeline's configuration.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline to update.
    :param original_config_snippet: The configuration snippet to replace.
    :param replacement_config_snippet: The new configuration snippet.
    :param skip_validation_errors: If True (default), updates the pipeline even if validation fails.
                                  If False, stops update when validation fails.
    :returns: Updated pipeline or error message.
    """
    try:
        original_pipeline = await client.pipelines(workspace=workspace).get(pipeline_name=pipeline_name)
    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}'. Did you mean to create it?"
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to fetch pipeline '{pipeline_name}': {e}"

    if original_pipeline.yaml_config is None:
        return f"The pipeline '{pipeline_name}' does not have a YAML configuration."

    occurrences = original_pipeline.yaml_config.count(original_config_snippet)

    if occurrences == 0:
        return f"No occurrences of the provided configuration snippet were found in the pipeline '{pipeline_name}'."

    if occurrences > 1:
        return (
            f"Multiple occurrences ({occurrences}) of the provided configuration snippet were found in the pipeline "
            f"'{pipeline_name}'. Specify a more precise snippet to proceed with the update."
        )

    updated_yaml_configuration = original_pipeline.yaml_config.replace(
        original_config_snippet, replacement_config_snippet, 1
    )

    try:
        validation_response = await client.pipelines(workspace=workspace).validate(updated_yaml_configuration)

        if not validation_response.valid and not skip_validation_errors:
            error_messages = [f"{error.code}: {error.message}" for error in validation_response.errors]
            return "Pipeline validation failed:\n" + "\n".join(error_messages)

        await client.pipelines(workspace=workspace).update(
            pipeline_name=pipeline_name, yaml_config=updated_yaml_configuration
        )

        # Get the full pipeline after update
        pipeline = await client.pipelines(workspace=workspace).get(pipeline_name)

        # If validation failed but we proceeded anyway, return the special model
        if not validation_response.valid:
            return PipelineOperationWithErrors(
                message="The operation completed with errors", validation_result=validation_response, pipeline=pipeline
            )

        # Otherwise return just the pipeline
        return pipeline

    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}'. Did you mean to create it?"
    except BadRequestError as e:
        return f"Failed to update the pipeline '{pipeline_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to update the pipeline '{pipeline_name}': {e}"


async def get_pipeline_logs(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str, limit: int = 30, level: LogLevel | None = None
) -> PipelineLogList | str:
    """Fetches logs for a specific pipeline.

    Retrieves log entries for the specified pipeline, with optional filtering by log level.
    This is useful for debugging pipeline issues or monitoring pipeline execution.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline to fetch logs for.
    :param limit: Maximum number of log entries to return (default: 30).
    :param level: Filter logs by level. If None, returns all levels.

    :returns: Pipeline logs or error message.
    """
    try:
        return await client.pipelines(workspace=workspace).get_logs(
            pipeline_name=pipeline_name, limit=limit, level=level
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
