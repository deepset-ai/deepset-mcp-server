import os
from typing import Any, cast

from mcp.server.fastmcp import FastMCP

from deepset_mcp.api.client import AsyncDeepsetClient

# Initialize MCP Server
mcp = FastMCP("Deepset Cloud MCP")


def get_workspace() -> str:
    """Gets the workspace configured for the environment."""
    workspace = os.environ.get("DEEPSET_WORKSPACE")
    if not workspace:
        raise ValueError("DEEPSET_WORKSPACE environment variable not set")
    return workspace


@mcp.tool()
async def list_pipelines() -> Any:
    """Retrieves a list of all pipeline available within the currently configured deepset workspace.

    Use this when you need to know the names or IDs of existing pipeline.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await client.request(endpoint=f"v1/workspaces/{workspace}/pipeline", method="GET")
        return response.json


@mcp.tool()
async def get_pipeline(pipeline_id: str) -> Any:
    """Fetches detailed configuration information for a specific pipeline, identified by its unique `pipeline_id`.

    This includes its components, connections, and metadata.
    Use this when you need to inspect the structure or settings of a known pipeline.

    :param pipeline_id: ID of the pipeline to retrieve.
    """
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        response = await client.request(endpoint=f"v1/workspaces/{workspace}/pipeline/{pipeline_id}", method="GET")
        return response.json


@mcp.tool()
async def get_component_schemas() -> Any:
    """Retrieves the schemas for all available Haystack components from the deepset API.

    These schemas define the expected input and output parameters for each component type, which is useful for
    constructing or validating componets in a pipeline YAML.
    """
    async with AsyncDeepsetClient() as client:
        response = await client.request(endpoint="v1/haystack/components", method="GET")
        return response.json


@mcp.tool()
async def validate_pipeline_yaml(yaml_content: str) -> Any:
    """
    Validates the structure and syntax of a provided pipeline YAML configuration against the deepset API specifications.

    Provide the YAML content as a string.
    Returns a validation result, indicating success or detailing any errors or warnings found.
    Use this *before* attempting to create or update a pipeline with new YAML.
    """
    # Basic validation of the input
    if not yaml_content or not yaml_content.strip():
        return {"error": "Empty YAML content provided"}

    # Check if content looks like YAML (basic check)
    if not yaml_content.strip().startswith("components:") and "components:" not in yaml_content:
        return {"error": "Invalid YAML content - missing 'components:' section"}

    workspace = get_workspace()

    async with AsyncDeepsetClient() as client:
        response = await client.request(
            endpoint=f"v1/workspaces/{workspace}/pipeline_validations",
            method="POST",
            data={"query_yaml": yaml_content},
        )

        return response.json


@mcp.tool()
async def get_pipeline_yaml(pipeline_name: str) -> Any:
    """Retrieves the complete YAML configuration file for a specific pipeline.

    Use this when you need the exact YAML definition of an existing pipeline, for example, to inspect it or use it as
    a base for modifications.

    :param pipeline_name: The name of the pipeline to retrieve.

    :return: The YAML configuration file for the specified pipeline.
    """
    workspace = get_workspace()

    async with AsyncDeepsetClient() as client:
        response = await client.request(
            endpoint=f"v1/workspaces/{workspace}/pipeline/{pipeline_name}/yaml", method="GET"
        )
        resp = response.json

    if isinstance(resp, dict) and "yaml" in resp:
        return str(resp["yaml"])

    return str(resp)


@mcp.tool()
async def update_pipeline_yaml(pipeline_name: str, yaml_content: str) -> Any:
    """Updates an existing pipeline in deepset.

    This will replace the entire existing configuration of the pipeline.
    Use this carefully, preferably after validating the new YAML content.

    :param pipeline_name: The name of the pipeline to update.
    :param yaml_content: The YAML content that the pipeline should be updated with.

    :return: A dictionary indicating success or failure of the update.
    """
    # Basic validation
    if not yaml_content or not yaml_content.strip():
        return {"error": "Empty YAML content provided"}
    if not yaml_content.strip().startswith("components:") and "components:" not in yaml_content:
        return {"error": "Invalid YAML content - missing 'components:' section"}

    workspace = get_workspace()

    async with AsyncDeepsetClient() as client:
        response = await client.request(
            endpoint=f"v1/workspaces/{workspace}/pipeline/{pipeline_name}/yaml",
            method="PUT",
            data={"query_yaml": yaml_content},
        )

        return response.json


@mcp.tool()
async def list_pipeline_templates() -> str:
    """Retrieves a list of pipeline templates to build AI applications like RAG or Agents."""
    workspace = get_workspace()
    async with AsyncDeepsetClient() as client:
        resp = await client.request(
            endpoint=f"v1/workspaces/{workspace}/pipeline_templates?limit=100&page_number=1&field=created_at&order=DESC"
        )

        response = cast(dict[str, Any], resp.json)

    if isinstance(response, dict) and "error" in response:
        return f"Error retrieving pipeline templates: {response['error']}"

    # Extract the template data
    templates = response.get("data", [])

    if not templates:
        return "No pipeline templates found."

    # Format the response as requested
    formatted_output = []
    for template in templates:
        name = template.get("pipeline_name", "Unnamed Template")
        description = template.get("description", "No description available")

        formatted_output.append(f"<template>\n{name}\n\n{description}\n</template>\n")

    # Join all template entries and return
    return "\n".join(formatted_output)


@mcp.tool()
async def get_pipeline_template(template_name: str) -> str:
    """Retrieves a specific pipeline template by name and returns its YAML configurations.

    Parameters
    ----------
    template_name : str
        The name of the pipeline template to retrieve

    Returns
    -------
    str
        A formatted string containing the template's query and indexing YAML (if available)
    """
    workspace = get_workspace()

    async with AsyncDeepsetClient() as client:
        resp = await client.request(endpoint=f"v1/workspaces/{workspace}/pipeline_templates/{template_name}")

        response = cast(dict[str, Any], resp.json)

    if isinstance(response, dict) and "error" in response:
        return f"Error retrieving pipeline template: {response['error']}"

    # Extract the YAML data
    query_yaml = response.get("query_yaml")
    indexing_yaml = response.get("indexing_yaml")
    template_name = response.get("name", "Unnamed Template")

    # Format the response
    formatted_output = [f"# Pipeline Template: {template_name}\n"]

    # Add query YAML if available
    if query_yaml:
        formatted_output.append("## QUERY PIPELINE YAML\n```yaml\n" + query_yaml + "\n```\n")
    else:
        formatted_output.append("## QUERY PIPELINE YAML\nNo query pipeline YAML available for this template.\n")

    # Add indexing YAML if available
    if indexing_yaml:
        formatted_output.append("## INDEXING PIPELINE YAML\n```yaml\n" + indexing_yaml + "\n```\n")
    else:
        formatted_output.append("## INDEXING PIPELINE YAML\nNo indexing pipeline YAML available for this template.\n")

    # Join all sections and return
    return "\n".join(formatted_output)


@mcp.tool()
async def get_custom_components() -> str:
    """Use this to get a list of all installed custom components."""
    response = await get_component_schemas()

    # Check for errors in the response
    if isinstance(response, dict) and "error" in response:
        return f"Error retrieving component schemas: {response['error']}"

    # Navigate to the components definition section
    # Typically structured as {definitions: {Components: {<component_name>: <schema>}}}
    schemas = response.get("component_schema", {})
    schemas = schemas.get("definitions", {}).get("Components", {})

    if not schemas:
        return "No component schemas found or unexpected schema format."

    # Filter for custom components (those with package_version key)
    custom_components = {}
    for component_name, schema in schemas.items():
        if "package_version" in schema:
            custom_components[component_name] = schema

    if not custom_components:
        return "No custom components found."

    # Format the response
    formatted_output = [f"# Custom Components ({len(custom_components)} found)\n"]

    for component_name, schema in custom_components.items():
        # Extract key information
        package_version = schema.get("package_version", "Unknown")
        dynamic_params = schema.get("dynamic_params", False)

        # Get component type info
        type_info = schema.get("properties", {}).get("type", {})
        const_value = type_info.get("const", "Unknown")
        family = type_info.get("family", "Unknown")
        family_description = type_info.get("family_description", "No description")

        # Format component details
        component_details = [
            f"## {component_name}",
            f"- **Type**: `{const_value}`",
            f"- **Package Version**: {package_version}",
            f"- **Family**: {family} - {family_description}",
            f"- **Dynamic Parameters**: {'Yes' if dynamic_params else 'No'}",
        ]

        # Add init parameters if available
        init_params = schema.get("properties", {}).get("init_parameters", {}).get("properties", {})
        if init_params:
            component_details.append("\n### Init Parameters:")
            for param_name, param_info in init_params.items():
                param_type = param_info.get("type", "Unknown")
                required = param_name in schema.get("properties", {}).get("init_parameters", {}).get("required", [])
                param_description = param_info.get("description", "No description")

                component_details.append(f"- **{param_name}** ({param_type}{', required' if required else ''}):")
                component_details.append(f"  {param_description}")

        formatted_output.append("\n".join(component_details) + "\n")

    # Join all sections and return
    return "\n".join(formatted_output)


@mcp.tool()
async def get_latest_custom_component_installation_logs() -> Any:
    """
    Use this to get the logs from the latest custom component installation.

    This will give you the full installation log output.
    It is useful for debugging custom component installations.
    """
    async with AsyncDeepsetClient() as client:
        return await client.request(endpoint="v2/custom_components/logs")


@mcp.tool()
async def list_custom_component_installations() -> str:
    """
    Retrieves a list of the most recent custom component installations.

    This will return version number, high-level log, status and information about who uploaded the package.
    """
    endpoint = "v2/custom_components?limit=20&page_number=1&field=created_at&order=DESC"
    async with AsyncDeepsetClient() as client:
        resp = await client.request(endpoint=endpoint)

        response = cast(dict[str, Any], resp.json)

    installations = response.get("data", [])
    total = response.get("total", 0)
    has_more = response.get("has_more", False)

    if not installations:
        return "No custom component installations found."

    # Format the response
    formatted_output = [f"# Custom Component Installations (showing {len(installations)} of {total})\n"]

    for install in installations:
        # Extract key information
        component_id = install.get("custom_component_id", "Unknown")
        status = install.get("status", "Unknown")
        version = install.get("version", "Unknown")
        user_id = install.get("created_by_user_id", "Unknown")

        # Try to fetch user information
        user_info = "Unknown"
        if user_id != "Unknown":
            user_url = f"v1/users/{user_id}"
            async with AsyncDeepsetClient() as client:
                user_response = await client.request(endpoint=user_url)

            user_data = user_response.json
            assert user_data is not None
            given_name = user_data.get("given_name", "")
            family_name = user_data.get("family_name", "")
            email = user_data.get("email", "")
            user_info = f"{given_name} {family_name} ({email})"

        # Format installation details
        install_details = [
            f"## Installation {component_id[:8]}...",
            f"- **Status**: {status}",
            f"- **Version**: {version}",
            f"- **Installed by**: {user_info}",
        ]

        # Add logs if available
        logs = install.get("logs", [])
        if logs:
            install_details.append("\n### Recent Logs:")
            for log in logs[:5]:  # Show only the first 5 logs
                level = log.get("level", "INFO")
                msg = log.get("msg", "No message")
                install_details.append(f"- [{level}] {msg}")

            if len(logs) > 5:
                install_details.append(f"- ... and {len(logs) - 5} more log entries")

        formatted_output.append("\n".join(install_details) + "\n")

        if has_more:
            formatted_output.append(
                "*Note: There are more installations available. This listing shows only the 10 most recent.*"
            )

    # Join all sections and return
    return "\n".join(formatted_output)


def launch_mcp() -> None:
    """Launches the MCP server."""
    mcp.run()


if __name__ == "__main__":
    launch_mcp()
