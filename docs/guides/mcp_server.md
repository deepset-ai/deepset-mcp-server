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
from deepset_mcp.tools import search_pipeline
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
from deepset_mcp.tools import search_pipeline

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

## How to deploy as a remote MCP server

This guide shows how to set up the deepset MCP server as a remote service that can be accessed by multiple clients over HTTP, rather than running locally with stdio transport.

### Prerequisites

- Production-ready web server infrastructure
- OAuth or similar authentication system
- Redis instance for object store backend
- SSL/TLS certificates for HTTPS

### Key differences from local setup

When running as a remote MCP server, several configuration changes are required:

1. **Transport Protocol**: Use `streamable-http` instead of `stdio`
2. **Object Store Backend**: Use Redis instead of memory for scalability
3. **Authentication**: Extract API keys from authorization headers
4. **Dynamic Workspace Mode**: Support multiple users with different workspaces

### Basic remote server setup

```python
from mcp.server.fastmcp import FastMCP
from deepset_mcp import configure_mcp_server, ALL_DEEPSET_TOOLS

# Create server instance
mcp = FastMCP("Deepset Remote MCP Server")

# Configure for remote deployment
configure_mcp_server(
    mcp_server_instance=mcp,
    tools_to_register=ALL_DEEPSET_TOOLS,
    get_api_key_from_authorization_header=True,
    object_store_backend="redis",
    object_store_redis_url="redis://localhost:6379",
    object_store_ttl=600,
)

# Run with HTTP transport
if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
```

### Redis configuration

The remote server requires Redis for the object store backend to handle multiple concurrent users:

```python
configure_mcp_server(
    mcp_server_instance=mcp,
    # ... other parameters
    object_store_backend="redis",
    object_store_redis_url="redis://your-redis-host:6379",
    object_store_ttl=600,  # 10 minutes
)
```

**Redis connection options:**

```python
# Basic Redis connection
object_store_redis_url="redis://localhost:6379"

# Redis with authentication
object_store_redis_url="redis://username:password@host:6379"

# Redis with SSL/TLS
object_store_redis_url="rediss://host:6379"

# Redis cluster
object_store_redis_url="redis://host1:6379,host2:6379,host3:6379"
```

### Authentication and authorization

The remote server extracts deepset API keys from client request headers:

```python
configure_mcp_server(
    mcp_server_instance=mcp,
    get_api_key_from_authorization_header=True,
    # No static deepset_api_key needed
)
```

**Client request format:**

Clients must include the deepset API key in the Authorization header:

```http
POST /mcp/v1/tools/list_pipelines
Authorization: Bearer your-deepset-api-key
Content-Type: application/json
```

### Multi-user workspace support

Enable dynamic workspace mode to support multiple users:

```python
configure_mcp_server(
    mcp_server_instance=mcp,
    deepset_workspace=None,  # Allow dynamic workspace selection
    get_api_key_from_authorization_header=True,
)
```

Users can specify workspaces in tool calls:
- "list my pipelines in the production workspace"
- "create a pipeline in the staging workspace"

### Production deployment considerations

**Security:**
- Implement proper authentication middleware
- Use HTTPS with valid SSL certificates  
- Validate and sanitize all client inputs
- Set up proper CORS policies

**Scalability:**
- Use a production WSGI server (gunicorn, uvicorn)
- Configure load balancing for multiple server instances
- Set appropriate Redis connection pool sizes
- Monitor server performance and resource usage

**Monitoring:**
```python
import logging

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

mcp = FastMCP("Deepset Remote MCP Server")
# Add monitoring middleware here
```

### Complete production example

```python
import logging
from mcp.server.fastmcp import FastMCP
from deepset_mcp import configure_mcp_server, ALL_DEEPSET_TOOLS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create server instance
mcp = FastMCP("Deepset Production MCP Server")

# Add your authentication middleware here
async def auth_middleware(request, handler):
    # Implement OAuth validation
    # Extract user info, validate tokens, etc.
    return await handler(request)

# Configure with production settings
configure_mcp_server(
    mcp_server_instance=mcp,
    tools_to_register=ALL_DEEPSET_TOOLS,
    get_api_key_from_authorization_header=True,
    object_store_backend="redis",
    object_store_redis_url="redis://your-redis-cluster:6379",
    object_store_ttl=1800,  # 30 minutes for production
)

if __name__ == "__main__":
    # Production server configuration
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        # Add SSL context for HTTPS in production
    )
```

### Client configuration

Configure MCP clients to connect to your remote server:

```json
{
  "mcpServers": {
    "deepset-remote": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "https://your-server.com/mcp",
        "-H", "Authorization: Bearer your-deepset-api-key",
        "-H", "Content-Type: application/json"
      ]
    }
  }
}
```

### Troubleshooting

**Common issues:**

- **Redis connection errors**: Verify Redis URL and network connectivity
- **Authentication failures**: Check authorization header format and API key validity  
- **Object store timeouts**: Adjust TTL settings based on usage patterns
- **Memory usage**: Monitor Redis memory usage and configure appropriate limits

## How to use deepset-mcp with a custom Haystack Agent

This guide shows how to integrate deepset-mcp tools with custom Haystack Agents using the MCPToolset. This enables agents to access your deepset platform resources, manage pipelines, search indexes, and work with Haystack components programmatically.

### Prerequisites

- deepset API key and workspace access
- Python environment with haystack-ai and deepset-mcp installed
- A running deepset MCP server (local or remote)

### Install dependencies

```bash
pip install haystack-ai deepset-mcp
```

### Agent setup with deepset-mcp tools

Create an agent that can access your deepset platform through MCP tools:

```python
import os
from haystack.components.agent.agent import Agent
from haystack.components.generators.chat.openai import OpenAIChatGenerator
from haystack_integrations.tools.mcp import MCPToolset, StdioServerInfo
from haystack.dataclasses.chat_message import ChatMessage

# Configure the MCP connection to deepset-mcp server
# This will start a locally running mcp server
server_info = StdioServerInfo(
    command="uvx",
    args=["deepset-mcp"],
    env={
        "DEEPSET_API_KEY": os.getenv("DEEPSET_API_KEY"),
        "DEEPSET_WORKSPACE": os.getenv("DEEPSET_WORKSPACE")  # Optional
    }
)

# Create MCPToolset that connects to deepset-mcp server
toolset = MCPToolset(server_info=server_info)

# Create chat generator
generator = OpenAIChatGenerator(
    model="gpt-5",
    api_key=os.getenv("OPENAI_API_KEY")
)

# Create agent with system prompt and deepset tools
agent = Agent(
    chat_generator=generator,
    tools=toolset,
    system_prompt="You are an AI assistant with access to the deepset AI platform. Use the available tools to help users create, manage, and debug AI pipelines on the platform."
)

# Use the agent with proper message formatting
query = "List all my pipelines and show their status"
result = agent.run([ChatMessage.from_user(query)])
print(result["messages"][-1]["content"])
```

### Filtering deepset tools for specific use cases

Limit the agent to specific deepset tools for focused functionality:

```python
import os
from haystack.components.agent.agent import Agent
from haystack.components.generators.chat.openai import OpenAIChatGenerator
from haystack_integrations.tools.mcp import MCPToolset, StdioServerInfo
from haystack.dataclasses.chat_message import ChatMessage

server_info = StdioServerInfo(
    command="uvx",
    args=["deepset-mcp"],
    env={
        "DEEPSET_API_KEY": os.getenv("DEEPSET_API_KEY"),
        "DEEPSET_WORKSPACE": os.getenv("DEEPSET_WORKSPACE")  # Optional
    }
)

# Only provide pipeline management tools
pipeline_toolset = MCPToolset(
    server_info=server_info,
    tool_names=[
        "list_pipelines",
        "get_pipeline", 
        "create_pipeline",
        "update_pipeline",
        "deploy_pipeline",
    ]
)

# Create chat generator
generator = OpenAIChatGenerator(
    model="gpt-5",
    api_key=os.getenv("OPENAI_API_KEY")
)

# Create specialized pipeline management agent
pipeline_agent = Agent(
    chat_generator=generator,
    tools=pipeline_toolset,
    system_prompt="You are a pipeline management specialist. Help users deploy, monitor, and manage their deepset AI pipelines."
)

# Use for pipeline-specific tasks
query = "Deploy my search-pipeline and check if deployment was successful"
result = pipeline_agent.run([ChatMessage.from_user(query)])
```

### Combining deepset tools with other capabilities

Create agents that bridge deepset platform with external systems:

```python
from haystack.components.websearch import SerperDevWebSearch
from haystack.mcptools import MCPToolset, StdioServerInfo

# Configure multiple tool sources
deepset_toolset = MCPToolset(server_info=server_info)
web_search = SerperDevWebSearch()

# Create multi-capability agent
multi_tool_agent = Agent(
    chat_generator=generator,
    tools=[deepset_toolset, web_search],
    system_prompt="You help users improve their deepset AI pipelines by researching best practices and applying them to existing configurations."
)

# Agent can now search web and manage deepset resources
query = """Search the web for latest best practices in RAG pipeline design, 
then check my existing deepset pipelines and suggest improvements"""
result = multi_tool_agent.run([ChatMessage.from_user(query)])
```

### Remote MCP server configuration

For production deployments, connect to a remote deepset MCP server:

```python
from haystack.mcptools import MCPToolset, SSEServerInfo

# Configure remote server connection
remote_server_info = SSEServerInfo(
    url="https://your-deepset-mcp-server.com/mcp",
    headers={
        "Authorization": f"Bearer {os.getenv('DEEPSET_API_KEY')}"
    }
)

# Create toolset with remote connection
remote_toolset = MCPToolset(server_info=remote_server_info)

# Create agent with remote tools
remote_agent = Agent(
    chat_generator=generator,
    tools=remote_toolset,
    system_prompt="You have access to the deepset AI platform through remote tools. Help users manage their pipelines and debug issues."
)
```


## How to create custom referenceable and explorable tools

This guide shows how to create custom tools that can both accept object references as parameters and store their outputs for later reference. This enables efficient multi-step workflows with large data structures.

### Understanding memory types

Tools can be configured with different memory behaviors:

- **`NO_MEMORY`**: Standard tools that return raw outputs
- **`EXPLORABLE`**: Tools store outputs in the object store for later reference
- **`REFERENCEABLE`**: Tools accept object references (`@obj_123`) as parameters
- **`EXPLORABLE_AND_REFERENCEABLE`**: Tools both accept references and store outputs

### Method 1: Using build_tool with ToolConfig

This is the recommended approach for integrating with the deepset MCP server infrastructure.

#### Create your custom tool function

```python
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.shared_models import DeepsetPipeline

async def analyze_pipeline_performance(
    *, 
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    days_to_analyze: int = 30
) -> dict:
    """Analyze pipeline performance metrics over time.
    
    :param client: The deepset API client
    :param workspace: The workspace containing the pipeline
    :param pipeline_name: Name of the pipeline to analyze
    :param days_to_analyze: Number of days to include in analysis
    :return: Performance analysis results
    """
    if not pipeline_name:
        return {"error": "Pipeline name is required"}
    
    # Get pipeline logs using the proper pipeline resource method
    try:
        # Fetch pipeline logs using the pipeline resource
        logs_response = await client.pipelines(workspace).get_logs(
            pipeline_name=pipeline_name,
            limit=100  # Get more logs for analysis
        )
        
        if not logs_response.data:
            return {
                "pipeline_name": pipeline_name,
                "analysis_period_days": days_to_analyze,
                "total_requests": 0,
                "message": "No logs found for this pipeline. The pipeline may not be deployed or has no recent activity."
            }
        
        # Analyze performance metrics from the logs
        logs_data = logs_response.data
        error_logs = [log for log in logs_data if log.level.lower() in ["error", "critical"]]
        warning_logs = [log for log in logs_data if log.level.lower() == "warning"]
        
        # Calculate basic metrics
        total_logs = len(logs_data)
        error_rate = len(error_logs) / total_logs if total_logs > 0 else 0
        
        # Extract recommendations based on log analysis
        recommendations = []
        if error_rate > 0.1:  # More than 10% error rate
            recommendations.append("High error rate detected. Check pipeline configuration and component settings.")
        if len(warning_logs) > 5:
            recommendations.append("Multiple warnings found. Review pipeline components for potential issues.")
        if total_logs < 10:
            recommendations.append("Low log activity. Verify pipeline is receiving requests and properly deployed.")
        
        # Default recommendations
        if not recommendations:
            recommendations.extend([
                "Pipeline appears to be running smoothly",
                "Consider monitoring memory and CPU usage during peak hours",
                "Review indexing performance if using retrieval components"
            ])
        
        analysis = {
            "pipeline_name": pipeline_name,
            "analysis_period_days": days_to_analyze,
            "total_log_entries": total_logs,
            "error_count": len(error_logs),
            "warning_count": len(warning_logs),
            "error_rate_percentage": round(error_rate * 100, 2),
            "most_recent_log": logs_data[0].timestamp if logs_data else None,
            "recommendations": recommendations,
            "sample_errors": [log.message for log in error_logs[:3]] if error_logs else []
        }
        
        return analysis
        
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}
```

#### Configure and register the tool

```python
from mcp.server.fastmcp import FastMCP
from deepset_mcp.mcp import build_tool, ToolConfig, MemoryType
from deepset_mcp.mcp.store import initialize_or_get_initialized_store

# Create server instance
mcp = FastMCP("Custom Analysis MCP Server")

# Initialize object store
store = initialize_or_get_initialized_store(
    backend="memory",  # or "redis" for production
    ttl=1800  # 30 minutes
)

# Configure tool with memory capabilities
config = ToolConfig(
    needs_client=True,
    needs_workspace=True,
    memory_type=MemoryType.EXPLORABLE_AND_REFERENCEABLE  # Both accepts references and stores output
)

# Build enhanced tool
enhanced_tool = build_tool(
    base_func=analyze_pipeline_performance,
    config=config,
    api_key="your-api-key",
    workspace="your-workspace",  # Optional: can be provided per call
    use_request_context=False,
    object_store=store
)

# Register with descriptive name
mcp.add_tool(
    enhanced_tool,
    name="analyze_pipeline_performance",
    description="Analyze pipeline performance metrics and provide optimization recommendations. Accepts pipeline configs by reference for efficient processing."
)

# Run server
mcp.run(transport="stdio")
```

### Method 2: Using decorators directly

For more control over the memory behavior, use the decorators directly.

#### Setup object store and explorer

```python
from deepset_mcp.tokonomics import ObjectStore, RichExplorer, InMemoryBackend
from deepset_mcp.tokonomics import explorable_and_referenceable

# Initialize object store with custom configuration
store = ObjectStore(
    backend=InMemoryBackend(),
    ttl=3600  # 1 hour TTL
)

# Create explorer with custom limits
explorer = RichExplorer(
    store=store,
    max_items=50,              # Show more items in collections
    max_string_length=500,     # Longer string previews
    max_depth=5,               # Deeper object exploration
    max_search_matches=20,     # More search results
    search_context_length=200  # More context around matches
)
```

#### Apply decorators to your function

```python
@explorable_and_referenceable(object_store=store, explorer=explorer)
async def merge_pipeline_configs(
    base_config: dict,
    override_config: dict,
    merge_strategy: str = "deep"
) -> dict:
    """Merge two pipeline configurations with specified strategy.
    
    :param base_config: Base pipeline configuration
    :param override_config: Configuration values to merge/override
    :param merge_strategy: Strategy for merging ('shallow' or 'deep')
    :return: Merged pipeline configuration
    """
    if merge_strategy == "shallow":
        return {**base_config, **override_config}
    
    # Deep merge implementation
    def deep_merge(base: dict, override: dict) -> dict:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    return deep_merge(base_config, override_config)

# Register the decorated function directly
mcp.add_tool(merge_pipeline_configs, name="merge_pipeline_configs")
```

### Workflow examples

These tools enable efficient multi-step workflows:

#### Example 1: Pipeline analysis workflow

```python
# Step 1: Get pipeline configuration (returns @obj_001)
get_pipeline("production-search-pipeline")

# Step 2: Analyze performance using stored config (saves tokens)
analyze_pipeline_performance(
    pipeline_config="@obj_001",  # Reference to stored pipeline config
    days_to_analyze=90
)
# Returns @obj_002 with analysis results

# Step 3: View specific recommendations without re-running analysis
get_from_object_store("@obj_002", path="recommendations")
```

#### Example 2: Configuration management workflow

```python
# Step 1: Get base configuration
get_pipeline("base-template")  # Returns @obj_003

# Step 2: Create environment-specific overrides
environment_overrides = {
    "retriever": {"top_k": 20},
    "llm": {"model": "gpt-4"},
    "indexing": {"batch_size": 1000}
}

# Step 3: Merge configurations efficiently
merge_pipeline_configs(
    base_config="@obj_003",  # Reference avoids re-transmitting large config
    override_config=environment_overrides,
    merge_strategy="deep"
)
# Returns @obj_004 with merged configuration

# Step 4: Deploy the merged configuration
create_pipeline(config="@obj_004", name="production-search-v2")
```

### Best practices

#### Tool design

- **Accept complex objects as references**: For parameters like `pipeline_config`, `data_batch`, or `analysis_results`
- **Return structured data**: Tools returning dicts, lists, or Pydantic models work well with the object store
- **Provide detailed docstrings**: Help LLMs understand when to use references vs. direct values

#### Memory configuration

- **Use `EXPLORABLE`** for tools that return large outputs others might need
- **Use `REFERENCEABLE`** for tools that process large inputs efficiently
- **Use `EXPLORABLE_AND_REFERENCEABLE`** for tools in multi-step workflows

#### Object store tuning

```python
# Production configuration
store = initialize_or_get_initialized_store(
    backend="redis",
    redis_url="redis://your-redis-cluster:6379",
    ttl=1800  # 30 minutes - balance between efficiency and memory usage
)

# Custom explorer for your data types
explorer = RichExplorer(
    store=store,
    max_items=30,           # Adjust based on typical data size
    max_string_length=400,  # Consider your typical string content
    max_depth=4,            # Match your data structure complexity
)
```

### Error handling

Reference-enabled tools provide helpful error messages:

```python
# Invalid reference format
validate_pipeline(config="obj_123")  # Missing @ prefix
# Error: Parameter 'config' expects dict, got string 'obj_123'. Use '@obj_id' for references.

# Expired or missing object
analyze_pipeline_performance(pipeline_config="@obj_999")
# Error: Object @obj_999 not found or expired

# Invalid path
get_from_object_store("@obj_001", path="nonexistent.field")
# Error: Object '@obj_001' does not have a value at path 'nonexistent.field'
```

This approach enables cost-effective, error-resistant workflows while maintaining the flexibility of direct parameter passing when needed.
