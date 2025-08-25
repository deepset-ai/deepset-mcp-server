# MCP Server Guides

## How to configure an MCP server to connect to the deepset platform

This guide shows how to set up an MCP server that connects to the deepset platform using the deepset-mcp library.

### Prerequisites

- deepset API key
- Python environment with deepset-mcp-server installed

### Basic server setup

Create a FastMCP server instance and configure it:

```python
from mcp.server.fastmcp import FastMCP
from deepset_mcp.mcp.server import configure_mcp_server

# Create server instance
mcp = FastMCP("deepset AI platform MCP server")

# Configure with API key and workspace
# This will take care of registering all deepset mcp tools on the instance
configure_mcp_server(
    mcp_server_instance=mcp,
    deepset_api_key="your-api-key",
    deepset_workspace="your-workspace",  # Optional: leave as None to require workspace in tool calls
    tools_to_register=None,  # Register all available tools
)

# Run the server
mcp.run(transport="stdio")
```

### Authentication options

#### Static API key
Pass the API key directly to `configure_mcp_server`:

```python
configure_mcp_server(
    mcp_server_instance=mcp,
    deepset_api_key="your-api-key",
)
```

#### Dynamic API key from request headers
Extract API key from authorization headers (useful for multi-user scenarios):

```python
configure_mcp_server(
    mcp_server_instance=mcp,
    get_api_key_from_authorization_header=True,
)
```

When using dynamic authentication, tools automatically receive a `ctx` parameter containing the [MCP Context](https://github.com/modelcontextprotocol/python-sdk?tab=readme-ov-file#context). The tool extracts the API key from the `Authorization` header in the request:

```python
# The tool automatically extracts: ctx.request_context.request.headers.get("Authorization")
# Removes "Bearer " prefix and uses the token as the deepset API key
```

### Workspace configuration

#### Fixed workspace
Pre-configure a workspace for all tool calls:

```python
configure_mcp_server(
    mcp_server_instance=mcp,
    deepset_workspace="my-workspace",
)
```

#### Dynamic workspace
Leave workspace as `None` to require it in each tool call:

```python
configure_mcp_server(
    mcp_server_instance=mcp,
    deepset_workspace=None,
)
```

### Tool selection

Register specific tools instead of all available tools:

```python
configure_mcp_server(
    mcp_server_instance=mcp,
    tools_to_register={"list_pipelines", "get_pipeline", "search_pipeline", "create_pipeline"},
)
```

See the [tool reference](../reference/tool_reference.md) for the complete list of available tools.

## How to add custom tools

This guide shows how to create and register custom tools that integrate with the deepset platform.

### Create a custom tool function

Define an async function that accepts the required parameters:

```python
async def get_current_user(*, client: AsyncDeepsetClient) -> DeepsetUser | str:
    """Get information about the current user.
    
    :param client: The deepset API client
    :returns: User information or error message
    """
    try:
        # Use client to make API calls
        resp = await client.request("v1/users/me", method="GET")
        if resp.success and resp.json:
            return DeepsetUser(**resp.json)
        return "Failed to get user information"
    except Exception as e:
        return f"Error: {e}"
```

### Configure the tool

Create a `ToolConfig` to specify dependencies:

```python
from deepset_mcp.mcp import ToolConfig

config = ToolConfig(
    needs_client=True,  # Inject AsyncDeepsetClient
    needs_workspace=False,  # No workspace needed for this tool
)
```

### Build and register the tool

Use `build_tool` to handle dependency injection:

```python
from deepset_mcp.mcp import build_tool

# Build the enhanced tool
enhanced_tool = build_tool(
    base_func=get_current_user,
    config=config,
    api_key="your-api-key",  # Or use dynamic auth
    use_request_context=False,
)

# Register with server
mcp.add_tool(enhanced_tool, name="get_current_user")
```

### Complete example

```python
from mcp.server.fastmcp import FastMCP
from deepset_mcp.mcp import build_tool, ToolConfig, configure_mcp_server
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.shared_models import DeepsetUser

async def get_current_user(*, client: AsyncClientProtocol) -> DeepsetUser | str:
    """Get current user information."""
    try:
        resp = await client.request("v1/users/me", method="GET")
        if resp.success and resp.json:
            return DeepsetUser(**resp.json)
        return "Failed to get user information"
    except Exception as e:
        return f"Error: {e}"

# Setup server
mcp = FastMCP("Custom deepset MCP server")
configure_mcp_server(
    mcp_server_instance=mcp,
    deepset_api_key="your-api-key"
)

# Add custom tool
config = ToolConfig(needs_client=True)
enhanced_tool = build_tool(
    base_func=get_current_user,
    config=config,
    api_key="your-api-key",
    use_request_context=False,
)
mcp.add_tool(enhanced_tool, name="get_current_user")

# Run server
mcp.run(transport="stdio")

# We now have all deepset mcp tools alongside your custom get_current_user tool exposed on the server
```

## How to expose a single deepset pipeline as a tool

This guide shows how to create a tool that uses a specific deepset pipeline.

### Import the pipeline search function

```python
from deepset_mcp.tools.pipeline import search_pipeline
```

### Configure for pipeline search

Create a `ToolConfig` with the pipeline name as a custom argument:

```python
from deepset_mcp.mcp import ToolConfig

config = ToolConfig(
    needs_client=True,
    needs_workspace=True,
    custom_args={"pipeline_name": "my-search-pipeline"}
)
```

### Build and register the tool

```python
from deepset_mcp.mcp import build_tool

# Build the pipeline search tool
pipeline_tool = build_tool(
    base_func=search_pipeline,
    config=config,
    api_key="your-api-key",
    workspace="my-workspace", # Needs to be the workspace that your pipeline is running in
    use_request_context=False,
)

# Register with custom name and description
# The description is important as it will act as the tool prompt so that your Agent knows when to call this tool
mcp.add_tool(
    pipeline_tool, 
    name="search_my_pipeline",
    description="Search through documents using the my-search-pipeline. Provide queries in natural language."
)
```

### Complete example

```python
from mcp.server.fastmcp import FastMCP
from deepset_mcp.mcp import build_tool, ToolConfig
from deepset_mcp.tools.pipeline import search_pipeline

# Setup server
mcp = FastMCP("Pipeline search MCP server")

# Configure pipeline tool
config = ToolConfig(
    needs_client=True,
    needs_workspace=True,
    custom_args={"pipeline_name": "document-search"}
)

# Build and register pipeline tool
pipeline_tool = build_tool(
    base_func=search_pipeline,
    config=config,
    api_key="your-api-key",
    workspace="my-workspace",
    use_request_context=False,
)
mcp.add_tool(
    pipeline_tool, 
    name="search_documents",
    description="Search through the document collection. Use this for finding information in company documents, manuals, and knowledge base articles."
)

# Run server
mcp.run(transport="stdio")
```

### Multiple pipeline tools

Register multiple pipeline tools for different use cases:

```python
# Document search pipeline
doc_config = ToolConfig(
    needs_client=True,
    needs_workspace=True,
    custom_args={"pipeline_name": "document-search"}
)
doc_tool = build_tool(search_pipeline, doc_config, api_key="your-key", workspace="my-workspace")
mcp.add_tool(
    doc_tool, 
    name="search_documents",
    description="Search company documents and knowledge base articles. Use for finding policies, procedures, and technical documentation."
)

# FAQ search pipeline
faq_config = ToolConfig(
    needs_client=True,
    needs_workspace=True,
    custom_args={"pipeline_name": "faq-search"}
)
faq_tool = build_tool(search_pipeline, faq_config, api_key="your-key", workspace="my-workspace")
mcp.add_tool(
    faq_tool, 
    name="search_faq",
    description="Search frequently asked questions. Use this for common questions about products, services, or company policies."
)
```

### Custom tool descriptions

When registering pipeline tools, you can provide custom descriptions to guide LLM usage. If no description is provided, the tool uses the default `search_pipeline` function docstring. Custom descriptions should explain:

- What type of content the pipeline searches
- When to use this tool vs others  
- Example use cases
