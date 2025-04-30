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
        "Accept": "application/json"
    }
    
    url = f"{DEEPSET_API_BASE_URL}{endpoint}"
    
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        headers["Content-Type"] = "application/json"
        response = requests.post(url, headers=headers, json=data)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
    
    if response.status_code >= 400:
        raise Exception(f"API error: {response.status_code} - {response.text}")
    
    return response.json()

@mcp.tool()
def list_pipelines() -> Dict[str, Any]:
    """Lists all pipelines in the configured deepset Cloud workspace"""
    workspace = get_workspace()
    try:
        return deepset_api_request(f"/workspaces/{workspace}/pipelines")
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_pipeline(pipeline_id: str) -> Dict[str, Any]:
    """Gets details for a specific pipeline by ID"""
    workspace = get_workspace()
    try:
        return deepset_api_request(f"/workspaces/{workspace}/pipelines/{pipeline_id}")
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_component_schemas() -> Dict[str, Any]:
    """
    Fetches all available Haystack component schemas showing their input/output types
    from the deepset Cloud API
    """
    try:
        return deepset_api_request("/haystack/components/input-output")
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_pipeline_yaml(pipeline_name: str) -> str:
    """
    Fetches the YAML definition of a specific pipeline
    
    Args:
        pipeline_name: The name of the pipeline to retrieve the YAML for
        
    Returns:
        The pipeline YAML definition as a string
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
    mcp.run()
