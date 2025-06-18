from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.tools.indexes import (
    create_index as create_index_tool,
    deploy_index as deploy_index_tool,
    get_index as get_index_tool,
    list_indexes as list_indexes_tool,
    update_index as update_index_tool,
)


async def list_indexes(workspace: str) -> str:
    """Retrieves a list of all indexes available in the deepset workspace.

    Use this to get an overview of existing indexes and their configurations.
    The response includes basic information for each index.

    :param workspace: The deepset workspace to operate on.
    """
    async with AsyncDeepsetClient() as client:
        response = await list_indexes_tool(client=client, workspace=workspace)
    return response


async def get_index(workspace: str, index_name: str) -> str:
    """Fetches detailed configuration information for a specific index.

    Use this to get the full configuration and details of a single index.

    :param workspace: The deepset workspace to operate on.
    :param index_name: The name of the index to fetch.
    """
    async with AsyncDeepsetClient() as client:
        response = await get_index_tool(client=client, workspace=workspace, index_name=index_name)
    return response


async def create_index(workspace: str, index_name: str, yaml_configuration: str, description: str | None = None) -> str:
    """Creates a new index in the deepset workspace.

    Use this to create a new index with the given configuration.
    Make sure the YAML configuration is valid before creating the index.

    :param workspace: The deepset workspace to operate on.
    :param index_name: The name for the new index.
    :param yaml_configuration: YAML configuration for the index.
    :param description: Optional description for the index.
    """
    async with AsyncDeepsetClient() as client:
        response = await create_index_tool(
            client=client,
            workspace=workspace,
            index_name=index_name,
            yaml_configuration=yaml_configuration,
            description=description,
        )
    return response


async def update_index(
    workspace: str, index_name: str, updated_index_name: str | None = None, yaml_configuration: str | None = None
) -> str:
    """Updates an existing index in the deepset workspace.

    Use this to update the name or configuration of an existing index.
    You must provide at least one of updated_index_name or yaml_configuration.

    :param workspace: The deepset workspace to operate on.
    :param index_name: The name of the index to update.
    :param updated_index_name: Optional new name for the index.
    :param yaml_configuration: Optional new YAML configuration.
    """
    async with AsyncDeepsetClient() as client:
        response = await update_index_tool(
            client=client,
            workspace=workspace,
            index_name=index_name,
            updated_index_name=updated_index_name,
            yaml_configuration=yaml_configuration,
        )
    return response


async def deploy_index(workspace: str, index_name: str) -> str:
    """Deploys an index to production in the deepset workspace.

    Use this to deploy an index that has been created and configured.
    The deployment process will validate the index configuration and deploy it if valid.
    If deployment fails due to validation errors, you will receive detailed error information.

    :param workspace: The deepset workspace to operate on.
    :param index_name: Name of the index to deploy.
    """
    async with AsyncDeepsetClient() as client:
        response = await deploy_index_tool(client=client, workspace=workspace, index_name=index_name)
    return response
