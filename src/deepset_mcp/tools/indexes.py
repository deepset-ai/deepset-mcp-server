# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.indexes.models import Index, IndexList
from deepset_mcp.api.pipeline import PipelineValidationResult
from deepset_mcp.api.protocols import AsyncClientProtocol


async def list_indexes(*, client: AsyncClientProtocol, workspace: str) -> IndexList | str:
    """Use this to list available indexes on the deepset platform in your workspace.

    :param client: Deepset API client to use for requesting indexes.
    :param workspace: Workspace of which to list indexes.
    """
    try:
        result = await client.indexes(workspace=workspace).list()
    except ResourceNotFoundError as e:
        return f"Error listing indexes. Error: {e.message} ({e.status_code})"

    return result


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
            name=index_name, yaml_config=yaml_configuration, description=description
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
) -> dict[str, str | Index] | str:
    """Updates an existing index in your deepset platform workspace.

    This function can update either the name or the configuration of an existing index, or both.
    At least one of updated_index_name or yaml_configuration must be provided.

    :param client: Deepset API client to use.
    :param workspace: Workspace in which to update the index.
    :param index_name: Unique name of the index to update.
    :param updated_index_name: Updated name of the index.
    :param yaml_configuration: YAML configuration to update the index with.
    """
    if not updated_index_name and not yaml_configuration:
        return "You must provide either a new name or a new configuration to update the index."

    try:
        result = await client.indexes(workspace=workspace).update(
            index_name=index_name, updated_index_name=updated_index_name, yaml_config=yaml_configuration
        )
    except ResourceNotFoundError:
        return f"There is no index named '{index_name}'. Did you mean to create it?"
    except BadRequestError as e:
        return f"Failed to update index '{index_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to update index '{index_name}': {e}"

    return {"message": f"Index '{index_name}' updated successfully.", "index": result}


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
