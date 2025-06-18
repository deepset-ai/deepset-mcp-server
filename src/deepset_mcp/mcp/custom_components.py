from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.tools.custom_components import (
    get_latest_custom_component_installation_logs as get_latest_custom_component_installation_logs_tool,
    list_custom_component_installations as list_custom_component_installations_tool,
)


async def list_custom_component_installations(workspace: str) -> str:
    """Retrieves a list of recent custom component installations.

    Use this to see the installation history of custom components, including status,
    version information, and who installed them. This also includes installation logs.

    :param workspace: The deepset workspace to operate on.
    """
    async with AsyncDeepsetClient() as client:
        response = await list_custom_component_installations_tool(client, workspace)

    return response


async def get_latest_custom_component_installation_logs(workspace: str) -> str:
    """Retrieves the logs from the latest custom component installation.

    Use this to debug custom component installation issues or to understand
    what happened during the most recent installation.

    :param workspace: The deepset workspace to operate on.
    """
    async with AsyncDeepsetClient() as client:
        response = await get_latest_custom_component_installation_logs_tool(client, workspace)

    return response
