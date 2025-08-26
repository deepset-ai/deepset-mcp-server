# deepset-mcp

**The official MCP server and Python SDK for the deepset AI platform**

deepset-mcp provides two powerful layers for interacting with the [deepset AI platform](https://www.deepset.ai/products-and-services/deepset-ai-platform):

- **MCP Server**: Enables AI agents to build and debug pipelines on the deepset platform through 30+ specialized tools
- **Python SDK**: Provides programmatic access to many deepset platform resources for developers

## Quick Start

Get started with the MCP server in 2 minutes:

1. Install `uv` (Python package manager):
   ```bash
   pipx install uv
   ```

2. Configure your MCP client (Cursor example):
   ```json
   {
     "mcpServers": {
       "deepset": {
         "command": "uvx",
         "args": ["deepset-mcp"],
         "env": {
           "DEEPSET_WORKSPACE": "your-workspace",
           "DEEPSET_API_KEY": "your-api-key"
         }
       }
     }
   }
   ```

3. Start building: *"Create a RAG pipeline with hybrid retrieval using Claude Sonnet as the LLM"*

## What You Can Do

**With the MCP Server:**

- Create and deploy AI pipelines through natural language

- Debug pipeline issues with intelligent log analysis

- Manage indexes, templates, and workspace resources

- Test pipelines interactively through agents


**With the Python SDK:**

- Programmatically manage pipelines, indexes, and workspaces

- Build custom tooling on top of deepset platform APIs

- Integrate deepset capabilities into existing applications

- Automate deployment and management workflows

## Documentation Structure

### [Installation](installation.md)
Set up deepset-mcp with Cursor, Claude Desktop, or other MCP clients.

### Guides
- **[MCP Server](guides/mcp_server.md)**: Configure and customize the MCP server
- **[API SDK](guides/api_sdk.md)**: Use the Python SDK programmatically

### Concepts
- **[MCP Server Concepts](concepts/mcp_server_concepts.md)**: Understanding tools, workspaces, and agent workflows
- **[SDK Concepts](concepts/sdk_concepts.md)**: Core patterns for API usage

### Reference
- **[MCP Server Reference](reference/mcp_reference.md)**: Complete server configuration options
- **[Tool Reference](reference/tool_reference.md)**: All 30+ available MCP tools
- **[API SDK Reference](reference/api_sdk_reference.md)**: Full SDK documentation

## Benefits

**Faster Development**: Build pipelines through conversation instead of clicking through UIs

**Intelligent Debugging**: Agents analyze logs and suggest fixes automatically  

**Flexible Access**: Choose between agent-driven workflows (MCP) or direct API control (SDK)

**Production Ready**: Built by deepset with enterprise-grade reliability
