from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.tools.formatting_utils import validation_result_to_llm_readable_string
from deepset_mcp.tools.formatting_utils_index import index_list_to_llm_readable_string, index_to_llm_readable_string


async def list_indexes(client: AsyncClientProtocol, workspace: str) -> str:
    """Retrieves a list of all indexes available within the currently configured deepset workspace."""
    response = await client.indexes(workspace=workspace).list()
    return index_list_to_llm_readable_string(response)


async def get_index(client: AsyncClientProtocol, workspace: str, index_name: str) -> str:
    """Fetches detailed configuration information for a specific index, identified by its unique `index_name`."""
    try:
        response = await client.indexes(workspace=workspace).get(index_name)
    except ResourceNotFoundError:
        return f"There is no index named '{index_name}'. Did you mean to create it?"

    return index_to_llm_readable_string(response)


async def create_index(
    client: AsyncClientProtocol,
    workspace: str,
    index_name: str,
    yaml_configuration: str,
    description: str | None = None,
) -> str:
    """Creates a new index within the currently configured deepset workspace."""
    try:
        await client.indexes(workspace=workspace).create(
            name=index_name, yaml_config=yaml_configuration, description=description
        )
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except BadRequestError as e:
        return f"Failed to create index '{index_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to create index '{index_name}': {e}"

    return f"Index '{index_name}' created successfully."


async def update_index(
    client: AsyncClientProtocol,
    workspace: str,
    index_name: str,
    updated_index_name: str | None = None,
    yaml_configuration: str | None = None,
) -> str:
    """Updates an existing index in the specified workspace.

    This function can update either the name or the configuration of an existing index, or both.
    At least one of updated_index_name or yaml_configuration must be provided.
    """
    if not updated_index_name and not yaml_configuration:
        return "You must provide either a new name or a new configuration to update the index."

    try:
        await client.indexes(workspace=workspace).update(
            index_name=index_name, updated_index_name=updated_index_name, yaml_config=yaml_configuration
        )
    except ResourceNotFoundError:
        return f"There is no index named '{index_name}'. Did you mean to create it?"
    except BadRequestError as e:
        return f"Failed to update index '{index_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to update index '{index_name}': {e}"

    return f"Index '{index_name}' updated successfully."


async def deploy_index(client: AsyncClientProtocol, workspace: str, index_name: str) -> str:
    """Deploys an index to production.

    This function attempts to deploy the specified index in the given workspace.
    If the deployment fails due to validation errors, it returns a readable string
    describing the validation errors.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param index_name: Name of the index to deploy.

    :returns: A string indicating the deployment result.
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
        return validation_result_to_llm_readable_string(deployment_result)

    return f"Index '{index_name}' deployed successfully."
