from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.mcp.initialize_embedding_model import get_initialized_model
from deepset_mcp.tools.pipeline_template import (
    get_pipeline_template as get_pipeline_template_tool,
    list_pipeline_templates as list_pipeline_templates_tool,
    search_pipeline_templates as search_pipeline_templates_tool,
)


async def list_pipeline_templates(workspace: str) -> str:
    """Retrieves a list of all pipeline templates available within the currently configured deepset workspace.

    Use this when you need to know the available pipeline templates and their capabilities.

    :param workspace: The name of the workspace where the pipeline templates are located.
    """
    async with AsyncDeepsetClient() as client:
        response = await list_pipeline_templates_tool(client, workspace)

    return response


async def get_pipeline_template(workspace: str, template_name: str) -> str:
    """Fetches detailed configuration information for a specific pipeline template.

    This includes its YAML configuration, metadata, and recommended use cases.
    Use this when you need to inspect a specific template's structure or settings.

    :param workspace: The deepset workspace to operate on.
    :param template_name: Name of the pipeline template to retrieve.
    """
    async with AsyncDeepsetClient() as client:
        response = await get_pipeline_template_tool(client, workspace, template_name)

    return response


async def search_pipeline_templates(workspace: str, query: str) -> str:
    """Use this to search for pipeline templates in deepset.

    You can use full natural language queries to find templates.
    You can also use simple keywords.
    Use this if you want to find pipeline templates for specific use cases,
    but you are not sure what the exact name of the template is.

    :param workspace: The deepset workspace to operate on.
    :param query: Search query for templates.
    """
    async with AsyncDeepsetClient() as client:
        response = await search_pipeline_templates_tool(
            client=client, query=query, model=get_initialized_model(), workspace=workspace
        )

    return response
