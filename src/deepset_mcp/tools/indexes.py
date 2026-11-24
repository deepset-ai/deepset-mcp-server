# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Literal

import yaml
from pydantic import BaseModel

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.indexes.models import Index, MetaFilterConditions
from deepset_mcp.api.pipeline.models import PipelineValidationResult
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.shared_models import PaginatedResponse


class IndexValidationResultWithYaml(BaseModel):
    """Model for index validation result that includes the original YAML."""

    validation_result: PipelineValidationResult
    "Result of validating the index configuration"
    yaml_config: str
    "Original YAML configuration that was validated"


class IndexOperationWithErrors(BaseModel):
    """Model for index operations that complete with validation errors."""

    message: str
    "Descriptive message about the index operation"
    validation_result: PipelineValidationResult
    "Validation errors encountered during the operation"
    index: Index
    "Index object after the operation completed"


async def list_indexes(
    *, client: AsyncClientProtocol, workspace: str, after: str | None = None
) -> PaginatedResponse[Index] | str:
    """Retrieves a list of all indexes available within the currently configured deepset workspace.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param after: The cursor to fetch the next page of results.
        If there are more results to fetch, the cursor will appear as `next_cursor` on the response.
    :returns: List of indexes or error message.
    """
    try:
        return await client.indexes(workspace=workspace).list(after=after)
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list indexes: {e}"


async def get_index(*, client: AsyncClientProtocol, workspace: str, index_name: str) -> Index | str:
    """Fetches detailed configuration information for a specific index, identified by its unique `index_name`.

    :param client: Deepset API client to use for requesting the index.
    :param workspace: Workspace of which to get the index from.
    :param index_name: Unique name of the index to fetch.
    :returns: The index configuration or an error message.
    """
    try:
        response = await client.indexes(workspace=workspace).get(index_name)
    except ResourceNotFoundError:
        return f"There is no index named '{index_name}'. Did you mean to create it?"

    return response


async def validate_index(
    *, client: AsyncClientProtocol, workspace: str, yaml_configuration: str
) -> IndexValidationResultWithYaml | str:
    """Validates the provided index YAML configuration against the deepset API.

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
        response = await client.indexes(workspace=workspace).validate(yaml_configuration)
        return IndexValidationResultWithYaml(validation_result=response, yaml_config=yaml_configuration)
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to validate index: {e}"


async def create_index(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    index_name: str,
    yaml_configuration: str,
    description: str | None = None,
) -> dict[str, str | Index] | str:
    """Creates a new index within your Haystack Enterprise Platform workspace.

    :param client: Deepset API client to use.
    :param workspace: Workspace in which to create the index.
    :param index_name: Unique name of the index to create.
    :param yaml_configuration: YAML configuration to use for the index.
    :param description: Description of the index to create.
    :returns: A message and the created index, or an error message.
    """
    try:
        result = await client.indexes(workspace=workspace).create(
            index_name=index_name, yaml_config=yaml_configuration, description=description
        )
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except BadRequestError as e:
        return f"Failed to create index '{index_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to create index '{index_name}': {e}"

    return {"message": f"Index '{index_name}' created successfully.", "index": result}


async def update_index(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    index_name: str,
    updated_index_name: str | None = None,
    yaml_configuration: str | None = None,
    description: str | None = None,
    max_allowed_batch_size: int | None = None,
    max_index_replica_count: int | None = None,
    gpu_enabled: bool | None = None,
    capture_traces: bool | None = None,
    instance_size: Literal["small", "medium", "large", "xl"] | None = None,
    file_name_prefix_filter: str | None = None,
    file_meta_filter: MetaFilterConditions | None = None,
    skip_validation_errors: bool = True,
) -> Index | IndexOperationWithErrors | str:
    """Updates an index in the specified workspace.

    Only the fields you pass are changed; a field left as None is not touched
    (it is not cleared server-side).

    Pass `yaml_configuration` to replace the index's YAML. When provided, pass the complete,
    updated configuration (not just the changed parts); it is validated before being applied.
    If validation fails and skip_validation_errors is False, it returns error messages.

    All other parameters are index settings that can be updated independently of the YAML:

    - `updated_index_name`: rename the index.
    - `description`: new description.
    - `max_allowed_batch_size`: cap the number of files indexed per batch (1-500). Lower values
      reduce the chance that heavy files exceed the queue timeout and get retried.
    - `max_index_replica_count`: maximum number of index replicas (1-10).
    - `gpu_enabled`: enable or disable GPU acceleration.
    - `capture_traces`: record an indexing trace for every file queued for this index.
    - `instance_size`: pod size used to index files ("small", "medium", "large", or "xl").
    - `file_name_prefix_filter`: prefix pattern (e.g. "myprefix*") selecting which files are
      indexed. Can only be updated while the index is not deployed.
    - `file_meta_filter`: metadata conditions (field/operator/value, AND-combined) selecting
      which files are indexed. Can only be updated while the index is not deployed.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param index_name: Name of the index to update.
    :param updated_index_name: Optional new name for the index.
    :param yaml_configuration: Optional complete, updated YAML configuration for the index.
    :param description: Optional new description.
    :param max_allowed_batch_size: Optional per-pipeline cap on files indexed per batch (1-500).
    :param max_index_replica_count: Optional max number of index replicas (1-10).
    :param gpu_enabled: Optional toggle for GPU acceleration.
    :param capture_traces: Optional toggle for recording an indexing trace per queued file.
    :param instance_size: Optional pod size: "small", "medium", "large", or "xl".
    :param file_name_prefix_filter: Optional file-name prefix pattern filter.
    :param file_meta_filter: Optional metadata conditions filtering which files are indexed.
    :param skip_validation_errors: If True (default), updates the index even if validation fails.
                                  If False, stops update when validation fails.
    :returns: Updated index or error message.
    """
    settings_provided = any(
        v is not None
        for v in (
            updated_index_name,
            description,
            max_allowed_batch_size,
            max_index_replica_count,
            gpu_enabled,
            capture_traces,
            instance_size,
            file_name_prefix_filter,
            file_meta_filter,
        )
    )
    if yaml_configuration is None and not settings_provided:
        return "You need to provide a YAML configuration or at least one setting to update the index."

    validation_response: PipelineValidationResult | None = None

    if yaml_configuration is not None:
        if not yaml_configuration.strip():
            return "You need to provide a YAML configuration to update the index."

        try:
            yaml.safe_load(yaml_configuration)
        except yaml.YAMLError as e:
            return f"Invalid YAML provided: {e}"

    try:
        if yaml_configuration is not None:
            validation_response = await client.indexes(workspace=workspace).validate(yaml_configuration)

            if not validation_response.valid and not skip_validation_errors:
                error_messages = [f"{error.code}: {error.message}" for error in validation_response.errors]
                return "Index validation failed:\n" + "\n".join(error_messages)

        await client.indexes(workspace=workspace).update(
            index_name=index_name,
            yaml_config=yaml_configuration,
            updated_index_name=updated_index_name,
            description=description,
            max_allowed_batch_size=max_allowed_batch_size,
            max_index_replica_count=max_index_replica_count,
            gpu_enabled=gpu_enabled,
            capture_traces=capture_traces,
            instance_size=instance_size,
            file_name_prefix_filter=file_name_prefix_filter,
            file_meta_filter=file_meta_filter,
        )

        # Get the full index after update
        index = await client.indexes(workspace=workspace).get(index_name)

        # If validation failed but we proceeded anyway, return the special model
        if validation_response is not None and not validation_response.valid:
            return IndexOperationWithErrors(
                message="The operation completed with errors", validation_result=validation_response, index=index
            )

        # Otherwise return just the index
        return index

    except ResourceNotFoundError:
        return f"There is no index named '{index_name}'. Did you mean to create it?"
    except BadRequestError as e:
        return f"Failed to update the index '{index_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to update the index '{index_name}': {e}"


async def deploy_index(
    *, client: AsyncClientProtocol, workspace: str, index_name: str
) -> str | PipelineValidationResult:
    """Deploys an index to production.

    This function attempts to deploy the specified index in the given workspace.
    If the deployment fails due to validation errors, it returns an object
    describing the validation errors.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param index_name: Name of the index to deploy.

    :returns: A string indicating the deployment result or the validation results including errors.
    """
    try:
        deployment_result = await client.indexes(workspace=workspace).deploy(index_name=index_name)
    except ResourceNotFoundError:
        return f"There is no index named '{index_name}' in workspace '{workspace}'."
    except BadRequestError as e:
        return f"Failed to deploy index '{index_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to deploy index '{index_name}': {e}"

    if not deployment_result.valid:
        return deployment_result

    return f"Index '{index_name}' deployed successfully."
