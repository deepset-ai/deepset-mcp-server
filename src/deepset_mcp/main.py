import os

from mcp.server.fastmcp import FastMCP
from model2vec import StaticModel

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.tools.haystack_service import (
    get_component_definition as get_component_definition_tool,
    list_component_families as list_component_families_tool,
    search_component_definition as search_component_definition_tool,
)
from deepset_mcp.tools.pipeline import (
    create_pipeline as create_pipeline_tool,
    get_pipeline as get_pipeline_tool,
    list_pipelines as list_pipelines_tool,
    update_pipeline as update_pipeline_tool,
    validate_pipeline as validate_pipeline_tool,
)
from deepset_mcp.tools.pipeline_template import (
    get_pipeline_template as get_pipeline_template_tool,
    list_pipeline_templates as list_pipeline_templates_tool,
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
async def create_pipeline(pipeline_name: str, yaml_configuration: str) -> str:
    """Creates a new pipeline in deepset."""
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await create_pipeline_tool(client, workspace, pipeline_name, yaml_configuration)

    return response


@mcp.tool()
async def update_pipeline(
    pipeline_name: str, original_configuration_snippet: str, replacement_configuration_snippet: str
) -> str:
    """Updates an existing pipeline in deepset.

    The update is performed by replacing the original configuration snippet with the new one.
    Make sure that your original snippet only has a single exact match in the pipeline configuration.
    Respect whitespace and formatting.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await update_pipeline_tool(
            client=client,
            workspace=workspace,
            pipeline_name=pipeline_name,
            original_config_snippet=original_configuration_snippet,
            replacement_config_snippet=replacement_configuration_snippet,
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


#
#
# @mcp.tool()
# async def get_custom_components() -> str:
#     """Use this to get a list of all installed custom components."""
#     response = await get_component_schemas()
#
#     # Check for errors in the response
#     if isinstance(response, dict) and "error" in response:
#         return f"Error retrieving component schemas: {response['error']}"
#
#     # Navigate to the components definition section
#     # Typically structured as {definitions: {Components: {<component_name>: <schema>}}}
#     schemas = response.get("component_schema", {})
#     schemas = schemas.get("definitions", {}).get("Components", {})
#
#     if not schemas:
#         return "No component schemas found or unexpected schema format."
#
#     # Filter for custom components (those with package_version key)
#     custom_components = {}
#     for component_name, schema in schemas.items():
#         if "package_version" in schema:
#             custom_components[component_name] = schema
#
#     if not custom_components:
#         return "No custom components found."
#
#     # Format the response
#     formatted_output = [f"# Custom Components ({len(custom_components)} found)\n"]
#
#     for component_name, schema in custom_components.items():
#         # Extract key information
#         package_version = schema.get("package_version", "Unknown")
#         dynamic_params = schema.get("dynamic_params", False)
#
#         # Get component type info
#         type_info = schema.get("properties", {}).get("type", {})
#         const_value = type_info.get("const", "Unknown")
#         family = type_info.get("family", "Unknown")
#         family_description = type_info.get("family_description", "No description")
#
#         # Format component details
#         component_details = [
#             f"## {component_name}",
#             f"- **Type**: `{const_value}`",
#             f"- **Package Version**: {package_version}",
#             f"- **Family**: {family} - {family_description}",
#             f"- **Dynamic Parameters**: {'Yes' if dynamic_params else 'No'}",
#         ]
#
#         # Add init parameters if available
#         init_params = schema.get("properties", {}).get("init_parameters", {}).get("properties", {})
#         if init_params:
#             component_details.append("\n### Init Parameters:")
#             for param_name, param_info in init_params.items():
#                 param_type = param_info.get("type", "Unknown")
#                 required = param_name in schema.get("properties", {}).get("init_parameters", {}).get("required", [])
#                 param_description = param_info.get("description", "No description")
#
#                 component_details.append(f"- **{param_name}** ({param_type}{', required' if required else ''}):")
#                 component_details.append(f"  {param_description}")
#
#         formatted_output.append("\n".join(component_details) + "\n")
#
#     # Join all sections and return
#     return "\n".join(formatted_output)
#
#
# @mcp.tool()
# async def get_latest_custom_component_installation_logs() -> Any:
#     """
#     Use this to get the logs from the latest custom component installation.
#
#     This will give you the full installation log output.
#     It is useful for debugging custom component installations.
#     """
#     async with AsyncDeepsetClient() as client:
#         return await client.request(endpoint="v2/custom_components/logs")
#
#
# @mcp.tool()
# async def list_custom_component_installations() -> str:
#     """
#     Retrieves a list of the most recent custom component installations.
#
#     This will return version number, high-level log, status and information about who uploaded the package.
#     """
#     endpoint = "v2/custom_components?limit=20&page_number=1&field=created_at&order=DESC"
#     async with AsyncDeepsetClient() as client:
#         resp = await client.request(endpoint=endpoint)
#
#         response = cast(dict[str, Any], resp.json)
#
#     installations = response.get("data", [])
#     total = response.get("total", 0)
#     has_more = response.get("has_more", False)
#
#     if not installations:
#         return "No custom component installations found."
#
#     # Format the response
#     formatted_output = [f"# Custom Component Installations (showing {len(installations)} of {total})\n"]
#
#     for install in installations:
#         # Extract key information
#         component_id = install.get("custom_component_id", "Unknown")
#         status = install.get("status", "Unknown")
#         version = install.get("version", "Unknown")
#         user_id = install.get("created_by_user_id", "Unknown")
#
#         # Try to fetch user information
#         user_info = "Unknown"
#         if user_id != "Unknown":
#             user_url = f"v1/users/{user_id}"
#             async with AsyncDeepsetClient() as client:
#                 user_response = await client.request(endpoint=user_url)
#
#             user_data = user_response.json
#             assert user_data is not None
#             given_name = user_data.get("given_name", "")
#             family_name = user_data.get("family_name", "")
#             email = user_data.get("email", "")
#             user_info = f"{given_name} {family_name} ({email})"
#
#         # Format installation details
#         install_details = [
#             f"## Installation {component_id[:8]}...",
#             f"- **Status**: {status}",
#             f"- **Version**: {version}",
#             f"- **Installed by**: {user_info}",
#         ]
#
#         # Add logs if available
#         logs = install.get("logs", [])
#         if logs:
#             install_details.append("\n### Recent Logs:")
#             for log in logs[:5]:  # Show only the first 5 logs
#                 level = log.get("level", "INFO")
#                 msg = log.get("msg", "No message")
#                 install_details.append(f"- [{level}] {msg}")
#
#             if len(logs) > 5:
#                 install_details.append(f"- ... and {len(logs) - 5} more log entries")
#
#         formatted_output.append("\n".join(install_details) + "\n")
#
#         if has_more:
#             formatted_output.append(
#                 "*Note: There are more installations available. This listing shows only the 10 most recent.*"
#             )
#
#     # Join all sections and return
#     return "\n".join(formatted_output)


def launch_mcp() -> None:
    """Launches the MCP server."""
    mcp.run()


if __name__ == "__main__":
    launch_mcp()
