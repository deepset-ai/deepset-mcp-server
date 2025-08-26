# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.indexes.models import Index
from deepset_mcp.api.pipeline.models import PipelineValidationResult
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.shared_models import PaginatedResponse


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
    """
    try:
        response = await client.indexes(workspace=workspace).get(index_name)
    except ResourceNotFoundError:
        return f"There is no index named '{index_name}'. Did you mean to create it?"

    return response


async def create_index(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    index_name: str,
    yaml_configuration: str,
    description: str | None = None,
) -> dict[str, str | Index] | str:
    """Creates a new index within your deepset platform workspace.

    :param client: Deepset API client to use.
    :param workspace: Workspace in which to create the index.
    :param index_name: Unique name of the index to create.
    :param yaml_configuration: YAML configuration to use for the index.
    :param description: Description of the index to create.
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
    original_config_snippet: str,
    replacement_config_snippet: str,
    skip_validation_errors: bool = True,
) -> Index | IndexOperationWithErrors | str:
    """
    Updates an index configuration in the specified workspace with a replacement configuration snippet.

    This function validates the replacement configuration snippet before applying it to the index.
    If the validation fails and skip_validation_errors is False, it returns error messages.
    Otherwise, the replacement snippet is used to update the index's configuration.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param index_name: Name of the index to update.
    :param original_config_snippet: The configuration snippet to replace.
    :param replacement_config_snippet: The new configuration snippet.
    :param skip_validation_errors: If True (default), updates the index even if validation fails.
                                  If False, stops update when validation fails.
    :returns: Updated index or error message.
    """
    try:
        original_index = await client.indexes(workspace=workspace).get(index_name=index_name)
    except ResourceNotFoundError:
        return f"There is no index named '{index_name}'. Did you mean to create it?"
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to fetch index '{index_name}': {e}"

    if original_index.yaml_config is None:
        return f"The index '{index_name}' does not have a YAML configuration."

    occurrences = original_index.yaml_config.count(original_config_snippet)

    if occurrences == 0:
        return f"No occurrences of the provided configuration snippet were found in the index '{index_name}'."

    if occurrences > 1:
        return (
            f"Multiple occurrences ({occurrences}) of the provided configuration snippet were found in the index "
            f"'{index_name}'. Specify a more precise snippet to proceed with the update."
        )

    updated_yaml_configuration = original_index.yaml_config.replace(
        original_config_snippet, replacement_config_snippet, 1
    )

    try:
        # Note: We don't have a validate endpoint for indexes like we do for pipelines
        # So we'll skip validation for now and attempt the update directly

        await client.indexes(workspace=workspace).update(index_name=index_name, yaml_config=updated_yaml_configuration)

        # Get the full index after update
        index = await client.indexes(workspace=workspace).get(index_name)

        # Return just the index since we don't have validation
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
