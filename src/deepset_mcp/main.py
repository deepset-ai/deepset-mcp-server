import argparse
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from model2vec import StaticModel

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.pipeline.log_level import LogLevel
from deepset_mcp.tools.custom_components import (
    get_latest_custom_component_installation_logs as get_latest_custom_component_installation_logs_tool,
    list_custom_component_installations as list_custom_component_installations_tool,
)
from deepset_mcp.tools.haystack_service import (
    get_component_definition as get_component_definition_tool,
    get_custom_components as get_custom_components_tool,
    list_component_families as list_component_families_tool,
    search_component_definition as search_component_definition_tool,
)
from deepset_mcp.tools.indexes import (
    create_index as create_index_tool,
    get_index as get_index_tool,
    list_indexes as list_indexes_tool,
    update_index as update_index_tool,
)
from deepset_mcp.tools.pipeline import (
    create_pipeline as create_pipeline_tool,
    deploy_pipeline as deploy_pipeline_tool,
    get_pipeline as get_pipeline_tool,
    get_pipeline_logs as get_pipeline_logs_tool,
    list_pipelines as list_pipelines_tool,
    update_pipeline as update_pipeline_tool,
    validate_pipeline as validate_pipeline_tool,
)
from deepset_mcp.tools.pipeline_template import (
    get_pipeline_template as get_pipeline_template_tool,
    list_pipeline_templates as list_pipeline_templates_tool,
    search_pipeline_templates as search_pipeline_templates_tool,
)

INITIALIZED_MODEL = StaticModel.from_pretrained("minishlab/potion-base-2M")

# Initialize MCP Server
mcp = FastMCP("Deepset Cloud MCP")


def get_workspace() -> str:
    """Gets the workspace configured for the environment."""
    workspace = os.environ.get("DEEPSET_WORKSPACE")
    if not workspace:
        raise ValueError("DEEPSET_WORKSPACE environment variable not set")
    return workspace


@mcp.prompt()
async def deepset_copilot() -> str:
    """System prompt for the deepset copilot."""
    prompt_path = Path(__file__).parent / "prompts/deepset_copilot_prompt.md"

    return prompt_path.read_text()


@mcp.tool()
async def list_pipelines() -> str:
    """Retrieves a list of all pipeline available within the currently configured deepset workspace.

    Use this when you need to know the names or IDs of existing pipeline.
    This does not return the pipeline configuration.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await list_pipelines_tool(client, workspace)

    return response


@mcp.tool()
async def list_pipeline_templates() -> str:
    """Retrieves a list of all pipeline templates available within the currently configured deepset workspace.

    Use this when you need to know the available pipeline templates and their capabilities.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await list_pipeline_templates_tool(client, workspace)

    return response


@mcp.tool()
async def get_pipeline_template(template_name: str) -> str:
    """Fetches detailed configuration information for a specific pipeline template.

    This includes its YAML configuration, metadata, and recommended use cases.
    Use this when you need to inspect a specific template's structure or settings.

    :param template_name: Name of the pipeline template to retrieve.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await get_pipeline_template_tool(client, workspace, template_name)

    return response


@mcp.tool()
async def get_pipeline(pipeline_name: str) -> str:
    """Fetches detailed configuration information for a specific pipeline, identified by its unique `pipeline_name`.

    This includes its components, connections, and metadata.
    Use this when you need to inspect the structure or settings of a known pipeline.

    :param pipeline_name: Name of the pipeline to retrieve.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await get_pipeline_tool(client, workspace, pipeline_name)

    return response


@mcp.tool()
async def create_pipeline(pipeline_name: str, yaml_configuration: str, skip_validation_errors: bool = True) -> str:
    """Creates a new pipeline in deepset.
    
    Args:
        pipeline_name: Name of the pipeline to create
        yaml_configuration: YAML configuration for the pipeline
        skip_validation_errors: If True (default), creates the pipeline even if validation fails.
                               If False, stops creation when validation fails.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await create_pipeline_tool(client, workspace, pipeline_name, yaml_configuration, skip_validation_errors)

    return response


@mcp.tool()
async def update_pipeline(
    pipeline_name: str, 
    original_configuration_snippet: str, 
    replacement_configuration_snippet: str,
    skip_validation_errors: bool = True
) -> str:
    """Updates an existing pipeline in deepset.

    The update is performed by replacing the original configuration snippet with the new one.
    Make sure that your original snippet only has a single exact match in the pipeline configuration.
    Respect whitespace and formatting.
    
    Args:
        pipeline_name: Name of the pipeline to update
        original_configuration_snippet: The configuration snippet to replace
        replacement_configuration_snippet: The new configuration snippet
        skip_validation_errors: If True (default), updates the pipeline even if validation fails.
                               If False, stops update when validation fails.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await update_pipeline_tool(
            client=client,
            workspace=workspace,
            pipeline_name=pipeline_name,
            original_config_snippet=original_configuration_snippet,
            replacement_config_snippet=replacement_configuration_snippet,
            skip_validation_errors=skip_validation_errors,
        )

    return response


@mcp.tool()
async def list_component_families() -> str:
    """
    Returns a list of all component families available in deepset alongside their descriptions.

    Use this as a starting point for when you are unsure what types of components are available.
    """
    async with AsyncDeepsetClient() as client:
        response = await list_component_families_tool(client)

    return response


@mcp.tool()
async def get_component_definition(component_type: str) -> str:
    """Use this to get the full definition of a specific component.

    The component type is the fully qualified import path of the component class.
    For example: haystack.components.converters.xlsx.XLSXToDocument
    The component definition contains a description, parameters, and example usage of the component.
    """
    async with AsyncDeepsetClient() as client:
        response = await get_component_definition_tool(client, component_type)

    return response


@mcp.tool()
async def validate_pipeline(yaml_configuration: str) -> str:
    """
    Validates the structure and syntax of a provided pipeline YAML configuration against the deepset API specifications.

    Provide the YAML configuration as a string.
    Returns a validation result, indicating success or detailing any errors or warnings found.
    Use this *before* attempting to create or update a pipeline with new YAML.
    """
    workspace = get_workspace()

    async with AsyncDeepsetClient() as client:
        response = await validate_pipeline_tool(client, workspace, yaml_configuration)

    return response


@mcp.tool()
async def search_component_definitions(query: str) -> str:
    """Use this to search for components in deepset.

    You can use full natural language queries to find components.
    You can also use simple keywords.
    Use this if you want to find the definition for a component,
    but you are not sure what the exact name of the component is.
    """
    async with AsyncDeepsetClient() as client:
        response = await search_component_definition_tool(client=client, query=query, model=INITIALIZED_MODEL)

    return response


@mcp.tool()
async def search_pipeline_templates(query: str) -> str:
    """Use this to search for pipeline templates in deepset.

    You can use full natural language queries to find templates.
    You can also use simple keywords.
    Use this if you want to find pipeline templates for specific use cases,
    but you are not sure what the exact name of the template is.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await search_pipeline_templates_tool(
            client=client, query=query, model=INITIALIZED_MODEL, workspace=workspace
        )

    return response


@mcp.tool()
async def list_indexes() -> str:
    """Retrieves a list of all indexes available in the deepset workspace.

    Use this to get an overview of existing indexes and their configurations.
    The response includes basic information for each index.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await list_indexes_tool(client=client, workspace=workspace)
    return response


@mcp.tool()
async def get_index(index_name: str) -> str:
    """Fetches detailed configuration information for a specific index.

    Use this to get the full configuration and details of a single index.

    :param index_name: The name of the index to fetch.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await get_index_tool(client=client, workspace=workspace, index_name=index_name)
    return response


@mcp.tool()
async def create_index(index_name: str, yaml_configuration: str, description: str | None = None) -> str:
    """Creates a new index in the deepset workspace.

    Use this to create a new index with the given configuration.
    Make sure the YAML configuration is valid before creating the index.

    :param index_name: The name for the new index.
    :param yaml_configuration: YAML configuration for the index.
    :param description: Optional description for the index.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await create_index_tool(
            client=client,
            workspace=workspace,
            index_name=index_name,
            yaml_configuration=yaml_configuration,
            description=description,
        )
    return response


@mcp.tool()
async def update_index(
    index_name: str, updated_index_name: str | None = None, yaml_configuration: str | None = None
) -> str:
    """Updates an existing index in the deepset workspace.

    Use this to update the name or configuration of an existing index.
    You must provide at least one of updated_index_name or yaml_configuration.

    :param index_name: The name of the index to update.
    :param updated_index_name: Optional new name for the index.
    :param yaml_configuration: Optional new YAML configuration.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await update_index_tool(
            client=client,
            workspace=workspace,
            index_name=index_name,
            updated_index_name=updated_index_name,
            yaml_configuration=yaml_configuration,
        )
    return response


@mcp.tool()
async def get_pipeline_logs(pipeline_name: str, limit: int = 30, level: str | None = None) -> str:
    """Fetches logs for a specific pipeline in the deepset workspace.

    Use this to debug pipeline issues, monitor pipeline execution, or understand what happened during pipeline runs.
    The logs provide detailed information about pipeline operations, errors, and warnings.

    :param pipeline_name: Name of the pipeline to fetch logs for.
    :param limit: Maximum number of log entries to return (default: 30, max: 100).
    :param level: Filter logs by level. Valid values: 'info', 'warning', 'error'. If not specified, returns all levels.
    """
    workspace = get_workspace()

    # Convert string level to LogLevel enum if provided
    log_level: LogLevel | None = None
    if level is not None:
        try:
            log_level = LogLevel(level)
        except ValueError:
            return f"Invalid log level '{level}'. Valid values are: 'info', 'warning', 'error'."

    async with AsyncDeepsetClient() as client:
        response = await get_pipeline_logs_tool(
            client=client,
            workspace=workspace,
            pipeline_name=pipeline_name,
            limit=limit,
            level=log_level,
        )
    return response


@mcp.tool()
async def deploy_pipeline(pipeline_name: str) -> str:
    """Deploys a pipeline to production in the deepset workspace.

    Use this to deploy a pipeline that has been created and validated.
    The deployment process will validate the pipeline configuration and deploy it if valid.
    If deployment fails due to validation errors, you will receive detailed error information.

    :param pipeline_name: Name of the pipeline to deploy.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await deploy_pipeline_tool(
            client=client,
            workspace=workspace,
            pipeline_name=pipeline_name,
        )
    return response


@mcp.tool()
async def get_custom_components() -> str:
    """Retrieves a list of all installed custom components.

    Use this when you need to know what custom components are available in the workspace.
    Custom components are identified by having a package_version in their schema.
    This returns detailed information about each custom component including version, type, and parameters.
    """
    async with AsyncDeepsetClient() as client:
        response = await get_custom_components_tool(client)

    return response


@mcp.tool()
async def list_custom_component_installations() -> str:
    """Retrieves a list of recent custom component installations.

    Use this to see the installation history of custom components, including status,
    version information, and who installed them. This also includes installation logs.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await list_custom_component_installations_tool(client, workspace)

    return response


@mcp.tool()
async def get_latest_custom_component_installation_logs() -> str:
    """Retrieves the logs from the latest custom component installation.

    Use this to debug custom component installation issues or to understand
    what happened during the most recent installation.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await get_latest_custom_component_installation_logs_tool(client, workspace)

    return response


def main() -> None:
    """Entrypoint for the deepset MCP server."""
    parser = argparse.ArgumentParser(description="Run the Deepset MCP server.")
    parser.add_argument(
        "--workspace",
        "-w",
        help="Deepset workspace (env DEEPSET_WORKSPACE)",
    )
    parser.add_argument(
        "--api-key",
        "-k",
        help="Deepset API key (env DEEPSET_API_KEY)",
    )
    args = parser.parse_args()

    # prefer flags, fallback to env
    workspace = args.workspace or os.getenv("DEEPSET_WORKSPACE")
    api_key = args.api_key or os.getenv("DEEPSET_API_KEY")
    if not workspace:
        parser.error("Missing workspace: set --workspace or DEEPSET_WORKSPACE")
    if not api_key:
        parser.error("Missing API key: set --api-key or DEEPSET_API_KEY")

    # make sure downstream tools see them
    os.environ["DEEPSET_WORKSPACE"] = workspace
    os.environ["DEEPSET_API_KEY"] = api_key

    # run with SSE transport (HTTP+Server-Sent Events)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
