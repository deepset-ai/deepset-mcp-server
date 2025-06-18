from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.pipeline.log_level import LogLevel
from deepset_mcp.tools.pipeline import (
    create_pipeline as create_pipeline_tool,
    deploy_pipeline as deploy_pipeline_tool,
    get_pipeline as get_pipeline_tool,
    get_pipeline_logs as get_pipeline_logs_tool,
    list_pipelines as list_pipelines_tool,
    search_pipeline as search_pipeline_tool,
    update_pipeline as update_pipeline_tool,
    validate_pipeline as validate_pipeline_tool,
)


async def list_pipelines(workspace: str) -> str:
    """Retrieves a list of all pipeline available within the currently configured deepset workspace.

    Use this when you need to know the names or IDs of existing pipeline.
    This does not return the pipeline configuration.
    """
    async with AsyncDeepsetClient() as client:
        response = await list_pipelines_tool(client, workspace)

    return response


async def get_pipeline(workspace: str, pipeline_name: str) -> str:
    """Fetches detailed configuration information for a specific pipeline, identified by its unique `pipeline_name`.

    This includes its components, connections, and metadata.
    Use this when you need to inspect the structure or settings of a known pipeline.

    :param workspace: The deepset workspace to operate on.
    :param pipeline_name: Name of the pipeline to retrieve.
    """
    async with AsyncDeepsetClient() as client:
        response = await get_pipeline_tool(client, workspace, pipeline_name)

    return response


async def create_pipeline(workspace: str, pipeline_name: str, yaml_configuration: str) -> str:
    """Creates a new pipeline in deepset.

    :param workspace: The deepset workspace to operate on.
    :param pipeline_name: Name of the pipeline to create
    :param yaml_configuration: YAML configuration for the pipeline
    """
    async with AsyncDeepsetClient() as client:
        response = await create_pipeline_tool(client, workspace, pipeline_name, yaml_configuration)

    return response


async def update_pipeline(
    workspace: str, pipeline_name: str, original_configuration_snippet: str, replacement_configuration_snippet: str
) -> str:
    """Updates an existing pipeline in deepset.

    The update is performed by replacing the original configuration snippet with the new one.
    Make sure that your original snippet only has a single exact match in the pipeline configuration.
    Respect whitespace and formatting.

    :param workspace: The deepset workspace to operate on.
    :param pipeline_name: Name of the pipeline to update
    :param original_configuration_snippet: The configuration snippet to replace
    :param replacement_configuration_snippet: The new configuration snippet
    """
    async with AsyncDeepsetClient() as client:
        response = await update_pipeline_tool(
            client=client,
            workspace=workspace,
            pipeline_name=pipeline_name,
            original_config_snippet=original_configuration_snippet,
            replacement_config_snippet=replacement_configuration_snippet,
        )

    return response


async def validate_pipeline(workspace: str, yaml_configuration: str) -> str:
    """
    Validates the structure and syntax of a provided pipeline YAML configuration against the deepset API specifications.

    Provide the YAML configuration as a string.
    Returns a validation result, indicating success or detailing any errors or warnings found.
    Use this *before* attempting to create or update a pipeline with new YAML.

    :param workspace: The deepset workspace to operate on.
    :param yaml_configuration: YAML configuration to validate.
    """
    async with AsyncDeepsetClient() as client:
        response = await validate_pipeline_tool(client, workspace, yaml_configuration)

    return response


async def get_pipeline_logs(workspace: str, pipeline_name: str, limit: int = 30, level: str | None = None) -> str:
    """Fetches logs for a specific pipeline in the deepset workspace.

    Use this to debug pipeline issues, monitor pipeline execution, or understand what happened during pipeline runs.
    The logs provide detailed information about pipeline operations, errors, and warnings.

    :param workspace: The deepset workspace to operate on.
    :param pipeline_name: Name of the pipeline to fetch logs for.
    :param limit: Maximum number of log entries to return (default: 30, max: 100).
    :param level: Filter logs by level. Valid values: 'info', 'warning', 'error'. If not specified, returns all levels.
    """
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


async def deploy_pipeline(workspace: str, pipeline_name: str) -> str:
    """Deploys a pipeline to production in the deepset workspace.

    Use this to deploy a pipeline that has been created and validated.
    The deployment process will validate the pipeline configuration and deploy it if valid.
    If deployment fails due to validation errors, you will receive detailed error information.

    :param workspace: The deepset workspace to operate on.
    :param pipeline_name: Name of the pipeline to deploy.
    """
    async with AsyncDeepsetClient() as client:
        response = await deploy_pipeline_tool(
            client=client, workspace=workspace, pipeline_name=pipeline_name, wait_for_deployment=True
        )
    return response


async def search_pipeline(workspace: str, pipeline_name: str, query: str) -> str:
    """Search using a deployed pipeline in the deepset workspace.

    This tool allows you to execute a search query using a specific pipeline.
    The pipeline must already be deployed (status = DEPLOYED) for the search to work.
    If the pipeline is not deployed, you will receive an error message instructing you to deploy it first.

    Use this tool when you want to:
    - Test a deployed pipeline with a specific query
    - Get search results from a knowledge base using a specific pipeline
    - Retrieve answers or documents based on a search query

    :param workspace: The deepset workspace to operate on.
    :param pipeline_name: Name of the deployed pipeline to use for search.
    :param query: The search query to execute.
    """
    async with AsyncDeepsetClient() as client:
        response = await search_pipeline_tool(
            client=client, workspace=workspace, pipeline_name=pipeline_name, query=query
        )
    return response
