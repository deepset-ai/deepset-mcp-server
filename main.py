import os
import requests
from typing import Dict, Any, Optional

from mcp.server.fastmcp import FastMCP

# Initialize MCP Server
mcp = FastMCP("Deepset Cloud MCP")

# Configuration
DEEPSET_API_BASE_URL = "https://api.cloud.deepset.ai/api/v1"

# Helper function to get API key from environment variable
def get_api_key() -> str:
    api_key = os.environ.get("DEEPSET_API_KEY")
    if not api_key:
        raise ValueError("DEEPSET_API_KEY environment variable not set")
    return api_key

# Helper function to get workspace name from environment variable
def get_workspace() -> str:
    workspace = os.environ.get("DEEPSET_WORKSPACE")
    if not workspace:
        raise ValueError("DEEPSET_WORKSPACE environment variable not set")
    return workspace

# Function to make authenticated requests to deepset Cloud API
def deepset_api_request(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Accept": "application/json,text/plain,*/*"
    }
    
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
            return {
                "error": error_message,
                "details": error_details
            }
        
        if not response.text or not response.text.strip():
            return {"status": "success", "message": "API returned empty response body"}
            
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return {"result": response.text, "warning": "API response was not valid JSON"}

    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error during request: {str(e)}"}

@mcp.tool()
def list_pipelines() -> Dict[str, Any]:
    """Retrieves a list of all pipelines available within the currently configured deepset workspace. Use this when you need to know the names or IDs of existing pipelines."""
    workspace = get_workspace()
    try:
        return deepset_api_request(f"/workspaces/{workspace}/pipelines")
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_pipeline(pipeline_id: str) -> Dict[str, Any]:
    """Fetches detailed configuration information for a specific pipeline, identified by its unique `pipeline_id`. This includes its components, connections, and metadata. Use this when you need to inspect the structure or settings of a known pipeline."""
    workspace = get_workspace()
    try:
        return deepset_api_request(f"/workspaces/{workspace}/pipelines/{pipeline_id}")
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_component_schemas() -> Dict[str, Any]:
    """Retrieves the schemas for all available Haystack components from the deepset API. These schemas define the expected input and output parameters for each component type, which is useful for constructing or validating componets in a pipeline YAML."""
    try:
        return deepset_api_request("/haystack/components/input-output")
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def validate_pipeline_yaml(yaml_content: str) -> Dict[str, Any]:
    """
    Validates the structure and syntax of a provided pipeline YAML configuration against the deepset API specifications. Provide the YAML content as a string. Returns a validation result, indicating success or detailing any errors or warnings found. Use this *before* attempting to create or update a pipeline with new YAML.
    """
    # Basic validation of the input
    if not yaml_content or not yaml_content.strip():
        return {"error": "Empty YAML content provided"}
        
    # Check if content looks like YAML (basic check)
    if not yaml_content.strip().startswith("components:") and not "components:" in yaml_content:
        return {"error": "Invalid YAML content - missing 'components:' section"}
    
    workspace = get_workspace()
    try:
        # Ensure the YAML is properly formatted for the request
        # The API expects the raw YAML as a string value in the query_yaml field
        payload = {"query_yaml": yaml_content}
        
        # Send the request with the properly formatted payload
        response = deepset_api_request(
            f"/workspaces/{workspace}/pipeline_validations",
            method="POST",
            data=payload
        )
        return response
    except Exception as e:
        error_details = str(e)
        # Provide clear error information
        return {
            "error": f"Validation API error: {error_details}", 
            "details": "Make sure your YAML is properly formatted for a query pipeline",
            "tip": "The YAML must be a valid query pipeline configuration with components, connections, inputs, and outputs sections."
        }

@mcp.tool()
def get_pipeline_yaml(pipeline_name: str) -> str:
    """
    Retrieves the complete YAML configuration file for a specific pipeline, identified by its `pipeline_name`. Returns the YAML content as a string. Use this when you need the exact YAML definition of an existing pipeline, for example, to inspect it or use it as a base for modifications.
    """
    workspace = get_workspace()
    try:
        response = deepset_api_request(f"/workspaces/{workspace}/pipelines/{pipeline_name}/yaml")
        # The response might be already a string or might need formatting 
        # depending on the API response structure
        if isinstance(response, dict) and "yaml" in response:
            return response["yaml"]
        return str(response)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def update_pipeline_yaml(pipeline_name: str, yaml_content: str) -> Dict[str, Any]:
    """
    Updates an existing pipeline in deepset, identified by `pipeline_name`, with a new YAML configuration provided as `yaml_content`. This will replace the entire existing configuration of the pipeline. Use this carefully, preferably after validating the new YAML content.
    """
    # Basic validation
    if not yaml_content or not yaml_content.strip():
        return {"error": "Empty YAML content provided"}
    if not yaml_content.strip().startswith("components:") and not "components:" in yaml_content:
        return {"error": "Invalid YAML content - missing 'components:' section"}

    workspace = get_workspace()
    try:
        endpoint = f"/workspaces/{workspace}/pipelines/{pipeline_name}/yaml"

        # API expects JSON input even for PUT /yaml endpoint
        headers = {
            "Authorization": f"Bearer {get_api_key()}",
            "Content-Type": "application/json",  # Set Content-Type to JSON
            "Accept": "application/json,text/plain,*/*" 
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
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return {"result": response.text, "warning": "API response was not valid JSON"}

    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error during YAML update: {str(e)}"}

@mcp.resource("pipelines://all")
def get_all_pipelines_resource() -> str:
    """Return all pipelines as a resource"""
    result = list_pipelines()
    return str(result)

@mcp.resource("pipeline://{pipeline_id}")
def get_pipeline_resource(pipeline_id: str) -> str:
    """Return a specific pipeline as a resource"""
    result = get_pipeline(pipeline_id)
    return str(result)

@mcp.resource("components://schemas")
def get_component_schemas_resource() -> str:
    """Return all component schemas as a resource"""
    result = get_component_schemas()
    return str(result)

@mcp.resource("pipeline-yaml://{pipeline_name}")
def get_pipeline_yaml_resource(pipeline_name: str) -> str:
    """Return the YAML definition of a specific pipeline as a resource"""
    return get_pipeline_yaml(pipeline_name)

if __name__ == "__main__":
    # Using the built-in server runner
    # Ensure it binds to 0.0.0.0 to be accessible in Docker
    mcp.run(host="0.0.0.0", port=8000) 