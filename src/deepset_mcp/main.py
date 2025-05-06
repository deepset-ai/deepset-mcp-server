import os
from typing import Any
from functools import wraps

import asyncio
import httpx
import requests
from mcp.server.fastmcp import FastMCP
from requests import HTTPError

from deepset_mcp.client import DeepsetClient

# Initialize MCP Server
mcp = FastMCP("Deepset Cloud MCP")

# Configuration
DEEPSET_API_BASE_URL = "https://api.cloud.deepset.ai/api/v1"


# Helper function to get API key from environment variable
def get_api_key() -> str:
    """Gets the API key configured for the environment."""
    api_key = os.environ.get("DEEPSET_API_KEY")
    if not api_key:
        raise ValueError("DEEPSET_API_KEY environment variable not set")
    return api_key


# Helper function to get workspace name from environment variable
def get_workspace() -> str:
    """Gets the workspace configured for the environment."""
    workspace = os.environ.get("DEEPSET_WORKSPACE")
    if not workspace:
        raise ValueError("DEEPSET_WORKSPACE environment variable not set")
    return workspace


# Function to make authenticated requests to deepset Cloud API
def deepset_api_request(endpoint: str, method: str = "GET", data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Makes a request to the deepset API."""
    headers = {"Authorization": f"Bearer {get_api_key()}", "Accept": "application/json,text/plain,*/*"}

    url = f"{DEEPSET_API_BASE_URL}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            headers["Content-Type"] = "application/json"
            response = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if response.status_code >= 400:
            error_message = f"API Error: {response.status_code}"
            try:
                error_details = response.json()
            except requests.exceptions.JSONDecodeError:
                error_details = response.text if response.text else "No error details provided by API"
            return {"error": error_message, "details": error_details}

        if not response.text or not response.text.strip():
            return {"status": "success", "message": "API returned empty response body"}

        try:
            return response.json()  # type: ignore
        except requests.exceptions.JSONDecodeError:
            return {"result": response.text, "warning": "API response was not valid JSON"}

    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error during request: {str(e)}"}


@mcp.tool()
def list_pipelines() -> dict[str, Any]:
    """Retrieves a list of all pipelines available within the currently configured deepset workspace.

    Use this when you need to know the names or IDs of existing pipelines.
    """
    workspace = get_workspace()
    try:
        return deepset_api_request(f"/workspaces/{workspace}/pipelines")
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_pipeline(pipeline_id: str) -> dict[str, Any]:
    """Fetches detailed configuration information for a specific pipeline, identified by its unique `pipeline_id`.

    This includes its components, connections, and metadata.
    Use this when you need to inspect the structure or settings of a known pipeline.

    :param pipeline_id: ID of the pipeline to retrieve.
    """
    workspace = get_workspace()
    try:
        return deepset_api_request(f"/workspaces/{workspace}/pipelines/{pipeline_id}")
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_component_schemas() -> dict[str, Any]:
    """Retrieves the schemas for all available Haystack components from the deepset API.

    These schemas define the expected input and output parameters for each component type, which is useful for
    constructing or validating componets in a pipeline YAML.
    """
    try:
        return deepset_api_request("/haystack/components")
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def validate_pipeline_yaml(yaml_content: str) -> dict[str, Any]:
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
    try:
        # Ensure the YAML is properly formatted for the request
        # The API expects the raw YAML as a string value in the query_yaml field
        payload = {"query_yaml": yaml_content}

        # Send the request with the properly formatted payload
        response = deepset_api_request(f"/workspaces/{workspace}/pipeline_validations", method="POST", data=payload)
        return response
    except Exception as e:
        error_details = str(e)
        # Provide clear error information
        return {
            "error": f"Validation API error: {error_details}",
            "details": "Make sure your YAML is properly formatted for a query pipeline",
            "tip": (
                "The YAML must be a valid query pipeline configuration with components, connections, inputs, and "
                "outputs sections."
            ),
        }


@mcp.tool()
def get_pipeline_yaml(pipeline_name: str) -> str | dict[str, Any]:
    """Retrieves the complete YAML configuration file for a specific pipeline.

    Use this when you need the exact YAML definition of an existing pipeline, for example, to inspect it or use it as
    a base for modifications.

    :param pipeline_name: The name of the pipeline to retrieve.

    :return: The YAML configuration file for the specified pipeline.
    """
    workspace = get_workspace()
    try:
        response = deepset_api_request(f"/workspaces/{workspace}/pipelines/{pipeline_name}/yaml")
        # The response might be already a string or might need formatting
        # depending on the API response structure
        if isinstance(response, dict) and "yaml" in response:
            return str(response["yaml"])
        return str(response)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def update_pipeline_yaml(pipeline_name: str, yaml_content: str) -> dict[str, Any]:
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
    try:
        endpoint = f"/workspaces/{workspace}/pipelines/{pipeline_name}/yaml"

        # API expects JSON input even for PUT /yaml endpoint
        headers = {
            "Authorization": f"Bearer {get_api_key()}",
            "Content-Type": "application/json",  # Set Content-Type to JSON
            "Accept": "application/json,text/plain,*/*",
        }

        # Structure the data as JSON payload
        payload = {"query_yaml": yaml_content}

        url = f"{DEEPSET_API_BASE_URL}{endpoint}"
        # Send JSON payload using the json parameter
        response = requests.put(url, headers=headers, json=payload)

        # Handle response (using similar logic as deepset_api_request)
        if response.status_code >= 400:
            error_message = f"API Error: {response.status_code}"
            try:
                error_details = response.json()
            except requests.exceptions.JSONDecodeError:
                error_details = response.text if response.text else "No error details provided"
            return {"error": error_message, "details": error_details}

        if not response.text or not response.text.strip():
            return {"status": "success", "message": "Pipeline YAML updated successfully (empty response body)"}

        try:
            return response.json()  # type: ignore
        except requests.exceptions.JSONDecodeError:
            return {"result": response.text, "warning": "API response was not valid JSON"}

    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error during YAML update: {str(e)}"}


@mcp.resource("pipelines://all")
def get_all_pipelines_resource() -> str:
    """Return all pipelines as a resource."""
    result = list_pipelines()
    return str(result)


@mcp.resource("pipeline://{pipeline_id}")
def get_pipeline_resource(pipeline_id: str) -> str:
    """Return a specific pipeline as a resource."""
    result = get_pipeline(pipeline_id)
    return str(result)


@mcp.resource("components://schemas")
def get_component_schemas_resource() -> str:
    """Return all component schemas as a resource."""
    result = get_component_schemas()
    return str(result)


@mcp.resource("pipeline-yaml://{pipeline_name}")
def get_pipeline_yaml_resource(pipeline_name: str) -> str | dict[str, Any]:
    """Return the YAML definition of a specific pipeline as a resource."""
    return get_pipeline_yaml(pipeline_name)  # type: ignore


@mcp.tool()
def list_pipeline_templates() -> str:
    """Retrieves a list of pipeline templates to build AI applications like RAG or Agents."""
    workspace = get_workspace()
    try:
        # Build the query parameters with fixed values
        endpoint = f"/workspaces/{workspace}/pipeline_templates?limit=100&page_number=1&field=created_at&order=DESC"

        # Make the API request
        response = deepset_api_request(endpoint)

        # Check for errors in the response
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

    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_pipeline_template(template_name: str) -> str:
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
    try:
        # Build the endpoint URL
        endpoint = f"/workspaces/{workspace}/pipeline_templates/{template_name}"

        # Make the API request
        response = deepset_api_request(endpoint)

        # Check for errors in the response
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
            formatted_output.append(
                "## INDEXING PIPELINE YAML\nNo indexing pipeline YAML available for this template.\n"
            )

        # Join all sections and return
        return "\n".join(formatted_output)

    except Exception as e:
        return f"Error retrieving pipeline template: {str(e)}"


@mcp.tool()
def get_custom_components() -> str:
    """Use this to get a list of all installed custom components."""
    try:
        # Retrieve all component schemas
        response = get_component_schemas()

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

    except Exception as e:
        return f"Error retrieving custom components: {str(e)}"


@mcp.tool()
def get_latest_custom_component_installation_logs() -> str:
    """
    Use this to get the logs from the latest custom component installation.

    This will give you the full installation log output.
    It is useful for debugging custom component installations.
    """
    try:
        # Note: This endpoint uses v2 of the API instead of v1
        endpoint = "/custom_components/logs"

        # Set up headers - using accept: text/plain since log output is plain text
        headers = {"Authorization": f"Bearer {get_api_key()}", "Accept": "text/plain"}

        url = f"{DEEPSET_API_BASE_URL.replace('/api/v1', '/api/v2')}{endpoint}"

        try:
            # Make direct request since our helper function expects JSON response
            response = requests.get(url, headers=headers)

            if response.status_code >= 400:
                error_message = f"API Error: {response.status_code}"
                try:
                    # Try to get any structured error info
                    error_details = response.json()
                except Exception:
                    # Fall back to text if not JSON
                    error_details = response.text if response.text else "No error details provided by API"
                return f"Error retrieving installation logs: {error_message}\nDetails: {error_details}"

            # Return raw log text
            return response.text

        except requests.exceptions.RequestException as e:
            return f"Request failed: {str(e)}"

    except Exception as e:
        return f"Error retrieving custom component logs: {str(e)}"


@mcp.tool()
def list_custom_component_installations() -> str:
    """
    Retrieves a list of the most recent custom component installations.

    This will return version number, high-level log, status and information about who uploaded the package.
    """
    try:
        # Note: This endpoint uses v2 of the API instead of v1
        endpoint = "/custom_components?limit=20&page_number=1&field=created_at&order=DESC"

        # Set up headers
        headers = {"Authorization": f"Bearer {get_api_key()}", "Accept": "application/json"}

        url = f"{DEEPSET_API_BASE_URL.replace('/api/v1', '/api/v2')}{endpoint}"

        try:
            # Make direct request
            response = requests.get(url, headers=headers)

            try:
                response.raise_for_status()
                data = response.json()
            except HTTPError:
                error_message = f"HTTP Error: {response.status_code}"
                error_details = response.text if response.text else "No error details provided by API"
                return f"Error retrieving installation history: {error_message}\nDetails: {error_details}"

            installations = data.get("data", [])
            total = data.get("total", 0)
            has_more = data.get("has_more", False)

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
                    try:
                        # Make request to the user API endpoint
                        user_url = f"{DEEPSET_API_BASE_URL}/users/{user_id}"
                        user_response = requests.get(
                            user_url, headers={"Authorization": f"Bearer {get_api_key()}", "Accept": "application/json"}
                        )

                        if user_response.status_code == 200:
                            user_data = user_response.json()
                            given_name = user_data.get("given_name", "")
                            family_name = user_data.get("family_name", "")
                            email = user_data.get("email", "")

                            if given_name and family_name:
                                user_info = f"{given_name} {family_name} ({email})"
                            elif email:
                                user_info = email
                    except Exception as e:
                        user_info = f"Error fetching user: {str(e)}"

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

        except requests.exceptions.RequestException as e:
            return f"Request failed: {str(e)}"

    except Exception as e:
        return f"Error retrieving custom component installations: {str(e)}"


def launch_mcp() -> None:
    """Launches the MCP server."""
    mcp.run()


if __name__ == "__main__":
    launch_mcp()
