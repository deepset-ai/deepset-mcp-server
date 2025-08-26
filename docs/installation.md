# Installation

Get the deepset MCP server running in your preferred environment. The server enables AI agents to interact with the deepset AI platform through standardized tools.

## Prerequisites

Before installing the deepset MCP server, ensure you have:

- A deepset AI platform account
- An API key for the deepset platform ([create one here](https://docs.cloud.deepset.ai/docs/generate-api-key))
- Python package manager `uv` installed

## Installing uv

If `uv` is not installed on your system, install it using one of these methods:

**If Python is already installed:**
```bash
pipx install uv
```

**Mac/Linux (no Python required):**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | more"
```

## Installation Methods

Choose your installation method based on your use case:

### For MCP Clients (Cursor, Claude Desktop)

This method is recommended for users who want to integrate with MCP-compatible AI tools.

The server will be automatically installed and managed when you configure your MCP client:

**Cursor Configuration:**

Create a file named `mcp.json` in your `.cursor` directory at the project root:

```json
{
  "mcpServers": {
    "deepset": {
      "command": "uvx",
      "args": ["deepset-mcp"],
      "env": {
        "DEEPSET_WORKSPACE": "your_workspace_name",
        "DEEPSET_API_KEY": "your_api_key"
      }
    }
  }
}
```

💡 **Note:** The `DEEPSET_WORKSPACE` is optional. If not provided, the AI agent will need to specify the workspace name when calling tools.

**Claude Desktop Configuration:**

Edit your Claude Desktop configuration file at `/Users/your_user/Library/Application Support/Claude/claude_desktop_config.json` (Mac):

```json
{
  "mcpServers": {
    "deepset": {
      "command": "uvx",
      "args": ["deepset-mcp"],
      "env": {
        "DEEPSET_WORKSPACE": "your_workspace_name",
        "DEEPSET_API_KEY": "your_api_key"
      }
    }
  }
}
```

💡 **Note:** The `DEEPSET_WORKSPACE` is optional. If not provided, the AI agent will need to specify the workspace name when calling tools.

### For Direct Python Integration

Install the package directly for use in your Python applications:

**Using pip:**
```bash
pip install deepset-mcp
```

**Using uv:**
```bash
uv add deepset-mcp
```

After installation, you can use the server programmatically in your Python code:

```python
from deepset_mcp import configure_mcp_server
from mcp.server.fastmcp import FastMCP

# Create and configure the MCP server
mcp = FastMCP("Deepset MCP Server")
configure_mcp_server(mcp_server_instance=mcp)

# Run the server
mcp.run()
```

### For Command Line Usage

Run the server directly from the command line:

**Using uvx (recommended):**
```bash
uvx deepset-mcp --workspace your_workspace --api-key your_api_key
```

**If installed globally:**
```bash
deepset-mcp --workspace your_workspace --api-key your_api_key
```

💡 **Note:** The `--workspace` parameter is optional. If omitted, the AI agent will need to specify the workspace name when calling tools.

### Using Docker

For containerized environments, use the official Docker image:

```json
{
  "mcpServers": {
    "deepset": {
      "command": "/usr/local/bin/docker",
      "args": [
        "run",
        "-i",
        "-e",
        "DEEPSET_WORKSPACE",
        "-e",
        "DEEPSET_API_KEY",
        "deepset/deepset-mcp-server:main"
      ],
      "env": {
       "DEEPSET_WORKSPACE": "your_workspace_name",
       "DEEPSET_API_KEY": "your_api_key"
     }
    }
  }
}
```

💡 **Note:** The `DEEPSET_WORKSPACE` environment variable is optional. If not provided, the AI agent will need to specify the workspace name when calling tools.

## Verification

After installation, verify the server is working:

1. **For MCP clients:** Check that the deepset server appears in your client's tools menu
2. **For command line:** Run `uvx deepset-mcp --list-tools` to see available tools
3. **For Python integration:** Import the module without errors

## Next Steps

- View in-depth [guides for working with the MCP server](guides/mcp_server.md)
- Learn about [available tools](reference/tool_reference.md)
